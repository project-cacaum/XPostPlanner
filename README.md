# XPostPlanner

[日本語版 README](README-ja.md)

A Discord bot for scheduling and managing X (Twitter) posts with team approval workflow.

## Features

- 📅 **Post Scheduling**: Schedule X posts using Discord slash commands
- 📷 **Image Support**: Attach up to 4 images per post (JPG, PNG, GIF, WebP)
- 👥 **Team Approval**: Team members can approve/reject posts using reaction buttons
- 🤖 **Automated Posting**: Automatically posts approved content at scheduled times
- 📊 **Approval Tracking**: Track who approved or rejected each post
- 🗂️ **Post Management**: List and cancel scheduled posts
- 📝 **Logging**: Success/failure notifications in dedicated log channels

## Prerequisites

Before you begin, ensure you have the following:

1. **Python 3.8+** and **rye** installed
2. **Discord Bot Token** - Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
3. **X (Twitter) API Keys** - Get API access from [X Developer Portal](https://developer.x.com/)

### Required Discord Bot Permissions

Your Discord bot needs the following permissions:
- Send Messages
- Use Slash Commands
- Read Message History
- Add Reactions
- Embed Links

### Required X API Permissions

Your X API app needs:
- Read and Write permissions
- OAuth 1.0a authentication

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/project-cacaum/XPostPlanner.git
   cd XPostPlanner
   ```

2. **Install dependencies**
   ```bash
   rye sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

4. **Configure your environment variables**
   Edit `.env` file with your credentials:
   ```env
   # Discord Bot Token
   DISCORD_TOKEN=your_discord_bot_token_here
   
   # Discord Channel IDs
   DISCORD_CHANNEL_ID=your_discord_channel_id_here
   DISCORD_LOG_CHANNEL_ID=your_log_channel_id_here
   
   # X (Twitter) API Keys
   TWITTER_API_KEY=your_twitter_api_key_here
   TWITTER_API_SECRET=your_twitter_api_secret_here
   TWITTER_ACCESS_TOKEN=your_twitter_access_token_here
   TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret_here
   ```

## Usage

### Starting the Bot

```bash
rye run start
```

### Scheduling a Post

Use the `/post` slash command in your Discord server:

```
/post content:"Hello, world! 🌟" time:"2025-12-31 23:59:30"
```

**Quick posting:**
```
/post content:"Emergency post!" time:"30秒後"
/post content:"Quick update" time:"5分30秒後"
```

**With images:**
```
/post content:"Check out these photos!" time:"14:30:45" image1:[attach file] image2:[attach file]
```

**Parameters:**
- `content`: The text content to post on X
- `time`: When to post - supports various formats including seconds
- `image1-4` (optional): Up to 4 image files to attach (JPG, PNG, GIF, WebP)

**Supported time formats:**
- Absolute: `2025-01-15 14:30:45`, `14:30:45`, `14:30`
- Relative: `30秒後`, `5分30秒後`, `2時間30分後`

### Managing Posts

**List scheduled posts:**
```
/list
```

**Cancel a scheduled post:**
```
/cancel post_id:123
```

### Approving Posts

After scheduling a post, team members can:
- Click 👍 to approve
- Click 👎 to reject
- The embed will show current approval counts

### Monitoring

The bot will send notifications to your log channel:
- ✅ Successful posts
- ❌ Failed posts
- 🚫 Cancelled posts
- ⚠️ System errors

## Project Structure

```
XPostPlanner/
├── src/xpostplanner/
│   ├── __init__.py
│   ├── bot.py              # Main Discord bot
│   ├── database.py         # SQLite database management
│   ├── scheduler.py        # Post scheduling logic
│   ├── twitter_client.py   # X API integration
│   ├── image_manager.py    # Image handling and storage
│   └── date_parser.py      # Date/time parsing utilities
├── docs/
│   └── requirements.md     # Project requirements
├── images/                 # Temporary image storage (auto-created)
├── .env.example           # Environment variables template
├── pyproject.toml         # Project configuration
└── README.md             # This file
```

## Configuration

### Getting Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section
4. Copy the token

### Getting X API Keys

1. Go to [X Developer Portal](https://developer.x.com/)
2. Create a new app
3. Generate API keys and access tokens
4. Make sure your app has Read and Write permissions

### Getting Discord Channel IDs

1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on your channel and select "Copy ID"

## Development

### Running in Development Mode

```bash
rye run start
```

### Database

The bot uses SQLite for storing scheduled posts, approvals, and image metadata. The database file (`xpost_scheduler.db`) is created automatically when the bot starts.

### Image Storage

Images are temporarily stored in the `images/` directory and automatically cleaned up after posting. Supported formats: JPG, PNG, GIF, WebP (max 4 images per post).

### Contributing

1. Create an issue describing your changes
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Commit with conventional commit messages
5. Push to your branch and create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues:

1. Check that all environment variables are set correctly
2. Verify your Discord bot has the required permissions
3. Ensure your X API keys are valid and have the correct permissions
4. Check the console output for error messages

For additional help, please create an issue on GitHub.
