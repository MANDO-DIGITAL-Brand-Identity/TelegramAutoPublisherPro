# Telegram Auto Publisher Pro

![Telegram Auto Publisher Pro](https://img.shields.io/badge/Telegram-Auto%20Publisher%20Pro-blue?style=for-the-badge)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-green?style=for-the-badge)
![Telethon](https://img.shields.io/badge/Telethon-2.3.0%2B-red?style=for-the-badge)
![aiogram 3](https://img.shields.io/badge/aiogram-3.0.0%2B-white?style=for-the-badge)

**Telegram Auto Publisher Pro** is a comprehensive, production-ready Telegram automation platform built with Telethon and aiogram. It provides multi-account management, scheduled publishing, content management, group management, and a complete administrator dashboard.

## Features

### Core Features
- **Multi-Account Management**: Connect and manage multiple Telegram accounts with persistent Telethon sessions
- **Content Management**: Store and manage text, images, videos, documents, and media with captions
- **Group Management**: Retrieve, validate permissions, and manage publishing groups for each account
- **Publishing Engine**: Asynchronous publishing with Telethon supporting all media types
- **Scheduling**: Advanced scheduling with APScheduler for automated publishing

### Administrator Features
- **Complete Dashboard**: Real-time statistics, user management, and system monitoring
- **User Management**: View, activate, deactivate, block, and manage user permissions
- **Role-Based Access Control**: Super Admin, Admin, Moderator, and Support Staff roles
- **Mandatory Channel Subscription**: Require users to join specific channels before accessing features
- **Subscription Management**: Free, Premium, Monthly, and Lifetime subscription support
- **Broadcast Management**: Send announcements to all authorized users
- **Audit Logs**: Track all administrative actions and changes
- **Error Reports**: Comprehensive error tracking and reporting

### User Features
- **Account Control Panel**: Full control over connected Telegram accounts
- **Publishing Settings**: Configure content, intervals, schedules, and target groups
- **Publishing Reports**: Detailed statistics and progress tracking
- **Private Messaging**: Manage consenting subscribers and send updates
- **Help and Support**: Access documentation and support information

## Technology Stack

- **Python**: 3.12+
- **Telethon**: 2.3.0+ (Primary Telegram client for user accounts)
- **aiogram**: 3.0.0+ (Control bot interface)
- **Asyncio**: Asynchronous operations
- **SQLAlchemy**: 2.0+ (Database ORM)
- **PostgreSQL**: Production database
- **SQLite**: Development database
- **APScheduler**: Task scheduling
- **Pydantic**: Configuration validation
- **Cryptography**: Sensitive data protection
- **Pytest**: Automated testing

## Architecture

```
TelegramAutoPublisher/
├── main.py                    # Application entry point
├── config.py                  # Configuration management
├── requirements.txt           # Dependencies
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── README.md                  # Documentation
│
├── bot/                       # Control bot (aiogram)
│   ├── __init__.py
│   ├── main.py                # Bot initialization
│   ├── handlers/              # Message and callback handlers
│   │   ├── __init__.py
│   │   ├── start.py           # Start command and main menu
│   │   ├── accounts.py        # Account management handlers
│   │   ├── publishing.py      # Publishing management handlers
│   │   ├── content.py         # Content management handlers
│   │   ├── groups.py          # Group management handlers
│   │   ├── subscriptions.py   # Subscription management handlers
│   │   ├── admin.py           # Administrator handlers
│   │   └── reports.py         # Reporting handlers
│   ├── keyboards/             # Inline keyboards
│   │   ├── __init__.py
│   │   ├── main.py            # Main menu keyboards
│   │   ├── accounts.py        # Account keyboards
│   │   ├── admin.py           # Admin keyboards
│   │   └── styles.py          # Button styling system
│   ├── middlewares/           # Bot middlewares
│   │   └── __init__.py
│   └── messages.py            # Message templates
│
├── accounts/                  # Telethon account management
│   ├── __init__.py
│   ├── manager.py             # Account manager
│   ├── authentication.py      # Authentication logic
│   ├── session_manager.py     # Session management
│   └── connection.py          # Connection handling
│
├── publisher/                 # Publishing engine
│   ├── __init__.py
│   ├── engine.py              # Core publishing engine
│   ├── scheduler.py           # Task scheduler
│   ├── content_manager.py     # Content management
│   ├── group_manager.py       # Group management
│   └── task_manager.py        # Task management
│
├── admin/                     # Administrator features
│   ├── __init__.py
│   ├── dashboard.py           # Admin dashboard
│   ├── user_manager.py        # User management
│   ├── admin_manager.py       # Admin management
│   ├── subscription_manager.py # Subscription management
│   ├── channel_manager.py     # Channel management
│   ├── broadcast_manager.py   # Broadcast management
│   └── audit_manager.py       # Audit logging
│
├── database/                  # Database layer
│   ├── __init__.py
│   ├── models.py              # Database models
│   ├── database.py            # Database connection
│   ├── repositories.py        # Data repositories
│   └── migrations/            # Database migrations
│
├── reports/                   # Reporting system
│   ├── __init__.py
│   ├── statistics.py          # Statistics calculation
│   └── report_generator.py    # Report generation
│
├── security/                  # Security utilities
│   ├── __init__.py
│   ├── encryption.py          # Data encryption
│   ├── permissions.py         # Permission validation
│   └── validation.py          # Input validation
│
├── notifications/             # Notification system
│   └── manager.py             # Notification management
│
├── media/                     # Uploaded media
├── sessions/                  # Telethon session files
├── logs/                      # Log files
└── tests/                     # Automated tests
```

## Quick Start

### Prerequisites

1. Python 3.12 or higher
2. pip (Python package manager)
3. Telegram Bot Token (from @BotFather)
4. Telegram API credentials (from https://my.telegram.org/apps)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-repo/TelegramAutoPublisher.git
cd TelegramAutoPublisher
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
python -c "from database.database import init_db; import asyncio; asyncio.run(init_db())"
```

6. **Run the application**
```bash
python main.py
```

## Configuration

Edit the `.env` file with your settings:

```ini
# Required
BOT_TOKEN=your_bot_token
API_ID=your_api_id
API_HASH=your_api_hash
SUPER_ADMIN_ID=your_telegram_id

# Optional (defaults shown)
DB_TYPE=sqlite
SQLite_PATH=data/bot.db
ENVIRONMENT=development
DEBUG=false
```

## Usage

### User Commands

1. **/start** - Start the bot and show main menu
2. **Main Menu** - Access all features
   - Account Management
   - Publishing Management
   - Content Management
   - Group Management
   - Private Messaging
   - Publishing Reports
   - Subscription Management
   - Application Settings
   - Help and Support

### Administrator Commands

Administrators have access to additional features through the Admin Panel:
- Dashboard Statistics
- User Management
- Account Management
- Subscription Management
- Mandatory Channel Subscription
- Broadcast Management
- Publishing Management
- Content Management
- Admin Management
- System Settings
- Activity Logs
- Error Reports
- Database Management
- Backup and Restore
- System Status
- Maintenance Mode

## Database Schema

The application uses SQLAlchemy with the following main tables:

- **users**: User information and settings
- **administrators**: Administrator accounts and roles
- **telegram_accounts**: Connected Telegram accounts
- **session_metadata**: Telethon session information
- **contents**: Saved posts and media
- **groups**: Managed groups and channels
- **publishing_tasks**: Scheduled publishing tasks
- **publishing_logs**: Publishing history and statistics
- **subscriptions**: User subscription information
- **required_channels**: Mandatory channel subscriptions
- **broadcasts**: Broadcast messages
- **audit_logs**: Administrative action logs
- **application_settings**: System-wide settings

## Security

### Important Security Notes

1. **Session Files**: Telethon session files contain authentication tokens. They are encrypted at rest.
2. **Environment Variables**: Never commit `.env` files to version control.
3. **Administrator Access**: Only the Super Admin can grant administrator privileges.
4. **Channel Verification**: Server-side verification prevents bypassing channel requirements.
5. **Rate Limiting**: Built-in rate limiting prevents Telegram API bans.
6. **Input Validation**: All user inputs are validated and sanitized.

### Security Features

- Encrypted sensitive data at rest
- Secure session storage
- Server-side permission validation
- Input validation and sanitization
- Rate limiting and FloodWait handling
- Audit logging for administrative actions
- Prevention of privilege escalation
- User isolation

## Testing

Run the automated test suite:

```bash
pytest tests/ -v
```

For test coverage:

```bash
pytest tests/ --cov=TelegramAutoPublisher --cov-report=html
```

## Deployment

### Production Deployment (VPS)

1. **Install dependencies**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev postgresql postgresql-contrib
```

2. **Set up application**
```bash
git clone https://github.com/your-repo/TelegramAutoPublisher.git
cd TelegramAutoPublisher
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. **Configure PostgreSQL**
```bash
sudo -u postgres psql
CREATE DATABASE telegram_publisher;
CREATE USER publisher_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE telegram_publisher TO publisher_user;
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with production settings
```

5. **Create systemd service**
```ini
[Unit]
Description=Telegram Auto Publisher Pro
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/TelegramAutoPublisher
Environment="PYTHONPATH=/path/to/TelegramAutoPublisher"
ExecStart=/path/to/TelegramAutoPublisher/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

6. **Enable and start service**
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-publisher
sudo systemctl start telegram-publisher
```

## API Rate Limiting

The application respects Telegram's rate limits:

- **FloodWait**: Automatically sleeps when receiving FloodWait errors
- **Request Rate**: Configurable request rate limiting
- **Concurrent Tasks**: Limited concurrent publishing tasks
- **Retry Logic**: Automatic retries for failed operations

## Troubleshooting

### Common Issues

1. **FloodWait errors**: Increase `FLOOD_SLEEP_THRESHOLD` in `.env`
2. **Session errors**: Delete old session files and reconnect
3. **Database errors**: Check database connection and credentials
4. **Authentication errors**: Verify API_ID and API_HASH

### Logs

Application logs are stored in `logs/bot.log`. For debugging:

```bash
# View recent logs
tail -f logs/bot.log

# View error logs
grep ERROR logs/bot.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Open an issue on GitHub
- Contact the project maintainers

## Acknowledgments

- [Telethon](https://docs.telethon.dev/) - Asynchronous Telegram client
- [aiogram](https://docs.aiogram.dev/) - Asynchronous Telegram Bot API framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [APScheduler](https://apscheduler.readthedocs.io/) - Task scheduling
- [Pydantic](https://docs.pydantic.dev/) - Data validation

---

**Telegram Auto Publisher Pro** - Professional Telegram Automation Platform

*Built with ❤️ for Telegram automation*
