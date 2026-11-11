"""FIFA 14 (PS4, CUSA00128) - PC installer and launcher wrapper for shadPS4.

The same executable works in two modes:
  * Installer: when it is NOT inside an installed folder. Extracts the user's own PKG files
    (or copies an already extracted folder), sets up a portable shadPS4 and creates a shortcut.
  * Launcher: when fifa14_install.json sits next to it. Shows the options window (or starts the
    game directly) and runs the FIFA 14 fix build of shadPS4 with the settings it needs.

No game files are included: the user must provide their own dumped PKG files or game folder.
"""

import ctypes
import json
import locale
import os
import queue
import shutil
import struct
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_VERSION = "1.0.0"
TITLE_ID = "CUSA00128"
GAME_NAME = "FIFA 14"
EXE_NAME = "FIFA14"
INSTALL_MARKER = "fifa14_install.json"
DEFAULT_INSTALL_DIR = r"C:\Games\FIFA 14"
REQUIRED_SPACE = 11_000_000_000
GAME_PATCH = "FIFA14-fix"
EMULATOR_LABEL = "shadPS4 FIFA 14 fix v4 (b72489d + patches)"
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

RESOLUTIONS = ["1280x720", "1600x900", "1920x1080", "2560x1440", "3840x2160"]
# PS4 system language ids
GAME_LANGUAGES = [
    ("English", 1),
    ("Español (España)", 3),
    ("Español (Latinoamérica)", 20),
    ("Français", 2),
    ("Deutsch", 4),
    ("Italiano", 5),
    ("Português (Brasil)", 17),
    ("Русский", 8),
    ("日本語", 0),
]

