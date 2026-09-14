import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import Lumen

// The one tactile control: an accent disc lifted by a soft neumorphic shadow pair that
// sinks when pressed. Adapted for WCAG: the disc keeps ≥3:1 against the window and the
// glyph ≥4.5:1 on the disc, unlike classic same-colour neumorphism.
AbstractButton {
    id: control

    property string iconName: "play"
    property string tip
    property int diameter: Theme.size.playButton
    readonly property color fill: down ? Theme.c.accentPressed
                                : hovered ? Theme.c.accentHover
                                : Theme.c.accentFill
    property real lift: down ? Theme.shadow.neu.distance * 0.35 : Theme.shadow.neu.distance

    implicitWidth: diameter
    implicitHeight: diameter
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    Accessible.role: Accessible.Button
    Accessible.name: tip

    Behavior on lift { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }

    background: Item {
        RectangularShadow {
            anchors.fill: disc
            radius: disc.radius
            offset: Qt.vector2d(-control.lift, -control.lift)
            blur: Theme.shadow.neu.blur
            color: Theme.c.neuLight
        }
        RectangularShadow {
            anchors.fill: disc
            radius: disc.radius
            offset: Qt.vector2d(control.lift, control.lift)
            blur: Theme.shadow.neu.blur
            color: Theme.c.neuDark
        }
        Rectangle {
            id: disc
            anchors.fill: parent
            radius: width / 2
            border.width: Theme.size.hairline
            border.color: Qt.darker(control.fill, 1.18)
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.lighter(control.fill, 1.10) }
                GradientStop { position: 1.0; color: control.fill }
            }
        }
        FocusRing {
            show: control.visualFocus
            ringRadius: disc.radius
        }
    }

    contentItem: Item {
        Icon {
            anchors.centerIn: parent
            // Optical centring: a play triangle looks left-heavy when centred mathematically.
            anchors.horizontalCenterOffset: control.iconName === "play" ? Theme.size.focusRing : 0
            name: control.iconName
            size: Theme.size.iconLg + Theme.space.xxs
            color: Theme.c.onAccent
        }
    }

    scale: down ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }

    Tip {
        visible: control.hovered && control.tip !== ""
        text: control.tip
    }
}
