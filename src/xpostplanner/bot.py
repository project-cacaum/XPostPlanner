import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
from .models.database import Database
from .services.scheduler import PostScheduler
from .utils.date_parser import parse_datetime, get_supported_formats
# プロジェクトルートの.envファイルを読み込み（他のインポートより先に実行）
project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

from .services.image_manager import ImageManager
from .utils.logger import get_logger, log_error_with_context, log_discord_event, log_security_event, performance_timer, log_structured
from .config.settings import settings

class XPostBot(commands.Bot):
    def __init__(self):
        self.logger = get_logger()
        
        # セキュリティ監査ログ - ボット初期化
        log_security_event('bot_initialization', {
            'timestamp': datetime.now().isoformat(),
            'pid': os.getpid()
        })
        
        # 設定の検証
        missing_settings = settings.validate()
        if missing_settings:
            self.logger.error(f"Missing required settings: {missing_settings}")
            log_security_event('configuration_error', {
                'missing_settings': missing_settings,
                'severity': 'high'
            })
            raise ValueError(f"Missing required environment variables: {', '.join(missing_settings)}")
        
        # 必要なディレクトリを作成
        settings.create_directories()
        
        log_structured('info', 'Initializing XPostBot', 
                      component='bot', 
                      operation='initialization',
                      settings_loaded=True)
        self.logger.info(f"Settings: {settings}")
        
        intents = discord.Intents.default()
        super().__init__(command_prefix='!', intents=intents)
        
        with performance_timer('bot_components_initialization'):
            try:
                self.db = Database()
                self.scheduler = PostScheduler(self)
                self.image_manager = ImageManager()
                log_structured('info', 'Bot components initialized successfully',
                              component='bot',
                              operation='component_initialization',
                              database_ready=True,
                              scheduler_ready=True,
                              image_manager_ready=True)
            except Exception as e:
                log_error_with_context(e, {
                    'component': 'bot_initialization',
                    'operation': 'component_setup',
                    'severity': 'critical'
                })
                raise
        
    async def setup_hook(self):
        # スラッシュコマンドを同期
        with performance_timer('slash_commands_sync'):
            try:
                log_discord_event('command_sync_start')
                synced = await self.tree.sync()
                log_discord_event('command_sync_complete', 
                                  command_count=len(synced),
                                  commands=[cmd.name for cmd in synced])
            except Exception as e:
                log_error_with_context(e, {
                    'operation': 'command_sync',
                    'component': 'discord_api',
                    'severity': 'high'
                })
                raise
    
    async def on_ready(self):
        log_discord_event('bot_ready', 
                          bot_user=str(self.user),
                          guild_count=len(self.guilds),
                          guild_ids=[str(guild.id) for guild in self.guilds])
        
        # スケジューラを開始
        try:
            asyncio.create_task(self.scheduler.start())
            log_structured('info', 'Scheduler started successfully',
                          component='scheduler',
                          operation='start',
                          status='running')
        except Exception as e:
            log_error_with_context(e, {
                'operation': 'scheduler_start',
                'component': 'scheduler',
                'severity': 'critical'
            })

bot = XPostBot()

