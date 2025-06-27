import tweepy
import os
from datetime import datetime
from typing import Optional, List
from ..utils.logger import get_logger, log_api_call, log_error_with_context, log_structured, performance_timer, log_security_event, log_metrics, log_health_check, log_slow_operation
from ..config.settings import settings

class TwitterClient:
    def __init__(self):
        self.logger = get_logger()
        
        self.api_key = settings.TWITTER_API_KEY
        self.api_secret = settings.TWITTER_API_SECRET
        self.access_token = settings.TWITTER_ACCESS_TOKEN
        self.access_token_secret = settings.TWITTER_ACCESS_TOKEN_SECRET
        
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            error_msg = "Twitter API credentials are not properly configured"
            self.logger.error(error_msg)
            log_security_event('twitter_credentials_missing', {
                'severity': 'critical',
                'missing_credentials': [
                    key for key, value in {
                        'api_key': self.api_key,
                        'api_secret': self.api_secret,
                        'access_token': self.access_token,
                        'access_token_secret': self.access_token_secret
                    }.items() if not value
                ]
            })
            raise ValueError(error_msg)
        
        with performance_timer('twitter_client_initialization'):
            # Twitter API v2クライアントを初期化
            self.client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=True
            )
            
            # Twitter API v1.1クライアント（メディアアップロード用）
            auth = tweepy.OAuth1UserHandler(
                self.api_key,
                self.api_secret,
                self.access_token,
                self.access_token_secret
            )
            self.api = tweepy.API(auth)
            
            log_structured('info', 'Twitter client initialized',
                          component='twitter_client',
                          api_v2_enabled=True,
                          api_v1_enabled=True,
                          rate_limit_handling=True)
    
    def post_tweet(self, content: str, image_paths: Optional[List[str]] = None) -> Optional[str]:
        """
        ツイートを投稿する
        
        Args:
            content (str): ツイート内容
            image_paths (Optional[List[str]]): 画像ファイルパスのリスト（最大4枚）
            
        Returns:
            Optional[str]: 投稿成功時はツイートID、失敗時はNone
        """
        with performance_timer('tweet_post_operation'):
            log_structured('info', 'Starting tweet post',
                          content_length=len(content),
                          has_images=bool(image_paths),
                          image_count=len(image_paths) if image_paths else 0)
            
            try:
                media_ids = []
            
                # 画像をアップロード
                if image_paths:
                    with performance_timer('image_upload_batch'):
                        for image_path in image_paths[:4]:  # 最大4枚まで
                            try:
                                with performance_timer(f'image_upload_{os.path.basename(image_path)}'):
                                    log_api_call('Twitter API v1.1', f'media_upload: {os.path.basename(image_path)}')
                                    media = self.api.media_upload(image_path)
                                    media_ids.append(media.media_id)
                                    
                                    log_structured('debug', 'Image uploaded successfully',
                                                  image_path=image_path,
                                                  media_id=media.media_id)
                            except Exception as e:
                                log_error_with_context(e, {
                                    'operation': 'image_upload',
                                    'image_path': image_path,
                                    'component': 'twitter_client'
                                })
                                continue
            
                # ツイートを投稿
                with performance_timer('tweet_creation'):
                    log_api_call('Twitter API v2', 'create_tweet')
                    response = self.client.create_tweet(
                        text=content,
                        media_ids=media_ids if media_ids else None
                    )
                
                if response.data:
                    tweet_id = response.data['id']
                    log_structured('info', 'Tweet posted successfully',
                                  tweet_id=tweet_id,
                                  content_length=len(content),
                                  media_count=len(media_ids))
                    log_api_call('Twitter API v2', 'create_tweet', 200)
                    log_metrics('tweets_posted', 1, 'count')
                    log_metrics('tweet_characters', len(content), 'count')
                    if media_ids:
                        log_metrics('tweets_with_media', 1, 'count')
                    return tweet_id
                else:
                    log_structured('warning', 'Tweet creation returned no data',
                                  response=str(response))
                    return None
                    
            except Exception as e:
                log_error_with_context(e, {
                    'operation': 'post_tweet',
                    'component': 'twitter_client',
                    'content_length': len(content),
                    'has_images': bool(image_paths),
                    'severity': 'high'
                })
                # エラーメトリクスを記録
                from ..utils.logger import _logger_instance
                _logger_instance.metrics.record_error('tweet_post_failed')
                log_metrics('tweet_post_failures', 1, 'count')
                return None
    
    def verify_credentials(self) -> bool:
        """
        認証情報を確認する
        
        Returns:
            bool: 認証成功時はTrue、失敗時はFalse
        """
        with performance_timer('credentials_verification'):
            log_security_event('credentials_verification_attempt', {
                'component': 'twitter_client',
                'timestamp': datetime.now().isoformat()
            })
            
            try:
                log_api_call('Twitter API v2', 'get_me')
                user = self.client.get_me()
                
                if user is not None:
                    log_structured('info', 'Credentials verified successfully',
                                  user_id=user.data.id,
                                  username=user.data.username)
                    log_security_event('credentials_verification_success', {
                        'user_id': user.data.id,
                        'username': user.data.username,
                        'component': 'twitter_client'
                    })
                    return True
                else:
                    log_structured('warning', 'Credentials verification returned no user data')
                    return False
                    
            except Exception as e:
                log_error_with_context(e, {
                    'operation': 'verify_credentials',
                    'component': 'twitter_client',
                    'severity': 'high'
                })
                log_security_event('credentials_verification_failed', {
                    'error': str(e),
                    'component': 'twitter_client'
                })
                return False
    
    def check_health(self) -> bool:
        """
        Twitter APIの健全性をチェック
        
        Returns:
            bool: API接続が正常ならTrue、異常ならFalse
        """
        with performance_timer('twitter_health_check'):
            try:
                # Rate limit情報を取得してAPIの健全性を確認
                log_api_call('Twitter API v2', 'rate_limit_status')
                rate_limit = self.client.get_rate_limit_status()
                
                # 基本的な接続テスト
                user = self.client.get_me()
                healthy = user is not None
                
                if healthy:
                    log_health_check('twitter_api', True, {
                        'user_verified': True,
                        'rate_limit_available': True
                    })
                    log_metrics('twitter_api_health_check', 1, 'success')
                else:
                    log_health_check('twitter_api', False, {
                        'user_verified': False,
                        'error': 'Failed to get user data'
                    })
                    log_metrics('twitter_api_health_check_failures', 1, 'count')
                
                return healthy
                
            except Exception as e:
                log_health_check('twitter_api', False, {
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                log_error_with_context(e, {
                    'operation': 'twitter_health_check',
                    'component': 'twitter_client'
                })
                log_metrics('twitter_api_health_check_failures', 1, 'count')
                return False