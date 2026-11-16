# tcm_scene.py
# 中医药主题场景、本草释义与轻量互动效果

import math
import random

import pygame

from src.config import (
    COLOR_TEXT, COLOR_DARK, COLOR_LIGHT, COLOR_ACCENT, COLOR_GREEN,
    COLOR_GOLD, COLOR_GRAY, COLOR_BORDER, FONT_SIZE_SMALL
)
from src.utils import get_font, draw_text, draw_text_block, wrap_text


PAPER = (239, 231, 212)
PAPER_LIGHT = (250, 247, 237)
WOOD = (117, 79, 52)
WOOD_LIGHT = (158, 116, 78)
WOOD_DARK = (70, 45, 32)
JADE = (49, 105, 82)
JADE_LIGHT = (91, 139, 111)
CINNABAR = (151, 52, 43)
INK = (43, 47, 42)
GOLD = (178, 141, 72)


HERB_LORE = {
    "桂枝": ("辛、甘，温", "心、肺、膀胱经", "发汗解肌，温通经脉。", "桂枝汤中的君药，善解肌表之风寒。"),
    "白芍": ("苦、酸，微寒", "肝、脾经", "养血敛阴，柔肝止痛。", "与桂枝相配，一散一收，调和营卫。"),
    "生姜": ("辛，微温", "肺、脾、胃经", "解表散寒，温中止呕。", "药食同源，常作方中佐使。"),
    "大枣": ("甘，温", "脾、胃、心经", "补中益气，养血安神。", "与生姜同用，善和脾胃。"),
    "炙甘草": ("甘，平", "心、肺、脾、胃经", "补脾益气，调和诸药。", "蜜炙后偏于温补，是方中常用的和事佬。"),
    "甘草": ("甘，平", "心、肺、脾、胃经", "补脾益气，清热解毒，调和诸药。", "生用偏于清热，炙用偏于补中。"),
    "生甘草": ("甘，平", "心、肺、脾、胃经", "清热解毒，润肺止咳，调和诸药。", "银翘散中用以清利咽喉。"),
    "麻黄": ("辛、微苦，温", "肺、膀胱经", "发汗解表，宣肺平喘。", "发汗力强，体虚者不可轻用。"),
    "杏仁": ("苦，微温；有小毒", "肺、大肠经", "降气止咳平喘，润肠通便。", "麻黄汤中助宣降肺气。"),
    "葛根": ("甘、辛，凉", "脾、胃、肺经", "解肌退热，生津止渴。", "善治项背强痛与热病口渴。"),
    "连翘": ("苦，微寒", "肺、心、小肠经", "清热解毒，消肿散结。", "银翘散中的清热解毒主力。"),
    "金银花": ("甘，寒", "肺、心、胃经", "清热解毒，疏散风热。", "花初开为银白，后转为金黄，故名金银花。"),
    "薄荷": ("辛，凉", "肺、肝经", "疏散风热，清利头目。", "香气清扬，常用于风热表证。"),
    "牛蒡子": ("辛、苦，寒", "肺、胃经", "疏散风热，解毒利咽。", "银翘散中助透表清热。"),
    "荆芥穗": ("辛，微温", "肺、肝经", "解表散风，透疹止痒。", "辛散而不燥，常用于外感表证。"),
    "淡豆豉": ("苦、辛，凉", "肺、胃经", "解表除烦，宣发郁热。", "与栀子同用，可治虚烦不眠。"),
    "桔梗": ("苦、辛，平", "肺经", "宣肺利咽，祛痰排脓。", "有“舟楫之剂”之称，能载药上行。"),
    "桑叶": ("甘、苦，寒", "肺、肝经", "疏散风热，清肺润燥。", "桑菊饮中的君药，善清肺络之热。"),
    "菊花": ("甘、苦，微寒", "肺、肝经", "疏散风热，平肝明目。", "与桑叶相须，轻清宣透。"),
    "芦根": ("甘，寒", "肺、胃经", "清热生津，除烦止呕。", "常用于热病津伤口渴。"),
    "石膏": ("甘、辛，大寒", "肺、胃经", "清热泻火，除烦止渴。", "白虎汤中的君药，清气分实热。"),
    "知母": ("苦、甘，寒", "肺、胃、肾经", "清热泻火，滋阴润燥。", "与石膏同用，清热而不伤津。"),
    "粳米": ("甘，平", "脾、胃经", "补中益气，健脾和胃。", "白虎汤中护胃生津。"),
    "黄连": ("苦，寒", "心、脾、胃、肝、胆、大肠经", "清热燥湿，泻火解毒。", "大苦大寒，善清心胃之火。"),
    "黄芩": ("苦，寒", "肺、胆、脾、大肠、小肠经", "清热燥湿，泻火解毒。", "善清上焦肺热。"),
    "黄柏": ("苦，寒", "肾、膀胱经", "清热燥湿，泻火除蒸。", "偏清下焦湿热。"),
    "栀子": ("苦，寒", "心、肺、三焦经", "泻火除烦，清热利湿。", "可引三焦之火从小便而出。"),
    "大黄": ("苦，寒", "脾、胃、大肠、肝、心包经", "泻下攻积，清热泻火。", "药力峻猛，为攻下要药。"),
    "犀角": ("苦、咸，寒", "心、肝、胃经", "清营凉血，解毒定惊。", "现代多以水牛角替代，古籍中保留原名。"),
    "生地黄": ("甘，寒", "心、肝、肾经", "清热凉血，养阴生津。", "清营汤中养阴凉血。"),
    "生地": ("甘，寒", "心、肝、肾经", "清热凉血，养阴生津。", "清营凉血的重要药物。"),
    "玄参": ("甘、苦、咸，微寒", "肺、胃、肾经", "清热凉血，滋阴降火。", "常与生地、麦冬同用。"),
    "竹叶心": ("甘、淡，寒", "心、肺、胃经", "清心除烦，利尿。", "取竹叶卷心，善清心火。"),
    "麦冬": ("甘、微苦，微寒", "心、肺、胃经", "养阴生津，润肺清心。", "热病后期常用以养阴。"),
    "丹参": ("苦，微寒", "心、肝经", "活血祛瘀，清心除烦。", "一味丹参，功同四物。"),
    "龙胆草": ("苦，寒", "肝、胆经", "清热燥湿，泻肝胆火。", "龙胆泻肝汤中的君药。"),
    "泽泻": ("甘，寒", "肾、膀胱经", "利水渗湿，泄热。", "五苓散中利水的重要药物。"),
    "木通": ("苦，寒", "心、小肠、膀胱经", "利尿通淋，清心降火。", "现代使用需注意品种与用量。"),
    "车前子": ("甘，微寒", "肝、肾、肺、小肠经", "清热利尿，渗湿通淋。", "善利水湿，使邪从小便而去。"),
    "当归": ("甘、辛，温", "肝、心、脾经", "补血活血，调经止痛。", "补血而不滞，活血而不破。"),
    "人参": ("甘、微苦，微温", "脾、肺、心、肾经", "大补元气，补脾益肺。", "四君子汤中的补气君药。"),
    "白术": ("苦、甘，温", "脾、胃经", "健脾益气，燥湿利水。", "补气健脾的常用药。"),
    "茯苓": ("甘、淡，平", "心、肺、脾、肾经", "利水渗湿，健脾宁心。", "淡渗利湿而不伤正。"),
    "黄芪": ("甘，微温", "脾、肺经", "补气升阳，固表止汗。", "补中益气汤中的君药。"),
    "陈皮": ("苦、辛，温", "肺、脾经", "理气健脾，燥湿化痰。", "陈久者良，故名陈皮。"),
    "半夏": ("辛，温；有毒", "脾、胃、肺经", "燥湿化痰，降逆止呕。", "需炮制后使用，生姜可制其毒。"),
    "川芎": ("辛，温", "肝、胆、心包经", "活血行气，祛风止痛。", "血中之气药，善行血中之滞。"),
    "熟地黄": ("甘，微温", "肝、肾经", "补血滋阴，益精填髓。", "四物汤中滋阴补血。"),
    "阿胶": ("甘，平", "肺、肝、肾经", "补血滋阴，润燥止血。", "烊化服用，为补血要药。"),
    "龙眼肉": ("甘，温", "心、脾经", "补益心脾，养血安神。", "药食同源，善治心脾两虚。"),
    "升麻": ("辛、微甘，微寒", "肺、脾、胃、大肠经", "发表透疹，升举阳气。", "与柴胡同用，可升举下陷之气。"),
    "柴胡": ("苦、辛，微寒", "肝、胆、肺经", "疏散退热，疏肝解郁。", "善解少阳，也能升举阳气。"),
    "香附": ("辛、微苦、微甘，平", "肝、脾、三焦经", "疏肝解郁，理气宽中。", "被称为“气病之总司，女科之主帅”。"),
    "枳壳": ("苦、辛、酸，微寒", "脾、胃经", "理气宽中，行滞消胀。", "与柴胡相配，一升一降。"),
    "赤芍": ("苦，微寒", "肝经", "清热凉血，散瘀止痛。", "血府逐瘀汤中活血凉血。"),
    "牛膝": ("苦、甘、酸，平", "肝、肾经", "活血通经，引血下行。", "与桔梗同用，一升一降调畅气血。"),
    "桃仁": ("苦、甘，平；有小毒", "心、肝、大肠经", "活血祛瘀，润肠通便。", "桃红四物汤中的活血药。"),
    "红花": ("辛，温", "心、肝经", "活血通经，散瘀止痛。", "常与桃仁相须为用。"),
    "苍术": ("辛、苦，温", "脾、胃、肝经", "燥湿健脾，祛风散寒。", "平胃散中燥湿运脾。"),
    "神曲": ("甘、辛，温", "脾、胃经", "消食和胃。", "越鞠丸中治食郁。"),
    "厚朴": ("苦、辛，温", "脾、胃、肺、大肠经", "燥湿消痰，下气除满。", "善除脘腹胀满。"),
    "薏苡仁": ("甘、淡，凉", "脾、胃、肺经", "利水渗湿，健脾除痹。", "药食同源，善渗湿健脾。"),
    "竹茹": ("甘，微寒", "肺、胃、心、胆经", "清热化痰，除烦止呕。", "温胆汤中清胆胃之热。"),
    "枳实": ("苦、辛、酸，微寒", "脾、胃经", "破气消积，化痰散痞。", "与竹茹相配，理气化痰。"),
    "胆南星": ("苦、微辛，凉", "肺、肝、脾经", "清热化痰，息风定惊。", "天南星经胆汁制后性转凉。"),
    "猪苓": ("甘、淡，平", "肾、膀胱经", "利水渗湿。", "五苓散中利水渗湿。"),
    "乌梅": ("酸、涩，平", "肝、脾、肺、大肠经", "敛肺生津，涩肠止泻。", "二陈汤中少量使用以敛肺。"),
    "艾叶": ("辛、苦，温；有小毒", "肝、脾、肾经", "温经止血，散寒止痛。", "晒干后香气清苦，是药囊与艾灸常用的本草。"),
}


