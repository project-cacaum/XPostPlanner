import asyncio
import schedule
import time
import os
import discord
from datetime import datetime
from typing import TYPE_CHECKING
from ..models.database import Database
from .twitter_client import TwitterClient
from ..utils.logger import get_logger, log_error_with_context, log_structured, performance_timer, log_system_status, log_metrics, log_health_check, log_slow_operation, check_anomalies

if TYPE_CHECKING:
    from .bot import XPostBot

class PostScheduler:
    def __init__(self, bot: 'XPostBot'):
        self.bot = bot
        self.db = Database()
        self.twitter_client = TwitterClient()
        self.is_running = False
        self.logger = get_logger()
        
        log_structured('info', 'PostScheduler initialized',
                      component='scheduler',
                      operation='initialization')
    
    async def start(self):
        """スケジューラを開始"""
        self.is_running = True
        
        log_system_status('scheduler', 'starting',
                         check_interval=30,
                         loop_interval=10)
        
        # 30秒ごとに投稿チェックを実行（秒単位対応のため）
        schedule.every(30).seconds.do(self._check_and_post)
        
        log_system_status('scheduler', 'running')
        
        # バックグラウンドでスケジューラを実行
        loop_count = 0
        while self.is_running:
            with performance_timer('scheduler_loop'):
                schedule.run_pending()
                
                # 定期的にヘルスチェックと異常検知を実行
                loop_count += 1
                if loop_count % 30 == 0:  # 5分ごと（30回のループ）
                    self._perform_health_check()
                    check_anomalies()
                    log_metrics('scheduler_loops', loop_count, 'count')
                    
            await asyncio.sleep(10)  # 10秒間隔でチェック
    
    def stop(self):
        """スケジューラを停止"""
        log_system_status('scheduler', 'stopping')
        self.is_running = False
        log_system_status('scheduler', 'stopped')
    
    def _check_and_post(self):
        """投稿時間が来た投稿をチェックして投稿"""
        with performance_timer('check_and_post_operation'):
            try:
                with performance_timer('pending_posts_query'):
                    pending_posts = self.db.get_pending_posts()
                
                log_structured('debug', 'Checking pending posts',
                              component='scheduler',
                              operation='check_pending',
                              post_count=len(pending_posts))
            
                for post in pending_posts:
                    with performance_timer(f'process_post_{post["id"]}'):
                        log_structured('info', 'Processing scheduled post',
                                      post_id=post['id'],
                                      scheduled_time=post['scheduled_time'],
                                      has_images=post['has_images'])
                        
                        # 画像があるかチェック
                        image_paths = []
                        if post['has_images']:
                            with performance_timer('load_post_images'):
                                images = self.db.get_post_images(post['id'])
                                image_paths = [img['file_path'] for img in images]
                            
                            log_structured('debug', 'Post images loaded',
                                          post_id=post['id'],
                                          image_count=len(image_paths))
                        
                        # 投稿を実行
                        with performance_timer('twitter_post_execution'):
                            tweet_id = self.twitter_client.post_tweet(
                                post['content'], 
                                image_paths if image_paths else None
                            )
                
                        if tweet_id:
                            # 投稿成功
                            with performance_timer('mark_post_as_posted'):
                                self.db.mark_post_as_posted(post['id'])
                            
                            log_structured('info', 'Post published successfully',
                                          post_id=post['id'],
                                          tweet_id=tweet_id,
                                          has_images=post['has_images'])
                            
                            # 画像ファイルをクリーンアップ
                            if image_paths:
                                with performance_timer('image_cleanup'):
                                    from .image_manager import ImageManager
                                    image_manager = ImageManager()
                                    image_manager.cleanup_images(image_paths)
                            
                            # ログチャンネルに通知
                            asyncio.create_task(self._log_success(post, tweet_id))
                        else:
                            # 投稿失敗
                            log_structured('error', 'Post publication failed',
                                          post_id=post['id'],
                                          scheduled_time=post['scheduled_time'])
                            # メトリクスにエラーを記録
                            from ..utils.logger import _logger_instance
                            _logger_instance.metrics.record_error('post_publication_failed')
                            asyncio.create_task(self._log_failure(post))
                    
            except Exception as e:
                log_error_with_context(e, {
                    'component': 'scheduler',
                    'operation': 'check_and_post',
                    'severity': 'high'
                })
                asyncio.create_task(self._log_error(str(e)))
    
    async def _log_success(self, post: dict, tweet_id: str):
        """投稿成功をログに記録"""
        log_channel_id = os.getenv('DISCORD_LOG_CHANNEL_ID')
        if not log_channel_id:
            return
        
        try:
            with performance_timer('discord_success_notification'):
                channel = self.bot.get_channel(int(log_channel_id))
                if channel:
                    embed = discord.Embed(
                        title="✅ 投稿成功",
                        description=f"**投稿内容:**\n{post['content']}\n\n**Tweet ID:** {tweet_id}",
                        color=0x00FF00,
                        timestamp=datetime.now()
                    )
                    await channel.send(embed=embed)
                    
                    log_structured('info', 'Success notification sent',
                                  post_id=post['id'],
                                  tweet_id=tweet_id,
                                  channel_id=log_channel_id)
        except Exception as e:
            log_error_with_context(e, {
                'operation': 'discord_success_notification',
                'post_id': post['id'],
                'tweet_id': tweet_id
            })
    
    async def _log_failure(self, post: dict):
        """投稿失敗をログに記録"""
        log_channel_id = os.getenv('DISCORD_LOG_CHANNEL_ID')
        if not log_channel_id:
            return
        
        try:
            with performance_timer('discord_failure_notification'):
                channel = self.bot.get_channel(int(log_channel_id))
                if channel:
                    embed = discord.Embed(
                        title="❌ 投稿失敗",
                        description=f"**投稿内容:**\n{post['content']}\n\n**予定時刻:** {post['scheduled_time']}",
                        color=0xFF0000,
                        timestamp=datetime.now()
                    )
                    await channel.send(embed=embed)
                    
                    log_structured('warning', 'Failure notification sent',
                                  post_id=post['id'],
                                  scheduled_time=post['scheduled_time'],
                                  channel_id=log_channel_id)
        except Exception as e:
            log_error_with_context(e, {
                'operation': 'discord_failure_notification',
                'post_id': post['id']
            })
    
    async def _log_error(self, error_message: str):
        """エラーをログに記録"""
        log_channel_id = os.getenv('DISCORD_LOG_CHANNEL_ID')
        if not log_channel_id:
            return
        
        try:
            with performance_timer('discord_error_notification'):
                channel = self.bot.get_channel(int(log_channel_id))
                if channel:
                    embed = discord.Embed(
                        title="⚠️ スケジューラエラー",
                        description=f"**エラー内容:**\n{error_message}",
                        color=0xFFFF00,
                        timestamp=datetime.now()
                    )
                    await channel.send(embed=embed)
                    
                    log_structured('error', 'Error notification sent',
                                  error_message=error_message,
                                  channel_id=log_channel_id)
        except Exception as e:
            log_error_with_context(e, {
                'operation': 'discord_error_notification',
                'original_error': error_message
            })
    
    def _perform_health_check(self):
        """スケジューラーのヘルスチェック"""
        try:
            # データベース接続をチェック
            pending_count = len(self.db.get_pending_posts())
            log_health_check('database', True, {'pending_posts_count': pending_count})
            
            # Twitter API接続をチェック
            twitter_healthy = self.twitter_client.check_health()
            log_health_check('twitter_api', twitter_healthy)
            
            # メトリクスを記録
            log_metrics('pending_posts', pending_count, 'count')
            log_metrics('scheduler_health_check', 1, 'count')
            
        except Exception as e:
            log_health_check('scheduler', False, {'error': str(e)})
            log_error_with_context(e, {
                'operation': 'health_check',
                'component': 'scheduler'
            })