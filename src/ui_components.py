# ui_components.py
# 通用UI组件：滚动文本区、选项按钮组、确认弹窗等

import pygame
from src.utils import (
    get_font, draw_text, draw_text_block, draw_button,
    draw_panel, is_mouse_over, wrap_text
)
from src.config import (
    COLOR_BG, COLOR_TEXT, COLOR_ACCENT, COLOR_SECONDARY,
    COLOR_LIGHT, COLOR_DARK, COLOR_RED, COLOR_GREEN, COLOR_GOLD, COLOR_BORDER,
    FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_LARGE
)


class ScrollTextArea:
    """可滚动的文本区域"""

    def __init__(self, rect, font=None, text_color=COLOR_TEXT,
                 bg_color=COLOR_LIGHT, border_color=COLOR_BORDER):
        self.rect = rect
        self.font = font if font else get_font(FONT_SIZE_NORMAL)
        self.text_color = text_color
        self.bg_color = bg_color
        self.border_color = border_color
        self.lines = []
        self.scroll_y = 0
        self.line_height = self.font.get_height() + 8
        self.padding = 15

    def set_text(self, text):
        """设置要显示的文本"""
        self.lines = wrap_text(text, self.font, self.rect.width - self.padding * 2 - 20)
        self.scroll_y = 0

    def append_text(self, text):
        """追加文本"""
        new_lines = wrap_text(text, self.font, self.rect.width - self.padding * 2 - 20)
        self.lines.extend(new_lines)

    def reveal_all_clues(self):
        """显示所有线索（ScrollTextArea 默认已显示全部内容，此方法用于兼容解谜逻辑）"""
        self.scroll_y = 0

    def handle_event(self, event):
        """处理滚动事件"""
        if event.type == pygame.MOUSEWHEEL and is_mouse_over(self.rect):
            self.scroll_y -= event.y * self.line_height * 3
            max_scroll = max(0, len(self.lines) * self.line_height - self.rect.height + self.padding * 2)
            self.scroll_y = max(-max_scroll, min(0, self.scroll_y))

    def draw(self, screen):
        """绘制文本区域"""
        # 绘制背景与边框
        draw_panel(screen, self.rect, self.bg_color, self.border_color)

        # 设置裁剪区域
        clip_rect = self.rect.copy()
        clip_rect.inflate_ip(-self.padding * 2, -self.padding * 2)
        screen.set_clip(clip_rect)

        start_y = self.rect.y + self.padding + self.scroll_y
        for i, line in enumerate(self.lines):
            y = start_y + i * self.line_height
            if y + self.line_height > self.rect.y and y < self.rect.y + self.rect.height:
                draw_text(screen, line, self.rect.x + self.padding, y,
                          self.font, self.text_color)

        screen.set_clip(None)

        # 绘制滚动条
        content_height = len(self.lines) * self.line_height + self.padding * 2
        if content_height > self.rect.height:
            visible_ratio = self.rect.height / content_height
            scrollbar_height = max(30, int(self.rect.height * visible_ratio))
            max_scroll = content_height - self.rect.height
            scroll_ratio = -self.scroll_y / max_scroll if max_scroll > 0 else 0
            scrollbar_y = self.rect.y + int((self.rect.height - scrollbar_height) * scroll_ratio)
            scrollbar_rect = pygame.Rect(
                self.rect.right - 10, scrollbar_y, 6, scrollbar_height
            )
            pygame.draw.rect(screen, COLOR_ACCENT, scrollbar_rect, border_radius=3)


