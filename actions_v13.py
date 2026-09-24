import os
import re
import threading
import time
import json
import urllib.parse
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from difflib import SequenceMatcher

import ollama
import pyautogui
import tkinter as tk
import psutil

MODEL = "llama3"



def _looks_like_action(command):
    """Fast gate: normal conversation skips the action LLM completely."""
    text = (command or "").lower().strip()

    action_words = (
        "open", "kholo", "khol", "close", "band", "search", "dhundo",
        "find", "volume", "awaaz", "mute", "screenshot", "window",
        "minimize", "maximize", "restore", "battery", "ram", "cpu",
        "processor", "disk", "storage", "system info", "laptop status",
        "desktop", "downloads", "documents", "pictures", "folder", "file",
        "app", "application", "scroll", "click", "copy", "paste",
        "select all", "undo", "redo", "type", "likho", "enter",
        "backspace", "delete", "tab", "escape", "space", "timer",
        "reminder", "yaad dil", "kitne baje", "time kya", "date kya",
        "aaj ka date", "show desktop", "switch window"
    )

    return any(word in text for word in action_words)


def understand_action(command):
    # V13 speed boost: ordinary chat no longer waits for an
    # unnecessary first Ollama action-classification request.
    if not _looks_like_action(command):
        return "NONE", ""

    prompt = """
You are the action controller for Luna, a Windows AI assistant.
The user may speak Hindi, Bengali, Hinglish, Banglish, or English.
Speech recognition may contain small spelling mistakes.

Available actions:
OPEN_CHROME
OPEN_NOTEPAD
OPEN_CALCULATOR
OPEN_EXPLORER
OPEN_GOOGLE
OPEN_YOUTUBE
GOOGLE_SEARCH
YOUTUBE_SEARCH
CLOSE_CHROME
CLOSE_NOTEPAD
CLOSE_CALCULATOR
CLOSE_EXPLORER
VOLUME_UP
VOLUME_DOWN
VOLUME_MUTE
TAKE_SCREENSHOT
WINDOW_MINIMIZE
WINDOW_MAXIMIZE
WINDOW_RESTORE
GET_BATTERY
GET_RAM
GET_CPU
GET_DISK
GET_SYSTEM_INFO
OPEN_DESKTOP
OPEN_DOWNLOADS
OPEN_DOCUMENTS
OPEN_PICTURES
OPEN_FOLDER
FIND_FILE
FIND_FOLDER
FIND_FILE_TYPE
OPEN_APP
CLOSE_APP
FIND_APP
LIST_APPS
ACTIVE_WINDOW_CLOSE
SHOW_DESKTOP
WINDOW_SNAP_LEFT
WINDOW_SNAP_RIGHT
SWITCH_WINDOW
SCROLL_UP
SCROLL_DOWN
MOUSE_CLICK
MOUSE_DOUBLE_CLICK
MOUSE_RIGHT_CLICK
COPY
PASTE
SELECT_ALL
UNDO
REDO
TYPE_TEXT
COPY_TEXT
READ_CLIPBOARD
CLEAR_CLIPBOARD
PRESS_ENTER
PRESS_BACKSPACE
PRESS_DELETE
PRESS_TAB
PRESS_ESCAPE
PRESS_SPACE
GET_TIME
GET_DATE
SET_TIMER
SET_REMINDER
LIST_REMINDERS
CANCEL_REMINDERS
NONE

For GOOGLE_SEARCH and YOUTUBE_SEARCH, extract the search query.
For OPEN_FOLDER, FIND_FILE, FIND_FOLDER, FIND_FILE_TYPE, OPEN_APP, CLOSE_APP and FIND_APP, put the requested name/type in query.
For TYPE_TEXT and COPY_TEXT, put ONLY the text the user wants typed/copied in query.
For SET_TIMER, put the duration phrase in query, for example "5 minutes".
For SET_REMINDER, preserve the time and reminder text in query.
For GET_TIME, GET_DATE, LIST_REMINDERS and CANCEL_REMINDERS, query must be empty.
For OPEN_DESKTOP, OPEN_DOWNLOADS, OPEN_DOCUMENTS and OPEN_PICTURES, query must be empty.
For all other actions, query must be an empty string.
Return ONLY valid JSON:
{"action":"ACTION_NAME","query":""}

Examples:
User: Chrome kholo
{"action":"OPEN_CHROME","query":""}
User: Chrome band karo
{"action":"CLOSE_CHROME","query":""}
User: Notepad close karo
{"action":"CLOSE_NOTEPAD","query":""}
User: calculator band karo
{"action":"CLOSE_CALCULATOR","query":""}
User: file explorer close karo
{"action":"CLOSE_EXPLORER","query":""}
User: volume badhao
{"action":"VOLUME_UP","query":""}
User: awaaz kam karo
{"action":"VOLUME_DOWN","query":""}
User: mute karo
{"action":"VOLUME_MUTE","query":""}
User: screenshot lo
{"action":"TAKE_SCREENSHOT","query":""}
User: window minimize karo
{"action":"WINDOW_MINIMIZE","query":""}
User: window maximize karo
{"action":"WINDOW_MAXIMIZE","query":""}
User: window restore karo
{"action":"WINDOW_RESTORE","query":""}
User: Google par Assam weather search karo
{"action":"GOOGLE_SEARCH","query":"Assam weather"}
User: YouTube par Python tutorial search karo
{"action":"YOUTUBE_SEARCH","query":"Python tutorial"}
User: battery kitni hai
{"action":"GET_BATTERY","query":""}
User: battery percentage batao
{"action":"GET_BATTERY","query":""}
User: RAM kitni use ho rahi hai
{"action":"GET_RAM","query":""}
User: memory usage batao
{"action":"GET_RAM","query":""}
User: CPU usage batao
{"action":"GET_CPU","query":""}
User: processor kitna use ho raha hai
{"action":"GET_CPU","query":""}
User: disk me kitni space baki hai
{"action":"GET_DISK","query":""}
User: storage kitni free hai
{"action":"GET_DISK","query":""}
User: system information batao
{"action":"GET_SYSTEM_INFO","query":""}
User: laptop status batao
{"action":"GET_SYSTEM_INFO","query":""}

User: Downloads folder kholo
{"action":"OPEN_DOWNLOADS","query":""}
User: Desktop kholo
{"action":"OPEN_DESKTOP","query":""}
User: Documents folder kholo
{"action":"OPEN_DOCUMENTS","query":""}
User: Pictures folder kholo
{"action":"OPEN_PICTURES","query":""}
User: nadia folder kholo
{"action":"OPEN_FOLDER","query":"nadia"}
User: resume file dhundo
{"action":"FIND_FILE","query":"resume"}
User: invoice folder dhundo
{"action":"FIND_FOLDER","query":"invoice"}
User: PDF files dhundo
{"action":"FIND_FILE_TYPE","query":"pdf"}
User: desktop par PDF files dhundo
{"action":"FIND_FILE_TYPE","query":"pdf"}
User: VS Code kholo
{"action":"OPEN_APP","query":"VS Code"}
User: Paint kholo
{"action":"OPEN_APP","query":"Paint"}
User: Spotify open karo
{"action":"OPEN_APP","query":"Spotify"}
User: VS Code band karo
{"action":"CLOSE_APP","query":"VS Code"}
User: Spotify close karo
{"action":"CLOSE_APP","query":"Spotify"}
User: Photoshop installed hai kya
{"action":"FIND_APP","query":"Photoshop"}
User: mere apps dikhao
{"action":"LIST_APPS","query":""}
User: installed applications batao
{"action":"LIST_APPS","query":""}
User: active window close karo
{"action":"ACTIVE_WINDOW_CLOSE","query":""}
User: desktop dikhao
{"action":"SHOW_DESKTOP","query":""}
User: window left side snap karo
{"action":"WINDOW_SNAP_LEFT","query":""}
User: window right side karo
{"action":"WINDOW_SNAP_RIGHT","query":""}
User: next window par switch karo
{"action":"SWITCH_WINDOW","query":""}
User: neeche scroll karo
{"action":"SCROLL_DOWN","query":""}
User: upar scroll karo
{"action":"SCROLL_UP","query":""}
User: click karo
{"action":"MOUSE_CLICK","query":""}
User: double click karo
{"action":"MOUSE_DOUBLE_CLICK","query":""}
User: right click karo
{"action":"MOUSE_RIGHT_CLICK","query":""}
User: copy karo
{"action":"COPY","query":""}
User: paste karo
{"action":"PASTE","query":""}
User: select all karo
{"action":"SELECT_ALL","query":""}
User: undo karo
{"action":"UNDO","query":""}
User: redo karo
{"action":"REDO","query":""}
User: type karo Hello, how are you
{"action":"TYPE_TEXT","query":"Hello, how are you"}
User: likho My name is Mohibul
{"action":"TYPE_TEXT","query":"My name is Mohibul"}
User: ye copy karo My name is Mohibul
{"action":"COPY_TEXT","query":"My name is Mohibul"}
User: clipboard me kya hai
{"action":"READ_CLIPBOARD","query":""}
User: clipboard clear karo
{"action":"CLEAR_CLIPBOARD","query":""}
User: Enter dabao
{"action":"PRESS_ENTER","query":""}
User: Backspace dabao
{"action":"PRESS_BACKSPACE","query":""}
User: Delete dabao
{"action":"PRESS_DELETE","query":""}
User: Tab dabao
{"action":"PRESS_TAB","query":""}
User: Escape dabao
{"action":"PRESS_ESCAPE","query":""}
User: Space dabao
{"action":"PRESS_SPACE","query":""}
User: abhi kitne baje hain
{"action":"GET_TIME","query":""}
User: aaj ka date kya hai
{"action":"GET_DATE","query":""}
User: 5 minute ka timer lagao
{"action":"SET_TIMER","query":"5 minutes"}
User: 20 minute baad medicine yaad dilana
{"action":"SET_REMINDER","query":"20 minute baad medicine"}
User: 8 PM par phone karna yaad dilana
{"action":"SET_REMINDER","query":"8 PM par phone karna"}
User: mere reminders batao
{"action":"LIST_REMINDERS","query":""}
User: reminders cancel karo
{"action":"CANCEL_REMINDERS","query":""}
User: Chrome kya hai?
{"action":"NONE","query":""}

User command:
""" + command

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0, "num_predict": 80},
            keep_alive="30m"
        )
        result = response["message"]["content"].strip()
        result = result.replace("```json", "").replace("```", "").strip()
        data = json.loads(result)
        action = str(data.get("action", "NONE")).upper().strip()
        query = str(data.get("query", "")).strip()
        return action, query
    except Exception as error:
        print("Action understanding error:", error)
        return "NONE", ""


