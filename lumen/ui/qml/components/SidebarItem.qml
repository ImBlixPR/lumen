import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Lumen

// Sidebar navigation row (same look as the Settings sidebar).
AbstractButton {
    id: item

    property string iconName
    property bool selected: false
    property string badge: ""  // small count on the right, e.g. number of favorites

    Layout.fillWidth: true
    implicitHeight: Theme.size.controlLarge
    leftPadding: Theme.space.sm
    rightPadding: Theme.space.sm
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.PageTab
    Accessible.name: text

    background: Rectangle {
        radius: Theme.radius.md
        color: item.selected ? Theme.c.accentSoft : item.hovered ? Theme.c.surfaceHover : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        FocusRing {
            show: item.visualFocus
            ringRadius: parent.radius
        }
    }
    contentItem: RowLayout {
        spacing: Theme.space.sm
        Icon {
            name: item.iconName
            size: Theme.size.iconSm + 2
            color: item.selected ? Theme.c.accent : Theme.c.textSecondary
        }
        Txt {
            Layout.fillWidth: true
            kind: item.selected ? "callout" : "body"
            text: item.text
            elide: Text.ElideRight
        }
        Txt {
            visible: item.badge !== "" && item.badge !== "0"
            kind: "caption"
            secondary: true
            font.features: { "tnum": 1 }
            text: item.badge
        }
    }
}
