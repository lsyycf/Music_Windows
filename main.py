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
import os

# 强制 SDL 使用系统原生的输入法界面 (修复 Windows 下输入法候选框不显示的问题)
os.environ["SDL_IME_SHOW_UI"] = "1"


def format_time(seconds):
    if seconds is None:
        return "00:00"
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins:02d}:{secs:02d}"


def main():
    app_data = load_app_data()
    global_volume = app_data["global_volume"]
    playlists_data = app_data["playlists"]
    music_folder = app_data["last_active_folder"]
    next_new_playlist_mode = app_data["next_new_playlist_mode"]
    phone_mappings = app_data["phone_mappings"]

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

    # --- UI Layout Constants ---
    BLOCK_MARGIN = 40

    # Block 1: Song Info & Progress (Top)
    music_progress_bar_y = 130
    music_progress_bar = MusicProgressBar(
        pygame.Rect(
            MIN_PROGRESS_BAR_PADDING,
            music_progress_bar_y,
            SCREEN_WIDTH - 2 * MIN_PROGRESS_BAR_PADDING,
            PROGRESS_BAR_HEIGHT,
        ),
        font_small,
    )

    # Block 2: Playback & Volume Control (Middle)
    ctrl_y = 260
    btn_w, btn_h, btn_sp = 64, 64, 15
    main_ctrl_total_w = 5 * btn_w + 4 * btn_sp
    ctrl_x_start = (SCREEN_WIDTH - main_ctrl_total_w) // 2

    controls = [
        Button(
            pygame.Rect(ctrl_x_start + i * (btn_w + btn_sp), ctrl_y, btn_w, btn_h),
            text,
            font_small,
        )
        for i, text in enumerate(["快退", "上首", "播放", "下首", "快进"])
    ]

    # Secondary buttons on sides of main controls
    side_btn_w, side_btn_h = 70, 36
    MODE_TEXT = {"random": "随机", "sequential": "顺序", "single_loop": "单循环"}
    mode_button = Button(
        pygame.Rect(ctrl_x_start - side_btn_w - 20, ctrl_y + (btn_h - side_btn_h)//2, side_btn_w, side_btn_h),
        MODE_TEXT.get(next_new_playlist_mode, "随机"),
        font_small,
        is_secondary=True
    )
    list_button = Button(
        pygame.Rect(ctrl_x_start + main_ctrl_total_w + 20, ctrl_y + (btn_h - side_btn_h)//2, side_btn_w, side_btn_h),
        "列表",
        font_small,
        is_secondary=True
    )

    # Volume Control Row
    volume_y = ctrl_y + btn_h + 26
    vol_label_w = 60
    vol_slider_w = 200
    vol_mute_w = 80
    vol_spacing = 20
    vol_total_w = vol_label_w + vol_slider_w + vol_mute_w + 2 * vol_spacing
    vol_x_start = (SCREEN_WIDTH - vol_total_w) // 2

    volume_slider = Slider(
        pygame.Rect(
            vol_x_start + vol_label_w + vol_spacing,
            volume_y + 10, # Vertical offset for centering thumb
            vol_slider_w,
            SLIDER_HEIGHT,
        ),
        0.0,
        1.0,
        global_volume,
        font_small,
    )
    mute_button = Button(
        pygame.Rect(volume_slider.rect.right + vol_spacing, volume_y, vol_mute_w, 36),
        "静音" if global_volume >= 0.01 else "取消静音",
        font_small,
        is_secondary=True
    )

    # Block 3: File & Sync Settings (Bottom)
    settings_y_start = 430
    row_h = 50
    label_w = 88
    input_w = 250
    action_btn_w = 62
    spacing = 8

    # Grid calculation
    settings_x_start = (SCREEN_WIDTH - (label_w + input_w + 2 * action_btn_w + 3 * spacing)) // 2

    # Row 1: Local Folder
    def on_folder_change(new_path):
        nonlocal music_folder
        music_folder = new_path

    folder_input_box = InputBox(
        pygame.Rect(settings_x_start + label_w + spacing, settings_y_start, input_w, 32),
        font_small,
        initial_text=music_folder,
        placeholder_text="请选择音乐文件夹...",
        on_change=on_folder_change
    )
    browse_button = Button(
        pygame.Rect(folder_input_box.rect.right + spacing, settings_y_start, action_btn_w, 32),
        "浏览",
        font_small,
        is_secondary=True
    )
    reset_button = Button(
        pygame.Rect(browse_button.rect.right + spacing, settings_y_start, action_btn_w, 32),
        "刷新",
        font_small,
        is_secondary=True
    )
    reset_playlist_button = Button(
        pygame.Rect(reset_button.rect.right + spacing, settings_y_start, action_btn_w, 32),
        "重置",
        font_small,
        is_secondary=True
    )

    # Row 2: Phone Sync
    def on_phone_change(new_path):
        if music_folder:
            phone_mappings[music_folder] = new_path

    sync_y = settings_y_start + row_h
    current_phone_path = phone_mappings.get(music_folder, "") if music_folder else ""
    phone_input_box = InputBox(
        pygame.Rect(settings_x_start + label_w + spacing, sync_y, input_w, 32),
        font_small,
        initial_text=current_phone_path,
        placeholder_text="未设置手机同步路径...",
        on_change=on_phone_change
    )
    sync_phone_button = Button(
        pygame.Rect(phone_input_box.rect.right + spacing, sync_y, action_btn_w, 32),
        "同步",
        font_small,
        is_secondary=True
    )
    reset_sync_button = Button(
        pygame.Rect(sync_phone_button.rect.right + spacing, sync_y, action_btn_w, 32),
        "重置",
        font_small,
        is_secondary=True
    )

    # Exit button at top-right
    exit_button = Button(
        pygame.Rect(SCREEN_WIDTH - 80 - 15, 15, 80, 32),
        "退出",
        font_small,
        is_secondary=True
    )

    playlist_ui = Playlist(
        pygame.Rect(40, 40, SCREEN_WIDTH - 80, SCREEN_HEIGHT - 80),
        font_medium,
        font_small
    )

    gui_elements = controls + [
        browse_button,
        mode_button,
        list_button,
        reset_button,
        reset_playlist_button,
        exit_button,
        mute_button,
        sync_phone_button,
        reset_sync_button,
        folder_input_box,
        phone_input_box,
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
    is_switching_song = False  # 对齐安卓：切歌状态标志，防止状态闪烁和并发冲突

    last_save_time = pygame.time.get_ticks()

    def persist_state(immediate_disk=False):
        nonlocal saved_pos
        current_pos_on_save = saved_pos + (
            pygame.mixer.music.get_pos() / 1000.0 if song_playing else 0
        )
        if music_folder and current_playlist:
            playlists_data[music_folder] = {
                "song_list": current_playlist,
                "last_index": current_index,
                "last_position": current_pos_on_save,
                "play_mode": active_playlist_mode,
                "duration": duration, # 对齐安卓：保存曲目时长
            }

        # 总是保存到内存，根据 immediate_disk 决定是否同步到磁盘
        if immediate_disk:
            save_app_data(global_volume, music_folder, next_new_playlist_mode, playlists_data, phone_mappings)

    def set_volume(level):
        nonlocal global_volume, volume_before_mute
        global_volume = max(0.0, min(1.0, level))
        if global_volume > 0.01:
            volume_before_mute = global_volume
        pygame.mixer.music.set_volume(global_volume)
        volume_slider.val = global_volume
        volume_slider._update_thumb_pos()
        mute_button.text = "取消静音" if global_volume < 0.01 else "静音"
        # 对齐安卓：音量改变立即同步到磁盘
        save_app_data(global_volume, music_folder, next_new_playlist_mode, playlists_data, phone_mappings)

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

        if current_mode != "random":
            # 顺序模式：删除已删文件，添加新文件，按文件名排序（不含后缀，保持与安卓一致）
            if deleted_songs:
                updated_playlist = [song for song in updated_playlist if song not in deleted_songs]
            if added_songs:
                updated_playlist.extend(list(added_songs))
            if updated_playlist:
                updated_playlist.sort(key=lambda f: os.path.splitext(os.path.basename(f))[0].lower())

            if not updated_playlist:
                updated_index = 0
            elif current_song_path and current_song_path in updated_playlist:
                updated_index = updated_playlist.index(current_song_path)
            elif current_song_path:
                # 智能定位：找到第一个文件名大于当前歌曲的位置
                current_name = os.path.splitext(os.path.basename(current_song_path))[0].lower()
                updated_index = len(updated_playlist)
                for i, song in enumerate(updated_playlist):
                    if os.path.splitext(os.path.basename(song))[0].lower() > current_name:
                        updated_index = i
                        break
            else:
                updated_index = 0
        else:
            # 随机模式：增量更新，保持原有顺序
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
                # 随机插入新歌曲，并相应调整索引
                new_songs_list = [f for f in new_files if f in added_songs]
                for new_song in new_songs_list:
                    insert_pos = random.randint(0, len(updated_playlist))
                    updated_playlist.insert(insert_pos, new_song)
                    if insert_pos <= updated_index:
                        updated_index += 1

        if updated_playlist:
            updated_index = max(0, min(updated_index, len(updated_playlist) - 1))
        else:
            updated_index = 0

        return updated_playlist, updated_index

    def load_playlist_state(folder_path, force_scan=False, auto_play=False, allow_auto_scan=True):
        nonlocal music_folder, current_playlist, current_index, saved_pos, active_playlist_mode, duration, is_paused, song_playing, next_new_playlist_mode

        # 如果文件夹没变，记录当前真实的播放位置，防止刷新时进度丢失
        current_pos_on_call = saved_pos + (pygame.mixer.music.get_pos() / 1000.0 if song_playing else 0)

        music_folder = folder_path
        folder_input_box.set_text(music_folder)

        current_phone_path = phone_mappings.get(music_folder, "") if music_folder else ""
        phone_input_box.set_text(current_phone_path)

        duration = 0.0
        # 仅在切换文件夹时重置 saved_pos
        if not force_scan:
             saved_pos = 0.0
        else:
             saved_pos = current_pos_on_call

        cached_data = playlists_data.get(music_folder) if music_folder else None
        has_valid_cache = bool(cached_data and cached_data.get("song_list"))

        # 逻辑对齐安卓：优先检查缓存，如果存在缓存且非强制刷新，则瞬间恢复（秒启动）
        if music_folder and has_valid_cache and not force_scan:
            data = cached_data
            current_playlist = data.get("song_list", [])
            current_index = data.get("last_index", 0)
            saved_pos = data.get("last_position", 0.0)
            active_playlist_mode = data.get("play_mode", "random")
            duration = data.get("duration", 0.0) # 对齐安卓：恢复时长
            # 对齐安卓：同步全局按钮模式到当前文件夹的模式
            next_new_playlist_mode = active_playlist_mode
            mode_button.text = MODE_TEXT.get(next_new_playlist_mode, "随机")
            print(f"Restore from cache: {len(current_playlist)} songs")

        elif music_folder:
            if not allow_auto_scan and not force_scan:
                current_playlist, current_index, saved_pos = [], 0, 0.0
                active_playlist_mode = next_new_playlist_mode
                is_paused, song_playing = True, False
                controls[2].text = "播放"
                mode_button.text = MODE_TEXT.get(active_playlist_mode, "随机")
                playlist_ui.set_items(current_playlist, current_index)
                print(f"No cache found and auto-scan disabled: {music_folder}")
                prepare_scrolling_text(
                    "无缓存数据，点击刷新以扫描", font_large, SCREEN_WIDTH - 120
                )
                return

            # 没有缓存或强制刷新：扫描磁盘
            print(f"Scanning folder: {music_folder}")
            all_files = validate_and_get_music_files(music_folder)

            if music_folder in playlists_data and has_valid_cache:
                # 增量更新模式（用于刷新）
                data = playlists_data[music_folder]
                if force_scan:
                    old_playlist = current_playlist
                    old_index = current_index
                else:
                    old_playlist = data.get("song_list", [])
                    old_index = data.get("last_index", 0)
                    active_playlist_mode = data.get("play_mode", "random")
                current_playlist, current_index = compare_and_update_playlist(
                    old_playlist, all_files, old_index, active_playlist_mode
                )
                if not force_scan:
                    saved_pos = data.get("last_position", 0.0)
            else:
                # 全新加载模式
                active_playlist_mode = next_new_playlist_mode
                current_playlist = create_ordered_playlist(all_files, active_playlist_mode)
                current_index, saved_pos = 0, 0.0

            # 扫描后立即持久化元数据
            persist_state(immediate_disk=True)
        else:
            current_playlist, current_index, saved_pos = [], 0, 0.0
            active_playlist_mode = next_new_playlist_mode

        is_paused, song_playing = True, False
        controls[2].text = "播放"
        mode_button.text = MODE_TEXT.get(active_playlist_mode, "随机")

        if not current_playlist:
            prepare_scrolling_text(
                "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 120
            )
        else:
            if auto_play:
                load_and_play_song(current_index, start_pos=saved_pos)
            else:
                load_song_info_only(current_index)
                if saved_pos > 0:
                    is_paused = True

            playlist_ui.set_items(current_playlist, current_index)
            persist_state(immediate_disk=True)

    def load_and_play_song(idx, start_pos=0.0, skip_count=0, original_length=None, direction=None):
        nonlocal duration, song_playing, is_paused, current_index, saved_pos
        if not current_playlist:
            prepare_scrolling_text(
                "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 120
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
                "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 120
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
                    "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 120
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
            nonlocal is_switching_song
            is_switching_song = True

            pygame.mixer.music.load(song_path)
            duration = pygame.mixer.Sound(song_path).get_length() or 0.0
            pygame.mixer.music.play(start=start_pos)
            song_playing, is_paused = True, False

            is_switching_song = False
            controls[2].text = "暂停"
            prepare_scrolling_text(
                os.path.splitext(os.path.basename(song_path))[0],
                font_large,
                SCREEN_WIDTH - 120,
            )
        except (pygame.error, FileNotFoundError):
            old_index = current_index
            current_playlist.pop(current_index)
            if not current_playlist:
                prepare_scrolling_text(
                    "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 120
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
        nonlocal duration, song_playing, current_index, saved_pos, is_paused
        if not current_playlist:
            prepare_scrolling_text(
                "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 120
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
                "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 120
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
                    "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 120
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
            is_paused = True
            controls[2].text = "播放"
            prepare_scrolling_text(
                os.path.splitext(os.path.basename(song_path))[0],
                font_large,
                SCREEN_WIDTH - 120,
            )
        except (pygame.error, FileNotFoundError):
            old_index = current_index
            current_playlist.pop(current_index)
            saved_pos = 0.0
            if not current_playlist:
                prepare_scrolling_text(
                    "无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 120
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
            # 逻辑对齐安卓：限制 seek 位置，防止刚好落在结尾触发切歌闪烁
            seek_pos = duration * ratio
            if seek_pos >= duration - 1.0:
                 seek_pos = max(0, duration - 1.0)

            saved_pos = seek_pos
            if song_playing and not is_paused:
                load_and_play_song(current_index, start_pos=seek_pos)
            else:
                saved_pos = seek_pos
                load_song_info_only(current_index)
            # 进度跳转属于重要状态变更，立即持久化
            persist_state(immediate_disk=True)

    def handle_action(action, **kwargs):
        nonlocal is_paused, song_playing, current_index, saved_pos, duration, next_new_playlist_mode, active_playlist_mode, music_folder, current_playlist, playlists_data, running, phone_mappings, is_syncing

        allowed_when_empty = ["browse", "toggle_mode", "exit", "reset", "reset_playlist", "toggle_mute", "sync_phone", "reset_sync", "toggle_playlist"]
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
                # 对齐安卓：暂停时立即持久化到磁盘
                persist_state(immediate_disk=True)
        elif action in ["prev", "next", "next_auto"]:
            # 继承播放状态：如果是自动切换，必定继承“播放中”状态；如果是手动切换，根据当前是否暂停决定
            was_playing = (not is_paused) or (action == "next_auto")

            # 处理单曲循环：仅在自动播放结束时触发
            if action == "next_auto" and active_playlist_mode == "single_loop":
                next_idx = current_index
            else:
                next_idx = (
                    (current_index + (-1 if action == "prev" else 1))
                    % len(current_playlist)
                    if current_playlist
                    else 0
                )

            direction = "prev" if action == "prev" else "next"

            if was_playing:
                load_and_play_song(next_idx, start_pos=0.0, direction=direction)
            else:
                load_song_info_only(next_idx, direction=direction)
                is_paused = True
                controls[2].text = "播放"
                saved_pos = 0.0

            playlist_ui.current_index = current_index
            persist_state(immediate_disk=True) # 索引改变属于元数据变更，立即同步磁盘
        elif action == "rewind":
            if duration > 0:
                curr = saved_pos + (pygame.mixer.music.get_pos() / 1000.0 if song_playing else 0)
                # 逻辑对齐安卓：如果在开头（或不到 1 秒），快退则切到上一首
                if curr <= 1.0:
                    handle_action("prev")
                else:
                    seek_music(max(0, (curr - FAST_FORWARD_REWIND_STEP) / duration))
        elif action == "fast_forward":
            if duration > 0:
                curr = saved_pos + (pygame.mixer.music.get_pos() / 1000.0 if song_playing else 0)
                # 逻辑对齐安卓：如果在结尾（或不到 1 秒），快进则直接切歌
                if curr >= duration - 1.0:
                    handle_action("next")
                else:
                    seek_music(min(1, (curr + FAST_FORWARD_REWIND_STEP) / duration))

        elif action == "toggle_mode":
            modes = ["random", "sequential", "single_loop"]
            idx = modes.index(next_new_playlist_mode)
            next_new_playlist_mode = modes[(idx + 1) % len(modes)]
            mode_button.text = MODE_TEXT.get(next_new_playlist_mode, "随机")
            if music_folder:
                active_playlist_mode = next_new_playlist_mode
            persist_state(immediate_disk=True)

        elif action == "toggle_playlist":
            playlist_ui.visible = not playlist_ui.visible
            if playlist_ui.visible:
                playlist_ui.set_items(current_playlist, current_index)
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()

        elif action == "play_at_index":
            idx = kwargs.get("index", 0)
            if 0 <= idx < len(current_playlist):
                was_playing = not is_paused
                current_index = idx
                if was_playing:
                    load_and_play_song(current_index, start_pos=0.0)
                else:
                    load_song_info_only(current_index)
                    saved_pos = 0.0
                playlist_ui.visible = False
                pygame.key.stop_text_input()
                playlist_ui.current_index = current_index
            persist_state(immediate_disk=True)

        elif action == "delete_song":
            idx = kwargs.get("index", 0)
            if 0 <= idx < len(current_playlist):
                song_path = current_playlist[idx]
                song_name = os.path.basename(song_path)

                # 对齐安卓：删除前进行确认提示
                if not ask_confirm("删除确认", f"确定要彻底删除歌曲吗？\n{song_name}"):
                    return

                try:
                    if os.path.exists(song_path):
                        os.remove(song_path)

                    # 对齐安卓：记录当前播放状态
                    was_playing = not is_paused

                    # 更新列表
                    current_playlist.pop(idx)
                    if idx == current_index:
                        # 如果删除的是当前播放的，根据原播放状态决定是加载还是播放
                        pygame.mixer.music.stop()
                        if current_playlist:
                            if was_playing:
                                load_and_play_song(current_index % len(current_playlist), start_pos=0.0)
                            else:
                                load_song_info_only(current_index % len(current_playlist))
                                is_paused = True
                                controls[2].text = "播放"
                                saved_pos = 0.0
                        else:
                            song_playing = False
                            is_paused = True
                            controls[2].text = "播放"
                            prepare_scrolling_text("无音乐", font_large, SCREEN_WIDTH - 40)
                    elif idx < current_index:
                        current_index -= 1

                    # 额外安全检查：确保 current_index 在有效范围内
                    if current_playlist:
                        current_index = max(0, min(current_index, len(current_playlist) - 1))
                    else:
                        current_index = 0

                    playlist_ui.set_items(current_playlist, current_index)
                    persist_state(immediate_disk=True)
                except Exception as e:
                    print(f"Delete failed: {e}")

        elif action == "rename_song":
            idx = kwargs.get("index", 0)
            if 0 <= idx < len(current_playlist):
                old_path = current_playlist[idx]
                old_name = os.path.basename(old_path)

                # 使用自定义的重命名对话框
                name_no_ext = os.path.splitext(old_name)[0]
                new_name = ask_rename(name_no_ext)

                if new_name and new_name != old_name:
                    # 对齐安卓：确保扩展名一致
                    old_ext = os.path.splitext(old_path)[1]
                    if old_ext and not new_name.lower().endswith(old_ext.lower()):
                        new_name += old_ext

                    new_path = os.path.join(os.path.dirname(old_path), new_name)
                    try:
                        # 对齐安卓逻辑：如果重命名的是当前播放，需要特殊处理（Windows下文件可能被占用）
                        was_playing = not is_paused
                        current_pos = saved_pos + (pygame.mixer.music.get_pos() / 1000.0 if song_playing else 0)

                        is_current = (idx == current_index)
                        if is_current:
                            pygame.mixer.music.stop() # 释放文件句柄
                            pygame.mixer.music.unload()

                        os.rename(old_path, new_path)
                        current_playlist[idx] = new_path

                        if is_current:
                            # 恢复状态
                            if was_playing:
                                load_and_play_song(current_index, start_pos=current_pos)
                            else:
                                load_song_info_only(current_index)
                                saved_pos = current_pos
                                prepare_scrolling_text(os.path.splitext(new_name)[0], font_large, SCREEN_WIDTH - 40)

                        playlist_ui.set_items(current_playlist, current_index)
                        persist_state(immediate_disk=True)
                    except Exception as e:
                        print(f"Rename failed: {e}")

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
                    "duration": duration,
                }
            persist_state(immediate_disk=True)

            pygame.mixer.music.stop()
            pygame.display.flip()

            root = Tk()
            root.withdraw()
            folder = filedialog.askdirectory()
            root.destroy()

            if folder:
                # 切换文件夹：逻辑对齐安卓，如果是已记录过的文件夹，则秒恢复
                load_playlist_state(os.path.abspath(folder), force_scan=False, auto_play=False)
            else:
                load_playlist_state(music_folder, force_scan=False, auto_play=is_playing_before_browse)

        elif action == "reset":
            if music_folder:
                # 刷新：显式执行三步物理处理
                try:
                    process_music_folder_three_steps(music_folder)
                except Exception:
                    pass

                # 逻辑对齐安卓：显式强制扫描
                load_playlist_state(music_folder, force_scan=True, auto_play=(not is_paused))
            persist_state(immediate_disk=True)

        elif action == "reset_playlist":
            if music_folder:
                if not ask_confirm("重置确认", "确定要清空当前播放列表并删除该文件夹的缓存吗？"):
                    return
                old_folder = music_folder
                pygame.mixer.music.stop()
                if old_folder in playlists_data:
                    del playlists_data[old_folder]
                current_playlist = []
                current_index = 0
                saved_pos = 0.0
                duration = 0.0
                music_folder = ""
                active_playlist_mode = "random"
                next_new_playlist_mode = "random"
                is_paused = True
                song_playing = False
                folder_input_box.set_text("")
                phone_input_box.set_text("")
                mode_button.text = MODE_TEXT.get(next_new_playlist_mode, "随机")
                controls[2].text = "播放"
                playlist_ui.set_items(current_playlist, current_index)
                prepare_scrolling_text("无音乐, 请浏览文件夹", font_large, SCREEN_WIDTH - 120)
                save_app_data(global_volume, music_folder, next_new_playlist_mode, playlists_data, phone_mappings)

        elif action == "toggle_mute":
            set_volume(0.0 if global_volume > 0.01 else 1.0)

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
            reset_playlist_button.disabled = True
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
                if ask_confirm("重置确认", "确定要清除该文件夹关联的手机同步路径吗？"):
                    del phone_mappings[music_folder]
                    phone_input_box.set_text("")
                    persist_state(immediate_disk=True)
            else:
                phone_input_box.set_text("")

        elif action == "exit":
            persist_state()
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
    mode_button.action, list_button.action, reset_button.action, reset_playlist_button.action, exit_button.action = (
        lambda: handle_action("toggle_mode"),
        lambda: handle_action("toggle_playlist"),
        lambda: handle_action("reset"),
        lambda: handle_action("reset_playlist"),
        lambda: handle_action("exit"),
    )

    playlist_ui.on_item_click = lambda idx: handle_action("play_at_index", index=idx)
    playlist_ui.on_delete = lambda idx: handle_action("delete_song", index=idx)
    playlist_ui.on_rename = lambda idx: handle_action("rename_song", index=idx)
    mute_button.action = lambda: handle_action("toggle_mute")
    sync_phone_button.action = lambda: handle_action("sync_phone")
    reset_sync_button.action = lambda: handle_action("reset_sync")

    set_volume(global_volume)
    load_playlist_state(music_folder, force_scan=False, allow_auto_scan=False)

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
                reset_playlist_button.disabled = False
                reset_sync_button.disabled = False

            if song_playing and not is_switching_song and not pygame.mixer.music.get_busy():
                handle_action("next_auto")

            ticks = pygame.time.get_ticks()
            if song_playing and ticks - last_save_time > 15000:
                persist_state(immediate_disk=True)
                last_save_time = ticks

            current_time = saved_pos + (
                pygame.mixer.music.get_pos() / 1000.0 if song_playing else 0
            )
            for el in gui_elements:
                if hasattr(el, 'update'):
                    el.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if playlist_ui.handle_event(event):
                    continue

                for el in gui_elements:
                    el.handle_event(event)

                volume_slider.handle_event(event, set_volume)
                if current_playlist:
                    music_progress_bar.handle_event(event, seek_music)

            screen.fill(BACKGROUND_COLOR)

            # --- Drawing Block 1: Song Info & Progress (Top) ---
            if is_scrolling:
                if pygame.time.get_ticks() - scroll_delay_start > SCROLL_DELAY_DURATION:
                    scroll_x = (scroll_x + scroll_speed * dt) % (scrolling_surface.get_width() / 2)

                # Draw scrolling title with clip
                title_clip_rect = pygame.Rect(60, 60, SCREEN_WIDTH - 120, 50)
                screen.blit(
                    scrolling_surface, (title_clip_rect.x - scroll_x, title_clip_rect.y + 5)
                )
            elif scrolling_surface:
                title_rect = scrolling_surface.get_rect(center=(SCREEN_WIDTH // 2, 85))
                screen.blit(scrolling_surface, title_rect)

            music_progress_bar.draw(screen, current_time, duration)

            # Time Labels below progress bar
            time_text = f"{format_time(current_time)} / {format_time(duration)}"
            time_surf = font_small.render(time_text, True, SECONDARY_TEXT_COLOR)
            screen.blit(time_surf, (SCREEN_WIDTH // 2 - time_surf.get_width() // 2, music_progress_bar.rect.bottom + 10))

            # Status and Index Info (Centered above buttons)
            status = "正在播放" if song_playing else "已暂停" if current_playlist else "空闲"
            info_text = f"{status}  |  {current_index + 1} / {len(current_playlist)}" if current_playlist else status
            info_surf = font_medium.render(info_text, True, ACCENT_COLOR)
            screen.blit(info_surf, (SCREEN_WIDTH // 2 - info_surf.get_width() // 2, ctrl_y - 45))

            # --- Drawing Block 2: Playback & Volume Control (Middle) ---
            for el in controls + [mode_button, list_button, mute_button]:
                el.draw(screen)

            # Volume Label and Slider
            vol_label = font_small.render("音量", True, SECONDARY_TEXT_COLOR)
            vol_x_start = (SCREEN_WIDTH - (60 + 200 + 80 + 2 * 20)) // 2
            screen.blit(vol_label, (vol_x_start + 10, volume_slider.rect.centery - vol_label.get_height() // 2))
            volume_slider.draw(screen)

            # --- Drawing Block 3: File & Sync Settings (Bottom) ---
            # Labels for settings block - they are grid-aligned
            settings_x_start = (SCREEN_WIDTH - (88 + 250 + 3 * 62 + 4 * 8)) // 2

            folder_label = font_small.render("本地文件夹", True, SECONDARY_TEXT_COLOR)
            screen.blit(folder_label, (settings_x_start, folder_input_box.rect.centery - folder_label.get_height() // 2))

            phone_label = font_small.render("手机路径", True, SECONDARY_TEXT_COLOR)
            screen.blit(phone_label, (settings_x_start, phone_input_box.rect.centery - phone_label.get_height() // 2))

            # Draw Inputs and Buttons in Block 3
            folder_input_box.draw(screen)
            browse_button.draw(screen)
            reset_button.draw(screen)
            reset_playlist_button.draw(screen)

            phone_input_box.draw(screen)
            sync_phone_button.draw(screen)
            reset_sync_button.draw(screen)

            # Exit button and other general elements
            exit_button.draw(screen)

            # Playlist overlay
            playlist_ui.draw(screen)

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
                "duration": duration,
            }

        save_app_data(
            global_volume, music_folder, next_new_playlist_mode, playlists_data, phone_mappings
        )
        pygame.quit()
        sys.exit()


main()
