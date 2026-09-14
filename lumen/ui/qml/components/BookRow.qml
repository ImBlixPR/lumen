import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import QtQuick.Layouts
import Lumen

// One book in the library: cover, title, author, length and progress. Click to play it.
AbstractButton {
    id: row

    property var book: ({})
    property bool current: false
    property bool showPlayed: false  // Recently Played: add when it was last played
    signal playRequested()
    signal removeRequested()
    signal favoriteRequested()

    readonly property bool missing: book.exists === false
    readonly property int coverSize: Theme.size.controlLarge + Theme.space.md

    // Letter for the placeholder tile, skipping a leading article ("Les Misérables" → M).
    function initial() {
        const title = (book.title || "?").trim()
        const stripped = title.replace(/^(l'|l’|(le|la|les|un|une|des|el|los|las|der|die|das|il|lo|the|an|a)\s+)/i, "")
        return (stripped || title).charAt(0).toUpperCase()
    }

    function progressText() {
        const detail = progressDetail()
        return showPlayed && book.playedText ? detail + " · " + book.playedText : detail
    }

    function progressDetail() {
        if (missing) return qsTr("File not found")
        if (book.finished) return qsTr("Finished")
        if (!book.started) return App.formatTime(book.duration)
        const left = Math.max(1, Math.round((1 - book.progress) * book.duration / 60))
        return qsTr("%1% · %2 min left").arg(Math.round(book.progress * 100)).arg(left)
    }

    implicitHeight: coverSize + Theme.space.sm * 2
    leftPadding: Theme.space.sm
    rightPadding: Theme.space.sm
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    opacity: missing ? 0.6 : 1
    Accessible.role: Accessible.ListItem
    Accessible.name: (book.title || "") + (book.author ? ", " + book.author : "") + ". " + progressText()
    onClicked: row.playRequested()
    Keys.onDeletePressed: row.removeRequested()
    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_F && event.modifiers === Qt.NoModifier) {
            row.favoriteRequested()
            event.accepted = true
        }
    }

    background: Rectangle {
        radius: Theme.radius.lg
        color: row.current ? Theme.c.accentSoft : row.hovered ? Theme.c.surfaceHover : "transparent"
        border.width: row.current ? Theme.size.hairline : 0
        border.color: Theme.c.accent
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        FocusRing {
            show: row.visualFocus
            ringRadius: parent.radius
        }
    }

    contentItem: RowLayout {
        spacing: Theme.space.md

        Item {
            Layout.preferredWidth: row.coverSize
            Layout.preferredHeight: row.coverSize

            RectangularShadow {
                anchors.fill: parent
                radius: Theme.radius.md
                offset: Qt.vector2d(0, Theme.shadow.sm.y * 2)
                blur: Theme.shadow.md.blur / 2
                color: Theme.c.shadow
            }
            Rectangle {  // no artwork: accent tile with the title's initial
                anchors.fill: parent
                radius: Theme.radius.md
                visible: cover.status !== Image.Ready
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Theme.c.accent }
                    GradientStop { position: 1.0; color: Theme.c.accentFill }
                }
                Txt {
                    anchors.centerIn: parent
                    kind: "title3"
                    color: Theme.c.onAccent
                    text: row.initial()
                }
            }
            Image {
                id: cover
                anchors.fill: parent
                source: row.book.cover || ""
                sourceSize.width: row.coverSize * 2
                sourceSize.height: row.coverSize * 2
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                visible: false
            }
            MultiEffect {
                anchors.fill: parent
                source: cover
                visible: cover.status === Image.Ready
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
                Rectangle { anchors.fill: parent; radius: Theme.radius.md; color: Theme.c.textPrimary }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Txt {
                Layout.fillWidth: true
                kind: "headline"
                elide: Text.ElideRight
                text: row.book.title || ""
            }
            Txt {
                Layout.fillWidth: true
                kind: "footnote"
                secondary: true
                elide: Text.ElideRight
                visible: text !== ""
                text: row.book.author || ""
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space.xs
                LProgressBar {
                    Layout.preferredWidth: Theme.size.cover * 0.4
                    visible: row.book.started && !row.missing
                    value: row.book.progress || 0
                }
                Txt {
                    Layout.fillWidth: true
                    kind: "caption"
                    color: row.missing ? Theme.c.danger : Theme.c.textSecondary
                    font.features: { "tnum": 1 }
                    elide: Text.ElideRight
                    text: row.progressText()
                }
            }
        }

        IconButton {
            // Always visible once favourited; otherwise appears on hover.
            visible: row.book.favorite || row.hovered || row.visualFocus
            iconName: row.book.favorite ? "heart:fill" : "heart"
            iconSize: Theme.size.iconSm
            tint: row.book.favorite ? Theme.c.accent : Theme.c.textPrimary
            tip: row.book.favorite ? qsTr("Remove from favorites (F)") : qsTr("Add to favorites (F)")
            Accessible.checked: row.book.favorite === true
            onClicked: row.favoriteRequested()
        }
        IconButton {
            visible: row.hovered || row.current || row.visualFocus
            enabled: !row.missing
            iconName: row.current && App.playing ? "pause" : "play"
            tip: row.current && App.playing ? qsTr("Pause") : qsTr("Play")
            onClicked: row.current && App.playing ? App.togglePlay() : row.playRequested()
        }
        IconButton {
            visible: row.hovered || row.visualFocus
            iconName: "trash-2"
            iconSize: Theme.size.iconSm
            tip: qsTr("Remove from library (the file is kept)")
            onClicked: row.removeRequested()
        }
    }
}