STRINGS = {
    "en": {
        "installer_title": "FIFA 14 - PC Installer",
        "launcher_title": "FIFA 14 - Launcher",
        "subtitle": "PS4 version (EUR, update 01.06) running on shadPS4, with the FIFA 14 fixes",
        "install_dir": "Install folder",
        "browse": "Browse...",
        "source": "Game source",
        "src_pkg": "PKG files",
        "src_folder": "Extracted folder",
        "base_pkg": "Base game PKG (required)",
        "update_pkg": "Update PKG 01.06 (strongly recommended)",
        "base_folder": "Game folder CUSA00128 (required)",
        "update_folder": "Update folder CUSA00128-patch (strongly recommended)",
        "shortcut": "Create desktop shortcut",
        "st_fonts": "Copying system fonts...",
        "install": "Start installation",
        "installing": "Installing...",
        "done_title": "Installation complete",
        "done_msg": "FIFA 14 is installed. Do you want to play now?",
        "err_title": "Error",
        "err_no_base": "Select the base game ({0}).",
        "err_wrong_game": "This is not FIFA 14 EUR ({0}). Found: {1}",
        "err_not_base": "The selected base PKG is not a base game package.",
        "err_not_update": "The selected update PKG is not a game update package.",
        "err_space": "Not enough free space in {0}. About 11 GB are needed.",
        "err_folder": "No eboot.bin / param.sfo found. Select the CUSA00128 folder (or the folder that contains it).",
        "warn_no_update": "No update selected. The fixes and the 60 FPS patch were made for update 01.06; without it the 60 FPS patch does not work and the game may behave differently.\n\nContinue anyway?",
        "warn_exists": "{0} already contains an installation. The game files will be replaced (saves are kept).\n\nContinue?",
        "st_prepare": "Preparing folders...",
        "st_extract_base": "Extracting base game (this can take a few minutes)...",
        "st_extract_update": "Extracting update...",
        "st_copy_base": "Copying game files...",
        "st_copy_update": "Copying update files...",
        "st_emulator": "Setting up shadPS4...",
        "st_shortcut": "Creating shortcut...",
        "st_done": "Done.",
        "fullscreen": "Fullscreen",
        "resolution": "Window resolution",
        "show_fps": "Show FPS counter",
        "fps_patch": "60 FPS in replays and cutscenes (needs update 01.06)",
        "gamma": "Brightness (gamma, 1.0 = default)",
        "game_language": "Game language",
        "direct": "Launch directly next time (hold Shift to open this window again)",
        "play": "PLAY",
        "open_saves": "Saves folder",
        "open_folder": "Install folder",
        "err_missing": "The installation is incomplete ({0} not found). Run the installer again.",
        "notice": "No game files are included. You must use your own legally dumped PKG files.",
    },
    "es": {
        "installer_title": "FIFA 14 - Instalador para PC",
        "launcher_title": "FIFA 14 - Launcher",
        "subtitle": "Versión de PS4 (EUR, actualización 01.06) en shadPS4, con los arreglos de FIFA 14",
        "install_dir": "Carpeta de instalación",
        "browse": "Examinar...",
        "source": "Origen del juego",
        "src_pkg": "Archivos PKG",
        "src_folder": "Carpeta ya extraída",
        "base_pkg": "PKG del juego base (obligatorio)",
        "update_pkg": "PKG de la actualización 01.06 (muy recomendado)",
        "base_folder": "Carpeta del juego CUSA00128 (obligatorio)",
        "update_folder": "Carpeta de la actualización CUSA00128-patch (muy recomendado)",
        "shortcut": "Crear acceso directo en el escritorio",
        "st_fonts": "Copiando las fuentes del sistema...",
        "install": "Instalar",
        "installing": "Instalando...",
        "done_title": "Instalación completada",
        "done_msg": "FIFA 14 está instalado. ¿Quieres jugar ahora?",
        "err_title": "Error",
        "err_no_base": "Elige el juego base ({0}).",
        "err_wrong_game": "Esto no es FIFA 14 EUR ({0}). Encontrado: {1}",
        "err_not_base": "El PKG base elegido no es un juego base.",
        "err_not_update": "El PKG de actualización elegido no es una actualización.",
        "err_space": "No hay espacio suficiente en {0}. Hacen falta unos 11 GB.",
        "err_folder": "No se encontró eboot.bin / param.sfo. Elige la carpeta CUSA00128 (o la carpeta que la contiene).",
        "warn_no_update": "No elegiste la actualización. Los arreglos y el parche de 60 FPS se hicieron para la 01.06; sin ella el parche de 60 FPS no funciona y el juego puede comportarse distinto.\n\n¿Continuar de todos modos?",
        "warn_exists": "{0} ya tiene una instalación. Se reemplazarán los archivos del juego (las partidas se conservan).\n\n¿Continuar?",
        "st_prepare": "Preparando carpetas...",
        "st_extract_base": "Extrayendo el juego base (puede tardar unos minutos)...",
        "st_extract_update": "Extrayendo la actualización...",
        "st_copy_base": "Copiando los archivos del juego...",
        "st_copy_update": "Copiando la actualización...",
        "st_emulator": "Configurando shadPS4...",
        "st_shortcut": "Creando el acceso directo...",
        "st_done": "Listo.",
        "fullscreen": "Pantalla completa",
        "resolution": "Resolución de la ventana",
        "show_fps": "Mostrar contador de FPS",
        "fps_patch": "60 FPS en repeticiones y cinemáticas (necesita la actualización 01.06)",
        "gamma": "Brillo (gamma, 1.0 = normal)",
        "game_language": "Idioma del juego",
        "direct": "Abrir el juego directamente la próxima vez (mantén Shift para volver a esta ventana)",
        "play": "JUGAR",
        "open_saves": "Partidas guardadas",
        "open_folder": "Carpeta de instalación",
        "err_missing": "La instalación está incompleta (no se encontró {0}). Vuelve a ejecutar el instalador.",
        "notice": "No incluye archivos del juego. Debes usar tus propios PKG extraídos legalmente.",
    },
}


def detect_language():
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if lang_id & 0x3FF == 0x0A:
            return "es"
    except Exception:
        pass
    try:
        if (locale.getlocale()[0] or "").lower().startswith(("es", "spanish")):
            return "es"
    except Exception:
        pass
    return "en"


LANG = detect_language()


def T(key, *args):
    text = STRINGS[LANG].get(key) or STRINGS["en"][key]
    return text.format(*args) if args else text


def default_game_language():
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        primary, sub = lang_id & 0x3FF, lang_id >> 10
        if primary == 0x0A:
            return 3 if sub in (1, 3) else 20
        return {0x0C: 2, 0x07: 4, 0x10: 5, 0x16: 17, 0x19: 8, 0x11: 0}.get(primary, 1)
    except Exception:
        return 1


def resource_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base.joinpath(*parts)


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def shift_held():
    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000)
    except Exception:
        return False


# ---------------------------------------------------------------- PS4 file helpers