def _press_media_key(key, presses=1):
    for _ in range(presses):
        pyautogui.press(key)


def _screenshot_folder():
    folder = os.path.join(
        os.path.expanduser("~"),
        "Pictures",
        "Luna Screenshots"
    )
    os.makedirs(folder, exist_ok=True)
    return folder



def _gb(value):
    return round(
        value / (1024 ** 3),
        1
    )


def get_battery_info():
    battery = psutil.sensors_battery()

    if battery is None:
        return (
            "Battery information available nahi hai. "
            "Ho sakta hai ye desktop ho ya Windows battery data report na kar raha ho."
        )

    percent = round(
        battery.percent
    )

    if battery.power_plugged:
        power = "charger connected hai"
    else:
        power = "charger connected nahi hai"

    return (
        f"Battery {percent} percent hai aur {power}."
    )


def get_ram_info():
    ram = psutil.virtual_memory()

    used = _gb(
        ram.used
    )

    total = _gb(
        ram.total
    )

    available = _gb(
        ram.available
    )

    return (
        f"RAM usage {round(ram.percent)} percent hai. "
        f"{used} GB use ho rahi hai, "
        f"{available} GB available hai, "
        f"total RAM {total} GB hai."
    )


def get_cpu_info():
    usage = psutil.cpu_percent(
        interval=0.5
    )

    logical = psutil.cpu_count(
        logical=True
    )

    physical = psutil.cpu_count(
        logical=False
    )

    parts = [
        f"CPU usage {round(usage)} percent hai"
    ]

    if physical:
        parts.append(
            f"{physical} physical cores hain"
        )

    if logical:
        parts.append(
            f"{logical} logical processors hain"
        )

    return ". ".join(parts) + "."


