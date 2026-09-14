# Lumen architecture

## Processes and threads

```
UI process (Qt event loop, never blocks)                  Worker process (spawned, below-normal priority)
─────────────────────────────────────────                 ────────────────────────────────────────────────
AppController  ── QML singleton "App"                     PipelineWorker.serve()
 ├ PlayerService      QMediaPlayer + QAudioOutput           1. apply every waiting command
 ├ SubtitleTrack      sorted subtitles (bisect)             2. translate backlog near the playhead, else
 ├ SubtitleClock      16 ms timer, smoothed position           transcribe + translate the next window
 ├ OverlayController  overlay window + native layer         3. poll commands mid-window; abort on a far seek
 ├ HotkeyService      Win32 RegisterHotKey (WM_HOTKEY)     ├ AudioDecoder   PyAV → 16 kHz mono float32
 ├ TrayService        QSystemTrayIcon + styled QMenu        ├ Transcriber    faster-whisper (word timestamps, VAD)
 ├ CommandServer      QLocalServer (single instance, CLI)   ├ SentenceBuilder words → whole sentences
 ├ DownloadService    thread: huggingface_hub snapshots     ├ Translator     NLLB-200 via CTranslate2
 ├ SettingsStore      JSON, QML singleton "Settings"        └ CacheStore     SQLite (WAL), the only writer
 └ WorkerBridge ── reader thread ──────── mp.Queue (events) ◀─┘
                └─────────────────────── mp.Queue (commands) ─▶
```

**Why a separate process?** CTranslate2 releases the GIL, but model loading, CUDA
initialization, out-of-memory errors and native crashes would still stall or kill a single
process. With a separate process, a crash only ends processing: the bridge notices,
restarts the worker and reopens the book at the playhead.

- **Worker → UI.** The worker sends plain-dict events. A reader thread in the UI process
  blocks on the queue and re-emits each event as a Qt signal, which Qt delivers on the main
  thread.
- **UI → worker.** Commands are plain dicts put on the command queue: `open`, `playhead`,
  `set_target`, `close` and `shutdown`.
- **Stale events.** Every event carries the `job` id of the book it belongs to, so events
  from a book you just left are ignored.

## Data flow

1. **Opening a book.** The UI hashes the size plus the first and last megabyte (`book_key`),
   reads the metadata (mutagen: title, author, cover, MP4/ID3 chapters) and opens the cache
   read-only. Already-cached subtitles appear at once. The UI then sends `open`, carrying the
   resume position.
2. **Scheduling** ([scheduler.py](lumen/pipeline/scheduler.py)).
   - **Where next:** the first unprocessed time at or after the playhead. Once everything
     ahead is done, it backfills from the start.
   - **Window size:** windows start at 60 s, so the first subtitles arrive quickly, then
     double up to 4 min on the CPU or 8 min on the GPU.
   - **Seeks:** a seek into unprocessed audio resets the window size to 60 s.
3. **Transcription.** Whisper runs with the language set explicitly, word timestamps, VAD
   and `condition_on_previous_text=False`, which avoids repetition loops. The previous
   sentence is passed as the prompt for context. Segments that are almost certainly silence,
   and known subtitle-credit hallucinations, are dropped.
4. **Sentences** ([sentences.py](lumen/pipeline/sentences.py)). Words are merged into whole
   sentences before translation. Splits happen at terminal punctuation, but not after
   abbreviations or initials, nor before a lowercase continuation (dialogue tags such as
   "—¿Vienes? —preguntó él.", or mid-sentence ellipses). They also happen on pauses of 2 s or
   more. Sentences longer than 18 s are force-split at the best comma or pause near the
   middle, and one-word fragments are merged into a neighbor. French spaced punctuation and
   guillemets are handled.
5. **Committing a window** (`plan_commit`). The last sentence of a window may be cut off by
   the window edge, so it's dropped and the next window starts just before it. If a window
   runs into existing coverage (usually after a seek), it decodes 15 s past the seam. It then
   splices at the first sentence boundary both transcriptions agree on, which replaces the
   fragment the seek-started chunk began with.
