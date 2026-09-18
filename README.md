# Toggle Platoon PTT v1.4.3

## Project files

- `src/mod_toggle_ptt.py` - mod source
- `tests/test_toggle_ptt.py` - local mock-runtime regression tests
- `build.py` - compiler/packager
- `build.bat` - one-click Windows build
- `build_install.bat` - build + copy into WoT
- `clean.bat` - remove generated build output
- `test.bat` - run mock tests
- `mod.json` - package metadata
- `build.local.example.json` - example local WoT install configuration
- `GOALS.md` - behavioral requirements
- `PATCHNOTES.md` - version history
- `lessons_learned.md` - engineering safeguards
- `DIAGNOSIS.md` - teardown trace and validation limits

## Requirements

### To build the actual `.wotmod`

World of Tanks production mods use Python 2.7 bytecode.

Install **Python 2.7.18** and either:

1. make it available through the Windows Python launcher as `py -2.7`; or
2. install it at `C:\Python27\python.exe`; or
3. set:

```bat
set PYTHON27=C:\path\to\python.exe
```

No pip packages are required.

### To run the mock tests

Python 3 is recommended.

## Build

Double-click:

```text
build.bat
```

or run:

```bat
build.bat
```

Output:

```text
dist\panda_toggle_platoon_ptt_1.4.3.wotmod
```

The generated `.wotmod` contains:

```text
meta.xml
res/
└── scripts/
    └── client/
        └── gui/
            └── mods/
                └── mod_toggle_ptt.pyc
```

## Manual installation

Copy the generated `.wotmod` into:

```text
<World of Tanks>\mods\<CURRENT_GAME_VERSION>\
```

Use the exact current version folder already present under the game's `mods`
directory.

## Automatic build + install

1. Copy:

```text
build.local.example.json
```

to:

```text
build.local.json
```

2. Edit `build.local.json`.

Example:

```json
{
  "game_dir": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\World of Tanks",
  "game_version": "2.4.0.0"
}
```

Use the version folder that exists on your machine; do not assume the example
version is still current.

3. Run:

```text
build_install.bat
```

## Tests

Run:

```text
test.bat
```

The tests cover normal PTT, toggle behavior, key rebinding, platoon transitions,
VOIP reconnects, silent microphone failure/self-healing, intentionally disabled
voice channels, settings changes, HUD failures, shutdown cleanup, and hook
coexistence.

## Settings panel

The core mod has no required third-party dependency.

If `ModsSettingsAPI` / a compatible Aslain settings API is already installed,
the mod exposes its settings panel there. Without that API, the mod still works
with its defaults:

- enabled: ON
- microphone indicator: ON

## Install the included build

The developer ZIP includes the compiled Python 2.7.18 package in `dist/`.
Exit WoT, remove older Toggle Platoon PTT packages from the active `mods/<version>/`
folder, and copy `dist/panda_toggle_platoon_ptt_1.4.3.wotmod` there. Also remove
any older standalone `mod_toggle_ptt.pyc` installation under `res_mods` to avoid
loading two versions. Restart WoT. The startup log should report v1.4.3.

For a Steam installation, use the regional game directory (for example,
`World of Tanks/eu`), containing `version.xml` and `mods`.

## Live verification

Enable the microphone in a platoon, enter battle, then return to the garage
without pressing PTT. Ask a platoon member to confirm that they still hear you.
Repeat after dying and after battle completion. Check manual OFF and leaving
the platoon, then test with the voice channel disabled. Local regression tests
pass, but v1.4.3 still requires this live audio verification.

See `DIAGNOSIS.md` for the verified source revision and evidence limits.