def read_param_sfo(path):
    data = Path(path).read_bytes()
    if data[:4] != b"\x00PSF":
        raise ValueError("not a param.sfo")
    key_table, data_table, count = struct.unpack_from("<III", data, 8)
    values = {}
    for i in range(count):
        key_off, fmt, length, _max_len, data_off = struct.unpack_from("<HHIII", data, 20 + i * 16)
        end = data.index(b"\x00", key_table + key_off)
        key = data[key_table + key_off:end].decode("utf-8", "replace")
        raw = data[data_table + data_off:data_table + data_off + length]
        if fmt == 0x0404:
            values[key] = struct.unpack("<I", raw[:4])[0]
        else:
            values[key] = raw.rstrip(b"\x00").decode("utf-8", "replace")
    return values


def pkg_content_id(path):
    with open(path, "rb") as f:
        header = f.read(0x80)
    if header[:4] != b"\x7fCNT":
        raise ValueError("not a PS4 PKG")
    return header[0x40:0x64].rstrip(b"\x00").decode("ascii", "replace")


def find_game_folder(folder):
    folder = Path(folder)
    candidates = [folder, folder / TITLE_ID] + [p for p in folder.iterdir() if p.is_dir()] if folder.is_dir() else []
    for c in candidates:
        sfo = c / "sce_sys" / "param.sfo"
        if (c / "eboot.bin").exists() and sfo.exists():
            return c
    return None


def find_update_folder(base):
    base = Path(base)
    for suffix in ("-patch", "-UPDATE"):
        p = base.with_name(base.name + suffix)
        if (p / "sce_sys" / "param.sfo").exists():
            return p
    return None


def folder_title(folder):
    try:
        return read_param_sfo(Path(folder) / "sce_sys" / "param.sfo").get("TITLE_ID", "?")
    except Exception:
        return "?"


def run_hidden(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors="replace",
                          creationflags=CREATE_NO_WINDOW)


def extractor_path():
    return resource_path("payload", "extractor", "pkg_extractor.exe")


def pkg_type(path):
    result = run_hidden([str(extractor_path()), str(path), "--check-type"],
                        cwd=str(extractor_path().parent))
    return {101: "base", 102: "update", 103: "dlc"}.get(result.returncode, "unknown")


# ---------------------------------------------------------------- install layout

class Layout:
    def __init__(self, root):
        self.root = Path(root)
        self.emulator = self.root / "emulator"
        self.user = self.emulator / "user"
        self.game = self.root / "game"
        self.base = self.game / TITLE_ID
        self.update = self.game / f"{TITLE_ID}-patch"
        self.eboot = self.base / "eboot.bin"
        self.exe = self.emulator / "shadPS4.exe"
        self.marker = self.root / INSTALL_MARKER
        self.saves = self.user / "home" / "1000" / "savedata"
        self.icon = self.root / f"{EXE_NAME}.ico"
        self.launcher = self.root / f"{EXE_NAME}.exe"
        self.game_patch = self.user / "patches" / GAME_PATCH
        self.imgui_ini = self.user / "imgui.ini"


DEFAULT_SETTINGS = {
    "fullscreen": False,
    "resolution": "1920x1080",
    "show_fps": False,
    "direct": False,
    "game_language": None,
    "fps_patch": True,
    "gamma": 1.0,
}


def load_settings(layout):
    settings = dict(DEFAULT_SETTINGS)
    try:
        settings.update(json.loads(layout.marker.read_text(encoding="utf-8")).get("settings", {}))
    except Exception:
        pass
    if settings["game_language"] is None:
        settings["game_language"] = default_game_language()
    return settings


def save_settings(layout, settings):
    data = {"app": GAME_NAME, "title_id": TITLE_ID, "version": APP_VERSION, "settings": settings}
    layout.marker.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_game_config(layout, settings):
    width, height = (int(v) for v in settings["resolution"].split("x"))
    config = {
        "GPU": {
            # Relaxed readbacks + linear image readbacks: FIFA 14 reads GPU-rendered textures
            # (pitch grass, jersey names) back on the CPU.
            "readbacks_mode": 1,
            "readback_linear_images_enabled": True,
            "direct_memory_access_enabled": False,
            "copy_gpu_buffers": False,
            "full_screen": bool(settings["fullscreen"]),
            "full_screen_mode": "Fullscreen (Borderless)" if settings["fullscreen"] else "Windowed",
            "window_width": width,
            "window_height": height,
        },
        "General": {
            "show_fps_counter": bool(settings["show_fps"]),
            "console_language": int(settings["game_language"]),
            "show_splash": False,
            "neo_mode": False,
        },
        "Log": {"filter": "*:Error Kernel.Fs:Critical Lib.NpParty:Critical Lib.GnmDriver:Critical",
                "sync": False},
        "Vulkan": {"pipeline_cache_enabled": True},
    }
    path = layout.user / "custom_configs" / f"{TITLE_ID}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=4), encoding="utf-8")
    apply_game_patch(layout, settings["fps_patch"])
    apply_gamma(layout, settings["gamma"])


