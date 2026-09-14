import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import Lumen

// A floating glass control for the orbital player: translucent disc, thin light rim, soft
// shadow, and a gentle glow on hover. It floats on its own; there's no toolbar behind it.
AbstractButton {
    id: control

    property string iconName
    property int diameter: 40
    property string tip

    implicitWidth: diameter
    implicitHeight: diameter
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    Accessible.role: Accessible.Button
    Accessible.name: tip

    background: Item {
        Rectangle {
            anchors.centerIn: parent
            width: parent.width + Theme.space.md
            height: width
            radius: width / 2
            color: Theme.c.orbGlow
            opacity: control.hovered ? 1 : 0
            visible: opacity > 0
            layer.enabled: true
            layer.effect: MultiEffect { blurEnabled: true; blur: 1.0; blurMax: 20 }
            Behavior on opacity { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }
        }
        RectangularShadow {
            anchors.fill: glass
            radius: glass.radius
            offset: Qt.vector2d(0, Theme.shadow.sm.y * 2)
            blur: Theme.shadow.md.blur
            color: Theme.c.shadow
        }
        Rectangle {
            id: glass
            anchors.fill: parent
            radius: width / 2
            color: control.down ? Theme.c.orbGlassStrong : Theme.c.orbGlass
            border.width: Theme.size.hairline
            border.color: Theme.c.orbBorder
            Behavior on color { ColorAnimation { duration: Theme.fast } }

            Rectangle {  // soft top highlight, so it reads as glass rather than flat plastic
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Theme.c.highlight }
                    GradientStop { position: 0.55; color: "transparent" }
                }
                opacity: 0.55
            }
        }
        FocusRing {
            show: control.visualFocus
            ringRadius: glass.radius
        }
    }

    contentItem: Item {
        Icon {
            anchors.centerIn: parent
            // Optical centring for the play triangle.
            anchors.horizontalCenterOffset: control.iconName === "play" ? Math.round(control.diameter * 0.04) : 0
            name: control.iconName
            size: Math.round(control.diameter * 0.44)
            color: Theme.c.textPrimary
        }
    }

    scale: down ? 0.94 : hovered ? 1.06 : 1
    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
}
