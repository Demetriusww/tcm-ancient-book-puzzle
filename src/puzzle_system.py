# puzzle_system.py
# 核心解谜系统，实现四层推理逻辑与方剂校验

from src.utils import get_font, wrap_text, draw_text, draw_text_block
from src.config import (
    COLOR_BG, COLOR_TEXT, COLOR_ACCENT, COLOR_SECONDARY,
    COLOR_LIGHT, COLOR_DARK, COLOR_RED, COLOR_GREEN,
    FONT_SIZE_NORMAL, FONT_SIZE_LARGE
)


class PuzzleSystem:
    """
    解谜系统：
    1. 残缺线索展示
    2. 药材筛选（从选项中选择）
    3. 君臣佐使配伍（按选择顺序排列）
    4. 方剂校验（与正确答案比对）
    """

    def __init__(self, puzzle_data, text_speed=30):
        self.puzzle = puzzle_data
        self.text_speed = text_speed

        # 玩家当前选择的药材
        self.selected_herbs = []
        # 文字缺失补全类谜题的填空答案
        self.missing_answers = []
        # 当前显示到哪条线索（用于逐条显示效果）
        self.visible_clue_index = 0
        # 当前显示的字符数（用于打字机效果）
        self.char_timer = 0
        # 反馈信息
        self.feedback = ""
        self.feedback_color = COLOR_TEXT
        self.show_answer = False
        # 当前是否已完成
        self.solved = False

        # 预计算字体
        self.font_normal = get_font(FONT_SIZE_NORMAL)
        self.font_large = get_font(FONT_SIZE_LARGE)

    def get_puzzle_type(self):
        """获取谜题类型"""
        return self.puzzle.get("type", "配伍补全")

    def get_name(self):
        """获取方剂名称"""
        return self.puzzle.get("name", "未知方剂")

    def get_clues(self):
        """获取所有残缺线索，并为散佚或空白内容提供可见占位。"""
        raw_clues = self.puzzle.get("clues", [])
        if isinstance(raw_clues, str):
            raw_clues = [raw_clues]
        elif not isinstance(raw_clues, (list, tuple)):
            raw_clues = []

        if not raw_clues:
            raw_clues = [self.puzzle.get("clue", "")]

        clues = []
        for index, clue in enumerate(raw_clues):
            text = str(clue).strip() if clue is not None else ""
            if not text:
                text = (
                    f"线索卡{index + 1}：此页墨迹散佚，"
                    "请点击“讨条线索”查看中医解析。"
                )
            clues.append(text)
        return clues

    def get_options(self):
        """获取候选药材选项"""
        return self.puzzle.get("options", [])

    def get_correct_answer(self):
        """获取正确答案药材列表"""
        return self.puzzle.get("correct_answer", [])

    def get_missing_text(self):
        """获取文字缺失补全类谜题的缺失文本答案"""
        return self.puzzle.get("missing_text", [])

    def toggle_herb(self, herb):
        """选中或取消选中一味药材"""
        if herb in self.selected_herbs:
            self.selected_herbs.remove(herb)
        else:
            self.selected_herbs.append(herb)
        self.feedback = ""

    def set_missing_answer(self, index, text):
        """设置文字缺失补全的答案"""
        while len(self.missing_answers) <= index:
            self.missing_answers.append("")
        self.missing_answers[index] = text
        self.feedback = ""

    def clear_selection(self):
        """清空当前选择"""
        self.selected_herbs = []
        self.missing_answers = []
        self.feedback = ""

    def check_answer(self):
        """
        校验玩家答案：
        - 配伍补全/药性推理/病症反推：比较selected_herbs与correct_answer
        - 文字缺失补全：先检查填空，再比较药材
        返回 (是否正确, 提示信息)
        """
        puzzle_type = self.get_puzzle_type()
        correct = self.get_correct_answer()

        # 如果是文字缺失补全，先校验填空
        if puzzle_type == "文字缺失补全":
            missing = self.get_missing_text()
            if missing:
                # 检查填空是否完整
                if len(self.missing_answers) < len(missing):
                    return False, "请先将残页上的文字空缺补全。"
                for i, ans in enumerate(self.missing_answers):
                    if ans.strip() != missing[i]:
                        return False, f"第{i+1}处文字补全有误，请结合病症与方名再作推敲。"

        # 检查是否选了药材
        if not self.selected_herbs:
            return False, "尚未选择任何药材，请先根据线索筛选药材。"

        # 核心校验：集合相同（不考虑顺序）
        selected_set = set(self.selected_herbs)
        correct_set = set(correct)

        if selected_set == correct_set:
            self.solved = True
            return True, "方剂配伍正确！古籍残页修复成功。"

        # 错误情况分析，给出提示
        extra = selected_set - correct_set  # 多选的药材
        missing = correct_set - selected_set  # 漏选的药材

        hint = "配伍有误："
        if missing:
            hint += f" 遗漏了 {', '.join(missing)}；"
        if extra:
            hint += f" 多选了 {', '.join(extra)}；"
        if not missing and not extra:
            hint += " 药材种类正确，但数量可能有重复，请检查君臣佐使配伍。"

        return False, hint

    def get_hint(self):
        """获取非直接答案的中医解析提示"""
        correct = self.get_correct_answer()
        clues = self.get_clues()
        # 根据当前错误给出通用中医提示
        hint_text = "【中医解析提示】\n"
        hint_text += self.puzzle.get("explanation", "")[:80] + "..."
        hint_text += "\n请重点回顾残页中关于君药、臣药、佐使药的描述，按君臣佐使顺序筛选药材。"
        return hint_text

    def set_solved(self):
        """标记为已完成（用于从存档恢复或展示答案）"""
        self.solved = True
        self.show_answer = True
        self.selected_herbs = list(self.get_correct_answer())

    def get_selected_count(self):
        """获取已选药材数量"""
        return len(self.selected_herbs)

    def is_all_clues_visible(self):
        """判断所有线索是否已展示完毕"""
        return self.visible_clue_index >= len(self.get_clues())

    def reveal_next_clue(self):
        """展示下一条线索"""
        if not self.is_all_clues_visible():
            self.visible_clue_index += 1

    def reveal_all_clues(self):
        """展示所有线索"""
        self.visible_clue_index = len(self.get_clues())

    def update(self, dt):
        """更新打字机效果计时"""
        self.char_timer += dt * self.text_speed

    def get_visible_clues(self):
        """获取当前应显示的线索列表"""
        clues = self.get_clues()
        return clues[:self.visible_clue_index]

    def get_remaining_options(self):
        """获取尚未被选中的候选药材"""
        options = self.get_options()
        return [opt for opt in options if opt not in self.selected_herbs]

    def get_explanation(self):
        """获取方剂解析"""
        return self.puzzle.get("explanation", "暂无解析")

    def get_story(self):
        """获取名医故事"""
        return self.puzzle.get("story", "暂无故事")
