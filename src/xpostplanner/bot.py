import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from .database import Database
from .scheduler import PostScheduler
from .date_parser import parse_datetime, get_supported_formats

load_dotenv()

class XPostBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix='!', intents=intents)
        self.db = Database()
        self.scheduler = PostScheduler(self)
        
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
async def post_command(interaction: discord.Interaction, content: str, time: str):
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
        
        embed = discord.Embed(
            title="📝 投稿予約",
            description=f"以下の投稿を予約しました:\n\n**投稿内容:**\n{content}\n\n**投稿予定時刻:**\n{scheduled_time.strftime('%Y-%m-%d %H:%M')}",
            color=0x1DA1F2
        )
        
        # 承認ボタンを追加
        view = ApprovalView(bot.db)
        
        message = await interaction.followup.send(embed=embed, view=view)
        
        # データベースに投稿予約を保存
        post_id = bot.db.add_scheduled_post(
            content=content,
            scheduled_time=scheduled_time,
            discord_message_id=str(message.id),
            guild_id=str(interaction.guild_id),
            channel_id=str(interaction.channel_id)
        )
        
        # ViewにPost IDを設定
        view.post_id = post_id
        await message.edit(view=view)
        
    except Exception as e:
        await interaction.followup.send(
            f"❌ 投稿の予約に失敗しました: {str(e)}",
            ephemeral=True
        )

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