import QtQuick
import QtQuick.Window
import Lumen
import "components"

// The floating subtitle window. Flags, click-through and always-on-top are managed by
// SubtitleOverlay (Python); this file only draws the pill and the unlock affordances.
Window {
    id: win

    visible: false
    color: "transparent"
    title: qsTr("Lumen subtitles")

    SubtitlePill {
        id: pill

        anchors.horizontalCenter: parent.horizontalCenter
        y: SubtitleOverlay.anchorTop ? Theme.space.xs : win.height - height - Theme.space.xs
        maxWidth: win.width - 2 * Theme.space.xs
        text: SubtitleOverlay.text
        placeholder: SubtitleOverlay.locked ? "" : qsTr("Drag to move · pull the ends to resize · scroll to resize text")
        unlocked: !SubtitleOverlay.locked
        fontSize: Settings.values.overlay_font_size
        textColor: Settings.values.overlay_text_color
        backingOpacity: Settings.values.overlay_backing_opacity
        fontFamily: Theme.familyFor(Settings.values.tgt_lang)
    }

    // Unlocked: drag anywhere on the pill to move; scroll to change the text size.
    MouseArea {
        anchors.fill: pill
        enabled: !SubtitleOverlay.locked
        cursorShape: Qt.SizeAllCursor
        onPressed: SubtitleOverlay.startMove()
        onWheel: (wheel) => {
            const step = wheel.angleDelta.y > 0 ? 2 : -2
            const size = Settings.values.overlay_font_size + step
            Settings.set("overlay_font_size", Math.max(Theme.overlay.minFontSize, Math.min(Theme.overlay.maxFontSize, size)))
        }
    }

    component Grip: MouseArea {
        width: Theme.space.md
        height: pill.height
        y: pill.y
        visible: !SubtitleOverlay.locked
        cursorShape: Qt.SizeHorCursor

        Rectangle {
            anchors.centerIn: parent
            width: Theme.space.xxs
            height: parent.height * 0.4
            radius: width / 2
            color: Theme.overlay.unlockedBorder
        }
    }
    Grip {
        x: pill.x
        onPressed: SubtitleOverlay.startResize(Qt.LeftEdge)
    }
    Grip {
        x: pill.x + pill.width - width
        onPressed: SubtitleOverlay.startResize(Qt.RightEdge)
    }
}
