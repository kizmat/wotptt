# Toggle Platoon PTT

A lightweight World of Tanks mod that changes platoon voice chat Push-to-Talk into a toggle.

Instead of holding the Push-to-Talk key while speaking:

- Press once to turn the microphone ON
- Press again to turn the microphone OFF

The mod automatically uses the Push-to-Talk key configured in World of Tanks.

## Features

- Uses your existing World of Tanks Push-to-Talk key
- No additional hotkey required
- Works while you are in a platoon
- First press toggles the microphone ON
- Second press toggles the microphone OFF
- Microphone stays open after releasing the PTT key
- `PLATOON MIC: ON` appears for 3 seconds
- `PLATOON MIC: OFF` appears for 3 seconds
- Leaving or disbanding the platoon automatically turns the microphone OFF
- Voice channel reconnects restore the active toggle state
- Outside a platoon, normal World of Tanks Push-to-Talk behavior is preserved

## Installation

### Recommended: `.wotmod`

Download:

    panda.toggle_ptt_1.3.0.wotmod

Copy it to:

    World of Tanks/
    └── mods/
        └── <game-version>/
            └── panda.toggle_ptt_1.3.0.wotmod

For example:

    World of Tanks/
    └── mods/
        └── 2.4.0.0/
            └── panda.toggle_ptt_1.3.0.wotmod

Restart World of Tanks after installing the mod.

## Usage

1. Enable voice chat in World of Tanks.
2. Configure your normal Push-to-Talk key in the WoT settings.
3. Create or join a platoon.
4. Press your normal Push-to-Talk key once.

The game will display:

    PLATOON MIC: ON

Your microphone will remain active after releasing the key.

Press the same key again to mute:

    PLATOON MIC: OFF

Both status messages disappear automatically after approximately 3 seconds.

## Outside a Platoon

The mod only changes Push-to-Talk behavior while you are in a platoon.

Outside a platoon, the configured Push-to-Talk key continues to work normally:

    Hold key   → Microphone ON
    Release key → Microphone OFF

## Leaving a Platoon

If you:

- Leave the platoon
- Are removed from the platoon
- Disband the platoon

the mod automatically clears the toggle and mutes the microphone.

This prevents the microphone from accidentally remaining open.

## Changing the PTT Key

No mod configuration is required.

Simply change the Push-to-Talk key from the normal World of Tanks controls menu.

The mod reads the currently configured WoT PTT binding.

## Compatibility

Designed for:

- World of Tanks PC
- WoT 2.4.x client family
- Python 2.7 WoT mod environment

Game updates may change internal APIs and require an updated version of the mod.

## Manual / Development Installation

For development, the compiled Python module can also be installed directly:

    World of Tanks/
    └── res_mods/
        └── <game-version>/
            └── scripts/
                └── client/
                    └── gui/
                        └── mods/
                            └── mod_toggle_ptt.pyc

The Python module must be named:

    mod_toggle_ptt.pyc

Do not include version numbers containing dots in the Python module filename.

For example, do not use:

    mod_toggle_ptt_v1.3.0.pyc

## Building

World of Tanks currently uses Python 2.7 bytecode for this mod environment.

Example:

    C:\Python27\python.exe -m py_compile mod_toggle_ptt.py

The resulting file should be packaged inside the `.wotmod` as:

    res/scripts/client/gui/mods/mod_toggle_ptt.pyc

A `.wotmod` should contain:

    meta.xml
    res/
        scripts/
            client/
                gui/
                    mods/
                        mod_toggle_ptt.pyc

## Notes

This mod modifies only the World of Tanks voice-chat behavior.

It does not:

- Modify Windows microphone settings
- Capture or record audio
- Transmit audio outside the WoT voice system
- Add a separate global microphone hotkey
