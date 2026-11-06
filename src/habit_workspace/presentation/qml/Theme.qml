pragma Singleton
import QtQuick

QtObject {
    property bool dark: true
    property bool reducedMotion: false
    readonly property int duration: reducedMotion ? 0 : 140
    readonly property color canvas: dark ? "#22252D" : "#FAFAFB"
    readonly property color sidebar: dark ? "#282C35" : "#F2F3F6"
    readonly property color surface: dark ? "#303540" : "#FFFFFF"
    readonly property color hover: dark ? "#3A414E" : "#E9EBF2"
    readonly property color border: dark ? "#474F5E" : "#DEE1E7"
    readonly property color text: dark ? "#F2F3F5" : "#171A21"
    readonly property color secondary: dark ? "#C0C6D1" : "#596271"
    readonly property color muted: dark ? "#ADB6C5" : "#646D7B"
    readonly property color accent: dark ? "#A0A6FF" : "#565DD7"
    readonly property color accentSurface: dark ? "#3D4262" : "#EDEDFC"
    readonly property color primaryFill: dark ? "#8C93F8" : "#565DD7"
    readonly property color onPrimary: dark ? "#22252D" : "#FFFFFF"
    readonly property color warning: dark ? "#E1AD69" : "#855316"
    readonly property color success: dark ? "#75C6A3" : "#23764F"
    readonly property color error: dark ? "#EA9399" : "#B02F43"
}
