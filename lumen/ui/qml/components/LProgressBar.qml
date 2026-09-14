import QtQuick
import Lumen

// Thin progress bar. value in 0…1; a negative value shows an indeterminate sweep.
Item {
    id: root

    property real value: 0
    readonly property bool indeterminate: value < 0

    implicitHeight: Theme.space.xxs
    implicitWidth: Theme.size.cover
    clip: true
    Accessible.role: Accessible.ProgressBar

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: Theme.c.surfaceSunken
    }

    Rectangle {
        id: fill
        property real sweep: 0
        height: parent.height
        radius: height / 2
        color: Theme.c.accent
        width: root.indeterminate ? parent.width * 0.3 : parent.width * Math.max(0, Math.min(1, root.value))
        x: root.indeterminate ? sweep * (root.width + width) - width : 0
        Behavior on width {
            enabled: !root.indeterminate
            NumberAnimation { duration: Theme.slow; easing.type: Easing.OutCubic }
        }

        NumberAnimation on sweep {
            running: root.indeterminate && root.visible && !Theme.reduceMotion
            from: 0
            to: 1
            duration: Theme.slow * 5
            loops: Animation.Infinite
            easing.type: Easing.InOutCubic
        }
    }
}
