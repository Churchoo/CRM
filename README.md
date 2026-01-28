# CRM - Customer Relationship Manager

A desktop application for managing customer relationships with automated birthday email reminders.

## Features

- 📇 **Customer Management**: Add, edit, delete, and search customers
- 📧 **Email Integration**: Send emails directly from the application
- 🎂 **Automated Birthday Emails**: Automatically send birthday wishes to customers
- 💾 **Local Database**: SQLite database stored in a single file for easy backup
- 🔒 **Secure**: Email credentials are encrypted
- 🎨 **User-Friendly GUI**: Clean and intuitive interface

## Installation

### Option 1: Run from Source (Requires Python)

1. **Install Python 3.8 or higher** from [python.org](https://www.python.org/downloads/)

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python crm_app.py
   ```

### Option 2: Use Standalone Executable (No Python Required)

Simply double-click `crm_app.exe` to run the application.

## First-Time Setup

### Email Configuration

1. Go to **Tools → Email Settings**
2. Select your email provider (Gmail, Outlook, Yahoo, or Custom)
3. Enter your email and password:
   - **Gmail**: Use an [App Password](https://support.google.com/accounts/answer/185833) (requires 2FA enabled)
   - **Outlook**: Use your regular password
   - **Yahoo**: Use an [App Password](https://help.yahoo.com/kb/generate-third-party-passwords-sln15241.html)
4. Click **Test Connection** to verify settings
5. Click **Save**

### Adding Customers

1. Click **➕ Add Customer**
2. Fill in customer details:
   - **Name** (required)
   - **Email** (required)
   - **Birthday** (for automated emails)
   - **Phone** (optional)
   - **Notes** (optional)
3. Click **💾 Save**

## Usage

### Managing Customers

- **Search**: Type in the search box to filter customers by name or email
- **Edit**: Click on a customer in the list to load their details, make changes, and click Save
- **Delete**: Select a customer and click **🗑️ Delete**

### Sending Emails

- **Manual Email**: Select a customer and click **📧 Send Email**
- **Birthday Emails**: Automatically sent daily at 9:00 AM (configurable)
- **Test Email**: Go to **Tools → Send Test Email** to test your email configuration

### Birthday Automation

The application automatically checks for birthdays every day at 9:00 AM and sends personalized birthday emails.

- **Manual Check**: Go to **Tools → Check Birthdays Now** to trigger an immediate check
- **Configure Time**: Edit `config.json` to change the check time

### Database Backup

#### Manual Backup
1. Go to **File → Backup Database**
2. Choose a location to save the backup file
3. The entire database is saved as a single `.db` file

#### Restore from Backup
1. Go to **File → Restore Database**
2. Select the backup file
3. Confirm the restoration (this will replace your current database)

#### Automatic Backup
Simply copy the `customers.db` file to your backup location (USB drive, cloud storage, etc.)

## File Structure

```
CRM/
├── .github/
│   └── workflows/
│       └── build.yml          # GitHub Actions build workflow
├── crm_app.py              # Main application entry point
├── crm_app.exe             # Standalone executable (if built)
├── database.py             # Database operations
├── email_handler.py        # Email functionality
├── birthday_scheduler.py   # Birthday automation
├── gui.py                  # User interface
├── utils.py                # Utility functions
├── requirements.txt        # Python dependencies
├── build_exe.py            # Windows build script
├── .gitignore              # Git ignore rules
├── config.json             # Application configuration (created on first run)
├── customers.db            # Customer database (created on first run)
├── README.md               # This file
└── RELEASE.md              # Release instructions
```

## Configuration

The `config.json` file stores application settings:

```json
{
    "email": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your-email@gmail.com",
        "password": "encrypted_password",
        "provider": "Gmail"
    },
    "birthday_scheduler": {
        "enabled": true,
        "check_time": "09:00"
    },
    "database": {
        "path": "customers.db",
        "backup_folder": "backups"
    }
}
```

## Troubleshooting

### Email Not Sending

1. **Check your email settings** in Tools → Email Settings
2. **Test the connection** using the Test Connection button
3. **For Gmail**: Make sure you're using an App Password, not your regular password
4. **Check your internet connection**

### Birthday Emails Not Sending Automatically

1. **Keep the application running** - it needs to be open to send scheduled emails
2. **Check the scheduler status** in the bottom-right of the window
3. **Verify email settings** are configured correctly
4. **Try a manual check** using Tools → Check Birthdays Now

### Database Issues

1. **Backup your database** regularly using File → Backup Database
2. **If corrupted**: Restore from a backup using File → Restore Database
3. **Database location**: The `customers.db` file is in the same folder as the application

## Building Executables

### Automated Builds (Recommended)

The easiest way to build executables for both Windows and macOS is using **GitHub Actions**:

1. **Push your code** to GitHub
2. **Create a version tag**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. **Download builds** from the GitHub Releases page

GitHub Actions will automatically build:
- **Windows**: `CRM.exe`
- **macOS**: `CRM.app` and `CRM.dmg`

See [RELEASE.md](RELEASE.md) for detailed instructions.

### Manual Builds

#### Windows
```bash
pip install pyinstaller
python build_exe.py
```

#### macOS
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name=CRM \
  --add-data="README.md:." \
  --hidden-import=tkcalendar \
  --hidden-import=babel.numbers \
  --collect-all=tkcalendar \
  --noconfirm crm_app.py
```

The executables will be created in the `dist` folder.

**Note**: You must build on the target platform (Windows builds on Windows, macOS builds on Mac).

## Support

For issues or questions, please refer to this README or check the application's Help → About menu.

## License

This application is provided as-is for personal and commercial use.

---

**Version**: 1.0  
**Last Updated**: January 2026
