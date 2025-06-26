# XPostPlanner

[English README](README.md)

チームのX（Twitter）投稿を効率的に管理するDiscordボットです。投稿のスケジューリングとチーム承認ワークフローを提供します。

## 機能

- 📅 **投稿スケジューリング**: Discordのスラッシュコマンドを使ってXの投稿を予約
- 👥 **チーム承認**: リアクションボタンを使ってチームメンバーが投稿を承認/却下
- 🤖 **自動投稿**: 承認された投稿を指定時間に自動投稿
- 📊 **承認状況の追跡**: 誰が投稿を承認・却下したかを記録
- 📝 **ログ機能**: 専用チャンネルに成功/失敗通知を送信

## 必要な準備

始める前に、以下を用意してください：

1. **Python 3.8+** と **rye** がインストール済み
2. **Discord Bot Token** - [Discord Developer Portal](https://discord.com/developers/applications)でボットを作成
3. **X (Twitter) API キー** - [X Developer Portal](https://developer.x.com/)でAPIアクセスを取得

### 必要なDiscordボット権限

Discordボットには以下の権限が必要です：
- メッセージを送信
- スラッシュコマンドを使用
- メッセージ履歴を読む
- リアクションを追加
- 埋め込みリンク

### 必要なX API権限

X APIアプリには以下が必要です：
- 読み取りと書き込み権限
- OAuth 1.0a認証

## インストール

1. **リポジトリをクローン**
   ```bash
   git clone https://github.com/project-cacaum/XPostPlanner.git
   cd XPostPlanner
   ```

2. **依存関係をインストール**
   ```bash
   rye sync
   ```

3. **環境変数を設定**
   ```bash
   cp .env.example .env
   ```

4. **環境変数を設定**
   `.env`ファイルを編集して認証情報を設定：
   ```env
   # Discord Bot Token
   DISCORD_TOKEN=あなたのdiscordボットトークン
   
   # Discord Channel IDs
   DISCORD_CHANNEL_ID=あなたのディスコードチャンネルID
   DISCORD_LOG_CHANNEL_ID=ログ用チャンネルID
   
   # X (Twitter) API Keys
   TWITTER_API_KEY=あなたのtwitter_api_key
   TWITTER_API_SECRET=あなたのtwitter_api_secret
   TWITTER_ACCESS_TOKEN=あなたのtwitter_access_token
   TWITTER_ACCESS_TOKEN_SECRET=あなたのtwitter_access_token_secret
   ```

## 使い方

### ボットの起動

```bash
rye run python -m xpostplanner.bot
```

### 投稿の予約

Discordサーバーで `/post` スラッシュコマンドを使用：

```
/post content:"こんにちは、世界！🌟" time:"2025-12-31 23:59"
```

**パラメータ:**
- `content`: Xに投稿するテキスト内容
- `time`: 投稿する時刻（形式：`YYYY-MM-DD HH:MM` または `YYYY-MM-DDTHH:MM`）

### 投稿の承認

投稿を予約した後、チームメンバーは：
- 👍 をクリックして承認
- 👎 をクリックして却下
- 埋め込みメッセージで現在の承認数を確認

### モニタリング

ボットはログチャンネルに以下の通知を送信します：
- ✅ 投稿成功
- ❌ 投稿失敗
- ⚠️ システムエラー

## プロジェクト構造

```
XPostPlanner/
├── src/xpostplanner/
│   ├── __init__.py
│   ├── bot.py              # メインのDiscordボット
│   ├── database.py         # SQLiteデータベース管理
│   ├── scheduler.py        # 投稿スケジューリングロジック
│   └── twitter_client.py   # X API連携
├── docs/
│   └── requirements.md     # プロジェクト要件
├── .env.example           # 環境変数テンプレート
├── pyproject.toml         # プロジェクト設定
└── README.md             # このファイル
```

## 設定

### Discord Bot Tokenの取得

1. [Discord Developer Portal](https://discord.com/developers/applications)にアクセス
2. 新しいアプリケーションを作成
3. "Bot"セクションに移動
4. トークンをコピー

### X API キーの取得

1. [X Developer Portal](https://developer.x.com/)にアクセス
2. 新しいアプリを作成
3. APIキーとアクセストークンを生成
4. アプリに読み取りと書き込み権限があることを確認

### Discord チャンネルIDの取得

1. Discordで開発者モードを有効化（ユーザー設定 > 高度な設定 > 開発者モード）
2. チャンネルを右クリックして「IDをコピー」を選択

## 開発

### 開発モードでの実行

```bash
rye run python -m xpostplanner.bot
```

### データベース

ボットは予約投稿と承認記録の保存にSQLiteを使用します。データベースファイル（`xpost_scheduler.db`）はボット起動時に自動作成されます。

### 貢献

1. 変更内容を説明するイシューを作成
2. フィーチャーブランチを作成：`git checkout -b feature/あなたの機能名`
3. 変更を実施
4. 従来のコミットメッセージでコミット
5. ブランチにプッシュしてプルリクエストを作成

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています。詳細はLICENSEファイルを参照してください。

## サポート

問題が発生した場合：

1. すべての環境変数が正しく設定されているか確認
2. Discordボットに必要な権限があるか確認
3. X APIキーが有効で正しい権限を持っているか確認
4. コンソール出力でエラーメッセージを確認

追加のヘルプが必要な場合は、GitHubでイシューを作成してください。