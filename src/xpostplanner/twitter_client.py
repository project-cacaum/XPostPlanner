import tweepy
import os
from typing import Optional

class TwitterClient:
    def __init__(self):
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            raise ValueError("Twitter API credentials are not properly configured")
        
        # Twitter API v2クライアントを初期化
        self.client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
            wait_on_rate_limit=True
        )
    
    def post_tweet(self, content: str) -> Optional[str]:
        """
        ツイートを投稿する
        
        Args:
            content (str): ツイート内容
            
        Returns:
            Optional[str]: 投稿成功時はツイートID、失敗時はNone
        """
        try:
            response = self.client.create_tweet(text=content)
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