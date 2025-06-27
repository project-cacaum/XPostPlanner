import json
import logging
import logging.handlers
import os
import sys
import time
import traceback
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union

class JSONFormatter(logging.Formatter):
    """JSON形式のログフォーマッター"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))


class PerformanceTimer:
    """パフォーマンス測定用タイマー"""
    
    def __init__(self, name: str, logger: logging.Logger):
        self.name = name
        self.logger = logger
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.logger.info(f'Performance: {self.name} took {duration:.3f}s')


class LogMetrics:
    """ログメトリクス収集クラス"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.error_history = deque(maxlen=1000)  # 最新1000件のエラー履歴
        self.lock = threading.Lock()
    
    def record_error(self, error_type: str, timestamp: datetime = None):
        """エラーを記録"""
        timestamp = timestamp or datetime.now()
        with self.lock:
            self.error_counts[error_type] += 1
            self.error_history.append((error_type, timestamp))
    
    def get_error_rate(self, time_window: timedelta = timedelta(minutes=5)) -> float:
        """指定時間内のエラー率を計算"""
        cutoff_time = datetime.now() - time_window
        with self.lock:
            recent_errors = [e for e in self.error_history if e[1] > cutoff_time]
            return len(recent_errors) / 1000  # 最大1000件に対する割合
    
    def should_alert(self, threshold: float) -> bool:
        """アラートが必要かチェック"""
        return self.get_error_rate() > threshold


class XPostLogger:
    """XPostPlannerの強化されたロギングシステム"""
    
    _instance: Optional['XPostLogger'] = None
    _initialized = False
    
    def __init__(self):
        if self._initialized:
            return
        
        self.metrics = LogMetrics()
        super().__init__()
    
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
        
        # ログディレクトリの設定
        log_dir = Path(os.getenv('LOG_DIR', 'logs'))
        log_dir.mkdir(exist_ok=True)
        
        # JSON形式を使用するかどうか
        use_json_format = os.getenv('LOG_FORMAT', 'text').lower() == 'json'
        
        # フォーマッターの設定
        if use_json_format:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # コンソールハンドラ
        console_level = os.getenv('CONSOLE_LOG_LEVEL', 'INFO').upper()
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_level, logging.INFO))
        console_handler.setFormatter(formatter)
        
        # ファイルハンドラ（ローテーション付き）
        file_max_bytes = int(os.getenv('LOG_FILE_MAX_BYTES', str(10 * 1024 * 1024)))  # 10MB
        file_backup_count = int(os.getenv('LOG_FILE_BACKUP_COUNT', '5'))
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'xpostplanner.log',
            maxBytes=file_max_bytes,
            backupCount=file_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # エラー専用ファイルハンドラ
        error_max_bytes = int(os.getenv('ERROR_LOG_MAX_BYTES', str(5 * 1024 * 1024)))  # 5MB
        error_backup_count = int(os.getenv('ERROR_LOG_BACKUP_COUNT', '3'))
        
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'xpostplanner_error.log',
            maxBytes=error_max_bytes,
            backupCount=error_backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # パフォーマンスログ専用ハンドラ（オプション）
        if os.getenv('ENABLE_PERFORMANCE_LOGGING', 'False').lower() == 'true':
            perf_handler = logging.handlers.RotatingFileHandler(
                log_dir / 'xpostplanner_performance.log',
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=3,
                encoding='utf-8'
            )
            perf_handler.setLevel(logging.INFO)
            perf_handler.setFormatter(formatter)
            
            perf_filter = logging.Filter()
            perf_filter.filter = lambda record: 'Performance:' in record.getMessage()
            perf_handler.addFilter(perf_filter)
            
            self.logger.addHandler(perf_handler)
        
        # ハンドラをロガーに追加
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        
        # 重複ログ防止
        self.logger.propagate = False
        
        # セットアップ完了ログ
        self.logger.info('Logging system initialized', extra={'extra_data': {
            'log_level': log_level,
            'log_dir': str(log_dir),
            'json_format': use_json_format,
            'performance_logging': os.getenv('ENABLE_PERFORMANCE_LOGGING', 'False').lower() == 'true'
        }})
    
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
        if os.getenv('LOG_FORMAT', 'text').lower() == 'json':
            self.logger.error(f"Error: {str(error)}", exc_info=True, extra={'extra_data': {
                'error_type': type(error).__name__,
                'error_message': str(error),
                'context': context
            }})
        else:
            context_str = ', '.join(f"{k}={v}" for k, v in context.items())
            self.logger.error(f"Error: {str(error)} | Context: {context_str}", exc_info=True)
    
    def log_structured(self, level: str, message: str, **kwargs):
        """構造化ログの出力"""
        log_level = getattr(logging, level.upper(), logging.INFO)
        if os.getenv('LOG_FORMAT', 'text').lower() == 'json':
            self.logger.log(log_level, message, extra={'extra_data': kwargs})
        else:
            extra_str = ', '.join(f"{k}={v}" for k, v in kwargs.items())
            self.logger.log(log_level, f"{message} | {extra_str}" if kwargs else message)
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """セキュリティイベントのログ"""
        self.log_structured('WARNING', f'Security event: {event_type}', 
                          event_type=event_type, 
                          details=details,
                          timestamp=datetime.now().isoformat())
    
    def log_database_operation(self, operation: str, table: str, affected_rows: int = 0, **kwargs):
        """データベース操作のログ"""
        self.log_structured('INFO', f'Database operation: {operation}',
                          operation=operation,
                          table=table,
                          affected_rows=affected_rows,
                          **kwargs)
    
    def log_discord_event(self, event_type: str, channel_id: Optional[str] = None, **kwargs):
        """Discordイベントのログ"""
        self.log_structured('INFO', f'Discord event: {event_type}',
                          event_type=event_type,
                          channel_id=channel_id,
                          **kwargs)
    
    def performance_timer(self, name: str) -> PerformanceTimer:
        """パフォーマンス測定タイマーを取得"""
        return PerformanceTimer(name, self.logger)
    
    def log_system_status(self, component: str, status: str, **kwargs):
        """システムステータスのログ"""
        self.log_structured('INFO', f'System status: {component} is {status}',
                          component=component,
                          status=status,
                          **kwargs)
    
    def log_metrics(self, metric_name: str, value: Union[int, float], unit: str = '', **kwargs):
        """メトリクスのログ"""
        from .config.settings import settings
        if settings.ENABLE_METRICS_LOGGING:
            self.log_structured('INFO', f'Metrics: {metric_name}={value}{unit}',
                              metric_name=metric_name,
                              value=value,
                              unit=unit,
                              **kwargs)
    
    def log_health_check(self, component: str, healthy: bool, details: Dict[str, Any] = None):
        """ヘルスチェックのログ"""
        from .config.settings import settings
        if settings.ENABLE_HEALTH_CHECK_LOGGING:
            status = 'healthy' if healthy else 'unhealthy'
            self.log_structured('INFO' if healthy else 'WARNING', 
                              f'Health check: {component} is {status}',
                              component=component,
                              healthy=healthy,
                              details=details or {})
    
    def log_slow_operation(self, operation: str, duration: float, threshold: float = None, **kwargs):
        """低速な操作のログ"""
        from .config.settings import settings
        threshold = threshold or settings.SLOW_QUERY_THRESHOLD
        
        if duration > threshold and settings.ENABLE_SLOW_QUERY_LOGGING:
            self.log_structured('WARNING', f'Slow operation detected: {operation}',
                              operation=operation,
                              duration=duration,
                              threshold=threshold,
                              **kwargs)
    
    def log_alert(self, alert_type: str, severity: str, message: str, **kwargs):
        """アラートのログ"""
        from .config.settings import settings
        if settings.ENABLE_ALERT_LOGGING:
            log_level = 'CRITICAL' if severity == 'critical' else 'ERROR' if severity == 'high' else 'WARNING'
            self.log_structured(log_level, f'ALERT [{alert_type}]: {message}',
                              alert_type=alert_type,
                              severity=severity,
                              **kwargs)

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

