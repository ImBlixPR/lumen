import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import Lumen

// Slider: thin sunken track, accent fill, elevated knob with a visible boundary.
Slider {
    id: control

    implicitHeight: Theme.size.control
    implicitWidth: Theme.size.cover
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus

    background: Item {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: Theme.space.xxs

        Rectangle {
            anchors.fill: parent
            radius: height / 2
            color: Theme.c.surfaceSunken
            border.width: Theme.size.hairline
            border.color: Theme.c.hairline
        }
        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: height / 2
            color: Theme.c.accent
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: Theme.size.knob
        height: width
        radius: width / 2
        color: Theme.c.bgElevated
        border.width: Theme.size.hairline
        border.color: Theme.c.controlBoundary
        scale: control.pressed ? 1.12 : control.hovered ? 1.06 : 1
        Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }

        RectangularShadow {
            z: -1
            anchors.fill: parent
            radius: parent.radius
            offset: Qt.vector2d(Theme.shadow.sm.x, Theme.shadow.sm.y)
            blur: Theme.shadow.sm.blur
            color: Theme.c.shadow
        }
        FocusRing {
            show: control.visualFocus
            ringRadius: parent.radius
        }
    }
}
