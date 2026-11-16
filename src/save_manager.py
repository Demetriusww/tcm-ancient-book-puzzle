# save_manager.py
# 负责游戏进度的本地存档读取与写入

import json
import os
import sys
from src.config import SAVE_PATH, SAVE_DIR


WEB_SAVE_KEY = "guji_puzzle_save_v1"


def _is_web_runtime():
    """判断当前是否运行在 Pygbag 提供的浏览器环境中。"""
    return sys.platform in ("emscripten", "wasi")


class SaveManager:
    """存档管理器，保存章节解锁、谜题完成、正确率、错题等进度"""

    def __init__(self):
        # 确保存档目录存在
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)
        self.save_data = self.load_save()

    def get_default_save(self):
        """返回默认存档结构"""
        return {
            "unlocked_chapters": ["jiebiao"],   # 默认解锁第一章
            "completed_puzzles": [],            # 已完成谜题ID列表
            "wrong_records": [],                # 错误记录
            "total_attempts": 0,                # 总尝试次数
            "correct_attempts": 0,              # 正确次数
            "text_speed": 30,                   # 文字速度
            "music_on": True,                   # 音乐开关
            "music_volume": 0.5,                # 音乐音量
            "first_run": True,                  # 是否首次运行
            "player_name": ""                   # 玩家角色名
        }

    def _get_browser_storage(self):
        """返回浏览器 localStorage，桌面端或初始化失败时返回 None。"""
        if not _is_web_runtime():
            return None
        try:
            import platform

            return platform.window.localStorage
        except Exception as exc:
            print(f"浏览器本地存储不可用：{exc}")
            return None

    def _load_browser_save(self):
        """从浏览器 localStorage 读取存档。"""
        storage = self._get_browser_storage()
        if storage is None:
            return None
        try:
            raw = storage.getItem(WEB_SAVE_KEY)
            if raw is None:
                return None
            raw = str(raw)
            if not raw or raw == "null":
                return None
            return json.loads(raw)
        except Exception as exc:
            print(f"读取浏览器存档失败，使用文件存档：{exc}")
            return None

    def _save_browser_save(self):
        """将存档同步到浏览器 localStorage。"""
        storage = self._get_browser_storage()
        if storage is None:
            return False
        try:
            raw = json.dumps(self.save_data, ensure_ascii=False, separators=(",", ":"))
            storage.setItem(WEB_SAVE_KEY, raw)
            return True
        except Exception as exc:
            print(f"写入浏览器存档失败：{exc}")
            return False

    def load_save(self):
        """读取本地存档，若不存在则创建默认存档"""
        browser_data = self._load_browser_save()
        if isinstance(browser_data, dict):
            default = self.get_default_save()
            for key, value in default.items():
                if key not in browser_data:
                    browser_data[key] = value
            return browser_data

        if os.path.exists(SAVE_PATH):
            try:
                with open(SAVE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 补充可能缺失的字段
                default = self.get_default_save()
                for key, value in default.items():
                    if key not in data:
                        data[key] = value
                return data
            except Exception as e:
                print(f"读取存档失败，使用默认存档：{e}")
                return self.get_default_save()
        else:
            return self.get_default_save()

    def save_to_file(self):
        """将当前进度写入本地文件"""
        saved = False
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.save_data, f, ensure_ascii=False, indent=2)
            saved = True
        except Exception as e:
            print(f"保存失败：{e}")

        # 浏览器虚拟文件系统可能在刷新后重置，localStorage 是网页端的主存档。
        if self._save_browser_save():
            saved = True
        return saved

    def is_chapter_unlocked(self, chapter_id):
        """判断章节是否已解锁"""
        return chapter_id in self.save_data.get("unlocked_chapters", [])

    def unlock_chapter(self, chapter_id):
        """解锁指定章节"""
        if chapter_id not in self.save_data["unlocked_chapters"]:
            self.save_data["unlocked_chapters"].append(chapter_id)
            self.save_to_file()

    def is_puzzle_completed(self, puzzle_id):
        """判断谜题是否已完成"""
        return puzzle_id in self.save_data.get("completed_puzzles", [])

    def complete_puzzle(self, puzzle_id):
        """标记谜题为已完成"""
        if puzzle_id not in self.save_data["completed_puzzles"]:
            self.save_data["completed_puzzles"].append(puzzle_id)
            self.save_to_file()

    def add_wrong_record(self, puzzle_id, selected_herbs, hint):
        """记录一次错误选择"""
        record = {
            "puzzle_id": puzzle_id,
            "selected": selected_herbs,
            "hint": hint
        }
        # 避免重复记录同一谜题连续错误
        self.save_data["wrong_records"].append(record)
        self.save_to_file()

    def clear_wrong_records(self, puzzle_id=None):
        """清空错误记录，可指定谜题ID"""
        if puzzle_id is None:
            self.save_data["wrong_records"] = []
        else:
            self.save_data["wrong_records"] = [
                r for r in self.save_data["wrong_records"]
                if r.get("puzzle_id") != puzzle_id
            ]
        self.save_to_file()

    def get_wrong_records(self):
        """获取所有错误记录"""
        return self.save_data.get("wrong_records", [])

    def add_attempt(self, correct):
        """记录一次尝试，correct为True表示答对"""
        self.save_data["total_attempts"] += 1
        if correct:
            self.save_data["correct_attempts"] += 1
        self.save_to_file()

    def get_accuracy(self):
        """计算正确率"""
        total = self.save_data.get("total_attempts", 0)
        correct = self.save_data.get("correct_attempts", 0)
        if total == 0:
            return 0.0
        return round(correct / total * 100, 1)

    def get_progress(self):
        """获取整体进度信息"""
        return {
            "unlocked_chapters": len(self.save_data.get("unlocked_chapters", [])),
            "completed_puzzles": len(self.save_data.get("completed_puzzles", [])),
            "total_attempts": self.save_data.get("total_attempts", 0),
            "correct_attempts": self.save_data.get("correct_attempts", 0),
            "accuracy": self.get_accuracy(),
            "wrong_records": len(self.save_data.get("wrong_records", []))
        }

    def reset_save(self):
        """重置游戏进度"""
        self.save_data = self.get_default_save()
        self.save_to_file()

    def get_setting(self, key, default=None):
        """获取设置项"""
        return self.save_data.get(key, default)

    def set_setting(self, key, value):
        """设置并保存设置项"""
        self.save_data[key] = value
        self.save_to_file()

    def get_player_name(self):
        """获取玩家角色名"""
        return self.save_data.get("player_name", "")

    def set_player_name(self, name):
        """设置玩家角色名"""
        self.save_data["player_name"] = name.strip()
        self.save_to_file()

    def is_first_run(self):
        """判断是否为首次运行"""
        return self.save_data.get("first_run", True)

    def set_first_run_done(self):
        """标记首次运行已完成"""
        self.save_data["first_run"] = False
        self.save_to_file()
