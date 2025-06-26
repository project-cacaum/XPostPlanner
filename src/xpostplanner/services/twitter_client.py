import tweepy
import os
from typing import Optional, List
from ..utils.logger import get_logger, log_api_call, log_error_with_context
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
            raise ValueError(error_msg)
        
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
    
    def post_tweet(self, content: str, image_paths: Optional[List[str]] = None) -> Optional[str]:
        """
        ツイートを投稿する
        
        Args:
            content (str): ツイート内容
            image_paths (Optional[List[str]]): 画像ファイルパスのリスト（最大4枚）
            
        Returns:
            Optional[str]: 投稿成功時はツイートID、失敗時はNone
        """
        try:
            media_ids = []
            
            # 画像をアップロード
            if image_paths:
                for image_path in image_paths[:4]:  # 最大4枚まで
                    try:
                        media = self.api.media_upload(image_path)
                        media_ids.append(media.media_id)
                    except Exception as e:
                        print(f"Failed to upload image {image_path}: {e}")
                        continue
            
            # ツイートを投稿
            response = self.client.create_tweet(
                text=content,
                media_ids=media_ids if media_ids else None
            )
            
            if response.data:
                return response.data['id']
            return None
        except Exception as e:
            print(f"Failed to post tweet: {e}")
            return None
    
    def verify_credentials(self) -> bool:
        """
        認証情報を確認する
        
        Returns:
            bool: 認証成功時はTrue、失敗時はFalse
        """
        try:
            user = self.client.get_me()
            return user is not None
        except Exception as e:
            print(f"Failed to verify credentials: {e}")
            return False