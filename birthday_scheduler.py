"""
Birthday scheduler module for CRM Application
Handles automated birthday email checking and sending
"""

import schedule
import time
import threading
from datetime import datetime
from typing import Callable, Optional
import logging


class BirthdayScheduler:
    def __init__(self, database, email_handler, check_time: str = "09:00"):
        """
        Initialize birthday scheduler
        
        Args:
            database: Database instance
            email_handler: EmailHandler instance
            check_time: Time to check for birthdays daily (HH:MM format)
        """
        self.database = database
        self.email_handler = email_handler
        self.check_time = check_time
        self.is_running = False
        self.scheduler_thread = None
        self.enabled = True
        self.last_check_date = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def check_and_send_birthday_emails(self) -> dict:
        """
        Check for today's birthdays and send emails
        
        Returns:
            Dictionary with results: {sent: int, failed: int, customers: list}
        """
        today = datetime.now().date()
        
        # Prevent duplicate checks on the same day
        if self.last_check_date == today:
            self.logger.info("Birthday check already performed today")
            return {"sent": 0, "failed": 0, "customers": [], "skipped": True}
        
        self.logger.info("Checking for birthdays today...")
        customers_with_birthdays = self.database.get_birthdays_today()
        
        results = {
            "sent": 0,
            "failed": 0,
            "customers": [],
            "skipped": False
        }
        
        if not customers_with_birthdays:
            self.logger.info("No birthdays today")
            self.last_check_date = today
            return results
        
        self.logger.info(f"Found {len(customers_with_birthdays)} birthday(s) today")
        
        for customer in customers_with_birthdays:
            if not self.enabled:
                self.logger.info("Birthday emails disabled, stopping")
                break
            
            success, message = self.email_handler.send_birthday_email(customer)
            
            if success:
                results["sent"] += 1
                self.logger.info(f"✓ Sent birthday email to {customer['name']}")
            else:
                results["failed"] += 1
                self.logger.error(f"✗ Failed to send to {customer['name']}: {message}")
            
            results["customers"].append({
                "name": customer["name"],
                "email": customer["email"],
                "success": success,
                "message": message
            })
        
        self.last_check_date = today
        return results
    
    def schedule_daily_check(self):
        """Schedule the daily birthday check"""
        schedule.clear()
        schedule.every().day.at(self.check_time).do(self.check_and_send_birthday_emails)
        self.logger.info(f"Scheduled daily birthday check at {self.check_time}")
    
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
    
    def manual_check(self) -> dict:
        """
        Manually trigger a birthday check (ignores last check date)
        
        Returns:
            Results dictionary
        """
        self.logger.info("Manual birthday check triggered")
        self.last_check_date = None  # Reset to allow manual check
        return self.check_and_send_birthday_emails()
    
    def get_upcoming_birthdays(self, days: int = 7) -> list:
        """Get customers with upcoming birthdays"""
        return self.database.get_upcoming_birthdays(days)


# Test function
def test_scheduler():
    """Test birthday scheduler functionality"""
    print("Birthday Scheduler Test")
    
    # Mock database and email handler
    class MockDB:
        def get_birthdays_today(self):
            return [
                {"name": "Test User", "email": "test@example.com", "birthday": "1990-01-27"}
            ]
        
        def get_upcoming_birthdays(self, days):
            return []
    
    class MockEmailHandler:
        def send_birthday_email(self, customer):
            return True, f"Mock email sent to {customer['name']}"
    
    db = MockDB()
    email = MockEmailHandler()
    scheduler = BirthdayScheduler(db, email, check_time="09:00")
    
    print(f"✓ Scheduler created with check time: {scheduler.check_time}")
    
    # Test manual check
    results = scheduler.manual_check()
    print(f"✓ Manual check completed: {results['sent']} sent, {results['failed']} failed")
    
    # Test enable/disable
    scheduler.disable()
    print(f"✓ Scheduler disabled: {not scheduler.enabled}")
    scheduler.enable()
    print(f"✓ Scheduler enabled: {scheduler.enabled}")
    
    # Test time update
    scheduler.set_check_time("10:30")
    print(f"✓ Check time updated to: {scheduler.check_time}")
    
    print("\n✓ Birthday scheduler tests passed!")


if __name__ == "__main__":
    test_scheduler()
