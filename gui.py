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
        
        # Create UI
        self.create_menu()
        self.create_main_layout()
        
        # Load initial data
        self.refresh_customer_list()
        
        # Start birthday scheduler
        self.scheduler.start()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        bg_color = "#f0f0f0"
        fg_color = "#333333"
        accent_color = "#4CAF50"
        
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TButton", background=accent_color, foreground="white")
        style.map("TButton", background=[("active", "#45a049")])
        
        # Custom styles
        style.configure("Title.TLabel", font=("Arial", 16, "bold"))
        style.configure("Subtitle.TLabel", font=("Arial", 10))
    
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
        tools_menu.add_command(label="Edit Birthday Template", command=self.show_birthday_template_editor)
        tools_menu.add_command(label="Send Birthday Emails", command=self.manual_birthday_check)
        
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
        self.customer_tree = ttk.Treeview(list_container, columns=("Name", "Email"), 
                                         show="tree headings", yscrollcommand=scrollbar.set)
        self.customer_tree.heading("Name", text="Name")
        self.customer_tree.heading("Email", text="Email")
        self.customer_tree.column("#0", width=0, stretch=False)
        self.customer_tree.column("Name", width=150)
        self.customer_tree.column("Email", width=200)
        
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
        
        # Name
        ttk.Label(details_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=5)
        self.name_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.name_var, width=40).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
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
            self.customer_tree.insert("", tk.END, iid=customer['id'],
                                     values=(customer['name'], customer['email']))
        
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
        self.name_var.set(customer['name'])
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
    
    def clear_form(self):
        """Clear the customer form"""
        self.selected_customer_id = None
        self.name_var.set("")
        self.email_var.set("")
        self.phone_var.set("")
        self.birthday_entry.set_date(datetime.now())
        self.notes_text.delete("1.0", tk.END)
        self.set_status("Form cleared")
    
    def add_customer(self):
        """Prepare form for adding new customer"""
        self.clear_form()
        self.set_status("Enter new customer details")
    
    def save_customer(self):
        """Save customer (add or update)"""
        # Validate
        name = self.name_var.get().strip()
        email = self.email_var.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Name is required")
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
                self.db.update_customer(self.selected_customer_id, name, email, birthday, phone, notes)
                messagebox.showinfo("Success", "Customer updated successfully")
                self.set_status(f"Updated: {name}")
            else:
                # Add new
                customer_id = self.db.add_customer(name, email, birthday, phone, notes)
                self.selected_customer_id = customer_id
                messagebox.showinfo("Success", "Customer added successfully")
                self.set_status(f"Added: {name}")
            
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
                              f"Are you sure you want to delete {customer['name']}?"):
            self.db.delete_customer(self.selected_customer_id)
            self.clear_form()
            self.refresh_customer_list()
            self.set_status(f"Deleted: {customer['name']}")
    
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
        subject_var = tk.StringVar(value=f"Hello {customer['name']}")
        ttk.Entry(dialog, textvariable=subject_var, width=70).pack(pady=5, padx=10, fill=tk.X)
        
        # Body
        ttk.Label(dialog, text="Message:").pack(pady=5, padx=10, anchor=tk.W)
        body_text = tk.Text(dialog, width=70, height=15, wrap=tk.WORD)
        body_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        body_text.insert("1.0", f"Dear {customer['name']},\n\n")
        
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

    def manual_birthday_check(self):
        """Manually trigger birthday check with interactive confirmation"""
        customers = self.scheduler.get_todays_birthdays()
        
        if not customers:
            messagebox.showinfo("Birthday Check", "No birthdays found for today.")
            return
            
        # Create confirmation list
        names = [c['name'] for c in customers]
        confirm_msg = f"Found {len(customers)} birthday(s) today:\n\n"
        confirm_msg += "\n".join(f"• {name}" for name in names)
        confirm_msg += "\n\nDo you want to send birthday emails to these people?"
        
        if messagebox.askyesno("Confirm Birthday Emails", confirm_msg):
            def send():
                # Use the interactive check results
                results = self.scheduler.check_and_send_birthday_emails(customers_to_send=customers)
                
                msg = f"Birthday Check Complete:\n\n"
                msg += f"Emails sent: {results['sent']}\n"
                msg += f"Failed: {results['failed']}\n\n"
                
                if results['customers']:
                    msg += "Details:\n"
                    for customer in results['customers']:
                        status = "✓" if customer['success'] else "✗"
                        msg += f"{status} {customer['name']}: {customer['message']}\n"
                
                # Show results on main thread
                self.root.after(0, lambda: messagebox.showinfo("Birthday Check Results", msg))
            
            # Run in thread to avoid blocking UI
            threading.Thread(target=send, daemon=True).start()
    
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
            status = f"🎂 Birthday emails: ON (Check at {self.scheduler.check_time})"
        else:
            status = "🎂 Birthday emails: OFF"
        
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
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


if __name__ == "__main__":
    # This file should be run from crm_app.py
    print("Please run crm_app.py to start the application")
