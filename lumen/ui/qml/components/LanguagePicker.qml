import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import QtQuick.Layouts
import Lumen

// Field that opens a searchable language list. Shows the endonym first ("Español · Spanish").
AbstractButton {
    id: control

    property string value
    property string exclude: ""
    property string caption
    signal picked(string code)

    function find(code) {
        const all = App.languages
        for (let i = 0; i < all.length; ++i)
            if (all[i].code === code) return all[i]
        return null
    }
    readonly property var current: find(value)

    implicitHeight: Theme.size.field
    implicitWidth: Theme.size.cover * 1.5
    leftPadding: Theme.space.md
    rightPadding: Theme.space.sm
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.ComboBox
    Accessible.name: caption + ": " + (current ? current.name : "")
    onClicked: popup.open()

    background: Rectangle {
        radius: Theme.radius.md
        color: control.hovered ? Theme.c.surfaceStrong : Theme.c.surface
        border.width: popup.visible ? Theme.size.focusRing : Theme.size.hairline
        border.color: popup.visible ? Theme.c.accent : Theme.c.controlBoundary
        Behavior on color { ColorAnimation { duration: Theme.fast } }

        FocusRing {
            show: control.visualFocus
            ringRadius: parent.radius
        }
    }

    contentItem: RowLayout {
        spacing: Theme.space.sm

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0

            Txt {
                kind: "caption"
                secondary: true
                text: control.caption
            }
            Txt {
                Layout.fillWidth: true
                kind: "headline"
                elide: Text.ElideRight
                text: !control.current ? qsTr("Choose…")
                      : control.current.native === control.current.name ? control.current.name
                      : control.current.native + "  ·  " + control.current.name
            }
        }
        Icon {
            name: "chevron-down"
            size: Theme.size.iconSm
            color: Theme.c.textSecondary
            rotation: popup.visible ? 180 : 0
            Behavior on rotation { NumberAnimation { duration: Theme.base; easing.type: Easing.OutCubic } }
        }
    }

    Popup {
        id: popup

        property string query: ""
        readonly property var results: App.languages.filter(l =>
            l.code !== control.exclude
            && (query === "" || l.name.toLowerCase().indexOf(query) >= 0
                || l.native.toLowerCase().indexOf(query) >= 0 || l.code === query))

        y: control.height + Theme.space.xxs
        width: control.width
        height: Theme.size.popupHeight
        padding: Theme.space.xs
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

        onOpened: {
            search.text = ""
            search.forceActiveFocus()
            for (let i = 0; i < results.length; ++i)
                if (results[i].code === control.value) list.currentIndex = i
            list.positionViewAtIndex(list.currentIndex, ListView.Center)
        }

        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.fast }
                NumberAnimation { property: "scale"; from: 0.97; to: 1; duration: Theme.fast; easing.type: Easing.OutCubic }
            }
        }
        exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.fast } }

        background: Item {
            RectangularShadow {
                anchors.fill: sheet
                radius: sheet.radius
                offset: Qt.vector2d(Theme.shadow.lg.x, Theme.shadow.lg.y)
                blur: Theme.shadow.lg.blur
                spread: Theme.shadow.lg.spread
                color: Theme.c.shadow
            }
            Rectangle {
                id: sheet
                anchors.fill: parent
                radius: Theme.radius.lg
                color: Theme.c.bgElevated
                border.width: Theme.size.hairline
                border.color: Theme.c.hairline
            }
        }

        contentItem: ColumnLayout {
            spacing: Theme.space.xs

            // Search field built on TextInput: Qt 6.11's Basic TextField fails to load its
            // context menu under PySide6, and every part of it is custom-styled here anyway.
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: Theme.size.controlLarge
                radius: Theme.radius.md
                color: Theme.c.surfaceSunken
                border.width: search.activeFocus ? Theme.size.focusRing : Theme.size.hairline
                border.color: search.activeFocus ? Theme.c.accent : Theme.c.controlBoundary

                Icon {
                    id: searchIcon
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.space.sm
                    anchors.verticalCenter: parent.verticalCenter
                    name: "search"
                    size: Theme.size.iconSm
                    color: Theme.c.textSecondary
                }
                TextInput {
                    id: search
                    anchors.left: searchIcon.right
                    anchors.right: parent.right
                    anchors.leftMargin: Theme.space.xs
                    anchors.rightMargin: Theme.space.sm
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.c.textPrimary
                    selectionColor: Theme.c.accentFill
                    selectedTextColor: Theme.c.onAccent
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.type.body.size
                    selectByMouse: true
                    clip: true
                    Accessible.role: Accessible.EditableText
                    Accessible.name: qsTr("Search languages")
                    onTextChanged: {
                        popup.query = text.trim().toLowerCase()
                        list.currentIndex = 0
                    }
                    Keys.onDownPressed: list.incrementCurrentIndex()
                    Keys.onUpPressed: list.decrementCurrentIndex()
                    Keys.onReturnPressed: list.choose(list.currentIndex)
                    Keys.onEnterPressed: list.choose(list.currentIndex)

                    Txt {
                        anchors.fill: parent
                        visible: search.text === ""
                        kind: "body"
                        secondary: true
                        text: qsTr("Search languages")
                    }
                }
            }

            ListView {
                id: list

                function choose(i) {
                    if (i >= 0 && i < popup.results.length) {
                        control.picked(popup.results[i].code)
                        popup.close()
                    }
                }

                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: popup.results
                boundsBehavior: Flickable.StopAtBounds
                keyNavigationWraps: true

                ScrollIndicator.vertical: ScrollIndicator {
                    contentItem: Rectangle {
                        implicitWidth: Theme.space.xxs - 1
                        radius: width / 2
                        color: Theme.c.controlBoundary
                    }
                }

                delegate: AbstractButton {
                    id: row
                    required property var modelData
                    required property int index

                    width: ListView.view.width
                    implicitHeight: Theme.size.controlLarge
                    leftPadding: Theme.space.sm
                    rightPadding: Theme.space.sm
                    hoverEnabled: true
                    Accessible.role: Accessible.ListItem
                    Accessible.name: modelData.name
                    onClicked: list.choose(index)
                    onHoveredChanged: if (hovered) list.currentIndex = index

                    background: Rectangle {
                        radius: Theme.radius.sm
                        color: row.ListView.isCurrentItem ? Theme.c.accentSoft : "transparent"
                    }
                    contentItem: RowLayout {
                        spacing: Theme.space.sm

                        Txt {
                            kind: "body"
                            text: row.modelData.native
                            font.family: Theme.familyFor(row.modelData.code)
                        }
                        Txt {
                            Layout.fillWidth: true
                            kind: "body"
                            secondary: true
                            elide: Text.ElideRight
                            visible: row.modelData.name !== row.modelData.native
                            text: row.modelData.name
                        }
                        Item {
                            Layout.fillWidth: true
                            visible: row.modelData.name === row.modelData.native
                        }
                        Icon {
                            visible: row.modelData.code === control.value
                            name: "check"
                            size: Theme.size.iconSm
                            color: Theme.c.accent
                        }
                    }
                }
            }

            Txt {
                visible: popup.results.length === 0
                Layout.alignment: Qt.AlignHCenter
                Layout.bottomMargin: Theme.space.md
                kind: "footnote"
                secondary: true
                text: qsTr("No matching language")
            }
        }
    }
}