def get_disk_info():
    system_drive = (
        os.environ.get(
            "SystemDrive",
            "C:"
        )
        + "\\"
    )

    disk = psutil.disk_usage(
        system_drive
    )

    free = _gb(
        disk.free
    )

    used = _gb(
        disk.used
    )

    total = _gb(
        disk.total
    )

    return (
        f"{system_drive} drive {round(disk.percent)} percent used hai. "
        f"{free} GB free, "
        f"{used} GB used aur "
        f"{total} GB total space hai."
    )


def get_system_info():
    cpu = psutil.cpu_percent(
        interval=0.5
    )

    ram = psutil.virtual_memory()

    system_drive = (
        os.environ.get(
            "SystemDrive",
            "C:"
        )
        + "\\"
    )

    disk = psutil.disk_usage(
        system_drive
    )

    battery = psutil.sensors_battery()

    status = (
        f"CPU {round(cpu)} percent, "
        f"RAM {round(ram.percent)} percent used, "
        f"{system_drive} drive me {_gb(disk.free)} GB free space"
    )

    if battery is not None:
        status += (
            f", battery {round(battery.percent)} percent"
        )

        if battery.power_plugged:
            status += " aur charger connected hai"
        else:
            status += " aur charger connected nahi hai"

    return status + "."



# ============================================
# FILE & FOLDER INTELLIGENCE
# ============================================

def _home():
    return Path.home()


def _common_locations():
    home = _home()

    candidates = [
        home / "Desktop",
        home / "Downloads",
        home / "Documents",
        home / "Pictures",
        Path("E:/"),
        home
    ]

    locations = []
    seen = set()

    for item in candidates:
        try:
            resolved = str(item.resolve()).lower()
        except Exception:
            resolved = str(item).lower()

        if item.exists() and resolved not in seen:
            locations.append(item)
            seen.add(resolved)

    return locations


def _open_path(path):
    try:
        os.startfile(str(path))
        return True
    except Exception as error:
        print("Open path error:", error)
        return False


