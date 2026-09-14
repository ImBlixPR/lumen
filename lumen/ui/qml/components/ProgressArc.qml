import QtQuick
import QtQuick.Shapes
import Lumen

// Playback progress as an orbit around the disc: a barely-there full ring, a brighter played
// arc with a soft glow, and a small playhead. Click or drag along the ring to seek; presses
// anywhere else fall through to what's underneath.
Item {
    id: root

    property real radius: 100
    property real progress: 0  // 0…1
    property real lineWidth: 3
    property bool interactive: true
    signal seekRequested(real fraction)

    property bool dragging: false
    property real dragProgress: 0
    readonly property real shown: dragging ? dragProgress : Math.max(0, Math.min(1, progress))

    function fractionAt(x, y) {
        let a = Math.atan2(x - width / 2, -(y - height / 2))
        if (a < 0) a += 2 * Math.PI
        return a / (2 * Math.PI)
    }
    function onRing(x, y) {
        return Math.abs(Math.hypot(x - width / 2, y - height / 2) - radius) < lineWidth * 4 + 6
    }

    width: (radius + lineWidth * 6) * 2
    height: width
    Accessible.role: Accessible.ProgressBar
    Accessible.name: qsTr("Playback progress")

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        ShapePath {  // unplayed: extremely subtle
            strokeColor: Theme.c.arcTrack
            strokeWidth: root.lineWidth * 0.66
            fillColor: "transparent"
            PathAngleArc {
                centerX: root.width / 2; centerY: root.height / 2
                radiusX: root.radius; radiusY: root.radius
                startAngle: 0; sweepAngle: 360
            }
        }
        ShapePath {  // glow under the played part
            strokeColor: Theme.c.orbGlow
            strokeWidth: root.lineWidth * 4
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            PathAngleArc {
                centerX: root.width / 2; centerY: root.height / 2
                radiusX: root.radius; radiusY: root.radius
                startAngle: -90; sweepAngle: 360 * root.shown
            }
        }
        ShapePath {  // played
            strokeColor: Theme.c.arcFill
            strokeWidth: root.lineWidth
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            PathAngleArc {
                centerX: root.width / 2; centerY: root.height / 2
                radiusX: root.radius; radiusY: root.radius
                startAngle: -90; sweepAngle: 360 * root.shown
            }
        }
    }

    Rectangle {  // playhead
        readonly property real angle: 2 * Math.PI * root.shown
        width: root.lineWidth * 3.4
        height: width
        radius: width / 2
        x: root.width / 2 + root.radius * Math.sin(angle) - width / 2
        y: root.height / 2 - root.radius * Math.cos(angle) - height / 2
        color: Theme.c.onAccent
        border.width: Theme.size.hairline
        border.color: Theme.c.arcFill
        visible: root.shown > 0
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.interactive
        hoverEnabled: true
        onPressed: (mouse) => {
            if (!root.onRing(mouse.x, mouse.y)) {
                mouse.accepted = false
                return
            }
            root.dragging = true
            root.dragProgress = root.fractionAt(mouse.x, mouse.y)
        }
        onPositionChanged: (mouse) => {
            cursorShape = (root.dragging || root.onRing(mouse.x, mouse.y)) ? Qt.PointingHandCursor : Qt.ArrowCursor
            if (root.dragging)
                root.dragProgress = root.fractionAt(mouse.x, mouse.y)
        }
        onReleased: (mouse) => {
            if (root.dragging) {
                root.dragging = false
                root.seekRequested(root.fractionAt(mouse.x, mouse.y))
            }
        }
    }
}
