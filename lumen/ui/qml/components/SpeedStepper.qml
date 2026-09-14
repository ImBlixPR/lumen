import QtQuick
import QtQuick.Effects
import Lumen

// Playback speed, 0.5× – 2× in quarter steps. A tactile capsule (soft neumorphic lift)
// with a visible boundary so it stays identifiable at 3:1.
Item {
    id: root

    property real value: 1.0
    readonly property real step: 0.25
    readonly property real minimum: 0.5
    readonly property real maximum: 2.0
    signal changeRequested(real value)

    implicitWidth: row.implicitWidth + Theme.space.xxs * 2
    implicitHeight: Theme.size.control + Theme.space.xxs
    Accessible.role: Accessible.SpinBox
    Accessible.name: qsTr("Playback speed %1×").arg(Number(value.toFixed(2)))

    RectangularShadow {
        anchors.fill: capsule
        radius: capsule.radius
        offset: Qt.vector2d(-Theme.shadow.neu.distance / 2, -Theme.shadow.neu.distance / 2)
        blur: Theme.shadow.neu.blur / 2
        color: Theme.c.neuLight
    }
    RectangularShadow {
        anchors.fill: capsule
        radius: capsule.radius
        offset: Qt.vector2d(Theme.shadow.neu.distance / 2, Theme.shadow.neu.distance / 2)
        blur: Theme.shadow.neu.blur / 2
        color: Theme.c.neuDark
    }
    Rectangle {
        id: capsule
        anchors.fill: parent
        radius: height / 2
        color: Theme.c.bgElevated
        border.width: Theme.size.hairline
        border.color: Theme.c.controlBoundary
    }

    Row {
        id: row
        anchors.centerIn: parent

        IconButton {
            iconName: "minus"
            iconSize: Theme.size.iconSm
            implicitWidth: Theme.size.control
            implicitHeight: Theme.size.control
            tip: qsTr("Slower")
            enabled: root.value > root.minimum + 0.001
            onClicked: root.changeRequested(Math.max(root.minimum, root.value - root.step))
        }
        Txt {
            id: speedLabel
            anchors.verticalCenter: parent.verticalCenter
            width: widest.width + Theme.space.xs
            horizontalAlignment: Text.AlignHCenter
            kind: "callout"
            font.features: { "tnum": 1 }
            text: Number(root.value.toFixed(2)) + "×"

            TextMetrics {
                id: widest
                font: speedLabel.font
                text: "1.75×"
            }
        }
        IconButton {
            iconName: "plus"
            iconSize: Theme.size.iconSm
            implicitWidth: Theme.size.control
            implicitHeight: Theme.size.control
            tip: qsTr("Faster")
            enabled: root.value < root.maximum - 0.001
            onClicked: root.changeRequested(Math.min(root.maximum, root.value + root.step))
        }
    }
}