def _safe_search(name, want_files=True, want_folders=True, extension=None, limit=8):
    name = (name or "").strip().lower()
    extension = (extension or "").strip().lower().lstrip(".")

    matches = []
    skip_names = {
        "$recycle.bin",
        "system volume information",
        "windows",
        "program files",
        "program files (x86)",
        "programdata",
        "appdata",
        ".git",
        ".venv",
        "node_modules"
    }

    for base in _common_locations():
        if len(matches) >= limit:
            break

        try:
            for root, dirs, files in os.walk(base, topdown=True):
                dirs[:] = [
                    d for d in dirs
                    if d.lower() not in skip_names
                ]

                if want_folders and not extension:
                    for folder in dirs:
                        if name and name in folder.lower():
                            matches.append(Path(root) / folder)
                            if len(matches) >= limit:
                                return matches

                if want_files:
                    for filename in files:
                        lower = filename.lower()

                        if extension:
                            if lower.endswith("." + extension):
                                matches.append(Path(root) / filename)
                        elif name and name in lower:
                            matches.append(Path(root) / filename)

                        if len(matches) >= limit:
                            return matches

        except (PermissionError, OSError):
            continue

    return matches


def _format_matches(matches, label):
    if not matches:
        return f"{label} nahi mila."

    if len(matches) == 1:
        return f"1 match mila: {matches[0]}"

    shown = matches[:5]
    text = "; ".join(
        str(item)
        for item in shown
    )

    extra = len(matches) - len(shown)

    if extra > 0:
        text += f"; aur {extra} match."

    return f"{len(matches)} matches mile: {text}"


def open_named_folder(name):
    matches = _safe_search(
        name,
        want_files=False,
        want_folders=True,
        limit=5
    )

    if not matches:
        return f"{name} folder nahi mila."

    if len(matches) == 1:
        if _open_path(matches[0]):
            return f"{name} folder khol diya."
        return f"{name} folder mila, lekin open nahi ho paya."

    return _format_matches(
        matches,
        f"{name} folder"
    )


def find_file(name):
    matches = _safe_search(
        name,
        want_files=True,
        want_folders=False,
        limit=8
    )
    return _format_matches(
        matches,
        f"{name} file"
    )


def find_folder(name):
    matches = _safe_search(
        name,
        want_files=False,
        want_folders=True,
        limit=8
    )
    return _format_matches(
        matches,
        f"{name} folder"
    )


def find_file_type(extension):
    aliases = {
        "pdf": "pdf",
        ".pdf": "pdf",
        "image": "jpg",
        "jpg": "jpg",
        "jpeg": "jpeg",
        "png": "png",
        "text": "txt",
        "txt": "txt",
        "word": "docx",
        "docx": "docx",
        "excel": "xlsx",
        "xlsx": "xlsx",
        "python": "py",
        "py": "py"
    }

    ext = aliases.get(
        extension.strip().lower(),
        extension.strip().lower().lstrip(".")
    )

    matches = _safe_search(
        "",
        want_files=True,
        want_folders=False,
        extension=ext,
        limit=8
    )

    return _format_matches(
        matches,
        f"{ext.upper()} file"
    )


def open_common_folder(folder_name):
    home = _home()

    mapping = {
        "desktop": home / "Desktop",
        "downloads": home / "Downloads",
        "documents": home / "Documents",
        "pictures": home / "Pictures"
    }

    path = mapping.get(
        folder_name.lower()
    )

    if path is None or not path.exists():
        return f"{folder_name} folder nahi mila."

    if _open_path(path):
        return f"{folder_name} folder khol diya."

    return f"{folder_name} folder open nahi ho paya."



# ============================================
# V8 - SMART APP CONTROL
# ============================================

APP_ALIASES = {
    "vs code": ["visual studio code", "code"],
    "vscode": ["visual studio code", "code"],
    "visual studio code": ["visual studio code", "code"],
    "paint": ["paint", "mspaint"],
    "calculator": ["calculator", "calc"],
    "notepad": ["notepad"],
    "file explorer": ["file explorer", "explorer"],
    "explorer": ["file explorer", "explorer"],
    "command prompt": ["command prompt", "cmd"],
    "cmd": ["command prompt", "cmd"],
    "powershell": ["windows powershell", "powershell"],
    "task manager": ["task manager", "taskmgr"],
    "settings": ["settings"],
    "control panel": ["control panel"],
    "chrome": ["google chrome", "chrome"],
    "edge": ["microsoft edge", "edge"],
    "firefox": ["mozilla firefox", "firefox"],
    "spotify": ["spotify"]
}

BUILTIN_APPS = {
    "paint": "mspaint",
    "mspaint": "mspaint",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "command prompt": "cmd",
    "cmd": "cmd",
    "powershell": "powershell",
    "task manager": "taskmgr",
    "taskmgr": "taskmgr",
    "control panel": "control",
    "settings": "ms-settings:"
}

PROCESS_HINTS = {
    "vs code": ["code.exe"],
    "vscode": ["code.exe"],
    "visual studio code": ["code.exe"],
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "spotify": ["spotify.exe"],
    "paint": ["mspaint.exe"],
    "notepad": ["notepad.exe"],
    "calculator": ["calculatorapp.exe", "calc.exe"],
    "file explorer": ["explorer.exe"],
    "powershell": ["powershell.exe", "pwsh.exe"],
    "command prompt": ["cmd.exe"],
    "cmd": ["cmd.exe"],
    "task manager": ["taskmgr.exe"]
}


def _normalize_app_name(name):
    text = (name or "").lower().strip()

    for word in [
        ".exe",
        "application",
        "app",
        "software"
    ]:
        text = text.replace(word, " ")

    return " ".join(text.split())


