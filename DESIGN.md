# Lumen design system

The single source of truth is [`lumen/ui/theme/tokens.json`](lumen/ui/theme/tokens.json).
`Theme` ([theme.py](lumen/ui/theme/theme.py)) exposes it to QML as a singleton and builds the
tray-menu stylesheet from it. Components read tokens only. `tests/test_contrast.py` fails the
build if any text or control pairing drops below WCAG 2.2 AA in either appearance.

## Direction

Calm, content-first, Apple-inspired:
- **Space and hierarchy:** generous whitespace, a clear type hierarchy, one accent color.
- **Glass:** the primary material. Translucent panels sit over the OS material (Mica on
  Windows 11), with a 1px hairline edge, a faint top highlight and a soft shadow.
- **Neumorphism:** used only on tactile controls, the play button and the speed capsule.
  It's adapted so the control keeps a visible boundary of at least 3:1 and its glyph at
  least 4.5:1. Classic same-color neumorphism fails both.
- **Motion:** 150–300 ms with ease-out or a spring. Every duration goes through
  `Theme.fast/base/slow`, which become 0 when Windows "Animation effects" is off.

## Color

Colors follow the system light/dark setting live, or a forced appearance set in Settings →
Playback.

| Token | Light | Dark | Use |
|---|---|---|---|
| `bg` | `#F5F5F7` | `#1C1C1E` | Window base (a 45% wash over Mica) |
| `bgElevated` | `#FFFFFF` | `#2C2C2E` | Popovers, knobs, keycaps |
| `surface` | `rgba(255,255,255,.72)` | `rgba(44,44,46,.66)` | Glass panels, fields |
| `surfaceStrong` | `rgba(255,255,255,.94)` | `rgba(44,44,46,.96)` | Hovered fields, tooltips |
| `surfaceSunken` | `rgba(0,0,0,.05)` | `rgba(255,255,255,.06)` | Tracks, segmented background |
| `surfaceHover` / `surfacePressed` | 4% / 8% black | 6% / 10% white | Interaction states |
| `hairline` | `rgba(0,0,0,.08)` | `rgba(255,255,255,.10)` | 1px glass edges, dividers |
| `highlight` | `rgba(255,255,255,.80)` | `rgba(255,255,255,.07)` | Glass top highlight |
| `textPrimary` | `#1D1D1F` | `#F5F5F7` | Body text |
| `textSecondary` | `#5E5E63` | `#AEAEB2` | Captions, hints (≥ 4.5:1 on every surface) |
| `textDisabled` | `#A1A1A6` | `#636366` | Disabled only (exempt from AA) |
| `controlBoundary` | `#8A8A8E` | `#7C7C80` | Borders that identify controls (≥ 3:1) |
| `accent` | `#0066CC` | `#4DA3FF` | Accent text, icons, progress |
| `accentFill` | `#0066CC` | `#0B68D0` | Filled buttons, play disc, switches |
| `onAccent` | `#FFFFFF` | `#FFFFFF` | Text and icons on `accentFill` |
| `accentSoft` | 12% accent | 16% accent | Selection backgrounds |
| `danger` / `success` | `#C4262E` / `#1E7F3C` | `#FF6B6B` / `#4CD07D` | Errors, installed state |
| `neuLight` / `neuDark` | white 95% / navy 16% | white 7% / black 55% | Neumorphic shadow pair |

Dark mode splits the accent in two. No single blue gives white text 4.5:1 *and* stands out
4.5:1 against a near-black background, so `accent` (text) and `accentFill` (fills) differ.

**Overlay.** Subtitle text is `#FFFFFF` on `#141416` at a default opacity of 62%. That's the
lowest opacity that keeps white text at 4.5:1 over a pure white page, and it is tested over
white, black, grey and yellow backdrops. Settings warns below 58%. There are five text color
presets: white, warm white, yellow, mint and sky.

## Typography

| Family | Stack |
|---|---|
| UI | Segoe UI Variable Text → SF Pro Text → Inter (bundled) → Segoe UI |
| Display | Segoe UI Variable Display → SF Pro Display → Inter → Segoe UI |
| Arabic script | IBM Plex Sans Arabic (bundled) → Segoe UI → Geeza Pro → Noto Sans Arabic |

Subtitles and language names written in Arabic script use IBM Plex Sans Arabic explicitly
(`Theme.familyFor(lang)`). Where Arabic appears inside other UI text, Qt falls back to the
system font, Segoe UI. PySide6 6.11 doesn't expose Qt's per-script
`addApplicationFallbackFontFamily`, but the app registers it automatically on versions that do.

| Style | Size / line (px) | Weight |
|---|---|---|
| caption | 12 / 16 | 400 |
| footnote | 13 / 18 | 400 |
| body | 15 / 22 | 400 |
| callout | 15 / 22 | 600 |
| headline | 17 / 24 | 600 |
| title3 | 20 / 26 | 600 |
| title2 | 24 / 30 | 700 |
| title1 | 32 / 38 | 700 |
| overlay | 28 / 38 (you set 18–56) | 500 |

## Space, shape, depth

- **Spacing (4/8 grid):** `xxs 4 · xs 8 · sm 12 · md 16 · lg 24 · xl 32 · xxl 48 · xxxl 64`
- **Radii:** `sm 6 · md 10 · lg 14 · xl 20 · pill 999`. The subtitle pill uses
  `min(height/2, 30)`.
