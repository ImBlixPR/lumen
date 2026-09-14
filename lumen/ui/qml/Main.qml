import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import Lumen
import "components"

// The player window: first-run onboarding, then the player. Closing it quits Lumen, or
// keeps it in the tray when the "close_to_tray" setting is on.
Window {
    id: root

    property bool backdrop: false

    width: Theme.window.main.width
    height: Theme.window.main.height
    minimumWidth: Theme.window.main.minWidth
    minimumHeight: Theme.window.main.minHeight
    visible: true
    title: App.hasBook ? App.book.title + " — Lumen" : "Lumen"
    color: backdrop ? "transparent" : Theme.c.bg

    Component.onCompleted: backdrop = App.registerWindow(root)

    // Called by the floating player: the library fades away when playback starts from it,
    // and fades back when the floating player's library button is pressed.
    function hideToFloating() {
        if (visible && !hideAnimation.running)
            hideAnimation.restart()
    }
    function showFromFloating() {
        hideAnimation.stop()
        if (!visible)
            opacity = 0
        show()
        raise()
        requestActivate()
        showAnimation.restart()
    }
    NumberAnimation {
        id: hideAnimation
        target: root
        property: "opacity"
        to: 0
        duration: Theme.slow
        easing.type: Easing.InCubic
        onFinished: {
            root.hide()
            root.opacity = 1
        }
    }
    NumberAnimation {
        id: showAnimation
        target: root
        property: "opacity"
        to: 1
        duration: Theme.slow
        easing.type: Easing.OutCubic
    }
    onClosing: (close) => {
        close.accepted = false
        if (Settings.values.close_to_tray)
            root.hide()
        else
            App.quit()
    }

    // A light wash over the OS material keeps text contrast predictable on any wallpaper.
    Rectangle {
        anchors.fill: parent
        color: Theme.c.bg
        opacity: root.backdrop ? 0.45 : 1
        Behavior on color { ColorAnimation { duration: Theme.base } }
    }

    Loader {
        id: screen
        anchors.fill: parent
        sourceComponent: Settings.values.onboarded ? playerScreen : onboardingScreen
        onLoaded: reveal.restart()
    }
    NumberAnimation {
        id: reveal
        target: screen.item
        property: "opacity"
        from: 0
        to: 1
        duration: Theme.slow
        easing.type: Easing.OutCubic
    }
    Component {
        id: onboardingScreen
        Onboarding {}
    }
    Component {
        id: playerScreen
        Home {}  // library + now playing
    }

    SettingsWindow {
        id: settingsWindow
    }

    Toast {}

    DropArea {
        anchors.fill: parent
        enabled: Settings.values.onboarded
        onDropped: (drop) => {
            if (!drop.hasUrls || drop.urls.length === 0)
                return
            if (drop.urls.length === 1) {
                App.openBook(drop.urls[0].toString())  // one file plays; a folder gets added
                return
            }
            const files = []
            for (let i = 0; i < drop.urls.length; ++i)
                files.push(drop.urls[i].toString())
            Library.addFiles(files)  // several files: add them all to the library
        }
    }

    Shortcut {
        sequence: "Space"
        enabled: Settings.values.onboarded && App.hasBook
        onActivated: App.togglePlay()
    }
    Shortcut {
        sequence: "Left"
        enabled: App.hasBook
        onActivated: App.skip(-15)
    }
    Shortcut {
        sequence: "Right"
        enabled: App.hasBook
        onActivated: App.skip(15)
    }
    Shortcut {
        sequence: "Shift+Left"
        enabled: App.hasBook
        onActivated: App.backSentence()
    }
    Shortcut {
        sequences: [StandardKey.Open]
        enabled: Settings.values.onboarded
        onActivated: App.openBookDialog()
    }
    Shortcut {
        sequence: "Ctrl+,"
        onActivated: settingsWindow.openAt("")
    }
    Shortcut {
        sequence: "Ctrl+Q"
        context: Qt.ApplicationShortcut
        onActivated: App.quit()
    }

    Connections {
        target: App
        function onShowPlayerRequested() {
            root.showFromFloating()
        }
        function onShowLibraryRequested() {
            root.showFromFloating()
        }
        function onShowSettingsRequested(section) {
            settingsWindow.openAt(section)
        }
    }
}
