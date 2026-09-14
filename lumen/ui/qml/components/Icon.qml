import QtQuick
import QtQuick.Window
import Lumen

// A Lucide icon, tinted and rasterised at device resolution by the Python icon provider.
Image {
    id: root

    property string name
    property color color: Theme.c.textPrimary
    property int size: Theme.size.icon
    property real stroke: 2

    width: size
    height: size
    sourceSize.width: Math.ceil(size * Screen.devicePixelRatio)
    sourceSize.height: Math.ceil(size * Screen.devicePixelRatio)
    source: name ? "image://icon/" + name + "/" + encodeURIComponent(String(color)) + "/" + stroke : ""
    fillMode: Image.PreserveAspectFit
    smooth: true
    Accessible.ignored: true
}
