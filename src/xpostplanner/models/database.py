import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

class Database:
    def __init__(self, db_path: str = "xpost_scheduler.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベースとテーブルを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 投稿予約テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    scheduled_time DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    posted_at DATETIME NULL,
                    is_posted BOOLEAN DEFAULT FALSE,
                    discord_message_id TEXT,
                    guild_id TEXT,
                    channel_id TEXT
                )
            ''')
            
            # 画像情報テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS post_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES scheduled_posts (id)
                )
            ''')
            
            # 承認記録テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS post_approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    user_id TEXT NOT NULL,
                    approval_type TEXT NOT NULL CHECK (approval_type IN ('good', 'bad')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES scheduled_posts (id),
                    UNIQUE(post_id, user_id)
                )
            ''')
            
            # マイグレーションを実行
            self._run_migrations(cursor)
            
            conn.commit()
    
    def _run_migrations(self, cursor):
        """データベースマイグレーションを実行"""
        # has_imagesカラムが存在するかチェック
        cursor.execute("PRAGMA table_info(scheduled_posts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'has_images' not in columns:
            cursor.execute('ALTER TABLE scheduled_posts ADD COLUMN has_images BOOLEAN DEFAULT FALSE')
            print("Added has_images column to scheduled_posts table")
    
    def add_scheduled_post(self, content: str, scheduled_time: datetime, 
                          discord_message_id: str, guild_id: str, channel_id: str,
                          has_images: bool = False) -> int:
        """投稿予約を追加"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scheduled_posts 
                (content, scheduled_time, discord_message_id, guild_id, channel_id, has_images)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (content, scheduled_time, discord_message_id, guild_id, channel_id, has_images))
            conn.commit()
            return cursor.lastrowid
    
    def get_pending_posts(self) -> List[Dict[str, Any]]:
        """投稿予定の投稿を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, content, scheduled_time, discord_message_id, guild_id, channel_id, has_images
                FROM scheduled_posts
                WHERE is_posted = FALSE AND scheduled_time <= ?
            ''', (datetime.now(),))
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'content': row[1],
                    'scheduled_time': row[2],
                    'discord_message_id': row[3],
                    'guild_id': row[4],
                    'channel_id': row[5],
                    'has_images': row[6]
                }
                for row in rows
            ]
    
    def mark_post_as_posted(self, post_id: int):
        """投稿済みとしてマーク"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE scheduled_posts
                SET is_posted = TRUE, posted_at = ?
                WHERE id = ?
            ''', (datetime.now(), post_id))
            conn.commit()
    
    def add_approval(self, post_id: int, user_id: str, approval_type: str):
        """承認記録を追加/更新"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO post_approvals (post_id, user_id, approval_type)
                VALUES (?, ?, ?)
            ''', (post_id, user_id, approval_type))
            conn.commit()
    
    def remove_approval(self, post_id: int, user_id: str):
        """承認記録を削除"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM post_approvals
                WHERE post_id = ? AND user_id = ?
            ''', (post_id, user_id))
            conn.commit()
    
    def get_approval_counts(self, post_id: int) -> Dict[str, int]:
        """承認数を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT approval_type, COUNT(*) as count
                FROM post_approvals
                WHERE post_id = ?
                GROUP BY approval_type
            ''', (post_id,))
            
            results = cursor.fetchall()
            counts = {'good': 0, 'bad': 0}
            for approval_type, count in results:
                counts[approval_type] = count
            
            return counts
    
    def get_post_by_message_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Discord メッセージIDから投稿を取得"""
        with performance_timer('get_post_by_message_id'):
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, content, scheduled_time, is_posted
                    FROM scheduled_posts
                    WHERE discord_message_id = ?
                ''', (message_id,))
                
                row = cursor.fetchone()
                
                log_database_operation('select', 'scheduled_posts', 1 if row else 0,
                                      message_id=message_id,
                                      operation='get_post_by_message_id',
                                      found=bool(row))
                
                if row:
                    return {
                        'id': row[0],
                        'content': row[1],
                        'scheduled_time': row[2],
                        'is_posted': row[3]
                    }
                return None
    
    def add_post_image(self, post_id: int, file_path: str, original_filename: str, file_size: int) -> int:
        """投稿に画像を追加"""
        with performance_timer('add_post_image'):
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO post_images (post_id, file_path, original_filename, file_size)
                    VALUES (?, ?, ?, ?)
                ''', (post_id, file_path, original_filename, file_size))
                conn.commit()
                image_id = cursor.lastrowid
                
                log_database_operation('insert', 'post_images', 1,
                                      post_id=post_id,
                                      image_id=image_id,
                                      file_path=file_path,
                                      original_filename=original_filename,
                                      file_size=file_size)
                
                return image_id
    
    def get_post_images(self, post_id: int) -> List[Dict[str, Any]]:
        """投稿の画像一覧を取得"""
        with performance_timer('get_post_images'):
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, file_path, original_filename, file_size
                    FROM post_images
                    WHERE post_id = ?
                    ORDER BY id
                ''', (post_id,))
                
                rows = cursor.fetchall()
                
                log_database_operation('select', 'post_images', len(rows),
                                      post_id=post_id,
                                      operation='get_post_images')
                
                return [
                    {
                        'id': row[0],
                        'file_path': row[1],
                        'original_filename': row[2],
                        'file_size': row[3]
                    }
                    for row in rows
                ]