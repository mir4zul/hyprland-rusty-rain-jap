pragma ComponentBehavior: Bound

import QtQuick

Item {
    id: root

    property bool active: false
    property bool inputEnabled: false
    // rusty-rain 0.3.4: -c jap -C green -H white -s
    property string characters: "ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ"
    property int cellSize: 20
    property color rainColor: "#00ff00"
    property var streams: []
    property point mouseOrigin: Qt.point(-1, -1)

    signal dismissed

    visible: active
    clip: true
    z: 1000

    function start() {
        streams = [];
        mouseOrigin = Qt.point(-1, -1);
        inputEnabled = false;
        active = true;
        inputDelay.restart();
        canvas.requestPaint();
    }

    function dismiss() {
        if (!active)
            return;
        active = false;
        inputDelay.stop();
        inputEnabled = false;
        streams = [];
        dismissed();
    }

    Rectangle {
        anchors.fill: parent
        color: "black"
    }

    Canvas {
        id: canvas

        anchors.fill: parent
        onWidthChanged: root.streams = []
        onHeightChanged: root.streams = []

        onPaint: {
            if (!root.active || width <= 0 || height <= 0)
                return;
            const ctx = getContext("2d");
            const size = root.cellSize;
            const columns = Math.ceil(width / size);
            const rows = Math.ceil(height / size);
            if (root.streams.length !== columns) {
                const next = [];
                for (let c = 0; c < columns; c++) {
                    next.push({ head: 0, speed: 33 / (40 + Math.random() * 160),
                        length: 4 + Math.floor(Math.random() * Math.max(1, rows - 14)), seed: Math.floor(Math.random() * 10000) });
                }
                root.streams = next;
            }
            ctx.fillStyle = "black";
            ctx.fillRect(0, 0, width, height);
            ctx.font = (size - 3) + "px monospace";
            ctx.textBaseline = "top";
            for (let c = 0; c < columns; c++) {
                const stream = root.streams[c];
                stream.head += stream.speed;
                if (stream.head - stream.length > rows) {
                    stream.head = -Math.random() * 12;
                    stream.seed = Math.floor(Math.random() * 10000);
                }
                const head = Math.floor(stream.head);
                for (let t = 0; t < stream.length; t++) {
                    const row = head - t;
                    if (row < 0 || row > rows)
                        continue;
                    const value = Math.abs(Math.sin(stream.seed + row * 127.1) * 43758.5453);
                    const glyph = root.characters.charAt(Math.floor(value) % root.characters.length);
                    ctx.globalAlpha = t === 0 ? 1 : 1 - t / stream.length;
                    ctx.fillStyle = t === 0 ? "#ffffff" : root.rainColor;
                    ctx.fillText(glyph, c * size + 2, row * size);
                }
            }
            ctx.globalAlpha = 1;
        }
    }

    Timer {
        interval: 33
        repeat: true
        running: root.active && root.visible
        onTriggered: canvas.requestPaint()
    }

    Timer {
        id: inputDelay

        interval: 500
        onTriggered: root.inputEnabled = true
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.active
        hoverEnabled: true
        cursorShape: Qt.BlankCursor
        onPressed: if (root.inputEnabled) root.dismiss()
        onWheel: if (root.inputEnabled) root.dismiss()
        onPositionChanged: mouse => {
            if (!root.inputEnabled)
                return;
            if (root.mouseOrigin.x < 0) {
                root.mouseOrigin = Qt.point(mouse.x, mouse.y);
                return;
            }
            if (Math.abs(mouse.x - root.mouseOrigin.x) + Math.abs(mouse.y - root.mouseOrigin.y) > 8)
                root.dismiss();
        }
    }
}