def _start_menu_locations():
    locations = []

    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")

    if appdata:
        locations.append(
            Path(appdata)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
        )

    if programdata:
        locations.append(
            Path(programdata)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
        )

    return [
        path
        for path in locations
        if path.exists()
    ]


def _discover_start_menu_apps():
    apps = {}

    allowed = {
        ".lnk",
        ".url",
        ".appref-ms",
        ".exe"
    }

    for base in _start_menu_locations():
        try:
            for item in base.rglob("*"):
                if not item.is_file():
                    continue

                if item.suffix.lower() not in allowed:
                    continue

                display = item.stem.strip()

                if not display:
                    continue

                key = _normalize_app_name(
                    display
                )

                if key and key not in apps:
                    apps[key] = {
                        "name": display,
                        "path": item
                    }

        except (PermissionError, OSError):
            continue

    return apps


def _candidate_names(query):
    query = _normalize_app_name(
        query
    )

    names = [query]

    for alias in APP_ALIASES.get(query, []):
        alias = _normalize_app_name(
            alias
        )
        if alias not in names:
            names.append(alias)

    return names


def _app_score(query, candidate):
    query = _normalize_app_name(
        query
    )
    candidate = _normalize_app_name(
        candidate
    )

    if not query or not candidate:
        return 0.0

    if query == candidate:
        return 1.0

    if query in candidate:
        return 0.92

    if candidate in query:
        return 0.88

    return SequenceMatcher(
        None,
        query,
        candidate
    ).ratio()


def _find_app_matches(query, limit=5):
    apps = _discover_start_menu_apps()
    queries = _candidate_names(
        query
    )

    ranked = []

    for key, info in apps.items():
        score = max(
            _app_score(q, key)
            for q in queries
        )

        if score >= 0.55:
            ranked.append(
                (
                    score,
                    info
                )
            )

    ranked.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [
        info
        for _, info in ranked[:limit]
    ]


def smart_open_app(name):
    normalized = _normalize_app_name(
        name
    )

    # Fast path for Windows built-ins.
    for candidate in _candidate_names(
        normalized
    ):
        if candidate in BUILTIN_APPS:
            target = BUILTIN_APPS[
                candidate
            ]

            try:
                if target.endswith(":"):
                    os.startfile(
                        target
                    )
                else:
                    os.system(
                        f'start "" "{target}"'
                    )

                return f"{name} khol diya."
            except Exception as error:
                print(
                    "Built-in app open error:",
                    error
                )

    matches = _find_app_matches(
        normalized,
        limit=5
    )

    if not matches:
        return (
            f"{name} app Start Menu me nahi mila. "
            "Ho sakta hai app installed na ho ya uska shortcut registered na ho."
        )

    # Open automatically only when the best match is clearly strong.
    best = matches[0]
    best_score = max(
        _app_score(
            q,
            best["name"]
        )
        for q in _candidate_names(
            normalized
        )
    )

    if best_score >= 0.72:
        try:
            os.startfile(
                str(best["path"])
            )
            return (
                f"{best['name']} khol diya."
            )
        except Exception as error:
            print(
                "Smart app open error:",
                error
            )
            return (
                f"{best['name']} mila, lekin open nahi ho paya."
            )

    names = ", ".join(
        item["name"]
        for item in matches
    )

    return (
        f"Exact app clear nahi hai. Mujhe ye matches mile: {names}."
    )


def find_installed_app(name):
    normalized = _normalize_app_name(
        name
    )

    if any(
        candidate in BUILTIN_APPS
        for candidate in _candidate_names(
            normalized
        )
    ):
        return f"{name} Windows me available hai."

    matches = _find_app_matches(
        normalized,
        limit=5
    )

    if not matches:
        return f"{name} app Start Menu me nahi mila."

    names = ", ".join(
        item["name"]
        for item in matches
    )

    return f"App matches mile: {names}."


def list_installed_apps():
    apps = _discover_start_menu_apps()

    if not apps:
        return "Start Menu se installed apps ki list nahi mil payi."

    names = sorted(
        {
            info["name"]
            for info in apps.values()
        },
        key=str.lower
    )

    # Keep spoken/UI reply manageable.
    shown = names[:25]

    text = ", ".join(
        shown
    )

    if len(names) > len(shown):
        text += (
            f". Aur {len(names) - len(shown)} apps bhi mile."
        )

    return (
        f"Mujhe {len(names)} Start Menu apps mile. "
        f"Pehle apps: {text}"
    )


def _process_matches_for_app(name):
    normalized = _normalize_app_name(
        name
    )

    hints = []

    for candidate in _candidate_names(
        normalized
    ):
        hints.extend(
            PROCESS_HINTS.get(
                candidate,
                []
            )
        )

    hint_set = {
        item.lower()
        for item in hints
    }

    matches = []

    for process in psutil.process_iter(
        ["pid", "name"]
    ):
        try:
            process_name = (
                process.info.get("name")
                or ""
            ).lower()

            stem = _normalize_app_name(
                Path(process_name).stem
            )

            direct_match = (
                process_name in hint_set
            )

            fuzzy_match = (
                normalized
                and len(normalized) >= 3
                and _app_score(
                    normalized,
                    stem
                ) >= 0.84
            )

            if direct_match or fuzzy_match:
                matches.append(
                    process
                )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied
        ):
            continue

    return matches


