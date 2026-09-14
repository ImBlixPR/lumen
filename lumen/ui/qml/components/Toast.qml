import QtQuick
import Lumen

// Transient message capsule at the bottom of a window (errors, hints).
Item {
    id: root

    function show(message) {
        label.text = message
        opacity = 1
        timer.restart()
    }

    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: parent.bottom
    anchors.bottomMargin: Theme.space.lg
    width: Math.min(parent.width - 2 * Theme.space.xl, label.implicitWidth + 2 * Theme.space.lg)
    height: label.height + 2 * Theme.space.sm
    opacity: 0
    visible: opacity > 0
    z: 100
    Accessible.role: Accessible.AlertMessage
    Accessible.name: label.text

    Behavior on opacity { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }

    GlassPanel {
        anchors.fill: parent
        radius: Math.min(height / 2, Theme.radius.xl)
        fill: Theme.c.surfaceStrong
    }
    Txt {
        id: label
        anchors.centerIn: parent
        width: Math.min(implicitWidth, root.parent.width - 2 * Theme.space.xl - 2 * Theme.space.lg)
        kind: "callout"
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
    }
    Timer {
        id: timer
        interval: 4500
        onTriggered: root.opacity = 0
    }
    Connections {
        target: App
        function onToast(message) { root.show(message) }
    }
}