def apply_game_patch(layout, enabled):
    """Installs or removes the 60 FPS replays/cutscenes game patch (applied in memory by shadPS4)."""
    if enabled:
        layout.game_patch.mkdir(parents=True, exist_ok=True)
        for f in resource_path("payload", "game_patch", GAME_PATCH).iterdir():
            shutil.copy2(f, layout.game_patch / f.name)
    elif layout.game_patch.exists():
        shutil.rmtree(layout.game_patch, ignore_errors=True)


def apply_gamma(layout, gamma):
    """Writes the post-processing gamma that the FIFA 14 fix build reads from imgui.ini."""
    line = "pp_gamma=%f" % max(0.5, min(2.0, float(gamma)))
    section = "[DevtoolsLayer][Data]"
    try:
        lines = layout.imgui_ini.read_text(encoding="utf-8").splitlines()
    except Exception:
        lines = []
    if section not in lines:
        lines = [section, line, ""] + lines
    else:
        start = lines.index(section) + 1
        end = start
        while end < len(lines) and lines[end].strip() and not lines[end].startswith("["):
            end += 1
        body = [l for l in lines[start:end] if not l.startswith("pp_gamma=")]
        lines[start:end] = [line] + body
    layout.imgui_ini.parent.mkdir(parents=True, exist_ok=True)
    layout.imgui_ini.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_user_dir(layout):
    for d in ("custom_configs", "home/1000/savedata", "home/1000/trophy", "home/1000/inputs"):
        (layout.user / d).mkdir(parents=True, exist_ok=True)


def find_fonts_folder(folder):
    folder = Path(folder)
    for c in (folder, folder / "fonts", folder.parent):
        if (c / "font").is_dir() and (c / "font2").is_dir():
            return c
    return None


def detect_fonts_folder():
    """Looks for PS4 system fonts the user already has in an existing shadPS4 setup."""
    candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "shadPS4" / "fonts")
        launcher_versions = Path(appdata) / "shadPS4QtLauncher" / "versions"
        if launcher_versions.is_dir():
            candidates += [v / "user" / "fonts" for v in launcher_versions.iterdir() if v.is_dir()]
    for c in candidates:
        try:
            found = find_fonts_folder(c)
            if found and any((found / "font").iterdir()) and any((found / "font2").iterdir()):
                return found
        except Exception:
            continue
    return None


def copy_tree(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def make_icon(layout):
    try:
        from PIL import Image
        src = layout.base / "sce_sys" / "icon0.png"
        if src.exists():
            Image.open(src).convert("RGBA").save(layout.icon, sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
            return layout.icon
    except Exception:
        pass
    return None


def create_shortcut(layout, icon):
    desktop = Path(os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"))
    try:
        result = run_hidden(["powershell", "-NoProfile", "-Command",
                             "[Environment]::GetFolderPath('Desktop')"])
        if result.stdout.strip():
            desktop = Path(result.stdout.strip())
    except Exception:
        pass
    lnk = desktop / f"{GAME_NAME}.lnk"
    icon_location = str(icon if icon else layout.launcher)
    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:FIFA14_LNK);"
        "$s.TargetPath=$env:FIFA14_TARGET;$s.WorkingDirectory=$env:FIFA14_DIR;"
        "$s.IconLocation=$env:FIFA14_ICON;$s.Description='FIFA 14 (PS4) on shadPS4';$s.Save()"
    )
    env = dict(os.environ, FIFA14_LNK=str(lnk), FIFA14_TARGET=str(layout.launcher),
               FIFA14_DIR=str(layout.root), FIFA14_ICON=icon_location)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                   env=env, capture_output=True, creationflags=CREATE_NO_WINDOW)


def launch_game(layout, settings):
    for needed in (layout.exe, layout.eboot):
        if not needed.exists():
            messagebox.showerror(T("err_title"), T("err_missing", needed))
            return False
    prepare_user_dir(layout)
    write_game_config(layout, settings)
    args = [str(layout.exe), "-g", str(layout.eboot)]
    if settings["fullscreen"]:
        args += ["--fullscreen", "true"]
    subprocess.Popen(args, cwd=str(layout.emulator), env=clean_child_env(),
                     creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS, close_fds=True)
    return True


