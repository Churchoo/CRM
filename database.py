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
        """Create database tables if they don't exist and perform migrations"""
        # Check if table exists
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        table_exists = self.cursor.fetchone()
        
        if not table_exists:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    surname TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    birthday TEXT,
                    phone TEXT,
                    notes TEXT,
                    created_date TEXT NOT NULL,
                    modified_date TEXT NOT NULL
                )
            ''')
            self.conn.commit()
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    erf_number TEXT NOT NULL,
                    land_type TEXT NOT NULL,
                    mandate INTEGER DEFAULT 0,
                    mandate_expiry TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
                )
            ''')
            self.conn.commit()
        else:
            self._migrate_schema()

    def _migrate_schema(self):
        """Migrate schema if necessary"""
        self.cursor.execute("PRAGMA table_info(customers)")
        columns = [row[1] for row in self.cursor.fetchall()]
        
        # Check if we need to split 'name' into 'first_name' and 'surname'
        if 'name' in columns and 'first_name' not in columns:
            print("Migrating database: Splitting 'name' into 'first_name' and 'surname'...")
            
            # 1. Rename old table
            self.cursor.execute("ALTER TABLE customers RENAME TO customers_old")
            
            # 2. Create new table with new schema
            self.cursor.execute('''
                CREATE TABLE customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    surname TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    birthday TEXT,
                    phone TEXT,
                    notes TEXT,
                    created_date TEXT NOT NULL,
                    modified_date TEXT NOT NULL
                )
            ''')
            
            # 3. Copy data and split names
            self.cursor.execute("SELECT * FROM customers_old")
            old_rows = self.cursor.fetchall()
            
            for row in old_rows:
                old_data = dict(row)
                full_name = old_data['name'].strip()
                
                # Split name: "John Doe" -> "John", "Doe" | "John" -> "John", ""
                parts = full_name.split(' ', 1)
                first_name = parts[0]
                surname = parts[1] if len(parts) > 1 else ""
                
                self.cursor.execute('''
                    INSERT INTO customers (id, first_name, surname, email, birthday, phone, notes, created_date, modified_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (old_data['id'], first_name, surname, old_data['email'], 
                      old_data.get('birthday'), old_data.get('phone'), old_data.get('notes'), 
                      old_data['created_date'], old_data['modified_date']))
            
            # 4. Drop old table
            self.cursor.execute("DROP TABLE customers_old")
            self.conn.commit()
            print("Migration complete!")
            
        # Ensure mandate columns exist (for cases where first_name already existed but mandate didn't)
        self.cursor.execute("PRAGMA table_info(customers)")
        columns = [row[1] for row in self.cursor.fetchall()]
        if 'mandate' in columns:
            print("Cleaning up legacy mandate columns from customers table...")
            # We already handle splitting name, if we are here and 'mandate' is in columns, we should move it to properties
            # but usually this migration happens after name split. 
            # In a real app we'd do a complex migration. For now we will ensure properties has the columns.
            pass
            
        # Ensure properties table exists with mandate columns
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='properties'")
        if self.cursor.fetchone():
            self.cursor.execute("PRAGMA table_info(properties)")
            prop_columns = [row[1] for row in self.cursor.fetchall()]
            if 'mandate' not in prop_columns:
                print("Adding mandate columns to properties table...")
                self.cursor.execute("ALTER TABLE properties ADD COLUMN mandate INTEGER DEFAULT 0")
                self.cursor.execute("ALTER TABLE properties ADD COLUMN mandate_expiry TEXT")
                self.conn.commit()
        else:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    erf_number TEXT NOT NULL,
                    land_type TEXT NOT NULL,
                    mandate INTEGER DEFAULT 0,
                    mandate_expiry TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
                )
            ''')
            self.conn.commit()
            
        # Migration: Move mandate data from customers to properties if any exists
        self.cursor.execute("PRAGMA table_info(customers)")
        cust_columns = [row[1] for row in self.cursor.fetchall()]
        if 'mandate' in cust_columns:
            print("Checking for mandate data to migrate from customers to properties...")
            self.cursor.execute("SELECT id, mandate, mandate_expiry FROM customers WHERE mandate = 1")
            legacy_found = self.cursor.fetchall()
            for row in legacy_found:
                cust_id, mandate, expiry = row
                # Check if this customer already has properties
                self.cursor.execute("SELECT id FROM properties WHERE customer_id = ?", (cust_id,))
                prop = self.cursor.fetchone()
                if prop:
                    # Update first property
                    self.cursor.execute("UPDATE properties SET mandate = ?, mandate_expiry = ? WHERE id = ?", (mandate, expiry, prop[0]))
                else:
                    # Create a "Legacy Property" entry
                    self.cursor.execute('''
                        INSERT INTO properties (customer_id, erf_number, land_type, mandate, mandate_expiry)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (cust_id, "LEGACY-MIGRATED", "Other", mandate, expiry))
            
            # We don't drop columns in SQLite easily, but we'll stop using them.
            self.conn.commit()
    
    def add_customer(self, first_name: str, surname: str, email: str, birthday: str = None, 
                    phone: str = None, notes: str = None) -> int:
        """
        Add a new customer to the database
        
        Args:
            first_name: Customer first name
            surname: Customer surname
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
                INSERT INTO customers (first_name, surname, email, birthday, phone, notes, created_date, modified_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (first_name, surname, email, birthday, phone, notes, now, now))
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
        """Get all customers sorted by surname then first name"""
        self.cursor.execute('SELECT * FROM customers ORDER BY surname, first_name')
        return [dict(row) for row in self.cursor.fetchall()]
    
    def update_customer(self, customer_id: int, first_name: str = None, surname: str = None, 
                       email: str = None, birthday: str = None, phone: str = None, 
                       notes: str = None) -> bool:
        """
        Update customer information
        
        Args:
            customer_id: ID of customer to update
            first_name, surname, email, birthday, phone, notes: Fields to update (None = no change)
            
        Returns:
            True if customer was updated, False if not found
        """
        # Get current customer data
        customer = self.get_customer(customer_id)
        if not customer:
            return False
        
        # Update only provided fields
        updated_first_name = first_name if first_name is not None else customer['first_name']
        updated_surname = surname if surname is not None else customer['surname']
        updated_email = email if email is not None else customer['email']
        updated_birthday = birthday if birthday is not None else customer['birthday']
        updated_phone = phone if phone is not None else customer['phone']
        updated_notes = notes if notes is not None else customer['notes']
        modified_date = datetime.now().isoformat()
        
        try:
            self.cursor.execute('''
                UPDATE customers 
                SET first_name = ?, surname = ?, email = ?, birthday = ?, phone = ?, notes = ?, 
                    modified_date = ?
                WHERE id = ?
            ''', (updated_first_name, updated_surname, updated_email, updated_birthday, 
                  updated_phone, updated_notes, modified_date, customer_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            raise ValueError(f"Customer with email '{updated_email}' already exists")
    
    def delete_customer(self, customer_id: int) -> bool:
        """Delete a customer and their properties (CASCADE handles this if PRAGMA foreign_keys=ON)"""
        # Ensure foreign keys are enabled for cascade delete
        self.cursor.execute('PRAGMA foreign_keys = ON')
        self.cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    # Property Methods
    
    def add_property(self, customer_id: int, erf_number: str, land_type: str, mandate: int = 0, mandate_expiry: str = None) -> int:
        """Add a property to a customer"""
        self.cursor.execute('''
            INSERT INTO properties (customer_id, erf_number, land_type, mandate, mandate_expiry)
            VALUES (?, ?, ?, ?, ?)
        ''', (customer_id, erf_number, land_type, mandate, mandate_expiry))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_properties(self, customer_id: int) -> List[Dict]:
        """Get all properties for a customer"""
        self.cursor.execute('SELECT * FROM properties WHERE customer_id = ?', (customer_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def delete_property(self, property_id: int) -> bool:
        """Delete a property by ID"""
        self.cursor.execute('DELETE FROM properties WHERE id = ?', (property_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def search_customers(self, query: str, mandate_status: str = "All", land_type: str = "All") -> List[Dict]:
        """Search customers by name, email, or ERF and filter by mandate status and land type"""
        search_term = f"%{query}%"
        
        sql = '''
            SELECT DISTINCT c.* 
            FROM customers c
            LEFT JOIN properties p ON c.id = p.customer_id
            WHERE (c.first_name LIKE ? OR c.surname LIKE ? OR c.email LIKE ? OR p.erf_number LIKE ?)
        '''
        params = [search_term, search_term, search_term, search_term]
        
        if mandate_status == "Active":
            sql += " AND p.mandate = 1"
        elif mandate_status == "Inactive":
            sql += " AND (p.mandate = 0 OR p.mandate IS NULL)"
            
        if land_type != "All":
            sql += " AND p.land_type = ?"
            params.append(land_type)
            
        sql += " ORDER BY c.surname, c.first_name"
        
        self.cursor.execute(sql, tuple(params))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_valid_mandates(self) -> List[Dict]:
        """Get all properties with an active mandate, including client names"""
        self.cursor.execute('''
            SELECT c.first_name, c.surname, p.* 
            FROM properties p
            JOIN customers c ON p.customer_id = c.id
            WHERE p.mandate = 1 
            ORDER BY c.surname, c.first_name
        ''')
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_expiring_mandates(self, months: int = 2) -> List[Dict]:
        """Get properties whose mandate expires within the next N months, including client names"""
        # Calculate cut-off date
        from datetime import timedelta
        cutoff_date = (datetime.now() + timedelta(days=months*30)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        self.cursor.execute('''
            SELECT c.first_name, c.surname, p.* 
            FROM properties p
            JOIN customers c ON p.customer_id = c.id
            WHERE p.mandate = 1 
            AND p.mandate_expiry IS NOT NULL 
            AND p.mandate_expiry != ''
            AND p.mandate_expiry <= ?
            AND p.mandate_expiry >= ?
            ORDER BY p.mandate_expiry
        ''', (cutoff_date, today))
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
    
    @property
    def name_field(self):
        """Legacy property for backward compatibility if needed, returns full name"""
        return "first_name || ' ' || surname"


# Test function
def test_crud():
    """Test basic CRUD operations"""
    print("Testing Database CRUD operations...")
    
    # Create test database
    db_path = "test_customers.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db = Database(db_path)
    
    # Add customers
    id1 = db.add_customer("John", "Doe", "john@example.com", "1990-05-15", "555-1234", "VIP customer")
    id2 = db.add_customer("Jane", "Smith", "jane@example.com", "1985-03-22", "555-5678")
    print(f"[OK] Added customers with IDs: {id1}, {id2}")
    
    # Get customer
    customer = db.get_customer(id1)
    print(f"[OK] Retrieved customer: {customer['first_name']} {customer['surname']}")
    
    # Update customer
    db.update_customer(id1, phone="555-9999")
    updated = db.get_customer(id1)
    print(f"[OK] Updated phone: {updated['phone']}")
    
    # Search
    results = db.search_customers("John")
    print(f"[OK] Search found {len(results)} customer(s)")
    
    # Get all
    all_customers = db.get_all_customers()
    print(f"[OK] Total customers: {len(all_customers)}")
    
    # Test Properties
    # 3-month expiry test case
    from datetime import timedelta
    three_months = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    one_month = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    prop_id1 = db.add_property(id1, "ERF123", "Residential", 1, one_month)
    prop_id2 = db.add_property(id1, "ERF456", "Vacant", 1, three_months)
    print(f"[OK] Added properties with IDs: {prop_id1}, {prop_id2}")
    
    # Test Mandate Queries
    valid_mandates = db.get_valid_mandates()
    print(f"[OK] Valid mandates found: {len(valid_mandates)}")
    assert len(valid_mandates) == 2
    
    expiring_2m = db.get_expiring_mandates(2)
    print(f"[OK] Expiring mandates (2 months) found: {len(expiring_2m)}")
    assert len(expiring_2m) == 1 # Only one_month
    
    expiring_3m = db.get_expiring_mandates(3)
    print(f"[OK] Expiring mandates (3 months) found: {len(expiring_3m)}")
    assert len(expiring_3m) == 2 # both
    
    props = db.get_properties(id1)
    print(f"[OK] Retrieved {len(props)} properties for customer {id1}")
    assert len(props) == 2
    
    db.delete_property(prop_id2)
    props = db.get_properties(id1)
    print(f"[OK] Total properties after deletion: {len(props)}")
    assert len(props) == 1
    
    # Delete
    db.delete_customer(id2)
    print(f"[OK] Deleted customer {id2}")
    
    # Cleanup
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)
    print("[OK] All tests passed!")


if __name__ == "__main__":
    test_crud()
