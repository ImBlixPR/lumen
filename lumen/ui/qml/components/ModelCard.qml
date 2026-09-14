import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Lumen

// Selectable model option with speed / accuracy meters (radio semantics).
// The meter row is a Flow so narrow cards (three across in onboarding) wrap, never overflow.
AbstractButton {
    id: card

    property var info: ({})       // {id, label, sizeMb, speed, accuracy, note, installed}
    property bool selected: false
    property bool recommended: false

    implicitWidth: Theme.size.cover
    implicitHeight: column.implicitHeight + Theme.space.md * 2
    padding: Theme.space.md
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.RadioButton
    Accessible.name: info.label + ". " + info.note
    Accessible.checked: selected

    background: Rectangle {
        radius: Theme.radius.lg
        color: card.selected ? Theme.c.accentSoft : card.hovered ? Theme.c.surfaceStrong : Theme.c.surface
        border.width: card.selected ? Theme.size.focusRing : Theme.size.hairline
        border.color: card.selected ? Theme.c.accent : Theme.c.hairline
        Behavior on color { ColorAnimation { duration: Theme.fast } }

        FocusRing {
            show: card.visualFocus
            ringRadius: parent.radius
        }
    }

    component Meter: Row {
        property string label
        property int value
        spacing: Theme.space.xxs

        Txt {
            kind: "caption"
            secondary: true
            text: parent.label
            anchors.verticalCenter: parent.verticalCenter
        }
        Repeater {
            model: 5
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: Theme.space.xs - 2
                height: width
                radius: width / 2
                color: index < parent.value ? Theme.c.accent : "transparent"
                border.width: Theme.size.hairline
                border.color: index < parent.value ? Theme.c.accent : Theme.c.controlBoundary
            }
        }
    }

    contentItem: ColumnLayout {
        id: column
        spacing: Theme.space.xs

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space.xs

            Txt {
                Layout.fillWidth: true
                kind: "headline"
                elide: Text.ElideRight
                text: card.info.label || ""
            }
            Badge {
                visible: card.recommended
                text: qsTr("Recommended")
            }
        }
        Txt {
            Layout.fillWidth: true
            kind: "footnote"
            secondary: true
            wrapMode: Text.WordWrap
            text: card.info.note || ""
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space.sm

            Meter { label: qsTr("Speed"); value: card.info.speed || 0 }
            Meter { label: qsTr("Accuracy"); value: card.info.accuracy || 0 }
            Row {
                spacing: Theme.space.xxs
                Icon {
                    visible: card.info.installed === true
                    anchors.verticalCenter: parent.verticalCenter
                    name: "check"
                    size: Theme.size.iconSm - 2
                    color: Theme.c.success
                }
                Txt {
                    kind: "caption"
                    secondary: true
                    text: card.info.installed ? qsTr("Installed")
                          : card.info.sizeMb >= 1000 ? (card.info.sizeMb / 1000).toFixed(1) + " GB"
                          : card.info.sizeMb + " MB"
                }
            }
        }
    }
}
