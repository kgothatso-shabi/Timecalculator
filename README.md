# Timecalculator
Time Calculator is a Windows desktop app built with Python and Tkinter. It adds lists of hours and minutes, finds the time between two clock times with overnight and break support, and counts calendar or working days between dates with configurable inclusive rules.


# Time Calculator (Windows, Python / Tkinter)


| Panel | What it does |
|-------|--------------|
| **Enter Time / See Your Total** | Adds up to 60 lines of `HH : MM` durations. Shows `HH : MM` and decimal hours (5h44m = 5.73). CALCULATE, CLEAR, PRINT, EMAIL. |
| **Time Between Hours** | From / To clock times with AM/PM. Handles overnight shifts and unpaid breaks. |
| **Time Between Dates** | From / To dates with calendar pop-up. Calendar days or working days, configurable inclusive-date rules, weekends and holidays. |

No third-party packages are needed to run it.

## 1. Setup (Windows 10/11)

1. Install **Python 3.10+ (64-bit)** from <https://www.python.org/downloads/>. Tick *"Add python.exe to PATH"* and keep *tcl/tk and IDLE* selected (the default).
2. Open this folder in a terminal and run:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

(`requirements.txt` only contains the optional `pywin32` for direct Outlook drafts. You can skip it.)

Double-click `run.bat` to launch without a console window.

### Run the tests

```bat
python -m unittest discover -s tests -v
```

## 2. Using the app

* **Enter Time**: type hours and minutes (hours 0-99, minutes 0-59). Focus jumps to the next box after two digits. *+ Add More Lines* adds 5 lines (max 60; a scrollbar appears after 10). Press **Enter** to calculate.
* **PRINT** sends a plain-text report to the default printer (via the Windows `print` verb for `.txt` files).
* **EMAIL** opens an unsent, pre-filled draft:
  1. classic **Outlook** directly (needs `pywin32`), otherwise
  2. your **default mail client** through a `mailto:` link. The body is shortened automatically if it would exceed Windows' ~2000-character link limit.
  If neither works, the report is copied to the clipboard.
* **Time Between Hours > More Options**: decimal (`07.50`) or `hh:mm` output, overnight handling, unpaid break minutes. Hour `0` or `12` both mean 12.
* **Time Between Dates > More Options**:
  * *Calendar days* or *Working days* (skips weekend days and holidays)
  * *Include start date* / *Include end date* (default: start in, end out)
  * Weekend days (any combination of Mon-Sun) and a holiday list (`YYYY-MM-DD`, one per line)
  * Result as days, weeks + days, or years + months + days
* Settings are saved to `%APPDATA%\TimeCalculator\settings.json`. Delete that file to reset.

### How inclusive-date rules work

The counted window is `[first, last)` where `first` = From (or From + 1 if the start is excluded) and `last` = To (+ 1 if the end is included).

| Oct 13 -> Nov 13, 2026 | Result |
|---|---|
| start included, end excluded (default) | 31 |
| both excluded | 30 |
| both included | 32 |
| working days, default rules | 23 |

### Validation

Bad input is highlighted with a red border, the cursor jumps to it, and a message appears in the status line at the bottom. Checked: non-numeric entries, minutes > 59, hour > 12 on the clock panel, nonexistent dates (e.g. 30 Feb), years outside 1900-2200, *To* before *From* (dates), break longer than the interval, malformed holiday dates.

## 3. Build a Windows .exe

```bat
build.bat
```

This creates a virtual environment, installs PyInstaller, runs the tests and produces **`dist\TimeCalculator.exe`**, a single file with no console window. Copy it anywhere; it needs no Python on the target PC.

Manual equivalent:

```bat
pip install -r requirements-build.txt
pyinstaller --noconfirm --clean --windowed --onefile --name TimeCalculator main.py
```

Tips

* **Icon**: save a multi-size `.ico` as `assets\app.ico`; `build.bat` adds it automatically.
* **Faster start-up**: replace `--onefile` with `--onedir` and ship the whole `dist\TimeCalculator` folder.
* **Antivirus false positives** are common with unsigned one-file PyInstaller builds. Prefer `--onedir`, build on a clean machine, and sign the exe (`signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a dist\TimeCalculator.exe`).
* **Build on the oldest Windows version** you need to support, and use 64-bit Python for 64-bit Windows.

### Optional installer

Install [Inno Setup 6](https://jrsoftware.org/isinfo.php), run `build.bat`, open `installer.iss` and press **Compile**. Output: `dist\TimeCalculator-Setup.exe` (per-user install, Start Menu entry, optional desktop shortcut, uninstaller).

## 4. Project layout

```
main.py              entry point (DPI awareness, then starts the UI)
timecalc/core.py     all calculations and validation (no GUI imports)
timecalc/ui.py       Tkinter window, calendar pop-up, option dialogs
timecalc/mailer.py   report text, Outlook / mailto draft, printing
timecalc/settings.py JSON settings in %APPDATA%
tests/test_core.py   unit tests for the calculations
build.bat, installer.iss, run.bat, requirements*.txt
```

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| `No module named tkinter` | Re-run the Python installer > Modify > tick *tcl/tk and IDLE*. |
| EMAIL opens the wrong app | Change the default **Email** app in *Settings > Apps > Default apps*. |
| "New Outlook" ignores direct drafts | New Outlook has no COM interface; the app falls back to `mailto:`, which it does support. |
| PRINT does nothing | Make sure a default printer is set and `.txt` files have a *Print* action (Notepad does). |
| Blurry text | The app is DPI-aware; check *Properties > Compatibility > Change high DPI settings* is not overriding it. |
