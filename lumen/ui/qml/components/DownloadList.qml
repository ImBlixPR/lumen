import QtQuick
import QtQuick.Layouts
import Lumen

// Per-model download progress rows (onboarding and Settings → Models).
ColumnLayout {
    id: root

    property var items: []

    function sizeText(mb) { return mb >= 1000 ? (mb / 1000).toFixed(1) + " GB" : Math.round(mb) + " MB" }

    spacing: Theme.space.lg

    Repeater {
        model: root.items

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.space.xs

            RowLayout {
                Layout.fillWidth: true
                Txt {
                    Layout.fillWidth: true
                    kind: "headline"
                    text: modelData.label
                }
                Icon {
                    visible: modelData.state === "done" || modelData.state === "failed"
                    name: modelData.state === "done" ? "circle-check" : "triangle-alert"
                    size: Theme.size.iconSm + 2
                    color: modelData.state === "done" ? Theme.c.success : Theme.c.danger
                }
            }
            LProgressBar {
                Layout.fillWidth: true
                value: modelData.state === "waiting" ? 0 : modelData.done / Math.max(1, modelData.total)
            }
            Txt {
                kind: "footnote"
                secondary: true
                font.features: { "tnum": 1 }
                text: modelData.state === "done" ? qsTr("Installed")
                      : modelData.state === "failed" ? qsTr("Download failed. Check your connection and try again.")
                      : modelData.state === "waiting" ? qsTr("Waiting…")
                      : qsTr("%1 of %2 · %3 MB/s")
                            .arg(root.sizeText(modelData.done / 1e6))
                            .arg(root.sizeText(modelData.total / 1e6))
                            .arg((modelData.rate / 1e6).toFixed(1))
            }
        }
    }
}
