# main.py
# 中医古籍解谜文字游戏 - 主程序入口

import asyncio
import datetime
import math
import os
import random
import sys
import pygame

IS_WEB = sys.platform in ("emscripten", "wasi")

if not IS_WEB:
    import ctypes

# 确保能正确导入src下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, COLOR_BG, COLOR_TEXT, COLOR_ACCENT,
    COLOR_SECONDARY, COLOR_LIGHT, COLOR_DARK, COLOR_RED, COLOR_GREEN, COLOR_GOLD,
    COLOR_GRAY, COLOR_BORDER,
    STATE_MENU, STATE_PROLOGUE, STATE_CHAPTER, STATE_INTRO, STATE_PUZZLE,
    STATE_ARCHIVE, STATE_REVIEW, STATE_SETTINGS, STATE_ENDING,
    MUSIC_DIR
)
from src.data_manager import DataManager
from src.save_manager import SaveManager
from src.puzzle_system import PuzzleSystem
from src.archive_system import ArchiveSystem
from src.review_system import ReviewSystem
from src.settings_manager import SettingsManager
from src.utils import (
    get_font, draw_text, draw_text_block, draw_button, draw_panel,
    is_mouse_over, draw_progress_bar, draw_page_heading, draw_section_label,
    draw_slider, draw_reveal_text_block, wrap_text, truncate_text,
    font_normal, font_large, font_small
)
from src.ui_components import ScrollTextArea, OptionButtonGroup, SimplePopup
from src.tcm_scene import TCMScene, get_herb_lore, draw_chapter_emblem


FOOTER_QUOTES = {
    STATE_PROLOGUE: [
        "落笔便是缘，先给自己取一个好听的名号。",
        "每一部残卷，都在等一位有耐心的修复师。",
        "别怕慢，慢工才能把古人的心意接住。",
    ],
    STATE_MENU: [
        "今日也来替古方续上一笔吧。",
        "好方子经得起推敲，好故事值得慢慢读。",
        "药香已备好，只差你翻开下一页。",
    ],
    STATE_CHAPTER: [
        "挑一卷顺眼的古籍，今天就从这里入局。",
        "修好一页不算少，每页都有它的光。",
        "前方有方剂，也有一点点小惊喜。",
    ],
    STATE_INTRO: [
        "先听古人把话说完，再落笔也不迟。",
        "每一段前言，都是下一场推理的钥匙。",
        "把心静下来，残卷的脉络会自己浮现。",
    ],
    STATE_PUZZLE: [
        "别急，君臣佐使正在等你排座次。",
        "每拆开一条线索，残卷就亮一分。",
        "选错也有收获，岐黄路上没有白走的一步。",
        "先抓住君药，再慢慢理顺其余药味。",
    ],
    STATE_ENDING: [
        "这一卷修完了，你的名字也留在了纸上。",
        "篇末不是终点，是另一册古籍的扉页。",
        "今日落下的每一笔，都算岐黄传承的一部分。",
    ],
    STATE_ARCHIVE: [
        "旧方重读，常读常新。",
        "翻开一页图鉴，就是和一位古人打个照面。",
        "把好方子记住，也把好故事带走。",
    ],
    STATE_REVIEW: [
        "错题不是脚印，是下一次辨药的路标。",
        "想不通的地方，正好值得再看一眼。",
        "复盘一题，胜过错过十题。",
    ],
    STATE_SETTINGS: [
        "调成舒服的节奏，才能读得更久。",
        "字快字慢都好，读进去才是正经事。",
        "听见风声，也听见自己慢慢入卷的声音。",
    ],
}

DAILY_HERBS = [
    "桂枝", "白芍", "当归", "黄芪", "柴胡", "麦冬",
    "连翘", "茯苓", "陈皮", "甘草", "桑叶", "菊花",
]


def _enable_high_dpi_awareness():
    """Keep the 1024x768 canvas from being clipped on Windows high-DPI screens."""
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


