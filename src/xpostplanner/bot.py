import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
from .database import Database
from .scheduler import PostScheduler
from .date_parser import parse_datetime, get_supported_formats
from .image_manager import ImageManager

load_dotenv()

class XPostBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix='!', intents=intents)
        self.db = Database()
        self.scheduler = PostScheduler(self)
        self.image_manager = ImageManager()
        
    async def setup_hook(self):
        # スラッシュコマンドを同期
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print(f'Bot is ready in {len(self.guilds)} guilds')
        
        # スケジューラを開始
        asyncio.create_task(self.scheduler.start())

bot = XPostBot()

@bot.tree.command(name="post", description="X(Twitter)への投稿を予約します（例: 30分後、14:30、01/15 14:30）")
async def post_command(interaction: discord.Interaction, content: str, time: str, 
                      image1: discord.Attachment = None, image2: discord.Attachment = None,
                      image3: discord.Attachment = None, image4: discord.Attachment = None):
    """
    投稿を予約するスラッシュコマンド
    """
    await interaction.response.defer()
    
    # 時刻をパース
    scheduled_time = parse_datetime(time)
    
    if scheduled_time is None:
        error_message = f"❌ 時刻の形式が正しくありません。\n\n{get_supported_formats()}"
        await interaction.followup.send(error_message, ephemeral=True)
        return
    
    # 過去の時刻でないかチェック
    if scheduled_time <= datetime.now():
        await interaction.followup.send("❌ 過去の時刻は指定できません。", ephemeral=True)
        return
    
    try:
        # 画像を処理
        attachments = [img for img in [image1, image2, image3, image4] if img is not None]
        saved_images = []
        has_images = len(attachments) > 0
        
        if has_images:
            # 画像を保存
            saved_images = await bot.image_manager.save_discord_attachments(attachments)
            if not saved_images:
                await interaction.followup.send("❌ 画像の保存に失敗しました。", ephemeral=True)
                return
        
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
        post_id = bot.db.add_scheduled_post(
            content=content,
            scheduled_time=scheduled_time,
            discord_message_id=str(message.id),
            guild_id=str(interaction.guild_id),
            channel_id=str(interaction.channel_id),
            has_images=has_images
        )
        
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
        await interaction.followup.send(
            f"❌ 投稿の予約に失敗しました: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="help", description="ボットの使い方と日付フォーマットを表示します")
async def help_command(interaction: discord.Interaction):
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