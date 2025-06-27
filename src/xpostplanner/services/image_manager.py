import os
import uuid
import shutil
from typing import List, Dict, Any
from pathlib import Path
from ..utils.logger import get_logger, log_structured, performance_timer, log_error_with_context, log_security_event

class ImageManager:
    def __init__(self, storage_dir: str = "images"):
        """
        画像管理クラス
        
        Args:
            storage_dir (str): 画像保存ディレクトリ
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.logger = get_logger()
        
        log_structured('info', 'ImageManager initialized',
                      component='image_manager',
                      storage_dir=str(self.storage_dir))
    
    async def save_discord_attachments(self, attachments: List[Any]) -> List[Dict[str, Any]]:
        """
        Discordの添付ファイルを保存
        
        Args:
            attachments: Discord添付ファイルのリスト
            
        Returns:
            List[Dict[str, Any]]: 保存された画像情報のリスト
        """
        with performance_timer('save_discord_attachments'):
            log_structured('info', 'Starting Discord attachments save',
                          attachment_count=len(attachments),
                          component='image_manager')
            
            saved_images = []
        
            for attachment in attachments:
                # 画像ファイルかチェック
                if not self._is_image_file(attachment.filename):
                    log_structured('warning', 'Non-image file skipped',
                                  filename=attachment.filename,
                                  component='image_manager')
                    continue
                
                # セキュリティチェック - ファイルサイズの確認
                if attachment.size > 10 * 1024 * 1024:  # 10MB制限
                    log_security_event('large_file_upload_attempt', {
                        'filename': attachment.filename,
                        'file_size': attachment.size,
                        'max_allowed': 10 * 1024 * 1024
                    })
                    continue
                
                # ユニークなファイル名を生成
                file_extension = Path(attachment.filename).suffix
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                file_path = self.storage_dir / unique_filename
                
                try:
                    with performance_timer(f'save_attachment_{attachment.filename}'):
                        # ファイルを保存
                        attachment_data = await attachment.read()
                        with open(file_path, 'wb') as f:
                            f.write(attachment_data)
                        
                        saved_images.append({
                            'file_path': str(file_path),
                            'original_filename': attachment.filename,
                            'file_size': attachment.size
                        })
                        
                        log_structured('info', 'Attachment saved successfully',
                                      original_filename=attachment.filename,
                                      unique_filename=unique_filename,
                                      file_size=attachment.size,
                                      component='image_manager')
                        
                except Exception as e:
                    log_error_with_context(e, {
                        'operation': 'save_attachment',
                        'filename': attachment.filename,
                        'component': 'image_manager'
                    })
                    continue
        
            log_structured('info', 'Discord attachments save completed',
                          saved_count=len(saved_images),
                          total_attempted=len(attachments),
                          component='image_manager')
            
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
        is_image = Path(filename).suffix.lower() in image_extensions
        
        log_structured('debug', 'Image file validation',
                      filename=filename,
                      is_image=is_image,
                      extension=Path(filename).suffix.lower(),
                      component='image_manager')
        
        return is_image
    
    def get_image_paths(self, images: List[Dict[str, Any]]) -> List[str]:
        """
        画像情報から画像パスのリストを取得
        
        Args:
            images: 画像情報のリスト
            
        Returns:
            List[str]: 画像パスのリスト
        """
        paths = [image['file_path'] for image in images]
        
        log_structured('debug', 'Image paths extracted',
                      image_count=len(images),
                      path_count=len(paths),
                      component='image_manager')
        
        return paths
    
    def cleanup_images(self, image_paths: List[str]):
        """
        画像ファイルを削除
        
        Args:
            image_paths: 削除する画像パスのリスト
        """
        with performance_timer('cleanup_images'):
            log_structured('info', 'Starting image cleanup',
                          image_count=len(image_paths),
                          component='image_manager')
            
            success_count = 0
            for image_path in image_paths:
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        success_count += 1
                        log_structured('debug', 'Image cleaned up successfully',
                                      image_path=image_path,
                                      component='image_manager')
                    else:
                        log_structured('warning', 'Image file not found for cleanup',
                                      image_path=image_path,
                                      component='image_manager')
                except Exception as e:
                    log_error_with_context(e, {
                        'operation': 'cleanup_image',
                        'image_path': image_path,
                        'component': 'image_manager'
                    })
            
            log_structured('info', 'Image cleanup completed',
                          success_count=success_count,
                          total_count=len(image_paths),
                          component='image_manager')