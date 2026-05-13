"""
GUI module for CRM Application
Tkinter-based graphical user interface
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
from tkcalendar import DateEntry
from datetime import datetime
from typing import Optional
import threading
import sv_ttk


class CRMApp:
    def __init__(self, database, email_handler, scheduler, config_manager):
        """Initialize the CRM application GUI"""
        self.db = database
        self.email = email_handler
        self.scheduler = scheduler
        self.config = config_manager
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("CRM - Customer Relationship Manager")
        self.root.geometry(self.config.get("ui.window_size", "1000x700"))
        
        # Configure style
        self.setup_styles()
        
        # Current customer selection
        self.selected_customer_id = None
        self.current_customer_id = None
        
        # Create UI
        self.create_menu()
        self.create_main_layout()
        
        # Load initial data
        self.refresh_customer_list()
        
        # Start birthday scheduler and register alert callback
        self.scheduler.on_birthdays_found = self._on_birthday_alert
        self.scheduler.start()
        
        # Check birthdays on startup (runs once per day)
        self.root.after(1500, self._run_startup_birthday_check)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Configure ttk styles"""
        # Apply the Sun Valley theme (Dark mode)
        sv_ttk.set_theme("dark")
        
        style = ttk.Style()
        # Custom styles
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
    
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Backup Database", command=self.backup_database)
        file_menu.add_command(label="Restore Database", command=self.restore_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Email Settings", command=self.show_email_settings)
        tools_menu.add_command(label="Send Test Email", command=self.send_test_email)
        tools_menu.add_separator()
        tools_menu.add_command(label="🎂 Check Today's Birthdays", command=self.manual_birthday_check)
        tools_menu.add_separator()
        tools_menu.add_command(label="Check Mandates", command=self.manual_mandate_check)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_main_layout(self):
        """Create main application layout"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Left panel - Customer list
        self.create_customer_list_panel(main_frame)
        
        # Right panel - Customer details
        self.create_customer_details_panel(main_frame)
        
        # Bottom panel - Status bar
        self.create_status_bar(main_frame)
    
    def create_customer_list_panel(self, parent):
        """Create customer list panel"""
        list_frame = ttk.Frame(parent, padding="5")
        list_frame.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        ttk.Label(list_frame, text="Customers", style="Title.TLabel").pack(pady=5)
        
        # Search bar
        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill=tk.X, pady=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.search_customers())
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Customer list
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        self.customer_tree = ttk.Treeview(list_container, columns=("FirstName", "Surname", "Email", "Mandate", "Expiry"), 
                                         show="tree headings", yscrollcommand=scrollbar.set)
        self.customer_tree.heading("FirstName", text="First Name")
        self.customer_tree.heading("Surname", text="Surname")
        self.customer_tree.heading("Email", text="Email")
        self.customer_tree.heading("Mandate", text="Mandate")
        self.customer_tree.heading("Expiry", text="Expiry")
        self.customer_tree.column("#0", width=0, stretch=False)
        self.customer_tree.column("FirstName", width=100)
        self.customer_tree.column("Surname", width=100)
        self.customer_tree.column("Email", width=200)
        self.customer_tree.column("Mandate", width=60)
        self.customer_tree.column("Expiry", width=80)
        
        self.customer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.customer_tree.yview)
        
        # Bind selection
        self.customer_tree.bind("<<TreeviewSelect>>", self.on_customer_select)
        
        # Buttons
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="➕ Add Customer", command=self.add_customer).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🗑️ Delete", command=self.delete_customer).pack(side=tk.LEFT, padx=2)
    
    def create_customer_details_panel(self, parent):
        """Create customer details panel"""
        details_frame = ttk.Frame(parent, padding="5")
        details_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        details_frame.columnconfigure(1, weight=1)
        
        # Title
        ttk.Label(details_frame, text="Customer Details", style="Title.TLabel").grid(row=0, column=0, columnspan=2, pady=5)
        
        # Form fields
        row = 1
        
        # First Name
        ttk.Label(details_frame, text="First Name:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.first_name_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.first_name_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        row += 1
        
        # Surname
        ttk.Label(details_frame, text="Surname:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.surname_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.surname_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        row += 1
        
        # Email
        ttk.Label(details_frame, text="Email:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.email_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.email_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        row += 1
        
        # Birthday
        ttk.Label(details_frame, text="Birthday:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.birthday_entry = DateEntry(details_frame, width=37, background='darkblue',
                                       foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.birthday_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        row += 1
        
        # Phone
        ttk.Label(details_frame, text="Phone:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.phone_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.phone_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        row += 1
        
        # Notes
        ttk.Label(details_frame, text="Notes:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=5, padx=5)
        self.notes_text = tk.Text(details_frame, width=40, height=8, wrap=tk.WORD)
        self.notes_text.grid(row=row, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        details_frame.rowconfigure(row, weight=1)
        row += 1
        ttk.Label(details_frame, text="Notes:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=5, padx=5)
        self.notes_text = tk.Text(details_frame, width=40, height=8, wrap=tk.WORD)
        self.notes_text.grid(row=row, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        details_frame.rowconfigure(row, weight=1)
        row += 1
        
        # Properties Section
        ttk.Label(details_frame, text="Properties:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=(10, 5), padx=5)
        row += 1
        
        prop_container = ttk.Frame(details_frame)
        prop_container.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        
        prop_columns = ("ERF", "Type", "Mandate", "Expiry")
        self.property_tree = ttk.Treeview(prop_container, columns=prop_columns, show="headings", height=4)
        self.property_tree.heading("ERF", text="ERF Number")
        self.property_tree.heading("Type", text="Land Type")
        self.property_tree.heading("Mandate", text="Mandate")
        self.property_tree.heading("Expiry", text="Expiry")
        self.property_tree.column("ERF", width=100)
        self.property_tree.column("Type", width=100)
        self.property_tree.column("Mandate", width=80)
        self.property_tree.column("Expiry", width=100)
        
        prop_scroll = ttk.Scrollbar(prop_container, orient=tk.VERTICAL, command=self.property_tree.yview)
        self.property_tree.configure(yscrollcommand=prop_scroll.set)
        
        self.property_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        prop_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        row += 1
        
        prop_btn_frame = ttk.Frame(details_frame)
        prop_btn_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        
        self.add_prop_btn = ttk.Button(prop_btn_frame, text="➕ Add Property", command=self.manual_add_property)
        self.add_prop_btn.pack(side=tk.LEFT, padx=2)
        self.remove_prop_btn = ttk.Button(prop_btn_frame, text="🗑️ Remove Property", command=self.manual_remove_property)
        self.remove_prop_btn.pack(side=tk.LEFT, padx=2)
        
        # Set buttons state initially (disabled until a customer is selected)
        self.add_prop_btn.config(state=tk.DISABLED)
        self.remove_prop_btn.config(state=tk.DISABLED)
        row += 1
        
        # Buttons
        button_frame = ttk.Frame(details_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="💾 Save", command=self.save_customer).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Clear", command=self.clear_form).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📧 Send Email", command=self.send_email_to_customer).pack(side=tk.LEFT, padx=5)
    
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent, relief=tk.SUNKEN, padding="2")
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # Birthday scheduler status
        self.scheduler_status_var = tk.StringVar()
        self.update_scheduler_status()
        ttk.Label(status_frame, textvariable=self.scheduler_status_var).pack(side=tk.RIGHT)
    
    def refresh_customer_list(self, customers=None):
        """Refresh the customer list"""
        # Clear existing items
        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)
        
        # Get customers
        if customers is None:
            customers = self.db.get_all_customers()
        
        # Add to tree
        for customer in customers:
             # Use proper fields with fallback for backward compatibility if needed (schema migration handles it though)
            first = customer.get('first_name', '')
            sur = customer.get('surname', '')
            mandate_status = "Active" if customer.get('mandate') else "Inactive"
            expiry = customer.get('mandate_expiry', '') if customer.get('mandate') else ""
            
            self.customer_tree.insert("", tk.END, iid=customer['id'],
                                     values=(first, sur, customer['email'], mandate_status, expiry))
        
        self.set_status(f"Loaded {len(customers)} customer(s)")
    
    def search_customers(self):
        """Search customers based on search term"""
        query = self.search_var.get().strip()
        
        if query:
            customers = self.db.search_customers(query)
        else:
            customers = self.db.get_all_customers()
        
        self.refresh_customer_list(customers)
    
    def on_customer_select(self, event):
        """Handle customer selection"""
        selection = self.customer_tree.selection()
        if not selection:
            return
        
        customer_id = int(selection[0])
        customer = self.db.get_customer(customer_id)
        
        if customer:
            self.selected_customer_id = customer_id
            self.load_customer_to_form(customer)
    
    def load_customer_to_form(self, customer):
        """Load customer data into form"""
        self.first_name_var.set(customer.get('first_name', ''))
        self.surname_var.set(customer.get('surname', ''))
        self.email_var.set(customer['email'])
        self.phone_var.set(customer['phone'] or "")
        
        if customer['birthday']:
            try:
                self.birthday_entry.set_date(datetime.strptime(customer['birthday'], "%Y-%m-%d"))
            except:
                pass
        
        self.notes_text.delete("1.0", tk.END)
        if customer['notes']:
            self.notes_text.insert("1.0", customer['notes'])
        
        # Load Properties
        self.current_customer_id = customer['id']
        self.refresh_property_list()
        
        # Enable property buttons
        self.add_prop_btn.config(state=tk.NORMAL)
        self.remove_prop_btn.config(state=tk.NORMAL)
    
    def clear_form(self):
        """Clear the customer form"""
        self.selected_customer_id = None
        self.first_name_var.set("")
        self.surname_var.set("")
        self.email_var.set("")
        self.phone_var.set("")
        self.birthday_entry.set_date(datetime.now())
        self.notes_text.delete("1.0", tk.END)
        
        # Properties
        for item in self.property_tree.get_children():
            self.property_tree.delete(item)
        
        self.current_customer_id = None
        self.add_prop_btn.config(state=tk.DISABLED)
        self.remove_prop_btn.config(state=tk.DISABLED)
        
        self.set_status("Form cleared")
    
    def add_customer(self):
        """Prepare form for adding new customer"""
        self.clear_form()
        self.set_status("Enter new customer details")
    
    def save_customer(self):
        """Save customer (add or update)"""
        # Validate
        first_name = self.first_name_var.get().strip()
        surname = self.surname_var.get().strip()
        email = self.email_var.get().strip()
        
        if not first_name:
            messagebox.showerror("Error", "First Name is required")
            return
            
        if not surname:
            messagebox.showerror("Error", "Surname is required")
            return
        
        if not email:
            messagebox.showerror("Error", "Email is required")
            return
        
        if not self.email.validate_email(email):
            messagebox.showerror("Error", "Invalid email address")
            return
        
        # Get form data
        birthday = self.birthday_entry.get_date().strftime("%Y-%m-%d")
        phone = self.phone_var.get().strip()
        notes = self.notes_text.get("1.0", tk.END).strip()
        
        try:
            if self.selected_customer_id:
                # Update existing
                self.db.update_customer(self.selected_customer_id, first_name=first_name, surname=surname, 
                                      email=email, birthday=birthday, phone=phone, notes=notes)
                messagebox.showinfo("Success", "Customer updated successfully")
                self.set_status(f"Updated: {first_name} {surname}")
            else:
                # Add new
                customer_id = self.db.add_customer(first_name, surname, email, birthday, phone, notes)
                self.selected_customer_id = customer_id
                messagebox.showinfo("Success", "Customer added successfully")
                self.set_status(f"Added: {first_name} {surname}")
            
            self.refresh_customer_list()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
    
    def delete_customer(self):
        """Delete selected customer"""
        if not self.selected_customer_id:
            messagebox.showwarning("Warning", "Please select a customer to delete")
            return
        
        customer = self.db.get_customer(self.selected_customer_id)
        if not customer:
            return
        
        if messagebox.askyesno("Confirm Delete", 
                              f"Are you sure you want to delete {customer['first_name']} {customer['surname']}?"):
            self.db.delete_customer(self.selected_customer_id)
            self.clear_form()
            self.refresh_customer_list()
            self.set_status(f"Deleted: {customer['first_name']} {customer['surname']}")
    
    def send_email_to_customer(self):
        """Send email to selected customer"""
        if not self.selected_customer_id:
            messagebox.showwarning("Warning", "Please select a customer")
            return
        
        customer = self.db.get_customer(self.selected_customer_id)
        if not customer:
            return
        
        # Show email composer dialog
        self.show_email_composer(customer)
    
    def show_email_composer(self, customer):
        """Show email composer window"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Send Email to {customer['name']}")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Subject
        ttk.Label(dialog, text="Subject:").pack(pady=5, padx=10, anchor=tk.W)
        subject_var = tk.StringVar(value=f"Hello {customer['first_name']}")
        ttk.Entry(dialog, textvariable=subject_var, width=70).pack(pady=5, padx=10, fill=tk.X)
        
        # Body
        ttk.Label(dialog, text="Message:").pack(pady=5, padx=10, anchor=tk.W)
        body_text = tk.Text(dialog, width=70, height=15, wrap=tk.WORD)
        body_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        body_text.insert("1.0", f"Dear {customer['first_name']},\n\n")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def send():
            subject = subject_var.get().strip()
            body = body_text.get("1.0", tk.END).strip()
            
            if not subject or not body:
                messagebox.showerror("Error", "Subject and message are required")
                return
            
            success, message = self.email.send_email(customer['email'], subject, body)
            
            if success:
                messagebox.showinfo("Success", message)
                dialog.destroy()
            else:
                messagebox.showerror("Error", message)
        
        ttk.Button(button_frame, text="Send", command=send).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_email_settings(self):
        """Show email settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Email Settings")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Provider selection
        ttk.Label(dialog, text="Email Provider:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=10)
        
        providers = list(self.email.get_common_smtp_settings().keys())
        provider_var = tk.StringVar(value=self.config.get("email.provider", "Gmail"))
        provider_combo = ttk.Combobox(dialog, textvariable=provider_var, values=providers, state="readonly")
        provider_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        
        # SMTP Server
        ttk.Label(dialog, text="SMTP Server:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=10)
        server_var = tk.StringVar(value=self.config.get("email.smtp_server", ""))
        ttk.Entry(dialog, textvariable=server_var, width=40).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        
        # SMTP Port
        ttk.Label(dialog, text="SMTP Port:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=10)
        port_var = tk.StringVar(value=str(self.config.get("email.smtp_port", 587)))
        ttk.Entry(dialog, textvariable=port_var, width=40).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        
        # Username
        ttk.Label(dialog, text="Email:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=10)
        username_var = tk.StringVar(value=self.config.get("email.username", ""))
        ttk.Entry(dialog, textvariable=username_var, width=40).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        
        # Password
        ttk.Label(dialog, text="Password:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=10)
        password_var = tk.StringVar(value=self.config.decrypt(self.config.get("email.password", "")))
        ttk.Entry(dialog, textvariable=password_var, width=40, show="*").grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        
        # Provider note
        note_label = ttk.Label(dialog, text="", wraplength=450, foreground="blue")
        note_label.grid(row=5, column=0, columnspan=2, pady=10, padx=10)
        
        def update_provider_info(*args):
            provider = provider_var.get()
            settings = self.email.get_common_smtp_settings().get(provider, {})
            if settings.get("server"):
                server_var.set(settings["server"])
                port_var.set(str(settings["port"]))
            note_label.config(text=settings.get("note", ""))
        
        provider_combo.bind("<<ComboboxSelected>>", update_provider_info)
        update_provider_info()
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        def test_connection():
            # Temporarily configure email handler
            temp_email = self.email
            temp_email.configure(server_var.get(), int(port_var.get()), 
                               username_var.get(), password_var.get())
            success, message = temp_email.test_connection()
            
            if success:
                messagebox.showinfo("Success", message)
            else:
                messagebox.showerror("Error", message)
        
        def save_settings():
            # Save to config
            self.config.set("email.provider", provider_var.get())
            self.config.set("email.smtp_server", server_var.get())
            self.config.set("email.smtp_port", int(port_var.get()))
            self.config.set("email.username", username_var.get())
            self.config.set("email.password", self.config.encrypt(password_var.get()))
            
            # Update email handler
            self.email.configure(server_var.get(), int(port_var.get()),
                               username_var.get(), password_var.get())
            
            messagebox.showinfo("Success", "Email settings saved")
            dialog.destroy()
        
        ttk.Button(button_frame, text="Test Connection", command=test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        dialog.columnconfigure(1, weight=1)
    
    def send_test_email(self):
        """Send a test email"""
        email_address = tk.simpledialog.askstring("Test Email", "Enter email address:")
        if email_address:
            success, message = self.email.send_email(
                email_address,
                "CRM Test Email",
                "This is a test email from your CRM application. If you received this, your email settings are working correctly!"
            )
            
            if success:
                messagebox.showinfo("Success", message)
            else:
                messagebox.showerror("Error", message)
    
    def show_birthday_template_editor(self):
        """Show dialog to edit birthday email template"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Birthday Template")
        dialog.geometry("600x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 200, self.root.winfo_rooty() + 100))
        
        ttk.Label(dialog, text="Birthday Message Template", style="Title.TLabel").pack(pady=10)
        ttk.Label(dialog, text="Use {name} as a placeholder for the customer's name.", style="Subtitle.TLabel").pack(pady=5)
        
        template_text = tk.Text(dialog, width=70, height=12, wrap=tk.WORD, font=("Arial", 10))
        template_text.pack(pady=10, padx=15, fill=tk.BOTH, expand=True)
        
        current_template = self.config.get("birthday_scheduler.template", "")
        template_text.insert("1.0", current_template)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)
        
        def save():
            new_template = template_text.get("1.0", tk.END).strip()
            if not new_template:
                messagebox.showerror("Error", "Template cannot be empty")
                return
            
            self.config.set("birthday_scheduler.template", new_template)
            messagebox.showinfo("Success", "Birthday template saved successfully!")
            dialog.destroy()
            
        ttk.Button(button_frame, text="💾 Save Template", command=save).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _run_startup_birthday_check(self):
        """Run birthday check once on startup (non-blocking)"""
        threading.Thread(
            target=self.scheduler.check_birthdays_today,
            daemon=True
        ).start()

    def _on_birthday_alert(self, customers: list):
        """Called by scheduler (background thread) when birthdays are found today."""
        # Marshal to main thread
        self.root.after(0, lambda: self.show_birthday_alert_dialog(customers))

    def manual_birthday_check(self):
        """Manually trigger today's birthday check and show the alert dialog"""
        customers = self.scheduler.get_todays_birthdays()
        if not customers:
            messagebox.showinfo("Birthday Check", "No birthdays today. 🎂")
            return
        self.show_birthday_alert_dialog(customers)

    def show_birthday_alert_dialog(self, customers: list):
        """Show a birthday alert dialog listing each person, with a Compose Email button."""
        dialog = tk.Toplevel(self.root)
        dialog.title("🎂 Birthday Alerts")
        dialog.geometry("480x400")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)
        
        # Centre on screen
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 150,
            self.root.winfo_rooty() + 80
        ))

        # Header
        header_frame = ttk.Frame(dialog, padding="10 10 10 0")
        header_frame.pack(fill=tk.X)
        ttk.Label(
            header_frame,
            text=f"🎂  {len(customers)} Birthday{'s' if len(customers) != 1 else ''} Today!",
            style="Title.TLabel"
        ).pack(anchor=tk.W)
        ttk.Label(
            header_frame,
            text="Choose who to email and personalise each message before sending.",
            style="Subtitle.TLabel",
            foreground="#555"
        ).pack(anchor=tk.W, pady=(2, 8))
        ttk.Separator(dialog, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)

        # Scrollable list of people
        canvas_frame = ttk.Frame(dialog, padding="10 5")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for customer in customers:
            first = customer.get('first_name', '')
            sur = customer.get('surname', '')
            email_addr = customer.get('email', 'No email')
            full_name = f"{first} {sur}".strip()

            row = ttk.Frame(inner, padding="5 6")
            row.pack(fill=tk.X, pady=2)

            # Name + email info
            info_frame = ttk.Frame(row)
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Label(info_frame, text=f"🎂  {full_name}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
            ttk.Label(info_frame, text=email_addr, foreground="#555", font=("Arial", 9)).pack(anchor=tk.W)

            # Compose button (capture customer in default arg)
            ttk.Button(
                row,
                text="✉ Compose Email",
                command=lambda c=customer: self._open_birthday_composer(c)
            ).pack(side=tk.RIGHT, padx=5)

            ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=2)

        # Footer
        ttk.Separator(dialog, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def _open_birthday_composer(self, customer):
        """Open the email composer pre-populated with a birthday greeting."""
        first_name = customer.get('first_name', 'there')
        surname = customer.get('surname', '')
        full_name = f"{first_name} {surname}".strip()
        email_addr = customer.get('email', '')

        dialog = tk.Toplevel(self.root)
        dialog.title(f"🎂 Birthday Email — {full_name}")
        dialog.geometry("620x520")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text=f"To: {full_name} <{email_addr}>",
                  foreground="#444").pack(pady=(12, 2), padx=15, anchor=tk.W)

        ttk.Label(dialog, text="Subject:").pack(pady=(8, 2), padx=15, anchor=tk.W)
        subject_var = tk.StringVar(value=f"Happy Birthday, {first_name}! 🎂")
        ttk.Entry(dialog, textvariable=subject_var, width=75).pack(pady=(0, 8), padx=15, fill=tk.X)

        ttk.Label(dialog, text="Message:").pack(pady=(0, 2), padx=15, anchor=tk.W)
        body_text = tk.Text(dialog, width=75, height=16, wrap=tk.WORD, font=("Arial", 10))
        body_text.pack(pady=(0, 8), padx=15, fill=tk.BOTH, expand=True)

        # Pre-populate with a simple, editable greeting
        default_body = (
            f"Dear {first_name},\n\n"
            f"Wishing you a very happy birthday! 🎉\n\n"
            f"Best regards,"
        )
        body_text.insert("1.0", default_body)

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        def send():
            subject = subject_var.get().strip()
            body = body_text.get("1.0", tk.END).strip()
            if not subject or not body:
                messagebox.showerror("Error", "Subject and message are required")
                return
            success, message = self.email.send_email(email_addr, subject, body)
            if success:
                messagebox.showinfo("Sent", f"Birthday email sent to {full_name}!")
                dialog.destroy()
            else:
                messagebox.showerror("Error", message)

        ttk.Button(button_frame, text="📤 Send", command=send).pack(side=tk.LEFT, padx=8)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=8)

    def check_expiring_mandates_startup(self):
        """Check for expiring mandates on startup and notify if found"""
        expiring = self.db.get_expiring_mandates(2) # 2 months
        if expiring:
            msg = f"Attention: {len(expiring)} property mandate(s) are expiring within the next 2 months:\n\n"
            for p in expiring:
                msg += f"• {p['first_name']} {p['surname']} - ERF: {p['erf_number']} (Expires: {p['mandate_expiry']})\n"
            msg += "\nWould you like to view the mandate management tool?"
            
            if messagebox.askyesno("Expiring Mandates", msg):
                self.manual_mandate_check()

    def manual_mandate_check(self):
        """Show mandate management dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Mandate Management")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Active & Expiring Mandates", style="Title.TLabel").pack(pady=10)
        
        # Container for the list
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for mandates
        columns = ("Name", "ERF", "Expiry", "Status")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        tree.heading("Name", text="Customer Name")
        tree.heading("ERF", text="ERF Number")
        tree.heading("Expiry", text="Expiry Date")
        tree.heading("Status", text="Status")
        
        tree.column("Name", width=150)
        tree.column("ERF", width=100)
        tree.column("Expiry", width=100)
        tree.column("Status", width=100)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load data
        all_active = self.db.get_valid_mandates()
        # Use property IDs to identify expiring ones
        expiring_props = self.db.get_expiring_mandates(2)
        expiring_ids = [p['id'] for p in expiring_props]
        
        for p in all_active:
            name = f"{p['first_name']} {p['surname']}"
            erf = p['erf_number']
            expiry = p['mandate_expiry'] or "N/A"
            status = "Expiring Soon!" if p['id'] in expiring_ids else "Valid"
            
            item = tree.insert("", tk.END, values=(name, erf, expiry, status))
            if p['id'] in expiring_ids:
                tree.item(item, tags=('expiring',))
        
        tree.tag_configure('expiring', foreground='red')
        
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def backup_database(self):
        """Backup database"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")],
            initialfile=f"crm_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        
        if filename:
            if self.db.backup_database(filename):
                messagebox.showinfo("Success", f"Database backed up to:\n{filename}")
            else:
                messagebox.showerror("Error", "Backup failed")
    
    def restore_database(self):
        """Restore database from backup"""
        filename = filedialog.askopenfilename(
            filetypes=[("Database files", "*.db"), ("All files", "*.*")]
        )
        
        if filename:
            if messagebox.askyesno("Confirm Restore", 
                                  "This will replace your current database. Continue?"):
                if self.db.restore_database(filename):
                    messagebox.showinfo("Success", "Database restored successfully")
                    self.refresh_customer_list()
                else:
                    messagebox.showerror("Error", "Restore failed")
    
    def update_scheduler_status(self):
        """Update scheduler status in status bar"""
        if self.scheduler.enabled:
            status = f"🎂 Birthday alerts: ON (Check at {self.scheduler.check_time})"
        else:
            status = "🎂 Birthday alerts: OFF"
        
        self.scheduler_status_var.set(status)
        
        # Schedule next update
        self.root.after(5000, self.update_scheduler_status)
    
    def set_status(self, message):
        """Set status bar message"""
        self.status_var.set(message)
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About CRM", 
                          "Customer Relationship Manager\n\n"
                          "Version 1.0\n\n"
                          "A simple CRM application with automated birthday emails.\n\n"
                          "Features:\n"
                          "• Customer management\n"
                          "• Email sending\n"
                          "• Automated birthday reminders\n"
                          "• Database backup/restore")
    
    def on_closing(self):
        """Handle window close"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.scheduler.stop()
            self.db.close()
            self.root.destroy()
    
    def refresh_property_list(self):
        """Refresh the property tree for the current customer"""
        for item in self.property_tree.get_children():
            self.property_tree.delete(item)
            
        if self.current_customer_id:
            properties = self.db.get_properties(self.current_customer_id)
            for prop in properties:
                mandate_str = "Yes" if prop['mandate'] else "No"
                expiry_str = prop['mandate_expiry'] if prop['mandate'] and prop['mandate_expiry'] else "-"
                self.property_tree.insert("", tk.END, iid=prop['id'], values=(prop['erf_number'], prop['land_type'], mandate_str, expiry_str))

    def manual_add_property(self):
        """Show dialog to add a property"""
        if not self.current_customer_id:
            messagebox.showwarning("Warning", "Please select a customer first.")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Property")
        dialog.geometry("350x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Form
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="ERF Number:").pack(anchor=tk.W, pady=(0, 5))
        erf_var = tk.StringVar()
        erf_entry = ttk.Entry(main_frame, textvariable=erf_var, width=30)
        erf_entry.pack(fill=tk.X, pady=(0, 15))
        erf_entry.focus_set()
        
        ttk.Label(main_frame, text="Land Type:").pack(anchor=tk.W, pady=(0, 5))
        type_var = tk.StringVar(value="Residential")
        type_combo = ttk.Combobox(main_frame, textvariable=type_var, values=["Vacant", "Residential", "Agricultural", "Industrial"], state="readonly")
        type_combo.pack(fill=tk.X, pady=(0, 15))
        
        # Mandate fields
        mandate_var = tk.IntVar(value=0)
        mandate_cb = ttk.Checkbutton(main_frame, text="Active Mandate", variable=mandate_var)
        mandate_cb.pack(anchor=tk.W, pady=(0, 5))
        
        ttk.Label(main_frame, text="Mandate Expiry:").pack(anchor=tk.W, pady=(0, 5))
        expiry_entry = DateEntry(main_frame, width=30, background='darkgreen',
                                foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        expiry_entry.pack(fill=tk.X, pady=(0, 20))
        
        def save():
            erf = erf_var.get().strip()
            land_type = type_var.get()
            mandate = mandate_var.get()
            expiry = expiry_entry.get_date().strftime("%Y-%m-%d") if mandate else ""
            
            if not erf:
                messagebox.showerror("Error", "ERF Number is required.")
                return
                
            try:
                self.db.add_property(self.current_customer_id, erf, land_type, mandate, expiry)
                self.refresh_property_list()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add property: {e}")
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)

    def manual_remove_property(self):
        """Remove selected property"""
        selected = self.property_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a property to remove.")
            return
            
        if messagebox.askyesno("Confirm", "Are you sure you want to remove this property?"):
            for item_id in selected:
                prop_id = int(item_id)
                self.db.delete_property(prop_id)
            self.refresh_property_list()

    def run(self):
        """Start the application"""
        self.root.mainloop()


if __name__ == "__main__":
    # This file should be run from crm_app.py
    print("Please run crm_app.py to start the application")
