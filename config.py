import os
import json
import datetime

APP_DATA_FILE = os.path.join(os.path.expanduser("~"), "settings.json")
SCREEN_WIDTH = 660
SCREEN_HEIGHT = 580
TEXT_COLOR = (230, 230, 240)
BACKGROUND_COLOR = (18, 18, 28)
ACCENT_COLOR = (99, 102, 241)
ACCENT_COLOR_LIGHT = (129, 140, 248)
BUTTON_COLOR = (37, 37, 56)
BUTTON_HOVER_COLOR = (55, 55, 85)
BUTTON_TEXT_COLOR = (240, 240, 250)
DISABLED_BUTTON_COLOR = (28, 28, 38)
DISABLED_TEXT_COLOR = (100, 100, 110)
SLIDER_BAR_COLOR = (45, 45, 65)
SLIDER_THUMB_COLOR = ACCENT_COLOR
INPUT_BOX_COLOR = (28, 28, 42)
INPUT_BOX_TEXT_COLOR = (210, 210, 220)
INPUT_BOX_BORDER_COLOR = (55, 55, 75)
SECONDARY_TEXT_COLOR = (160, 160, 180)
PROGRESS_BAR_HEIGHT = 12
SLIDER_HEIGHT = 16
MIN_PROGRESS_BAR_PADDING = 45
FAST_FORWARD_REWIND_STEP = 10
SCROLL_DELAY_DURATION = 2000
SUPPORTED_FORMATS = (".flac", ".mp3", ".wav", ".ogg", ".m4a")


def get_datetime():
    today = datetime.datetime.now()
    return datetime.datetime(today.year, today.month, today.day, 0, 0, 0)


def get_timestr():
    return get_datetime().strftime("%Y%m%d%H%M")


def load_app_data():
    default_data = {
        "global_volume": 1.0,
        "last_active_folder": "",
        "next_new_playlist_mode": "random",
        "playlists": {},
        "phone_mappings": {},
    }
    try:
        with open(APP_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in default_data.items():
            data.setdefault(key, value)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data


def save_app_data(volume, active_folder, next_mode, playlists_data, phone_mappings):
    data = {
        "global_volume": volume,
        "last_active_folder": active_folder,
        "next_new_playlist_mode": next_mode,
        "playlists": playlists_data,
        "phone_mappings": phone_mappings,
    }
    try:
        with open(APP_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass
