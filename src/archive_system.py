# archive_system.py
# 图鉴归档系统：管理已解锁方剂、原文、解析、名医故事的浏览

from src.config import SAVE_PATH


class ArchiveSystem:
    """图鉴归档系统"""

    def __init__(self, data_manager, save_manager):
        self.data_manager = data_manager
        self.save_manager = save_manager

    def get_unlocked_archives(self):
        """获取所有已解锁的方剂图鉴"""
        completed = self.save_manager.save_data.get("completed_puzzles", [])
        all_puzzles = self.data_manager.get_all_puzzles()
        archives = []
        for puzzle in all_puzzles:
            if puzzle.get("id") in completed:
                archives.append(puzzle)
        return archives

    def get_archives_by_chapter(self):
        """按章节分类返回已解锁图鉴"""
        completed = self.save_manager.save_data.get("completed_puzzles", [])
        chapters = self.data_manager.get_chapters()
        result = []
        for chapter in chapters:
            chapter_archives = []
            for puzzle in chapter.get("puzzles", []):
                if puzzle.get("id") in completed:
                    puzzle_info = {
                        "chapter_id": chapter.get("id"),
                        "chapter_name": chapter.get("name"),
                        **puzzle
                    }
                    chapter_archives.append(puzzle_info)
            result.append({
                "chapter": chapter,
                "archives": chapter_archives,
                "unlocked": chapter.get("id") in self.save_manager.save_data.get("unlocked_chapters", [])
            })
        return result

    def is_puzzle_unlocked(self, puzzle_id):
        """判断某方剂是否已解锁"""
        return puzzle_id in self.save_manager.save_data.get("completed_puzzles", [])

    def get_archive_detail(self, puzzle_id):
        """获取某个图鉴的详细信息"""
        all_puzzles = self.data_manager.get_all_puzzles()
        for puzzle in all_puzzles:
            if puzzle.get("id") == puzzle_id:
                return puzzle
        return None

    def get_collection_progress(self):
        """获取收藏进度"""
        total = self.data_manager.get_total_puzzle_count()
        unlocked = len(self.save_manager.save_data.get("completed_puzzles", []))
        return unlocked, total
