import QtQuick
import Lumen

// Playback position bar. The faint accent segments behind the playhead show which parts
// of the book already have subtitles; hairline gaps mark chapters.
Item {
    id: root

    property real duration: 0
    property real position: 0
    property var coverage: []   // [[start, end], …] in seconds
    property var chapters: []   // [{start, title}, …]
    signal seekRequested(real seconds)

    property real previewPosition: 0
    readonly property bool dragging: mouse.pressed
    readonly property real shown: dragging ? previewPosition : position
    readonly property bool engaged: mouse.containsMouse || dragging || activeFocus

    function fraction(t) { return duration > 0 ? Math.max(0, Math.min(1, t / duration)) : 0 }
    function timeAt(x) { return Math.max(0, Math.min(1, x / track.width)) * duration }

    implicitHeight: Theme.space.lg
    activeFocusOnTab: true
    Accessible.role: Accessible.Slider
    Accessible.name: qsTr("Playback position")
    Keys.onLeftPressed: seekRequested(Math.max(0, position - 15))
    Keys.onRightPressed: seekRequested(Math.min(duration, position + 15))

    Item {
        id: track
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        height: root.engaged ? Theme.space.xs - 2 : Theme.space.xxs
        Behavior on height { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }

        Rectangle {
            anchors.fill: parent
            radius: height / 2
            color: Theme.c.surfaceSunken
            border.width: Theme.size.hairline
            border.color: Theme.c.hairline
        }
        Repeater {
            model: root.coverage
            Rectangle {
                x: root.fraction(modelData[0]) * track.width
                width: Math.max(Theme.size.hairline, (root.fraction(modelData[1]) - root.fraction(modelData[0])) * track.width)
                height: track.height
                radius: height / 2
                color: Theme.c.accentSoft
            }
        }
        Rectangle {
            width: root.fraction(root.shown) * track.width
            height: track.height
            radius: height / 2
            color: Theme.c.accent
        }
        Repeater {
            model: root.chapters
            Rectangle {
                visible: index > 0
                x: root.fraction(modelData.start) * track.width
                width: Theme.size.focusRing
                height: track.height
                color: Theme.c.bg
            }
        }
    }

    Rectangle {
        id: knob
        width: Theme.space.md - 2
        height: width
        radius: width / 2
        x: root.fraction(root.shown) * track.width - width / 2
        anchors.verticalCenter: track.verticalCenter
        color: Theme.c.bgElevated
        border.width: Theme.size.hairline
        border.color: Theme.c.controlBoundary
        scale: root.engaged ? 1 : 0
        Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
    }

    FocusRing {
        show: root.activeFocus
        ringRadius: Theme.radius.sm
    }

    Rectangle {
        id: bubble
        visible: mouse.containsMouse && root.duration > 0
        width: bubbleLabel.implicitWidth + 2 * Theme.space.xs
        height: bubbleLabel.implicitHeight + Theme.space.xxs
        radius: Theme.radius.sm
        color: Theme.c.surfaceStrong
        border.width: Theme.size.hairline
        border.color: Theme.c.hairline
        x: Math.max(0, Math.min(root.width - width, mouse.mouseX - width / 2))
        y: -height - Theme.space.xxs

        Txt {
            id: bubbleLabel
            anchors.centerIn: parent
            kind: "footnote"
            font.features: { "tnum": 1 }
            text: App.formatTime(root.timeAt(mouse.mouseX))
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        anchors.topMargin: -Theme.space.xs
        anchors.bottomMargin: -Theme.space.xs
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onPressed: (event) => root.previewPosition = root.timeAt(event.x)
        onPositionChanged: (event) => { if (pressed) root.previewPosition = root.timeAt(event.x) }
        onReleased: (event) => root.seekRequested(root.timeAt(event.x))
    }
}