@bot.tree.command(name="post", description="X(Twitter)への投稿を予約します（例: 30分後、14:30、01/15 14:30）")
async def post_command(interaction: discord.Interaction, content: str, time: str, 
                      image1: discord.Attachment = None, image2: discord.Attachment = None,
                      image3: discord.Attachment = None, image4: discord.Attachment = None):
    """
    投稿を予約するスラッシュコマンド
    """
    await interaction.response.defer()
    
    # コマンド実行をログに記録
    log_discord_event('slash_command_executed', 
                      command='post',
                      user_id=str(interaction.user.id),
                      guild_id=str(interaction.guild_id),
                      channel_id=str(interaction.channel_id),
                      content_length=len(content),
                      has_attachments=any([image1, image2, image3, image4]))
    
    # 時刻をパース
    with performance_timer('datetime_parsing'):
        scheduled_time = parse_datetime(time)
    
    if scheduled_time is None:
        error_message = f"❌ 時刻の形式が正しくありません。\n\n{get_supported_formats()}"
        log_structured('warning', 'Invalid datetime format provided',
                      user_id=str(interaction.user.id),
                      time_input=time,
                      operation='post_command')
        await interaction.followup.send(error_message, ephemeral=True)
        return
    
    # 過去の時刻でないかチェック
    if scheduled_time <= datetime.now():
        log_security_event('invalid_time_attempt', {
            'user_id': str(interaction.user.id),
            'attempted_time': scheduled_time.isoformat(),
            'current_time': datetime.now().isoformat()
        })
        await interaction.followup.send("❌ 過去の時刻は指定できません。", ephemeral=True)
        return
    
    try:
        # 画像を処理
        attachments = [img for img in [image1, image2, image3, image4] if img is not None]
        saved_images = []
        has_images = len(attachments) > 0
        
        if has_images:
            # 画像を保存
            with performance_timer('image_processing'):
                saved_images = await bot.image_manager.save_discord_attachments(attachments)
                if not saved_images:
                    log_structured('error', 'Image save failed',
                                  user_id=str(interaction.user.id),
                                  attachment_count=len(attachments),
                                  operation='image_save')
                    await interaction.followup.send("❌ 画像の保存に失敗しました。", ephemeral=True)
                    return
                
                log_structured('info', 'Images saved successfully',
                              user_id=str(interaction.user.id),
                              saved_count=len(saved_images),
                              total_size=sum(img['file_size'] for img in saved_images))
        
        # 埋め込みを作成
        embed = discord.Embed(
            title="📝 投稿予約",
            description=f"以下の投稿を予約しました:\n\n**投稿内容:**\n{content}\n\n**投稿予定時刻:**\n{scheduled_time.strftime('%Y-%m-%d %H:%M')}",
            color=0x1DA1F2
        )
        
        # 画像がある場合は情報を追加
        if has_images:
            embed.add_field(
                name="📷 添付画像",
                value=f"{len(saved_images)}枚の画像が添付されています",
                inline=False
            )
            # 最初の画像をサムネイルとして設定
            if saved_images:
                embed.set_thumbnail(url=f"attachment://{Path(saved_images[0]['original_filename']).name}")
        
        # 承認ボタンを追加
        view = ApprovalView(bot.db)
        
        # 画像ファイルを添付
        files = []
        if has_images:
            for image in saved_images:
                try:
                    file = discord.File(image['file_path'], filename=image['original_filename'])
                    files.append(file)
                except Exception as e:
                    print(f"Failed to attach image {image['file_path']}: {e}")
        
        message = await interaction.followup.send(embed=embed, files=files, view=view)
        
        # データベースに投稿予約を保存
        with performance_timer('database_post_creation'):
            post_id = bot.db.add_scheduled_post(
                content=content,
                scheduled_time=scheduled_time,
                discord_message_id=str(message.id),
                guild_id=str(interaction.guild_id),
                channel_id=str(interaction.channel_id),
                has_images=has_images
            )
            
            log_structured('info', 'Post scheduled successfully',
                          post_id=post_id,
                          user_id=str(interaction.user.id),
                          scheduled_time=scheduled_time.isoformat(),
                          has_images=has_images,
                          content_length=len(content))
        
        # 画像情報をデータベースに保存
        if has_images:
            for image in saved_images:
                bot.db.add_post_image(
                    post_id=post_id,
                    file_path=image['file_path'],
                    original_filename=image['original_filename'],
                    file_size=image['file_size']
                )
        
        # ViewにPost IDを設定
        view.post_id = post_id
        await message.edit(view=view)
        
    except Exception as e:
        log_error_with_context(e, {
            'operation': 'post_command',
            'user_id': str(interaction.user.id),
            'guild_id': str(interaction.guild_id),
            'channel_id': str(interaction.channel_id),
            'content_length': len(content),
            'has_images': has_images
        })
        await interaction.followup.send(
            f"❌ 投稿の予約に失敗しました: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="help", description="ボットの使い方と日付フォーマットを表示します")
async def help_command(interaction: discord.Interaction):
    log_discord_event('help_command_executed',
                      user_id=str(interaction.user.id),
                      guild_id=str(interaction.guild_id))
    """
    ヘルプコマンド - ボットの使い方を表示
    """
    embed = discord.Embed(
        title="🤖 XPostPlanner ボットの使い方",
        description="X（Twitter）投稿を予約・管理するDiscordボットです",
        color=0x1DA1F2
    )
    
    # 基本的な使い方
    embed.add_field(
        name="📝 基本的な使い方",
        value="`/post content:\"投稿内容\" time:\"投稿時刻\"`\n投稿を予約して、チームメンバーの承認を得ることができます。",
        inline=False
    )
    
    # 日付フォーマット
    date_formats = get_supported_formats()
    embed.add_field(
        name="📅 日付フォーマット",
        value=date_formats,
        inline=False
    )
    
    # 使用例
    examples = """
**使用例:**
• `/post content:"緊急投稿" time:"30秒後"`
• `/post content:"すぐ投稿" time:"5分30秒後"`
• `/post content:"定期投稿" time:"14:30:45"`
• `/post content:"明日の予告" time:"01/15 10:00"`
• `/post content:"画像付き投稿" time:"16:00" image1:[画像ファイル]`
"""
    embed.add_field(
        name="💡 使用例", 
        value=examples,
        inline=False
    )
    
    # 画像機能の説明
    image_info = """
最大4枚の画像を添付できます（image1〜image4パラメータ）。
対応形式：JPG、PNG、GIF、WebP
投稿後、画像ファイルは自動的に削除されます。
"""
    embed.add_field(
        name="📷 画像機能",
        value=image_info,
        inline=False
    )
    
    # 管理機能
    management_info = """
• `/list` - スケジュール中の投稿一覧を表示
• `/cancel post_id:[投稿ID]` - 指定した投稿をキャンセル
"""
    embed.add_field(
        name="🗂️ 管理機能",
        value=management_info,
        inline=False
    )
    
    # 承認機能
    embed.add_field(
        name="👥 承認機能",
        value="投稿予約後、👍ボタンで承認、👎ボタンで却下できます。\n指定時刻になると自動的にXに投稿されます。",
        inline=False
    )
    
    # フッター
    embed.set_footer(text="🚀 XPostPlanner | チーム投稿管理ボット")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

class ApprovalView(discord.ui.View):
    def __init__(self, db: Database):
        super().__init__(timeout=None)
        self.db = db
        self.post_id = None
    
    @discord.ui.button(emoji="👍", style=discord.ButtonStyle.success, custom_id="good_button")
    async def good_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        log_discord_event('approval_button_clicked',
                          button_type='good',
                          user_id=str(interaction.user.id),
                          post_id=self.post_id)
        if not self.post_id:
            await interaction.response.send_message("❌ 投稿IDが見つかりません", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        
        # 既存の承認記録を確認
        approval_counts = self.db.get_approval_counts(self.post_id)
        
        # 既に👍を押している場合は取り消し
        try:
            self.db.remove_approval(self.post_id, user_id)
            self.db.add_approval(self.post_id, user_id, 'good')
            await interaction.response.send_message("👍 Good!", ephemeral=True)
        except:
            # 初回の場合
            self.db.add_approval(self.post_id, user_id, 'good')
            await interaction.response.send_message("👍 Good!", ephemeral=True)
        
        await self.update_embed(interaction)
    
    @discord.ui.button(emoji="👎", style=discord.ButtonStyle.danger, custom_id="bad_button")
    async def bad_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        log_discord_event('approval_button_clicked',
                          button_type='bad',
                          user_id=str(interaction.user.id),
                          post_id=self.post_id)
        if not self.post_id:
            await interaction.response.send_message("❌ 投稿IDが見つかりません", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        
        # 既存の承認記録を確認
        approval_counts = self.db.get_approval_counts(self.post_id)
        
        # 既に👎を押している場合は取り消し
        try:
            self.db.remove_approval(self.post_id, user_id)
            self.db.add_approval(self.post_id, user_id, 'bad')
            await interaction.response.send_message("👎 Bad!", ephemeral=True)
        except:
            # 初回の場合
            self.db.add_approval(self.post_id, user_id, 'bad')
            await interaction.response.send_message("👎 Bad!", ephemeral=True)
        
        await self.update_embed(interaction)
    
    async def update_embed(self, interaction: discord.Interaction):
        if not self.post_id:
            return
        
        # 元のembedを取得
        embed = interaction.message.embeds[0]
        
        # データベースから承認状況を取得
        approval_counts = self.db.get_approval_counts(self.post_id)
        
        # フィールドを追加/更新
        embed.clear_fields()
        embed.add_field(name="👍 Good", value=f"{approval_counts['good']}人", inline=True)
        embed.add_field(name="👎 Bad", value=f"{approval_counts['bad']}人", inline=True)
        
        # メッセージを編集
        try:
            await interaction.edit_original_response(embed=embed, view=self)
        except:
            # 既にレスポンス済みの場合
            await interaction.message.edit(embed=embed, view=self)

def main():
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables")
        return
    
    bot.run(token)

if __name__ == "__main__":
    main()