6. **Translation.** Sentences go to NLLB-200 in batches of up to 24, with the SentencePiece
   format `[src_Latn] tokens </s>` → prefix `[tgt]`. Beam size is 4. Translations are cached
   per target language and model.
7. **Display.** On every commit the worker sends a `region` event (start, end and the new
   rows). The UI's `SubtitleTrack` mirrors the cache's replace rule. The clock samples the
   playback position every 16 ms and interpolates between the media backend's coarse updates.
   It never runs backwards through jitter. A sentence stays up through pauses shorter than
   2 s, lingers 0.8 s after longer ones, and shows for at least 1.2 s. The clock emits only
   when the text changes, and the overlay crossfades the new text in from that same frame.

### Cache (`%LOCALAPPDATA%\Lumen\Cache\books\<key>-<src>-<asr>.sqlite`)

```
meta(key, value)
sentences(id, start, end, text)                                  -- source language, never shown
translations(sentence_id → sentences ON DELETE CASCADE, tgt_lang, mt_model, text)
coverage(start, end)                                             -- merged processed intervals
```

- **One file per (book, source language, speech model):** switching speech models never
  mixes transcripts.
- **Changing only the subtitle language:** transcripts are reused and only translated
  again, nearest the playhead first.
- **Reopening a book:** everything loads from the cache, with no processing.

## Overlay window (Windows)

| Need | How |
|---|---|
| Transparent, frameless | `Qt::FramelessWindowHint`, transparent `QQuickWindow` with alpha buffer, rendered with Qt's **OpenGL** backend. With the default Direct3D 11 backend, DWM composites translucent windows over white, which also breaks Mica on the main windows. |
| No taskbar entry, never steals focus | `Qt::Tool` + `Qt::WindowDoesNotAcceptFocus` (`WS_EX_TOOLWINDOW`, `WS_EX_NOACTIVATE`) |
| Always on top | `Qt::WindowStaysOnTopHint`, re-asserted every 2 s with `SetWindowPos(HWND_TOPMOST)` |
| Click-through | `Qt::WindowTransparentForInput` + `WS_EX_TRANSPARENT \| WS_EX_LAYERED`, toggled in place |
| Move / resize when unlocked | `QWindow::startSystemMove()` / `startSystemResize()` (native, DPI-correct) |
| Glass backing | A tinted pill drawn in QML (`#141416` at 62% by default, tested to keep white text at 4.5:1 over white, black, grey and yellow). DWM Acrylic was tried and dropped: on a layered (click-through) window it fills the whole window rectangle as an opaque slab, and `SetWindowRgn` doesn't clip it. The main and Settings windows do get real Mica. |
| Placement | Remembered as a bottom-centre anchor, so larger text grows upward; validated against the connected screens on start |

## Library

The library lives in `services/book_library.py` (`LibraryStore`, the QML singleton
`Library`) with the views `Home.qml`, `LibraryView.qml` and `components/BookRow.qml`.

- **Data:** `library.json` (in the config folder) indexes what `read_book()` already
  extracts (path, title, author, cover, duration), plus when each book was added and last
  played. Entries are keyed by the same content key as the cache and resume positions, so
  a moved file is matched rather than duplicated. Progress isn't stored twice: it's computed
  from `SettingsStore.position()`.
- **Adding books:** "Add books", "Add folder" and dropped files read their metadata on a
  background thread and hand each entry back to the UI thread through a queued signal. The
  file is saved once at the end.
- **Opening:** `AppController.openBook()` records every opened book (`record_opened`), so
  the library also fills itself as you listen.
- **Search:** `fold()` compares case- and accent-insensitively, and every word must match
  the title, author or file name. Results come most recently played or added first.

## Floating player

The floating player lives in `services/floating_player.py` (`FloatingPlayerController`, the
QML singleton `FloatingPlayer`) and `ui/qml/FloatingPlayer.qml`. It's a presentation layer
only: it reads `App` (position, duration, playing, book, chapter) and calls `App`'s actions.
There's no second audio player.