def get_herb_lore(herb_name):
    """返回本草释义；补全题中的非药材词使用线索说明。"""
    if herb_name in HERB_LORE:
        nature, meridian, effect, note = HERB_LORE[herb_name]
        return {
            "name": herb_name,
            "nature": nature,
            "meridian": meridian,
            "effect": effect,
            "note": note,
            "is_herb": True,
        }
    return {
        "name": herb_name,
        "nature": "方剂线索",
        "meridian": "非单味药材",
        "effect": "这是文字缺失补全题中的方剂关键字。",
        "note": "结合前后文与方剂功效，判断应填入的内容。",
        "is_herb": False,
    }


def draw_chapter_emblem(screen, center, chapter_id, unlocked=True):
    """绘制章节药材徽记，使用代码图形避免额外资源依赖。"""
    cx, cy = center
    main_color = JADE if unlocked else (130, 126, 118)
    pale_color = (222, 216, 199) if unlocked else (208, 203, 192)

    pygame.draw.circle(screen, pale_color, center, 31)
    pygame.draw.circle(screen, main_color, center, 31, 2)

    if chapter_id == "qingre":
        pygame.draw.polygon(screen, CINNABAR if unlocked else main_color,
                            [(cx, cy - 18), (cx - 11, cy + 9), (cx, cy + 17), (cx + 11, cy + 9)])
        pygame.draw.line(screen, pale_color, (cx, cy - 8), (cx, cy + 10), 3)
    elif chapter_id == "buyi":
        pygame.draw.circle(screen, main_color, (cx, cy - 8), 9, 2)
        pygame.draw.line(screen, main_color, (cx, cy + 1), (cx, cy + 18), 4)
        pygame.draw.line(screen, main_color, (cx - 10, cy + 9), (cx + 10, cy + 9), 3)
        pygame.draw.line(screen, main_color, (cx - 8, cy + 18), (cx - 15, cy + 10), 2)
        pygame.draw.line(screen, main_color, (cx + 8, cy + 18), (cx + 15, cy + 10), 2)
    elif chapter_id == "liqihuoxue":
        pygame.draw.line(screen, main_color, (cx - 15, cy + 14), (cx + 12, cy - 14), 3)
        pygame.draw.line(screen, main_color, (cx - 8, cy + 1), (cx - 16, cy - 8), 2)
        pygame.draw.line(screen, main_color, (cx + 2, cy - 4), (cx + 13, cy + 2), 2)
        for px, py in ((cx - 15, cy + 14), (cx + 12, cy - 14), (cx - 16, cy - 8), (cx + 13, cy + 2)):
            pygame.draw.circle(screen, main_color, (px, py), 4)
    elif chapter_id == "qushihuatan":
        pygame.draw.polygon(screen, main_color,
                            [(cx, cy - 20), (cx - 14, cy + 5), (cx, cy + 19), (cx + 14, cy + 5)])
        pygame.draw.arc(screen, pale_color, (cx - 8, cy - 2, 16, 13), 0.2, 2.9, 2)
    else:
        pygame.draw.line(screen, main_color, (cx - 11, cy + 17), (cx + 8, cy - 16), 3)
        leaves = [((cx - 2, cy - 5), 10, 0.8), ((cx + 4, cy + 3), 10, 2.5),
                  ((cx - 8, cy + 11), 8, -0.4)]
        for (lx, ly), size, angle in leaves:
            leaf = pygame.Surface((size * 2, size), pygame.SRCALPHA)
            pygame.draw.ellipse(leaf, main_color, leaf.get_rect())
            leaf = pygame.transform.rotate(leaf, math.degrees(angle))
            screen.blit(leaf, (lx - leaf.get_width() // 2, ly - leaf.get_height() // 2))


class TCMScene:
    """可复用的中医药场景背景与本草互动层。"""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.time = 0.0
        self.hovered_key = None
        self.particles = []
        self.feedback_timer = 0.0
        self.feedback_color = JADE
        self.backdrop = self._build_backdrop()
        self.hotspots = self._build_hotspots()
        self._rng = random.Random(1207)

    def _build_hotspots(self):
        left_herbs = ["桂枝", "白芍", "当归", "黄芪"]
        right_herbs = ["柴胡", "甘草", "麦冬", "连翘"]
        hotspots = []
        for index, herb in enumerate(left_herbs):
            hotspots.append({
                "key": f"left_{index}",
                "herb": herb,
                "rect": pygame.Rect(12, 155 + index * 106, 80, 54),
            })
        for index, herb in enumerate(right_herbs):
            hotspots.append({
                "key": f"right_{index}",
                "herb": herb,
                "rect": pygame.Rect(self.width - 92, 155 + index * 106, 80, 54),
            })
        hotspots.append({
            "key": "herb_pot",
            "herb": "艾叶",
            "rect": pygame.Rect(self.width - 124, self.height - 126, 88, 88),
        })
        return hotspots

    def _build_backdrop(self):
        surface = pygame.Surface((self.width, self.height))
        surface.fill(PAPER)
        rng = random.Random(20261114)

        grain = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for _ in range(360):
            x = rng.randrange(self.width)
            y = rng.randrange(self.height)
            length = rng.randrange(5, 34)
            alpha = rng.randrange(10, 24)
            pygame.draw.line(grain, (110, 91, 65, alpha), (x, y), (x + length, y + rng.choice((-1, 0, 1))), 1)
        for _ in range(18):
            x = rng.randrange(self.width)
            y = rng.randrange(self.height)
            radius = rng.randrange(18, 60)
            pygame.draw.circle(grain, (126, 93, 55, rng.randrange(3, 8)), (x, y), radius)
        surface.blit(grain, (0, 0))

        self._draw_ink_landscape(surface)
        self._draw_cabinet(surface, 5, ["桂枝", "白芍", "当归", "黄芪"])
        self._draw_cabinet(surface, self.width - 97, ["柴胡", "甘草", "麦冬", "连翘"])
        self._draw_seal(surface, (54, 25), "岐黄")
        self._draw_seal(surface, (self.width - 54, 25), "本草")
        self._draw_herb_sprig(surface, (self.width - 155, self.height - 205), 1.1)
        self._draw_medicine_pot(surface, (self.width - 82, self.height - 70))
        return surface

    def _draw_ink_landscape(self, surface):
        wash = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.polygon(wash, (49, 72, 61, 16), [
            (0, self.height - 50), (110, self.height - 155), (210, self.height - 75),
            (330, self.height - 185), (455, self.height - 72), (590, self.height - 160),
            (720, self.height - 70), (855, self.height - 150), (self.width, self.height - 55),
            (self.width, self.height), (0, self.height)
        ])
        pygame.draw.polygon(wash, (43, 57, 51, 10), [
            (0, self.height - 15), (145, self.height - 95), (280, self.height - 25),
            (430, self.height - 120), (610, self.height - 30), (790, self.height - 105),
            (self.width, self.height - 18), (self.width, self.height), (0, self.height)
        ])
        surface.blit(wash, (0, 0))

    def _draw_cabinet(self, surface, x, herbs):
        body = pygame.Rect(x, 89, 92, 530)
        pygame.draw.rect(surface, WOOD_DARK, body, border_radius=6)
        pygame.draw.rect(surface, WOOD, body.inflate(-8, -8), border_radius=4)
        pygame.draw.rect(surface, GOLD, body, 2, border_radius=6)

        top = pygame.Rect(x + 9, 101, 74, 34)
        pygame.draw.rect(surface, WOOD_DARK, top, border_radius=3)
        draw_text(surface, "百草柜", top.centerx, top.centery, get_font(16), (236, 218, 173), center=True)

        for index, herb in enumerate(herbs):
            drawer = pygame.Rect(x + 9, 147 + index * 106, 74, 66)
            pygame.draw.rect(surface, WOOD_LIGHT, drawer, border_radius=3)
            pygame.draw.rect(surface, WOOD_DARK, drawer, 1, border_radius=3)
            pygame.draw.line(surface, (135, 94, 60), (drawer.x + 8, drawer.y + 38),
                             (drawer.right - 8, drawer.y + 38), 1)
            draw_text(surface, herb, drawer.centerx, drawer.y + 18,
                      get_font(17), (67, 48, 34), center=True)
            pygame.draw.circle(surface, (214, 174, 83), (drawer.centerx, drawer.y + 49), 4)
            pygame.draw.circle(surface, (94, 62, 37), (drawer.centerx, drawer.y + 49), 4, 1)

        pygame.draw.rect(surface, WOOD_DARK, (x + 5, 610, 82, 11), border_radius=3)

    def _draw_seal(self, surface, center, text):
        seal = pygame.Surface((58, 58), pygame.SRCALPHA)
        pygame.draw.rect(seal, (151, 52, 43, 180), (3, 3, 52, 52), border_radius=3)
        pygame.draw.rect(seal, (112, 35, 31, 205), (7, 7, 44, 44), 1, border_radius=2)
        font = get_font(16)
        rendered = font.render(text, True, (249, 226, 201))
        seal.blit(rendered, rendered.get_rect(center=(29, 29)))
        rotated = pygame.transform.rotate(seal, -4)
        surface.blit(rotated, rotated.get_rect(center=center))

    def _draw_herb_sprig(self, surface, origin, scale=1.0):
        x, y = origin
        stem = (86, 116, 76)
        pygame.draw.line(surface, stem, (x, y + int(100 * scale)), (x + int(36 * scale), y - int(62 * scale)), 3)
        for index in range(6):
            py = y + int(75 * scale) - index * int(24 * scale)
            px = x + int(index * 7 * scale)
            direction = -1 if index % 2 else 1
            leaf_center = (px + direction * 16, py - 5)
            leaf_rect = pygame.Rect(0, 0, 27, 13)
            leaf = pygame.Surface(leaf_rect.size, pygame.SRCALPHA)
            pygame.draw.ellipse(leaf, (56, 103, 75), leaf.get_rect())
            pygame.draw.line(leaf, (222, 230, 205), (3, 6), (23, 6), 1)
            rotated = pygame.transform.rotate(leaf, -35 * direction)
            surface.blit(rotated, rotated.get_rect(center=leaf_center))

    def _draw_medicine_pot(self, surface, center):
        cx, cy = center
        shadow = pygame.Rect(cx - 41, cy - 5, 82, 20)
        pygame.draw.ellipse(surface, (86, 74, 57, 60), shadow)
        pot = [(cx - 34, cy - 38), (cx + 27, cy - 38), (cx + 22, cy + 3), (cx - 23, cy + 3)]
        pygame.draw.polygon(surface, (74, 82, 72), pot)
        pygame.draw.ellipse(surface, (52, 62, 54), (cx - 35, cy - 49, 62, 22))
        pygame.draw.ellipse(surface, (96, 103, 89), (cx - 27, cy - 44, 46, 12), 2)
        pygame.draw.line(surface, (46, 53, 47), (cx - 16, cy - 46), (cx + 20, cy - 52), 3)
        draw_text(surface, "药", cx, cy - 16, get_font(18), (214, 202, 171), center=True)

    def handle_event(self, event, active=True):
        """处理本草柜悬停与点击，返回被点击的互动项。"""
        if not active:
            self.hovered_key = None
            return None

        if event.type == pygame.MOUSEMOTION:
            self.hovered_key = None
            for hotspot in self.hotspots:
                if hotspot["rect"].collidepoint(event.pos):
                    self.hovered_key = hotspot["key"]
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for hotspot in self.hotspots:
                if hotspot["rect"].collidepoint(event.pos):
                    return hotspot
        return None

    def get_hotspot_herb(self, key):
        for hotspot in self.hotspots:
            if hotspot["key"] == key:
                return hotspot["herb"]
        return None

    def update(self, dt):
        self.time += dt
        if self.feedback_timer > 0:
            self.feedback_timer = max(0.0, self.feedback_timer - dt)
        alive = []
        for particle in self.particles:
            particle["life"] -= dt
            if particle["life"] <= 0:
                continue
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vy"] += 28 * dt
            alive.append(particle)
        self.particles = alive

    def burst_herb(self, position, color=None):
        """药材点击时产生轻量药叶粒子。"""
        base_color = color or JADE_LIGHT
        for index in range(12):
            angle = self._rng.uniform(-math.pi, 0)
            speed = self._rng.uniform(35, 105)
            self.particles.append({
                "x": float(position[0]),
                "y": float(position[1]),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": self._rng.uniform(0.45, 0.9),
                "max_life": 0.9,
                "size": self._rng.choice((2, 3, 4)),
                "color": base_color if index % 3 else GOLD,
            })

    def flash_feedback(self, correct):
        self.feedback_timer = 0.7
        self.feedback_color = JADE if correct else CINNABAR

    def draw(self, screen, allow_hotspots=False):
        screen.blit(self.backdrop, (0, 0))
        self._draw_ambient(screen)
        if allow_hotspots:
            self._draw_hotspots(screen)

    def _draw_ambient(self, screen):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for index in range(3):
            phase = self.time * 0.6 + index * 1.7
            x = self.width - 83 + math.sin(phase) * 10
            y = self.height - 130 - (self.time * 18 + index * 19) % 88
            radius = 5 + index * 2
            alpha = max(0, 42 - index * 9 - int((self.height - 130 - y) * 0.15))
            pygame.draw.circle(overlay, (92, 109, 91, alpha), (int(x), int(y)), radius)

        for index in range(8):
            phase = self.time * 0.22 + index * 0.85
            right_side = index % 2 == 0
            base_x = self.width - 145 if right_side else 125
            x = base_x + math.sin(phase) * (16 + index * 2)
            y = 120 + ((self.time * (7 + index * 0.8) + index * 74) % (self.height - 240))
            pygame.draw.ellipse(overlay, (66, 113, 82, 26), (int(x), int(y), 7, 3))
        screen.blit(overlay, (0, 0))

    def _draw_hotspots(self, screen):
        glow = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for hotspot in self.hotspots:
            if hotspot["key"] == self.hovered_key:
                pygame.draw.rect(glow, (240, 205, 112, 58), hotspot["rect"], border_radius=4)
                pygame.draw.rect(glow, (185, 137, 54, 190), hotspot["rect"], 2, border_radius=4)
        screen.blit(glow, (0, 0))

        if self.hovered_key:
            herb = self.get_hotspot_herb(self.hovered_key)
            if herb:
                self.draw_herb_tooltip(screen, herb, pygame.mouse.get_pos())

    def draw_herb_tooltip(self, screen, herb_name, anchor):
        """在鼠标附近绘制本草释义浮签。"""
        lore = get_herb_lore(herb_name)
        width = 348
        height = 132
        x = anchor[0] + 18
        y = anchor[1] + 18
        if x + width > self.width - 12:
            x = anchor[0] - width - 18
        if y + height > self.height - 12:
            y = anchor[1] - height - 18
        x = max(12, min(x, self.width - width - 12))
        y = max(12, min(y, self.height - height - 12))

        shadow = pygame.Rect(x + 5, y + 6, width, height)
        pygame.draw.rect(screen, (65, 48, 34), shadow, border_radius=6)
        panel = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, PAPER_LIGHT, panel, border_radius=6)
        pygame.draw.rect(screen, JADE, panel, 2, border_radius=6)
        pygame.draw.rect(screen, JADE, (x, y, width, 34), border_top_left_radius=6, border_top_right_radius=6)
        draw_text(screen, f"{lore['name']}  ｜  {lore['nature']}", x + 12, y + 7,
                  get_font(18), (248, 245, 228))
        draw_text(screen, f"归经：{lore['meridian']}", x + 12, y + 42,
                  get_font(15), COLOR_DARK)
        effect_lines = wrap_text(lore["effect"], get_font(16), width - 24)
        draw_text(screen, effect_lines[0] if effect_lines else "", x + 12, y + 66,
                  get_font(16), COLOR_TEXT)
        if len(effect_lines) > 1:
            draw_text(screen, effect_lines[1], x + 12, y + 89,
                      get_font(16), COLOR_TEXT)
        elif lore.get("note"):
            note_lines = wrap_text(lore["note"], get_font(14), width - 24)
            draw_text(screen, note_lines[0] if note_lines else "", x + 12, y + 92,
                      get_font(14), COLOR_GRAY)
        return panel

    def draw_foreground(self, screen):
        """绘制粒子与答题反馈，使交互有即时手感。"""
        for particle in self.particles:
            ratio = max(0.0, particle["life"] / particle["max_life"])
            size = max(1, int(particle["size"] * (0.55 + ratio * 0.45)))
            color = tuple(int(c * (0.55 + ratio * 0.45)) for c in particle["color"])
            pygame.draw.circle(screen, color, (int(particle["x"]), int(particle["y"])), size)

        if self.feedback_timer > 0:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            alpha = int(90 * (self.feedback_timer / 0.7))
            pygame.draw.rect(overlay, (*self.feedback_color, alpha), screen.get_rect(), 7)
            screen.blit(overlay, (0, 0))
