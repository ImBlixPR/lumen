import QtQuick
import Lumen

// The subtitle "pill": a tinted glass backing that keeps text readable over anything,
// from a white web page to a dark film. Shared by the overlay and the Settings preview.
//
// Sentence changes crossfade between two text layers. The new text starts appearing on
// the very frame it becomes current, so the animation never delays subtitle timing.
Item {
    id: root

    property string text
    property string placeholder: ""
    property real maxWidth: Theme.window.main.width
    property int fontSize: Theme.type.overlay.size
    property color textColor: Theme.overlay.text
    property real backingOpacity: Theme.overlay.backingOpacity
    property string fontFamily: Theme.fontFamily
    property bool unlocked: false
    property int maxLines: 3

    readonly property string display: text !== "" ? text : placeholder
    readonly property bool hasContent: display !== ""
    readonly property real padH: Theme.space.lg
    readonly property real padV: Theme.space.sm
    readonly property real lineHeight: Math.round(fontSize * Theme.type.overlay.line / Theme.type.overlay.size)
    readonly property real cornerRadius: Math.min(height / 2, Theme.radius.xl * 1.5)
    property int front: 0  // which text layer holds the current sentence
    readonly property Text current: front === 0 ? textA : textB

    implicitWidth: unlocked ? maxWidth : Math.min(maxWidth, Math.ceil(current.contentWidth) + 2 * padH)
    implicitHeight: Math.max(lineHeight, Math.ceil(current.contentHeight)) + 2 * padV
    width: implicitWidth
    height: implicitHeight
    opacity: hasContent ? 1 : 0

    Behavior on opacity { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }
    Behavior on width {
        enabled: root.opacity > 0.05
        NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic }
    }
    Behavior on height {
        enabled: root.opacity > 0.05
        NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic }
    }

    onDisplayChanged: {
        if (display === "")
            return  // keep the last text while the pill fades out
        if (front === 0) {
            textB.text = display
            front = 1
        } else {
            textA.text = display
            front = 0
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.cornerRadius
        color: Theme.overlay.backing
        opacity: root.backingOpacity
    }
    Rectangle {
        anchors.fill: parent
        radius: root.cornerRadius
        color: "transparent"
        border.width: root.unlocked ? Theme.size.focusRing : Theme.size.hairline
        border.color: root.unlocked ? Theme.overlay.unlockedBorder : Theme.overlay.border
    }

    component SubtitleText: Text {
        anchors.centerIn: parent
        width: root.maxWidth - 2 * root.padH
        wrapMode: Text.Wrap
        maximumLineCount: root.maxLines
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        textFormat: Text.PlainText
        color: root.textColor
        font.family: root.fontFamily
        font.pixelSize: root.fontSize
        font.weight: Theme.type.overlay.weight
        lineHeightMode: Text.FixedHeight
        lineHeight: root.lineHeight
        Behavior on opacity { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }
    }

    SubtitleText {
        id: textA
        opacity: root.front === 0 ? 1 : 0
    }
    SubtitleText {
        id: textB
        opacity: root.front === 1 ? 1 : 0
    }
}
