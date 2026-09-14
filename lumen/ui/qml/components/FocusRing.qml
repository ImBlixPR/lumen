import QtQuick
import Lumen

// Keyboard-focus ring: a 2px accent outline just outside the control.
Rectangle {
    property bool show: false
    property real ringRadius: Theme.radius.md

    anchors.fill: parent
    anchors.margins: -(Theme.size.focusRing + 1)
    radius: ringRadius + Theme.size.focusRing + 1
    color: "transparent"
    border.width: Theme.size.focusRing
    border.color: Theme.c.accent
    visible: show
}
