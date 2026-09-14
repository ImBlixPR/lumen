import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Lumen
import "components"

// First run: welcome → languages → models → download → ready.
Item {
    id: root

    property int step: 0
    readonly property int stepCount: 5
    property string src: Settings.values.src_lang
    property string tgt: Settings.values.tgt_lang
    property string asr: App.gpu.recommendedAsr
    property string mt: App.gpu.recommendedMt
    readonly property var downloads: App.downloadService
    readonly property bool downloadsDone: downloads.items.length > 0
                                          && downloads.items.every(item => item.state === "done")
    readonly property bool downloadFailed: downloads.items.some(item => item.state === "failed")

    function languageName(code) {
        const all = App.languages
        for (let i = 0; i < all.length; ++i)
            if (all[i].code === code) return all[i].name
        return code
    }
    function sizeText(mb) { return mb >= 1000 ? (mb / 1000).toFixed(1) + " GB" : Math.round(mb) + " MB" }
    function selectedSize() {
        let total = 0
        for (const m of App.asrModels.concat(App.mtModels))
            if ((m.id === asr || m.id === mt) && !m.installed) total += m.sizeMb
        return total
    }
    function advance() {
        if (step === 2) {
            step = 3
            App.startModelDownloads(asr, mt)
        } else if (step === 4) {
            App.finishOnboarding(src, tgt, asr, mt)
            App.openBookDialog()
        } else {
            step += 1
        }
    }

    // Pages slide a few pixels and crossfade; with reduced motion they just switch.
    component Page: Item {
        property int index
        visible: opacity > 0
        opacity: root.step === index ? 1 : 0
        x: (index - root.step) * Theme.space.xl
        Behavior on opacity { NumberAnimation { duration: Theme.slow; easing.type: Easing.OutCubic } }
        Behavior on x { NumberAnimation { duration: Theme.slow; easing.type: Easing.OutCubic } }
    }

    component Feature: RowLayout {
        property string iconName
        property string title
        property string detail
        spacing: Theme.space.md
        Layout.fillWidth: true

        Rectangle {
            Layout.alignment: Qt.AlignTop
            width: Theme.size.controlLarge
            height: width
            radius: Theme.radius.md
            color: Theme.c.accentSoft
            Icon {
                anchors.centerIn: parent
                name: parent.parent.iconName
                color: Theme.c.accent
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Txt { kind: "headline"; text: parent.parent.title }
            Txt {
                Layout.fillWidth: true
                kind: "body"
                secondary: true
                wrapMode: Text.WordWrap
                text: parent.parent.detail
            }
        }
    }

    component Keycap: Rectangle {
        property alias text: capLabel.text
        implicitWidth: capLabel.implicitWidth + Theme.space.sm * 2
        implicitHeight: Theme.size.control - Theme.space.xxs
        radius: Theme.radius.sm
        color: Theme.c.bgElevated
        border.width: Theme.size.hairline
        border.color: Theme.c.controlBoundary
        Txt {
            id: capLabel
            anchors.centerIn: parent
            kind: "footnote"
            font.weight: Font.Medium
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space.xl
        spacing: Theme.space.lg

        Row {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.space.xs
            Accessible.role: Accessible.ProgressBar
            Accessible.name: qsTr("Step %1 of %2").arg(root.step + 1).arg(root.stepCount)

            Repeater {
                model: root.stepCount
                Rectangle {
                    width: index === root.step ? Theme.space.lg : Theme.space.xs
                    height: Theme.space.xs
                    radius: height / 2
                    color: index <= root.step ? Theme.c.accent : Theme.c.controlBoundary
                    Behavior on width { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }
                    Behavior on color { ColorAnimation { duration: Theme.base } }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // 0 — Welcome
            Page {
                index: 0
                anchors.fill: parent

                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width, Theme.window.main.minWidth - Theme.space.xxxl * 2)
                    spacing: Theme.space.lg

                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        width: Theme.size.playButton + Theme.space.md
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
                    Txt {
                        Layout.fillWidth: true
                        kind: "title1"
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        text: qsTr("Hear one language. Read another.")
                    }
                    Txt {
                        Layout.fillWidth: true
                        kind: "body"
                        secondary: true
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        text: qsTr("Lumen plays your audiobooks and floats a translated subtitle above every window, so you can keep listening while you work.")
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: Theme.space.sm
                        spacing: Theme.space.md

                        Feature {
                            iconName: "headphones"
                            title: qsTr("Any audiobook")
                            detail: qsTr("MP3, M4A, M4B and WAV, with chapters and cover art.")
                        }
                        Feature {
                            iconName: "captions"
                            title: qsTr("Subtitles above everything")
                            detail: qsTr("A glass caption that clicks through to the apps beneath it.")
                        }
                        Feature {
                            iconName: "cpu"
                            title: qsTr("Private and offline")
                            detail: qsTr("Speech recognition and translation run on this computer.")
                        }
                    }
                }
            }

            // 1 — Languages
            Page {
                index: 1
                anchors.fill: parent

                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width, Theme.window.main.minWidth - Theme.space.xxxl * 2)
                    spacing: Theme.space.lg

                    Txt { kind: "title2"; text: qsTr("Choose your languages") }
                    Txt {
                        Layout.fillWidth: true
                        kind: "body"
                        secondary: true
                        wrapMode: Text.WordWrap
                        text: qsTr("Lumen listens in the language you're learning and shows only the translation.")
                    }
                    LanguagePicker {
                        Layout.fillWidth: true
                        caption: qsTr("I'm learning")
                        value: root.src
                        exclude: root.tgt
                        onPicked: (code) => root.src = code
                    }
                    IconButton {
                        Layout.alignment: Qt.AlignHCenter
                        iconName: "arrow-left-right"
                        rotation: 90
                        tip: qsTr("Swap languages")
                        onClicked: {
                            const s = root.src
                            root.src = root.tgt
                            root.tgt = s
                        }
                    }
                    LanguagePicker {
                        Layout.fillWidth: true
                        caption: qsTr("Show subtitles in")
                        value: root.tgt
                        exclude: root.src
                        onPicked: (code) => root.tgt = code
                    }
                }
            }

            // 2 — Models
            Page {
                index: 2
                anchors.fill: parent

                Flickable {
                    anchors.fill: parent
                    contentHeight: modelsColumn.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollIndicator.vertical: ScrollIndicator {
                        contentItem: Rectangle {
                            implicitWidth: Theme.space.xxs - 1
                            radius: width / 2
                            color: Theme.c.controlBoundary
                        }
                    }

                    ColumnLayout {
                        id: modelsColumn
                        width: parent.width
                        spacing: Theme.space.md

                        Txt { kind: "title2"; text: qsTr("Pick your models") }
                        RowLayout {
                            spacing: Theme.space.xs
                            Badge {
                                text: App.gpu.available ? qsTr("GPU") : qsTr("CPU")
                                iconName: App.gpu.available ? "zap" : "cpu"
                            }
                            Txt {
                                Layout.fillWidth: true
                                kind: "body"
                                secondary: true
                                wrapMode: Text.WordWrap
                                text: App.gpu.available
                                      ? qsTr("%1 found. Processing will run on the GPU.").arg(App.gpu.name)
                                      : qsTr("No compatible GPU found. Lumen will use the CPU; smaller models keep up best.")
                            }
                        }

                        Txt { kind: "headline"; text: qsTr("Speech recognition"); Layout.topMargin: Theme.space.xs }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 3
                            columnSpacing: Theme.space.sm
                            rowSpacing: Theme.space.sm

                            Repeater {
                                model: App.asrModels
                                ModelCard {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Layout.preferredWidth: 1
                                    info: modelData
                                    selected: root.asr === modelData.id
                                    recommended: modelData.id === App.gpu.recommendedAsr
                                    onClicked: root.asr = modelData.id
                                }
                            }
                        }

                        Txt { kind: "headline"; text: qsTr("Translation"); Layout.topMargin: Theme.space.xs }
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
                                    selected: root.mt === modelData.id
                                    recommended: modelData.id === App.gpu.recommendedMt
                                    onClicked: root.mt = modelData.id
                                }
                            }
                        }
                        Txt {
                            Layout.fillWidth: true
                            kind: "footnote"
                            secondary: true
                            wrapMode: Text.WordWrap
                            text: qsTr("NLLB-200 is licensed for non-commercial use (CC-BY-NC 4.0). You can change models later in Settings.")
                        }
                    }
                }
            }

            // 3 — Download
            Page {
                index: 3
                anchors.fill: parent

                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width, Theme.window.main.minWidth - Theme.space.xxxl * 2)
                    spacing: Theme.space.lg

                    Txt { kind: "title2"; text: root.downloadsDone ? qsTr("Models ready") : qsTr("Downloading models") }
                    Txt {
                        Layout.fillWidth: true
                        kind: "body"
                        secondary: true
                        wrapMode: Text.WordWrap
                        text: qsTr("This happens once. Afterwards Lumen works without an internet connection.")
                    }
                    GlassPanel {
                        Layout.fillWidth: true
                        implicitHeight: downloadList.implicitHeight + Theme.space.lg * 2
                        elevated: false

                        DownloadList {
                            id: downloadList
                            anchors.fill: parent
                            anchors.margins: Theme.space.lg
                            items: root.downloads.items
                        }
                    }
                    LButton {
                        visible: root.downloadFailed && !root.downloads.busy
                        iconName: "refresh-cw"
                        text: qsTr("Try again")
                        onClicked: App.startModelDownloads(root.asr, root.mt)
                    }
                }
            }

            // 4 — Ready
            Page {
                index: 4
                anchors.fill: parent

                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width, Theme.window.main.minWidth - Theme.space.xxxl * 2)
                    spacing: Theme.space.lg

                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        width: Theme.size.playButton
                        height: width
                        radius: width / 2
                        color: Theme.c.accentSoft
                        Icon {
                            anchors.centerIn: parent
                            name: "check"
                            size: Theme.size.iconLg + Theme.space.xs
                            color: Theme.c.accent
                        }
                    }
                    Txt {
                        Layout.alignment: Qt.AlignHCenter
                        kind: "title1"
                        text: qsTr("You're all set")
                    }
                    Txt {
                        Layout.fillWidth: true
                        kind: "body"
                        secondary: true
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        text: qsTr("You'll hear %1 and read %2. These shortcuts work from any app:")
                                .arg(root.languageName(root.src)).arg(root.languageName(root.tgt))
                    }
                    GridLayout {
                        Layout.alignment: Qt.AlignHCenter
                        columns: 2
                        columnSpacing: Theme.space.lg
                        rowSpacing: Theme.space.sm

                        Repeater {
                            model: [
                                { label: qsTr("Play / pause"), key: "hotkey_play_pause" },
                                { label: qsTr("Back one sentence"), key: "hotkey_back_sentence" },
                                { label: qsTr("Show / hide subtitles"), key: "hotkey_toggle_overlay" },
                                { label: qsTr("Move subtitles"), key: "hotkey_lock_overlay" }
                            ]
                            delegate: RowLayout {
                                required property var modelData
                                spacing: Theme.space.xs
                                Txt { kind: "body"; text: modelData.label; Layout.preferredWidth: Theme.size.cover * 0.8 }
                                Repeater {
                                    model: String(Settings.values[modelData.key]).split("+")
                                    Keycap { text: modelData }
                                }
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space.sm

            LButton {
                visible: root.step > 0 && root.step !== 3
                text: qsTr("Back")
                onClicked: root.step -= 1
            }
            Item { Layout.fillWidth: true }
            Txt {
                visible: root.step === 2
                kind: "footnote"
                secondary: true
                text: root.selectedSize() > 0 ? qsTr("Download size: %1").arg(root.sizeText(root.selectedSize()))
                                              : qsTr("Already installed")
            }
            LButton {
                primary: true
                enabled: root.step !== 3 || root.downloadsDone
                text: root.step === 0 ? qsTr("Get started")
                      : root.step === 2 ? (root.selectedSize() > 0 ? qsTr("Download") : qsTr("Continue"))
                      : root.step === 4 ? qsTr("Open an audiobook")
                      : qsTr("Continue")
                onClicked: root.advance()
            }
        }
    }
}
