"""
CRM Application - Main Entry Point
Customer Relationship Manager with automated birthday emails
"""

import os
import sys
from database import Database
from email_handler import EmailHandler
from birthday_scheduler import BirthdayScheduler
from utils import ConfigManager
from gui import CRMApp


VERSION = "1.1.0"

def main():
    """Main application entry point"""
    # Check for command line arguments
    if "--version" in sys.argv:
        print(f"CRM Application Version {VERSION}")
        return

    print(f"Starting CRM Application v{VERSION}...")
    
    # Initialize configuration
    config = ConfigManager("config.json")
    
    # Initialize database
    db_path = config.get("database.path", "customers.db")
    db = Database(db_path)
    print(f"[OK] Database initialized: {db_path}")
    
    # Initialize email handler
    email = EmailHandler(
        smtp_server=config.get("email.smtp_server"),
        smtp_port=config.get("email.smtp_port"),
        username=config.get("email.username"),
        password=config.decrypt(config.get("email.password", ""))
    )
    print("[OK] Email handler initialized")
    
    # Initialize birthday scheduler
    scheduler = BirthdayScheduler(
        database=db,
        email_handler=email,
        check_time=config.get("birthday_scheduler.check_time", "09:00"),
        config_manager=config
    )
    
    if config.get("birthday_scheduler.enabled", True):
        scheduler.enable()
    else:
        scheduler.disable()
    
    print(f"[OK] Birthday scheduler initialized (Check time: {scheduler.check_time})")
    
    # Create and run GUI
    print("[OK] Launching GUI...")
    app = CRMApp(db, email, scheduler, config)
    
    # Check for expiring mandates on startup
    app.check_expiring_mandates_startup()
    
    app.run()
    
    print("Application closed")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
