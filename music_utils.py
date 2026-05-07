import os
import random
from mutagen import File
from config import SUPPORTED_FORMATS


def validate_and_get_music_files(folder):
    if not os.path.isdir(folder):
        return []
    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(SUPPORTED_FORMATS)
    ]


def create_ordered_playlist(files, mode):
    files_copy = list(files)
    if mode == "random":
        random.shuffle(files_copy)
    else:
        # sequential and single_loop both use alphabetical sorting (without extension)
        files_copy.sort(key=lambda f: os.path.splitext(os.path.basename(f))[0].lower())
    return files_copy


def format_time(s):
    return f"{int(s//60):02d}:{int(s%60):02d}" if s >= 0 else "--:--"

def get_music_duration(file_path):
    try:
        audio = File(file_path)
        if audio and audio.info:
            return audio.info.length
    except Exception:
        pass
    return 0.0
