"""
Database module for CRM Application
Handles all SQLite database operations for customer management
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class Database:
    def __init__(self, db_path: str = "customers.db"):
        """Initialize database connection and create tables if needed"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self.cursor = self.conn.cursor()
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                birthday TEXT,
                phone TEXT,
                notes TEXT,
                created_date TEXT NOT NULL,
                modified_date TEXT NOT NULL
            )
        ''')
        self.conn.commit()
    
    def add_customer(self, name: str, email: str, birthday: str = None, 
                    phone: str = None, notes: str = None) -> int:
        """
        Add a new customer to the database
        
        Args:
            name: Customer name
            email: Customer email (must be unique)
            birthday: Birthday in YYYY-MM-DD format
            phone: Phone number
            notes: Additional notes
            
        Returns:
            Customer ID of newly created customer
        """
        now = datetime.now().isoformat()
        
        try:
            self.cursor.execute('''
                INSERT INTO customers (name, email, birthday, phone, notes, created_date, modified_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, birthday, phone, notes, now, now))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"Customer with email '{email}' already exists")
    
    def get_customer(self, customer_id: int) -> Optional[Dict]:
        """Get a customer by ID"""
        self.cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_customers(self) -> List[Dict]:
        """Get all customers"""
        self.cursor.execute('SELECT * FROM customers ORDER BY name')
        return [dict(row) for row in self.cursor.fetchall()]
    
    def update_customer(self, customer_id: int, name: str = None, email: str = None,
                       birthday: str = None, phone: str = None, notes: str = None) -> bool:
        """
        Update customer information
        
        Args:
            customer_id: ID of customer to update
            name, email, birthday, phone, notes: Fields to update (None = no change)
            
        Returns:
            True if customer was updated, False if not found
        """
        # Get current customer data
        customer = self.get_customer(customer_id)
        if not customer:
            return False
        
        # Update only provided fields
        updated_name = name if name is not None else customer['name']
        updated_email = email if email is not None else customer['email']
        updated_birthday = birthday if birthday is not None else customer['birthday']
        updated_phone = phone if phone is not None else customer['phone']
        updated_notes = notes if notes is not None else customer['notes']
        modified_date = datetime.now().isoformat()
        
        try:
            self.cursor.execute('''
                UPDATE customers 
                SET name = ?, email = ?, birthday = ?, phone = ?, notes = ?, modified_date = ?
                WHERE id = ?
            ''', (updated_name, updated_email, updated_birthday, updated_phone, 
                  updated_notes, modified_date, customer_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            raise ValueError(f"Customer with email '{updated_email}' already exists")
    
    def delete_customer(self, customer_id: int) -> bool:
        """Delete a customer by ID"""
        self.cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def search_customers(self, query: str) -> List[Dict]:
        """Search customers by name or email"""
        search_term = f"%{query}%"
        self.cursor.execute('''
            SELECT * FROM customers 
            WHERE name LIKE ? OR email LIKE ?
            ORDER BY name
        ''', (search_term, search_term))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_birthdays_today(self) -> List[Dict]:
        """Get customers with birthdays today (MM-DD match)"""
        today = datetime.now().strftime("%m-%d")
        self.cursor.execute('''
            SELECT * FROM customers 
            WHERE substr(birthday, 6, 5) = ?
        ''', (today,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_upcoming_birthdays(self, days: int = 7) -> List[Dict]:
        """Get customers with birthdays in the next N days"""
        from datetime import timedelta
        
        customers = self.get_all_customers()
        upcoming = []
        today = datetime.now()
        
        for customer in customers:
            if customer['birthday']:
                try:
                    # Parse birthday and set to current year
                    bday = datetime.strptime(customer['birthday'], "%Y-%m-%d")
                    bday_this_year = bday.replace(year=today.year)
                    
                    # If birthday already passed this year, check next year
                    if bday_this_year < today:
                        bday_this_year = bday.replace(year=today.year + 1)
                    
                    # Check if within range
                    days_until = (bday_this_year - today).days
                    if 0 <= days_until <= days:
                        customer['days_until_birthday'] = days_until
                        upcoming.append(customer)
                except ValueError:
                    continue
        
        return sorted(upcoming, key=lambda x: x['days_until_birthday'])
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database file"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            import shutil
            self.close()
            shutil.copy2(backup_path, self.db_path)
            self.connect()
            return True
        except Exception as e:
            print(f"Restore failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        """Ensure connection is closed on deletion"""
        self.close()


# Test function
def test_crud():
    """Test basic CRUD operations"""
    print("Testing Database CRUD operations...")
    
    # Create test database
    db = Database("test_customers.db")
    
    # Add customers
    id1 = db.add_customer("John Doe", "john@example.com", "1990-05-15", "555-1234", "VIP customer")
    id2 = db.add_customer("Jane Smith", "jane@example.com", "1985-03-22", "555-5678")
    print(f"✓ Added customers with IDs: {id1}, {id2}")
    
    # Get customer
    customer = db.get_customer(id1)
    print(f"✓ Retrieved customer: {customer['name']}")
    
    # Update customer
    db.update_customer(id1, phone="555-9999")
    updated = db.get_customer(id1)
    print(f"✓ Updated phone: {updated['phone']}")
    
    # Search
    results = db.search_customers("john")
    print(f"✓ Search found {len(results)} customer(s)")
    
    # Get all
    all_customers = db.get_all_customers()
    print(f"✓ Total customers: {len(all_customers)}")
    
    # Delete
    db.delete_customer(id2)
    print(f"✓ Deleted customer {id2}")
    
    # Cleanup
    db.close()
    os.remove("test_customers.db")
    print("✓ All tests passed!")


if __name__ == "__main__":
    test_crud()
