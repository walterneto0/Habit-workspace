pragma Singleton
import QtQuick

QtObject {
    property bool dark: true
    property bool reducedMotion: false
    readonly property int duration: reducedMotion ? 0 : 140
    readonly property color canvas: dark ? "#101116" : "#FAFAFB"
    readonly property color sidebar: dark ? "#14161C" : "#F2F3F6"
    readonly property color surface: dark ? "#1A1D25" : "#FFFFFF"
    readonly property color hover: dark ? "#242832" : "#E9EBF2"
    readonly property color border: dark ? "#30343D" : "#DEE1E7"
    readonly property color text: dark ? "#F2F3F5" : "#171A21"
    readonly property color secondary: dark ? "#A7ADB8" : "#596271"
    readonly property color muted: dark ? "#969EAC" : "#646D7B"
    readonly property color accent: dark ? "#A0A6FF" : "#565DD7"
    readonly property color accentSurface: dark ? "#292B45" : "#EDEDFC"
    readonly property color primaryFill: dark ? "#8C93F8" : "#565DD7"
    readonly property color onPrimary: dark ? "#101116" : "#FFFFFF"
    readonly property color warning: dark ? "#E1AD69" : "#855316"
    readonly property color success: dark ? "#75C6A3" : "#23764F"
    readonly property color error: dark ? "#EA9399" : "#B02F43"
}
