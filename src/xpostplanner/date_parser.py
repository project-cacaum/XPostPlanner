import re
from datetime import datetime, timedelta
from typing import Optional

def parse_datetime(time_str: str) -> Optional[datetime]:
    """
    様々な形式の日時文字列をパースして datetime オブジェクトを返す
    
    対応フォーマット:
    - 2025-01-15 14:30
    - 2025/01/15 14:30
    - 01-15 14:30 (今年)
    - 01/15 14:30 (今年)
    - 15日 14:30 (今月)
    - 14:30 (今日)
    - 30分後
    - 1時間後
    - 2時間30分後
    
    Args:
        time_str (str): 日時文字列
        
    Returns:
        Optional[datetime]: パース成功時はdatetimeオブジェクト、失敗時はNone
    """
    time_str = time_str.strip()
    now = datetime.now()
    
    # 相対時間のパターン
    relative_patterns = [
        (r'(\d+)分後', lambda m: now + timedelta(minutes=int(m.group(1)))),
        (r'(\d+)時間後', lambda m: now + timedelta(hours=int(m.group(1)))),
        (r'(\d+)時間(\d+)分後', lambda m: now + timedelta(hours=int(m.group(1)), minutes=int(m.group(2)))),
        (r'(\d+)日後', lambda m: now + timedelta(days=int(m.group(1)))),
    ]
    
    for pattern, func in relative_patterns:
        match = re.match(pattern, time_str)
        if match:
            return func(match)
    
    # 絶対時間のパターン
    absolute_patterns = [
        # YYYY-MM-DD HH:MM または YYYY/MM/DD HH:MM
        (r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2})', 
         lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 
                           int(m.group(4)), int(m.group(5)))),
        
        # MM-DD HH:MM または MM/DD HH:MM (今年)
        (r'(\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2})', 
         lambda m: datetime(now.year, int(m.group(1)), int(m.group(2)), 
                           int(m.group(3)), int(m.group(4)))),
        
        # DD日 HH:MM (今月)
        (r'(\d{1,2})日\s+(\d{1,2}):(\d{2})', 
         lambda m: datetime(now.year, now.month, int(m.group(1)), 
                           int(m.group(2)), int(m.group(3)))),
        
        # HH:MM (今日)
        (r'(\d{1,2}):(\d{2})', 
         lambda m: datetime(now.year, now.month, now.day, 
                           int(m.group(1)), int(m.group(2)))),
        
        # YYYY-MM-DDTHH:MM (ISO format)
        (r'(\d{4})-(\d{1,2})-(\d{1,2})T(\d{1,2}):(\d{2})', 
         lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 
                           int(m.group(4)), int(m.group(5)))),
    ]
    
    for pattern, func in absolute_patterns:
        match = re.match(pattern, time_str)
        if match:
            try:
                result = func(match)
                # 過去の時刻の場合は次の日/月/年に調整
                if result <= now:
                    if ':' in pattern:  # 時刻のみの場合は翌日
                        result = result + timedelta(days=1)
                    elif '日' in pattern:  # 日付のみの場合は翌月
                        if result.month == 12:
                            result = result.replace(year=result.year + 1, month=1)
                        else:
                            result = result.replace(month=result.month + 1)
                return result
            except ValueError:
                continue
    
    return None

def get_supported_formats() -> str:
    """
    サポートされている日時フォーマットの例を返す
    
    Returns:
        str: フォーマット例の文字列
    """
    return """
サポートされている日時フォーマット:

📅 **絶対時刻指定:**
• `2025-01-15 14:30` (年月日 時分)
• `2025/01/15 14:30` (年/月/日 時分)  
• `01-15 14:30` (月日 時分 - 今年)
• `01/15 14:30` (月/日 時分 - 今年)
• `15日 14:30` (日 時分 - 今月)
• `14:30` (時分 - 今日、過去の場合は翌日)

⏰ **相対時刻指定:**
• `30分後`
• `1時間後`
• `2時間30分後`
• `3日後`
"""