import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Lumen
import "components"

// The main window after onboarding: a sidebar with the Library and Now Playing views.
Item {
    id: root
    objectName: "home"

    property string view: "library"  // library | favorites | recent | player

    // Library, Favorites and Recently Played are one list with a different filter.
    onViewChanged: {
        if (view === "favorites") Library.setFilter("favorites")
        else if (view === "recent") Library.setFilter("recent")
        else if (view === "library") Library.setFilter("all")
    }

    Connections {
        target: App
        function onShowLibraryRequested() { root.view = "library" }
        function onShowPlayerRequested() { root.view = "player" }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: false
            Layout.preferredWidth: Theme.size.sidebar
            Layout.maximumWidth: Theme.size.sidebar
            Layout.fillHeight: true
            Layout.margins: Theme.space.md
            spacing: Theme.space.xxs

            RowLayout {
                Layout.leftMargin: Theme.space.xs
                Layout.topMargin: Theme.space.xs
                Layout.bottomMargin: Theme.space.md
                spacing: Theme.space.sm
                Rectangle {
                    width: Theme.size.control
                    height: width
                    radius: width * 0.26
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: Theme.c.accent }
                        GradientStop { position: 1.0; color: Theme.c.accentFill }
                    }
                    Icon {
                        anchors.centerIn: parent
                        name: "captions"
                        size: Theme.size.iconSm + 2
                        color: Theme.c.onAccent
                    }
                }
                Txt { kind: "title3"; text: "Lumen" }
            }

            SidebarItem {
                text: qsTr("Library")
                iconName: "library-big"
                selected: root.view === "library"
                onClicked: root.view = "library"
            }
            SidebarItem {
                text: qsTr("Favorites")
                iconName: "heart"
                badge: String(Library.favoriteCount)
                selected: root.view === "favorites"
                onClicked: root.view = "favorites"
            }
            SidebarItem {
                text: qsTr("Recently Played")
                iconName: "history"
                badge: String(Library.recentCount)
                selected: root.view === "recent"
                onClicked: root.view = "recent"
            }
            SidebarItem {
                text: qsTr("Now Playing")
                iconName: "headphones"
                selected: root.view === "player"
                onClicked: root.view = "player"
            }
            SidebarItem {
                text: qsTr("Settings")
                iconName: "settings"
                onClicked: App.showSettings()
            }
            SidebarItem {
                text: qsTr("Quit Lumen")
                iconName: "power"
                Accessible.role: Accessible.Button
                onClicked: App.quit()
            }

            Item { Layout.fillHeight: true }

            // What's loaded right now, one click from playing.
            GlassPanel {
                Layout.fillWidth: true
                implicitHeight: nowPlaying.implicitHeight + Theme.space.sm * 2
                visible: App.hasBook
                elevated: false

                RowLayout {
                    id: nowPlaying
                    anchors.fill: parent
                    anchors.margins: Theme.space.sm
                    spacing: Theme.space.xs

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Txt { kind: "caption"; secondary: true; text: App.playing ? qsTr("Playing") : qsTr("Paused") }
                        Txt {
                            Layout.fillWidth: true
                            kind: "footnote"
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                            text: App.book.title || ""
                        }
                    }
                    IconButton {
                        iconName: App.playing ? "pause" : "play"
                        iconSize: Theme.size.iconSm
                        implicitWidth: Theme.size.control
                        implicitHeight: Theme.size.control
                        tip: App.playing ? qsTr("Pause") : qsTr("Play")
                        onClicked: App.togglePlay()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: Theme.size.hairline
            color: Theme.c.hairline
        }

        StackLayout {
            id: views
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.view === "player" ? 1 : 0
            onCurrentIndexChanged: reveal.restart()

            LibraryView {}
            Player {}
        }
    }

    NumberAnimation {
        id: reveal
        target: views.children[views.currentIndex] || null
        property: "opacity"
        from: 0
        to: 1
        duration: Theme.base
        easing.type: Easing.OutCubic
    }
}
