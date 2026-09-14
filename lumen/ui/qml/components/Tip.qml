import QtQuick
import QtQuick.Controls.Basic
import Lumen

// Tooltip in the design system (never the default grey box).
ToolTip {
    id: tip

    delay: 600
    timeout: 5000
    topPadding: Theme.space.xxs + 2
    bottomPadding: Theme.space.xxs + 2
    leftPadding: Theme.space.sm
    rightPadding: Theme.space.sm

    contentItem: Txt {
        kind: "footnote"
        text: tip.text
    }
    background: Rectangle {
        radius: Theme.radius.sm
        color: Theme.c.surfaceStrong
        border.width: Theme.size.hairline
        border.color: Theme.c.hairline
    }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.fast } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.fast } }
}
