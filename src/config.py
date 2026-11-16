# config.py
# 游戏全局配置，保存路径、颜色、状态常量等

import os

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 资源路径
DATA_DIR = os.path.join(BASE_DIR, "data")
SAVE_DIR = os.path.join(BASE_DIR, "save")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

# 关键文件路径
GAME_DATA_PATH = os.path.join(DATA_DIR, "game_data.json")
SAVE_PATH = os.path.join(SAVE_DIR, "save_data.json")
SETTINGS_PATH = os.path.join(SAVE_DIR, "settings.json")

# 窗口默认尺寸
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# 游戏状态常量
STATE_MENU = "menu"             # 主菜单
STATE_PROLOGUE = "prologue"     # 开篇角色设定
STATE_CHAPTER = "chapter"       # 章节选择
STATE_INTRO = "intro"           # 章节开篇
STATE_PUZZLE = "puzzle"         # 解谜界面
STATE_ARCHIVE = "archive"       # 图鉴界面
STATE_REVIEW = "review"         # 复盘界面
STATE_SETTINGS = "settings"     # 设置界面
STATE_ENDING = "ending"         # 章节结局

# 古风配色方案：旧纸、朱砂、青玉与松烟墨
COLOR_BG = (237, 230, 211)          # 宣纸底色
COLOR_TEXT = (53, 48, 40)           # 浓墨色
COLOR_ACCENT = (150, 49, 39)        # 朱砂色
COLOR_SECONDARY = (205, 190, 158)   # 浅赭辅助色
COLOR_LIGHT = (250, 247, 236)       # 米白色
COLOR_DARK = (44, 54, 47)           # 松烟墨绿
COLOR_RED = (164, 55, 45)           # 朱砂红
COLOR_GREEN = (51, 110, 83)         # 青玉色
COLOR_GOLD = (177, 139, 68)         # 古金色
COLOR_GRAY = (122, 119, 111)        # 灰墨色
COLOR_BORDER = (155, 123, 79)       # 边框色

# 字体大小
FONT_SIZE_SMALL = 18
FONT_SIZE_NORMAL = 22
FONT_SIZE_LARGE = 28
FONT_SIZE_TITLE = 36

# 默认设置
DEFAULT_TEXT_SPEED = 30      # 文字显示速度，数字越大越快
DEFAULT_MUSIC_VOLUME = 0.5
DEFAULT_MUSIC_ON = True