def clean_child_env():
    """Keeps the emulator from loading DLLs out of PyInstaller's temporary folder, which would
    otherwise stay locked and trigger 'Failed to remove temporary directory' on exit."""
    if not getattr(sys, "frozen", False):
        return None
    try:
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    except Exception:
        pass
    meipass = str(getattr(sys, "_MEIPASS", "")).lower()
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("_MEI", "_PYI"))}
    for key in ("TCL_LIBRARY", "TK_LIBRARY"):
        env.pop(key, None)
    if meipass and "PATH" in env:
        env["PATH"] = os.pathsep.join(p for p in env["PATH"].split(os.pathsep)
                                      if p and not p.lower().startswith(meipass))
    return env


# ---------------------------------------------------------------- UI helpers

BG = "#14161c"
PANEL = "#1d2029"
FG = "#e8e8ec"
MUTED = "#9aa0ac"
ACCENT = "#3ec46d"


def style_root(root, title):
    root.title(title)
    root.configure(bg=BG)
    root.resizable(False, False)
    try:
        root.iconbitmap(str(resource_path("assets", "app.ico")))
    except Exception:
        pass
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, font=("Segoe UI", 10))
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("Muted.TLabel", foreground=MUTED, font=("Segoe UI", 9))
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 24), foreground=ACCENT)
    style.configure("TCheckbutton", background=BG, foreground=FG)
    style.map("TCheckbutton", background=[("active", BG)])
    style.configure("TRadiobutton", background=BG, foreground=FG)
    style.map("TRadiobutton", background=[("active", BG)])
    style.configure("TEntry", fieldbackground=PANEL, foreground=FG, insertcolor=FG)
    style.configure("TCombobox", fieldbackground=PANEL, foreground=FG, background=PANEL, arrowcolor=FG)
    style.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)])
    style.configure("TButton", background=PANEL, foreground=FG, padding=6)
    style.map("TButton", background=[("active", "#2a2e3a")])
    style.configure("Accent.TButton", background=ACCENT, foreground="#04210f",
                    font=("Segoe UI Semibold", 12), padding=10)
    style.map("Accent.TButton", background=[("active", "#55d982"), ("disabled", "#2a4a35")])
    style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=PANEL)
    root.option_add("*TCombobox*Listbox.background", PANEL)
    root.option_add("*TCombobox*Listbox.foreground", FG)


def header(parent, subtitle):
    frame = ttk.Frame(parent, style="TFrame")
    ttk.Label(frame, text=subtitle, style="Muted.TLabel").pack(anchor="w")
    return frame


BANNER_RATIO = 480 / 1280


def add_banner(root, below, sources, fade=False):
    """Shows the first existing image of `sources` as a banner above `below`, sized to the window."""
    try:
        from PIL import Image, ImageDraw, ImageTk
        image = None
        for src in sources:
            if src and Path(src).exists():
                image = Image.open(src).convert("RGB")
                break
        if image is None:
            return
        root.update_idletasks()
        width = max(below.winfo_reqwidth(), 480)
        height = int(width * BANNER_RATIO)
        w, h = image.size
        crop_h = int(w * BANNER_RATIO)
        if crop_h <= h:
            top = (h - crop_h) // 2
            image = image.crop((0, top, w, top + crop_h))
        image = image.resize((width, height), Image.LANCZOS)
        if fade:
            bg = tuple(int(BG[i:i + 2], 16) for i in (1, 3, 5))
            mask = Image.new("L", image.size)
            draw = ImageDraw.Draw(mask)
            for y in range(height):
                t = max(0.0, (y - height * 0.6) / (height * 0.4))
                draw.line([(0, y), (width, y)], fill=int(255 * t ** 1.6))
            image = Image.composite(Image.new("RGB", image.size, bg), image, mask)
        photo = ImageTk.PhotoImage(image)
        label = tk.Label(root, image=photo, bd=0, highlightthickness=0, bg=BG)
        label.image = photo
        label.pack(side="top", fill="x", before=below)
    except Exception:
        pass


def path_row(parent, label, var, command):
    ttk.Label(parent, text=label).pack(anchor="w", pady=(8, 2))
    row = ttk.Frame(parent)
    row.pack(fill="x")
    ttk.Entry(row, textvariable=var, width=62).pack(side="left", fill="x", expand=True)
    ttk.Button(row, text=T("browse"), command=command).pack(side="left", padx=(6, 0))


# ---------------------------------------------------------------- installer

