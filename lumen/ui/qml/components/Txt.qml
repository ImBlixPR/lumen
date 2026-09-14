import QtQuick
import Lumen

// Text in the type scale. `kind` selects a Theme.type token (caption … title1).
Text {
    id: root

    property string kind: "body"
    property bool secondary: false
    readonly property var spec: Theme.type[kind]

    font.family: (kind === "title1" || kind === "title2") ? Theme.displayFamily : Theme.fontFamily
    font.pixelSize: spec.size
    font.weight: spec.weight
    lineHeightMode: Text.FixedHeight
    lineHeight: spec.line
    verticalAlignment: Text.AlignVCenter
    color: secondary ? Theme.c.textSecondary : Theme.c.textPrimary
    textFormat: Text.PlainText
    renderType: Text.NativeRendering

    Behavior on color { ColorAnimation { duration: Theme.base } }
}