class OptionButtonGroup:
    """选项按钮组，用于药材选择"""

    def __init__(self, rect, options, columns=4, font=None,
                 normal_color=COLOR_SECONDARY, selected_color=COLOR_GREEN,
                 text_color=COLOR_TEXT):
        self.rect = rect
        self.options = options
        self.columns = columns
        self.font = font if font else get_font(FONT_SIZE_NORMAL)
        self.normal_color = normal_color
        self.selected_color = selected_color
        self.text_color = text_color
        self.selected = []
        self.buttons = []
        self._build_buttons()

    def _build_buttons(self):
        """根据选项构建按钮矩形"""
        self.buttons = []
        margin = 10
        total_width = self.rect.width
        btn_width = (total_width - margin * (self.columns + 1)) // self.columns
        btn_height = 45
        for i, option in enumerate(self.options):
            col = i % self.columns
            row = i // self.columns
            x = self.rect.x + margin + col * (btn_width + margin)
            y = self.rect.y + margin + row * (btn_height + margin)
            self.buttons.append({
                "text": option,
                "rect": pygame.Rect(x, y, btn_width, btn_height),
                "index": i
            })

    def set_options(self, options):
        """更新选项"""
        self.options = options
        self.selected = []
        self._build_buttons()

    def get_hovered_option(self):
        """返回鼠标当前悬停的药材名。"""
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            if btn["rect"].collidepoint(mouse_pos):
                return btn["text"]
        return None

    def handle_event(self, event, max_select=None):
        """处理点击事件，max_select限制最大可选数量"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn["rect"].collidepoint(event.pos):
                    text = btn["text"]
                    if text in self.selected:
                        self.selected.remove(text)
                    else:
                        if max_select is None or len(self.selected) < max_select:
                            self.selected.append(text)
                    return text
        return None

    def draw(self, screen):
        """绘制所有选项按钮"""
        for btn in self.buttons:
            selected = btn["text"] in self.selected
            color = self.selected_color if selected else self.normal_color
            is_hover = is_mouse_over(btn["rect"])
            draw_button(screen, btn["rect"], btn["text"], self.font,
                        bg_color=color, text_color=self.text_color, hover=is_hover)
            if is_hover and not selected:
                pygame.draw.rect(screen, COLOR_ACCENT, btn["rect"], 2, border_radius=5)
            if selected:
                check_x = btn["rect"].right - 13
                check_y = btn["rect"].y + 12
                pygame.draw.circle(screen, COLOR_GOLD, (check_x, check_y), 7)
                pygame.draw.lines(screen, (250, 246, 228), False,
                                  [(check_x - 3, check_y), (check_x - 1, check_y + 3),
                                   (check_x + 4, check_y - 3)], 2)

    def get_selected(self):
        """返回当前选中的选项列表"""
        return self.selected.copy()

    def set_selected(self, selected):
        """设置选中的选项"""
        self.selected = selected.copy()


class SimplePopup:
    """简单弹窗，用于显示反馈、提示"""

    def __init__(self, width=600, height=300):
        self.width = width
        self.height = height
        self.visible = False
        self.title = ""
        self.content = ""
        self.buttons = []  # [(text, callback), ...]
        self.rect = None

    def show(self, title, content, buttons=None):
        """显示弹窗"""
        self.visible = True
        self.title = title
        self.content = content
        self.buttons = buttons if buttons else [("确定", None)]

    def close(self):
        """关闭弹窗"""
        self.visible = False

    def handle_event(self, event, screen_width, screen_height):
        """处理弹窗事件，返回被点击按钮索引或None"""
        if not self.visible:
            return None
        self.rect = pygame.Rect(
            (screen_width - self.width) // 2,
            (screen_height - self.height) // 2,
            self.width, self.height
        )
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            btn_width = 120
            btn_height = 45
            start_x = self.rect.centerx - (len(self.buttons) * btn_width + (len(self.buttons) - 1) * 20) // 2
            for i, (text, _) in enumerate(self.buttons):
                btn_rect = pygame.Rect(start_x + i * (btn_width + 20), self.rect.bottom - 70, btn_width, btn_height)
                if btn_rect.collidepoint(event.pos):
                    return i
        return None

    def draw(self, screen):
        """绘制弹窗"""
        if not self.visible:
            return
        if self.rect is None:
            self.rect = pygame.Rect(
                (screen.get_width() - self.width) // 2,
                (screen.get_height() - self.height) // 2,
                self.width,
                self.height
            )
        # 半透明遮罩
        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # 弹窗面板
        draw_panel(screen, self.rect, COLOR_LIGHT, COLOR_ACCENT, border_width=3)

        # 标题
        title_font = get_font(FONT_SIZE_LARGE)
        draw_text(screen, self.title, self.rect.centerx, self.rect.y + 25,
                  title_font, COLOR_ACCENT, center=True)

        # 内容
        content_font = get_font(FONT_SIZE_NORMAL)
        draw_text_block(screen, self.content, self.rect.x + 30, self.rect.y + 70,
                        self.rect.width - 60, content_font)

        # 按钮
        btn_width = 120
        btn_height = 45
        start_x = self.rect.centerx - (len(self.buttons) * btn_width + (len(self.buttons) - 1) * 20) // 2
        for i, (text, _) in enumerate(self.buttons):
            btn_rect = pygame.Rect(start_x + i * (btn_width + 20), self.rect.bottom - 70, btn_width, btn_height)
            is_hover = is_mouse_over(btn_rect)
            draw_button(screen, btn_rect, text, get_font(FONT_SIZE_NORMAL),
                        bg_color=COLOR_SECONDARY, hover=is_hover)