def log_structured(level: str, message: str, **kwargs):
    """構造化ログのヘルパー関数"""
    _logger_instance.log_structured(level, message, **kwargs)

def log_security_event(event_type: str, details: Dict[str, Any]):
    """セキュリティイベントログのヘルパー関数"""
    _logger_instance.log_security_event(event_type, details)

def log_database_operation(operation: str, table: str, affected_rows: int = 0, **kwargs):
    """データベース操作ログのヘルパー関数"""
    _logger_instance.log_database_operation(operation, table, affected_rows, **kwargs)

def log_discord_event(event_type: str, channel_id: Optional[str] = None, **kwargs):
    """Discordイベントログのヘルパー関数"""
    _logger_instance.log_discord_event(event_type, channel_id, **kwargs)

def performance_timer(name: str) -> PerformanceTimer:
    """パフォーマンス測定タイマーのヘルパー関数"""
    return _logger_instance.performance_timer(name)

def log_system_status(component: str, status: str, **kwargs):
    """システムステータスログのヘルパー関数"""
    _logger_instance.log_system_status(component, status, **kwargs)

def log_metrics(metric_name: str, value: Union[int, float], unit: str = '', **kwargs):
    """メトリクスログのヘルパー関数"""
    _logger_instance.log_metrics(metric_name, value, unit, **kwargs)

def log_health_check(component: str, healthy: bool, details: Dict[str, Any] = None):
    """ヘルスチェックログのヘルパー関数"""
    _logger_instance.log_health_check(component, healthy, details)

def log_slow_operation(operation: str, duration: float, threshold: float = None, **kwargs):
    """低速操作ログのヘルパー関数"""
    _logger_instance.log_slow_operation(operation, duration, threshold, **kwargs)

def log_alert(alert_type: str, severity: str, message: str, **kwargs):
    """アラートログのヘルパー関数"""
    _logger_instance.log_alert(alert_type, severity, message, **kwargs)

def check_anomalies():
    """異常検知チェック"""
    from .config.settings import settings
    if settings.ENABLE_ANOMALY_DETECTION:
        if _logger_instance.metrics.should_alert(settings.ERROR_RATE_THRESHOLD):
            log_alert('high_error_rate', 'high', 
                     f'Error rate exceeded threshold: {_logger_instance.metrics.get_error_rate():.2%}',
                     threshold=settings.ERROR_RATE_THRESHOLD)