def smart_close_app(name):
    normalized = _normalize_app_name(
        name
    )

    # Explorer is special: killing explorer.exe also kills the desktop/taskbar.
    if normalized in {
        "explorer",
        "file explorer"
    }:
        pyautogui.hotkey(
            "alt",
            "f4"
        )
        return (
            "Active File Explorer window band karne ki command de di."
        )

    matches = _process_matches_for_app(
        name
    )

    if not matches:
        return (
            f"{name} ka running process nahi mila."
        )

    closed = 0

    for process in matches:
        try:
            process.terminate()
            closed += 1
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied
        ):
            continue

    if closed:
        return (
            f"{name} ke {closed} running process ko close command de di."
        )

    return (
        f"{name} mila, lekin Windows ne close karne ki permission nahi di."
    )



# ============================================
# V10 - CLIPBOARD & SMART TYPING
# ============================================

def _clipboard_set(text):
    try:
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception as error:
        print("Clipboard set error:", error)
        return False


def _clipboard_get():
    try:
        root = tk.Tk()
        root.withdraw()
        try:
            text = root.clipboard_get()
        except tk.TclError:
            text = ""
        root.destroy()
        return text
    except Exception as error:
        print("Clipboard read error:", error)
        return ""


def _clipboard_clear():
    try:
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.update()
        root.destroy()
        return True
    except Exception as error:
        print("Clipboard clear error:", error)
        return False


def smart_type_text(text):
    if not text:
        return "Kya type karna hai?"
    # Ctrl+V supports Hindi/Bengali/Unicode better than pyautogui.write().
    if not _clipboard_set(text):
        return "Text clipboard me set nahi ho paya."
    pyautogui.hotkey("ctrl", "v")
    return "Text type kar diya."


def copy_given_text(text):
    if not text:
        return "Kya copy karna hai?"
    if _clipboard_set(text):
        return "Text clipboard me copy kar diya."
    return "Text copy nahi ho paya."


def read_clipboard_text():
    text = _clipboard_get()
    if not text:
        return "Clipboard khali hai ya text available nahi hai."
    if len(text) > 800:
        return "Clipboard me bahut lamba text hai. Pehle 800 characters: " + text[:800]
    return "Clipboard me ye hai: " + text


def clear_clipboard_text():
    if _clipboard_clear():
        return "Clipboard clear kar diya."
    return "Clipboard clear nahi ho paya."



# ============================================
# V12 - TIME, DATE, TIMER & REMINDERS
# ============================================

REMINDER_FILE = Path("luna_reminders.json")
_reminder_lock = threading.Lock()


def _load_reminders():
    with _reminder_lock:
        if not REMINDER_FILE.exists():
            return []
        try:
            return json.loads(REMINDER_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []


def _save_reminders(items):
    with _reminder_lock:
        REMINDER_FILE.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


def _duration_seconds(text):
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(second|seconds|sec|minute|minutes|min|hour|hours|hr|ghanta|ghante)",
        (text or "").lower()
    )
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    if unit.startswith(("second", "sec")):
        return int(value)
    if unit.startswith(("minute", "min")):
        return int(value * 60)
    return int(value * 3600)


def _parse_exact_time(text):
    now = datetime.now()
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", (text or "").lower())
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = match.group(3)
    if hour < 1 or hour > 12 or minute > 59:
        return None
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def _clean_reminder_text(text):
    cleaned = text or ""
    cleaned = re.sub(
        r"\b\d+(?:\.\d+)?\s*(second|seconds|sec|minute|minutes|min|hour|hours|hr|ghanta|ghante)\s*(baad|bad|later)?\b",
        "", cleaned, flags=re.I
    )
    cleaned = re.sub(
        r"\b\d{1,2}(?::\d{2})?\s*(am|pm)\s*(par|pe|at)?\b",
        "", cleaned, flags=re.I
    )
    cleaned = re.sub(
        r"\b(yaad dilana|remind me|reminder|set karo|lagao)\b",
        "", cleaned, flags=re.I
    )
    return " ".join(cleaned.split()).strip(" ,.-") or "Reminder"


def _add_reminder(kind, when, message):
    items = _load_reminders()
    items.append({
        "id": int(time.time() * 1000),
        "kind": kind,
        "when": when.isoformat(),
        "message": message,
        "done": False
    })
    _save_reminders(items)


def set_luna_timer(text):
    seconds = _duration_seconds(text)
    if not seconds or seconds <= 0:
        return "Timer duration samajh nahi aayi."
    when = datetime.now() + timedelta(seconds=seconds)
    _add_reminder("timer", when, "Timer complete")
    return f"Timer {text} ke liye set kar diya."


