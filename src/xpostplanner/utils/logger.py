import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

class XPostLogger:
    """XPostPlannerのロギングシステム"""
    
    _instance: Optional['XPostLogger'] = None
    _initialized = False
    
    def __new__(cls) -> 'XPostLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.logger = logging.getLogger('xpostplanner')
        self.setup_logging()
        self._initialized = True
    
    def setup_logging(self):
        """ロギングシステムのセットアップ"""
        # ログレベルの設定（環境変数から）
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # ログディレクトリの作成
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # フォーマッターの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # コンソールハンドラ
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # ファイルハンドラ（ローテーション付き）
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'xpostplanner.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # エラー専用ファイルハンドラ
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'xpostplanner_error.log',
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # ハンドラをロガーに追加
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        
        # 重複ログ防止
        self.logger.propagate = False
    
    def get_logger(self) -> logging.Logger:
        """ロガーインスタンスを取得"""
        return self.logger
    
    def log_function_call(self, func_name: str, **kwargs):
        """関数呼び出しのログ"""
        args_str = ', '.join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.debug(f"Function call: {func_name}({args_str})")
    
    def log_api_call(self, api_name: str, endpoint: str, status_code: Optional[int] = None):
        """API呼び出しのログ"""
        if status_code:
            self.logger.info(f"API call: {api_name} {endpoint} - Status: {status_code}")
        else:
            self.logger.info(f"API call: {api_name} {endpoint}")
    
    def log_error_with_context(self, error: Exception, context: dict):
        """コンテキスト付きエラーログ"""
        context_str = ', '.join(f"{k}={v}" for k, v in context.items())
        self.logger.error(f"Error: {str(error)} | Context: {context_str}", exc_info=True)

# グローバルロガーインスタンス
_logger_instance = XPostLogger()

def get_logger() -> logging.Logger:
    """ロガーを取得するヘルパー関数"""
    return _logger_instance.get_logger()

def log_function_call(func_name: str, **kwargs):
    """関数呼び出しログのヘルパー関数"""
    _logger_instance.log_function_call(func_name, **kwargs)

def log_api_call(api_name: str, endpoint: str, status_code: Optional[int] = None):
    """API呼び出しログのヘルパー関数"""
    _logger_instance.log_api_call(api_name, endpoint, status_code)

def log_error_with_context(error: Exception, context: dict):
    """コンテキスト付きエラーログのヘルパー関数"""
    _logger_instance.log_error_with_context(error, context)