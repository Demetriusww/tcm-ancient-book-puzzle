# settings_manager.py
# 游戏设置管理：文字速度、音乐开关与音量

from src.config import DEFAULT_TEXT_SPEED, DEFAULT_MUSIC_ON, DEFAULT_MUSIC_VOLUME


class SettingsManager:
    """设置管理器"""

    def __init__(self, save_manager):
        self.save_manager = save_manager
        self.text_speed = save_manager.get_setting("text_speed", DEFAULT_TEXT_SPEED)
        self.music_on = save_manager.get_setting("music_on", DEFAULT_MUSIC_ON)
        self.music_volume = save_manager.get_setting("music_volume", DEFAULT_MUSIC_VOLUME)

    def get_text_speed(self):
        """获取文字速度"""
        return self.text_speed

    def set_text_speed(self, speed):
        """设置文字速度并保存"""
        self.text_speed = max(10, min(100, speed))
        self.save_manager.set_setting("text_speed", self.text_speed)

    def is_music_on(self):
        """获取音乐开关状态"""
        return self.music_on

    def set_music_on(self, on):
        """设置音乐开关"""
        self.music_on = bool(on)
        self.save_manager.set_setting("music_on", self.music_on)

    def get_music_volume(self):
        """获取音乐音量"""
        return self.music_volume

    def set_music_volume(self, volume):
        """设置音乐音量"""
        self.music_volume = max(0.0, min(1.0, volume))
        self.save_manager.set_setting("music_volume", self.music_volume)

    def reset_to_default(self):
        """恢复默认设置"""
        self.text_speed = DEFAULT_TEXT_SPEED
        self.music_on = DEFAULT_MUSIC_ON
        self.music_volume = DEFAULT_MUSIC_VOLUME
        self.save_manager.set_setting("text_speed", self.text_speed)
        self.save_manager.set_setting("music_on", self.music_on)
        self.save_manager.set_setting("music_volume", self.music_volume)
