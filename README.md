# PolyMod Launcher (FNF Launcher)

A launcher for **Friday Night Funkin' V-Slice** (PolyMod). Browse, search and install mods from GameBanana, turn installed mods on and off or delete them, and start the game, all from one window.

This is an unofficial fan tool. It is not affiliated with the Friday Night Funkin' team or GameBanana.

## Features

- Browse GameBanana's mod feed, search by name, or paste a mod page link (or a mod ID) to open a mod directly
- Filters: category, sort (default, newest, most liked, most viewed) and "Hide installed"
- **Best of today**: the most liked mod added or updated in the last 24 hours, shown on every screen
- Download one or several mods at once. Mods without a zip archive are skipped
- Manage installed mods: enable, disable or delete them (deleting asks for confirmation)
- Start the game from the launcher, optionally closing the launcher on start
- Interface in English, Português (BR), Русский, Español and Bahasa Indonesia
- Background music, interface sounds, button colors and smooth animations. Sounds and animations can be switched off

## Requirements

- Python 3.14 (the version the launcher is developed on)
- pygame-ce, listed in [requirements.txt](requirements.txt)
- tkinter, used by the folder picker. It is included with Python on Windows and macOS. On Linux install it with your package manager, for example `sudo apt install python3-tk`

pygame-ce and the classic `pygame` package both provide the `pygame` module, so they cannot be used together. If classic pygame is installed, remove it first with `pip uninstall pygame`.

## Installation

```bash
git clone <repository-url>
cd <repository-folder>
python -m venv .venv
```

Activate the virtual environment:

- Windows: `.venv\Scripts\activate`
- macOS / Linux: `source .venv/bin/activate`

Install the requirements and start the launcher:

```bash
pip install -r requirements.txt
python fnf_launcher.py
```

## First start

1. Open **OPTIONS** and press **Browse...**
2. Choose the folder where Friday Night Funkin' V-Slice is installed, the one that contains the game file (for example `Funkin.exe` on Windows)
3. Go back to **GAME**. **LAUNCH** starts the game, and the **MODS** button there shows the mods you have installed

## Using the launcher

- **GAME**: **LAUNCH** starts the game. The **MODS** button opens your installed mods, where you can enable, disable or delete them
- **MODS** in the left menu: browse GameBanana. Type a name in the search box and press Enter. Click cards to select mods, then press **Download selected** or **Download page**
- **OPTIONS**: game folder, language (click the Language row to switch it), sounds, button color, smooth animations and "Close launcher on game start"
- **F11** switches fullscreen, **Esc** leaves fullscreen

The first time you use the filters, the launcher downloads the full mod list once and keeps it for 7 days, so this takes a moment.

The **Best of today** banner is built from the newest pages of GameBanana's feed. It is not GameBanana's own ranking, so it can differ from the website.

## Assets

The launcher loads its pictures, fonts and sounds from the `assets/` folder next to `fnf_launcher.py`.

Required. Without these files the launcher stops and lists what is missing:

| File | Used for |
| --- | --- |
| `FunkinOptions.otf` | English interface font |
| `menuDesat.png` | background |
| `FNF_logo.png` | logo on the GAME screen |
| `GameButton.png`, `GameButtonSelected.png` | GAME menu button |
| `ModsButton.png`, `ModsButtonSelected.png` | MODS menu button |
| `OptionsButton.png`, `OptionsButtonSelected.png` | OPTIONS menu button |
| `ButtonMods.png` | MODS button on the GAME screen |
| `ButtonLaunch.png` | LAUNCH button |

Optional. The launcher works without these:

| File | Used for |
| --- | --- |
| `difficultyFont.ttf` | font for Português, Русский and Español (the English font is used if it is missing) |
| `LauncherLogo.png` | window icon |
| `BGMusic.mp3` | background music |
| `CS_select.ogg`, `CS_confirm.ogg` | interface sounds |

To translate the menu pictures, put a picture with the same name into `assets/pt/`, `assets/ru/`, `assets/es/` or `assets/id/`. It is used only for that language.

## Project structure

```
fnf_launcher.py      the launcher
assets/              pictures, fonts and sounds
requirements.txt     Python dependencies
LICENSE              MIT license for the code
README.md
```

## Files the launcher creates

- `~/.fnf_launcher.json`: your settings
- `~/.fnf_mods_index.json`: cached mod list, refreshed every 7 days
- `mods/` and `mods_disabled/` inside the game folder: installed mods. Each mod installed by the launcher gets a small `fnf_mod.json` with its GameBanana ID

## Building an executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name PolyModLauncher --add-data "assets;assets" fnf_launcher.py
```

On macOS and Linux use `--add-data "assets:assets"`. The result appears in `dist/`.

## Troubleshooting

- **"These files are missing from the assets folder"**: add the listed files to `assets/`. The message is printed in the terminal
- **No folder picker on Linux**: install `python3-tk`
- **"No game file found in this folder"**: choose the folder that contains the game file itself
- **"No connection to GameBanana"**: check your internet connection. The status line at the bottom of the window shows the error

## License

The code is released under the [MIT License](LICENSE).

Friday Night Funkin' and its artwork, music and sounds belong to their creators (ninjamuffin99, PhantomArcade, KawaiSprite and evilsk8r) and are not covered by the MIT License. Mods belong to their authors on GameBanana.

## Credits

- Friday Night Funkin' and its creators
- [GameBanana](https://gamebanana.com) for the mods
- [pygame-ce](https://github.com/pygame-community/pygame-ce)