class Installer:
    def __init__(self, root):
        self.root = root
        style_root(root, T("installer_title"))
        ttk.Style(root).configure("TFrame", background=BG)
        main = ttk.Frame(root, padding=20)
        main.pack(fill="both", expand=True)
        header(main, T("subtitle")).pack(fill="x", pady=(0, 6))

        self.install_dir = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        path_row(main, T("install_dir"), self.install_dir, self.pick_install_dir)

        ttk.Label(main, text=T("source")).pack(anchor="w", pady=(14, 2))
        self.mode = tk.StringVar(value="pkg")
        modes = ttk.Frame(main)
        modes.pack(anchor="w")
        ttk.Radiobutton(modes, text=T("src_pkg"), value="pkg", variable=self.mode,
                        command=self.refresh_mode).pack(side="left")
        ttk.Radiobutton(modes, text=T("src_folder"), value="folder", variable=self.mode,
                        command=self.refresh_mode).pack(side="left", padx=(16, 0))

        self.base = tk.StringVar()
        self.update = tk.StringVar()
        self.source_frame = ttk.Frame(main)
        self.source_frame.pack(fill="x")
        self.refresh_mode()

        self.shortcut = tk.BooleanVar(value=True)
        ttk.Checkbutton(main, text=T("shortcut"), variable=self.shortcut).pack(anchor="w", pady=(14, 0))

        self.status = tk.StringVar(value="")
        self.progress_slot = ttk.Frame(main, height=12)
        self.progress_slot.pack(fill="x", pady=(16, 4))
        self.progress = ttk.Progressbar(self.progress_slot, mode="indeterminate", length=520)
        ttk.Label(main, textvariable=self.status, style="Muted.TLabel").pack(anchor="w")

        self.button = ttk.Button(main, text=T("install"), style="Accent.TButton", command=self.start)
        self.button.pack(fill="x", pady=(12, 6))
        ttk.Label(main, text=T("notice"), style="Muted.TLabel").pack(anchor="w")
        ttk.Label(main, text=f"v{APP_VERSION}", style="Muted.TLabel").pack(anchor="e")
        self.events = queue.Queue()
        add_banner(root, main, [resource_path("assets", "banner.png")])

    def refresh_mode(self):
        for child in self.source_frame.winfo_children():
            child.destroy()
        self.base.set("")
        self.update.set("")
        if self.mode.get() == "pkg":
            path_row(self.source_frame, T("base_pkg"), self.base, lambda: self.pick_pkg(self.base))
            path_row(self.source_frame, T("update_pkg"), self.update, lambda: self.pick_pkg(self.update))
        else:
            path_row(self.source_frame, T("base_folder"), self.base, self.pick_base_folder)
            path_row(self.source_frame, T("update_folder"), self.update, lambda: self.pick_folder(self.update))

    def pick_install_dir(self):
        d = filedialog.askdirectory(initialdir=self.install_dir.get() or "C:\\")
        if d:
            p = Path(d)
            self.install_dir.set(str(p if p.name.lower() == GAME_NAME.lower() else p / GAME_NAME))

    def pick_pkg(self, var):
        f = filedialog.askopenfilename(filetypes=[("PS4 PKG", "*.pkg"), ("*", "*.*")])
        if f:
            var.set(str(Path(f)))

    def pick_folder(self, var):
        d = filedialog.askdirectory()
        if d:
            var.set(str(Path(d)))

    def pick_base_folder(self):
        d = filedialog.askdirectory()
        if not d:
            return
        game = find_game_folder(d)
        self.base.set(str(game or Path(d)))
        if game and not self.update.get():
            upd = find_update_folder(game)
            if upd:
                self.update.set(str(upd))

    def validate(self):
        base, update = self.base.get().strip(), self.update.get().strip()

        if not base:
            raise ValueError(T("err_no_base", TITLE_ID))
        if self.mode.get() == "pkg":
            cid = pkg_content_id(base)
            if TITLE_ID not in cid:
                raise ValueError(T("err_wrong_game", TITLE_ID, cid))
            if pkg_type(base) != "base":
                raise ValueError(T("err_not_base"))
            if update:
                cid = pkg_content_id(update)
                if TITLE_ID not in cid:
                    raise ValueError(T("err_wrong_game", TITLE_ID, cid))
                if pkg_type(update) != "update":
                    raise ValueError(T("err_not_update"))
            return Path(base), Path(update) if update else None
        game = find_game_folder(base)
        if not game:
            raise ValueError(T("err_folder"))
        title = folder_title(game)
        if title != TITLE_ID:
            raise ValueError(T("err_wrong_game", TITLE_ID, title))
        upd = Path(update) if update else None
        if upd:
            if not (upd / "sce_sys" / "param.sfo").exists():
                found = find_game_folder(upd)
                upd = found
            if not upd or folder_title(upd) != TITLE_ID:
                raise ValueError(T("err_wrong_game", TITLE_ID, folder_title(upd) if upd else "?"))
        return game, upd

    def start(self):
        try:
            base, update = self.validate()
        except Exception as e:
            messagebox.showerror(T("err_title"), str(e))
            return
        if not update and not messagebox.askyesno(GAME_NAME, T("warn_no_update")):
            return
        layout = Layout(self.install_dir.get().strip() or DEFAULT_INSTALL_DIR)
        if layout.marker.exists() and not messagebox.askyesno(GAME_NAME, T("warn_exists", layout.root)):
            return
        try:
            layout.root.mkdir(parents=True, exist_ok=True)
            if shutil.disk_usage(layout.root).free < REQUIRED_SPACE:
                raise ValueError(T("err_space", layout.root))
        except Exception as e:
            messagebox.showerror(T("err_title"), str(e))
            return
        self.button.configure(state="disabled", text=T("installing"))
        self.progress.pack(fill="x")
        self.progress.start(12)
        threading.Thread(target=self.worker, args=(layout, base, update, self.mode.get(),
                                                   self.shortcut.get()), daemon=True).start()
        self.root.after(200, self.poll)

    def worker(self, layout, base, update, mode, shortcut):
        try:
            self.events.put(("status", T("st_prepare")))
            for old in (layout.base, layout.update):
                if old.exists():
                    shutil.rmtree(old)
            layout.game.mkdir(parents=True, exist_ok=True)
            prepare_user_dir(layout)
            if mode == "pkg":
                self.events.put(("status", T("st_extract_base")))
                self.extract(base, layout.game)
                if update:
                    self.events.put(("status", T("st_extract_update")))
                    self.extract(update, layout.game)
            else:
                self.events.put(("status", T("st_copy_base")))
                copy_tree(base, layout.base)
                if update:
                    self.events.put(("status", T("st_copy_update")))
                    copy_tree(update, layout.update)
            if not layout.eboot.exists():
                raise RuntimeError(T("err_missing", layout.eboot))
            fonts_dir = detect_fonts_folder()
            if fonts_dir and fonts_dir.resolve() != (layout.user / "fonts").resolve():
                self.events.put(("status", T("st_fonts")))
                for sub in ("font", "font2"):
                    copy_tree(fonts_dir / sub, layout.user / "fonts" / sub)

            self.events.put(("status", T("st_emulator")))
            layout.emulator.mkdir(parents=True, exist_ok=True)
            # Shaders cached by an older emulator build would keep the old (buggy) translation.
            shutil.rmtree(layout.user / "cache" / TITLE_ID, ignore_errors=True)
            shutil.copy2(resource_path("payload", "emulator", "shadPS4.exe"), layout.exe)
            licenses = layout.root / "licenses"
            if licenses.exists():
                shutil.rmtree(licenses)
            shutil.copytree(resource_path("payload", "licenses"), licenses)
            if getattr(sys, "frozen", False) and Path(sys.executable).resolve() != layout.launcher.resolve():
                shutil.copy2(sys.executable, layout.launcher)
            settings = load_settings(layout)
            save_settings(layout, settings)
            write_game_config(layout, settings)
            icon = make_icon(layout)
            if shortcut:
                self.events.put(("status", T("st_shortcut")))
                create_shortcut(layout, icon)
            self.events.put(("done", layout))
        except Exception as e:
            self.events.put(("error", str(e)))

    def extract(self, pkg, dest):
        result = run_hidden([str(extractor_path()), str(pkg), str(dest)], cwd=str(extractor_path().parent))
        if result.returncode != 0:
            tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-5:])
            raise RuntimeError(f"pkg_extractor failed ({result.returncode}):\n{tail}")

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    self.status.set(value)
                elif kind == "error":
                    self.progress.stop()
                    self.status.set("")
                    self.button.configure(state="normal", text=T("install"))
                    messagebox.showerror(T("err_title"), value)
                    return
                elif kind == "done":
                    self.progress.stop()
                    self.status.set(T("st_done"))
                    self.button.configure(text=T("st_done"))
                    if messagebox.askyesno(T("done_title"), T("done_msg")):
                        launch_game(value, load_settings(value))
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(200, self.poll)


