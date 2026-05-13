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
        
        # Current customer selection state
        self.selected_customer_id = None
        self._expanded_customer_id = None
        self.current_customer_id = None  # used by manual_add_property
        
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
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Top - Search & Filters
        self.create_search_bar(main_frame)
        
        # Middle - Full-width customer tree
        self.create_customer_tree(main_frame)
        
        # Bottom - Action buttons
        self.create_action_bar(main_frame)
        
        # Status bar
        self.create_status_bar(main_frame)
    
    def create_search_bar(self, parent):
        """Create top search and filter bar"""
        top_frame = ttk.Frame(parent, padding="5")
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        top_frame.columnconfigure(1, weight=1)
        
        ttk.Label(top_frame, text="Customers", style="Title.TLabel").grid(row=0, column=0, columnspan=6, sticky=tk.W, pady=(0, 6))
        
        ttk.Label(top_frame, text="Search:").grid(row=1, column=0, sticky=tk.W, padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.search_customers())
        ttk.Entry(top_frame, textvariable=self.search_var).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 15))
        
        ttk.Label(top_frame, text="Mandate:").grid(row=1, column=2, sticky=tk.W, padx=(0, 4))
        self.mandate_filter_var = tk.StringVar(value="All")
        mandate_combo = ttk.Combobox(top_frame, textvariable=self.mandate_filter_var,
                                     values=["All", "Active", "Inactive"], state="readonly", width=9)
        mandate_combo.grid(row=1, column=3, sticky=tk.W, padx=(0, 15))
        mandate_combo.bind("<<ComboboxSelected>>", lambda e: self.search_customers())
        
        ttk.Label(top_frame, text="Land Type:").grid(row=1, column=4, sticky=tk.W, padx=(0, 4))
        self.type_filter_var = tk.StringVar(value="All")
        type_combo = ttk.Combobox(top_frame, textvariable=self.type_filter_var,
                                   values=["All", "Residential", "Commercial", "Agricultural", "Industrial", "Vacant", "Other"],
                                   state="readonly", width=12)
        type_combo.grid(row=1, column=5, sticky=tk.W)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self.search_customers())

    def create_customer_tree(self, parent):
        """Create the full-width expandable customer/property tree"""
        tree_frame = ttk.Frame(parent)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(6, 0))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        columns = ("Surname", "FirstName", "Email", "Phone", "ERF", "LandType", "Mandate", "Expiry")
        self.customer_tree = ttk.Treeview(tree_frame, columns=columns,
                                          show="tree headings", selectmode="browse")
        
        self.customer_tree.heading("#0",       text="")
        self.customer_tree.heading("Surname",   text="Surname")
        self.customer_tree.heading("FirstName", text="First Name")
        self.customer_tree.heading("Email",     text="Email")
        self.customer_tree.heading("Phone",     text="Phone")
        self.customer_tree.heading("ERF",       text="ERF Number")
        self.customer_tree.heading("LandType",  text="Land Type")
        self.customer_tree.heading("Mandate",   text="Mandate")
        self.customer_tree.heading("Expiry",    text="Expiry")
        
        self.customer_tree.column("#0",       width=24, stretch=False)
        self.customer_tree.column("Surname",   width=130)
        self.customer_tree.column("FirstName", width=120)
        self.customer_tree.column("Email",     width=200)
        self.customer_tree.column("Phone",     width=120)
        self.customer_tree.column("ERF",       width=110)
        self.customer_tree.column("LandType",  width=110)
        self.customer_tree.column("Mandate",   width=80)
        self.customer_tree.column("Expiry",    width=90)
        
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,   command=self.customer_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.customer_tree.xview)
        self.customer_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.customer_tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.E, tk.W))
        
        # Tags for child rows (slightly muted)
        self.customer_tree.tag_configure("property", foreground="#aaaaaa")
        
        # Bind double-click to toggle expand/collapse
        self.customer_tree.bind("<Double-1>", self._on_tree_double_click)
        # Track expanded state
        self._expanded_customer_id = None

    def create_action_bar(self, parent):
        """Create the bottom action button bar"""
        action_frame = ttk.Frame(parent, padding="5")
        action_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(6, 0))
        
        ttk.Button(action_frame, text="➕ Add Customer",  command=self.add_customer).pack(side=tk.LEFT, padx=4)
        
        self.edit_btn = ttk.Button(action_frame, text="✏️ Edit Customer",
                                   command=self.edit_selected_customer, state=tk.DISABLED)
        self.edit_btn.pack(side=tk.LEFT, padx=4)
        
        self.email_btn = ttk.Button(action_frame, text="📧 Send Email",
                                    command=self.send_email_to_customer, state=tk.DISABLED)
        self.email_btn.pack(side=tk.LEFT, padx=4)
        
        self.delete_btn = ttk.Button(action_frame, text="🗑️ Delete",
                                     command=self.delete_customer, state=tk.DISABLED)
        self.delete_btn.pack(side=tk.LEFT, padx=4)
    
    # --- status bar (row 3) ---
    
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent, relief=tk.SUNKEN, padding="2")
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(4, 0))
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # Birthday scheduler status
        self.scheduler_status_var = tk.StringVar()
        self.update_scheduler_status()
        ttk.Label(status_frame, textvariable=self.scheduler_status_var).pack(side=tk.RIGHT)
    
    def refresh_customer_list(self, customers=None):
        """Refresh the full-width customer/property tree"""
        # Remember which customer is expanded
        expanded_id = self._expanded_customer_id
        
        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)
        
        if customers is None:
            customers = self.db.get_all_customers()
        
        for customer in customers:
            cid = customer['id']
            sur  = customer.get('surname', '')
            first = customer.get('first_name', '')
            # Insert customer as parent row (property columns blank)
            self.customer_tree.insert("", tk.END, iid=str(cid),
                                      values=(sur, first, customer['email'],
                                              customer.get('phone', '') or '',
                                              '', '', '', ''),
                                      open=False)
            # Insert property child rows
            properties = self.db.get_properties(cid)
            for prop in properties:
                mandate_str = "Yes" if prop['mandate'] else "No"
                expiry_str  = prop['mandate_expiry'] if prop['mandate'] and prop['mandate_expiry'] else "-"
                self.customer_tree.insert(str(cid), tk.END,
                                          values=('', '', '', '',
                                                  prop['erf_number'], prop['land_type'],
                                                  mandate_str, expiry_str),
                                          tags=("property",))
            
            # Re-expand if it was open before refresh
            if expanded_id is not None and str(cid) == str(expanded_id):
                self.customer_tree.item(str(cid), open=True)
        
        self.set_status(f"Loaded {len(customers)} customer(s)")
    
    def search_customers(self):
        """Search customers based on search term and filters"""
        query = self.search_var.get().strip()
        mandate_status = getattr(self, 'mandate_filter_var', tk.StringVar(value="All")).get()
        land_type = getattr(self, 'type_filter_var', tk.StringVar(value="All")).get()
        
        customers = self.db.search_customers(query, mandate_status, land_type)
        
        self.refresh_customer_list(customers)
    
    def _on_tree_double_click(self, event):
        """Toggle expand/collapse on double-clicking a customer row; enable Edit button when expanded."""
        item = self.customer_tree.identify_row(event.y)
        if not item:
            return
        # Only act on top-level (customer) rows
        if self.customer_tree.parent(item) != '':
            return
        currently_open = self.customer_tree.item(item, 'open')
        new_state = not currently_open
        self.customer_tree.item(item, open=new_state)
        if new_state:
            self._expanded_customer_id = int(item)
            self.selected_customer_id  = int(item)
            self.edit_btn.config(state=tk.NORMAL)
            self.email_btn.config(state=tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
        else:
            self._expanded_customer_id = None
            self.edit_btn.config(state=tk.DISABLED)

    def on_customer_select(self, event):
        """Track which top-level customer row is selected for email/delete."""
        selection = self.customer_tree.selection()
        if not selection:
            return
        item = selection[0]
        # Walk up to the top-level parent if a property row is selected
        while self.customer_tree.parent(item):
            item = self.customer_tree.parent(item)
        try:
            self.selected_customer_id = int(item)
            self.email_btn.config(state=tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
        except ValueError:
            pass
    
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
        """Reset selection state"""
        self.selected_customer_id = None
        self._expanded_customer_id = None
        self.edit_btn.config(state=tk.DISABLED)
        self.email_btn.config(state=tk.DISABLED)
        self.delete_btn.config(state=tk.DISABLED)
        self.set_status("Ready")
    
    def edit_selected_customer(self):
        """Open the edit dialog for the currently expanded customer."""
        if not self._expanded_customer_id:
            messagebox.showwarning("Warning", "Please expand a customer row first.")
            return
        customer = self.db.get_customer(self._expanded_customer_id)
        if customer:
            self.show_edit_customer_dialog(customer)

    def show_edit_customer_dialog(self, customer):
        """Open a pre-filled dialog to edit a customer and their properties."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit — {customer.get('first_name','')} {customer.get('surname','')}")
        dialog.geometry("560x620")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

        ttk.Label(dialog, text="Edit Customer", style="Title.TLabel").pack(pady=(12, 4), padx=15, anchor=tk.W)
        ttk.Separator(dialog).pack(fill=tk.X, padx=15, pady=(0, 8))

        # ── Basic info form ──
        form = ttk.Frame(dialog, padding="15 0 15 0")
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)

        fields = [
            ("First Name:*", "first_name"),
            ("Surname:*",    "surname"),
            ("Email:*",      "email"),
            ("Phone:",       "phone"),
        ]
        vars_ = {}
        for r, (label, key) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky=tk.W, pady=4, padx=(0,10))
            v = tk.StringVar(value=customer.get(key, '') or '')
            vars_[key] = v
            ttk.Entry(form, textvariable=v).grid(row=r, column=1, sticky=(tk.W, tk.E), pady=4)

        ttk.Label(form, text="Birthday:").grid(row=len(fields), column=0, sticky=tk.W, pady=4, padx=(0,10))
        bday_entry = DateEntry(form, width=17, background='darkblue', foreground='white',
                               borderwidth=2, date_pattern='yyyy-mm-dd')
        if customer.get('birthday'):
            try:
                bday_entry.set_date(datetime.strptime(customer['birthday'], "%Y-%m-%d"))
            except Exception:
                pass
        bday_entry.grid(row=len(fields), column=1, sticky=tk.W, pady=4)

        ttk.Label(form, text="Notes:").grid(row=len(fields)+1, column=0, sticky=(tk.W, tk.N), pady=4, padx=(0,10))
        notes_box = tk.Text(form, height=4, wrap=tk.WORD)
        notes_box.insert("1.0", customer.get('notes', '') or '')
        notes_box.grid(row=len(fields)+1, column=1, sticky=(tk.W, tk.E), pady=4)

        ttk.Separator(dialog).pack(fill=tk.X, padx=15, pady=8)

        # ── Properties sub-section ──
        prop_frame = ttk.Frame(dialog, padding="15 0 15 0")
        prop_frame.pack(fill=tk.BOTH, expand=True)
        prop_frame.columnconfigure(0, weight=1)
        prop_frame.rowconfigure(0, weight=1)

        ttk.Label(prop_frame, text="Properties", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 4))

        prop_cols = ("ERF", "Type", "Mandate", "Expiry")
        prop_tree = ttk.Treeview(prop_frame, columns=prop_cols, show="headings", height=5)
        for col, heading in zip(prop_cols, ("ERF Number", "Land Type", "Mandate", "Expiry")):
            prop_tree.heading(col, text=heading)
            prop_tree.column(col, width=120)

        prop_vsb = ttk.Scrollbar(prop_frame, orient=tk.VERTICAL, command=prop_tree.yview)
        prop_tree.configure(yscrollcommand=prop_vsb.set)
        prop_tree.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        prop_vsb.grid(row=1, column=1, sticky=(tk.N, tk.S))

        def _reload_props():
            for i in prop_tree.get_children():
                prop_tree.delete(i)
            for p in self.db.get_properties(customer['id']):
                ms = "Yes" if p['mandate'] else "No"
                ex = p['mandate_expiry'] if p['mandate'] and p['mandate_expiry'] else "-"
                prop_tree.insert("", tk.END, iid=str(p['id']), values=(p['erf_number'], p['land_type'], ms, ex))
        _reload_props()

        prop_btn_row = ttk.Frame(prop_frame)
        prop_btn_row.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        def _add_prop():
            self.current_customer_id = customer['id']
            self.manual_add_property(callback=_reload_props)

        def _remove_prop():
            sel = prop_tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "Select a property to remove.", parent=dialog)
                return
            if messagebox.askyesno("Confirm", "Remove selected property?", parent=dialog):
                self.db.delete_property(int(sel[0]))
                _reload_props()

        ttk.Button(prop_btn_row, text="➕ Add Property",    command=_add_prop).pack(side=tk.LEFT, padx=(0,4))
        ttk.Button(prop_btn_row, text="🗑️ Remove Property", command=_remove_prop).pack(side=tk.LEFT)

        # ── Footer buttons ──
        ttk.Separator(dialog).pack(fill=tk.X, padx=15, pady=8)
        footer = ttk.Frame(dialog, padding="15 0 15 12")
        footer.pack(fill=tk.X)

        def _save():
            fn    = vars_['first_name'].get().strip()
            sn    = vars_['surname'].get().strip()
            email = vars_['email'].get().strip()
            if not fn or not sn or not email:
                messagebox.showerror("Error", "First Name, Surname, and Email are required.", parent=dialog)
                return
            if not self.email.validate_email(email):
                messagebox.showerror("Error", "Invalid email address.", parent=dialog)
                return
            try:
                self.db.update_customer(
                    customer['id'],
                    first_name=fn, surname=sn, email=email,
                    birthday=bday_entry.get_date().strftime("%Y-%m-%d"),
                    phone=vars_['phone'].get().strip(),
                    notes=notes_box.get("1.0", tk.END).strip()
                )
                self.set_status(f"Updated: {fn} {sn}")
                self.refresh_customer_list()
                dialog.destroy()
            except ValueError as exc:
                messagebox.showerror("Error", str(exc), parent=dialog)

        ttk.Button(footer, text="💾 Save",   command=_save).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(footer, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)

    def add_customer(self):
        """Show dialog to add a new customer"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Customer")
        dialog.geometry("450x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Add New Customer", style="Title.TLabel").pack(pady=10)
        
        form_frame = ttk.Frame(dialog, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Form fields
        ttk.Label(form_frame, text="First Name:*").grid(row=0, column=0, sticky=tk.W, pady=5)
        first_name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=first_name_var).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(form_frame, text="Surname:*").grid(row=1, column=0, sticky=tk.W, pady=5)
        surname_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=surname_var).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(form_frame, text="Email:*").grid(row=2, column=0, sticky=tk.W, pady=5)
        email_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=email_var).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(form_frame, text="Birthday:").grid(row=3, column=0, sticky=tk.W, pady=5)
        birthday_entry = DateEntry(form_frame, width=17, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        birthday_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(form_frame, text="Phone:").grid(row=4, column=0, sticky=tk.W, pady=5)
        phone_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=phone_var).grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(form_frame, text="Notes:").grid(row=5, column=0, sticky=(tk.W, tk.N), pady=5)
        notes_text = tk.Text(form_frame, width=30, height=5, wrap=tk.WORD)
        notes_text.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5)
        
        form_frame.columnconfigure(1, weight=1)
        
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X)
        
        def save():
            first_name = first_name_var.get().strip()
            surname = surname_var.get().strip()
            email = email_var.get().strip()
            
            if not first_name or not surname or not email:
                messagebox.showerror("Error", "First Name, Surname, and Email are required", parent=dialog)
                return
                
            if not self.email.validate_email(email):
                messagebox.showerror("Error", "Invalid email address", parent=dialog)
                return
                
            birthday = birthday_entry.get_date().strftime("%Y-%m-%d")
            phone = phone_var.get().strip()
            notes = notes_text.get("1.0", tk.END).strip()
            
            try:
                self.db.add_customer(first_name, surname, email, birthday, phone, notes)
                messagebox.showinfo("Success", "Customer added successfully", parent=dialog)
                self.set_status(f"Added: {first_name} {surname}")
                self.refresh_customer_list()
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=dialog)
                
        ttk.Button(button_frame, text="Save", command=save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    

    def delete_customer(self):
        """Delete the currently selected customer"""
        if not self.selected_customer_id:
            messagebox.showwarning("Warning", "Please select a customer first.")
            return
        customer = self.db.get_customer(self.selected_customer_id)
        if not customer:
            return
        if messagebox.askyesno("Confirm Delete",
                               f"Delete {customer['first_name']} {customer['surname']} and all their properties?"):
            self.db.delete_customer(self.selected_customer_id)
            self._expanded_customer_id = None
            self.selected_customer_id = None
            self.edit_btn.config(state=tk.DISABLED)
            self.email_btn.config(state=tk.DISABLED)
            self.delete_btn.config(state=tk.DISABLED)
            self.refresh_customer_list()
            self.set_status(f"Deleted: {customer['first_name']} {customer['surname']}")
    
    def send_email_to_customer(self):
        """Send email to the selected customer"""
        if not self.selected_customer_id:
            messagebox.showwarning("Warning", "Please select a customer first.")
            return
        customer = self.db.get_customer(self.selected_customer_id)
        if customer:
            self.show_email_composer(customer)
    
    def show_email_composer(self, customer):
        """Show email composer window"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Send Email to {customer.get('first_name','')} {customer.get('surname','')}")
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
    

    def manual_add_property(self, callback=None):
        """Show dialog to add a property. Optional callback is called after saving."""
        if not self.current_customer_id:
            messagebox.showwarning("Warning", "Please select a customer first.")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Property")
        dialog.geometry("350x280")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="ERF Number:").pack(anchor=tk.W, pady=(0, 5))
        erf_var = tk.StringVar()
        erf_entry = ttk.Entry(main_frame, textvariable=erf_var, width=30)
        erf_entry.pack(fill=tk.X, pady=(0, 15))
        erf_entry.focus_set()
        
        ttk.Label(main_frame, text="Land Type:").pack(anchor=tk.W, pady=(0, 5))
        type_var = tk.StringVar(value="Residential")
        type_combo = ttk.Combobox(main_frame, textvariable=type_var,
                                  values=["Vacant", "Residential", "Agricultural", "Industrial", "Commercial", "Other"],
                                  state="readonly")
        type_combo.pack(fill=tk.X, pady=(0, 15))
        
        mandate_var = tk.IntVar(value=0)
        ttk.Checkbutton(main_frame, text="Active Mandate", variable=mandate_var).pack(anchor=tk.W, pady=(0, 5))
        
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
                # Refresh the main tree too
                self.refresh_customer_list()
                dialog.destroy()
                if callback:
                    callback()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add property: {e}")
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Save",   command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)



    def run(self):
        """Start the application"""
        self.root.mainloop()


if __name__ == "__main__":
    # This file should be run from crm_app.py
    print("Please run crm_app.py to start the application")
