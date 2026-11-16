# data_manager.py
# 负责读取和管理游戏数据（JSON）

import json
import os
from src.config import GAME_DATA_PATH


class DataManager:
    """游戏数据管理器，负责加载题库、剧情、配置等JSON数据"""

    def __init__(self):
        self.data = {}
        self.settings = {}
        self.chapters = []
        self.load_data()

    def load_data(self):
        """从JSON文件加载游戏数据"""
        if not os.path.exists(GAME_DATA_PATH):
            raise FileNotFoundError(f"找不到游戏数据文件：{GAME_DATA_PATH}")

        with open(GAME_DATA_PATH, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.settings = self.data.get("settings", {})
        self.chapters = self.data.get("chapters", [])

    def get_chapters(self):
        """获取所有章节信息"""
        return self.chapters

    def get_chapter_by_id(self, chapter_id):
        """根据章节ID获取章节详情"""
        for chapter in self.chapters:
            if chapter.get("id") == chapter_id:
                return chapter
        return None

    def get_puzzle(self, chapter_id, puzzle_id):
        """根据章节ID和谜题ID获取谜题"""
        chapter = self.get_chapter_by_id(chapter_id)
        if not chapter:
            return None
        for puzzle in chapter.get("puzzles", []):
            if puzzle.get("id") == puzzle_id:
                return puzzle
        return None

    def get_settings(self):
        """获取游戏默认设置"""
        return self.settings

    def get_all_puzzles(self):
        """获取所有谜题，用于图鉴展示"""
        all_puzzles = []
        for chapter in self.chapters:
            for puzzle in chapter.get("puzzles", []):
                puzzle_info = {
                    "chapter_id": chapter.get("id"),
                    "chapter_name": chapter.get("name"),
                    "chapter_title": chapter.get("title"),
                    **puzzle
                }
                all_puzzles.append(puzzle_info)
        return all_puzzles

    def get_total_puzzle_count(self):
        """获取谜题总数"""
        return len(self.get_all_puzzles())
