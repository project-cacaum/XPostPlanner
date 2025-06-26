import os
from typing import Optional
from pathlib import Path

class Settings:
    """アプリケーション設定管理"""
    
    def __init__(self):
        # Discord設定
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
        self.DISCORD_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')
        self.DISCORD_LOG_CHANNEL_ID = os.getenv('DISCORD_LOG_CHANNEL_ID')
        
        # X (Twitter) API設定
        self.TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
        self.TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
        self.TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
        self.TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        # データベース設定
        self.DATABASE_PATH = os.getenv('DATABASE_PATH', 'xpost_scheduler.db')
        
        # 画像ストレージ設定
        self.IMAGE_STORAGE_DIR = os.getenv('IMAGE_STORAGE_DIR', 'images')
        
        # ログ設定
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_DIR = os.getenv('LOG_DIR', 'logs')
        
        # スケジューラ設定
        self.SCHEDULER_CHECK_INTERVAL = int(os.getenv('SCHEDULER_CHECK_INTERVAL', '30'))  # 秒
        self.SCHEDULER_LOOP_INTERVAL = int(os.getenv('SCHEDULER_LOOP_INTERVAL', '10'))   # 秒
        
        # デバッグ設定
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        self.ENABLE_PERFORMANCE_LOGGING = os.getenv('ENABLE_PERFORMANCE_LOGGING', 'False').lower() == 'true'
    
    def validate(self) -> list[str]:
        """設定の検証を行い、不足している項目をリストで返す"""
        missing = []
        
        if not self.DISCORD_TOKEN:
            missing.append('DISCORD_TOKEN')
        
        if not self.TWITTER_API_KEY:
            missing.append('TWITTER_API_KEY')
        
        if not self.TWITTER_API_SECRET:
            missing.append('TWITTER_API_SECRET')
        
        if not self.TWITTER_ACCESS_TOKEN:
            missing.append('TWITTER_ACCESS_TOKEN')
        
        if not self.TWITTER_ACCESS_TOKEN_SECRET:
            missing.append('TWITTER_ACCESS_TOKEN_SECRET')
        
        return missing
    
    def create_directories(self):
        """必要なディレクトリを作成"""
        Path(self.IMAGE_STORAGE_DIR).mkdir(exist_ok=True)
        Path(self.LOG_DIR).mkdir(exist_ok=True)
    
    def __str__(self) -> str:
        """設定情報の文字列表現（機密情報は隠す）"""
        return f"""
XPostPlanner Settings:
  Discord Token: {'*' * 10 if self.DISCORD_TOKEN else 'Not set'}
  Discord Channel ID: {self.DISCORD_CHANNEL_ID or 'Not set'}
  Discord Log Channel ID: {self.DISCORD_LOG_CHANNEL_ID or 'Not set'}
  Twitter API Key: {'*' * 10 if self.TWITTER_API_KEY else 'Not set'}
  Database Path: {self.DATABASE_PATH}
  Image Storage: {self.IMAGE_STORAGE_DIR}
  Log Level: {self.LOG_LEVEL}
  Debug Mode: {self.DEBUG}
"""

# グローバル設定インスタンス
settings = Settings()