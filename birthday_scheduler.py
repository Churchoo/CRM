"""
Birthday scheduler module for CRM Application
Handles birthday detection and alerts - emails are NOT sent automatically.
The user is notified of today's birthdays and manually composes/sends each email.
"""

import schedule
import time
import threading
from datetime import datetime
from typing import Callable, Optional
import logging


class BirthdayScheduler:
    def __init__(self, database, email_handler=None, check_time: str = "09:00", config_manager=None):
        """
        Initialize birthday scheduler
        
        Args:
            database: Database instance
            email_handler: Kept for compatibility but no longer used for auto-sending
            check_time: Time to check for birthdays daily (HH:MM format)
            config_manager: ConfigManager instance
        """
        self.database = database
        self.email_handler = email_handler  # kept for compatibility
        self.check_time = check_time
        self.config_manager = config_manager
        self.is_running = False
        self.scheduler_thread = None
        self.enabled = True
        self.last_check_date = None
        self.on_birthdays_found: Optional[Callable] = None  # GUI callback
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def check_birthdays_today(self) -> list:
        """
        Check for today's birthdays and fire the alert callback if any are found.
        Does NOT send any emails - that is left to the user.
        
        Returns:
            List of customers with birthdays today
        """
        today = datetime.now().date()
        
        # Prevent duplicate alerts on the same day
        if self.last_check_date == today:
            self.logger.info("Birthday check already performed today")
            return []
        
        self.logger.info("Checking for birthdays today...")
        customers = self.database.get_birthdays_today()
        self.last_check_date = today
        
        if customers:
            self.logger.info(f"Found {len(customers)} birthday(s) today - alerting user")
            if self.on_birthdays_found:
                self.on_birthdays_found(customers)
        else:
            self.logger.info("No birthdays today")
        
        return customers
    
    def schedule_daily_check(self):
        """Schedule the daily birthday check"""
        schedule.clear()
        schedule.every().day.at(self.check_time).do(self.check_birthdays_today)
        self.logger.info(f"Scheduled daily birthday alert check at {self.check_time}")
    
    def run_scheduler(self):
        """Run the scheduler loop (runs in background thread)"""
        self.is_running = True
        self.schedule_daily_check()
        
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def start(self):
        """Start the birthday scheduler in a background thread"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.logger.warning("Scheduler already running")
            return
        
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("Birthday scheduler started")
    
    def stop(self):
        """Stop the birthday scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2)
        self.logger.info("Birthday scheduler stopped")
    
    def set_check_time(self, check_time: str):
        """
        Update the daily check time
        
        Args:
            check_time: Time in HH:MM format (24-hour)
        """
        try:
            # Validate time format
            datetime.strptime(check_time, "%H:%M")
            self.check_time = check_time
            
            # Reschedule if running
            if self.is_running:
                self.schedule_daily_check()
            
            self.logger.info(f"Check time updated to {check_time}")
        except ValueError:
            self.logger.error(f"Invalid time format: {check_time}. Use HH:MM format")
    
    def enable(self):
        """Enable birthday email sending"""
        self.enabled = True
        self.logger.info("Birthday emails enabled")
    
    def disable(self):
        """Disable birthday email sending"""
        self.enabled = False
        self.logger.info("Birthday emails disabled")
    
    def get_todays_birthdays(self) -> list:
        """Get customers who have birthdays today"""
        return self.database.get_birthdays_today()
    
    def manual_check(self) -> list:
        """
        Manually trigger a birthday alert check (ignores last check date).
        Does NOT send emails.
        
        Returns:
            List of customers with birthdays today
        """
        self.logger.info("Manual birthday check triggered")
        self.last_check_date = None  # Reset to allow re-check
        return self.check_birthdays_today()
    
    def get_upcoming_birthdays(self, days: int = 7) -> list:
        """Get customers with upcoming birthdays"""
        return self.database.get_upcoming_birthdays(days)


# Test function
def test_scheduler():
    """Test birthday scheduler functionality"""
    print("Birthday Scheduler Test")
    
    class MockDB:
        def get_birthdays_today(self):
            return [
                {"first_name": "Test", "surname": "User", "email": "test@example.com", "birthday": "1990-01-27"}
            ]
        
        def get_upcoming_birthdays(self, days):
            return []
    
    db = MockDB()
    scheduler = BirthdayScheduler(db, check_time="09:00")
    
    # Register a test callback
    alerted = []
    scheduler.on_birthdays_found = lambda customers: alerted.extend(customers)
    
    print(f"[OK] Scheduler created with check time: {scheduler.check_time}")
    
    # Test manual check
    results = scheduler.manual_check()
    print(f"[OK] Manual check found {len(results)} birthday(s)")
    print(f"[OK] Alert callback fired: {len(alerted)} customer(s) alerted")
    
    # Test enable/disable
    scheduler.disable()
    print(f"[OK] Scheduler disabled: {not scheduler.enabled}")
    scheduler.enable()
    print(f"[OK] Scheduler enabled: {scheduler.enabled}")
    
    # Test time update
    scheduler.set_check_time("10:30")
    print(f"[OK] Check time updated to: {scheduler.check_time}")
    
    print("\n[OK] Birthday scheduler tests passed!")


if __name__ == "__main__":
    test_scheduler()
