import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import Lumen

// Segmented control with a sliding thumb. options: [{ value, label }].
Item {
    id: root

    property var options: []
    property var value
    signal activated(var value)

    function indexOfValue() {
        for (let i = 0; i < options.length; ++i)
            if (options[i].value === value) return i
        return -1
    }

    implicitWidth: row.implicitWidth + Theme.space.xxs * 2
    implicitHeight: Theme.size.control + Theme.space.xxs
    Accessible.role: Accessible.PageTabList

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius.md
        color: Theme.c.surfaceSunken
        border.width: Theme.size.hairline
        border.color: Theme.c.hairline
    }

    Rectangle {
        id: thumb
        readonly property Item target: { repeater.count; return repeater.itemAt(root.indexOfValue()) }
        visible: target !== null
        x: target ? row.x + target.x : 0
        y: row.y
        width: target ? target.width : 0
        height: row.height
        radius: Theme.radius.md - Theme.space.xxs / 2
        color: Theme.c.bgElevated
        border.width: Theme.size.hairline
        border.color: Theme.c.controlBoundary
        Behavior on x { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }

        RectangularShadow {
            z: -1
            anchors.fill: parent
            radius: parent.radius
            offset: Qt.vector2d(Theme.shadow.sm.x, Theme.shadow.sm.y)
            blur: Theme.shadow.sm.blur
            color: Theme.c.shadow
        }
    }

    Row {
        id: row
        anchors.centerIn: parent

        Repeater {
            id: repeater
            model: root.options

            AbstractButton {
                id: segment
                readonly property bool selected: modelData.value === root.value
                implicitWidth: Math.max(Theme.size.controlLarge * 2, label.implicitWidth + Theme.space.md * 2)
                implicitHeight: Theme.size.control
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.PageTab
                Accessible.name: modelData.label
                Accessible.checked: selected
                onClicked: root.activated(modelData.value)

                background: FocusRing {
                    show: segment.visualFocus
                    ringRadius: Theme.radius.sm
                }
                contentItem: Txt {
                    id: label
                    kind: segment.selected ? "callout" : "body"
                    text: modelData.label
                    horizontalAlignment: Text.AlignHCenter
                    secondary: !segment.selected && !segment.hovered
                }
            }
        }
    }
}
