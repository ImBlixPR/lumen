import QtQuick
import Lumen

// Single-line text field. Built on TextInput rather than Controls' TextField, whose context
// menu fails to load under PySide6 6.11 (see LanguagePicker); every part is styled here.
Rectangle {
    id: root

    property alias text: input.text
    property string placeholder
    property string iconName: ""  // optional leading icon, e.g. "search"
    signal accepted()
    signal downPressed()

    function focusInput() {
        input.forceActiveFocus()
        input.selectAll()
    }

    implicitHeight: Theme.size.controlLarge
    implicitWidth: Theme.size.cover
    radius: Theme.radius.md
    color: Theme.c.surfaceSunken
    border.width: input.activeFocus ? Theme.size.focusRing : Theme.size.hairline
    border.color: input.activeFocus ? Theme.c.accent : Theme.c.controlBoundary

    Icon {
        visible: root.iconName !== ""
        anchors.left: parent.left
        anchors.leftMargin: Theme.space.sm
        anchors.verticalCenter: parent.verticalCenter
        name: root.iconName
        size: Theme.size.iconSm
        color: Theme.c.textSecondary
    }

    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: root.iconName !== "" ? Theme.space.sm * 2 + Theme.size.iconSm : Theme.space.sm
        anchors.rightMargin: Theme.space.sm
        verticalAlignment: TextInput.AlignVCenter
        color: Theme.c.textPrimary
        selectionColor: Theme.c.accentFill
        selectedTextColor: Theme.c.onAccent
        font.family: Theme.fontFamily
        font.pixelSize: Theme.type.body.size
        selectByMouse: true
        clip: true
        Accessible.role: Accessible.EditableText
        Accessible.name: root.placeholder
        onAccepted: root.accepted()
        Keys.onDownPressed: root.downPressed()

        Txt {
            anchors.fill: parent
            visible: input.text === ""
            kind: "body"
            secondary: true
            text: root.placeholder
        }
    }
}
