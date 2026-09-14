import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import Lumen

// On/off switch. Off: sunken track with a 3:1 boundary. On: accent track.
Switch {
    id: control

    implicitHeight: Theme.size.control
    implicitWidth: indicator.width + (text !== "" ? spacing + contentItem.implicitWidth : 0)
    spacing: Theme.space.sm
    padding: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus

    indicator: Rectangle {
        x: control.leftPadding
        y: (control.height - height) / 2
        width: Theme.size.toggleWidth
        height: Theme.size.toggleHeight
        radius: height / 2
        color: control.checked ? Theme.c.accentFill : Theme.c.surfaceSunken
        border.width: control.checked ? 0 : Theme.size.hairline
        border.color: Theme.c.controlBoundary
        Behavior on color { ColorAnimation { duration: Theme.base } }

        Rectangle {
            id: knob
            readonly property real inset: (parent.height - height) / 2
            width: parent.height - Theme.space.xxs - 2
            height: width
            radius: width / 2
            y: inset
            x: control.checked ? parent.width - width - inset : inset
            color: Theme.c.onAccent
            Behavior on x { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }

            RectangularShadow {
                z: -1
                anchors.fill: parent
                radius: parent.radius
                offset: Qt.vector2d(Theme.shadow.sm.x, Theme.shadow.sm.y)
                blur: Theme.shadow.sm.blur
                color: Theme.c.shadow
            }
        }
        FocusRing {
            show: control.visualFocus
            ringRadius: parent.radius
        }
    }

    contentItem: Txt {
        text: control.text
        visible: text !== ""
        leftPadding: control.indicator.width + control.spacing
    }
}
