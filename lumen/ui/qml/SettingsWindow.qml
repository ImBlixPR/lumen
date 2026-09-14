import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Lumen
import "components"

// Settings: sidebar sections with glass groups, including a live subtitle preview.
Window {
    id: win
    objectName: "settingsWindow"

    property bool backdrop: false
    property bool registered: false
    property string section: "languages"
    readonly property var sections: [
        { id: "languages", label: qsTr("Languages"), icon: "languages" },
        { id: "models", label: qsTr("Models"), icon: "cpu" },
        { id: "subtitles", label: qsTr("Subtitles"), icon: "captions" },
        { id: "shortcuts", label: qsTr("Shortcuts"), icon: "keyboard" },
        { id: "playback", label: qsTr("Playback"), icon: "headphones" },
        { id: "about", label: qsTr("About"), icon: "info" }
    ]
    readonly property var samples: ({
        ar: "كان الصباح هادئًا، والمدينة لا تزال نائمة.",
        de: "Der Morgen war still, und die Stadt schlief noch.",
        en: "The morning was quiet, and the city was still asleep.",
        es: "La mañana estaba tranquila y la ciudad aún dormía.",
        fa: "صبح آرام بود و شهر هنوز در خواب بود.",
        fr: "La matinée était calme et la ville dormait encore.",
        he: "הבוקר היה שקט, והעיר עדיין ישנה.",
        hi: "सुबह शांत थी और शहर अभी भी सो रहा था।",
        it: "La mattina era tranquilla e la città dormiva ancora.",
        ja: "朝は静かで、街はまだ眠っていた。",
        ko: "아침은 고요했고 도시는 아직 잠들어 있었다.",
        pt: "A manhã estava tranquila e a cidade ainda dormia.",
        ru: "Утро было тихим, и город ещё спал.",
        tr: "Sabah sessizdi ve şehir hâlâ uyuyordu.",
        ur: "صبح پرسکون تھی اور شہر ابھی سو رہا تھا۔",
        zh: "早晨很安静，城市还在沉睡。"
    })

    function openAt(name) {
        if (name)
            section = name
        show()
        raise()
        requestActivate()
        if (!registered) {
            registered = true
            backdrop = App.registerWindow(win)
        }
    }

    width: Theme.window.settings.width
    height: Theme.window.settings.height
    minimumWidth: Theme.window.settings.minWidth
    minimumHeight: Theme.window.settings.minHeight
    visible: false
    title: qsTr("Lumen Settings")
    color: backdrop ? "transparent" : Theme.c.bg

    Rectangle {
        anchors.fill: parent
        color: Theme.c.bg
        opacity: win.backdrop ? 0.45 : 1
        Behavior on color { ColorAnimation { duration: Theme.base } }
    }

    Shortcut {
        sequences: [StandardKey.Close]
        onActivated: win.close()
    }

    // -- building blocks ------------------------------------------------------------------------
    component SectionTitle: Txt {
        kind: "title2"
        Layout.bottomMargin: Theme.space.xs
    }
    component GroupLabel: Txt {
        kind: "footnote"
        secondary: true
        font.weight: Font.DemiBold
        Layout.topMargin: Theme.space.md
        Layout.leftMargin: Theme.space.xxs
    }
    component Hint: Txt {
        Layout.fillWidth: true
        kind: "footnote"
        secondary: true
        wrapMode: Text.WordWrap
    }
    component Group: GlassPanel {
        default property alias rows: groupColumn.data
        Layout.fillWidth: true
        implicitHeight: groupColumn.implicitHeight + Theme.space.xs * 2
        elevated: false

        ColumnLayout {
            id: groupColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: Theme.space.xs
            anchors.leftMargin: Theme.space.md
            anchors.rightMargin: Theme.space.md
            spacing: 0
        }
    }
    component Divider: Rectangle {
        Layout.fillWidth: true
        implicitHeight: Theme.size.hairline
        color: Theme.c.hairline
    }
    component SettingRow: RowLayout {
        id: settingRow
        property string label
        property string detail
        property color detailColor: Theme.c.textSecondary
        default property alias control: slot.data

        Layout.fillWidth: true
        Layout.minimumHeight: Theme.size.field
        spacing: Theme.space.md

        ColumnLayout {
            Layout.fillWidth: true
            Layout.topMargin: Theme.space.sm
            Layout.bottomMargin: Theme.space.sm
            spacing: 2

            Txt {
                kind: "body"
                text: settingRow.label
            }
            Txt {
                Layout.fillWidth: true
                visible: settingRow.detail !== ""
                kind: "footnote"
                color: settingRow.detailColor
                wrapMode: Text.WordWrap
                text: settingRow.detail
            }
        }
        Row {
            id: slot
            Layout.alignment: Qt.AlignVCenter
            spacing: Theme.space.xs
        }
    }

    // -- layout -------------------------------------------------------------------------------
    RowLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            // Nested layouts default to fillWidth: true, which would starve the page area.
            Layout.fillWidth: false
            Layout.preferredWidth: Theme.size.sidebar
            Layout.maximumWidth: Theme.size.sidebar
            Layout.fillHeight: true
            Layout.margins: Theme.space.md
            spacing: Theme.space.xxs

            Txt {
                Layout.leftMargin: Theme.space.xs
                Layout.topMargin: Theme.space.xs
                Layout.bottomMargin: Theme.space.sm
                kind: "title3"
                text: qsTr("Settings")
            }
            Repeater {
                model: win.sections

                delegate: AbstractButton {
                    id: navItem
                    required property var modelData
                    readonly property bool selected: win.section === modelData.id

                    Layout.fillWidth: true
                    implicitHeight: Theme.size.controlLarge
                    leftPadding: Theme.space.sm
                    rightPadding: Theme.space.sm
                    hoverEnabled: true
                    focusPolicy: Qt.StrongFocus
                    Accessible.role: Accessible.PageTab
                    Accessible.name: modelData.label
                    onClicked: win.section = modelData.id

                    background: Rectangle {
                        radius: Theme.radius.md
                        color: navItem.selected ? Theme.c.accentSoft : navItem.hovered ? Theme.c.surfaceHover : "transparent"
                        Behavior on color { ColorAnimation { duration: Theme.fast } }
                        FocusRing {
                            show: navItem.visualFocus
                            ringRadius: parent.radius
                        }
                    }
                    contentItem: RowLayout {
                        spacing: Theme.space.sm
                        Icon {
                            name: navItem.modelData.icon
                            size: Theme.size.iconSm + 2
                            color: navItem.selected ? Theme.c.accent : Theme.c.textSecondary
                        }
                        Txt {
                            Layout.fillWidth: true
                            kind: navItem.selected ? "callout" : "body"
                            text: navItem.modelData.label
                        }
                    }
                }
            }
            Item { Layout.fillHeight: true }
            Txt {
                Layout.leftMargin: Theme.space.xs
                kind: "caption"
                secondary: true
                text: "Lumen " + App.version
            }
        }

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: Theme.size.hairline
            color: Theme.c.hairline
        }

        Flickable {
            id: scroller
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: pageLoader.height + Theme.space.xl * 2
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ScrollBar.vertical: ScrollBar {
                contentItem: Rectangle {
                    implicitWidth: Theme.space.xxs + 2
                    radius: width / 2
                    color: Theme.c.controlBoundary
                    opacity: parent.active ? 1 : 0.4
                    Behavior on opacity { NumberAnimation { duration: Theme.base } }
                }
            }

            Loader {
                id: pageLoader
                x: Theme.space.xl
                y: Theme.space.xl
                width: scroller.width - Theme.space.xl * 2
                sourceComponent: ({
                    languages: languagesPage, models: modelsPage, subtitles: subtitlesPage,
                    shortcuts: shortcutsPage, playback: playbackPage, about: aboutPage
                })[win.section]
                onLoaded: {
                    scroller.contentY = 0
                    pageReveal.restart()
                }
            }
            NumberAnimation {
                id: pageReveal
                target: pageLoader.item
                property: "opacity"
                from: 0
                to: 1
                duration: Theme.base
                easing.type: Easing.OutCubic
            }
        }
    }

    // -- pages --------------------------------------------------------------------------------
    Component {
        id: languagesPage

        ColumnLayout {
            spacing: Theme.space.sm

            SectionTitle { text: qsTr("Languages") }
            LanguagePicker {
                Layout.fillWidth: true
                caption: qsTr("Audiobook language (what you're learning)")
                value: Settings.values.src_lang
                exclude: Settings.values.tgt_lang
                onPicked: (code) => Settings.set("src_lang", code)
            }
            Hint { text: qsTr("Speech is transcribed in this language. Changing it transcribes the book again.") }
            LanguagePicker {
                Layout.fillWidth: true
                Layout.topMargin: Theme.space.md
                caption: qsTr("Subtitle language (your native language)")
                value: Settings.values.tgt_lang
                exclude: Settings.values.src_lang
                onPicked: (code) => Settings.set("tgt_lang", code)
            }
            Hint { text: qsTr("Only the translation appears on screen. Each subtitle language is cached separately, so switching back is instant.") }
        }
    }

    Component {
        id: modelsPage

        ColumnLayout {
            id: modelsColumn

            property string pendingId: ""
            property string pendingKey: ""
            readonly property var downloads: App.downloadService

            function choose(key, info) {
                if (info.installed) {
                    Settings.set(key, info.id)
                    return
                }
                pendingId = info.id
                pendingKey = key
                downloads.start([info.id])
            }

            spacing: Theme.space.sm

            Connections {
                target: modelsColumn.downloads
                function onFinished(ok, error) {
                    if (ok && modelsColumn.pendingId !== "")
                        Settings.set(modelsColumn.pendingKey, modelsColumn.pendingId)
                    modelsColumn.pendingId = ""
                }
            }

            SectionTitle { text: qsTr("Models") }
            RowLayout {
                spacing: Theme.space.xs
                Badge {
                    text: App.gpu.available ? qsTr("GPU") : qsTr("CPU")
                    iconName: App.gpu.available ? "zap" : "cpu"
                }
                Txt {
                    Layout.fillWidth: true
                    kind: "footnote"
                    secondary: true
                    wrapMode: Text.WordWrap
                    text: App.gpu.available ? qsTr("%1 · models use the GPU automatically").arg(App.gpu.name)
                                            : qsTr("Running on the CPU")
                }
            }

            GroupLabel { text: qsTr("Speech recognition") }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: Theme.space.sm
                rowSpacing: Theme.space.sm

                Repeater {
                    model: App.asrModels
                    ModelCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        info: modelData
                        selected: Settings.values.asr_model === modelData.id
                        recommended: modelData.id === App.gpu.recommendedAsr
                        enabled: !modelsColumn.downloads.busy
                        onClicked: modelsColumn.choose("asr_model", modelData)
                    }
                }
            }

            GroupLabel { text: qsTr("Translation") }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: Theme.space.sm
                rowSpacing: Theme.space.sm

                Repeater {
                    model: App.mtModels
                    ModelCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        info: modelData
                        selected: Settings.values.mt_model === modelData.id
                        recommended: modelData.id === App.gpu.recommendedMt
                        enabled: !modelsColumn.downloads.busy
                        onClicked: modelsColumn.choose("mt_model", modelData)
                    }
                }
            }

            GlassPanel {
                Layout.fillWidth: true
                Layout.topMargin: Theme.space.sm
                visible: modelsColumn.downloads.busy || modelsColumn.pendingId !== ""
                implicitHeight: settingsDownloads.implicitHeight + Theme.space.lg * 2
                elevated: false

                DownloadList {
                    id: settingsDownloads
                    anchors.fill: parent
                    anchors.margins: Theme.space.lg
                    items: modelsColumn.downloads.items
                }
            }

            Hint {
                Layout.topMargin: Theme.space.xs
                text: qsTr("Uninstalled models download when you pick them. A new speech model transcribes books again; earlier transcripts stay cached.")
            }
        }
    }

    Component {
        id: subtitlesPage

        ColumnLayout {
            spacing: Theme.space.sm

            SectionTitle { text: qsTr("Subtitles") }

            // Live preview over a bright page and a dark video, side by side.
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.size.cover
                radius: Theme.radius.lg
                border.width: Theme.size.hairline
                border.color: Theme.c.hairline
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: Theme.overlay.previewBright }
                    GradientStop { position: 0.5; color: Theme.overlay.previewBright }
                    GradientStop { position: 0.5001; color: Theme.overlay.previewDark }
                    GradientStop { position: 1.0; color: Theme.overlay.previewDark }
                }

                Column {
                    x: Theme.space.lg
                    y: Theme.space.lg
                    spacing: Theme.space.xs
                    Repeater {
                        model: [0.34, 0.28, 0.36, 0.22, 0.3, 0.26]
                        Rectangle {
                            width: parent.parent.width * modelData
                            height: Theme.space.xs
                            radius: height / 2
                            color: Theme.overlay.previewBrightInk
                        }
                    }
                }
                Icon {
                    x: parent.width * 0.75 - width / 2
                    y: Theme.space.lg
                    name: "play"
                    size: Theme.size.playButton * 0.6
                    color: Theme.overlay.previewDarkInk
                }

                SubtitlePill {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: Theme.space.lg
                    maxWidth: parent.width - Theme.space.lg * 2
                    maxLines: 2
                    text: win.samples[Settings.values.tgt_lang] || win.samples.en
                    fontSize: Settings.values.overlay_font_size
                    textColor: Settings.values.overlay_text_color
                    backingOpacity: Settings.values.overlay_backing_opacity
                    fontFamily: Theme.familyFor(Settings.values.tgt_lang)
                }
            }

            Group {
                Layout.topMargin: Theme.space.sm

                SettingRow {
                    label: qsTr("Show subtitles")
                    LToggle {
                        checked: SubtitleOverlay.shown
                        Accessible.name: qsTr("Show subtitles")
                        onToggled: SubtitleOverlay.setShown(checked)
                    }
                }
                Divider {}
                SettingRow {
                    label: qsTr("Text size")
                    LSlider {
                        width: Theme.size.cover
                        from: Theme.overlay.minFontSize
                        to: Theme.overlay.maxFontSize
                        stepSize: 1
                        value: Settings.values.overlay_font_size
                        Accessible.name: qsTr("Text size")
                        onMoved: Settings.set("overlay_font_size", value)
                    }
                    Txt {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Theme.space.xl + Theme.space.xs
                        kind: "footnote"
                        secondary: true
                        font.features: { "tnum": 1 }
                        text: Settings.values.overlay_font_size + " pt"
                    }
                }
                Divider {}
                SettingRow {
                    label: qsTr("Text color")
                    Repeater {
                        model: Theme.overlay.textColors
                        AbstractButton {
                            id: swatch
                            readonly property bool selected: String(Settings.values.overlay_text_color).toUpperCase() === String(modelData).toUpperCase()
                            implicitWidth: Theme.size.control - Theme.space.xxs
                            implicitHeight: implicitWidth
                            focusPolicy: Qt.StrongFocus
                            Accessible.role: Accessible.RadioButton
                            Accessible.name: qsTr("Text color %1").arg(modelData)
                            Accessible.checked: selected
                            onClicked: Settings.set("overlay_text_color", modelData)

                            background: Rectangle {
                                radius: width / 2
                                color: modelData
                                border.width: swatch.selected ? Theme.size.focusRing : Theme.size.hairline
                                border.color: swatch.selected ? Theme.c.accent : Theme.c.controlBoundary
                                FocusRing {
                                    show: swatch.visualFocus
                                    ringRadius: parent.radius
                                }
                            }
                        }
                    }
                }
                Divider {}
                SettingRow {
                    label: qsTr("Backing opacity")
                    detail: Settings.values.overlay_backing_opacity < Theme.overlay.minReadableOpacity
                            ? qsTr("Below %1%, text can be hard to read over bright pages.").arg(Math.round(Theme.overlay.minReadableOpacity * 100))
                            : qsTr("How strongly the glass behind the text is tinted.")
                    detailColor: Settings.values.overlay_backing_opacity < Theme.overlay.minReadableOpacity ? Theme.c.danger : Theme.c.textSecondary
                    LSlider {
                        width: Theme.size.cover
                        from: 0.2
                        to: 0.95
                        stepSize: 0.01
                        value: Settings.values.overlay_backing_opacity
                        Accessible.name: qsTr("Backing opacity")
                        onMoved: Settings.set("overlay_backing_opacity", value)
                    }
                    Txt {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Theme.space.xl + Theme.space.xs
                        kind: "footnote"
                        secondary: true
                        font.features: { "tnum": 1 }
                        text: Math.round(Settings.values.overlay_backing_opacity * 100) + "%"
                    }
                }
                Divider {}
                SettingRow {
                    label: qsTr("Position")
                    detail: Settings.values.overlay_position === "custom" ? qsTr("Currently where you dragged it.") : ""
                    SegmentedControl {
                        options: [
                            { value: "bottom", label: qsTr("Bottom") },
                            { value: "top", label: qsTr("Top") }
                        ]
                        value: Settings.values.overlay_position
                        onActivated: (value) => SubtitleOverlay.setPosition(value)
                    }
                }
                Divider {}
                SettingRow {
                    label: qsTr("Move and resize")
                    detail: qsTr("Unlock, then drag the subtitle anywhere or pull its ends. Scroll over it to change the text size.")
                    LToggle {
                        checked: !SubtitleOverlay.locked
                        Accessible.name: qsTr("Unlock subtitles")
                        onToggled: SubtitleOverlay.setLocked(!checked)
                    }
                }
            }
        }
    }

    Component {
        id: shortcutsPage

        ColumnLayout {
            spacing: Theme.space.sm

            SectionTitle { text: qsTr("Shortcuts") }
            Hint {
                text: qsTr("These work from any app, even when Lumen is in the background. Click a shortcut, then press the new keys. Esc cancels, Backspace clears.")
            }
            Group {
                Layout.topMargin: Theme.space.sm

                Repeater {
                    model: [
                        { action: "play_pause", label: qsTr("Play / pause") },
                        { action: "back_sentence", label: qsTr("Back one sentence") },
                        { action: "toggle_overlay", label: qsTr("Show / hide subtitles") },
                        { action: "lock_overlay", label: qsTr("Unlock subtitles to move") }
                    ]
                    delegate: ColumnLayout {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        spacing: 0

                        SettingRow {
                            label: modelData.label
                            detail: App.hotkeyErrors[modelData.action] || ""
                            detailColor: Theme.c.danger
                            HotkeyChip { hotkeyAction: modelData.action }
                        }
                        Divider { visible: index < 3 }
                    }
                }
            }
            Hint {
                Layout.topMargin: Theme.space.sm
                text: qsTr("In the player window: Space plays or pauses, ← and → skip 15 seconds, Shift+← goes back one sentence, Ctrl+O opens a book, Ctrl+Q quits.")
            }
            Hint {
                text: qsTr("From scripts or launchers: lumen --cmd play-pause (also back-sentence, toggle-overlay, lock-overlay).")
            }
        }
    }

    Component {
        id: playbackPage

        ColumnLayout {
            spacing: Theme.space.sm

            SectionTitle { text: qsTr("Playback") }
            Group {
                SettingRow {
                    label: qsTr("Pause when subtitles aren't ready")
                    detail: qsTr("If you jump ahead of processing, playback waits for the translation instead of continuing without it.")
                    LToggle {
                        checked: Settings.values.pause_when_not_ready
                        Accessible.name: qsTr("Pause when subtitles aren't ready")
                        onToggled: Settings.set("pause_when_not_ready", checked)
                    }
                }
                Divider {}
                SettingRow {
                    label: qsTr("Keep running when the window is closed")
                    detail: qsTr("Lumen stays in the tray by the clock. Quit from its menu, the sidebar or Ctrl+Q.")
                    LToggle {
                        checked: Settings.values.close_to_tray
                        Accessible.name: qsTr("Keep running when the window is closed")
                        onToggled: Settings.set("close_to_tray", checked)
                    }
                }
                Divider {}
                SettingRow {
                    label: qsTr("Appearance")
                    SegmentedControl {
                        options: [
                            { value: "system", label: qsTr("System") },
                            { value: "light", label: qsTr("Light") },
                            { value: "dark", label: qsTr("Dark") }
                        ]
                        value: Settings.values.appearance
                        onActivated: (value) => Settings.set("appearance", value)
                    }
                }
                Divider {}
                SettingRow {
                    label: qsTr("Volume")
                    LSlider {
                        width: Theme.size.cover
                        from: 0
                        to: 1
                        value: Settings.values.volume
                        Accessible.name: qsTr("Volume")
                        onMoved: Settings.set("volume", value)
                    }
                }
            }
            Hint {
                text: App.pitchCompensated ? qsTr("Voices keep their natural pitch at every speed.")
                                           : qsTr("At speeds other than 1× voices shift in pitch on this Qt version.")
            }
        }
    }

    Component {
        id: aboutPage

        ColumnLayout {
            spacing: Theme.space.sm

            RowLayout {
                spacing: Theme.space.md
                Rectangle {
                    width: Theme.size.playButton
                    height: width
                    radius: width * 0.23
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: Theme.c.accent }
                        GradientStop { position: 1.0; color: Theme.c.accentFill }
                    }
                    Icon {
                        anchors.centerIn: parent
                        name: "captions"
                        size: parent.width * 0.55
                        color: Theme.c.onAccent
                    }
                }
                ColumnLayout {
                    spacing: 0
                    Txt { kind: "title2"; text: "Lumen" }
                    Txt { kind: "body"; secondary: true; text: qsTr("Version %1").arg(App.version) }
                }
            }
            Txt {
                Layout.fillWidth: true
                Layout.topMargin: Theme.space.sm
                kind: "body"
                wrapMode: Text.WordWrap
                text: qsTr("Listen to audiobooks in the language you're learning, with translated subtitles above every window. All processing happens on this computer.")
            }
            Group {
                Layout.topMargin: Theme.space.sm

                SettingRow { label: qsTr("Speech recognition"); detail: "OpenAI Whisper via faster-whisper and CTranslate2 · MIT" }
                Divider {}
                SettingRow { label: qsTr("Translation"); detail: "Meta NLLB-200 distilled · CC-BY-NC 4.0 (non-commercial use only)" }
                Divider {}
                SettingRow { label: qsTr("Icons"); detail: "Lucide · ISC" }
                Divider {}
                SettingRow { label: qsTr("Fonts"); detail: "Inter, IBM Plex Sans Arabic · SIL Open Font License 1.1" }
                Divider {}
                SettingRow { label: qsTr("Interface"); detail: "Qt 6 via PySide6 · LGPLv3" }
            }
        }
    }
}
