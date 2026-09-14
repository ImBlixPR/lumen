import QtQuick
import QtQuick.Controls.Basic
import Lumen

// Round, borderless icon button. `active` marks an on-state (e.g. subtitles shown).
AbstractButton {
    id: control

    property string iconName
    property int iconSize: Theme.size.icon
    property color tint: Theme.c.textPrimary
    property string tip
    property bool active: false

    implicitWidth: Theme.size.controlLarge
    implicitHeight: Theme.size.controlLarge
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    Accessible.role: Accessible.Button
    Accessible.name: tip

    background: Rectangle {
        radius: height / 2
        color: control.down ? Theme.c.surfacePressed
             : control.active ? Theme.c.accentSoft
             : control.hovered ? Theme.c.surfaceHover
             : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.fast } }

        FocusRing {
            show: control.visualFocus
            ringRadius: parent.radius
        }
    }

    contentItem: Item {
        Icon {
            anchors.centerIn: parent
            name: control.iconName
            size: control.iconSize
            color: !control.enabled ? Theme.c.textDisabled
                 : control.active ? Theme.c.accent
                 : control.tint
        }
    }

    scale: down ? 0.94 : 1
    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }

    Tip {
        visible: control.hovered && control.tip !== ""
        text: control.tip
    }
}
