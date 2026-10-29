import QtQuick

Canvas {
    id: icon
    property string name: "grid"
    property color ink: Theme.secondary
    implicitWidth: 18
    implicitHeight: 18
    onNameChanged: requestPaint()
    onInkChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    // Original geometric line icons, drawn locally; no downloaded assets or font glyphs.
    onPaint: {
        const c = getContext("2d");
        c.reset();
        c.scale(width / 24, height / 24);
        c.strokeStyle = ink;
        c.lineWidth = 1.6;
        c.lineCap = "round";
        c.lineJoin = "round";
        function line(x1, y1, x2, y2) {
            c.moveTo(x1, y1);
            c.lineTo(x2, y2);
        }
        c.beginPath();
        switch (name) {
        case "drag":
            for (let x of [9, 15]) {
                for (let y of [6, 12, 18]) {
                    c.moveTo(x + 0.8, y);
                    c.arc(x, y, 0.8, 0, 2 * Math.PI);
                }
            }
            break;
        case "left":
            line(14, 6, 8, 12);
            line(8, 12, 14, 18);
            break;
        case "right":
            line(10, 6, 16, 12);
            line(16, 12, 10, 18);
            break;
        case "close":
            line(6, 6, 18, 18);
            line(6, 18, 18, 6);
            break;
        case "plus":
            line(12, 5, 12, 19);
            line(5, 12, 19, 12);
            break;
        case "search":
            c.arc(10, 10, 6, 0, 2 * Math.PI);
            line(15, 15, 21, 21);
            break;
        case "sidebar":
            c.rect(3, 4, 18, 16);
            line(9, 4, 9, 20);
            break;
        case "folder":
            c.moveTo(3, 19);
            c.lineTo(3, 5);
            c.lineTo(9, 5);
            c.lineTo(12, 8);
            c.lineTo(21, 8);
            c.lineTo(21, 19);
            c.closePath();
            break;
        case "calendar":
            c.rect(4, 5, 16, 16);
            line(4, 10, 20, 10);
            line(8, 3, 8, 7);
            line(16, 3, 16, 7);
            line(8, 14, 10, 14);
            line(14, 14, 16, 14);
            break;
        case "chart":
            line(4, 3, 4, 21);
            line(4, 21, 21, 21);
            line(9, 16, 9, 11);
            line(14, 16, 14, 5);
            line(19, 16, 19, 8);
            break;
        case "note":
            c.rect(5, 3, 14, 18);
            line(9, 8, 15, 8);
            line(9, 12, 15, 12);
            line(9, 16, 13, 16);
            break;
        case "settings":
            c.arc(12, 12, 7, 0, 2 * Math.PI);
            c.moveTo(15, 12);
            c.arc(12, 12, 3, 0, 2 * Math.PI);
            line(12, 2, 12, 5);
            line(12, 19, 12, 22);
            line(2, 12, 5, 12);
            line(19, 12, 22, 12);
            break;
        case "download":
            line(12, 3, 12, 15);
            line(8, 11, 12, 15);
            line(12, 15, 16, 11);
            line(4, 16, 4, 21);
            line(4, 21, 20, 21);
            line(20, 21, 20, 16);
            break;
        case "check":
            line(5, 12, 10, 17);
            line(10, 17, 20, 7);
            break;
        case "info":
            c.arc(12, 12, 9, 0, 2 * Math.PI);
            line(12, 11, 12, 17);
            line(12, 7, 12, 7.1);
            break;
        case "sun":
            c.arc(12, 12, 4, 0, 2 * Math.PI);
            line(12, 2, 12, 4);
            line(12, 20, 12, 22);
            line(2, 12, 4, 12);
            line(20, 12, 22, 12);
            line(5, 5, 6, 6);
            line(18, 18, 19, 19);
            break;
        case "week":
            c.rect(3, 5, 18, 15);
            line(3, 10, 21, 10);
            line(9, 10, 9, 20);
            line(15, 10, 15, 20);
            break;
        case "day":
            c.arc(12, 12, 8, 0, 2 * Math.PI);
            line(12, 7, 12, 12);
            line(12, 12, 16, 14);
            break;
        default:
            c.rect(4, 4, 6, 6);
            c.rect(14, 4, 6, 6);
            c.rect(4, 14, 6, 6);
            c.rect(14, 14, 6, 6);
        }
        c.stroke();
    }
}