def set_luna_reminder(text):
    seconds = _duration_seconds(text)
    when = datetime.now() + timedelta(seconds=seconds) if seconds else _parse_exact_time(text)
    if when is None:
        return "Reminder ka time samajh nahi aaya. Jaise: 20 minute baad ya 8 PM par."
    message = _clean_reminder_text(text)
    _add_reminder("reminder", when, message)
    return f"Reminder set kar diya: {message}, {when.strftime('%d %b %Y %I:%M %p')}."


def list_luna_reminders():
    now = datetime.now()
    items = []
    for item in _load_reminders():
        try:
            when = datetime.fromisoformat(item["when"])
        except Exception:
            continue
        if not item.get("done", False) and when >= now:
            items.append(item)
    if not items:
        return "Koi pending reminder nahi hai."
    items.sort(key=lambda x: x["when"])
    parts = []
    for item in items[:8]:
        when = datetime.fromisoformat(item["when"])
        parts.append(f"{item['message']} at {when.strftime('%d %b %I:%M %p')}")
    return "Pending reminders: " + "; ".join(parts)


def cancel_luna_reminders():
    items = _load_reminders()
    count = 0
    for item in items:
        if not item.get("done", False):
            item["done"] = True
            count += 1
    _save_reminders(items)
    return f"{count} pending reminder cancel kar diye." if count else "Koi pending reminder nahi tha."


def get_due_reminders():
    now = datetime.now()
    items = _load_reminders()
    due = []
    changed = False
    for item in items:
        if item.get("done", False):
            continue
        try:
            when = datetime.fromisoformat(item["when"])
        except Exception:
            continue
        if when <= now:
            item["done"] = True
            due.append(item)
            changed = True
    if changed:
        _save_reminders(items)
    return due


