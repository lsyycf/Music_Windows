import os
import sys
import random
import subprocess
import pygame
import threading
from tkinter import Tk, filedialog

from config import *
from gui_components import *
from phone_sync import *
from music_utils import *
from init import process_music_folder_three_steps


def main():
    app_data = load_app_data()
    global_volume = app_data["global_volume"]
    playlists_data = app_data["playlists"]
    music_folder = app_data["last_active_folder"]
    next_new_playlist_mode = app_data["next_new_playlist_mode"]
    phone_mappings = app_data["phone_mappings"]
    
    if music_folder and os.path.isdir(music_folder):
        try:
            process_music_folder_three_steps(music_folder)
        except Exception:
            pass
    
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.font.init()

    FONT_PATH = next(
        (
            p
            for p in [
                "C:/Windows/Fonts/msyh.ttf",
                "C:/Windows/Fonts/simsun.ttc",
                "wqy-microhei.ttc",
            ]
            if os.path.exists(p)
        ),
        None,
    )
    try:
        font_large, font_medium, font_small = [
            pygame.font.Font(FONT_PATH, s) for s in (26, 20, 16)
        ]
    except (pygame.error, FileNotFoundError):
        font_large, font_medium, font_small = [
            pygame.font.Font(None, s) for s in (32, 24, 18)
        ]

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("网易云音乐")

    try:
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_path, "outline.png")
        app_icon = pygame.image.load(icon_path)
        pygame.display.set_icon(app_icon)
    except Exception:
        pass

    if not music_folder:
        next_new_playlist_mode = "random"

    current_playlist, current_index, saved_pos = [], 0, 0.0
    active_playlist_mode = "random"

    music_progress_bar = MusicProgressBar(
        pygame.Rect(
            MIN_PROGRESS_BAR_PADDING,
            225,
            SCREEN_WIDTH - 2 * MIN_PROGRESS_BAR_PADDING,
            PROGRESS_BAR_HEIGHT,
        ),
        font_small,
    )
    
    btn_w, btn_h, btn_sp = 80, 40, 12
    ctrl_y = 285
    ctrl_w = 5 * btn_w + 4 * btn_sp
    ctrl_x_start = (SCREEN_WIDTH - ctrl_w) // 2
    
    volume_label_w, mute_btn_w, volume_slider_width, volume_control_spacing = (
        70,
        80,
        160,
        25,
    )
    volume_controls_total_w = (
        volume_label_w + volume_slider_width + mute_btn_w + (2 * volume_control_spacing)
    )
    volume_controls_x_start = (SCREEN_WIDTH - volume_controls_total_w) // 2
    volume_slider_y = ctrl_y + btn_h + 35
    volume_slider = Slider(
        pygame.Rect(
            volume_controls_x_start + volume_label_w + volume_control_spacing,
            volume_slider_y,
            volume_slider_width,
            SLIDER_HEIGHT,
        ),
        0.0,
        1.0,
        global_volume,
        font_small,
    )
    mute_button = Button(
        pygame.Rect(
            volume_slider.rect.right + volume_control_spacing, 0, mute_btn_w, 30
        ),
        "静音",
        font_small,
    )
    mute_button.rect.centery = volume_slider.rect.centery
    
    folder_ctrl_y = volume_slider.rect.bottom + 38
    folder_label_w = 90
    browse_btn_w = mode_btn_w = reset_btn_w = 75
    padding = MIN_PROGRESS_BAR_PADDING
    folder_ctrl_total_w = SCREEN_WIDTH - 2 * padding
    input_w = folder_ctrl_total_w - folder_label_w - browse_btn_w - mode_btn_w - reset_btn_w - 40
    
    folder_input_box = InputBox(
        pygame.Rect(padding + folder_label_w + 10, folder_ctrl_y, input_w, 30),
        font_small,
        initial_text=music_folder,
        placeholder_text="请选择音乐文件夹...",
    )
    browse_button = Button(
        pygame.Rect(folder_input_box.rect.right + 10, folder_ctrl_y, browse_btn_w, 30),
        "浏览",
        font_small,
    )
    mode_button = Button(
        pygame.Rect(browse_button.rect.right + 10, folder_ctrl_y, mode_btn_w, 30),
        f"{'随机' if next_new_playlist_mode == 'random' else '顺序'}",
        font_small,
    )
    reset_button = Button(
        pygame.Rect(mode_button.rect.right + 10, folder_ctrl_y, reset_btn_w, 30),
        "重置",
        font_small,
    )
    
    phone_ctrl_y = folder_ctrl_y + 40
    phone_label_w = 90
    sync_btn_w = reset_sync_btn_w = 75
    phone_input_w = folder_ctrl_total_w - phone_label_w - sync_btn_w - reset_sync_btn_w - 30
    
    current_phone_path = phone_mappings.get(music_folder, "") if music_folder else ""
    phone_input_box = InputBox(
        pygame.Rect(padding + phone_label_w + 10, phone_ctrl_y, phone_input_w, 30),
        font_small,
        initial_text=current_phone_path,
        placeholder_text="未设置手机同步路径...",
    )
    
    sync_phone_button = Button(
        pygame.Rect(phone_input_box.rect.right + 10, phone_ctrl_y, sync_btn_w, 30),
        "同步",
        font_small,
    )
    reset_sync_button = Button(
        pygame.Rect(sync_phone_button.rect.right + 10, phone_ctrl_y, reset_sync_btn_w, 30),
        "重置",
        font_small,
    )
    
    exit_button = Button(
        pygame.Rect(SCREEN_WIDTH - 75 - 15, 15, 75, 32),
        "退出",
        font_small
    )
    
    controls = [
        Button(
            pygame.Rect(ctrl_x_start + i * (btn_w + btn_sp), ctrl_y, btn_w, btn_h),
            text,
            font_small,
        )
        for i, text in enumerate(["快退", "上首", "播放", "下首", "快进"])
    ]
    
    gui_elements = controls + [
        browse_button,
        mode_button,
        reset_button,
        exit_button,
        mute_button,
        sync_phone_button,
        reset_sync_button,
    ]

    is_paused, song_playing, duration = True, False, 0.0
    volume_before_mute = global_volume if global_volume > 0 else 1.0
    scroll_x, scroll_speed, scroll_delay_start, is_scrolling, scrolling_surface = (
        0,
        30,
        0,
        False,
        None,
    )
    is_syncing = False
    sync_thread = None

    def set_volume(level):
        nonlocal global_volume, volume_before_mute
        global_volume = max(0.0, min(1.0, level))
        if global_volume > 0.01:
            volume_before_mute = global_volume
        pygame.mixer.music.set_volume(global_volume)
        volume_slider.val = global_volume
        volume_slider._update_thumb_pos()
        mute_button.text = "取消静音" if global_volume < 0.01 else "静音"

    def prepare_scrolling_text(text, font, max_width):
        nonlocal is_scrolling, scrolling_surface, scroll_x, scroll_delay_start
        text_width = font.size(text)[0]
        if text_width > max_width:
            is_scrolling, scroll_x, scroll_delay_start = (
                True,
                0,
                pygame.time.get_ticks(),
            )
            scrolling_surface = font.render(text + " " * 10 + text, True, TEXT_COLOR)
        else:
            is_scrolling, scrolling_surface = False, font.render(text, True, TEXT_COLOR)

    def compare_and_update_playlist(old_playlist, new_files, current_idx, current_mode):
        if not old_playlist:
            return create_ordered_playlist(new_files, current_mode), 0
        
        old_set = set(old_playlist)
        new_set = set(new_files)
        
        deleted_songs = old_set - new_set
        added_songs = new_set - old_set
        
        current_song_path = None
        if 0 <= current_idx < len(old_playlist):
            current_song_path = old_playlist[current_idx]
        
        updated_playlist = list(old_playlist)
        updated_index = current_idx
        
        if current_mode == "sequential":
            if deleted_songs:
                updated_playlist = [song for song in updated_playlist if song not in deleted_songs]
            if added_songs:
                updated_playlist.extend(list(added_songs))
            if updated_playlist:
                updated_playlist.sort(key=lambda f: os.path.basename(f).lower())
            if not updated_playlist:
                updated_index = 0
            elif current_song_path and current_song_path in updated_playlist:
                updated_index = updated_playlist.index(current_song_path)
            elif current_song_path:
                current_name = os.path.basename(current_song_path).lower()
                updated_index = len(updated_playlist)
                for i, song in enumerate(updated_playlist):
                    if os.path.basename(song).lower() > current_name:
                        updated_index = i
                        break
            else:
                updated_index = 0
        else:
            if deleted_songs:
                indices_to_remove = []
                for song in deleted_songs:
                    if song in updated_playlist:
                        song_idx = updated_playlist.index(song)
                        indices_to_remove.append(song_idx)
                
                for song_idx in sorted(indices_to_remove, reverse=True):
                    updated_playlist.pop(song_idx)
                    if song_idx < updated_index:
                        updated_index -= 1
            
            if added_songs:
                if updated_index < len(updated_playlist):
                    songs_after_current = updated_playlist[updated_index + 1:]
                    updated_playlist = updated_playlist[:updated_index + 1]
                    songs_to_shuffle = list(added_songs) + songs_after_current
                    random.shuffle(songs_to_shuffle)
                    updated_playlist.extend(songs_to_shuffle)
                else:
                    new_songs_list = list(added_songs)
                    random.shuffle(new_songs_list)
                    updated_playlist.extend(new_songs_list)
        
        if updated_playlist:
            if updated_index >= len(updated_playlist):
                updated_index = len(updated_playlist) - 1
            elif updated_index < 0:
                updated_index = 0
        else:
            updated_index = 0
            
        return updated_playlist, updated_index

    def load_playlist_state(folder_path, process_files=True, auto_play=False):
        nonlocal music_folder, current_playlist, current_index, saved_pos, active_playlist_mode, duration, is_paused, song_playing

        music_folder = folder_path
        folder_input_box.set_text(music_folder)
        
        current_phone_path = phone_mappings.get(music_folder, "") if music_folder else ""
        phone_input_box.set_text(current_phone_path)

        duration, saved_pos = 0.0, 0.0
        if music_folder and process_files:
            try:
                process_music_folder_three_steps(music_folder)
            except Exception:
                pass

        if music_folder and music_folder in playlists_data:
            data = playlists_data[music_folder]
            old_playlist = data.get("song_list", [])
            old_index = data.get("last_index", 0)
            saved_pos = data.get("last_position", 0.0)
            active_playlist_mode = data.get("play_mode", "random")
            
            all_files = validate_and_get_music_files(music_folder)
            
            current_playlist, current_index = compare_and_update_playlist(
                old_playlist, all_files, old_index, active_playlist_mode
            )
            
        elif music_folder:
            all_files = validate_and_get_music_files(music_folder)
            active_playlist_mode = next_new_playlist_mode
            current_playlist = create_ordered_playlist(all_files, active_playlist_mode)
            current_index, saved_pos = 0, 0.0
        else:
            current_playlist, current_index, saved_pos = [], 0, 0.0
            active_playlist_mode = next_new_playlist_mode

        is_paused, song_playing = True, False
        controls[2].text = "播放"
        mode_button.text = f"{'随机' if active_playlist_mode == 'random' else '顺序'}"

        if not current_playlist:
            prepare_scrolling_text(
                "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 40
            )
        else:
            if auto_play:
                load_and_play_song(current_index, start_pos=saved_pos)
            else:
                load_song_info_only(current_index)
                if saved_pos > 0:
                    is_paused = True

    def load_and_play_song(idx, start_pos=0.0, skip_count=0, original_length=None, direction=None):
        nonlocal duration, song_playing, is_paused, current_index, saved_pos
        if not current_playlist:
            prepare_scrolling_text(
                "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 40
            )
            duration = 0.0
            song_playing = False
            is_paused = True
            controls[2].text = "播放"
            current_index = 0
            return
        
        if original_length is None:
            original_length = len(current_playlist)
        
        if skip_count >= original_length:
            prepare_scrolling_text(
                "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 40
            )
            duration = 0.0
            song_playing = False
            is_paused = True
            controls[2].text = "播放"
            current_index = 0
            return
        
        current_index = idx % len(current_playlist)
        song_path = current_playlist[current_index]
        saved_pos = start_pos
        
        if not os.path.exists(song_path):
            old_index = current_index
            current_playlist.pop(current_index)
            if not current_playlist:
                prepare_scrolling_text(
                    "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 40
                )
                duration = 0.0
                song_playing = False
                is_paused = True
                controls[2].text = "播放"
                current_index = 0
                return
            if direction == "prev":
                next_idx = (old_index - 1) % len(current_playlist)
            elif direction == "next":
                next_idx = old_index % len(current_playlist)
            else:
                if old_index >= len(current_playlist):
                    next_idx = 0
                else:
                    next_idx = old_index % len(current_playlist)
            load_and_play_song(next_idx, start_pos=0.0, skip_count=skip_count + 1, original_length=original_length, direction=direction)
            return
        
        try:
            pygame.mixer.music.load(song_path)
            duration = pygame.mixer.Sound(song_path).get_length() or 0.0
            pygame.mixer.music.play(start=start_pos)
            song_playing, is_paused = True, False
            controls[2].text = "暂停"
            prepare_scrolling_text(
                os.path.splitext(os.path.basename(song_path))[0],
                font_large,
                SCREEN_WIDTH - 40,
            )
        except (pygame.error, FileNotFoundError):
            old_index = current_index
            current_playlist.pop(current_index)
            if not current_playlist:
                prepare_scrolling_text(
                    "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 40
                )
                duration = 0.0
                song_playing = False
                is_paused = True
                controls[2].text = "播放"
                current_index = 0
                return
            if direction == "prev":
                next_idx = (old_index - 1) % len(current_playlist)
            elif direction == "next":
                next_idx = old_index % len(current_playlist)
            else:
                if old_index >= len(current_playlist):
                    next_idx = 0
                else:
                    next_idx = old_index % len(current_playlist)
            load_and_play_song(next_idx, start_pos=0.0, skip_count=skip_count + 1, original_length=original_length, direction=direction)

    def load_song_info_only(idx, skip_count=0, original_length=None, direction=None):
        nonlocal duration, song_playing, current_index, saved_pos
        if not current_playlist:
            prepare_scrolling_text(
                "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 40
            )
            duration = 0.0
            song_playing = False
            current_index = 0
            saved_pos = 0.0
            return
        
        if original_length is None:
            original_length = len(current_playlist)
        
        if skip_count >= original_length:
            prepare_scrolling_text(
                "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 40
            )
            duration = 0.0
            song_playing = False
            current_index = 0
            saved_pos = 0.0
            return
        
        current_index = idx % len(current_playlist)
        song_path = current_playlist[current_index]
        
        if not os.path.exists(song_path):
            old_index = current_index
            current_playlist.pop(current_index)
            saved_pos = 0.0
            if not current_playlist:
                prepare_scrolling_text(
                    "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 40
                )
                duration = 0.0
                song_playing = False
                current_index = 0
                return
            if direction == "prev":
                next_idx = (old_index - 1) % len(current_playlist)
            elif direction == "next":
                next_idx = old_index % len(current_playlist)
            else:
                if old_index >= len(current_playlist):
                    next_idx = 0
                else:
                    next_idx = old_index % len(current_playlist)
            load_song_info_only(next_idx, skip_count=skip_count + 1, original_length=original_length, direction=direction)
            return
        
        try:
            duration = pygame.mixer.Sound(song_path).get_length() or 0.0
            song_playing = False
            prepare_scrolling_text(
                os.path.splitext(os.path.basename(song_path))[0],
                font_large,
                SCREEN_WIDTH - 40,
            )
        except (pygame.error, FileNotFoundError):
            old_index = current_index
            current_playlist.pop(current_index)
            saved_pos = 0.0
            if not current_playlist:
                prepare_scrolling_text(
                    "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 40
                )
                duration = 0.0
                song_playing = False
                current_index = 0
                return
            if direction == "prev":
                next_idx = (old_index - 1) % len(current_playlist)
            elif direction == "next":
                next_idx = old_index % len(current_playlist)
            else:
                if old_index >= len(current_playlist):
                    next_idx = 0
                else:
                    next_idx = old_index % len(current_playlist)
            load_song_info_only(next_idx, skip_count=skip_count + 1, original_length=original_length, direction=direction)

    def seek_music(ratio):
        nonlocal saved_pos
        if duration > 0:
            seek_pos = duration * ratio
            saved_pos = seek_pos
            if song_playing and not is_paused:
                load_and_play_song(current_index, start_pos=seek_pos)

    def handle_action(action):
        nonlocal is_paused, song_playing, current_index, saved_pos, duration, next_new_playlist_mode, active_playlist_mode, music_folder, current_playlist, playlists_data, running, phone_mappings, is_syncing

        allowed_when_empty = ["browse", "toggle_mode", "exit", "reset", "toggle_mute", "sync_phone", "reset_sync"]
        if not current_playlist and action not in allowed_when_empty:
            return

        if action == "play_pause":
            if is_paused:
                load_and_play_song(current_index, start_pos=saved_pos)
            else:
                if song_playing:
                    saved_pos += pygame.mixer.music.get_pos() / 1000.0
                    pygame.mixer.music.stop()
                    song_playing = False
                is_paused = True
                controls[2].text = "播放"
        elif action in ["prev", "next", "next_auto"]:
            next_idx = (
                (current_index + (-1 if action == "prev" else 1))
                % len(current_playlist)
                if current_playlist
                else 0
            )
            direction = "prev" if action == "prev" else ("next" if action in ["next", "next_auto"] else None)
            if action == "next_auto" or not is_paused:
                load_and_play_song(next_idx, start_pos=0.0, direction=direction)
            else:
                load_song_info_only(next_idx, direction=direction)
                saved_pos = 0.0
        elif action == "rewind":
            if duration > 0:
                seek_music(
                    max(
                        0,
                        (
                            saved_pos
                            + (
                                pygame.mixer.music.get_pos() / 1000.0
                                if song_playing
                                else 0
                            )
                            - FAST_FORWARD_REWIND_STEP
                        )
                        / duration,
                    )
                )
        elif action == "fast_forward":
            if duration > 0:
                seek_music(
                    min(
                        1,
                        (
                            saved_pos
                            + (
                                pygame.mixer.music.get_pos() / 1000.0
                                if song_playing
                                else 0
                            )
                            + FAST_FORWARD_REWIND_STEP
                        )
                        / duration,
                    )
                )

        elif action == "toggle_mode":
            next_new_playlist_mode = (
                "sequential" if next_new_playlist_mode == "random" else "random"
            )
            mode_button.text = f"{'随机' if next_new_playlist_mode == 'random' else '顺序'}"

        elif action == "browse":
            is_playing_before_browse = not is_paused
            if music_folder and current_playlist:
                current_pos_on_save = saved_pos + (
                    pygame.mixer.music.get_pos() / 1000.0 if song_playing else 0
                )
                playlists_data[music_folder] = {
                    "song_list": current_playlist,
                    "last_index": current_index,
                    "last_position": current_pos_on_save,
                    "play_mode": active_playlist_mode,
                }

            pygame.mixer.music.stop()
            pygame.display.flip()

            root = Tk()
            root.withdraw()
            folder = filedialog.askdirectory()
            root.destroy()

            if folder:
                load_playlist_state(os.path.abspath(folder), process_files=True, auto_play=False)
            else:
                load_playlist_state(music_folder, process_files=False, auto_play=False)

        elif action == "reset":
            if music_folder in playlists_data:
                del playlists_data[music_folder]
            pygame.mixer.music.stop()
            music_folder = ""
            next_new_playlist_mode = "random"
            load_playlist_state(music_folder, process_files=False)
        elif action == "toggle_mute":
            set_volume(0.0 if global_volume > 0.01 else volume_before_mute)
        
        elif action == "sync_phone":
            if not music_folder:
                return
            
            if is_syncing:
                return
            
            if not check_adb_connection():
                return
            
            phone_path = phone_mappings.get(music_folder, "")
            if not phone_path:
                phone_path = ask_phone_path()
                
                if not phone_path:
                    return
                
                if not is_adb_path(phone_path):
                    adb_path = convert_windows_path_to_adb(phone_path)
                    phone_path = adb_path
                
                creation_flags = 0x08000000 if sys.platform == 'win32' else 0
                test_result = subprocess.run(
                    ["adb", "shell", f"ls '{phone_path}'"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=5,
                    creationflags=creation_flags
                )
                
                if test_result.returncode != 0:
                    return
                
                phone_mappings[music_folder] = phone_path
                phone_input_box.set_text(phone_path)
            
            is_syncing = True
            sync_phone_button.text = "同步"
            sync_phone_button.disabled = True
            browse_button.disabled = True
            mode_button.disabled = True
            reset_button.disabled = True
            reset_sync_button.disabled = True
            
            def sync_thread_func():
                nonlocal is_syncing
                try:
                    sync_phone_complete(music_folder, phone_path)
                except Exception:
                    pass
                finally:
                    is_syncing = False
            
            sync_thread = threading.Thread(target=sync_thread_func, daemon=True)
            sync_thread.start()
        
        elif action == "reset_sync":
            if music_folder and music_folder in phone_mappings:
                del phone_mappings[music_folder]
                phone_input_box.set_text("")
            else:
                phone_input_box.set_text("")
        
        elif action == "exit":
            running = False

    controls[0].action, controls[1].action, controls[2].action = (
        lambda: handle_action("rewind"),
        lambda: handle_action("prev"),
        lambda: handle_action("play_pause"),
    )
    controls[3].action, controls[4].action, browse_button.action = (
        lambda: handle_action("next"),
        lambda: handle_action("fast_forward"),
        lambda: handle_action("browse"),
    )
    mode_button.action, reset_button.action, exit_button.action = (
        lambda: handle_action("toggle_mode"),
        lambda: handle_action("reset"),
        lambda: handle_action("exit"),
    )
    mute_button.action = lambda: handle_action("toggle_mute")
    sync_phone_button.action = lambda: handle_action("sync_phone")
    reset_sync_button.action = lambda: handle_action("reset_sync")

    set_volume(global_volume)
    load_playlist_state(music_folder, process_files=False)

    running, clock = True, pygame.time.Clock()
    try:
        while running:
            dt = clock.tick(60) / 1000.0
            
            if not is_syncing and sync_phone_button.disabled:
                sync_phone_button.disabled = False
                sync_phone_button.text = "同步"
                browse_button.disabled = False
                mode_button.disabled = False
                reset_button.disabled = False
                reset_sync_button.disabled = False
            
            if song_playing and not pygame.mixer.music.get_busy():
                handle_action("next_auto")

            current_time = saved_pos + (
                pygame.mixer.music.get_pos() / 1000.0 if song_playing else 0
            )
            folder_input_box.update(dt)
            phone_input_box.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                for el in gui_elements:
                    el.handle_event(event)
                volume_slider.handle_event(event, set_volume)
                if current_playlist:
                    music_progress_bar.handle_event(event, seek_music)

            screen.fill(BACKGROUND_COLOR)
            
            separator_color = (40, 40, 55)
            pygame.draw.line(screen, separator_color, (padding, 207), (SCREEN_WIDTH - padding, 207), 1)
            pygame.draw.line(screen, separator_color, (padding, folder_ctrl_y - 19), (SCREEN_WIDTH - padding, folder_ctrl_y - 19), 1)
            
            if is_scrolling:
                if pygame.time.get_ticks() - scroll_delay_start > SCROLL_DELAY_DURATION:
                    scroll_x = (scroll_x + scroll_speed * dt) % (
                        scrolling_surface.get_width() / 2
                    )
                clip_rect = pygame.Rect(20, 60, SCREEN_WIDTH - 40, 50)
                screen.blit(
                    scrolling_surface, (clip_rect.x - scroll_x, clip_rect.y + 10)
                )
            elif scrolling_surface:
                screen.blit(
                    scrolling_surface,
                    scrolling_surface.get_rect(center=(SCREEN_WIDTH // 2, 80)),
                )

            status_y, status_spacing = 125, 25
            status = (
                "正在播放"
                if song_playing
                else "已暂停" if current_playlist else "空闲"
            )
            status_surface = font_small.render(status, True, ACCENT_COLOR)
            screen.blit(
                status_surface,
                status_surface.get_rect(center=(SCREEN_WIDTH // 2, status_y)),
            )

            index_text = (
                f"{current_index + 1} / {len(current_playlist)}"
                if current_playlist
                else "0 / 0"
            )
            index_surface = font_small.render(index_text, True, TEXT_COLOR)
            screen.blit(
                index_surface,
                index_surface.get_rect(
                    center=(SCREEN_WIDTH // 2, status_y + status_spacing)
                ),
            )

            time_text = f"{format_time(current_time)} / {format_time(duration)}"
            time_surface = font_medium.render(time_text, True, TEXT_COLOR)
            screen.blit(
                time_surface,
                time_surface.get_rect(
                    center=(SCREEN_WIDTH // 2, status_y + status_spacing * 2.2)
                ),
            )

            volume_label_surface = font_small.render(
                f"音量: {int(global_volume*100)}%", True, TEXT_COLOR
            )
            screen.blit(
                volume_label_surface,
                volume_label_surface.get_rect(
                    centerx=volume_controls_x_start + volume_label_w / 2,
                    centery=volume_slider.rect.centery,
                ),
            )

            music_progress_bar.draw(screen, current_time, duration)
            volume_slider.draw(screen)
            
            folder_label_surface = font_small.render("本地文件夹", True, SECONDARY_TEXT_COLOR)
            screen.blit(
                folder_label_surface,
                folder_label_surface.get_rect(
                    left=padding,
                    centery=folder_input_box.rect.centery
                )
            )
            folder_input_box.draw(screen)
            
            phone_label_surface = font_small.render("手机路径", True, SECONDARY_TEXT_COLOR)
            screen.blit(
                phone_label_surface,
                phone_label_surface.get_rect(
                    left=padding,
                    centery=phone_input_box.rect.centery
                )
            )
            phone_input_box.draw(screen)
            
            for el in gui_elements:
                el.draw(screen)
            pygame.display.flip()

    except Exception:
        pass
    finally:
        pos = saved_pos
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pos = saved_pos + pygame.mixer.music.get_pos() / 1000.0

        if music_folder and current_playlist:
            playlists_data[music_folder] = {
                "song_list": current_playlist,
                "last_index": current_index,
                "last_position": pos,
                "play_mode": active_playlist_mode,
            }

        save_app_data(
            global_volume, music_folder, next_new_playlist_mode, playlists_data, phone_mappings
        )
        pygame.quit()
        sys.exit()


main()
