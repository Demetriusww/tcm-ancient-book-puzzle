# utils.py
# 工具函数集合，包括文字渲染、按钮绘制、文字自动换行等

import math
import os
import pygame
from src.config import (
    COLOR_TEXT, COLOR_ACCENT, COLOR_LIGHT, COLOR_SECONDARY,
    COLOR_DARK, COLOR_BORDER, COLOR_GREEN, COLOR_GOLD, COLOR_GRAY,
    FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_LARGE, FONTS_DIR
)


_FONT_CACHE = {}

# 行楷负责卷首标题，隶书负责栏目题签，楷体负责正文和操作文字。
_FONT_FAMILIES = {
    "display": (
        r"C:\Windows\Fonts\STXINGKA.TTF",
        r"C:\Windows\Fonts\STKAITI.TTF",
        r"C:\Windows\Fonts\simkai.ttf",
        r"C:\Windows\Fonts\STSONG.TTF",
        r"C:\Windows\Fonts\simsun.ttc",
    ),
    "heading": (
        r"C:\Windows\Fonts\STLITI.TTF",
        r"C:\Windows\Fonts\STKAITI.TTF",
        r"C:\Windows\Fonts\simkai.ttf",
        r"C:\Windows\Fonts\STFANGSO.TTF",
        r"C:\Windows\Fonts\simfang.ttf",
    ),
    "body": (
        r"C:\Windows\Fonts\simkai.ttf",
        r"C:\Windows\Fonts\STKAITI.TTF",
        r"C:\Windows\Fonts\STFANGSO.TTF",
        r"C:\Windows\Fonts\simfang.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ),
}

_SYSTEM_FONT_NAMES = {
    "display": ("STXingkai", "华文行楷", "STKaiti", "KaiTi"),
    "heading": ("STLiti", "华文隶书", "STKaiti", "KaiTi"),
    "body": ("KaiTi", "楷体", "STKaiti", "FangSong", "SimSun"),
}

_ASSET_FONT_FILES = {
    "display": (
        "MaShanZheng-Regular.ttf",
        "LXGWWenKai-Regular.ttf",
        "NotoSerifSC-Regular.otf",
    ),
    "heading": (
        "MaShanZheng-Regular.ttf",
        "LXGWWenKai-Regular.ttf",
        "NotoSerifSC-Regular.otf",
    ),
    "body": (
        "ZCOOLXiaoWei-Regular.ttf",
        "LXGWWenKai-Regular.ttf",
        "NotoSerifSC-Regular.otf",
        "MaShanZheng-Regular.ttf",
    ),
}


def _find_asset_font(family="body"):
    """查找项目字体，标题与正文使用不同字形以保持层次。"""
    if not os.path.exists(FONTS_DIR):
        return None

    for filename in _ASSET_FONT_FILES.get(family, ()):
        candidate = os.path.join(FONTS_DIR, filename)
        if os.path.exists(candidate):
            return candidate

    for name in os.listdir(FONTS_DIR):
        if name.lower().endswith((".ttf", ".ttc", ".otf")):
            return os.path.join(FONTS_DIR, name)
    return None


def _font_family_for(size, bold, family):
    """根据字号与字重分配字体角色，未指定时保持现有调用方式可用。"""
    if family in _FONT_FAMILIES:
        return family
    if bold and size >= 32:
        return "display"
    if bold and size >= 20:
        return "heading"
    return "body"


def _find_family_font(family):
    """按字体角色查找本地字体，项目自带字体具有最高优先级。"""
    asset_font = _find_asset_font(family)
    if asset_font:
        return asset_font

    for path in _FONT_FAMILIES[family]:
        if os.path.exists(path):
            return path

    for name in _SYSTEM_FONT_NAMES[family]:
        try:
            matched_font = pygame.font.match_font(name)
        except Exception:
            matched_font = None
        if matched_font:
            return matched_font
    return None


def get_font(size, bold=False, family=None):
    """获取指定大小与角色的中文字体，并缓存字体对象。"""
    # 确保字体模块已初始化
    if not pygame.font.get_init():
        pygame.font.init()

    family = _font_family_for(size, bold, family)
    cache_key = (family, size, bool(bold))
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    font_path = _find_family_font(family)
    if font_path:
        try:
            font = pygame.font.Font(font_path, size)
            # 行楷和隶书本身已有鲜明笔画，正文才使用人工加粗强调。
            if bold and family == "body":
                font.set_bold(True)
            _FONT_CACHE[cache_key] = font
            return font
        except Exception:
            pass

    # 找不到字体文件时，再尝试系统字体名称。
    for name in _SYSTEM_FONT_NAMES[family]:
        try:
            font = pygame.font.SysFont(name, size)
            # 简单验证：看是否能渲染一个常见汉字
            if font.render("中", True, (0, 0, 0)).get_width() > 0:
                if bold and family == "body":
                    font.set_bold(True)
                _FONT_CACHE[cache_key] = font
                return font
        except Exception:
            continue

    # 若都失败，使用系统默认字体（可能无法显示中文）。
    print("警告：未找到中文字体，文字可能显示为方块。请将中文字体文件放入 assets/fonts/ 目录。")
    font = pygame.font.Font(None, size)
    font.set_bold(bold)
    _FONT_CACHE[cache_key] = font
    return font


# 预加载常用字体对象
font_small = get_font(FONT_SIZE_SMALL)
font_normal = get_font(FONT_SIZE_NORMAL)
font_large = get_font(FONT_SIZE_LARGE)


def draw_text(screen, text, x, y, font=font_normal, color=COLOR_TEXT, center=False):
    """在屏幕上绘制单行文字"""
    if text is None:
        return
    surface = font.render(str(text), True, color)
    rect = surface.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    screen.blit(surface, rect)


def draw_text_block(screen, text, x, y, max_width, font=font_normal,
                    color=COLOR_TEXT, line_spacing=8):
    """绘制自动换行的多行文字，返回实际占用高度"""
    lines = wrap_text(text, font, max_width)
    current_y = y
    for line in lines:
        draw_text(screen, line, x, current_y, font, color)
        current_y += font.get_height() + line_spacing
    return current_y - y


def wrap_text(text, font, max_width):
    """将长文本按指定宽度自动换行"""
    if text is None:
        return []
    text = str(text)
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current_line = ""
        for char in paragraph:
            test_line = current_line + char
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
    return lines


def draw_button(screen, rect, text, font=font_normal,
                bg_color=COLOR_SECONDARY, text_color=COLOR_TEXT,
                border_color=COLOR_BORDER, hover=False):
    """绘制带纸张阴影与药签质感的按钮，hover 时微微提亮。"""
    color = bg_color
    if hover:
        color = tuple(min(255, c + 22) for c in bg_color)

    draw_rect = rect.move(0, -2) if hover else rect
    shadow_rect = draw_rect.move(3, 6 if hover else 4)
    pygame.draw.rect(screen, (117, 101, 78), shadow_rect, border_radius=5)
    pygame.draw.rect(screen, color, draw_rect, border_radius=5)
    top_color = tuple(min(255, c + 18) for c in color)
    pygame.draw.line(screen, top_color, (draw_rect.x + 8, draw_rect.y + 2),
                     (draw_rect.right - 8, draw_rect.y + 2), 1)
    pygame.draw.rect(screen, border_color, draw_rect, width=2, border_radius=5)
    pygame.draw.line(screen, (*border_color,), (draw_rect.x + 7, draw_rect.centery),
                     (draw_rect.x + 7, draw_rect.bottom - 9), 2)

    luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
    render_color = text_color
    if text_color == COLOR_TEXT and luminance < 125:
        render_color = (248, 242, 222)
    text_surface = font.render(str(text), True, render_color)
    text_rect = text_surface.get_rect(center=draw_rect.center)
    screen.blit(text_surface, text_rect)


def draw_page_heading(screen, title, subtitle="", kicker="岐黄手札",
                      time=0.0, y=24, title_size=40, compact=False):
    """绘制带动态墨线的页面标题，形成统一而活泼的卷首版式。"""
    center_x = screen.get_width() // 2
    if compact:
        y = max(10, y - 8)

    kicker_font = get_font(14, bold=True)
    kicker_surface = kicker_font.render(kicker, True, COLOR_LIGHT)
    kicker_width = max(96, kicker_surface.get_width() + 34)
    kicker_rect = pygame.Rect(center_x - kicker_width // 2, y, kicker_width, 24)
    pygame.draw.rect(screen, COLOR_ACCENT, kicker_rect, border_radius=3)
    pygame.draw.rect(screen, COLOR_GOLD, kicker_rect.inflate(-4, -4), 1, border_radius=2)
    screen.blit(kicker_surface, kicker_surface.get_rect(center=kicker_rect.center))

    title_font = get_font(
        title_size - (4 if compact else 0), bold=True, family="display"
    )
    title_gap = 8 if compact else 12
    if compact and title_size >= 48:
        # 卷首大标题的行楷笔画会向上伸展，额外留白可避免与栏目签重叠。
        title_gap = 15
    title_center_y = (
        kicker_rect.bottom + title_gap + title_font.get_height() // 2
    )
    draw_text(
        screen, title, center_x, title_center_y,
        title_font, COLOR_DARK, center=True
    )

    title_width = title_font.size(title)[0]
    underline_half = min(190, max(74, title_width // 2 + 28))
    breathe = math.sin(time * 2.2) * 7
    underline_y = title_center_y + title_font.get_height() // 2 + 8
    pygame.draw.line(screen, COLOR_ACCENT,
                     (center_x - underline_half - breathe, underline_y),
                     (center_x + underline_half + breathe, underline_y), 3)
    pygame.draw.circle(screen, COLOR_GOLD,
                       (center_x - underline_half - breathe - 7, underline_y), 3)
    pygame.draw.circle(screen, COLOR_GOLD,
                       (center_x + underline_half + breathe + 7, underline_y), 3)

    if subtitle:
        subtitle_y = underline_y + (20 if compact else 25)
        draw_text(screen, subtitle, center_x, subtitle_y,
                  get_font(16 if compact else 18), COLOR_GRAY, center=True)


def draw_section_label(screen, text, x, y, trailing="", line_end=None,
                       color=COLOR_DARK, trailing_y_offset=27):
    """绘制带朱砂书签和细墨线的栏目标题。"""
    accent_rect = pygame.Rect(x, y + 3, 5, 25)
    pygame.draw.rect(screen, COLOR_ACCENT, accent_rect, border_radius=2)
    label_font = get_font(25, bold=True, family="heading")
    draw_text(screen, text, x + 14, y, label_font, color)

    line_start = x + 20 + label_font.size(text)[0]
    line_end = line_end if line_end is not None else line_start + 120
    if line_end > line_start:
        pygame.draw.line(screen, COLOR_BORDER, (line_start, y + 17),
                         (line_end, y + 17), 1)
    if trailing:
        trailing_font = get_font(14)
        trailing_surface = trailing_font.render(trailing, True, COLOR_GRAY)
        screen.blit(trailing_surface,
                    (line_end - trailing_surface.get_width(),
                     y + trailing_y_offset))


def draw_slider(screen, rect, value, fill_color=COLOR_ACCENT, hover=False):
    """绘制带可按圆钮的横向滑杆。"""
    value = max(0.0, min(1.0, value))
    track = pygame.Rect(rect.x, rect.centery - 5, rect.width, 10)
    pygame.draw.rect(screen, (182, 170, 146), track, border_radius=5)
    fill_width = max(8, int(track.width * value))
    pygame.draw.rect(screen, fill_color,
                     pygame.Rect(track.x, track.y, fill_width, track.height),
                     border_radius=5)
    knob_x = track.x + int(track.width * value)
    knob_radius = 11 if hover else 9
    pygame.draw.circle(screen, (94, 70, 48), (knob_x + 2, track.centery + 2), knob_radius)
    pygame.draw.circle(screen, COLOR_LIGHT, (knob_x, track.centery), knob_radius)
    pygame.draw.circle(screen, fill_color, (knob_x, track.centery), knob_radius, 3)


def draw_reveal_text_block(screen, text, x, y, max_width, font=font_normal,
                           color=COLOR_TEXT, line_spacing=8,
                           elapsed=1.0, chars_per_second=42):
    """逐行展开正文，返回正文高度与是否播放完毕。"""
    lines = wrap_text(text, font, max_width)
    remaining = max(1, int(elapsed * chars_per_second))
    current_y = y
    complete = True
    for line in lines:
        if remaining <= 0:
            complete = False
            break
        visible_line = line[:remaining]
        draw_text(screen, visible_line, x, current_y, font, color)
        remaining -= max(1, len(line) + 3)
        current_y += font.get_height() + line_spacing

    if not complete:
        cursor_y = current_y - font.get_height() - line_spacing
        draw_text(screen, "▌", x + font.size(" ")[0], cursor_y, font, COLOR_ACCENT)
    return current_y - y, complete


def draw_panel(screen, rect, color=COLOR_LIGHT, border_color=COLOR_BORDER, border_width=2):
    """绘制带淡墨投影与双层纸边的面板。"""
    shadow_rect = rect.move(4, 5)
    pygame.draw.rect(screen, (196, 184, 162), shadow_rect, border_radius=6)
    pygame.draw.rect(screen, color, rect, border_radius=6)
    inner_rect = rect.inflate(-8, -8)
    pygame.draw.rect(screen, tuple(min(255, c + 25) for c in border_color),
                     inner_rect, width=1, border_radius=4)
    pygame.draw.rect(screen, border_color, rect, border_width, border_radius=6)


def draw_title_bar(screen, title, y=30, font=font_large, color=COLOR_ACCENT):
    """绘制居中的标题文字"""
    draw_text(screen, title, screen.get_width() // 2, y, font, color, center=True)


def draw_info_line(screen, text, x, y, label_color=COLOR_ACCENT, value_color=COLOR_TEXT):
    """绘制带标签的信息行，格式为 '标签：内容'"""
    if "：" in text:
        label, value = text.split("：", 1)
        label_surface = font_normal.render(label + "：", True, label_color)
        value_surface = font_normal.render(value, True, value_color)
        screen.blit(label_surface, (x, y))
        screen.blit(value_surface, (x + label_surface.get_width(), y))
    else:
        draw_text(screen, text, x, y, font_normal, value_color)


def is_mouse_over(rect):
    """判断鼠标是否在指定矩形区域内"""
    mouse_pos = pygame.mouse.get_pos()
    return rect.collidepoint(mouse_pos)


def draw_progress_bar(screen, rect, progress, bg_color=COLOR_SECONDARY,
                      fill_color=COLOR_ACCENT, border_color=COLOR_BORDER):
    """绘制进度条，progress范围0-1"""
    pygame.draw.rect(screen, bg_color, rect, border_radius=4)
    fill_width = int(rect.width * max(0, min(1, progress)))
    if fill_width > 0:
        fill_rect = pygame.Rect(rect.x, rect.y, fill_width, rect.height)
        pygame.draw.rect(screen, fill_color, fill_rect, border_radius=4)
    pygame.draw.rect(screen, border_color, rect, width=2, border_radius=4)


def truncate_text(text, font, max_width):
    """如果文字过长，截断并加省略号"""
    if font.size(text)[0] <= max_width:
        return text
    ellipsis = "..."
    for i in range(len(text), 0, -1):
        truncated = text[:i] + ellipsis
        if font.size(truncated)[0] <= max_width:
            return truncated
    return ellipsis
