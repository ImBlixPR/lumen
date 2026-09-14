import QtQuick
import QtQuick.Window
import QtQuick.Effects
import QtQuick.Layouts
import Lumen
import "components"

// The floating orbital player. There's no frame and no background, just the book's disc,
// its progress orbit, and three controls orbiting it. FloatingPlayer (Python) owns the
// window, placement, mask and state; App owns everything about playback.
Window {
    id: win

    readonly property var g: FloatingPlayer.geometry
    readonly property string phase: FloatingPlayer.state
    readonly property bool expanded: phase === "expanded"
    readonly property var center: g.centers[phase] || g.centers.hidden
    readonly property var home: g.centers.expanded
    readonly property real progress: App.duration > 0 ? App.position / App.duration : 0
    readonly property int travel: Theme.reduceMotion ? 0 : 420
    property real reveal: expanded ? 1 : 0

    visible: false
    color: "transparent"
    title: qsTr("Lumen player")

    Behavior on reveal { NumberAnimation { duration: Theme.reduceMotion ? 0 : 360; easing.type: Easing.OutCubic } }

    // -- the object: disc + its orbit, moving together ------------------------------------------
    Item {
        id: orbit
        width: arc.width
        height: arc.height
        x: win.center[0] - width / 2
        y: win.center[1] - height / 2
        Behavior on x { NumberAnimation { duration: win.travel; easing.type: Easing.OutCubic } }
        Behavior on y { NumberAnimation { duration: win.travel; easing.type: Easing.OutCubic } }

        Item {
            id: disc
            anchors.centerIn: parent
            width: win.g.disc
            height: width
            opacity: win.phase === "collapsed" ? 0.9 : 1
            Behavior on opacity { NumberAnimation { duration: Theme.base } }

            Rectangle {  // ambient blue/lavender glow
                anchors.centerIn: parent
                width: parent.width * 1.22
                height: width
                radius: width / 2
                color: Theme.c.orbGlow
                opacity: win.expanded ? 0.9 : 0.45
                layer.enabled: true
                layer.effect: MultiEffect { blurEnabled: true; blur: 1.0; blurMax: 48 }
                Behavior on opacity { NumberAnimation { duration: Theme.slow } }
            }
            RectangularShadow {
                anchors.fill: rim
                radius: rim.radius
                offset: Qt.vector2d(0, Theme.shadow.md.y * 2)
                blur: Theme.shadow.lg.blur
                color: Theme.c.shadow
            }
            Rectangle {  // frosted glass rim around the artwork
                id: rim
                anchors.fill: parent
                radius: width / 2
                color: Theme.c.orbGlass
                border.width: Theme.size.hairline
                border.color: Theme.c.orbBorder
            }

            Item {
                id: artwork
                anchors.fill: parent
                anchors.margins: Math.round(parent.width * 0.05)

                Image {
                    id: art
                    anchors.fill: parent
                    source: App.book.cover || ""
                    sourceSize.width: win.g.disc * 2
                    sourceSize.height: win.g.disc * 2
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    visible: false
                }
                MultiEffect {
                    anchors.fill: parent
                    source: art
                    visible: art.status === Image.Ready
                    maskEnabled: true
                    maskSource: roundMask
                    maskThresholdMin: 0.5
                    maskSpreadAtMin: 1.0
                }
                Item {
                    id: roundMask
                    anchors.fill: parent
                    layer.enabled: true
                    visible: false
                    Rectangle { anchors.fill: parent; radius: width / 2; color: Theme.c.textPrimary }
                }

                Rectangle {  // no artwork: a calm generated visual instead of an empty hole
                    anchors.fill: parent
                    radius: width / 2
                    visible: art.status !== Image.Ready
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: Theme.c.accent }
                        GradientStop { position: 1.0; color: Theme.c.accentFill }
                    }
                    Repeater {
                        model: 3
                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * (0.42 + index * 0.18)
                            height: width
                            radius: width / 2
                            color: "transparent"
                            border.width: Theme.size.hairline
                            border.color: Theme.c.orbBorder
                            opacity: 0.5 - index * 0.14
                        }
                    }
                    Icon {
                        anchors.centerIn: parent
                        name: "headphones"
                        size: parent.width * 0.3
                        stroke: 1.5
                        color: Theme.c.onAccent
                    }
                }

                Rectangle {  // glass sheen over the artwork
                    anchors.fill: parent
                    radius: width / 2
                    opacity: 0.35
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: Theme.c.highlight }
                        GradientStop { position: 0.45; color: "transparent" }
                    }
                }

                NumberAnimation on opacity { id: artFade; from: 0.15; to: 1; duration: Theme.slow; easing.type: Easing.OutCubic; running: false }
            }

            // Hover is tracked by FloatingPlayer's cursor polling (near → peek, on the disc →
            // expanded). A click on the disc jumps straight to the full player; dragging it
            // moves the player up or down the screen edge, and the spot is remembered.
            MouseArea {
                property real pressY: 0
                property bool moved: false

                anchors.fill: parent
                cursorShape: moved ? Qt.ClosedHandCursor : Qt.PointingHandCursor
                Accessible.role: Accessible.Button
                Accessible.name: qsTr("Show player controls")

                onPressed: (mouse) => {
                    pressY = mapToGlobal(mouse.x, mouse.y).y
                    moved = false
                    FloatingPlayer.beginDrag(pressY)
                }
                onPositionChanged: (mouse) => {
                    const y = mapToGlobal(mouse.x, mouse.y).y
                    if (Math.abs(y - pressY) > 4)
                        moved = true
                    if (moved)
                        FloatingPlayer.dragTo(y)
                }
                onReleased: {
                    FloatingPlayer.endDrag()
                    if (!moved)
                        FloatingPlayer.reveal()
                    moved = false
                }
            }
        }

        ProgressArc {
            id: arc
            anchors.centerIn: parent
            radius: win.g.arcRadius
            progress: win.progress
            interactive: win.expanded
            opacity: win.phase === "collapsed" ? 0.55 : 1
            Behavior on opacity { NumberAnimation { duration: Theme.base } }
            onSeekRequested: (fraction) => FloatingPlayer.seekFraction(fraction)
        }
    }

    Connections {
        target: App
        function onBookChanged() { artFade.restart() }  // new book: the artwork fades in, the player stays put
    }

    // -- timestamp, riding on the orbit ---------------------------------------------------------
    Rectangle {
        x: win.g.timestamp[0] - width / 2
        y: win.g.timestamp[1] - height / 2
        width: stamp.implicitWidth + Theme.space.sm
        height: stamp.implicitHeight + Theme.space.xxs
        radius: height / 2
        color: Theme.c.orbGlassStrong
        border.width: Theme.size.hairline
        border.color: Theme.c.orbBorder
        opacity: win.reveal
        visible: opacity > 0.01

        Txt {
            id: stamp
            anchors.centerIn: parent
            kind: "caption"
            font.features: { "tnum": 1 }
            text: App.formatTime(App.position) + " / " + App.formatTime(App.duration)
        }
    }

    // -- the three orbiting controls ------------------------------------------------------------
    component OrbControl: GlassOrb {
        property var target: [0, 0]
        // Controls fan out from the disc as it expands, and fold back in as it collapses.
        x: win.home[0] + (target[0] - win.home[0]) * (0.72 + 0.28 * win.reveal) - width / 2
        y: win.home[1] + (target[1] - win.home[1]) * (0.72 + 0.28 * win.reveal) - height / 2
        opacity: win.reveal
        visible: opacity > 0.01
        enabled: win.expanded
    }
    OrbControl {
        target: win.g.play
        diameter: win.g.playSize
        iconName: App.playing ? "pause" : "play"
        tip: App.playing ? qsTr("Pause") : qsTr("Play")
        onClicked: FloatingPlayer.playPause()
    }
    OrbControl {
        target: win.g.library
        diameter: win.g.buttonSize
        iconName: "library-big"
        tip: qsTr("Open library")
        onClicked: FloatingPlayer.openLibrary()
    }
    OrbControl {
        target: win.g.settings
        diameter: win.g.buttonSize
        iconName: "settings"
        tip: qsTr("Player settings")
        onClicked: FloatingPlayer.toggleSettings()
    }

    // -- title and chapter, secondary to the artwork --------------------------------------------
    Rectangle {
        x: win.g.info[0]
        y: win.g.info[1]
        width: win.g.info[2]
        height: win.g.info[3]
        radius: Theme.radius.lg
        color: Theme.c.orbGlassStrong
        border.width: Theme.size.hairline
        border.color: Theme.c.orbBorder
        opacity: win.reveal
        visible: opacity > 0.01

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: Theme.space.md
            anchors.rightMargin: Theme.space.md
            spacing: 2

            Txt {
                width: parent.width
                kind: "callout"
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                text: App.book.title || ""
            }
            Txt {
                width: parent.width
                kind: "footnote"
                secondary: true
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                text: App.chapter !== "" ? App.chapter : (App.book.author || "")
            }
        }
    }

    // -- settings popover: only settings the app already has ------------------------------------
    Item {
        x: win.g.popover[0]
        y: win.g.popover[1]
        width: win.g.popover[2]
        height: win.g.popover[3]
        opacity: FloatingPlayer.settingsOpen ? 1 : 0
        scale: FloatingPlayer.settingsOpen ? 1 : 0.96
        visible: opacity > 0.01
        transformOrigin: Item.TopRight
        Behavior on opacity { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }

        RectangularShadow {
            anchors.fill: sheet
            radius: sheet.radius
            offset: Qt.vector2d(Theme.shadow.lg.x, Theme.shadow.lg.y)
            blur: Theme.shadow.lg.blur
            spread: Theme.shadow.lg.spread
            color: Theme.c.shadow
        }
        Rectangle {
            id: sheet
            anchors.fill: parent
            radius: Theme.radius.xl
            color: Theme.c.orbGlassStrong
            border.width: Theme.size.hairline
            border.color: Theme.c.orbBorder
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.space.md
            spacing: Theme.space.sm

            Txt { kind: "headline"; text: qsTr("Player") }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space.xs
                Icon { name: "volume-2"; size: Theme.size.iconSm + 2; color: Theme.c.textSecondary }
                LSlider {
                    Layout.fillWidth: true
                    from: 0
                    to: 1
                    value: Settings.values.volume
                    Accessible.name: qsTr("Volume")
                    onMoved: Settings.set("volume", value)
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Txt { Layout.fillWidth: true; kind: "body"; text: qsTr("Speed") }
                SpeedStepper {
                    value: App.rate
                    onChangeRequested: (value) => App.setRate(value)
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Txt { Layout.fillWidth: true; kind: "body"; text: qsTr("Subtitles") }
                LToggle {
                    checked: SubtitleOverlay.shown
                    Accessible.name: qsTr("Show subtitles")
                    onToggled: SubtitleOverlay.setShown(checked)
                }
            }
            Item { Layout.fillHeight: true }
            LButton {
                Layout.fillWidth: true
                text: qsTr("All settings…")
                onClicked: {
                    FloatingPlayer.closeSettings()
                    App.showSettings()
                }
            }
        }
    }
}
