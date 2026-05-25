import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".md_yomikakikun"
CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULTS: dict = {
    "theme": "system",          # "light" | "dark" | "system"
    "font_family": "Consolas",
    "font_size": 14,
    "auto_save": True,
    "auto_save_interval": 2000,  # ms of inactivity before save
    "sync_scroll": False,
    "word_wrap": True,
    "toc_visible": True,
    "last_directory": str(Path.home()),
    "recent_files": [],
    "shortcuts": {
        "save":            "Ctrl+S",
        "new":             "Ctrl+N",
        "open":            "Ctrl+O",
        "find":            "Ctrl+F",
        "bold":            "Ctrl+B",
        "italic":          "Ctrl+I",
        "toggle_preview":  "Ctrl+Shift+P",
        "toggle_sidebar":  "Ctrl+Shift+E",
        "export_html":     "Ctrl+Shift+H",
        "export_pdf":      "Ctrl+Shift+X",
        "insert_link":     "Ctrl+K",
        "insert_image":    "Ctrl+Shift+I",
    },
    "window": {
        "width": 1400,
        "height": 900,
        "maximized": False,
        "splitter_sidebar": 220,
        "splitter_editor": 550,
    },
}


class Settings:
    def __init__(self) -> None:
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data = _deep_merge(DEFAULTS.copy(), loaded)
                return
            except (json.JSONDecodeError, OSError):
                pass
        self._data = _deep_merge({}, DEFAULTS)

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        parts = key.split(".")
        val = self._data
        for p in parts:
            if not isinstance(val, dict):
                return default
            val = val.get(p)
        return val if val is not None else default

    def set(self, key: str, value) -> None:
        parts = key.split(".")
        d = self._data
        for p in parts[:-1]:
            d = d.setdefault(p, {})
        d[parts[-1]] = value
        self.save()

    def add_recent(self, path: str) -> None:
        recent: list = self.get("recent_files", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.set("recent_files", recent[:20])


def _deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base
