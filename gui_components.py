import os
import pygame
from tkinter import Tk, Toplevel, Label, Entry, Button as TkButton
from config import *


class Button:
    def __init__(self, rect, text, font, action=None, debounce_ms=250, is_secondary=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.action = action
        self.is_hovered = False
        self.disabled = False
        self.debounce_ms = debounce_ms
        self.last_click_time = 0
        self.is_secondary = is_secondary

    def draw(self, screen):
        if self.is_secondary:
            color = (
                DISABLED_BUTTON_COLOR
                if self.disabled
                else (50, 50, 70) if self.is_hovered else (30, 30, 45)
            )
            text_color = DISABLED_TEXT_COLOR if self.disabled else SECONDARY_TEXT_COLOR
            if self.is_hovered and not self.disabled:
                text_color = BUTTON_TEXT_COLOR
        else:
            color = (
                DISABLED_BUTTON_COLOR
                if self.disabled
                else BUTTON_HOVER_COLOR if self.is_hovered else BUTTON_COLOR
            )
            text_color = DISABLED_TEXT_COLOR if self.disabled else BUTTON_TEXT_COLOR

        pygame.draw.rect(screen, color, self.rect, border_radius=10)

        if not self.is_secondary and self.is_hovered and not self.disabled:
            # Subtle glow effect for main buttons
            for i in range(1, 4):
                pygame.draw.rect(screen, (*ACCENT_COLOR, 50//i), self.rect.inflate(i*2, i*2), 1, border_radius=10+i)
            pygame.draw.rect(screen, ACCENT_COLOR, self.rect, 2, border_radius=10)
        elif self.is_secondary:
            border_color = ACCENT_COLOR if self.is_hovered and not self.disabled else (60, 60, 80)
            pygame.draw.rect(screen, border_color, self.rect, 1, border_radius=10)

        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if self.disabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                current_time = pygame.time.get_ticks()
                if current_time - self.last_click_time > self.debounce_ms:
                    self.last_click_time = current_time
                    if self.action:
                        self.action()
                    return True
        return False


class Slider:
    def __init__(self, rect, min_val, max_val, initial_val, font):
        self.rect, self.min_val, self.max_val, self.val, self.font = (
            pygame.Rect(rect),
            min_val,
            max_val,
            initial_val,
            font,
        )
        self.dragging = False
        self.thumb_radius = self.rect.height // 2 + 2
        self._update_thumb_pos()

    def _update_thumb_pos(self):
        ratio = (
            (self.val - self.min_val) / (self.max_val - self.min_val)
            if (self.max_val - self.min_val) != 0
            else 0
        )
        self.thumb_x = self.rect.x + ratio * self.rect.width

    def draw(self, screen):
        pygame.draw.rect(
            screen, SLIDER_BAR_COLOR, self.rect, border_radius=self.rect.height // 2
        )
        color = ACCENT_COLOR_LIGHT if hasattr(self, 'dragging') and self.dragging else SLIDER_THUMB_COLOR
        pygame.draw.circle(
            screen,
            color,
            (int(self.thumb_x), self.rect.centery),
            self.thumb_radius,
        )
        highlight_color = tuple(min(255, c + 40) for c in color)
        pygame.draw.circle(
            screen,
            highlight_color,
            (int(self.thumb_x), self.rect.centery),
            max(2, self.thumb_radius - 3),
        )

    def handle_event(self, event, on_change_callback=None):
        if event.type not in (
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
            pygame.MOUSEMOTION,
        ):
            return False
        pos = event.pos
        thumb_hitbox = pygame.Rect(
            0, 0, self.thumb_radius * 2.5, self.rect.height * 2.5
        )
        thumb_hitbox.center = (self.thumb_x, self.rect.centery)
        is_over_thumb = thumb_hitbox.collidepoint(pos)
        is_over_bar = self.rect.collidepoint(pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if is_over_bar or is_over_thumb:
                self.dragging = True
                self._set_value_from_mouse(pos[0], on_change_callback)
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                if on_change_callback:
                    on_change_callback(self.val)
                return True
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._set_value_from_mouse(pos[0], on_change_callback)
                return True
        return False

    def _set_value_from_mouse(self, mouse_x, on_change_callback=None):
        if self.rect.width == 0:
            return
        self.val = self.min_val + ((mouse_x - self.rect.x) / self.rect.width) * (
            self.max_val - self.min_val
        )
        self.val = max(self.min_val, min(self.max_val, self.val))
        self._update_thumb_pos()
        if on_change_callback:
            on_change_callback(self.val)


class MusicProgressBar(Slider):
    def __init__(self, rect, font):
        super().__init__(rect, 0.0, 1.0, 0.0, font)
        self.thumb_radius = self.rect.height + 2

    def handle_event(self, event, on_seek_callback=None):
        if event.type not in (
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
            pygame.MOUSEMOTION,
        ):
            return False
        pos = event.pos
        is_over_bar = self.rect.collidepoint(pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if is_over_bar:
                self.dragging = True
                self._set_value_from_mouse(pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                if on_seek_callback:
                    on_seek_callback(self.val)
                return True
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._set_value_from_mouse(pos[0])
                return True
        return False

    def draw(self, screen, current_time, duration):
        if not self.dragging:
            self.val = current_time / duration if duration > 0 else 0
            self._update_thumb_pos()

        pygame.draw.rect(
            screen, SLIDER_BAR_COLOR, self.rect, border_radius=self.rect.height // 2
        )

        fill_rect = self.rect.copy()
        fill_rect.width = max(0, self.thumb_x - self.rect.x)
        if fill_rect.width > 0:
            pygame.draw.rect(
                screen, ACCENT_COLOR, fill_rect, border_radius=self.rect.height // 2
            )

        pygame.draw.circle(
            screen,
            ACCENT_COLOR_LIGHT if self.dragging else ACCENT_COLOR,
            (int(self.thumb_x), self.rect.centery),
            self.thumb_radius
        )

        highlight_color = ACCENT_COLOR_LIGHT if self.dragging else (180, 180, 255)
        pygame.draw.circle(
            screen,
            highlight_color,
            (int(self.thumb_x), self.rect.centery),
            self.thumb_radius - 3,
        )


class InputBox:
    def __init__(self, rect, font, initial_text="", placeholder_text="", on_change=None):
        self.rect, self.font, self.placeholder_text = (
            pygame.Rect(rect),
            font,
            placeholder_text,
        )
        self.text = initial_text
        self.composition = "" # IME 正在输入的未确认文字
        self.text_surface = None
        self.is_scrolling = False
        self.scroll_x = 0
        self.scroll_delay_start = 0
        self.is_active = False
        self.cursor_visible = True
        self.last_cursor_toggle = 0
        self.on_change = on_change
        self.SCROLL_DELAY_DURATION, self.SCROLL_SPEED = 2000, 30
        self.set_text(initial_text)

    def set_text(self, new_text):
        self.text = new_text
        self.scroll_x = 0
        self.is_scrolling = False
        self._update_surface()

    def _update_surface(self):
        # 组合显示文字 = 已确认文字 + 正在输入的未确认文字
        full_display_text = self.text + self.composition

        display_text, text_color = (
            (full_display_text, INPUT_BOX_TEXT_COLOR)
            if full_display_text
            else (self.placeholder_text, (150, 150, 150))
        )
        text_width = self.font.size(display_text)[0]
        if text_width > self.rect.width - 25:
            self.is_scrolling, self.scroll_delay_start = True, pygame.time.get_ticks()
            self.text_surface = self.font.render(
                display_text + " " * 10 + display_text, True, text_color
            )
        else:
            self.text_surface = self.font.render(display_text, True, text_color)

    def update(self, dt):
        if (
            self.is_scrolling
            and pygame.time.get_ticks() - self.scroll_delay_start
            > self.SCROLL_DELAY_DURATION
        ):
            self.scroll_x += self.SCROLL_SPEED * dt
            if self.scroll_x > self.text_surface.get_width() / 2:
                self.scroll_x, self.scroll_delay_start = 0, pygame.time.get_ticks()

        if self.is_active and pygame.time.get_ticks() - self.last_cursor_toggle > 500:
            self.cursor_visible = not self.cursor_visible
            self.last_cursor_toggle = pygame.time.get_ticks()

    def draw(self, screen):
        pygame.draw.rect(screen, INPUT_BOX_COLOR, self.rect, border_radius=5)
        border_color = ACCENT_COLOR if self.is_active else INPUT_BOX_BORDER_COLOR
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=5)

        if not self.text_surface:
            return

        clip_rect = self.rect.inflate(-20, -10)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        try:
            if self.is_scrolling:
                screen.blit(
                    self.text_surface,
                    clip_rect.topleft,
                    area=pygame.Rect(self.scroll_x, 0, clip_rect.width, clip_rect.height),
                )
            else:
                text_rect = self.text_surface.get_rect(midleft=(self.rect.x + 10, self.rect.centery))
                screen.blit(self.text_surface, text_rect)

                # 绘制未确认文字的下划线
                if self.composition:
                    confirmed_width = self.font.size(self.text)[0]
                    comp_width = self.font.size(self.composition)[0]
                    line_y = text_rect.bottom - 2
                    pygame.draw.line(screen, ACCENT_COLOR,
                                     (text_rect.x + confirmed_width, line_y),
                                     (text_rect.x + confirmed_width + comp_width, line_y), 2)

                # Draw cursor
                if self.is_active and self.cursor_visible:
                    # Cursor should be at the end of actual text (including composition), not placeholder
                    text_width = self.font.size(self.text + self.composition)[0] if (self.text or self.composition) else 0
                    cursor_x = self.rect.x + 10 + text_width
                    pygame.draw.line(screen, ACCENT_COLOR, (cursor_x, self.rect.y + 8), (cursor_x, self.rect.bottom - 8), 2)
        finally:
            screen.set_clip(old_clip)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.is_active = True
                pygame.key.start_text_input()
                pygame.key.set_text_input_rect(self.rect)
                return True
            else:
                if self.is_active:
                    self.is_active = False
                return False

        if not self.is_active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                self._update_surface()
                if self.on_change: self.on_change(self.text)
                return True
            elif event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                self.is_active = False
                self.composition = ""
                self._update_surface()
                return True
        elif event.type == pygame.TEXTEDITING:
            self.composition = event.text
            self._update_surface()
            return True
        elif event.type == pygame.TEXTINPUT:
            self.text += event.text
            self.composition = "" # 提交输入后清空组合字符串
            self._update_surface()
            if self.on_change: self.on_change(self.text)
            return True
        return False


def ask_phone_path():
    root = Tk()
    root.withdraw()

    dialog = Toplevel(root)
    dialog.title("输入手机路径")
    dialog.geometry("800x160")
    dialog.configure(bg="#1e1e2e")

    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - 400
    y = (dialog.winfo_screenheight() // 2) - 80
    dialog.geometry(f"800x160+{x}+{y}")

    result = {"path": None}

    Label(
        dialog,
        text="请输入或粘贴手机音乐文件夹的完整路径:",
        font=("微软雅黑", 12),
        fg="#ffffff",
        bg="#1e1e2e",
        pady=15
    ).pack()

    entry = Entry(
        dialog,
        font=("Consolas", 11),
        width=85,
        bg="#2a2a3d",
        fg="#ffffff",
        insertbackground="#ffffff",
        relief="flat",
        borderwidth=10
    )
    entry.pack(padx=30, pady=10)
    entry.focus_set()

    def ok_clicked():
        result["path"] = entry.get()
        dialog.quit()
        dialog.destroy()

    def cancel_clicked():
        result["path"] = None
        dialog.quit()
        dialog.destroy()

    button_frame = Label(dialog, bg="#1e1e2e")
    button_frame.pack(pady=10)

    TkButton(
        button_frame,
        text="确定",
        command=ok_clicked,
        width=12,
        font=("微软雅黑", 10),
        bg="#44475a",
        fg="#ffffff",
        activebackground="#6272a4",
        activeforeground="#ffffff",
        relief="flat"
    ).pack(side="left", padx=15)

    TkButton(
        button_frame,
        text="取消",
        command=cancel_clicked,
        width=12,
        font=("微软雅黑", 10),
        bg="#44475a",
        fg="#ffffff",
        activebackground="#ff5555",
        activeforeground="#ffffff",
        relief="flat"
    ).pack(side="left", padx=15)

    entry.bind('<Return>', lambda e: ok_clicked())
    entry.bind('<Escape>', lambda e: cancel_clicked())

    dialog.protocol("WM_DELETE_WINDOW", cancel_clicked)
    dialog.mainloop()

    root.destroy()
    return result["path"]


def ask_rename(initial_name):
    root = Tk()
    root.withdraw()

    dialog = Toplevel(root)
    dialog.title("重命名")
    dialog.geometry("800x160")
    dialog.configure(bg="#1e1e2e") # Use a dark background consistent with the app

    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - 400
    y = (dialog.winfo_screenheight() // 2) - 80
    dialog.geometry(f"800x160+{x}+{y}")

    result = {"name": None}

    Label(
        dialog,
        text="请输入新的文件名:",
        font=("微软雅黑", 12),
        fg="#ffffff",
        bg="#1e1e2e",
        pady=15
    ).pack()

    entry = Entry(
        dialog,
        font=("微软雅黑", 11),
        width=80,
        bg="#2a2a3d",
        fg="#ffffff",
        insertbackground="#ffffff", # Cursor color
        relief="flat",
        borderwidth=10
    )
    entry.insert(0, initial_name)
    entry.pack(padx=30, pady=10)
    entry.focus_set()
    entry.selection_range(0, 'end') # Select all text by default

    def ok_clicked():
        result["name"] = entry.get()
        dialog.quit()
        dialog.destroy()

    def cancel_clicked():
        result["name"] = None
        dialog.quit()
        dialog.destroy()

    button_frame = Label(dialog, bg="#1e1e2e")
    button_frame.pack(pady=10)

    TkButton(
        button_frame,
        text="确定",
        command=ok_clicked,
        width=12,
        font=("微软雅黑", 10),
        bg="#44475a",
        fg="#ffffff",
        activebackground="#6272a4",
        activeforeground="#ffffff",
        relief="flat"
    ).pack(side="left", padx=15)

    TkButton(
        button_frame,
        text="取消",
        command=cancel_clicked,
        width=12,
        font=("微软雅黑", 10),
        bg="#44475a",
        fg="#ffffff",
        activebackground="#ff5555",
        activeforeground="#ffffff",
        relief="flat"
    ).pack(side="left", padx=15)

    entry.bind('<Return>', lambda e: ok_clicked())
    entry.bind('<Escape>', lambda e: cancel_clicked())

    dialog.protocol("WM_DELETE_WINDOW", cancel_clicked)
    dialog.mainloop()

    root.destroy()
    return result["name"]


def ask_confirm(title, message):
    root = Tk()
    root.withdraw()

    dialog = Toplevel(root)
    dialog.title(title)
    dialog.geometry("500x180")
    dialog.configure(bg="#1e1e2e")

    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - 250
    y = (dialog.winfo_screenheight() // 2) - 90
    dialog.geometry(f"500x180+{x}+{y}")

    result = {"confirm": False}

    Label(
        dialog,
        text=message,
        font=("微软雅黑", 11),
        fg="#ffffff",
        bg="#1e1e2e",
        wraplength=440,
        pady=25
    ).pack()

    button_frame = Label(dialog, bg="#1e1e2e")
    button_frame.pack(pady=5)

    def ok_clicked():
        result["confirm"] = True
        dialog.quit()
        dialog.destroy()

    def cancel_clicked():
        result["confirm"] = False
        dialog.quit()
        dialog.destroy()

    TkButton(
        button_frame,
        text="确定",
        command=ok_clicked,
        width=10,
        font=("微软雅黑", 10),
        bg="#ff5555", # Red for destructive actions
        fg="#ffffff",
        activebackground="#ff6e6e",
        activeforeground="#ffffff",
        relief="flat"
    ).pack(side="left", padx=15)

    TkButton(
        button_frame,
        text="取消",
        command=cancel_clicked,
        width=10,
        font=("微软雅黑", 10),
        bg="#44475a",
        fg="#ffffff",
        activebackground="#6272a4",
        activeforeground="#ffffff",
        relief="flat"
    ).pack(side="left", padx=15)

    entry_hidden = Entry(dialog) # Just to catch Enter/Esc
    entry_hidden.bind('<Return>', lambda e: ok_clicked())
    entry_hidden.bind('<Escape>', lambda e: cancel_clicked())

    dialog.protocol("WM_DELETE_WINDOW", cancel_clicked)
    dialog.mainloop()

    root.destroy()
    return result["confirm"]


class Playlist:
    def __init__(self, rect, font, small_font):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.small_font = small_font
        self.items = [] # Original items (full paths)
        self.filtered_items = [] # Filtered items for display
        self.current_index = -1
        self.scroll_y = 0
        self.item_height = 40
        self.visible = False
        self.on_item_click = None
        self.is_hovered = False
        self.hover_index = -1
        self.on_delete = None
        self.on_rename = None
        self.icon_hover = None # 'delete' or 'rename'
        self.search_query = ""
        self.search_composition = "" # IME 正在输入的未确认文字
        self.search_active = False

    def _update_filter(self):
        if not self.search_query:
            self.filtered_items = [(i, item) for i, item in enumerate(self.items)]
        else:
            self.filtered_items = [
                (i, item) for i, item in enumerate(self.items)
                if self.search_query.lower() in os.path.basename(item).lower()
            ]
        self.scroll_y = 0

    def set_items(self, items, current_index):
        self.items = items
        self.current_index = current_index
        self._update_filter()
        # 当项数较多时，自动滚动到当前项
        if self.current_index >= 0 and not self.search_query:
            target_scroll = self.current_index * self.item_height - self.rect.height // 2
            max_scroll = max(0, len(self.filtered_items) * self.item_height - (self.rect.height - 60) + 20)
            self.scroll_y = max(0, min(max_scroll, target_scroll))
        else:
            self.scroll_y = 0

    def draw(self, screen):
        if not self.visible:
            return

        # 绘制背景遮罩
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # 绘制列表区域
        pygame.draw.rect(screen, BUTTON_COLOR, self.rect, border_radius=10)
        pygame.draw.rect(screen, ACCENT_COLOR, self.rect, 2, border_radius=10)

        # 绘制搜索栏
        search_rect = pygame.Rect(self.rect.x + 20, self.rect.y + 15, self.rect.width - 40, 35)
        pygame.draw.rect(screen, INPUT_BOX_COLOR, search_rect, border_radius=8)
        search_border_color = ACCENT_COLOR if (self.search_active or self.search_query) else (60, 60, 80)
        pygame.draw.rect(screen, search_border_color, search_rect, 1, border_radius=8)

        search_display_text = (self.search_query + self.search_composition) if (self.search_query or self.search_composition) else "输入关键词搜索..."
        search_color = BUTTON_TEXT_COLOR if (self.search_query or self.search_composition) else SECONDARY_TEXT_COLOR

        # 搜索提示文字
        search_label_surf = self.small_font.render("搜索:", True, ACCENT_COLOR)
        screen.blit(search_label_surf, (search_rect.x + 10, search_rect.centery - search_label_surf.get_height() // 2))

        search_text_surf = self.small_font.render(search_display_text, True, search_color)
        text_x = search_rect.x + 15 + search_label_surf.get_width()
        screen.blit(search_text_surf, (text_x, search_rect.centery - search_text_surf.get_height() // 2))

        # 绘制未确认文字的下划线
        if self.search_composition:
            confirmed_width = self.small_font.size(self.search_query)[0]
            comp_width = self.small_font.size(self.search_composition)[0]
            line_y = search_rect.centery + search_text_surf.get_height() // 2 - 2
            pygame.draw.line(screen, ACCENT_COLOR, (text_x + confirmed_width, line_y), (text_x + confirmed_width + comp_width, line_y), 2)

        # 绘制光标 (如果是活动状态)
        if self.search_active and (pygame.time.get_ticks() // 500) % 2 == 0:
            cursor_x = text_x + self.small_font.size(self.search_query + self.search_composition)[0]
            pygame.draw.line(screen, ACCENT_COLOR, (cursor_x, search_rect.y + 10), (cursor_x, search_rect.bottom - 10), 2)

        # 搜索结果统计
        count_text = f"找到 {len(self.filtered_items)} 首" if self.search_query else f"共 {len(self.items)} 首"
        count_surf = self.small_font.render(count_text, True, SECONDARY_TEXT_COLOR)
        screen.blit(count_surf, (search_rect.right - count_surf.get_width() - 10, search_rect.centery - count_surf.get_height() // 2))

        # 裁剪区域 (内部列表区域) - 避开搜索栏
        list_area_rect = pygame.Rect(self.rect.x + 10, self.rect.y + 60, self.rect.width - 20, self.rect.height - 80)
        old_clip = screen.get_clip()
        screen.set_clip(list_area_rect)

        try:
            for i, (orig_idx, item) in enumerate(self.filtered_items):
                item_y = list_area_rect.y + 10 + i * self.item_height - self.scroll_y
                # 优化绘制：只绘制可见区域内的项
                if item_y + self.item_height < list_area_rect.y or item_y > list_area_rect.bottom:
                    continue

                item_rect = pygame.Rect(self.rect.x + 10, item_y, self.rect.width - 20, self.item_height - 4)

                # 绘制选中或悬停效果
                if orig_idx == self.current_index:
                    pygame.draw.rect(screen, (60, 60, 100), item_rect, border_radius=5)
                    pygame.draw.rect(screen, ACCENT_COLOR, item_rect, 1, border_radius=5)
                    color = ACCENT_COLOR_LIGHT
                elif i == self.hover_index:
                    pygame.draw.rect(screen, (45, 45, 65), item_rect, border_radius=5)
                    color = BUTTON_TEXT_COLOR
                else:
                    color = SECONDARY_TEXT_COLOR

                # 绘制文件名
                filename = os.path.basename(item)
                name_without_ext = os.path.splitext(filename)[0]
                text_surface = self.small_font.render(f"{orig_idx+1}. {name_without_ext}", True, color)
                text_rect = text_surface.get_rect(midleft=(item_rect.x + 15, item_rect.centery))
                screen.blit(text_surface, text_rect)

                # 如果悬停，显示删除和重命名图标
                if i == self.hover_index:
                    rename_rect = pygame.Rect(item_rect.right - 80, item_rect.y + 5, 30, item_rect.height - 10)
                    delete_rect = pygame.Rect(item_rect.right - 40, item_rect.y + 5, 30, item_rect.height - 10)

                    r_color = ACCENT_COLOR if self.icon_hover == ('rename', i) else SECONDARY_TEXT_COLOR
                    r_surf = self.small_font.render("改", True, r_color)
                    screen.blit(r_surf, r_surf.get_rect(center=rename_rect.center))

                    d_color = (255, 100, 100) if self.icon_hover == ('delete', i) else SECONDARY_TEXT_COLOR
                    d_surf = self.small_font.render("删", True, d_color)
                    screen.blit(d_surf, d_surf.get_rect(center=delete_rect.center))
        finally:
            screen.set_clip(old_clip)

        # 绘制滚动条
        if len(self.filtered_items) * self.item_height > list_area_rect.height:
            scroll_bar_w = 6
            scroll_bar_h = (list_area_rect.height) ** 2 / (len(self.filtered_items) * self.item_height)
            scroll_bar_h = max(20, min(list_area_rect.height, scroll_bar_h))

            scroll_ratio = self.scroll_y / (len(self.filtered_items) * self.item_height - list_area_rect.height + 20)
            scroll_bar_y = list_area_rect.y + 10 + scroll_ratio * (list_area_rect.height - 20 - scroll_bar_h)

            pygame.draw.rect(
                screen,
                (100, 100, 100),
                (self.rect.right - 10, scroll_bar_y, scroll_bar_w, scroll_bar_h),
                border_radius=scroll_bar_w // 2
            )

    def handle_event(self, event):
        if not self.visible:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            search_rect = pygame.Rect(self.rect.x + 20, self.rect.y + 15, self.rect.width - 40, 35)
            if search_rect.collidepoint(event.pos):
                self.search_active = True
                pygame.key.start_text_input()
                pygame.key.set_text_input_rect(search_rect)
                return True
            else:
                self.search_active = False

            if not self.rect.collidepoint(event.pos):
                self.visible = False
                self.search_query = ""
                self.search_composition = ""
                self._update_filter()
                pygame.key.stop_text_input()
                return True

            if event.button == 1: # 左键点击
                list_area_rect = pygame.Rect(self.rect.x + 10, self.rect.y + 60, self.rect.width - 20, self.rect.height - 80)
                if list_area_rect.collidepoint(event.pos):
                    inner_y = event.pos[1] - list_area_rect.y - 10 + self.scroll_y
                    clicked_i = int(inner_y // self.item_height)
                    if 0 <= clicked_i < len(self.filtered_items):
                        orig_idx, item = self.filtered_items[clicked_i]

                        item_y = list_area_rect.y + 10 + clicked_i * self.item_height - self.scroll_y
                        item_rect = pygame.Rect(self.rect.x + 10, item_y, self.rect.width - 20, self.item_height - 4)
                        rename_rect = pygame.Rect(item_rect.right - 80, item_rect.y + 5, 30, item_rect.height - 10)
                        delete_rect = pygame.Rect(item_rect.right - 40, item_rect.y + 5, 30, item_rect.height - 10)

                        if rename_rect.collidepoint(event.pos):
                            if self.on_rename: self.on_rename(orig_idx)
                            return True
                        elif delete_rect.collidepoint(event.pos):
                            if self.on_delete: self.on_delete(orig_idx)
                            # 删除后需要更新过滤列表
                            # 注意：orig_idx 对应的项可能已经在外部被删除了，但这里我们先返回 True
                            return True

                        if self.on_item_click:
                            self.on_item_click(orig_idx)
                        return True
            elif event.button == 4: # 滚轮向上
                self.scroll_y = max(0, self.scroll_y - self.item_height * 3)
                return True
            elif event.button == 5: # 滚轮向下
                list_area_rect = pygame.Rect(self.rect.x + 10, self.rect.y + 60, self.rect.width - 20, self.rect.height - 80)
                max_scroll = max(0, len(self.filtered_items) * self.item_height - list_area_rect.height + 20)
                self.scroll_y = min(max_scroll, self.scroll_y + self.item_height * 3)
                return True

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search_query or self.search_composition:
                    self.search_query = ""
                    self.search_composition = ""
                    self._update_filter()
                else:
                    self.visible = False
                    pygame.key.stop_text_input()
                return True
            elif event.key == pygame.K_BACKSPACE:
                if self.search_query:
                    self.search_query = self.search_query[:-1]
                    self._update_filter()
                return True
            elif event.key == pygame.K_RETURN:
                if self.filtered_items:
                    orig_idx, _ = self.filtered_items[0]
                    if self.on_item_click:
                        self.on_item_click(orig_idx)
                return True
            # KEYDOWN 不再直接处理普通字符输入，交给 TEXTINPUT
            # 但我们需要返回 True 以拦截这些按键
            if event.unicode and event.unicode.isprintable():
                return True

        elif event.type == pygame.TEXTEDITING:
            self.search_composition = event.text
            self.search_active = True
            return True
        elif event.type == pygame.TEXTINPUT:
            self.search_query += event.text
            self.search_composition = ""
            self._update_filter()
            self.search_active = True
            return True

        elif event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                list_area_rect = pygame.Rect(self.rect.x + 10, self.rect.y + 60, self.rect.width - 20, self.rect.height - 80)
                if list_area_rect.collidepoint(event.pos):
                    relative_y = event.pos[1] - list_area_rect.y - 10
                    index = int((relative_y + self.scroll_y) // self.item_height)
                    if 0 <= index < len(self.filtered_items):
                        self.hover_index = index
                        # 检查图标悬停
                        item_y = list_area_rect.y + 10 + index * self.item_height - self.scroll_y
                        item_rect = pygame.Rect(self.rect.x + 10, item_y, self.rect.width - 20, self.item_height - 4)
                        rename_rect = pygame.Rect(item_rect.right - 80, item_rect.y + 5, 30, item_rect.height - 10)
                        delete_rect = pygame.Rect(item_rect.right - 40, item_rect.y + 5, 30, item_rect.height - 10)

                        if rename_rect.collidepoint(event.pos):
                            self.icon_hover = ('rename', index)
                        elif delete_rect.collidepoint(event.pos):
                            self.icon_hover = ('delete', index)
                        else:
                            self.icon_hover = None
                    else:
                        self.hover_index = -1
                        self.icon_hover = None
                else:
                    self.hover_index = -1
                    self.icon_hover = None
            else:
                self.hover_index = -1
                self.icon_hover = None
            return True

        return False