- **Shadows:**
  - `sm`: 0/1, blur 3
  - `md`: 0/4, blur 16
  - `lg`: 0/12, blur 40, spread −4
  - `neu`: ±5px offset pair, blur 14
- **Blur levels:** `thin 20 · regular 30 · thick 50`. These are reserved for platforms
  without an OS material. On Windows the blur comes from DWM (Mica or Acrylic) and its radius
  isn't adjustable.
- **Sizes:** control 32, large control 40, field 52, play button 64, cover 208, sidebar 200,
  knob 20, switch 44×26.

## Screens

1. **Onboarding** (in the player window). A dot stepper, then five pages that slide and
   crossfade: welcome (mark and three features), languages (two searchable pickers with a
   swap), models (six speech cards and two translation cards with speed/accuracy meters and a
   GPU/CPU badge), download (per-model progress, MB/s, retry), and ready (hotkeys as keycaps,
   "Open an audiobook").
2. **Player.**
   - Toolbar: open, device label, subtitles on/off, lock/unlock, settings.
   - Middle: a 208px cover with a large shadow (or a gradient placeholder), with the chapter,
     title (title1), author and a language-pair chip beside it.
   - A glass transport panel:
     - scrubber, with processed coverage drawn behind the playhead and chapter gaps
     - elapsed and remaining time
     - speed capsule, back one sentence, −15s, the neumorphic play button, +15s, volume
     - processing line: "Transcribed 12 of 45 min · 8 min ahead" with a thin progress bar
   - Empty state: a glass drop card.
3. **Settings** (separate Mica window). A sidebar with Languages, Models, Subtitles,
   Shortcuts, Playback and About. Each page stacks glass groups of rows (label and hint on the
   left, control on the right). Subtitles has a live preview: the real `SubtitlePill` over a
   half bright-page, half dark-video sample.
4. **Overlay.** A glass pill with up to three centered lines, RTL-aware, crossfading in
   220 ms. Unlocked, it shows an accent border, side grips and a placeholder hint. You drag it
   to move, pull the ends to resize, and scroll to change the text size.
5. **Tray menu.**
   - Items: play/pause, back one sentence, show subtitles, unlock to move, open player, open
     book, settings, quit.
   - Styling: rounded, token-styled, with tinted Lucide icons.
6. **Floating player** (docked to the right edge of the screen, a third of the way down,
   no frame or background). It stays clear of the top-right corner and the top 64 px, where
   windows keep their caption buttons and tabs, and it can be dragged along the edge.
   - **The disc:** the book's artwork, masked to a circle with a frosted glass rim, a soft
     glass sheen and an ambient blue/lavender glow (`orbGlass`, `orbBorder`, `orbGlow`).
     With no artwork, it shows an accent gradient with concentric rings and a headphones
     glyph.
   - **The progress orbit:** it sits just outside the disc. The unplayed ring is barely
     visible (`arcTrack`), while the played arc is brighter (`arcFill`), glows softly and
     ends in a small playhead. The timestamp is a small glass pill riding on the orbit.
   - **The controls:** three glass orbs outside the disc on the side facing into the screen:
     settings at about 10:45, library at 9 and play/pause (larger) at about 7:15. They fan
     out from the disc as it expands. The timestamp rides at the top of the orbit.
   - **Title and chapter:** a small glass box below. Settings open a glass popover to the
     left.
   - **Motion:** the disc and orbit travel together in 420 ms (OutCubic), and the controls,
     timestamp and info fade in over 360 ms. With reduced motion, everything jumps
     straight to its final position.
7. **Library** (the main window's home view).
   - **Sidebar:** the Lumen mark, then Library, Favorites, Recently Played (these two with
     small secondary counts), Now Playing (the player screen above) and Settings, with a
     small glass "Playing / Paused" card at the bottom.
   - **Favorites and Recently Played:** these views reuse the library list with a filter,
     their own title and their own empty state ("No favorites yet", "Nothing played yet").
     The Add buttons show only in Library. A favorited book shows a filled accent heart
     (`heart:fill` in the icon provider), and Recently Played adds "· Today" and similar to
     each row.
   - **Library view:** a title2 header with the book count and "Add books" and "Add folder"
     buttons, a search field with a leading icon, then the list.
   - **Book rows:**
     - Each row shows a 56 px rounded cover (or an accent tile with the initial), the title
       (headline), the author (footnote), and progress (a thin bar with "43% · 12 min left",
       or "Finished").
     - Hovering shows play/pause and remove buttons.
     - The loaded book is highlighted with `accentSoft` and an accent hairline.
     - Missing files are dimmed, with the note in `danger`.
   - **Empty states:** "Your library is empty" and "No books match …" each get a soft
     accent circle icon and a hint.

## Components (`lumen/ui/qml/components`)

- **Text and icons:**
  - `Txt`: type scale.
  - `Icon`: Lucide via the tinted image provider.
  - `Tip`
  - `FocusRing`
- **Surfaces:** `GlassPanel`, `Badge`, `Toast`.
- **Buttons:** `IconButton`, `NeuButton`, `LButton`.
- **Inputs:** `LSlider`, `Scrubber`, `SpeedStepper`, `LToggle`, `SegmentedControl`,
  `LanguagePicker`, `HotkeyChip`.
- **Display:** `LProgressBar`, `DownloadList`, `ModelCard`, `SubtitlePill`.

Every interactive control has hover and press states, a keyboard focus ring and an
accessible name.
