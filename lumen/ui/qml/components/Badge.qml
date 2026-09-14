import QtQuick
import Lumen

// Small filled label ("Recommended", "GPU"). Accent fill + onAccent text passes AA in both themes.
Rectangle {
    id: root

    property alias text: label.text
    property string iconName

    implicitWidth: row.implicitWidth + Theme.space.xs * 2
    implicitHeight: label.implicitHeight + Theme.space.xxs
    radius: height / 2
    color: Theme.c.accentFill

    Row {
        id: row
        anchors.centerIn: parent
        spacing: Theme.space.xxs

        Icon {
            visible: root.iconName !== ""
            anchors.verticalCenter: parent.verticalCenter
            name: root.iconName
            size: Theme.size.iconSm - 4
            color: Theme.c.onAccent
        }
        Txt {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            kind: "caption"
            font.weight: Font.DemiBold
            color: Theme.c.onAccent
        }
    }
}
