import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Lumen
import "components"

// The audiobook library: search, add books, and pick one to play.
Item {
    id: root

    readonly property string mode: Library.filter  // all | favorites | recent
    readonly property int modeCount: mode === "favorites" ? Library.favoriteCount
                                     : mode === "recent" ? Library.recentCount : Library.total

    function play(book) {
        if (book.exists === false) {
            App.toast(qsTr("Can't find “%1”. It may have been moved or deleted.").arg(book.title))
            return
        }
        App.openBook(book.path)  // plays it; the window then hands off to the floating player
    }

    onVisibleChanged: if (visible) Library.refresh()

    Shortcut {
        sequences: [StandardKey.Find]
        enabled: root.visible
        onActivated: search.focusInput()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space.xl
        spacing: Theme.space.md

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space.sm

            Txt {
                kind: "title2"
                text: root.mode === "favorites" ? qsTr("Favorites")
                      : root.mode === "recent" ? qsTr("Recently Played") : qsTr("Library")
            }
            Txt {
                Layout.alignment: Qt.AlignBaseline
                kind: "footnote"
                secondary: true
                visible: root.modeCount > 0
                text: root.modeCount === 1 ? qsTr("1 book") : qsTr("%1 books").arg(root.modeCount)
            }
            Item { Layout.fillWidth: true; implicitHeight: Theme.size.controlLarge }
            LButton {
                visible: root.mode === "all"
                iconName: "plus"
                text: qsTr("Add books")
                onClicked: Library.addFilesDialog()
            }
            LButton {
                visible: root.mode === "all"
                iconName: "folder-plus"
                text: qsTr("Add folder")
                onClicked: Library.addFolderDialog()
            }
        }

        LTextField {
            id: search
            objectName: "librarySearch"
            Layout.fillWidth: true
            iconName: "search"
            placeholder: qsTr("Search by title, author or file name")
            visible: root.modeCount > 0
            onTextChanged: Library.setQuery(text)
            onDownPressed: {
                list.forceActiveFocus()
                list.currentIndex = 0
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: Library.importing
            spacing: Theme.space.sm
            LProgressBar { Layout.preferredWidth: Theme.size.cover; value: -1 }
            Txt { kind: "footnote"; secondary: true; text: qsTr("Adding books…") }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: count > 0
            clip: true
            spacing: Theme.space.xxs
            model: Library.books
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationEnabled: true
            Accessible.role: Accessible.List
            Accessible.name: qsTr("Audiobooks")

            ScrollBar.vertical: ScrollBar {
                contentItem: Rectangle {
                    implicitWidth: Theme.space.xxs + 2
                    radius: width / 2
                    color: Theme.c.controlBoundary
                    opacity: parent.active ? 1 : 0.4
                    Behavior on opacity { NumberAnimation { duration: Theme.base } }
                }
            }

            delegate: BookRow {
                required property var modelData
                required property int index
                width: ListView.view.width - Theme.space.sm
                book: modelData
                current: App.hasBook && App.book.path === modelData.path
                showPlayed: root.mode === "recent"
                focus: ListView.isCurrentItem
                onPlayRequested: root.play(modelData)
                onRemoveRequested: Library.remove(modelData.key)
                onFavoriteRequested: Library.toggleFavorite(modelData.key)
                Keys.onReturnPressed: root.play(modelData)
                Keys.onEnterPressed: root.play(modelData)
            }
        }

        // Empty states, centred in the space the list would use
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: list.count === 0 && !Library.importing

            ColumnLayout {
            anchors.centerIn: parent
            width: Math.min(parent.width, Theme.window.main.minWidth - Theme.space.xxxl * 2)
            spacing: Theme.space.md

            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: Theme.size.playButton
                height: width
                radius: width / 2
                color: Theme.c.accentSoft
                Icon {
                    anchors.centerIn: parent
                    name: root.modeCount > 0 ? "search"
                          : root.mode === "favorites" ? "heart"
                          : root.mode === "recent" ? "history" : "library-big"
                    size: Theme.size.iconLg + Theme.space.xs
                    color: Theme.c.accent
                }
            }
            Txt {
                Layout.alignment: Qt.AlignHCenter
                kind: "title3"
                text: root.modeCount > 0 ? qsTr("No books match “%1”").arg(Library.query)
                      : root.mode === "favorites" ? qsTr("No favorites yet")
                      : root.mode === "recent" ? qsTr("Nothing played yet")
                      : qsTr("Your library is empty")
            }
            Txt {
                Layout.alignment: Qt.AlignHCenter
                Layout.maximumWidth: Theme.window.main.minWidth - Theme.space.xxxl * 2
                kind: "body"
                secondary: true
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                text: root.modeCount > 0 ? qsTr("Try a shorter search, or search by author.")
                      : root.mode === "favorites" ? qsTr("Click the heart on a book to keep it here.")
                      : root.mode === "recent" ? qsTr("Books you listen to will appear here, the latest first.")
                      : qsTr("Add audiobooks (MP3, M4A, M4B or WAV), or drop files and folders onto this window.")
            }
            }
        }
    }
}