class Game:
    """游戏主类，负责状态管理和主循环"""

    def __init__(self):
        if not IS_WEB:
            _enable_high_dpi_awareness()
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error as exc:
            print(f"音频初始化失败，已继续静音运行：{exc}")

        if IS_WEB:
            # Pygbag 的网页画布由外层 CSS 缩放，不使用桌面端的 SCALED 标志。
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        else:
            self.screen = pygame.display.set_mode(
                (SCREEN_WIDTH, SCREEN_HEIGHT),
                pygame.SCALED | pygame.RESIZABLE,
            )
        pygame.display.set_caption("古籍解谜｜中医传承")
        self.clock = pygame.time.Clock()
        self.running = True
        self.scene = TCMScene(SCREEN_WIDTH, SCREEN_HEIGHT)

        # 初始化数据与存档
        self.data_manager = DataManager()
        self.save_manager = SaveManager()
        self.archive_system = ArchiveSystem(self.data_manager, self.save_manager)
        self.review_system = ReviewSystem(self.save_manager, self.data_manager)
        self.settings_manager = SettingsManager(self.save_manager)

        # 游戏状态，首次运行进入角色设定界面
        self.state = STATE_PROLOGUE if self.save_manager.is_first_run() else STATE_MENU
        self.previous_state = None

        # 当前章节与谜题
        self.current_chapter = None
        self.current_puzzle_index = 0
        self.current_puzzle_system = None

        # 玩家角色信息
        self.player_name = self.save_manager.get_player_name()
        self.role_title = self.data_manager.get_settings().get("role_title", "古籍修复师")
        self.prologue_text = self.data_manager.get_settings().get("prologue", "")

        # UI 组件
        self.clue_area = None
        self.option_group = None
        self.popup = SimplePopup(width=640, height=400)
        self.archive_scroll = None
        self.review_scroll = None
        self.settings_scroll = None

        # 文字缺失补全的输入框
        self.missing_inputs = []
        self.active_input_index = -1

        # 角色设定界面输入框
        self.name_input_active = True
        self.cursor_visible = True
        self.cursor_timer = 0

        # 页面节奏与互动状态
        self.ui_time = 0.0
        self.state_time = 0.0
        self.footer_quote_index = {state: 0 for state in FOOTER_QUOTES}
        self.footer_hover = False
        self.footer_flash_timer = 0.0
        self.intro_skip_reveal = False
        self.puzzle_clue_opened = []
        self.archive_tab = "explanation"
        self.archive_focus_index = 0
        self.archive_page = 0
        self.review_tab = "hint"
        self.review_focus_index = 0
        self.review_page = 0
        self.dragging_slider = None

        # 章节选择按钮
        self.chapter_buttons = []
        self.menu_buttons = []
        self._init_menu_buttons()

        # 音乐相关
        self.music_loaded = False
        self._load_music()
        self._apply_music_settings()

    def _load_music(self):
        """尝试加载背景音乐"""
        # 查找music目录下的音乐文件
        music_files = []
        if os.path.exists(MUSIC_DIR):
            for f in os.listdir(MUSIC_DIR):
                if f.lower().endswith((".mp3", ".ogg", ".wav")):
                    music_files.append(os.path.join(MUSIC_DIR, f))

        if music_files:
            try:
                pygame.mixer.music.load(music_files[0])
                self.music_loaded = True
            except Exception as e:
                print(f"音乐加载失败：{e}")
                self.music_loaded = False

    def _apply_music_settings(self):
        """应用音乐设置"""
        if not self.music_loaded:
            return
        volume = self.settings_manager.get_music_volume()
        pygame.mixer.music.set_volume(volume)
        if self.settings_manager.is_music_on():
            pygame.mixer.music.play(-1)
        else:
            pygame.mixer.music.stop()

    def _init_menu_buttons(self):
        """初始化主菜单按钮"""
        btn_width = 370
        btn_height = 60
        start_y = 152
        gap = 12
        labels = [
            ("开始解谜", "启", "挑一卷残页，循着药香入局", COLOR_ACCENT,
             lambda: self.set_state(STATE_CHAPTER)),
            ("古籍图鉴", "鉴", "回看已修方剂与名医医案", COLOR_GREEN,
             lambda: self.set_state(STATE_ARCHIVE)),
            ("错题复盘", "复", "折一枚错题药签，温故再练", COLOR_RED,
             lambda: self.set_state(STATE_REVIEW)),
            ("游戏设置", "调", "调好字迹速度与案前乐声", COLOR_SECONDARY,
             lambda: self.set_state(STATE_SETTINGS)),
            ("退出游戏", "归", "合上今日卷册，改日再会", COLOR_GRAY,
             lambda: self.quit_game())
        ]
        self.menu_buttons = []
        for i, (label, tag, hint, accent, action) in enumerate(labels):
            rect = pygame.Rect(
                508,
                start_y + i * (btn_height + gap),
                btn_width, btn_height
            )
            self.menu_buttons.append({
                "text": label,
                "tag": tag,
                "hint": hint,
                "accent": accent,
                "rect": rect,
                "action": action,
            })

    def _get_daily_herb(self):
        """按日期从本草名录中取今日药材。"""
        index = datetime.date.today().toordinal() % len(DAILY_HERBS)
        return DAILY_HERBS[index]

    def _get_menu_herb_rect(self):
        """返回主菜单今日药材卡区域。"""
        return pygame.Rect(142, 150, 332, 438)

    def set_state(self, new_state):
        """切换游戏状态"""
        self.previous_state = self.state
        self.state = new_state
        self.state_time = 0.0

        # 根据新状态初始化对应界面
        if new_state == STATE_CHAPTER:
            self._init_chapter_screen()
        elif new_state == STATE_INTRO:
            self.intro_skip_reveal = False
        elif new_state == STATE_ENDING:
            self.intro_skip_reveal = False
        elif new_state == STATE_ARCHIVE:
            self._init_archive_screen()
        elif new_state == STATE_REVIEW:
            self._init_review_screen()
        elif new_state == STATE_SETTINGS:
            self._init_settings_screen()

    def quit_game(self):
        """退出游戏"""
        self.running = False

    def _format_text(self, text):
        """替换文本中的玩家角色占位符"""
        if text is None:
            return ""
        name = self.player_name if self.player_name else "年轻的修复师"
        return text.replace("{player_name}", name)

    def _allow_scene_hotspots(self):
        """在不会被主内容遮挡的界面启用百草柜互动。"""
        return (
            not self.popup.visible
            and self.state not in (STATE_PUZZLE, STATE_ARCHIVE, STATE_REVIEW)
        )

    def _show_herb_note(self, herb_name):
        """显示一条本草札记。"""
        lore = get_herb_lore(herb_name)
        content = (
            f"性味：{lore['nature']}\n"
            f"归经：{lore['meridian']}\n"
            f"功效：{lore['effect']}\n\n"
            f"{lore['note']}\n\n"
            "本草内容仅作传统文化科普，不构成用药建议。"
        )
        self.popup.show(f"本草札记｜{herb_name}", content, [("知道了", None)])

    def _footer_rect(self):
        """返回页脚鼓励签的固定区域。"""
        return pygame.Rect(112, 720, 800, 38)

    def _footer_change_rect(self):
        """返回页脚换签按钮区域。"""
        return pygame.Rect(826, 725, 76, 27)

    def _draw_page_footer(self):
        """绘制每页底部的动态鼓励药签。"""
        rect = self._footer_rect()
        change_rect = self._footer_change_rect()
        quotes = FOOTER_QUOTES.get(self.state, FOOTER_QUOTES[STATE_MENU])
        quote = quotes[self.footer_quote_index.get(self.state, 0) % len(quotes)]

        band = pygame.Surface(rect.size, pygame.SRCALPHA)
        flash_alpha = int(28 * min(1.0, self.footer_flash_timer / 0.5))
        band.fill((250, 247, 236, 224))
        if flash_alpha:
            band.fill((*COLOR_GOLD, flash_alpha))
        screen_rect = band.get_rect()
        pygame.draw.rect(band, (*COLOR_BORDER, 185), screen_rect, 1, border_radius=3)
        pygame.draw.line(band, (*COLOR_ACCENT, 150), (72, 5), (72, rect.height - 5), 2)
        self.screen.blit(band, rect.topleft)

        seal_rect = pygame.Rect(rect.x + 8, rect.y + 7, 56, 24)
        pygame.draw.rect(self.screen, COLOR_ACCENT, seal_rect, border_radius=3)
        draw_text(self.screen, "今日药签", seal_rect.centerx, seal_rect.centery,
                  get_font(13, bold=True), COLOR_LIGHT, center=True)

        bob = math.sin(self.ui_time * 2.4) * 1.2
        draw_text(self.screen, quote, rect.centerx + 12, rect.centery + bob,
                  get_font(16), COLOR_DARK, center=True)

        pulse = 2 + int((math.sin(self.ui_time * 4.0) + 1) * 1.5)
        pygame.draw.circle(self.screen, COLOR_GOLD,
                           (change_rect.x - 13, change_rect.centery), pulse)
        hover = is_mouse_over(change_rect)
        tag_color = COLOR_GREEN if hover else COLOR_SECONDARY
        draw_button(self.screen, change_rect, "换一签", get_font(14),
                    bg_color=tag_color, hover=hover)

    def _handle_footer_event(self, event):
        """处理底部换签互动，返回是否消费当前事件。"""
        if event.type == pygame.MOUSEMOTION:
            self.footer_hover = self._footer_rect().collidepoint(event.pos)
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._footer_rect().collidepoint(event.pos):
                quotes = FOOTER_QUOTES.get(self.state, FOOTER_QUOTES[STATE_MENU])
                current = self.footer_quote_index.get(self.state, 0)
                self.footer_quote_index[self.state] = (current + 1) % len(quotes)
                self.footer_flash_timer = 0.5
                self.scene.burst_herb(event.pos, COLOR_GOLD)
                return True
        return False

    def _get_global_nav_rects(self):
        """返回所有页面共用的回退与退出按钮区域。"""
        rects = {"quit": pygame.Rect(166, 14, 72, 30)}
        if self.state not in (STATE_MENU, STATE_PROLOGUE):
            rects["back"] = pygame.Rect(90, 14, 70, 30)
        return rects

    def _draw_global_nav(self):
        """绘制始终可用的回退与退出入口。"""
        rects = self._get_global_nav_rects()
        if "back" in rects:
            back_rect = rects["back"]
            draw_button(
                self.screen, back_rect, "回退", get_font(14),
                bg_color=COLOR_SECONDARY,
                hover=is_mouse_over(back_rect)
            )
        quit_rect = rects["quit"]
        draw_button(
            self.screen, quit_rect, "退出", get_font(14),
            bg_color=COLOR_RED,
            hover=is_mouse_over(quit_rect)
        )

    def _show_exit_confirm(self):
        """显示全局退出确认。"""
        self.popup.show(
            "暂离卷册",
            "当前游戏进度会自动保存。要退出游戏，还是继续修卷？",
            [("继续游玩", None), ("退出游戏", self.quit_game)]
        )

    def _go_back(self):
        """按当前页面返回上一级。"""
        back_targets = {
            STATE_CHAPTER: STATE_MENU,
            STATE_INTRO: STATE_CHAPTER,
            STATE_PUZZLE: STATE_CHAPTER,
            STATE_ENDING: STATE_CHAPTER,
            STATE_ARCHIVE: STATE_MENU,
            STATE_REVIEW: STATE_MENU,
            STATE_SETTINGS: STATE_MENU,
        }
        target = back_targets.get(self.state)
        if target:
            self.scene.burst_herb((124, 29), COLOR_GOLD)
            self.set_state(target)

    def _handle_global_nav_event(self, event):
        """处理全局回退、退出按钮和 Esc 快捷键。"""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.state in (STATE_MENU, STATE_PROLOGUE):
                self._show_exit_confirm()
            else:
                self._go_back()
            return True

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        rects = self._get_global_nav_rects()
        if rects["quit"].collidepoint(event.pos):
            self.scene.burst_herb(event.pos, COLOR_RED)
            self._show_exit_confirm()
            return True
        if "back" in rects and rects["back"].collidepoint(event.pos):
            self._go_back()
            return True
        return False

    # ==================== 角色设定界面 ====================

    def _draw_prologue_screen(self):
        """绘制开篇角色设定界面"""
        self.scene.draw(self.screen, allow_hotspots=self._allow_scene_hotspots())
        draw_page_heading(
            self.screen, "古籍解谜｜中医传承",
            subtitle=f"你的身份：{self.role_title}",
            kicker="序章｜入卷", time=self.ui_time, y=16,
            title_size=44, compact=True
        )

        # 剧情介绍
        draw_section_label(self.screen, "残卷序言", 128, 124,
                           trailing="墨迹待续", line_end=882)
        prologue_rect = pygame.Rect(120, 160, SCREEN_WIDTH - 240, 210)
        draw_panel(self.screen, prologue_rect, COLOR_LIGHT, COLOR_ACCENT)
        elapsed = 20.0 if self.intro_skip_reveal else self.state_time
        draw_reveal_text_block(
            self.screen, self.prologue_text,
            prologue_rect.x + 28, prologue_rect.y + 24,
            prologue_rect.width - 56, font_normal,
            line_spacing=10, elapsed=elapsed, chars_per_second=34
        )

        # 输入框提示
        draw_text(self.screen, "请输入你的名字，开启修复之旅：",
                  SCREEN_WIDTH // 2, 408, font_large, COLOR_DARK, center=True)

        # 输入框
        input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, 445, 400, 50)
        border_color = COLOR_ACCENT if self.name_input_active else COLOR_BORDER
        draw_panel(self.screen, input_rect, COLOR_LIGHT, border_color)

        # 文字居中显示在输入框内
        display_name = self.player_name if self.player_name else "输入名字"
        name_color = COLOR_TEXT if self.player_name else COLOR_GRAY
        draw_text(self.screen, display_name, input_rect.centerx,
                  input_rect.centery, font_large, name_color, center=True)

        # 绘制闪烁光标
        if self.name_input_active and self.cursor_visible:
            text_width = font_large.size(display_name)[0] if self.player_name else 0
            cursor_x = input_rect.centerx + text_width // 2 + 2
            cursor_y = input_rect.y + 10
            pygame.draw.line(self.screen, COLOR_TEXT,
                             (cursor_x, cursor_y),
                             (cursor_x, cursor_y + 30), 2)

        # 开始按钮
        start_rect = pygame.Rect(SCREEN_WIDTH // 2 - 112, 525, 224, 50)
        can_start = len(self.player_name.strip()) > 0
        start_color = COLOR_SECONDARY if can_start else (200, 190, 180)
        draw_button(self.screen, start_rect, "落笔入卷", font_large,
                    bg_color=start_color, hover=is_mouse_over(start_rect) and can_start)

        if not can_start:
            draw_text(self.screen, "请先为自己取一个名字", SCREEN_WIDTH // 2, 592,
                      font_small, COLOR_RED, center=True)
        else:
            shimmer = "墨迹已干，静候开卷"
            draw_text(self.screen, shimmer, SCREEN_WIDTH // 2, 592,
                      font_small, COLOR_GRAY, center=True)

    def _handle_prologue_event(self, event):
        """处理角色设定界面事件"""
        input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, 445, 400, 50)
        start_rect = pygame.Rect(SCREEN_WIDTH // 2 - 112, 525, 224, 50)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.name_input_active = input_rect.collidepoint(event.pos)

            if start_rect.collidepoint(event.pos) and len(self.player_name.strip()) > 0:
                self._start_game_from_prologue()
            elif pygame.Rect(120, 160, SCREEN_WIDTH - 240, 210).collidepoint(event.pos):
                self.intro_skip_reveal = True

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if len(self.player_name.strip()) > 0:
                    self._start_game_from_prologue()
            elif event.key == pygame.K_BACKSPACE:
                self.player_name = self.player_name[:-1]
                self.cursor_visible = True
                self.cursor_timer = 0

        elif event.type == pygame.TEXTINPUT:
            # 通过文本输入事件接收字符（避免与 KEYDOWN 重复）
            if self.name_input_active and event.text:
                for char in event.text:
                    if char.isprintable() and not char.isspace() and len(self.player_name) < 10:
                        self.player_name += char
                self.cursor_visible = True
                self.cursor_timer = 0

    def _start_game_from_prologue(self):
        """从角色设定界面进入主菜单"""
        self.save_manager.set_player_name(self.player_name)
        self.save_manager.set_first_run_done()
        self.set_state(STATE_MENU)

    # ==================== 章节选择界面 ====================

    def _init_chapter_screen(self):
        """初始化章节选择界面"""
        self.chapter_buttons = []
        chapters = self.data_manager.get_chapters()
        btn_width = 760
        btn_height = 76
        start_y = 136
        gap = 12
        completed = self.save_manager.save_data.get("completed_puzzles", [])

        for i, chapter in enumerate(chapters):
            chapter_id = chapter.get("id")
            unlocked = self.save_manager.is_chapter_unlocked(chapter_id)
            puzzles = chapter.get("puzzles", [])
            total = len(puzzles)
            done = sum(1 for p in puzzles if p.get("id") in completed)

            rect = pygame.Rect((SCREEN_WIDTH - btn_width) // 2, start_y + i * (btn_height + gap), btn_width, btn_height)
            self.chapter_buttons.append({
                "chapter": chapter,
                "rect": rect,
                "unlocked": unlocked,
                "progress": done / total if total > 0 else 0,
                "done": done,
                "total": total
            })

    def _draw_chapter_screen(self):
        """绘制章节选择界面"""
        self.scene.draw(self.screen, allow_hotspots=self._allow_scene_hotspots())
        draw_page_heading(
            self.screen, "选择古籍章节",
            subtitle="循着药香，逐卷修复散落人间的古方",
            kicker="修复卷宗", time=self.ui_time, y=12,
            title_size=42, compact=True
        )

        for item in self.chapter_buttons:
            rect = item["rect"]
            chapter = item["chapter"]
            unlocked = item["unlocked"]

            # 背景色：未解锁为灰色
            bg_color = COLOR_SECONDARY if unlocked else (200, 190, 180)
            is_hover = is_mouse_over(rect) and unlocked
            draw_rect = rect.move(0, -3 if is_hover else 0)
            draw_panel(self.screen, draw_rect, bg_color,
                       COLOR_ACCENT if unlocked else COLOR_GRAY)
            draw_chapter_emblem(self.screen, (draw_rect.x + 48, draw_rect.centery),
                                chapter.get("id", ""), unlocked)
            if is_hover:
                pygame.draw.rect(self.screen, COLOR_GOLD, draw_rect.inflate(-6, -6),
                                 2, border_radius=5)

            # 章节名称
            name_color = COLOR_TEXT if unlocked else COLOR_GRAY
            draw_text(self.screen, chapter.get("name", ""), draw_rect.x + 86,
                      draw_rect.y + 10, get_font(26, bold=True), name_color)
            draw_text(self.screen, chapter.get("title", ""), draw_rect.x + 86,
                      draw_rect.y + 43, font_small, name_color)

            # 进度条
            progress_rect = pygame.Rect(draw_rect.right - 236, draw_rect.y + 20, 158, 14)
            draw_progress_bar(self.screen, progress_rect, item["progress"])
            progress_text = f"{item['done']}/{item['total']}"
            draw_text(self.screen, progress_text, draw_rect.right - 70,
                      draw_rect.y + 15, font_small, COLOR_DARK, center=True)
            status_text = "启卷" if unlocked else "封存"
            status_color = COLOR_GREEN if unlocked else COLOR_GRAY
            draw_text(self.screen, status_text, draw_rect.right - 68,
                      draw_rect.y + 45, get_font(15, bold=True),
                      status_color, center=True)

            if not unlocked:
                draw_text(self.screen, "封", draw_rect.right - 168,
                          draw_rect.y + 45, get_font(16, bold=True),
                          COLOR_RED, center=True)

        progress = self.save_manager.get_progress()
        strip = pygame.Rect(148, 580, 728, 48)
        draw_panel(self.screen, strip, COLOR_LIGHT, COLOR_BORDER)
        summary = (
            f"已解锁 {progress['unlocked_chapters']} 卷  ｜  "
            f"已修复 {progress['completed_puzzles']} 篇  ｜  "
            f"辨方正确率 {progress['accuracy']}%"
        )
        draw_text(self.screen, summary, strip.centerx, strip.centery,
                  get_font(18, bold=True), COLOR_DARK, center=True)

        # 返回按钮
        back_rect = pygame.Rect(40, 658, 120, 45)
        draw_button(self.screen, back_rect, "返回", font_normal, hover=is_mouse_over(back_rect))

    def _handle_chapter_click(self, event):
        """处理章节选择点击"""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        for item in self.chapter_buttons:
            if item["rect"].collidepoint(event.pos):
                self.scene.burst_herb(event.pos, COLOR_GOLD)
                if item["unlocked"]:
                    self.current_chapter = item["chapter"]
                    self.current_puzzle_index = 0
                    self.set_state(STATE_INTRO)
                else:
                    self.popup.show("提示", "该章节尚未解锁，请先完成前面的章节。")
                return
        # 返回按钮
        back_rect = pygame.Rect(40, 658, 120, 45)
        if back_rect.collidepoint(event.pos):
            self.set_state(STATE_MENU)

    # ==================== 章节开篇界面 ====================

    def _draw_intro_screen(self):
        """绘制章节开篇界面"""
        self.scene.draw(self.screen, allow_hotspots=self._allow_scene_hotspots())
        chapter = self.current_chapter
        draw_page_heading(
            self.screen, chapter.get("name", ""),
            subtitle=chapter.get("title", ""),
            kicker="卷首题记", time=self.ui_time, y=12,
            title_size=42, compact=True
        )

        # 引言文本（替换玩家名字占位符）
        intro_rect = pygame.Rect(112, 142, SCREEN_WIDTH - 224, 420)
        draw_panel(self.screen, intro_rect, COLOR_LIGHT, COLOR_ACCENT)
        pygame.draw.line(self.screen, COLOR_GOLD,
                         (intro_rect.x + 40, intro_rect.y + 50),
                         (intro_rect.right - 40, intro_rect.y + 50), 1)
        elapsed = 20.0 if self.intro_skip_reveal else self.state_time
        text_height, complete = draw_reveal_text_block(
            self.screen, self._format_text(chapter.get("intro", "")),
            intro_rect.x + 38, intro_rect.y + 76,
            intro_rect.width - 76, font_normal,
            line_spacing=12, elapsed=elapsed, chars_per_second=30
        )
        if complete:
            pulse = 3 + int((math.sin(self.ui_time * 3.2) + 1) * 2)
            pygame.draw.circle(self.screen, COLOR_GOLD,
                               (intro_rect.right - 44, intro_rect.bottom - 34), pulse)
            draw_text(self.screen, "墨定", intro_rect.right - 70,
                      intro_rect.bottom - 46, get_font(14), COLOR_GRAY)
        else:
            draw_text(self.screen, "轻触残卷，令墨迹尽显",
                      intro_rect.centerx, intro_rect.bottom - 34,
                      get_font(15), COLOR_GRAY, center=True)

        # 开始解谜按钮
        start_rect = pygame.Rect(SCREEN_WIDTH // 2 - 118, 605, 236, 50)
        draw_button(self.screen, start_rect, "展卷解题", font_large,
                    hover=is_mouse_over(start_rect))

        # 返回按钮
        back_rect = pygame.Rect(40, 663, 120, 42)
        draw_button(self.screen, back_rect, "返回", font_normal, hover=is_mouse_over(back_rect))

    def _handle_intro_click(self, event):
        """处理开篇界面点击"""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if pygame.Rect(112, 142, SCREEN_WIDTH - 224, 420).collidepoint(event.pos):
            if not self.intro_skip_reveal:
                self.intro_skip_reveal = True
                self.scene.burst_herb(event.pos, COLOR_GOLD)
                return
        start_rect = pygame.Rect(SCREEN_WIDTH // 2 - 118, 605, 236, 50)
        if start_rect.collidepoint(event.pos):
            self._start_puzzle()
        back_rect = pygame.Rect(40, 663, 120, 42)
        if back_rect.collidepoint(event.pos):
            self.set_state(STATE_CHAPTER)

    def _start_puzzle(self):
        """开始当前章节的第一道或下一道谜题"""
        puzzles = self.current_chapter.get("puzzles", [])
        if self.current_puzzle_index < len(puzzles):
            puzzle_data = puzzles[self.current_puzzle_index]
            speed = self.settings_manager.get_text_speed()
            self.current_puzzle_system = PuzzleSystem(puzzle_data, text_speed=speed)
            self._init_puzzle_screen()
            self.set_state(STATE_PUZZLE)
        else:
            self.set_state(STATE_ENDING)

    # ==================== 解谜界面 ====================

    def _init_puzzle_screen(self):
        """初始化解谜界面"""
        puzzle = self.current_puzzle_system
        # 线索显示区
        clue_rect = pygame.Rect(112, 124, 474, 318)
        self.clue_area = ScrollTextArea(clue_rect, font_normal)
        self.clue_area.set_text("\n\n".join(puzzle.get_clues()))
        self.clue_area.reveal_all_clues()
        clue_count = len(puzzle.get_clues())
        self.puzzle_clue_opened = [index < min(2, clue_count) for index in range(clue_count)]
        puzzle.visible_clue_index = sum(self.puzzle_clue_opened)

        # 候选药材区
        option_rect = pygame.Rect(118, 470, 462, 175)
        self.option_group = OptionButtonGroup(
            option_rect, puzzle.get_options(), columns=4, font=font_normal
        )

        # 初始化文字缺失补全输入框
        self.missing_inputs = []
        self.active_input_index = -1
        if puzzle.get_puzzle_type() == "文字缺失补全":
            missing = puzzle.get_missing_text()
            for i in range(len(missing)):
                self.missing_inputs.append("")

    def _get_puzzle_action_rects(self):
        """返回解谜页右侧操作按钮，文字补全题使用更低的按钮组。"""
        is_missing = self.current_puzzle_system.get_puzzle_type() == "文字缺失补全"
        top_y = 448 if is_missing else 302
        return {
            "check": pygame.Rect(604, top_y, 148, 42),
            "clear": pygame.Rect(764, top_y, 148, 42),
            "hint": pygame.Rect(604, top_y + 50, 148, 42),
            "back": pygame.Rect(764, top_y + 50, 148, 42),
        }

    def _get_puzzle_clue_rects(self):
        """返回五张线索卡的点击区域。"""
        rects = []
        for index in range(len(self.puzzle_clue_opened)):
            rects.append(pygame.Rect(120, 168 + index * 54, 458, 48))
        return rects

    def _get_puzzle_reveal_all_rect(self):
        return pygame.Rect(488, 130, 86, 25)

    def _get_puzzle_next_rect(self):
        return pygame.Rect(604, 663, 308, 44)

    def _get_missing_input_rects(self):
        """将缺失文字输入框按两列排布，避免小屏越界。"""
        rects = []
        start_x = 620
        start_y = 344
        box_width = 126
        box_height = 38
        gap_x = 14
        gap_y = 48
        for i in range(len(self.missing_inputs)):
            col = i % 2
            row = i // 2
            rects.append(pygame.Rect(
                start_x + col * (box_width + gap_x),
                start_y + row * gap_y,
                box_width,
                box_height
            ))
        return rects

    def _draw_puzzle_screen(self):
        """绘制解谜界面"""
        self.scene.draw(self.screen, allow_hotspots=self._allow_scene_hotspots())
        puzzle = self.current_puzzle_system
        chapter = self.current_chapter
        clues = puzzle.get_clues()

        opened_count = sum(1 for opened in self.puzzle_clue_opened if opened)
        draw_page_heading(
            self.screen, f"{chapter.get('name', '')}｜{puzzle.get_name()}",
            subtitle=f"{puzzle.get_puzzle_type()}  ｜  已拆封 {opened_count}/{len(self.puzzle_clue_opened)} 条线索",
            kicker=f"第 {self.current_puzzle_index + 1} 题｜辨方", time=self.ui_time,
            y=10, title_size=34, compact=True
        )

        # 可逐条拆封的线索卡
        clue_panel = pygame.Rect(112, 124, 474, 318)
        draw_panel(self.screen, clue_panel, COLOR_LIGHT, COLOR_ACCENT)
        draw_text(self.screen, "残缺线索", clue_panel.x + 16, clue_panel.y + 11,
                  get_font(22, bold=True), COLOR_DARK)
        progress_text = f"{opened_count}/{len(self.puzzle_clue_opened)}"
        draw_text(self.screen, progress_text, clue_panel.x + 132,
                  clue_panel.y + 15, get_font(14, bold=True), COLOR_ACCENT)
        reveal_rect = self._get_puzzle_reveal_all_rect()
        all_open = opened_count == len(self.puzzle_clue_opened)
        draw_button(self.screen, reveal_rect, "展卷" if not all_open else "已展",
                    get_font(14), bg_color=COLOR_SECONDARY if not all_open else COLOR_GREEN,
                    hover=is_mouse_over(reveal_rect) and not all_open)

        clue_font = get_font(14)
        for index, rect in enumerate(self._get_puzzle_clue_rects()):
            if index >= len(self.puzzle_clue_opened):
                break
            opened = self.puzzle_clue_opened[index]
            hover = is_mouse_over(rect)
            if opened:
                card_color = (248, 242, 226) if index % 2 == 0 else (243, 235, 216)
                draw_panel(self.screen, rect, card_color,
                           COLOR_GOLD if hover else COLOR_BORDER, border_width=1)
                tag_rect = pygame.Rect(rect.x + 5, rect.y + 5, 42, rect.height - 10)
                pygame.draw.rect(self.screen, COLOR_ACCENT, tag_rect, border_radius=2)
                draw_text(self.screen, f"{index + 1:02d}", tag_rect.centerx,
                          tag_rect.centery, get_font(15, bold=True),
                          COLOR_LIGHT, center=True)
                lines = wrap_text(clues[index], clue_font, rect.width - 62)
                for line_index, line in enumerate(lines[:2]):
                    draw_text(self.screen, line, rect.x + 54,
                              rect.y + 5 + line_index * 19,
                              clue_font, COLOR_TEXT)
            else:
                sealed_color = (225, 216, 196) if not hover else (235, 225, 204)
                draw_panel(self.screen, rect, sealed_color,
                           COLOR_ACCENT if hover else COLOR_GRAY, border_width=1)
                for line_x in range(rect.x + 16, rect.right - 12, 26):
                    pygame.draw.line(self.screen, (197, 184, 158),
                                     (line_x, rect.y + 8), (line_x + 12, rect.bottom - 8), 1)
                seal = pygame.Rect(rect.x + 10, rect.y + 10, 28, 28)
                pygame.draw.rect(self.screen, COLOR_ACCENT, seal, border_radius=3)
                draw_text(self.screen, "封", seal.centerx, seal.centery,
                          get_font(16, bold=True), COLOR_LIGHT, center=True)
                draw_text(self.screen, f"第 {index + 1} 条线索尚未拆封",
                          rect.x + 52, rect.y + 13, get_font(15), COLOR_DARK)
                draw_text(self.screen, "轻触药签，看看残卷还藏着什么",
                          rect.x + 250, rect.y + 15, get_font(13), COLOR_GRAY)

        # 右侧药理案
        selected_rect = pygame.Rect(604, 124, 308, 160)
        draw_panel(self.screen, selected_rect, COLOR_LIGHT, COLOR_GREEN)
        draw_text(self.screen, "药理案", selected_rect.x + 15, selected_rect.y + 10,
                  get_font(21, bold=True), COLOR_DARK)
        selected_count_font = get_font(14)
        selected_count = f"{len(puzzle.selected_herbs)} 味入方"
        draw_text(self.screen, selected_count,
                  selected_rect.right - 16
                  - selected_count_font.size(selected_count)[0] // 2,
                  selected_rect.y + 14,
                  selected_count_font, COLOR_GREEN, center=True)
        pygame.draw.line(self.screen, COLOR_BORDER, (selected_rect.x + 14, selected_rect.y + 43),
                         (selected_rect.right - 14, selected_rect.y + 43), 1)
        if puzzle.selected_herbs:
            selected_text = "  ".join(
                f"{index + 1}.{herb}" for index, herb in enumerate(puzzle.selected_herbs)
            )
            draw_text_block(self.screen, selected_text, selected_rect.x + 16,
                            selected_rect.y + 54, selected_rect.width - 32,
                            get_font(18), COLOR_DARK, line_spacing=4)
        else:
            draw_text(self.screen, "尚未落笔", selected_rect.centerx,
                      selected_rect.y + 78, get_font(20, bold=True),
                      COLOR_GRAY, center=True)
            draw_text(self.screen, "从候选药材中挑起第一味",
                      selected_rect.centerx, selected_rect.y + 108,
                      get_font(14), COLOR_GRAY, center=True)

        # 文字缺失补全输入框
        if puzzle.get_puzzle_type() == "文字缺失补全":
            self._draw_missing_inputs()

        # 候选药材区
        draw_section_label(self.screen, "候选药材", 120, 444,
                           trailing="按君臣佐使挑药", line_end=574,
                           trailing_y_offset=0)
        self.option_group.set_selected(puzzle.selected_herbs)
        self.option_group.draw(self.screen)
        hovered_option = self.option_group.get_hovered_option()
        if hovered_option and not self.popup.visible:
            self.scene.draw_herb_tooltip(self.screen, hovered_option, pygame.mouse.get_pos())

        # 操作按钮
        action_rects = self._get_puzzle_action_rects()
        check_rect = action_rects["check"]
        clear_rect = action_rects["clear"]
        hint_rect = action_rects["hint"]
        back_rect = action_rects["back"]

        draw_button(self.screen, check_rect, "照方验药", font_normal,
                    hover=is_mouse_over(check_rect))
        draw_button(self.screen, clear_rect, "拂去墨迹", font_normal,
                    hover=is_mouse_over(clear_rect))
        draw_button(self.screen, hint_rect, "讨条线索", font_normal,
                    hover=is_mouse_over(hint_rect))
        draw_button(self.screen, back_rect, "合卷暂退", font_normal,
                    hover=is_mouse_over(back_rect))

        # 反馈与下一题
        feedback_rect = pygame.Rect(112, 659, 474, 48)
        if puzzle.feedback:
            feedback_color = COLOR_GREEN if puzzle.solved else COLOR_RED
            draw_panel(self.screen, feedback_rect, COLOR_LIGHT, feedback_color, border_width=2)
            feedback_font = get_font(16)
            feedback_lines = wrap_text(puzzle.feedback, feedback_font, feedback_rect.width - 28)
            for index, line in enumerate(feedback_lines[:2]):
                draw_text(self.screen, line, feedback_rect.centerx,
                          feedback_rect.y + 8 + index * 20,
                          feedback_font, puzzle.feedback_color, center=True)
        if puzzle.solved:
            next_rect = self._get_puzzle_next_rect()
            next_label = "装订残卷｜继续" if self.current_puzzle_index + 1 < len(
                chapter.get("puzzles", [])) else "修成正卷｜阅篇末"
            draw_button(self.screen, next_rect, next_label, font_normal,
                        bg_color=COLOR_GREEN, hover=is_mouse_over(next_rect))

    def _draw_missing_inputs(self):
        """绘制文字缺失补全输入框"""
        puzzle = self.current_puzzle_system
        missing = puzzle.get_missing_text()
        if not missing:
            return
        draw_text(self.screen, "补全空缺", 620, 302, get_font(21, bold=True), COLOR_DARK)
        draw_text(self.screen, "依方名与前文，填入残字", 712, 308,
                  get_font(14), COLOR_GRAY)
        for i, rect in enumerate(self._get_missing_input_rects()):
            color = COLOR_ACCENT if i == self.active_input_index else COLOR_BORDER
            draw_panel(self.screen, rect, COLOR_LIGHT, color)
            text = self.missing_inputs[i] if i < len(self.missing_inputs) else ""
            if text:
                draw_text(self.screen, text, rect.centerx, rect.centery,
                          font_normal, COLOR_TEXT, center=True)
            else:
                draw_text(self.screen, f"残字{i + 1}", rect.centerx, rect.centery,
                          font_small, COLOR_GRAY, center=True)

    def _handle_puzzle_event(self, event):
        """处理解谜界面事件"""
        puzzle = self.current_puzzle_system

        # 拆封线索
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            reveal_all_rect = self._get_puzzle_reveal_all_rect()
            if reveal_all_rect.collidepoint(event.pos):
                if not all(self.puzzle_clue_opened):
                    self.puzzle_clue_opened = [True] * len(self.puzzle_clue_opened)
                    puzzle.reveal_all_clues()
                    self.scene.burst_herb(event.pos, COLOR_GOLD)
                return

            for index, rect in enumerate(self._get_puzzle_clue_rects()):
                if rect.collidepoint(event.pos):
                    if not self.puzzle_clue_opened[index]:
                        self.puzzle_clue_opened[index] = True
                        puzzle.visible_clue_index = sum(self.puzzle_clue_opened)
                        self.scene.burst_herb(event.pos, COLOR_GOLD)
                    else:
                        self.popup.show(
                            f"线索卡｜{index + 1}",
                            puzzle.get_clues()[index],
                            [("收入眼帘", None)]
                        )
                        self.scene.burst_herb(event.pos, COLOR_GOLD)
                    return

        # 候选药材点击
        clicked = self.option_group.handle_event(event)
        if clicked:
            puzzle.toggle_herb(clicked)
            self.scene.burst_herb(event.pos)
            return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            # 文字输入处理
            if event.type == pygame.KEYDOWN and puzzle.get_puzzle_type() == "文字缺失补全":
                self._handle_text_input(event)
            return

        # 校验按钮
        action_rects = self._get_puzzle_action_rects()
        check_rect = action_rects["check"]
        if check_rect.collidepoint(event.pos):
            self._check_puzzle_answer()
            return

        # 清空按钮
        clear_rect = action_rects["clear"]
        if clear_rect.collidepoint(event.pos):
            puzzle.clear_selection()
            self.missing_inputs = ["" for _ in self.missing_inputs]
            puzzle.feedback = ""
            return

        # 提示按钮
        hint_rect = action_rects["hint"]
        if hint_rect.collidepoint(event.pos):
            hint = puzzle.get_hint()
            self.popup.show("中医解析提示", hint, [("知道了", None)])
            return

        # 返回章节按钮
        back_rect = action_rects["back"]
        if back_rect.collidepoint(event.pos):
            self.set_state(STATE_CHAPTER)
            return

        # 文字缺失输入框激活
        if puzzle.get_puzzle_type() == "文字缺失补全":
            missing = puzzle.get_missing_text()
            for i, rect in enumerate(self._get_missing_input_rects()):
                if rect.collidepoint(event.pos):
                    self.active_input_index = i
                    return

        # 继续按钮
        if puzzle.solved:
            next_rect = self._get_puzzle_next_rect()
            if next_rect.collidepoint(event.pos):
                self._go_to_next_puzzle()

    def _handle_text_input(self, event):
        """处理文字缺失补全的键盘输入"""
        if self.active_input_index < 0:
            return
        if self.active_input_index >= len(self.missing_inputs):
            return

        if event.key == pygame.K_RETURN:
            self.active_input_index = -1
        elif event.key == pygame.K_BACKSPACE:
            self.missing_inputs[self.active_input_index] = self.missing_inputs[self.active_input_index][:-1]
        elif event.unicode and len(event.unicode) == 1 and not event.unicode.isspace():
            # 限制输入长度
            if len(self.missing_inputs[self.active_input_index]) < 4:
                self.missing_inputs[self.active_input_index] += event.unicode

        # 同步到puzzle_system
        for i, text in enumerate(self.missing_inputs):
            self.current_puzzle_system.set_missing_answer(i, text)

    def _check_puzzle_answer(self):
        """校验当前谜题答案"""
        puzzle = self.current_puzzle_system
        correct, message = puzzle.check_answer()
        puzzle.feedback = message
        puzzle.feedback_color = COLOR_GREEN if correct else COLOR_RED
        self.scene.flash_feedback(correct)

        self.save_manager.add_attempt(correct)

        if correct:
            puzzle_id = puzzle.puzzle.get("id")
            self.save_manager.complete_puzzle(puzzle_id)
            # 清除该谜题的错误记录
            self.save_manager.clear_wrong_records(puzzle_id)
            # 检查是否解锁下一章
            self._check_chapter_unlock()
        else:
            # 记录错误
            hint = puzzle.get_hint()
            self.save_manager.add_wrong_record(
                puzzle.puzzle.get("id"),
                puzzle.selected_herbs.copy(),
                hint
            )

    def _check_chapter_unlock(self):
        """检查是否需要解锁下一章节"""
        chapters = self.data_manager.get_chapters()
        chapter_id = self.current_chapter.get("id")

        # 找到当前章节索引
        current_index = -1
        for i, ch in enumerate(chapters):
            if ch.get("id") == chapter_id:
                current_index = i
                break

        if current_index < 0 or current_index >= len(chapters) - 1:
            return

        # 检查当前章节所有谜题是否完成
        puzzles = self.current_chapter.get("puzzles", [])
        completed = self.save_manager.save_data.get("completed_puzzles", [])
        all_done = all(p.get("id") in completed for p in puzzles)

        if all_done:
            next_chapter = chapters[current_index + 1]
            self.save_manager.unlock_chapter(next_chapter.get("id"))

    def _go_to_next_puzzle(self):
        """进入下一题或章节结局"""
        self.current_puzzle_index += 1
        puzzles = self.current_chapter.get("puzzles", [])
        if self.current_puzzle_index >= len(puzzles):
            self.set_state(STATE_ENDING)
        else:
            self._start_puzzle()

    # ==================== 章节结局界面 ====================

    def _draw_ending_screen(self):
        """绘制章节结局界面"""
        self.scene.draw(self.screen, allow_hotspots=self._allow_scene_hotspots())
        chapter = self.current_chapter
        draw_page_heading(
            self.screen, f"{chapter.get('name', '')}｜篇末",
            subtitle="残页归位，墨香未散",
            kicker="修卷有成", time=self.ui_time, y=12,
            title_size=42, compact=True
        )

        ending_rect = pygame.Rect(112, 142, SCREEN_WIDTH - 224, 326)
        draw_panel(self.screen, ending_rect, COLOR_LIGHT, COLOR_ACCENT)
        elapsed = 20.0 if self.intro_skip_reveal else self.state_time
        draw_reveal_text_block(
            self.screen, self._format_text(chapter.get("ending", "")),
            ending_rect.x + 38, ending_rect.y + 34,
            ending_rect.width - 76, font_normal,
            line_spacing=12, elapsed=elapsed, chars_per_second=32
        )
        footer_hint = "轻触卷面，读完篇末余墨"
        if not self.intro_skip_reveal:
            draw_text(self.screen, footer_hint, ending_rect.centerx,
                      ending_rect.bottom - 28, get_font(15), COLOR_GRAY, center=True)
        else:
            pygame.draw.circle(self.screen, COLOR_GOLD,
                               (ending_rect.right - 40, ending_rect.bottom - 34),
                               5 + int((math.sin(self.ui_time * 3) + 1) * 2))

        # 统计
        progress = self.save_manager.get_progress()
        stats_rect = pygame.Rect(112, 487, SCREEN_WIDTH - 224, 86)
        draw_panel(self.screen, stats_rect, COLOR_SECONDARY, COLOR_GOLD)
        stats = [
            ("修复方剂", f"{progress['completed_puzzles']} 篇"),
            ("辨方正确率", f"{progress['accuracy']}%"),
            ("本章进度", f"{self.current_puzzle_index + 1}/{len(chapter.get('puzzles', []))}"),
        ]
        column_width = stats_rect.width // 3
        for index, (label, value) in enumerate(stats):
            center_x = stats_rect.x + column_width * index + column_width // 2
            draw_text(self.screen, label, center_x, stats_rect.y + 11,
                      get_font(14), COLOR_GRAY, center=True)
            draw_text(self.screen, value, center_x, stats_rect.y + 35,
                      get_font(28, bold=True), COLOR_DARK, center=True)
            if index < 2:
                line_x = stats_rect.x + column_width * (index + 1)
                pygame.draw.line(self.screen, COLOR_BORDER,
                                 (line_x, stats_rect.y + 14),
                                 (line_x, stats_rect.bottom - 14), 1)

        seal_rect = pygame.Rect(44, 500, 60, 60)
        pygame.draw.rect(self.screen, COLOR_ACCENT, seal_rect, border_radius=5)
        pygame.draw.rect(self.screen, COLOR_GOLD, seal_rect.inflate(-8, -8),
                         1, border_radius=3)
        draw_text(self.screen, "岐黄", seal_rect.centerx, seal_rect.centery,
                  get_font(16, bold=True), COLOR_LIGHT, center=True)
        if is_mouse_over(seal_rect):
            pygame.draw.rect(self.screen, COLOR_GOLD, seal_rect.inflate(6, 6),
                             2, border_radius=6)

        # 按钮
        next_rect = pygame.Rect(274, 615, 220, 48)
        back_rect = pygame.Rect(530, 615, 220, 48)
        draw_button(self.screen, next_rect, "再挑一卷", font_large,
                    hover=is_mouse_over(next_rect))
        draw_button(self.screen, back_rect, "回到案前", font_normal,
                    hover=is_mouse_over(back_rect))

    def _handle_ending_click(self, event):
        """处理结局界面点击"""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if pygame.Rect(112, 142, SCREEN_WIDTH - 224, 326).collidepoint(event.pos):
            self.intro_skip_reveal = True
            self.scene.burst_herb(event.pos, COLOR_GOLD)
            return
        seal_rect = pygame.Rect(44, 500, 60, 60)
        if seal_rect.collidepoint(event.pos):
            progress = self.save_manager.get_progress()
            self.popup.show(
                "修卷小记",
                f"{self.player_name or '年轻的修复师'}，你已修成 {progress['completed_puzzles']} 篇古方。"
                f"\n\n{self.current_chapter.get('name', '')}的余墨已经落定，下一页还在等你。",
                [("收下这枚印章", None)]
            )
            self.scene.burst_herb(seal_rect.center, COLOR_GOLD)
            return
        next_rect = pygame.Rect(274, 615, 220, 48)
        back_rect = pygame.Rect(530, 615, 220, 48)
        if next_rect.collidepoint(event.pos):
            self.set_state(STATE_CHAPTER)
        elif back_rect.collidepoint(event.pos):
            self.set_state(STATE_MENU)

    # ==================== 图鉴界面 ====================

    def _init_archive_screen(self):
        """初始化图鉴界面"""
        self._refresh_archive_content()
        if self.archive_items:
            self.archive_focus_index = min(
                self.archive_focus_index, len(self.archive_items) - 1
            )
            self.archive_page = self.archive_focus_index // 5
        else:
            self.archive_focus_index = 0
            self.archive_page = 0

    def _refresh_archive_content(self):
        """刷新图鉴药签目录。"""
        archives = self.archive_system.get_archives_by_chapter()
        self.archive_items = []
        self.archive_total = 0
        for group in archives:
            self.archive_total += len(group["chapter"].get("puzzles", []))
            self.archive_items.extend(group["archives"])

    def _archive_page_count(self):
        return max(1, math.ceil(len(self.archive_items) / 5))

    def _get_archive_card_rects(self):
        """返回当前页五张方剂药签。"""
        page_start = self.archive_page * 5
        visible = self.archive_items[page_start:page_start + 5]
        return [
            (page_start + index, pygame.Rect(126, 180 + index * 78, 264, 68))
            for index, _item in enumerate(visible)
        ]

    def _get_archive_tab_rects(self):
        detail = pygame.Rect(414, 126, 498, 500)
        return {
            "explanation": pygame.Rect(detail.x + 20, detail.y + 76, 132, 34),
            "story": pygame.Rect(detail.x + 158, detail.y + 76, 132, 34),
        }

    def _get_archive_random_rect(self):
        return pygame.Rect(706, 650, 146, 42)

    def _archive_change_page(self, direction):
        if not self.archive_items:
            return
        page = (self.archive_page + direction) % self._archive_page_count()
        self.archive_page = page
        self.archive_focus_index = min(page * 5, len(self.archive_items) - 1)
        self.scene.burst_herb((512, 666), COLOR_GOLD)

    def _percent(self, a, b):
        if b == 0:
            return 0
        return round(a / b * 100, 1)

    def _draw_archive_screen(self):
        """绘制图鉴界面"""
        self.scene.draw(self.screen, allow_hotspots=self._allow_scene_hotspots())
        unlocked_count = len(self.archive_items)
        draw_page_heading(
            self.screen, "古籍图鉴",
            subtitle=f"已收 {unlocked_count}/{self.archive_total} 方｜重读配伍与医案故事",
            kicker="本草藏卷", time=self.ui_time, y=12,
            title_size=42, compact=True
        )

        list_panel = pygame.Rect(112, 126, 288, 500)
        detail_panel = pygame.Rect(414, 126, 498, 500)
        draw_panel(self.screen, list_panel, COLOR_LIGHT, COLOR_BORDER)
        draw_panel(self.screen, detail_panel, COLOR_LIGHT, COLOR_ACCENT)
        draw_text(self.screen, "方剂药签", list_panel.x + 16, list_panel.y + 12,
                  get_font(22, bold=True), COLOR_DARK)
        page_font = get_font(13)
        page_label = f"第 {self.archive_page + 1}/{self._archive_page_count()} 页"
        draw_text(self.screen, page_label,
                  list_panel.right - 16 - page_font.size(page_label)[0] // 2,
                  list_panel.y + 18, page_font, COLOR_GRAY, center=True)

        if self.archive_items:
            for absolute_index, rect in self._get_archive_card_rects():
                item = self.archive_items[absolute_index]
                selected = absolute_index == self.archive_focus_index
                hover = is_mouse_over(rect)
                card_color = COLOR_GREEN if selected else (
                    (241, 234, 215) if hover else (247, 242, 228)
                )
                draw_rect = rect.move(0, -2 if hover and not selected else 0)
                draw_panel(self.screen, draw_rect, card_color,
                           COLOR_GOLD if selected else COLOR_BORDER, border_width=1)
                name_color = COLOR_LIGHT if selected else COLOR_DARK
                chapter_color = (234, 226, 202) if selected else COLOR_GRAY
                draw_text(self.screen, item.get("chapter_name", ""),
                          draw_rect.x + 12, draw_rect.y + 9,
                          get_font(13), chapter_color)
                draw_text(self.screen, item.get("name", ""),
                          draw_rect.x + 12, draw_rect.y + 30,
                          get_font(22, bold=True), name_color)
                type_font = get_font(13)
                type_text = item.get("type", "")
                draw_text(self.screen, type_text,
                          draw_rect.right - 12
                          - type_font.size(type_text)[0] // 2,
                          draw_rect.y + 38, type_font, chapter_color, center=True)
        else:
            draw_text(self.screen, "药签尚空", list_panel.centerx,
                      list_panel.y + 170, get_font(24, bold=True),
                      COLOR_GRAY, center=True)
            draw_text_block(
                self.screen, "修成第一道方剂后，这里会落下第一枚药签。",
                list_panel.x + 34, list_panel.y + 210,
                list_panel.width - 68, get_font(16), COLOR_GRAY
            )

        if self.archive_items:
            item = self.archive_items[self.archive_focus_index]
            draw_text(self.screen, item.get("name", ""), detail_panel.x + 22,
                      detail_panel.y + 14, get_font(29, bold=True), COLOR_DARK)
            draw_text(self.screen, item.get("chapter_name", ""), detail_panel.x + 24,
                      detail_panel.y + 50, get_font(14), COLOR_ACCENT)
            detail_type_font = get_font(14)
            detail_type = item.get("type", "")
            draw_text(
                self.screen, detail_type,
                detail_panel.right - 20
                - detail_type_font.size(detail_type)[0] // 2,
                detail_panel.y + 25, detail_type_font, COLOR_GREEN, center=True
            )

            tabs = self._get_archive_tab_rects()
            for key, label in (("explanation", "配伍方解"), ("story", "名医医案")):
                active = self.archive_tab == key
                draw_button(
                    self.screen, tabs[key], label, get_font(15),
                    bg_color=COLOR_ACCENT if active else COLOR_SECONDARY,
                    hover=is_mouse_over(tabs[key])
                )

            herbs = item.get("herbs", [])
            draw_text(self.screen, "方中诸药", detail_panel.x + 22,
                      detail_panel.y + 124, get_font(15, bold=True), COLOR_GRAY)
            tag_x = detail_panel.x + 94
            tag_y = detail_panel.y + 117
            for herb in herbs:
                tag_width = get_font(14).size(herb)[0] + 20
                if tag_x + tag_width > detail_panel.right - 20:
                    tag_x = detail_panel.x + 22
                    tag_y += 31
                tag = pygame.Rect(tag_x, tag_y, tag_width, 25)
                pygame.draw.rect(self.screen, (224, 232, 215), tag, border_radius=3)
                pygame.draw.rect(self.screen, COLOR_GREEN, tag, 1, border_radius=3)
                draw_text(self.screen, herb, tag.centerx, tag.centery,
                          get_font(14), COLOR_DARK, center=True)
                tag_x += tag_width + 6

            content_y = max(detail_panel.y + 188, tag_y + 45)
            pygame.draw.line(self.screen, COLOR_BORDER,
                             (detail_panel.x + 22, content_y - 14),
                             (detail_panel.right - 22, content_y - 14), 1)
            content_key = "explanation" if self.archive_tab == "explanation" else "story"
            content = item.get(content_key, "暂无记载")
            draw_text_block(
                self.screen, content, detail_panel.x + 24, content_y,
                detail_panel.width - 48, get_font(17), COLOR_TEXT, line_spacing=8
            )
        else:
            draw_text(self.screen, "卷页未启", detail_panel.centerx,
                      detail_panel.y + 150, get_font(30, bold=True),
                      COLOR_GRAY, center=True)
            draw_text_block(
                self.screen, "完成解谜后，方剂原文、配伍解析与名医故事会收录在这里。",
                detail_panel.x + 74, detail_panel.y + 205,
                detail_panel.width - 148, get_font(18), COLOR_GRAY,
                line_spacing=10
            )
            enter_rect = pygame.Rect(detail_panel.centerx - 92,
                                     detail_panel.y + 315, 184, 44)
            draw_button(self.screen, enter_rect, "去修第一叶", font_normal,
                        bg_color=COLOR_GREEN, hover=is_mouse_over(enter_rect))

        prev_rect = pygame.Rect(180, 650, 100, 42)
        next_rect = pygame.Rect(332, 650, 100, 42)
        draw_button(self.screen, prev_rect, "上一页", font_small,
                    hover=is_mouse_over(prev_rect) and self._archive_page_count() > 1)
        draw_button(self.screen, next_rect, "下一页", font_small,
                    hover=is_mouse_over(next_rect) and self._archive_page_count() > 1)
        random_rect = self._get_archive_random_rect()
        draw_button(self.screen, random_rect, "随机回看", font_normal,
                    bg_color=COLOR_GREEN if self.archive_items else COLOR_SECONDARY,
                    hover=is_mouse_over(random_rect) and bool(self.archive_items))

        back_rect = pygame.Rect(40, 663, 120, 42)
        draw_button(self.screen, back_rect, "返回", font_normal, hover=is_mouse_over(back_rect))

    def _handle_archive_click(self, event):
        """处理图鉴界面事件"""
        if event.type == pygame.MOUSEWHEEL:
            if pygame.Rect(112, 126, 800, 500).collidepoint(pygame.mouse.get_pos()):
                self._archive_change_page(-1 if event.y > 0 else 1)
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        back_rect = pygame.Rect(40, 663, 120, 42)
        if back_rect.collidepoint(event.pos):
            self.set_state(STATE_MENU)
            return
        if not self.archive_items:
            enter_rect = pygame.Rect(414 + (498 - 184) // 2, 126 + 315, 184, 44)
            if enter_rect.collidepoint(event.pos):
                self.set_state(STATE_CHAPTER)
            return

        tabs = self._get_archive_tab_rects()
        for key, rect in tabs.items():
            if rect.collidepoint(event.pos):
                self.archive_tab = key
                self.scene.burst_herb(event.pos, COLOR_GOLD)
                return

        if self._get_archive_random_rect().collidepoint(event.pos):
            if len(self.archive_items) > 1:
                choices = [index for index in range(len(self.archive_items))
                           if index != self.archive_focus_index]
                self.archive_focus_index = random.choice(choices)
            self.archive_page = self.archive_focus_index // 5
            self.scene.burst_herb(event.pos, COLOR_GOLD)
            return

        if pygame.Rect(180, 650, 100, 42).collidepoint(event.pos):
            self._archive_change_page(-1)
            return
        if pygame.Rect(332, 650, 100, 42).collidepoint(event.pos):
            self._archive_change_page(1)
            return

        for absolute_index, rect in self._get_archive_card_rects():
            if rect.collidepoint(event.pos):
                self.archive_focus_index = absolute_index
                self.scene.burst_herb(event.pos, COLOR_GOLD)
                return

    # ==================== 复盘界面 ====================

    def _init_review_screen(self):
        """初始化错题复盘界面"""
        self._refresh_review_content()
        if self.review_items:
            self.review_focus_index = min(self.review_focus_index, len(self.review_items) - 1)
            self.review_page = self.review_focus_index // 5
        else:
            self.review_focus_index = 0
            self.review_page = 0

    def _refresh_review_content(self):
        """刷新复盘药签目录。"""
        self.review_items = self.review_system.get_wrong_records()

    def _review_page_count(self):
        return max(1, math.ceil(len(self.review_items) / 5))

    def _get_review_card_rects(self):
        page_start = self.review_page * 5
        visible = self.review_items[page_start:page_start + 5]
        return [
            (page_start + index, pygame.Rect(126, 180 + index * 78, 264, 68))
            for index, _item in enumerate(visible)
        ]

    def _get_review_tab_rects(self):
        detail = pygame.Rect(414, 126, 498, 500)
        return {
            "hint": pygame.Rect(detail.x + 20, detail.y + 76, 132, 34),
            "clues": pygame.Rect(detail.x + 158, detail.y + 76, 132, 34),
        }

    def _get_review_random_rect(self):
        return pygame.Rect(706, 650, 146, 42)

    def _review_change_page(self, direction):
        if not self.review_items:
            return
        page = (self.review_page + direction) % self._review_page_count()
        self.review_page = page
        self.review_focus_index = min(page * 5, len(self.review_items) - 1)
        self.scene.burst_herb((512, 666), COLOR_GOLD)

    def _practice_reviewed_puzzle(self, puzzle_id):
        """从复盘页直接重练指定谜题。"""
        for chapter in self.data_manager.get_chapters():
            for index, puzzle in enumerate(chapter.get("puzzles", [])):
                if puzzle.get("id") == puzzle_id:
                    self.current_chapter = chapter
                    self.current_puzzle_index = index
                    self._start_puzzle()
                    return
        self.popup.show("提示", "这道谜题暂时无法重新打开。")

    def _draw_review_screen(self):
        """绘制复盘界面"""
        self.scene.draw(self.screen, allow_hotspots=self._allow_scene_hotspots())
        draw_page_heading(
            self.screen, "错题复盘",
            subtitle="把误判折成一枚药签，再从头辨一次",
            kicker="温故知新", time=self.ui_time, y=12,
            title_size=42, compact=True
        )

        list_panel = pygame.Rect(112, 126, 288, 500)
        detail_panel = pygame.Rect(414, 126, 498, 500)
        draw_panel(self.screen, list_panel, COLOR_LIGHT, COLOR_BORDER)
        draw_panel(self.screen, detail_panel, COLOR_LIGHT, COLOR_ACCENT)
        draw_text(self.screen, "待温故药签", list_panel.x + 16, list_panel.y + 12,
                  get_font(22, bold=True), COLOR_DARK)
        page_font = get_font(13)
        page_label = f"第 {self.review_page + 1}/{self._review_page_count()} 页"
        draw_text(self.screen, page_label,
                  list_panel.right - 16 - page_font.size(page_label)[0] // 2,
                  list_panel.y + 18, page_font, COLOR_GRAY, center=True)

        if self.review_items:
            for absolute_index, rect in self._get_review_card_rects():
                record = self.review_items[absolute_index]
                puzzle = record["puzzle"]
                selected = absolute_index == self.review_focus_index
                hover = is_mouse_over(rect)
                card_color = COLOR_RED if selected else (
                    (241, 234, 215) if hover else (247, 242, 228)
                )
                draw_rect = rect.move(0, -2 if hover and not selected else 0)
                draw_panel(self.screen, draw_rect, card_color,
                           COLOR_GOLD if selected else COLOR_BORDER, border_width=1)
                name_color = COLOR_LIGHT if selected else COLOR_DARK
                sub_color = (247, 218, 206) if selected else COLOR_GRAY
                draw_text(self.screen, puzzle.get("name", ""),
                          draw_rect.x + 12, draw_rect.y + 10,
                          get_font(21, bold=True), name_color)
                draw_text(self.screen, puzzle.get("type", ""),
                          draw_rect.x + 12, draw_rect.y + 41,
                          get_font(13), sub_color)
                error_count = record["record"].get("count", 1)
                error_font = get_font(13)
                error_text = f"误判 {error_count} 次"
                draw_text(self.screen, error_text,
                          draw_rect.right - 12
                          - error_font.size(error_text)[0] // 2,
                          draw_rect.y + 43, error_font, sub_color, center=True)
        else:
            draw_text(self.screen, "暂无错题", list_panel.centerx,
                      list_panel.y + 170, get_font(24, bold=True),
                      COLOR_GREEN, center=True)
            draw_text_block(
                self.screen, "这说明你辨方很稳。也可以挑一题再练练手。",
                list_panel.x + 34, list_panel.y + 210,
                list_panel.width - 68, get_font(16), COLOR_GRAY
            )

        if self.review_items:
            item = self.review_items[self.review_focus_index]
            puzzle = item["puzzle"]
            draw_text(self.screen, puzzle.get("name", ""), detail_panel.x + 22,
                      detail_panel.y + 14, get_font(29, bold=True), COLOR_DARK)
            draw_text(self.screen, "复盘札记", detail_panel.x + 24,
                      detail_panel.y + 50, get_font(14), COLOR_ACCENT)
            draw_text(self.screen, puzzle.get("type", ""),
                      detail_panel.right - 62, detail_panel.y + 25,
                      get_font(14), COLOR_RED, center=True)

            tabs = self._get_review_tab_rects()
            for key, label in (("hint", "错因提示"), ("clues", "重看线索")):
                active = self.review_tab == key
                draw_button(
                    self.screen, tabs[key], label, get_font(15),
                    bg_color=COLOR_RED if active else COLOR_SECONDARY,
                    hover=is_mouse_over(tabs[key])
                )

            content_y = detail_panel.y + 132
            pygame.draw.line(self.screen, COLOR_BORDER,
                             (detail_panel.x + 22, content_y - 16),
                             (detail_panel.right - 22, content_y - 16), 1)
            if self.review_tab == "hint":
                content = self.review_system.get_hint_for_puzzle(puzzle.get("id"))
            else:
                content = "逐页重读：\n\n" + "\n\n".join(puzzle.get("clues", []))
            draw_text_block(
                self.screen, content, detail_panel.x + 24, content_y,
                detail_panel.width - 48, get_font(16), COLOR_TEXT, line_spacing=7
            )

            practice_rect = pygame.Rect(detail_panel.right - 166,
                                        detail_panel.bottom - 64, 142, 42)
            draw_button(self.screen, practice_rect, "再练一次", font_normal,
                        bg_color=COLOR_GREEN, hover=is_mouse_over(practice_rect))
        else:
            draw_text(self.screen, "辨证清明", detail_panel.centerx,
                      detail_panel.y + 145, get_font(31, bold=True),
                      COLOR_GREEN, center=True)
            draw_text_block(
                self.screen, "没有错题不是终点。去做一道新题，让这本札记继续长出新页。",
                detail_panel.x + 74, detail_panel.y + 200,
                detail_panel.width - 148, get_font(18), COLOR_GRAY,
                line_spacing=10
            )
            practice_rect = pygame.Rect(detail_panel.centerx - 96,
                                        detail_panel.y + 312, 192, 44)
            draw_button(self.screen, practice_rect, "去挑一题", font_normal,
                        bg_color=COLOR_GREEN, hover=is_mouse_over(practice_rect))

        clear_rect = pygame.Rect(330, 583, 56, 28)
        draw_button(self.screen, clear_rect, "清空", get_font(13),
                    bg_color=COLOR_SECONDARY, hover=is_mouse_over(clear_rect))
        prev_rect = pygame.Rect(180, 650, 100, 42)
        next_rect = pygame.Rect(332, 650, 100, 42)
        draw_button(self.screen, prev_rect, "上一页", font_small,
                    hover=is_mouse_over(prev_rect) and self._review_page_count() > 1)
        draw_button(self.screen, next_rect, "下一页", font_small,
                    hover=is_mouse_over(next_rect) and self._review_page_count() > 1)
        random_rect = self._get_review_random_rect()
        draw_button(self.screen, random_rect, "抽一题温故", font_normal,
                    bg_color=COLOR_GREEN if self.review_items else COLOR_SECONDARY,
                    hover=is_mouse_over(random_rect) and bool(self.review_items))

        back_rect = pygame.Rect(40, 663, 120, 42)
        draw_button(self.screen, back_rect, "返回", font_normal,
                    hover=is_mouse_over(back_rect))

    def _handle_review_click(self, event):
        """处理复盘界面事件"""
        if event.type == pygame.MOUSEWHEEL:
            if pygame.Rect(112, 126, 800, 500).collidepoint(pygame.mouse.get_pos()):
                self._review_change_page(-1 if event.y > 0 else 1)
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        back_rect = pygame.Rect(40, 663, 120, 42)
        if back_rect.collidepoint(event.pos):
            self.set_state(STATE_MENU)
            return
        clear_rect = pygame.Rect(330, 583, 56, 28)
        if clear_rect.collidepoint(event.pos):
            self.popup.show(
                "清空复盘札记",
                "确定要拂去所有错题记录吗？这个动作无法撤回。",
                [("再想想", None), ("清空", self._clear_review_records)]
            )
            return
        if not self.review_items:
            practice_rect = pygame.Rect(414 + (498 - 192) // 2, 126 + 312, 192, 44)
            if practice_rect.collidepoint(event.pos):
                self.set_state(STATE_CHAPTER)
            return

        tabs = self._get_review_tab_rects()
        for key, rect in tabs.items():
            if rect.collidepoint(event.pos):
                self.review_tab = key
                self.scene.burst_herb(event.pos, COLOR_GOLD)
                return

        practice_rect = pygame.Rect(414 + 498 - 166, 126 + 500 - 64, 142, 42)
        if practice_rect.collidepoint(event.pos):
            self._practice_reviewed_puzzle(
                self.review_items[self.review_focus_index]["puzzle"].get("id")
            )
            return

        if self._get_review_random_rect().collidepoint(event.pos):
            if len(self.review_items) > 1:
                choices = [index for index in range(len(self.review_items))
                           if index != self.review_focus_index]
                self.review_focus_index = random.choice(choices)
            self.review_page = self.review_focus_index // 5
            self.scene.burst_herb(event.pos, COLOR_GOLD)
            return

        if pygame.Rect(180, 650, 100, 42).collidepoint(event.pos):
            self._review_change_page(-1)
            return
        if pygame.Rect(332, 650, 100, 42).collidepoint(event.pos):
            self._review_change_page(1)
            return

        for absolute_index, rect in self._get_review_card_rects():
            if rect.collidepoint(event.pos):
                self.review_focus_index = absolute_index
                self.scene.burst_herb(event.pos, COLOR_GOLD)
                return

    def _clear_review_records(self):
        self.review_system.clear_all_records()
        self.popup.close()
        self._init_review_screen()

    # ==================== 设置界面 ====================

    def _init_settings_screen(self):
        """初始化设置界面"""
        self.dragging_slider = None

    def _get_settings_rects(self):
        return {
            "speed": pygame.Rect(372, 210, 356, 30),
            "music": pygame.Rect(754, 334, 86, 38),
            "volume": pygame.Rect(372, 402, 356, 30),
            "reset": pygame.Rect(166, 662, 176, 44),
            "default": pygame.Rect(422, 662, 180, 44),
            "back": pygame.Rect(40, 663, 120, 42),
        }

    def _draw_settings_screen(self):
        """绘制设置界面"""
        self.scene.draw(self.screen, allow_hotspots=self._allow_scene_hotspots())
        draw_page_heading(
            self.screen, "游戏设置",
            subtitle="把字迹与药香调成最顺手的节奏",
            kicker="案前调息", time=self.ui_time, y=12,
            title_size=42, compact=True
        )
        rects = self._get_settings_rects()

        # 文字速度
        speed_panel = pygame.Rect(150, 138, 724, 150)
        draw_panel(self.screen, speed_panel, COLOR_LIGHT, COLOR_GREEN)
        draw_text(self.screen, "文字浮现", speed_panel.x + 24, speed_panel.y + 14,
                  get_font(23, bold=True), COLOR_DARK)
        speed_value = self.settings_manager.get_text_speed()
        draw_text(self.screen, f"{speed_value} 字 / 秒", speed_panel.right - 120,
                  speed_panel.y + 18, get_font(15, bold=True),
                  COLOR_GREEN, center=True)
        speed_rect = rects["speed"]
        draw_text(self.screen, "慢", speed_rect.x - 36, speed_rect.y + 2,
                  font_small, COLOR_GRAY)
        draw_text(self.screen, "快", speed_rect.right + 12, speed_rect.y + 2,
                  font_small, COLOR_GRAY)
        draw_slider(
            self.screen, speed_rect, (speed_value - 10) / 90,
            fill_color=COLOR_GREEN, hover=is_mouse_over(speed_rect)
        )
        preview_elapsed = 1.0 + (self.state_time * speed_value / 18) % 5.0
        preview_font = get_font(16)
        preview, complete = draw_reveal_text_block(
            self.screen, "药香入卷，字句渐明。此页读完，下一页就亮了。",
            speed_panel.x + 24, speed_panel.y + 97,
            speed_panel.width - 48, preview_font,
            color=COLOR_GRAY, elapsed=preview_elapsed,
            chars_per_second=max(10, speed_value * 0.8)
        )
        if complete:
            pulse = 3 + int((math.sin(self.ui_time * 4) + 1) * 2)
            pygame.draw.circle(self.screen, COLOR_GOLD,
                               (speed_panel.right - 28, speed_panel.y + 104), pulse)

        # 音乐与声纹
        audio_panel = pygame.Rect(150, 304, 724, 205)
        draw_panel(self.screen, audio_panel, COLOR_LIGHT, COLOR_ACCENT)
        draw_text(self.screen, "古风乐声", audio_panel.x + 24, audio_panel.y + 14,
                  get_font(23, bold=True), COLOR_DARK)
        draw_text(self.screen, "徽调药香" if self.settings_manager.is_music_on()
                  else "静室听墨", audio_panel.x + 24, audio_panel.y + 48,
                  get_font(15), COLOR_GRAY)
        music_rect = rects["music"]
        music_on = self.settings_manager.is_music_on()
        draw_button(self.screen, music_rect, "开启" if music_on else "关闭",
                    get_font(15), bg_color=COLOR_GREEN if music_on else COLOR_RED,
                    hover=is_mouse_over(music_rect))

        volume = self.settings_manager.get_music_volume()
        draw_text(self.screen, f"音量 {int(volume * 100)}%", 246,
                  audio_panel.y + 107, get_font(16, bold=True), COLOR_DARK)
        vol_rect = rects["volume"]
        draw_slider(self.screen, vol_rect, volume, fill_color=COLOR_ACCENT,
                    hover=is_mouse_over(vol_rect))
        draw_text(self.screen, "静", vol_rect.x - 34, vol_rect.y + 2,
                  font_small, COLOR_GRAY)
        draw_text(self.screen, "响", vol_rect.right + 12, vol_rect.y + 2,
                  font_small, COLOR_GRAY)

        wave_rect = pygame.Rect(746, 378, 106, 58)
        pygame.draw.rect(self.screen, (229, 220, 199), wave_rect, border_radius=4)
        wave_color = COLOR_GREEN if music_on else COLOR_GRAY
        amplitude = (3 + volume * 18) if music_on else 2
        center_y = wave_rect.centery
        for x_offset in range(8, wave_rect.width - 8, 5):
            phase = self.ui_time * 7 + x_offset * 0.32
            y_offset = int(math.sin(phase) * amplitude)
            pygame.draw.line(self.screen, wave_color,
                             (wave_rect.x + x_offset, center_y - y_offset),
                             (wave_rect.x + x_offset, center_y + y_offset), 2)

        # 操作按钮
        reset_rect = rects["reset"]
        default_rect = rects["default"]
        back_rect = rects["back"]
        draw_button(self.screen, reset_rect, "重置进度", font_normal,
                    bg_color=COLOR_RED, hover=is_mouse_over(reset_rect))
        draw_button(self.screen, default_rect, "恢复默认", font_normal,
                    hover=is_mouse_over(default_rect))
        draw_button(self.screen, back_rect, "返回", font_normal, hover=is_mouse_over(back_rect))

    def _handle_settings_click(self, event):
        """处理设置界面事件"""
        rects = self._get_settings_rects()
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_slider = None
            return

        if event.type == pygame.MOUSEMOTION and self.dragging_slider:
            rect = rects[self.dragging_slider]
            ratio = max(0.0, min(1.0, (event.pos[0] - rect.x) / rect.width))
            if self.dragging_slider == "speed":
                self.settings_manager.set_text_speed(int(10 + ratio * 90))
            else:
                self.settings_manager.set_music_volume(ratio)
                self._apply_music_settings()
            return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        speed_hit = rects["speed"].inflate(0, 18)
        volume_hit = rects["volume"].inflate(0, 18)
        if speed_hit.collidepoint(event.pos):
            self.dragging_slider = "speed"
            ratio = max(0.0, min(1.0, (event.pos[0] - rects["speed"].x) / rects["speed"].width))
            self.settings_manager.set_text_speed(int(10 + ratio * 90))
            return
        if volume_hit.collidepoint(event.pos):
            self.dragging_slider = "volume"
            ratio = max(0.0, min(1.0, (event.pos[0] - rects["volume"].x) / rects["volume"].width))
            self.settings_manager.set_music_volume(ratio)
            self._apply_music_settings()
            return

        music_btn_rect = rects["music"]
        if music_btn_rect.collidepoint(event.pos):
            self.settings_manager.set_music_on(not self.settings_manager.is_music_on())
            self._apply_music_settings()
            self.scene.burst_herb(event.pos, COLOR_GOLD)
            return

        reset_rect = rects["reset"]
        if reset_rect.collidepoint(event.pos):
            self.popup.show(
                "确认重置",
                "确定要重置所有游戏进度吗？此操作不可恢复。",
                [("取消", None), ("确定", self._reset_game)]
            )
            return

        default_rect = rects["default"]
        if default_rect.collidepoint(event.pos):
            self.settings_manager.reset_to_default()
            self._apply_music_settings()
            self.scene.burst_herb(event.pos, COLOR_GOLD)
            return

        back_rect = rects["back"]
        if back_rect.collidepoint(event.pos):
            self.set_state(STATE_MENU)

    def _reset_game(self):
        """重置游戏进度"""
        self.save_manager.reset_save()
        self.player_name = ""
        self._init_chapter_screen()
        self.popup.close()
        self.set_state(STATE_PROLOGUE)

    # ==================== 主菜单 ====================

    def _draw_menu_screen(self):
        """绘制主菜单"""
        self.scene.draw(self.screen, allow_hotspots=self._allow_scene_hotspots())
        draw_page_heading(
            self.screen, "古籍解谜",
            subtitle="中医传承｜修一卷古籍，辨一味本草",
            kicker="岐黄手札｜今日开卷", time=self.ui_time,
            y=18, title_size=52, compact=True
        )

        if self.player_name:
            role_font = get_font(13)
            role_text = truncate_text(
                f"案主｜{self.player_name}", role_font, 150
            )
            role_rect = pygame.Rect(816, 58, 174, 30)
            draw_panel(self.screen, role_rect, COLOR_LIGHT, COLOR_GOLD, border_width=1)
            draw_text(self.screen, role_text, role_rect.centerx, role_rect.centery,
                      role_font, COLOR_ACCENT, center=True)

        # 今日药材卡
        herb_rect = self._get_menu_herb_rect()
        herb_hover = is_mouse_over(herb_rect)
        draw_rect = herb_rect.move(0, -3 if herb_hover else 0)
        draw_panel(self.screen, draw_rect, (245, 238, 219),
                   COLOR_GOLD if herb_hover else COLOR_ACCENT)

        herb_name = self._get_daily_herb()
        lore = get_herb_lore(herb_name)
        tag_rect = pygame.Rect(draw_rect.x + 18, draw_rect.y + 16, 92, 25)
        pygame.draw.rect(self.screen, COLOR_ACCENT, tag_rect, border_radius=3)
        draw_text(self.screen, "今日一味", tag_rect.centerx, tag_rect.centery,
                  get_font(14, bold=True), COLOR_LIGHT, center=True)
        draw_text(self.screen, "每日药笺", draw_rect.right - 26,
                  draw_rect.y + 21, get_font(13), COLOR_GRAY, center=True)

        breath = 48 + int((math.sin(self.ui_time * 2.1) + 1) * 3)
        orb = pygame.Surface((132, 132), pygame.SRCALPHA)
        pygame.draw.circle(orb, (*COLOR_GOLD, 28), (66, 66), breath)
        pygame.draw.circle(orb, (*COLOR_ACCENT, 115), (66, 66), breath, 1)
        pygame.draw.circle(orb, (*COLOR_GREEN, 65), (66, 66), 38, 1)
        self.screen.blit(orb, (draw_rect.centerx - 66, draw_rect.y + 44))
        draw_text(self.screen, herb_name, draw_rect.centerx, draw_rect.y + 86,
                  get_font(42, bold=True), COLOR_DARK, center=True)
        draw_text(self.screen, "悬壶有方｜本草可亲", draw_rect.centerx,
                  draw_rect.y + 125, get_font(14), COLOR_ACCENT, center=True)

        pygame.draw.line(self.screen, COLOR_BORDER,
                         (draw_rect.x + 24, draw_rect.y + 151),
                         (draw_rect.right - 24, draw_rect.y + 151), 1)
        info_font = get_font(15)
        draw_text(self.screen, f"性味｜{lore['nature']}",
                  draw_rect.x + 24, draw_rect.y + 164, info_font, COLOR_DARK)
        draw_text(self.screen, f"归经｜{lore['meridian']}",
                  draw_rect.x + 24, draw_rect.y + 192, info_font, COLOR_DARK)
        effect_lines = wrap_text(
            f"功效｜{lore['effect']}", get_font(14), draw_rect.width - 48
        )
        draw_text_block(
            self.screen, "功效｜" + lore["effect"],
            draw_rect.x + 24, draw_rect.y + 224,
            draw_rect.width - 48, get_font(14), COLOR_TEXT, line_spacing=4
        )
        note_lines = wrap_text(lore["note"], get_font(13), draw_rect.width - 48)
        note_y = draw_rect.y + 224 + min(3, max(1, len(effect_lines))) * 22 + 10
        for index, line in enumerate(note_lines[:3]):
            draw_text(self.screen, line, draw_rect.x + 24,
                      note_y + index * 18, get_font(13), COLOR_GRAY)

        open_rect = pygame.Rect(draw_rect.x + 24, draw_rect.bottom - 51,
                                draw_rect.width - 48, 34)
        draw_button(
            self.screen, open_rect, "点开本草札记", get_font(14),
            bg_color=COLOR_GREEN if herb_hover else COLOR_SECONDARY,
            hover=herb_hover
        )

        # 药签式导航
        for btn in self.menu_buttons:
            rect = btn["rect"]
            hover = is_mouse_over(rect)
            draw_rect = rect.move(0, -2 if hover else 0)
            draw_panel(
                self.screen, draw_rect,
                (237, 229, 210) if hover else (247, 242, 228),
                btn["accent"], border_width=1
            )
            seal_rect = pygame.Rect(draw_rect.x + 11, draw_rect.y + 10,
                                    draw_rect.height - 20, draw_rect.height - 20)
            pygame.draw.rect(self.screen, btn["accent"], seal_rect, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_GOLD, seal_rect.inflate(-6, -6),
                             1, border_radius=2)
            draw_text(self.screen, btn["tag"], seal_rect.centerx,
                      seal_rect.centery, get_font(24, bold=True),
                      COLOR_LIGHT, center=True)
            draw_text(self.screen, btn["text"], draw_rect.x + 70,
                      draw_rect.y + 8, get_font(23, bold=True), COLOR_DARK)
            draw_text(self.screen, btn["hint"], draw_rect.x + 70,
                      draw_rect.y + 36, get_font(13), COLOR_GRAY)
            chevron_x = draw_rect.right - 22
            chevron_y = draw_rect.centery
            pygame.draw.lines(
                self.screen, btn["accent"], False,
                [(chevron_x - 6, chevron_y - 7),
                 (chevron_x, chevron_y),
                 (chevron_x - 6, chevron_y + 7)], 2
            )

        # 修卷进度
        progress = self.save_manager.get_progress()
        progress_rect = pygame.Rect(508, 522, 370, 66)
        draw_panel(self.screen, progress_rect, COLOR_SECONDARY, COLOR_GREEN)
        draw_text(self.screen, "修卷手记", progress_rect.x + 16,
                  progress_rect.y + 8, get_font(16, bold=True), COLOR_DARK)
        overview = (
            f"{progress['unlocked_chapters']} 卷已启  ｜  "
            f"{progress['completed_puzzles']} 方已成  ｜  "
            f"辨证 {progress['accuracy']}%"
        )
        draw_text(self.screen, overview, progress_rect.centerx,
                  progress_rect.y + 40, get_font(14), COLOR_DARK, center=True)

    def _handle_menu_click(self, event):
        """处理主菜单点击"""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self._get_menu_herb_rect().collidepoint(event.pos):
            self.scene.burst_herb(event.pos, COLOR_GOLD)
            self._show_herb_note(self._get_daily_herb())
            return
        for btn in self.menu_buttons:
            if btn["rect"].collidepoint(event.pos):
                self.scene.burst_herb(event.pos, COLOR_GOLD)
                btn["action"]()
                return

    # ==================== 主循环 ====================

    async def run(self):
        """游戏主循环"""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # 秒
            self.ui_time += dt
            self.state_time += dt
            self.footer_flash_timer = max(0.0, self.footer_flash_timer - dt)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue

                # 弹窗事件优先处理
                if self.popup.visible:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.popup.close()
                        continue
                    idx = self.popup.handle_event(event, SCREEN_WIDTH, SCREEN_HEIGHT)
                    if idx is not None:
                        # 获取按钮回调
                        buttons = self.popup.buttons
                        if idx < len(buttons):
                            callback = buttons[idx][1]
                            if callback:
                                callback()
                            else:
                                self.popup.close()
                    # 弹窗显示期间阻止点击穿透到底层界面
                    continue

                # 全局回退与退出入口优先于页内操作
                if self._handle_global_nav_event(event):
                    continue

                # 页脚鼓励签始终位于页面最下层，并优先接收换签点击
                if self._handle_footer_event(event):
                    continue

                # 百草柜互动优先于界面按钮，但仅在外围区域启用
                hotspot = self.scene.handle_event(
                    event, active=self._allow_scene_hotspots()
                )
                if hotspot:
                    self._show_herb_note(hotspot["herb"])
                    continue

                # 根据当前状态分发事件
                if self.state == STATE_MENU:
                    self._handle_menu_click(event)
                elif self.state == STATE_PROLOGUE:
                    self._handle_prologue_event(event)
                elif self.state == STATE_CHAPTER:
                    self._handle_chapter_click(event)
                elif self.state == STATE_INTRO:
                    self._handle_intro_click(event)
                elif self.state == STATE_PUZZLE:
                    self._handle_puzzle_event(event)
                elif self.state == STATE_ENDING:
                    self._handle_ending_click(event)
                elif self.state == STATE_ARCHIVE:
                    self._handle_archive_click(event)
                elif self.state == STATE_REVIEW:
                    self._handle_review_click(event)
                elif self.state == STATE_SETTINGS:
                    self._handle_settings_click(event)

            # 更新谜题打字机效果
            if self.state == STATE_PUZZLE and self.current_puzzle_system:
                self.current_puzzle_system.update(dt)
            self.scene.update(dt)

            # 更新角色设定界面光标闪烁
            if self.state == STATE_PROLOGUE:
                self.cursor_timer += dt
                if self.cursor_timer >= 0.5:
                    self.cursor_timer = 0
                    self.cursor_visible = not self.cursor_visible

            # 绘制当前状态
            if self.state == STATE_MENU:
                self._draw_menu_screen()
            elif self.state == STATE_PROLOGUE:
                self._draw_prologue_screen()
            elif self.state == STATE_CHAPTER:
                self._draw_chapter_screen()
            elif self.state == STATE_INTRO:
                self._draw_intro_screen()
            elif self.state == STATE_PUZZLE:
                self._draw_puzzle_screen()
            elif self.state == STATE_ENDING:
                self._draw_ending_screen()
            elif self.state == STATE_ARCHIVE:
                self._draw_archive_screen()
            elif self.state == STATE_REVIEW:
                self._draw_review_screen()
            elif self.state == STATE_SETTINGS:
                self._draw_settings_screen()

            self._draw_page_footer()
            self._draw_global_nav()

            # 药叶粒子与答题边框反馈
            self.scene.draw_foreground(self.screen)

            # 绘制弹窗
            self.popup.draw(self.screen)

            pygame.display.flip()
            # 把控制权交还浏览器事件循环，Pygbag 才能持续刷新画面和接收输入。
            await asyncio.sleep(0)

        pygame.quit()
        if not IS_WEB:
            sys.exit()


async def main():
    game = Game()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
