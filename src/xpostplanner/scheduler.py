import asyncio
import schedule
import time
import os
import discord
from datetime import datetime
from typing import TYPE_CHECKING
from .database import Database
from .twitter_client import TwitterClient

if TYPE_CHECKING:
    from .bot import XPostBot

class PostScheduler:
    def __init__(self, bot: 'XPostBot'):
        self.bot = bot
        self.db = Database()
        self.twitter_client = TwitterClient()
        self.is_running = False
    
    async def start(self):
        """スケジューラを開始"""
        self.is_running = True
        
        # 30秒ごとに投稿チェックを実行（秒単位対応のため）
        schedule.every(30).seconds.do(self._check_and_post)
        
        # バックグラウンドでスケジューラを実行
        while self.is_running:
            schedule.run_pending()
            await asyncio.sleep(10)  # 10秒間隔でチェック
    
    def stop(self):
        """スケジューラを停止"""
        self.is_running = False
    
    def _check_and_post(self):
        """投稿時間が来た投稿をチェックして投稿"""
        try:
            pending_posts = self.db.get_pending_posts()
            
            for post in pending_posts:
                # 画像があるかチェック
                image_paths = []
                if post['has_images']:
                    images = self.db.get_post_images(post['id'])
                    image_paths = [img['file_path'] for img in images]
                
                # 投稿を実行
                tweet_id = self.twitter_client.post_tweet(
                    post['content'], 
                    image_paths if image_paths else None
                )
                
                if tweet_id:
                    # 投稿成功
                    self.db.mark_post_as_posted(post['id'])
                    
                    # 画像ファイルをクリーンアップ
                    if image_paths:
                        from .image_manager import ImageManager
                        image_manager = ImageManager()
                        image_manager.cleanup_images(image_paths)
                    
                    # ログチャンネルに通知
                    asyncio.create_task(self._log_success(post, tweet_id))
                else:
                    # 投稿失敗
                    asyncio.create_task(self._log_failure(post))
                    
        except Exception as e:
            print(f"Error in scheduler: {e}")
            asyncio.create_task(self._log_error(str(e)))
    
    async def _log_success(self, post: dict, tweet_id: str):
        """投稿成功をログに記録"""
        log_channel_id = os.getenv('DISCORD_LOG_CHANNEL_ID')
        if not log_channel_id:
            return
        
        try:
            channel = self.bot.get_channel(int(log_channel_id))
            if channel:
                embed = discord.Embed(
                    title="✅ 投稿成功",
                    description=f"**投稿内容:**\n{post['content']}\n\n**Tweet ID:** {tweet_id}",
                    color=0x00FF00,
                    timestamp=datetime.now()
                )
                await channel.send(embed=embed)
        except Exception as e:
            print(f"Failed to log success: {e}")
    
    async def _log_failure(self, post: dict):
        """投稿失敗をログに記録"""
        log_channel_id = os.getenv('DISCORD_LOG_CHANNEL_ID')
        if not log_channel_id:
            return
        
        try:
            channel = self.bot.get_channel(int(log_channel_id))
            if channel:
                embed = discord.Embed(
                    title="❌ 投稿失敗",
                    description=f"**投稿内容:**\n{post['content']}\n\n**予定時刻:** {post['scheduled_time']}",
                    color=0xFF0000,
                    timestamp=datetime.now()
                )
                await channel.send(embed=embed)
        except Exception as e:
            print(f"Failed to log failure: {e}")
    
    async def _log_error(self, error_message: str):
        """エラーをログに記録"""
        log_channel_id = os.getenv('DISCORD_LOG_CHANNEL_ID')
        if not log_channel_id:
            return
        
        try:
            channel = self.bot.get_channel(int(log_channel_id))
            if channel:
                embed = discord.Embed(
                    title="⚠️ スケジューラエラー",
                    description=f"**エラー内容:**\n{error_message}",
                    color=0xFFFF00,
                    timestamp=datetime.now()
                )
                await channel.send(embed=embed)
        except Exception as e:
            print(f"Failed to log error: {e}")