import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import QtQuick.Layouts
import Lumen
import "components"

// Now playing: cover, title, chapter, transport and processing progress.
Item {
    id: root

    function languageLabel(code) {
        const all = App.languages
        for (let i = 0; i < all.length; ++i)
            if (all[i].code === code) return all[i].native
        return code
    }

    RowLayout {
        id: toolbar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.space.md
        spacing: Theme.space.xxs

        IconButton {
            iconName: "folder-open"
            tip: qsTr("Open audiobook (Ctrl+O)")
            onClicked: App.openBookDialog()
        }
        Item { Layout.fillWidth: true }
        Txt {
            visible: App.device !== ""
            Layout.rightMargin: Theme.space.xs
            kind: "footnote"
            secondary: true
            text: App.device
        }
        IconButton {
            iconName: "captions"
            active: SubtitleOverlay.shown
            tip: SubtitleOverlay.shown ? qsTr("Hide subtitles") : qsTr("Show subtitles")
            onClicked: SubtitleOverlay.toggleShown()
        }
        IconButton {
            iconName: SubtitleOverlay.locked ? "lock" : "lock-open"
            active: !SubtitleOverlay.locked
            tip: SubtitleOverlay.locked ? qsTr("Unlock subtitles to move them") : qsTr("Lock subtitles in place")
            onClicked: App.toggleOverlayLock()
        }
        IconButton {
            iconName: "settings"
            tip: qsTr("Settings (Ctrl+,)")
            onClicked: App.showSettings()
        }
    }

    // Empty state
    Item {
        anchors.fill: parent
        anchors.topMargin: toolbar.height + Theme.space.md
        visible: !App.hasBook

        GlassPanel {
            anchors.centerIn: parent
            width: Math.min(parent.width - Theme.space.xxl * 2, Theme.window.main.minWidth - Theme.space.xxxl * 2)
            height: emptyColumn.implicitHeight + Theme.space.xxl * 2

            ColumnLayout {
                id: emptyColumn
                anchors.centerIn: parent
                width: parent.width - Theme.space.xxl * 2
                spacing: Theme.space.md

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: Theme.size.playButton
                    height: width
                    radius: width / 2
                    color: Theme.c.accentSoft
                    Icon {
                        anchors.centerIn: parent
                        name: "book-open"
                        size: Theme.size.iconLg + Theme.space.xs
                        color: Theme.c.accent
                    }
                }
                Txt {
                    Layout.alignment: Qt.AlignHCenter
                    kind: "title2"
                    text: qsTr("Open an audiobook")
                }
                Txt {
                    Layout.fillWidth: true
                    kind: "body"
                    secondary: true
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: qsTr("MP3, M4A, M4B or WAV. You can also drop a file anywhere in this window.")
                }
                LButton {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.topMargin: Theme.space.xs
                    primary: true
                    iconName: "folder-open"
                    text: qsTr("Choose file…")
                    onClicked: App.openBookDialog()
                }
            }
        }
    }

    // Now playing
    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: toolbar.height + Theme.space.md
        anchors.leftMargin: Theme.space.xl
        anchors.rightMargin: Theme.space.xl
        anchors.bottomMargin: Theme.space.xl
        spacing: Theme.space.lg
        visible: App.hasBook

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.space.xl

            Item {
                id: cover
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: Theme.size.cover
                Layout.preferredHeight: Theme.size.cover

                RectangularShadow {
                    anchors.fill: parent
                    radius: Theme.radius.lg
                    offset: Qt.vector2d(Theme.shadow.lg.x, Theme.shadow.lg.y)
                    blur: Theme.shadow.lg.blur
                    spread: Theme.shadow.lg.spread
                    color: Theme.c.shadow
                }
                Rectangle {
                    anchors.fill: parent
                    radius: Theme.radius.lg
                    visible: art.status !== Image.Ready
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: Theme.c.accent }
                        GradientStop { position: 1.0; color: Theme.c.accentFill }
                    }
                    Icon {
                        anchors.centerIn: parent
                        name: "headphones"
                        size: parent.width * 0.32
                        color: Theme.c.onAccent
                        stroke: 1.5
                    }
                }
                Image {
                    id: art
                    anchors.fill: parent
                    source: App.book.cover || ""
                    sourceSize.width: Theme.size.cover * 2
                    sourceSize.height: Theme.size.cover * 2
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    visible: false
                }
                MultiEffect {
                    anchors.fill: parent
                    source: art
                    visible: art.status === Image.Ready
                    maskEnabled: true
                    maskSource: coverMask
                    maskThresholdMin: 0.5
                    maskSpreadAtMin: 1.0
                }
                Item {
                    id: coverMask
                    anchors.fill: parent
                    layer.enabled: true
                    visible: false
                    Rectangle {
                        anchors.fill: parent
                        radius: Theme.radius.lg
                        color: Theme.c.textPrimary
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: Theme.space.xs

                Txt {
                    Layout.fillWidth: true
                    kind: "footnote"
                    secondary: true
                    elide: Text.ElideRight
                    text: App.chapter
                    visible: App.chapter !== ""
                }
                Txt {
                    Layout.fillWidth: true
                    kind: "title1"
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                    text: App.book.title || ""
                }
                Txt {
                    Layout.fillWidth: true
                    kind: "title3"
                    font.weight: Font.Normal
                    secondary: true
                    elide: Text.ElideRight
                    visible: text !== ""
                    text: App.book.author || ""
                }
                Rectangle {
                    Layout.topMargin: Theme.space.xs
                    implicitWidth: pair.implicitWidth + Theme.space.sm * 2
                    implicitHeight: pair.implicitHeight + Theme.space.xxs * 2
                    radius: height / 2
                    color: Theme.c.surfaceSunken

                    Row {
                        id: pair
                        anchors.centerIn: parent
                        spacing: Theme.space.xs
                        Icon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: "languages"
                            size: Theme.size.iconSm
                            color: Theme.c.textSecondary
                        }
                        Txt {
                            anchors.verticalCenter: parent.verticalCenter
                            kind: "footnote"
                            secondary: true
                            text: root.languageLabel(Settings.values.src_lang) + "  →  " + root.languageLabel(Settings.values.tgt_lang)
                        }
                    }
                }

                // Character names: a spelling hint for Whisper, saved per book.
                AbstractButton {
                    id: namesButton
                    Layout.topMargin: Theme.space.xxs
                    Layout.maximumWidth: parent.width
                    implicitWidth: namesRow.implicitWidth + Theme.space.sm * 2
                    implicitHeight: namesRow.implicitHeight + Theme.space.xxs * 2
                    hoverEnabled: true
                    focusPolicy: Qt.StrongFocus
                    Accessible.role: Accessible.Button
                    Accessible.name: qsTr("Character names")
                    onClicked: namesPopup.open()

                    background: Rectangle {
                        radius: height / 2
                        color: namesButton.hovered ? Theme.c.surfaceHover : "transparent"
                        border.width: Theme.size.hairline
                        border.color: Theme.c.controlBoundary
                        Behavior on color { ColorAnimation { duration: Theme.fast } }
                        FocusRing {
                            show: namesButton.visualFocus
                            ringRadius: parent.radius
                        }
                    }
                    contentItem: Item {
                        implicitWidth: namesRow.implicitWidth
                        implicitHeight: namesRow.implicitHeight

                        Row {
                            id: namesRow
                            anchors.centerIn: parent
                            spacing: Theme.space.xs
                            Icon {
                                anchors.verticalCenter: parent.verticalCenter
                                name: "users"
                                size: Theme.size.iconSm
                                color: Theme.c.textSecondary
                            }
                            Txt {
                                anchors.verticalCenter: parent.verticalCenter
                                width: Math.min(implicitWidth, Theme.size.cover * 1.6)
                                kind: "footnote"
                                secondary: true
                                elide: Text.ElideRight
                                text: App.bookNames !== "" ? App.bookNames : qsTr("Add character names")
                            }
                        }
                    }

                    Popup {
                        id: namesPopup
                        objectName: "namesPopup"

                        function save() {
                            App.setBookNames(namesField.text)
                            close()
                        }

                        y: namesButton.height + Theme.space.xxs
                        width: Theme.size.cover * 2
                        padding: Theme.space.md
                        focus: true
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
                        onOpened: {
                            namesField.text = App.bookNames
                            namesField.focusInput()
                        }

                        enter: Transition {
                            ParallelAnimation {
                                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.fast }
                                NumberAnimation { property: "scale"; from: 0.97; to: 1; duration: Theme.fast; easing.type: Easing.OutCubic }
                            }
                        }
                        exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.fast } }

                        background: Item {
                            RectangularShadow {
                                anchors.fill: namesSheet
                                radius: namesSheet.radius
                                offset: Qt.vector2d(Theme.shadow.lg.x, Theme.shadow.lg.y)
                                blur: Theme.shadow.lg.blur
                                spread: Theme.shadow.lg.spread
                                color: Theme.c.shadow
                            }
                            Rectangle {
                                id: namesSheet
                                anchors.fill: parent
                                radius: Theme.radius.lg
                                color: Theme.c.bgElevated
                                border.width: Theme.size.hairline
                                border.color: Theme.c.hairline
                            }
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.space.sm

                            Txt {
                                kind: "headline"
                                text: qsTr("Character names")
                            }
                            Txt {
                                Layout.fillWidth: true
                                kind: "footnote"
                                secondary: true
                                wrapMode: Text.WordWrap
                                text: qsTr("Names that appear in this book, separated by commas. Lumen uses them so speech recognition spells them correctly, then transcribes the book again.")
                            }
                            LTextField {
                                id: namesField
                                Layout.fillWidth: true
                                placeholder: qsTr("e.g. Ernest, Célestine")
                                onAccepted: namesPopup.save()
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.topMargin: Theme.space.xxs
                                spacing: Theme.space.xs
                                Item { Layout.fillWidth: true }
                                LButton {
                                    text: qsTr("Cancel")
                                    onClicked: namesPopup.close()
                                }
                                LButton {
                                    primary: true
                                    text: qsTr("Save")
                                    onClicked: namesPopup.save()
                                }
                            }
                        }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            implicitHeight: transport.implicitHeight + Theme.space.lg * 2

            ColumnLayout {
                id: transport
                anchors.fill: parent
                anchors.margins: Theme.space.lg
                spacing: Theme.space.sm

                Scrubber {
                    Layout.fillWidth: true
                    duration: App.duration
                    position: App.position
                    coverage: App.coverage
                    chapters: App.book.chapters || []
                    onSeekRequested: (seconds) => App.seek(seconds)
                }
                RowLayout {
                    Layout.fillWidth: true
                    Txt {
                        kind: "footnote"
                        secondary: true
                        font.features: { "tnum": 1 }
                        text: App.formatTime(App.position)
                    }
                    Item { Layout.fillWidth: true }
                    Txt {
                        kind: "footnote"
                        secondary: true
                        font.features: { "tnum": 1 }
                        text: "−" + App.formatTime(Math.max(0, App.duration - App.position))
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space.sm

                    SpeedStepper {
                        id: speed
                        value: App.rate
                        onChangeRequested: (value) => App.setRate(value)
                    }
                    Item { Layout.fillWidth: true }
                    IconButton {
                        iconName: "skip-back"
                        tip: qsTr("Back one sentence (Shift+Left)")
                        onClicked: App.backSentence()
                    }
                    IconButton {
                        iconName: "rotate-ccw"
                        tip: qsTr("Back 15 seconds (Left)")
                        onClicked: App.skip(-15)
                    }
                    NeuButton {
                        Layout.leftMargin: Theme.space.xs
                        Layout.rightMargin: Theme.space.xs
                        iconName: App.playing ? "pause" : "play"
                        tip: App.playing ? qsTr("Pause (Space)") : qsTr("Play (Space)")
                        onClicked: App.togglePlay()
                    }
                    IconButton {
                        iconName: "rotate-cw"
                        tip: qsTr("Forward 15 seconds (Right)")
                        onClicked: App.skip(15)
                    }
                    Item {
                        implicitWidth: Theme.size.controlLarge
                        implicitHeight: Theme.size.controlLarge
                    }
                    Item { Layout.fillWidth: true }
                    RowLayout {
                        Layout.preferredWidth: speed.implicitWidth
                        spacing: Theme.space.xxs
                        Icon {
                            name: "volume-2"
                            size: Theme.size.iconSm + 2
                            color: Theme.c.textSecondary
                        }
                        LSlider {
                            Layout.fillWidth: true
                            from: 0
                            to: 1
                            value: Settings.values.volume
                            Accessible.name: qsTr("Volume")
                            onMoved: Settings.set("volume", value)
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: Theme.space.xxs
                    spacing: Theme.space.sm

                    Icon {
                        name: App.processingState === "done" ? "circle-check"
                              : App.processingState === "error" ? "triangle-alert"
                              : App.device.indexOf("GPU") === 0 ? "zap" : "cpu"
                        size: Theme.size.iconSm
                        color: App.processingState === "error" ? Theme.c.danger : Theme.c.textSecondary
                    }
                    Txt {
                        Layout.fillWidth: true
                        kind: "footnote"
                        secondary: true
                        elide: Text.ElideRight
                        text: App.statusText
                    }
                    LProgressBar {
                        Layout.preferredWidth: Theme.size.cover * 0.7
                        visible: App.processingState === "processing" || App.processingState === "loading"
                        value: App.processingState === "loading" ? -1
                               : App.duration > 0 ? App.processedSeconds / App.duration : 0
                    }
                }
            }
        }
    }
}
