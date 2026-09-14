import QtQuick
import QtQuick.Controls.Basic
import Lumen

// Shows a global shortcut as keycaps; click, then press a new combination to rebind.
// Esc cancels, Backspace clears. Global hotkeys are suspended while recording.
AbstractButton {
    id: control

    property string hotkeyAction            // "play_pause", "back_sentence", …
    readonly property string settingKey: "hotkey_" + hotkeyAction
    readonly property string sequence: Settings.values[settingKey] || ""
    readonly property string error: App.hotkeyErrors[hotkeyAction] || ""
    property bool recording: false

    function start() {
        recording = true
        App.suspendHotkeys()
        forceActiveFocus()
    }
    function stop(newSequence) {
        if (!recording) return
        recording = false
        if (newSequence !== undefined)
            Settings.set(settingKey, newSequence)
        App.resumeHotkeys()
    }
    function keyName(key) {
        if (key >= Qt.Key_A && key <= Qt.Key_Z) return String.fromCharCode(key)
        if (key >= Qt.Key_0 && key <= Qt.Key_9) return String.fromCharCode(key)
        if (key >= Qt.Key_F1 && key <= Qt.Key_F24) return "F" + (key - Qt.Key_F1 + 1)
        switch (key) {
        case Qt.Key_Space: return "Space"
        case Qt.Key_Left: return "Left"
        case Qt.Key_Right: return "Right"
        case Qt.Key_Up: return "Up"
        case Qt.Key_Down: return "Down"
        case Qt.Key_Home: return "Home"
        case Qt.Key_End: return "End"
        case Qt.Key_PageUp: return "PgUp"
        case Qt.Key_PageDown: return "PgDown"
        case Qt.Key_Insert: return "Ins"
        case Qt.Key_Comma: return ","
        case Qt.Key_Period: return "."
        case Qt.Key_Slash: return "/"
        case Qt.Key_Semicolon: return ";"
        case Qt.Key_BracketLeft: return "["
        case Qt.Key_BracketRight: return "]"
        case Qt.Key_Minus: return "-"
        case Qt.Key_Equal: return "="
        case Qt.Key_MediaTogglePlayPause:
        case Qt.Key_MediaPlay: return "Media Play"
        case Qt.Key_MediaPrevious: return "Media Previous"
        case Qt.Key_MediaNext: return "Media Next"
        }
        return ""
    }

    implicitHeight: Theme.size.control + Theme.space.xxs
    implicitWidth: Math.max(Theme.size.cover * 0.8, caps.implicitWidth + Theme.space.md * 2)
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.Button
    Accessible.name: recording ? qsTr("Press a new shortcut") : qsTr("Shortcut %1. Activate to change.").arg(sequence || qsTr("not set"))

    onClicked: recording ? stop() : start()
    onActiveFocusChanged: if (!activeFocus) stop()

    Keys.onPressed: (event) => {
        if (!recording)
            return
        event.accepted = true
        if (event.key === Qt.Key_Escape) { stop(); return }
        if (event.key === Qt.Key_Backspace || event.key === Qt.Key_Delete) { stop(""); return }
        const key = keyName(event.key)
        if (key === "")
            return  // a lone modifier: keep waiting for the real key
        const parts = []
        if (event.modifiers & Qt.ControlModifier) parts.push("Ctrl")
        if (event.modifiers & Qt.AltModifier) parts.push("Alt")
        if (event.modifiers & Qt.ShiftModifier) parts.push("Shift")
        if (event.modifiers & Qt.MetaModifier) parts.push("Meta")
        const standalone = /^F\d+$/.test(key) || key.indexOf("Media") === 0
        if (parts.length === 0 && !standalone)
            return  // plain letters would swallow normal typing system-wide
        parts.push(key)
        stop(parts.join("+"))
    }

    background: Rectangle {
        radius: Theme.radius.md
        color: control.recording ? Theme.c.accentSoft : control.hovered ? Theme.c.surfaceStrong : Theme.c.surface
        border.width: control.recording || control.error ? Theme.size.focusRing : Theme.size.hairline
        border.color: control.error ? Theme.c.danger : control.recording ? Theme.c.accent : Theme.c.controlBoundary
        Behavior on color { ColorAnimation { duration: Theme.fast } }

        FocusRing {
            show: control.visualFocus && !control.recording
            ringRadius: parent.radius
        }
    }

    contentItem: Item {
        Row {
            id: caps
            anchors.centerIn: parent
            spacing: Theme.space.xxs
            visible: !control.recording && control.sequence !== ""

            Repeater {
                model: control.sequence.split("+").filter(part => part !== "")
                Rectangle {
                    implicitWidth: Math.max(height, keyLabel.implicitWidth + Theme.space.xs * 2)
                    height: Theme.size.control - Theme.space.xxs * 2
                    radius: Theme.radius.sm
                    color: Theme.c.bgElevated
                    border.width: Theme.size.hairline
                    border.color: Theme.c.controlBoundary

                    Txt {
                        id: keyLabel
                        anchors.centerIn: parent
                        kind: "footnote"
                        font.weight: Font.Medium
                        text: modelData
                    }
                }
            }
        }
        Txt {
            anchors.centerIn: parent
            visible: control.recording || control.sequence === ""
            kind: "footnote"
            secondary: !control.recording
            color: control.recording ? Theme.c.accent : Theme.c.textSecondary
            text: control.recording ? qsTr("Press a shortcut…") : qsTr("Not set")
        }
    }
}