def execute_action(command):
    action, query = understand_action(command)
    print("Detected action:", action)

    if query:
        print("Search query:", query)

    if action == "OPEN_CHROME":
        os.system("start chrome")
        return "Chrome khol diya."

    elif action == "OPEN_NOTEPAD":
        os.system("start notepad")
        return "Notepad khol diya."

    elif action == "OPEN_CALCULATOR":
        os.system("start calc")
        return "Calculator khol diya."

    elif action == "OPEN_EXPLORER":
        os.system("start explorer")
        return "File Explorer khol diya."

    elif action == "OPEN_GOOGLE":
        webbrowser.open("https://www.google.com")
        return "Google khol diya."

    elif action == "OPEN_YOUTUBE":
        webbrowser.open("https://www.youtube.com")
        return "YouTube khol diya."

    elif action == "GOOGLE_SEARCH":
        if not query:
            return "Kya search karna hai?"
        encoded_query = urllib.parse.quote_plus(query)
        webbrowser.open("https://www.google.com/search?q=" + encoded_query)
        return f"Google par {query} search kar diya."

    elif action == "YOUTUBE_SEARCH":
        if not query:
            return "YouTube par kya search karna hai?"
        encoded_query = urllib.parse.quote_plus(query)
        webbrowser.open(
            "https://www.youtube.com/results?search_query=" + encoded_query
        )
        return f"YouTube par {query} search kar diya."

    elif action == "CLOSE_CHROME":
        os.system("taskkill /IM chrome.exe /F >nul 2>&1")
        return "Chrome band kar diya."

    elif action == "CLOSE_NOTEPAD":
        os.system("taskkill /IM notepad.exe /F >nul 2>&1")
        return "Notepad band kar diya."

    elif action == "CLOSE_CALCULATOR":
        os.system("taskkill /IM CalculatorApp.exe /F >nul 2>&1")
        os.system("taskkill /IM calc.exe /F >nul 2>&1")
        return "Calculator band kar diya."

    elif action == "CLOSE_EXPLORER":
        pyautogui.hotkey("alt", "f4")
        return "Active File Explorer window band kar diya."

    elif action == "VOLUME_UP":
        _press_media_key("volumeup", presses=3)
        return "Volume badha diya."

    elif action == "VOLUME_DOWN":
        _press_media_key("volumedown", presses=3)
        return "Volume kam kar diya."

    elif action == "VOLUME_MUTE":
        _press_media_key("volumemute")
        return "Mute toggle kar diya."

    elif action == "TAKE_SCREENSHOT":
        folder = _screenshot_folder()
        filename = "Luna_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        path = os.path.join(folder, filename)
        pyautogui.screenshot().save(path)
        return "Screenshot save kar diya: " + path

    elif action == "WINDOW_MINIMIZE":
        pyautogui.hotkey("win", "down")
        return "Active window minimize kar diya."

    elif action == "WINDOW_MAXIMIZE":
        pyautogui.hotkey("win", "up")
        return "Active window maximize kar diya."

    elif action == "WINDOW_RESTORE":
        pyautogui.hotkey("win", "down")
        return "Active window restore kar diya."

    elif action == "GET_BATTERY":
        return get_battery_info()

    elif action == "GET_RAM":
        return get_ram_info()

    elif action == "GET_CPU":
        return get_cpu_info()

    elif action == "GET_DISK":
        return get_disk_info()

    elif action == "GET_SYSTEM_INFO":
        return get_system_info()

    elif action == "OPEN_DESKTOP":
        return open_common_folder("Desktop")

    elif action == "OPEN_DOWNLOADS":
        return open_common_folder("Downloads")

    elif action == "OPEN_DOCUMENTS":
        return open_common_folder("Documents")

    elif action == "OPEN_PICTURES":
        return open_common_folder("Pictures")

    elif action == "OPEN_FOLDER":
        if not query:
            return "Kaunsa folder kholna hai?"
        return open_named_folder(query)

    elif action == "FIND_FILE":
        if not query:
            return "Kaunsi file dhundni hai?"
        return find_file(query)

    elif action == "FIND_FOLDER":
        if not query:
            return "Kaunsa folder dhundna hai?"
        return find_folder(query)

    elif action == "FIND_FILE_TYPE":
        if not query:
            return "Kaunsi file type dhundni hai?"
        return find_file_type(query)

    elif action == "OPEN_APP":
        if not query:
            return "Kaunsa app kholna hai?"
        return smart_open_app(query)

    elif action == "CLOSE_APP":
        if not query:
            return "Kaunsa app band karna hai?"
        return smart_close_app(query)

    elif action == "FIND_APP":
        if not query:
            return "Kaunsa app check karna hai?"
        return find_installed_app(query)

    elif action == "LIST_APPS":
        return list_installed_apps()

    # ========================================
    # V9 - WINDOW & DESKTOP CONTROL
    # ========================================

    elif action == "ACTIVE_WINDOW_CLOSE":
        pyautogui.hotkey("alt", "f4")
        return "Active window close command de diya."

    elif action == "SHOW_DESKTOP":
        pyautogui.hotkey("win", "d")
        return "Desktop dikha diya."

    elif action == "WINDOW_SNAP_LEFT":
        pyautogui.hotkey("win", "left")
        return "Active window left side snap kar diya."

    elif action == "WINDOW_SNAP_RIGHT":
        pyautogui.hotkey("win", "right")
        return "Active window right side snap kar diya."

    elif action == "SWITCH_WINDOW":
        pyautogui.hotkey("alt", "tab")
        return "Next window par switch kar diya."

    elif action == "SCROLL_UP":
        pyautogui.scroll(6)
        return "Upar scroll kar diya."

    elif action == "SCROLL_DOWN":
        pyautogui.scroll(-6)
        return "Neeche scroll kar diya."

    elif action == "MOUSE_CLICK":
        pyautogui.click()
        return "Click kar diya."

    elif action == "MOUSE_DOUBLE_CLICK":
        pyautogui.doubleClick(interval=0.12)
        return "Double click kar diya."

    elif action == "MOUSE_RIGHT_CLICK":
        pyautogui.rightClick()
        return "Right click kar diya."

    elif action == "COPY":
        pyautogui.hotkey("ctrl", "c")
        return "Copy kar diya."

    elif action == "PASTE":
        pyautogui.hotkey("ctrl", "v")
        return "Paste kar diya."

    elif action == "SELECT_ALL":
        pyautogui.hotkey("ctrl", "a")
        return "Select all kar diya."

    elif action == "UNDO":
        pyautogui.hotkey("ctrl", "z")
        return "Undo kar diya."

    elif action == "REDO":
        pyautogui.hotkey("ctrl", "y")
        return "Redo kar diya."

    # ========================================
    # V10 - CLIPBOARD & SMART TYPING
    # ========================================

    elif action == "TYPE_TEXT":
        return smart_type_text(query)

    elif action == "COPY_TEXT":
        return copy_given_text(query)

    elif action == "READ_CLIPBOARD":
        return read_clipboard_text()

    elif action == "CLEAR_CLIPBOARD":
        return clear_clipboard_text()

    elif action == "PRESS_ENTER":
        pyautogui.press("enter")
        return "Enter daba diya."

    elif action == "PRESS_BACKSPACE":
        pyautogui.press("backspace")
        return "Backspace daba diya."

    elif action == "PRESS_DELETE":
        pyautogui.press("delete")
        return "Delete daba diya."

    elif action == "PRESS_TAB":
        pyautogui.press("tab")
        return "Tab daba diya."

    elif action == "PRESS_ESCAPE":
        pyautogui.press("esc")
        return "Escape daba diya."

    elif action == "PRESS_SPACE":
        pyautogui.press("space")
        return "Space daba diya."

    elif action == "GET_TIME":
        return "Abhi " + datetime.now().strftime("%I:%M %p") + " ho rahe hain."

    elif action == "GET_DATE":
        return "Aaj " + datetime.now().strftime("%A, %d %B %Y") + " hai."

    elif action == "SET_TIMER":
        return set_luna_timer(query)

    elif action == "SET_REMINDER":
        return set_luna_reminder(query)

    elif action == "LIST_REMINDERS":
        return list_luna_reminders()

    elif action == "CANCEL_REMINDERS":
        return cancel_luna_reminders()

    return None
