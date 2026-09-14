import QtQuick
import QtQuick.Controls.Basic
import Lumen

// Text button. `primary` is the filled accent style; otherwise a bordered glass button.
AbstractButton {
    id: control

    property bool primary: false
    property string iconName

    implicitHeight: Theme.size.controlLarge
    implicitWidth: Math.max(Theme.size.controlLarge * 2.5, label.implicitWidth + leftPadding + rightPadding)
    leftPadding: Theme.space.lg
    rightPadding: Theme.space.lg
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.Button
    Accessible.name: text

    background: Rectangle {
        radius: Theme.radius.md
        opacity: control.enabled ? 1 : 0.5
        color: control.primary
               ? (control.down ? Theme.c.accentPressed : control.hovered ? Theme.c.accentHover : Theme.c.accentFill)
               : (control.down ? Theme.c.surfacePressed : control.hovered ? Theme.c.surfaceHover : Theme.c.surface)
        border.width: control.primary ? 0 : Theme.size.hairline
        border.color: Theme.c.controlBoundary
        Behavior on color { ColorAnimation { duration: Theme.fast } }

        FocusRing {
            show: control.visualFocus
            ringRadius: parent.radius
        }
    }

    contentItem: Item {
        implicitWidth: label.implicitWidth
        implicitHeight: label.implicitHeight

        Row {
            id: label
            anchors.centerIn: parent
            spacing: Theme.space.xs
            opacity: control.enabled ? 1 : 0.6

            Icon {
                visible: control.iconName !== ""
                anchors.verticalCenter: parent.verticalCenter
                name: control.iconName
                size: Theme.size.iconSm + 2
                color: control.primary ? Theme.c.onAccent : Theme.c.textPrimary
            }
            Txt {
                anchors.verticalCenter: parent.verticalCenter
                kind: "callout"
                text: control.text
                color: control.primary ? Theme.c.onAccent : Theme.c.textPrimary
            }
        }
    }

    scale: down ? 0.98 : 1
    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
}
