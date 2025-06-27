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
        self.LOG_FORMAT = os.getenv('LOG_FORMAT', 'text')  # 'text' or 'json'
        self.CONSOLE_LOG_LEVEL = os.getenv('CONSOLE_LOG_LEVEL', 'INFO')
        
        # ログファイルローテーション設定
        self.LOG_FILE_MAX_BYTES = int(os.getenv('LOG_FILE_MAX_BYTES', str(10 * 1024 * 1024)))  # 10MB
        self.LOG_FILE_BACKUP_COUNT = int(os.getenv('LOG_FILE_BACKUP_COUNT', '5'))
        self.ERROR_LOG_MAX_BYTES = int(os.getenv('ERROR_LOG_MAX_BYTES', str(5 * 1024 * 1024)))  # 5MB
        self.ERROR_LOG_BACKUP_COUNT = int(os.getenv('ERROR_LOG_BACKUP_COUNT', '3'))
        
        # スケジューラ設定
        self.SCHEDULER_CHECK_INTERVAL = int(os.getenv('SCHEDULER_CHECK_INTERVAL', '30'))  # 秒
        self.SCHEDULER_LOOP_INTERVAL = int(os.getenv('SCHEDULER_LOOP_INTERVAL', '10'))   # 秒
        
        # デバッグ設定
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        self.ENABLE_PERFORMANCE_LOGGING = os.getenv('ENABLE_PERFORMANCE_LOGGING', 'False').lower() == 'true'
        self.ENABLE_STRUCTURED_LOGGING = os.getenv('ENABLE_STRUCTURED_LOGGING', 'True').lower() == 'true'
        
        # セキュリティ監査設定
        self.ENABLE_SECURITY_AUDIT = os.getenv('ENABLE_SECURITY_AUDIT', 'True').lower() == 'true'
        self.LOG_SENSITIVE_DATA = os.getenv('LOG_SENSITIVE_DATA', 'False').lower() == 'true'
        
        # 高度なロギング設定
        self.ENABLE_METRICS_LOGGING = os.getenv('ENABLE_METRICS_LOGGING', 'True').lower() == 'true'
        self.ENABLE_HEALTH_CHECK_LOGGING = os.getenv('ENABLE_HEALTH_CHECK_LOGGING', 'True').lower() == 'true'
        self.LOG_RETENTION_DAYS = int(os.getenv('LOG_RETENTION_DAYS', '30'))
        self.ENABLE_SLOW_QUERY_LOGGING = os.getenv('ENABLE_SLOW_QUERY_LOGGING', 'True').lower() == 'true'
        self.SLOW_QUERY_THRESHOLD = float(os.getenv('SLOW_QUERY_THRESHOLD', '1.0'))  # 秒
        
        # 異常検知設定
        self.ENABLE_ANOMALY_DETECTION = os.getenv('ENABLE_ANOMALY_DETECTION', 'True').lower() == 'true'
        self.ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', '0.1'))  # 10%
        self.ENABLE_ALERT_LOGGING = os.getenv('ENABLE_ALERT_LOGGING', 'True').lower() == 'true'
    
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
  Log Format: {self.LOG_FORMAT}
  Debug Mode: {self.DEBUG}
  Performance Logging: {self.ENABLE_PERFORMANCE_LOGGING}
  Structured Logging: {self.ENABLE_STRUCTURED_LOGGING}
  Security Audit: {self.ENABLE_SECURITY_AUDIT}
  Metrics Logging: {self.ENABLE_METRICS_LOGGING}
  Health Check Logging: {self.ENABLE_HEALTH_CHECK_LOGGING}
  Anomaly Detection: {self.ENABLE_ANOMALY_DETECTION}
  Alert Logging: {self.ENABLE_ALERT_LOGGING}
"""

# グローバル設定インスタンス
settings = Settings()