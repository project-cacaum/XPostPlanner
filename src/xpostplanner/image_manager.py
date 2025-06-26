import os
import uuid
import shutil
from typing import List, Dict, Any
from pathlib import Path

class ImageManager:
    def __init__(self, storage_dir: str = "images"):
        """
        画像管理クラス
        
        Args:
            storage_dir (str): 画像保存ディレクトリ
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    async def save_discord_attachments(self, attachments: List[Any]) -> List[Dict[str, Any]]:
        """
        Discordの添付ファイルを保存
        
        Args:
            attachments: Discord添付ファイルのリスト
            
        Returns:
            List[Dict[str, Any]]: 保存された画像情報のリスト
        """
        saved_images = []
        
        for attachment in attachments:
            # 画像ファイルかチェック
            if not self._is_image_file(attachment.filename):
                continue
            
            # ユニークなファイル名を生成
            file_extension = Path(attachment.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = self.storage_dir / unique_filename
            
            try:
                # ファイルを保存
                attachment_data = await attachment.read()
                with open(file_path, 'wb') as f:
                    f.write(attachment_data)
                
                saved_images.append({
                    'file_path': str(file_path),
                    'original_filename': attachment.filename,
                    'file_size': attachment.size
                })
                
            except Exception as e:
                print(f"Failed to save attachment {attachment.filename}: {e}")
                continue
        
        return saved_images
    
    def _is_image_file(self, filename: str) -> bool:
        """
        画像ファイルかどうかを判定
        
        Args:
            filename (str): ファイル名
            
        Returns:
            bool: 画像ファイルの場合True
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        return Path(filename).suffix.lower() in image_extensions
    
    def get_image_paths(self, images: List[Dict[str, Any]]) -> List[str]:
        """
        画像情報から画像パスのリストを取得
        
        Args:
            images: 画像情報のリスト
            
        Returns:
            List[str]: 画像パスのリスト
        """
        return [image['file_path'] for image in images]
    
    def cleanup_images(self, image_paths: List[str]):
        """
        画像ファイルを削除
        
        Args:
            image_paths: 削除する画像パスのリスト
        """
        for image_path in image_paths:
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"Cleaned up image: {image_path}")
            except Exception as e:
                print(f"Failed to cleanup image {image_path}: {e}")