# ---------------------------------------------------------------- launcher

class Launcher:
    def __init__(self, root, layout):
        self.root = root
        self.layout = layout
        self.settings = load_settings(layout)
        style_root(root, T("launcher_title"))
        ttk.Style(root).configure("TFrame", background=BG)
        main = ttk.Frame(root, padding=20)
        main.pack(fill="both", expand=True)
        header(main, T("subtitle")).pack(fill="x", pady=(0, 14))
        main.configure(width=520)

        self.fullscreen = tk.BooleanVar(value=self.settings["fullscreen"])
        self.show_fps = tk.BooleanVar(value=self.settings["show_fps"])
        self.direct = tk.BooleanVar(value=self.settings["direct"])
        self.resolution = tk.StringVar(value=self.settings["resolution"])
        self.fps_patch = tk.BooleanVar(value=self.settings["fps_patch"])
        self.gamma = tk.DoubleVar(value=float(self.settings["gamma"]))
        self.gamma_text = tk.StringVar(value="%.2f" % self.gamma.get())
        lang_names = [n for n, _ in GAME_LANGUAGES]
        current = next((n for n, v in GAME_LANGUAGES if v == self.settings["game_language"]), lang_names[0])
        self.game_language = tk.StringVar(value=current)

        ttk.Checkbutton(main, text=T("fullscreen"), variable=self.fullscreen).pack(anchor="w")
        row = ttk.Frame(main)
        row.pack(fill="x", pady=(10, 0))
        ttk.Label(row, text=T("resolution")).pack(side="left")
        ttk.Combobox(row, textvariable=self.resolution, values=RESOLUTIONS, state="readonly",
                     width=12).pack(side="right")
        row = ttk.Frame(main)
        row.pack(fill="x", pady=(10, 0))
        ttk.Label(row, text=T("game_language")).pack(side="left")
        ttk.Combobox(row, textvariable=self.game_language, values=lang_names, state="readonly",
                     width=24).pack(side="right")
        row = ttk.Frame(main)
        row.pack(fill="x", pady=(10, 0))
        ttk.Label(row, text=T("gamma")).pack(side="left")
        ttk.Label(row, textvariable=self.gamma_text, width=5).pack(side="right")
        ttk.Scale(row, from_=0.5, to=2.0, variable=self.gamma, length=160,
                  command=lambda v: self.gamma_text.set("%.2f" % float(v))).pack(side="right", padx=(0, 6))
        ttk.Checkbutton(main, text=T("fps_patch"), variable=self.fps_patch).pack(anchor="w", pady=(10, 0))
        ttk.Checkbutton(main, text=T("show_fps"), variable=self.show_fps).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(main, text=T("direct"), variable=self.direct).pack(anchor="w", pady=(6, 0))

        ttk.Button(main, text=T("play"), style="Accent.TButton", command=self.play).pack(fill="x", pady=(18, 8))
        row = ttk.Frame(main)
        row.pack(fill="x")
        ttk.Button(row, text=T("open_saves"), command=lambda: self.open(layout.saves)).pack(side="left", expand=True, fill="x")
        ttk.Button(row, text=T("open_folder"), command=lambda: self.open(layout.root)).pack(side="left", expand=True, fill="x", padx=(6, 0))
        ttk.Label(main, text=f"v{APP_VERSION}  ·  {EMULATOR_LABEL}", style="Muted.TLabel").pack(anchor="e", pady=(10, 0))
        user_logo = layout.base / "sce_sys" / "pic1.png"
        if user_logo.exists():
            add_banner(root, main, [user_logo], fade=True)
        else:
            add_banner(root, main, [resource_path("assets", "banner.png")])

    def collect(self):
        self.settings.update(
            fullscreen=self.fullscreen.get(),
            show_fps=self.show_fps.get(),
            direct=self.direct.get(),
            resolution=self.resolution.get(),
            fps_patch=self.fps_patch.get(),
            gamma=round(self.gamma.get(), 2),
            game_language=dict(GAME_LANGUAGES)[self.game_language.get()],
        )
        save_settings(self.layout, self.settings)

    def open(self, path):
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))

    def play(self):
        self.collect()
        if launch_game(self.layout, self.settings):
            self.root.destroy()


def main():
    here = app_dir()
    layout = Layout(here)
    if layout.marker.exists():
        settings = load_settings(layout)
        if settings["direct"] and not shift_held():
            root = tk.Tk()
            root.withdraw()
            launch_game(layout, settings)
            root.destroy()
            return
        root = tk.Tk()
        Launcher(root, layout)
    else:
        root = tk.Tk()
        Installer(root)
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
    root.mainloop()


if __name__ == "__main__":
    main()
