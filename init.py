import os
import stat
import win32file
import pywintypes
from mutagen import File as MutagenFile
from config import SUPPORTED_FORMATS, get_datetime

def process_music_folder_three_steps(folder_path):
    if not os.path.isdir(folder_path):
        return

    music_files = [f for f in os.listdir(folder_path)
                   if f.lower().endswith(SUPPORTED_FORMATS)]

    if not music_files:
        return

    fields_to_delete = ['subtitle', 'description', 'albumartist', 'album', 'genre', 'tracknumber']
    target_time = get_datetime()
    win_time = pywintypes.Time(target_time)

    for filename in music_files:
        file_path = os.path.join(folder_path, filename)

        # 步骤 1 & 2：元数据清理与标准化 (合并循环)
        try:
            audio = MutagenFile(file_path, easy=True)
            if audio is not None:
                changed = False
                name_without_ext = os.path.splitext(filename)[0]

                # 解析 Artist - Title
                if '-' in name_without_ext:
                    parts = name_without_ext.rsplit('-', 1)
                    artist, title = parts[0].strip(), parts[1].strip()
                    if audio.get('artist') != [artist]:
                        audio['artist'] = artist
                        changed = True
                    if audio.get('title') != [title]:
                        audio['title'] = title
                        changed = True

                # 删除冗余字段
                for field in fields_to_delete:
                    if field in audio:
                        del audio[field]
                        changed = True

                if changed:
                    audio.save()
        except Exception:
            pass

        # 步骤 3：统一修改物理时间戳 (win32file)
        handle = None
        try:
            if not os.access(file_path, os.W_OK):
                os.chmod(file_path, stat.S_IWRITE)

            handle = win32file.CreateFile(
                file_path,
                win32file.GENERIC_WRITE,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None,
                win32file.OPEN_EXISTING,
                win32file.FILE_ATTRIBUTE_NORMAL,
                None
            )
            # 同时修改创建、访问和修改时间，确保物理排序绝对 deterministic
            win32file.SetFileTime(handle, win_time, win_time, win_time)
        except Exception:
            pass
        finally:
            if handle:
                win32file.CloseHandle(handle)
