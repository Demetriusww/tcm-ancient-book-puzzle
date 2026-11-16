# review_system.py
# 错题/误判复盘系统：记录、展示、提示和重新尝试

from src.data_manager import DataManager


class ReviewSystem:
    """错题复盘系统"""

    def __init__(self, save_manager, data_manager):
        self.save_manager = save_manager
        self.data_manager = data_manager

    def get_wrong_records(self):
        """获取所有错误记录，并附加谜题信息"""
        records = self.save_manager.get_wrong_records()
        enriched = []
        for record in records:
            puzzle = self.data_manager.get_puzzle_by_id_only(record.get("puzzle_id"))
            if puzzle:
                enriched.append({
                    "record": record,
                    "puzzle": puzzle
                })
        return enriched

    def get_wrong_puzzle_ids(self):
        """获取有错误记录的谜题ID集合"""
        records = self.save_manager.get_wrong_records()
        ids = []
        for record in records:
            pid = record.get("puzzle_id")
            if pid and pid not in ids:
                ids.append(pid)
        return ids

    def get_hint_for_puzzle(self, puzzle_id):
        """获取某谜题的复盘提示（非直接答案）"""
        puzzle = self.data_manager.get_puzzle_by_id_only(puzzle_id)
        if not puzzle:
            return "未找到该谜题。"
        hint = "【复盘提示】\n"
        hint += puzzle.get("explanation", "") + "\n"
        hint += "\n重点线索：\n"
        for clue in puzzle.get("clues", [])[:3]:
            hint += "• " + clue + "\n"
        hint += "\n请重新审视君药、臣药、佐使药的配伍关系，再作尝试。"
        return hint

    def clear_record(self, puzzle_id):
        """清空指定谜题的错误记录"""
        self.save_manager.clear_wrong_records(puzzle_id)

    def clear_all_records(self):
        """清空所有错误记录"""
        self.save_manager.clear_wrong_records()


# 为DataManager补充按ID查找谜题的方法

def get_puzzle_by_id_only(self, puzzle_id):
    """仅根据谜题ID在所有章节中查找"""
    for chapter in self.chapters:
        for puzzle in chapter.get("puzzles", []):
            if puzzle.get("id") == puzzle_id:
                return puzzle
    return None


# 动态绑定方法到DataManager类
DataManager.get_puzzle_by_id_only = get_puzzle_by_id_only
