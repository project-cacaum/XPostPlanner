import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from .database import Database
from .scheduler import PostScheduler
from .date_parser import get_supported_formats

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

@bot.tree.command(name="post", description="X(Twitter)への投稿を予約します")
async def post_command(interaction: discord.Interaction, content: str, time: str):
    """
    投稿を予約するスラッシュコマンド
    """
    await interaction.response.defer()
    
    try:
        # 時刻をパース
        scheduled_time = datetime.fromisoformat(time.replace('T', ' '))
        
        # 過去の時刻でないかチェック
        if scheduled_time <= datetime.now():
            await interaction.followup.send("❌ 過去の時刻は指定できません。", ephemeral=True)
            return
        
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
        
    except ValueError:
        await interaction.followup.send(
            "❌ 時刻の形式が正しくありません。\n例: `2025-07-01 10:00` または `2025-07-01T10:00`",
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
• `/post content:"こんにちは！" time:"30分後"`
• `/post content:"定期投稿です" time:"14:30"`
• `/post content:"明日の予告" time:"01/15 10:00"`
• `/post content:"新商品のお知らせ" time:"2025-01-20 15:30"`
"""
    embed.add_field(
        name="💡 使用例", 
        value=examples,
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