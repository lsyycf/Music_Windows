import os
import sys
import subprocess
from progress_state import progress_manager

from concurrent.futures import ThreadPoolExecutor, as_completed
from config import SUPPORTED_FORMATS, get_timestr
from music_utils import validate_and_get_music_files

if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

MAX_WORKERS = 8


def convert_windows_path_to_adb(windows_path):
    path = windows_path.strip().strip('"').strip("'")
    path = path.replace('/', '\\')
    parts = [p.strip() for p in path.split('\\') if p.strip()]
    
    pc_names = ('此电脑', 'This PC', 'My Computer')
    if parts and parts[0] in pc_names:
        parts = parts[1:]

    internal_storage_names = (
        '内部共享存储空间',
        '内部存储',
        'Internal shared storage',
        'Internal storage',
        'Internal',
    )
    for index, part in enumerate(parts):
        if any(name in part for name in internal_storage_names):
            parts = parts[index + 1:]
            break

    base = '/sdcard'
    
    if parts:
        adb_path = base + '/' + '/'.join(parts)
    else:
        adb_path = base
    
    return adb_path


def is_adb_path(path):
    return path.startswith('/') and '\\' not in path


def check_adb_connection():
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        lines = result.stdout.strip().split('\n')
        devices = [line for line in lines[1:] if line.strip() and '\tdevice' in line]
        return len(devices) > 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


def list_phone_files(phone_path):
    try:
        result = subprocess.run(
            ["adb", "shell", f"ls -1 '{phone_path}'"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        if result.returncode == 0 and result.stdout:
            files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            music_files = [f for f in files if any(f.lower().endswith(ext) for ext in SUPPORTED_FORMATS)]
            return music_files
        return []
    except Exception:
        return []


def delete_phone_file(phone_path, filename):
    try:
        file_path = f"{phone_path}/{filename}"
        result = subprocess.run(
            ["adb", "shell", f"rm '{file_path}'"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        return result.returncode == 0
    except Exception:
        return False


def copy_file_to_phone(local_path, phone_folder_path):
    try:
        filename = os.path.basename(local_path)
        dest_path = f"{phone_folder_path}/{filename}"
        
        result = subprocess.run(
            ["adb", "push", local_path, dest_path],
            capture_output=True,
            text=False,
            timeout=120,
            creationflags=CREATE_NO_WINDOW
        )
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def touch_phone_file(phone_path, filename, time_str):
    try:
        file_path = f"{phone_path}/{filename}"
        result = subprocess.run(
            ["adb", "shell", f"touch -c -t {time_str} '{file_path}'"],
            capture_output=True, text=True, encoding='utf-8', errors='ignore',
            timeout=5, creationflags=CREATE_NO_WINDOW
        )
        return result.returncode
    except Exception:
        return False


def process_phone_music_metadata(phone_path):
    try:
        time_str = get_timestr()
        
        files = list_phone_files(phone_path)
        total = len(files)
        
        if total == 0:
            return True
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_filename = {
                executor.submit(touch_phone_file, phone_path, filename, time_str): filename
                for filename in files
            }
            # Add progress_manager for metadata scan on phone
            progress_manager.start(len(files), "正在刷新手机媒体库元数据")
            try:
                for future in as_completed(future_to_filename):
                    future.result()
                    progress_manager.update(1)
            finally:
                progress_manager.finish()

        
        result = subprocess.run(
            ["adb", "shell", f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{phone_path}"],
            capture_output=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False


def sync_phone_complete(music_folder, phone_path):
    try:
        pc_files = [os.path.basename(f) for f in validate_and_get_music_files(music_folder)]
        phone_files = list_phone_files(phone_path)
        
        pc_set = set(pc_files)
        phone_set = set(phone_files)
        
        to_delete = phone_set - pc_set
        to_upload = pc_set - phone_set
        
        if to_delete:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_filename = {
                    executor.submit(delete_phone_file, phone_path, filename): filename
                    for filename in to_delete
                }
                progress_manager.start(len(to_delete), "正在删除手机失效文件")
                try:
                    for future in as_completed(future_to_filename):
                        future.result()
                        progress_manager.update(1)
                finally:
                    progress_manager.finish()

        
        if to_upload:
            time_str = get_timestr()
            newly_pushed_files = []
            
            with ThreadPoolExecutor(max_workers=min(4, MAX_WORKERS)) as executor:
                future_to_filename = {
                    executor.submit(copy_file_to_phone, os.path.join(music_folder, filename), phone_path): filename
                    for filename in to_upload
                }
                progress_manager.start(len(to_upload), "正在上传新歌曲到手机")
                try:
                    for future in as_completed(future_to_filename):
                        filename = future_to_filename[future]
                        if future.result():
                            newly_pushed_files.append(filename)
                        progress_manager.update(1)
                finally:
                    progress_manager.finish()

            
            if newly_pushed_files:
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    future_to_filename = {
                        executor.submit(touch_phone_file, phone_path, filename, time_str): filename
                        for filename in newly_pushed_files
                    }
                    progress_manager.start(len(newly_pushed_files), "正在校准手机文件时间")
                    try:
                        for future in as_completed(future_to_filename):
                            future.result()
                            progress_manager.update(1)
                    finally:
                        progress_manager.finish()

        
        process_phone_music_metadata(phone_path)
        return True
        
    except Exception:
        return False
