import QtQuick
import QtQuick.Window

Window {
    id: window
    width: 1000
    height: 650
    visible: true
    title: "Live Japanese Rain — press a key to close"
    color: "black"
    LiveRain {
        id: rain
        anchors.fill: parent
        focus: true
        Keys.onPressed: event => { event.accepted = true; rain.dismiss(); }
        onDismissed: if (!Qt.application.arguments.includes("--test")) Qt.quit()
        Component.onCompleted: start()
    }
    Timer {
        interval: 1200
        running: Qt.application.arguments.includes("--test")
        onTriggered: {
            if (!rain.active || !rain.inputEnabled || rain.streams.length === 0)
                throw new Error("Rain failed to start");
            rain.dismiss();
            if (rain.active || rain.inputEnabled || rain.streams.length !== 0)
                throw new Error("Rain failed to dismiss");
            rain.start();
            if (!rain.active || rain.inputEnabled)
                throw new Error("Rain failed to restart");
            console.log("PASS: render, dismiss, restart");
            Qt.quit();
        }
    }
}