- **Handoff:** when playback starts while the main window is visible, the controller calls
  `Main.qml`'s `hideToFloating()`, which fades the window out. The window's `visibleChanged`
  then shows the floating player, and hides it again when the main window comes back.
  A book you open yourself starts playing. The last book, reopened at startup, doesn't.
- **Layout:** `orbit_layout(screen)` is pure and unit-tested. It computes the disc size
  (120–200 px), the center for each state, and the positions of the controls, timestamp,
  info box and popover. QML only animates between them.
- **States:** hidden → collapsed (a crescent, about 31% of the disc visible) → peek (about
  66%) → expanded. The disc slides horizontally only. They're driven by polling the global cursor every 50 ms, and the player
  collapses 0.9 s after the cursor leaves.
- **Click-through:** `QWindow.setMask` clips the window to the disc, plus the controls, info
  box and popover when expanded. The mask grows before an expansion animates, and shrinks
  after a collapse settles.
- **Window:** a tool window, frameless, always on top, never takes focus. Topmost is
  re-asserted every 2 s. It's docked to the primary screen's right edge and re-placed when
  the screen geometry changes. It avoids the top-right corner, where maximized windows keep
  their caption buttons: by default the disc sits 32% down the screen and nothing enters
  the top 64 px (`window_top()`, unit-tested). Dragging the disc moves it along the edge,
  and the spot is saved as the `floating_y` setting.

## Hotkeys and the command channel

- **Global hotkeys** use `RegisterHotKey`, caught by a `QAbstractNativeEventFilter`. There's
  no keyboard hook and no elevated permissions.
- **Conflicts:** if another app owns a combination, Settings shows the conflict on that row.
- **While you record a shortcut,** Lumen suspends its own hotkeys, so pressing the old
  combination doesn't trigger it.
- **Single instance:** a named `QLocalServer`. `lumen --cmd play-pause` or `lumen book.m4b`
  forwards to the running instance. That lets any launcher, Stream Deck or AutoHotkey script
  control Lumen.

## Porting checklist (macOS and Linux, deferred)

Everything OS-specific sits behind `lumen/native/__init__.py`. Other platforms already run
through its no-op fallback, just without blur or global hotkeys. To port:

**macOS (`native/macos.py` via pyobjc):**
- **Menu bar only:** `NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)` for
  a menu-bar-only app. This is required for the overlay to appear over other apps'
  fullscreen Spaces.
- **Overlay window level:** `setLevel_(NSStatusWindowLevel)`, and collection behavior
  `CanJoinAllSpaces | FullScreenAuxiliary | Stationary | IgnoresCycle`.
- **Click-through:** `setIgnoresMouseEvents_`. Qt's flag already maps to this.
- **Vibrancy:** reparent the Qt `NSView` (from `winId()`) into an `NSVisualEffectView`
  (`.hudWindow` for the overlay, `.sidebar` / `.windowBackground` for the main windows). Mask
  it with a rounded `maskImage`.
- **Hotkeys:** Carbon `RegisterEventHotKey`, which needs no Accessibility permission, unlike
  event taps.
- **Reduce motion:** `NSWorkspace.accessibilityDisplayShouldReduceMotion`.

**Linux:**
- **X11:** Qt's flags give always-on-top (`_NET_WM_STATE_ABOVE`), skip-taskbar and
  click-through (empty input shape). Blur only works on KWin, through
  `_KDE_NET_WM_BLUR_BEHIND_REGION`. Elsewhere, fall back to the tinted pill (already drawn).
- **Wayland:**
  - **Always-on-top:** no protocol lets a normal window stay on top, and GNOME has no
    layer-shell. The workaround is to start with `QT_QPA_PLATFORM=xcb` (XWayland), or add a
    KDE window rule.
  - **Hotkeys:** apps can't grab global hotkeys. Use the `org.freedesktop.portal.GlobalShortcuts`
    portal (KDE, GNOME 48+) or bind a DE shortcut to `lumen --cmd …`.
  - **Tray:** GNOME needs the AppIndicator extension.
- **Reduce motion:** `gsettings get org.gnome.desktop.interface enable-animations`.
