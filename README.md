# Lumen

Listen to audiobooks in the language you're learning while a translated subtitle floats
above every window. Lumen transcribes the book with Whisper and translates each sentence
with NLLB-200, entirely on your computer. Only the translation is shown, never the original.

## Read this first: scope and trade-offs

1. **Windows only, for now.** You asked for Windows first. macOS and Linux are designed
   for (every OS call sits behind `lumen/native/`) but not implemented. The porting
   checklist is in [ARCHITECTURE.md](ARCHITECTURE.md#porting-checklist-macos-and-linux-deferred).
2. **The subtitle glass is a tinted pill, not a real OS blur.** On Windows, DWM Acrylic on
   a click-through (layered) window fills the whole window rectangle as an opaque grey
   slab, and it can't be clipped to the pill. So the overlay uses a tinted pill tuned to keep
   text at WCAG AA (4.5:1) over any background. The player and Settings windows do use real
   Windows 11 Mica.
3. **Qt renders with OpenGL on Windows.** With Qt's default Direct3D 11 backend, DWM
   composites translucent windows over white, which breaks Mica. Lumen switches Qt Quick
   to OpenGL at startup.
4. **Exclusive-fullscreen games can't be overlaid** by any normal window. Borderless
   fullscreen apps, browsers and video players work.
5. **Global shortcuts can clash with other apps.** On the development PC another app
   already owned Ctrl+Alt+Space, so play/pause defaults to **Ctrl+Alt+P**. If any shortcut is
   taken, Lumen tells you at startup and on its row in Settings → Shortcuts.
6. **The NLLB-200 translation model is licensed CC-BY-NC 4.0**, meaning non-commercial use
   only. That's fine for personal learning, but Lumen can't be sold with it. Swapping in
   M2M100 (MIT) is a small change in `lumen/models.py` and `pipeline/translator.py`.

## How it works

```
audiobook ─▶ PyAV decode ─▶ faster-whisper (fr, word timestamps, VAD) ─▶ whole sentences
          ─▶ NLLB-200 (fr → ar) ─▶ SQLite cache ─▶ subtitle clock ─▶ overlay (translation only)
```

- **Processing:** a background process always works on the first unprocessed part at or
  after the playhead, so subtitles stay ahead of what you hear. Once everything ahead is
  done, it fills in the rest of the book.
- **Caching:** results are cached per book, so reopening a book is instant. Switching your
  native language re-translates the cached transcript without re-transcribing.

**Stack.** PySide6 (Qt 6.11) with QML for the UI, faster-whisper and CTranslate2 for speech,
and NLLB-200 through CTranslate2 plus SentencePiece for translation (no PyTorch at runtime).
PyAV decodes audio; mutagen reads covers and chapters. See
[ARCHITECTURE.md](ARCHITECTURE.md) for why this stack beat Tauri, the threading model and
the cache. See [DESIGN.md](DESIGN.md) for the full design-token set and the screens.

## Setup (Windows 10/11)

You need [uv](https://docs.astral.sh/uv/). It installs Python 3.12 for the project
automatically, and there's nothing else to install; FFmpeg comes bundled in PyAV and Qt.

```bash
uv sync --extra dev
```

**NVIDIA GPU (optional, much faster):** add the CUDA 12 runtime libraries, about 1.2 GB:

```bash
uv sync --extra gpu --extra dev
```

`uv run` re-syncs the environment to the extras you pass it. With the GPU extra
installed, either keep passing `--extra gpu` or use `uv run --no-sync`, so the CUDA
libraries aren't removed.

**Models (one-time download).** Onboarding does this for you, or you can use the script:

```bash
uv run --no-sync python scripts/setup_models.py
```

- **Auto:** the default picks Large v3 Turbo + NLLB 1.3B on an NVIDIA GPU, and Small +
  NLLB 600M on a CPU.
- **Choose explicitly:** for example `--asr medium --mt nllb-1.3b`.
- **List the options:** `--list`.

Models go to `%LOCALAPPDATA%\Lumen\models`. After that, Lumen never needs the network.

## Run

```bash
uv run --no-sync python -m lumen
```

- **First run:** onboarding asks for your languages (for example French → Arabic), lets you
  pick model sizes and downloads them.
- **Opening a book:** open an MP3, M4A/M4B or WAV, or drop it onto the window.
- **Resuming:** Lumen remembers each book's position and reopens the last book.
- **Closing:** closing the window, the sidebar's **Quit Lumen**, Ctrl+Q, or Ctrl+C in the
  terminal that started it all quit Lumen. Turn on Settings → Playback → "Keep running when
  the window is closed" to keep it in the notification area instead (quit from its tray menu).

**Controls.**

| Where | What |
|---|---|
| Anywhere (global) | **Ctrl+Alt+P** play/pause · **Ctrl+Alt+Left** back one sentence · **Ctrl+Alt+H** show/hide subtitles · **Ctrl+Alt+L** unlock subtitles to move them. All of them can be rebound in Settings. |
| Player window | Space · ← / → ±15 s · Shift+← back one sentence · Ctrl+O open · Ctrl+, settings · Ctrl+Q quit |
| Scripts / launchers | `lumen --cmd play-pause` (also `back-sentence`, `toggle-overlay`, `lock-overlay`, `show`, `quit`), or `lumen "book.m4b"` to open a book in the running instance |
| Unlocked subtitles | Drag to move, pull the ends to resize, scroll to change the text size |

### The library

The main window opens on your **Library**: every audiobook you've added or opened, most
recently played first, with its cover, author, length and how far you've listened.

- **Adding books:**
  - **Add books** lets you pick several files.
  - **Add folder** scans a folder and all its subfolders.
  - You can also drop files or a folder onto the window.
  - Any book you open joins the library automatically.
- **Search:** covers title, author and file name, ignoring capitals and accents (`celestine`
  finds *Célestine*). Ctrl+F jumps to the search box, and ↓ moves into the list.
- **Playing:** click a book, or press Enter on it. It starts playing and the window hands
  off to the floating player. Clicking the book that's already loaded just resumes it.
- **Removing:** the trash icon on a row removes the book from the library. The file itself
  is never touched.
- **Favorites:** the heart on a row (or **F** on a selected row) adds the book to
  **Favorites** in the sidebar. A book keeps its heart when you reopen it or add it again
  from a new location.
- **Recently Played** lists only books you've played, newest first, with when you last
  played them ("Today", "Yesterday", "3 days ago", or a date).
- **Search inside views:** search works in Favorites and Recently Played too. The sidebar
  shows how many books each view has.
- **Moved or missing files:** a moved or renamed file is recognized when you add it again,
  and its progress is kept. Files that can't be found are greyed out as "File not found".
- **Now Playing** in the sidebar is the full player screen (scrubber, speed, volume,
  processing progress). A small card at the bottom of the sidebar shows what's loaded and
  lets you play or pause it.

The library is stored in `library.json` next to `settings.json`. Reading progress comes from
the saved resume positions.

### The floating player

When a book starts playing from the main window, the window fades away and the book floats
at the right edge of the screen, about a third of the way down: a glass disc with its
artwork, a progress orbit, and three controls orbiting it. It stays out of the top-right
corner, where maximized windows keep their minimize, maximize and close buttons, and by
default nothing of it enters the top 64 px (title bars, browser tabs). It has no frame and no background, and it uses the same player
as the main window (there's no second audio engine).

| State | What you see |
|---|---|
| Collapsed | About a third of the disc peeks out of the right edge. No controls. |
| Mouse approaches | More of the disc slides into view. |
| Mouse on the disc (or click it) | The full disc, the progress orbit with its timestamp, the three controls, and the title and chapter. |
| Mouse leaves | It slides back into the edge after about a second. |

- **Play/pause** is the larger glass button below the disc.
- **Library** brings back the main window. Playback continues, and the floating player
  tucks away until the main window is closed again or you start another book.
- **Settings** opens a small popover with volume, speed, subtitles on/off, and **All
  settings…**.
- **Seeking:** click or drag along the progress orbit.
- **Moving it:** drag the disc up or down along the edge. Lumen remembers the spot. To go
  back to the default, set `floating_y` to `-1` in `settings.json`.
- **Click-through:** the window is clipped to the disc and controls, so clicks on the
  transparent area around them reach the app underneath. Proximity is tracked from the
  cursor position rather than an invisible hover zone, so the edge never blocks clicks on
  the app underneath.
- **Size:** the disc scales with the screen, between 120 and 200 px. The player sits on
  the primary screen.

**Subtitles and pausing.** The subtitle is shown only while the audio plays. Pausing fades it
out, and pressing play brings back the sentence at the current position. It also clears when
the book ends, and nothing shows before you first press play.

**Monitors and audio devices.** Sound follows the Windows default output. Plug in an HDMI
monitor or headphones and, once Windows switches to them, playback moves there without
stopping; unplug them and it moves back, with a short message saying where the audio now
plays. If a device disappears mid-sentence, playback resumes from the same point, and the
subtitles wait for the audio instead of running ahead. The subtitle overlay and the floating
player re-position themselves whenever a monitor is plugged in, unplugged, or rescaled. If
you had dragged the subtitles onto a monitor that's gone, they come back to the main screen,
and they return to your spot when that monitor does.

**Without the UI.** This transcribes and translates a book and prints the timed sentences:

```bash
uv run --no-sync python -m lumen.pipeline.worker "book.mp3" --src fr --tgt ar --asr small
```

**Tests:**

```bash
uv run --no-sync python -m pytest
```

**Build a standalone app** (to share it, for example):

```bash
uv run --no-sync python -m PyInstaller lumen.spec --noconfirm
```

This produces a `dist\Lumen\` folder with `Lumen.exe`. Nothing needs installing on the other
PC: no Python and no CUDA. It includes the NVIDIA GPU libraries if the `gpu` extra is
installed, which makes the folder about 2.4 GB (roughly 1.3 GB zipped). On PCs without an
NVIDIA card the same build simply uses the CPU. Models aren't bundled; the first-run setup
downloads them. To share it, zip the whole `dist\Lumen` folder together with
`packaging\How to run Lumen.txt`. Because the exe isn't code-signed, Windows SmartScreen
asks for "More info → Run anyway" the first time.

## What was verified on the development PC

The development PC runs Windows 11 with an RTX 3050 and a 3440×1440 display. Tests used a
2.2-minute French reading (*Ernest & Célestine*, Lambert Wilson), translated French → Arabic.

| Area | Result |
|---|---|
| Unit tests (sentences, scheduler and seam repair, cache, subtitle timing, languages, WCAG contrast) | ✅ 72 passed |
| Pipeline on CPU (Small int8 + NLLB-600M) | ✅ 32 sentences, all translated, at 6.4× real time |
| Cache | ✅ The second run loaded everything with 0.0 s of processing |
| Overlay | ✅ Arabic subtitle rendered RTL in sync with the audio (0:59 → the sentence timed 58.1–60.3 s) |
| Overlay window flags | ✅ Always on top, no taskbar entry, never takes focus, click-through (a hit-test over the subtitle returns the window beneath) |
| Global hotkeys | ✅ Show/hide and back one sentence fire once each. ⚠️ Ctrl+Alt+Space was taken by another app, hence the new default |
| Command channel | ✅ `--cmd play-pause`, `--cmd back-sentence` |
| Back one sentence / end of book | ✅ Jumps to the sentence start or the previous sentence; pressing play on a finished book restarts it |
| Speed | ✅ Measured 0.51× and 2.00×, with pitch compensation on |
| Resume position and settings persistence | ✅ |
| Worker process cleanup | ✅ It exits by itself if the UI is killed |
| GPU (CUDA, RTX 3050 4 GB) | ✅ Detected as `cuda` / `int8_float16`. Large v3 Turbo processed the clip at **22.6× real time** (5.8 s), against 3.9× for the same model on the CPU |
| Player, all six Settings pages, tray menu | ✅ Rendered and checked on screen, with 0 QML warnings |

**Not verified yet:** onboarding driven through the UI (downloads were done by the script),
dragging and resizing the overlay, the overlay above a fullscreen video, light mode, and reduced
motion. (The packaged `Lumen.exe` was tested: it ran the pipeline on the GPU and produced
translated subtitles in a fresh profile.)

**GPU install note:** on the development PC, PyPI delivered the CUDA wheels at only about
0.5 MB/s, so `uv sync --extra gpu` took a long time. Lumen also uses a system-wide CUDA 12 +
cuDNN 9 install if its DLLs are on `PATH`.

## Getting the most accurate subtitles

- **Model size matters most.** The GPU only changes speed: on the RTX 3050 or on the CPU,
  the same model gives essentially the same transcript. Accuracy comes from the model size,
  and the GPU is what makes the big models fast enough.
- **On an NVIDIA GPU, use Large v3 Turbo + NLLB 1.3B** (the automatic choice). Together they
  peaked at about 2.8 GB of GPU memory on the development PC's 4 GB RTX 3050.
- **A misheard word can't be fixed by the translator.** On the test clip, Small heard
  *comptes* ("accounts") where the reader said *contes* ("tales"), and the Arabic said
  "accounts". Large v3 Turbo heard it correctly.
- **Subtitles are capped at about 8 s or 110 characters, split at commas.** Long
  comma-chained dialogue otherwise gets silently cut short by NLLB. In testing, both
  translators dropped the end of a 12-second line.
- **Add the book's character names.** Click **Add character names** under the title in the
  player and type them separated by commas, for example `Ernest, Célestine`. They're saved
  per book and given to Whisper both in its prompt and as "hotwords". The prompt only
  reaches the first 30 seconds of each processing window; hotwords are repeated on every
  segment, so the names help throughout the book. The book is then transcribed again from where you are. For the command-line
  test, use `--names "Ernest, Célestine"`.
- **When these rules change, older transcripts are redone automatically.** Each cache
  records the transcription version that produced it.

**Integrated vs NVIDIA GPU.** On laptops with two GPUs, Windows draws Lumen's windows on the
integrated chip to save battery. That's expected, and it has no effect on the subtitles.
Transcription and translation run through CUDA, which only exists on the NVIDIA GPU. The
device label in the player shows which one is in use.

## Known limitations

- **Overlay:** no real OS blur behind subtitles on Windows (see item 2 at the top).
- **Mica:** it requires Windows 11 22H2 or later. Windows 10 gets the accent blur, and older
  versions an opaque window.
- **Exclusive-fullscreen games:** the overlay can't appear above them.
- **Accuracy:** it depends on the model. Small on CPU handles clear narration well but
  makes mistakes with names and fast dialogue. Use Large v3 Turbo on a GPU if you can.
- **Music-heavy stretches:** Whisper's voice detection skips music, so there are no
  subtitles there, by design.
- **Translation:** NLLB translates sentence by sentence, without context from the
  surrounding sentences.
- **VBR MP3 seeking:** if a variable-bitrate MP3 lacks a seek table, positions after a seek
  can be slightly off. Sequential playback is exact.

## Next steps

1. **macOS and Linux:** port following the checklist in ARCHITECTURE.md (vibrancy through
   `NSVisualEffectView`, the Spaces/fullscreen collection behavior, and Wayland workarounds).
2. **Overlay blur:** try a separate non-layered backdrop window sized to the pill (Acrylic
   plus DWM rounded corners), placed under a click-through text window.
3. **Context-aware translation:** pass the previous sentence, or use an LLM-based
   translator for more natural dialogue.
4. **Learning features:** a "reveal original" hotkey (shown only on demand), and saving
   sentences to a flashcard deck.
5. **Performance:** batched Whisper inference on GPU for faster whole-book processing.
