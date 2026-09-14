import QtQuick
import QtQuick.Effects
import Lumen

// Frosted glass: a translucent fill over the window's OS material, a 1px hairline edge,
// a soft top highlight and an optional soft shadow.
Item {
    id: root

    property real radius: Theme.radius.lg
    property bool elevated: true
    property color fill: Theme.c.surface
    default property alias content: body.data

    RectangularShadow {
        anchors.fill: glass
        visible: root.elevated
        radius: root.radius
        offset: Qt.vector2d(Theme.shadow.md.x, Theme.shadow.md.y)
        blur: Theme.shadow.md.blur
        spread: Theme.shadow.md.spread
        color: Theme.c.shadow
    }

    Rectangle {
        id: glass
        anchors.fill: parent
        radius: root.radius
        color: root.fill
        border.width: Theme.size.hairline
        border.color: Theme.c.hairline
        Behavior on color { ColorAnimation { duration: Theme.base } }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: root.radius
            anchors.rightMargin: root.radius
            anchors.topMargin: Theme.size.hairline
            height: Theme.size.hairline
            color: Theme.c.highlight
        }
    }

    Item {
        id: body
        anchors.fill: parent
    }
}
