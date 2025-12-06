import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from tkcalendar import Calendar, DateEntry
# from stfoom.logicold import calendar_base as cal  # DISABLED: migrated to CalendarService


class CalendarPage(ttk.Frame):
    # Default category colors (used as fallback)
    CATEGORY_COLORS = {
        "Cars":        "#a3c1ad",
        "Paiement":    "#d6a77a",
        "Facturation": "#7ca6d6",
        "Other":       "#b5a3c1"
    }

    def __init__(self, parent, container_or_go_home, go_home=None):
        super().__init__(parent)
        
        # ✅ PHASE 2H MIGRATION: Support dependency injection
        if go_home is not None:
            # New signature: CalendarPage(parent, di_container, go_home)
            self.di_container = container_or_go_home
            self.go_home = go_home
            self.calendar_service = None
            
            # Try to get service from container
            try:
                self.calendar_service = self.di_container.get('calendar_service')
                print("[CALENDAR_PAGE] Using CalendarService from DI container")
            except Exception as e:
                print(f"[CALENDAR_PAGE] Failed to get CalendarService: {e}")
                self.calendar_service = None
        else:
            # Old signature: CalendarPage(parent, go_home) - for backward compatibility
            self.go_home = container_or_go_home
            self.di_container = None
            self.calendar_service = None
            print("[CALENDAR_PAGE] Using legacy calendar_base module")

        self.show_past = tk.BooleanVar(value=False)
        self.past_period = tk.StringVar(value="1_week")  # Default to 1 week

        # Load categories from database
        self._load_categories()

        # Configure style for this page
        style = ttk.Style()
        style.configure('CalendarPage.TFrame', background='white')
        style.configure('CalendarHeader.TLabel', font=('Arial', 14, 'bold'), background='white')
        style.configure('CalendarFilter.TLabelframe', background='white')
        style.configure('CalendarFilter.TLabelframe.Label', font=('Arial', 10, 'bold'), background='white')

        self.configure(style='CalendarPage.TFrame')
        
        # Initialize the UI
        self._setup_ui()
    
    def _load_categories(self):
        """Load calendar categories from database."""
        import sqlite3
        from config.settings import get_db_path
        
        try:
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name, color, default_reminder_days 
                FROM calendar_categories 
                ORDER BY is_system DESC, name
            """)
            
            categories = cursor.fetchall()
            conn.close()
            
            if categories:
                # Update CATEGORY_COLORS from database
                self.CATEGORY_COLORS = {}
                self.category_reminder_defaults = {}
                
                for cat in categories:
                    self.CATEGORY_COLORS[cat['name']] = cat['color']
                    self.category_reminder_defaults[cat['name']] = cat['default_reminder_days']
                
                print(f"[CALENDAR PAGE] Loaded {len(categories)} categories from database")
            else:
                # Use default categories if none in database
                print("[CALENDAR PAGE] No categories in database, using defaults")
                self.category_reminder_defaults = {
                    "Cars": 10,
                    "Paiement": 7,
                    "Facturation": 1,
                    "Other": 1
                }
        
        except Exception as e:
            print(f"[CALENDAR PAGE] Error loading categories: {e}")
            # Use default categories on error
            self.category_reminder_defaults = {
                "Cars": 10,
                "Paiement": 7,
                "Facturation": 1,
                "Other": 1
            }
    
    def _manage_categories_dialog(self):
        """Open dialog to manage calendar categories."""
        dlg = tk.Toplevel(self)
        dlg.grab_set()
        dlg.title("Gérer les Catégories")
        dlg.geometry("600x500")
        dlg.resizable(False, False)
        dlg.configure(bg='white')
        
        # Main container
        main_frame = ttk.Frame(dlg, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(header_frame, text="Catégories du Calendrier", 
                 font=('Arial', 14, 'bold')).pack(side="left")
        
        # Add button
        add_btn = tk.Button(header_frame, text="➕ Nouvelle Catégorie", 
                           command=lambda: self._add_category_dialog(load_categories),
                           bg="#4CAF50", fg="white", font=('Arial', 9, 'bold'),
                           relief="flat", padx=15, pady=5)
        add_btn.pack(side="right")
        
        # Categories list with scrollbar
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill="both", expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Treeview for categories
        columns = ("name", "color", "reminder", "type")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", 
                           yscrollcommand=scrollbar.set, height=15)
        
        tree.heading("name", text="Nom")
        tree.heading("color", text="Couleur")
        tree.heading("reminder", text="Rappel (jours)")
        tree.heading("type", text="Type")
        
        tree.column("name", width=200)
        tree.column("color", width=100)
        tree.column("reminder", width=120)
        tree.column("type", width=100)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=tree.yview)
        
        # Load categories
        def load_categories():
            tree.delete(*tree.get_children())
            
            import sqlite3
            from config.settings import get_db_path
            
            try:
                db_path = get_db_path()
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT name, color, default_reminder_days, is_system 
                    FROM calendar_categories 
                    ORDER BY is_system DESC, name
                """)
                
                for row in cursor.fetchall():
                    cat_type = "Système" if row['is_system'] else "Personnalisé"
                    tree.insert("", "end", values=(
                        row['name'],
                        row['color'],
                        row['default_reminder_days'],
                        cat_type
                    ), tags=(row['color'],))
                    
                    # Color the row background
                    tree.tag_configure(row['color'], background=row['color'])
                
                conn.close()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement: {e}")
        
        load_categories()
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        def edit_category():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Veuillez sélectionner une catégorie")
                return
            
            item = tree.item(sel[0])
            values = item['values']
            self._edit_category_dialog(dlg, values[0], values[1], values[2], load_categories)
        
        def delete_category():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Attention", "Veuillez sélectionner une catégorie")
                return
            
            item = tree.item(sel[0])
            cat_name = item['values'][0]
            cat_type = item['values'][3]
            
            if cat_type == "Système":
                messagebox.showerror("Erreur", "Impossible de supprimer une catégorie système")
                return
            
            if not messagebox.askyesno("Confirmer", f"Supprimer la catégorie '{cat_name}' ?"):
                return
            
            import sqlite3
            from config.settings import get_db_path
            
            try:
                db_path = get_db_path()
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if category is used
                cursor.execute("SELECT COUNT(*) FROM calendar_events WHERE category = ?", (cat_name,))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    if not messagebox.askyesno("Attention", 
                        f"Cette catégorie est utilisée par {count} événement(s).\n" +
                        "Les événements seront changés en 'Other'. Continuer ?"):
                        conn.close()
                        return
                    
                    # Move events to 'Other'
                    cursor.execute("UPDATE calendar_events SET category = 'Other' WHERE category = ?", 
                                 (cat_name,))
                
                # Delete category
                cursor.execute("DELETE FROM calendar_categories WHERE name = ?", (cat_name,))
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Succès", f"Catégorie '{cat_name}' supprimée")
                load_categories()
                self._load_categories()  # Reload in main page
                self.refresh_list()
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
        
        edit_btn = tk.Button(btn_frame, text="✏️ Modifier", command=edit_category,
                            bg="#2196F3", fg="white", font=('Arial', 9),
                            relief="flat", padx=15, pady=5)
        edit_btn.pack(side="left", padx=(0, 5))
        
        delete_btn = tk.Button(btn_frame, text="🗑️ Supprimer", command=delete_category,
                              bg="#f44336", fg="white", font=('Arial', 9),
                              relief="flat", padx=15, pady=5)
        delete_btn.pack(side="left")
        
        close_btn = tk.Button(btn_frame, text="Fermer", command=dlg.destroy,
                             bg="#9E9E9E", fg="white", font=('Arial', 9),
                             relief="flat", padx=15, pady=5)
        close_btn.pack(side="right")
    
    def _add_category_dialog(self, reload_callback):
        """Dialog to add new category."""
        dlg = tk.Toplevel(self)
        dlg.grab_set()
        dlg.title("Nouvelle Catégorie")
        dlg.geometry("400x300")
        dlg.resizable(False, False)
        dlg.configure(bg='white')
        
        main_frame = ttk.Frame(dlg, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Name
        ttk.Label(main_frame, text="Nom de la catégorie *").pack(anchor="w", pady=(0, 5))
        name_entry = ttk.Entry(main_frame, width=40)
        name_entry.pack(fill="x", pady=(0, 15))
        
        # Color
        ttk.Label(main_frame, text="Couleur").pack(anchor="w", pady=(0, 5))
        color_frame = ttk.Frame(main_frame)
        color_frame.pack(fill="x", pady=(0, 15))
        
        color_var = tk.StringVar(value="#95a5a6")
        color_entry = ttk.Entry(color_frame, textvariable=color_var, width=10)
        color_entry.pack(side="left")
        
        color_preview = tk.Label(color_frame, bg=color_var.get(), width=3, height=1, relief="ridge")
        color_preview.pack(side="left", padx=(10, 0))
        
        def update_color_preview(*args):
            try:
                color_preview.config(bg=color_var.get())
            except:
                pass
        
        color_var.trace_add("write", update_color_preview)
        
        def choose_color():
            from tkinter import colorchooser
            color = colorchooser.askcolor(color_var.get())
            if color[1]:
                color_var.set(color[1])
        
        ttk.Button(color_frame, text="Choisir...", command=choose_color).pack(side="left", padx=(10, 0))
        
        # Reminder days
        ttk.Label(main_frame, text="Rappel par défaut (jours)").pack(anchor="w", pady=(0, 5))
        reminder_spin = ttk.Spinbox(main_frame, from_=1, to=90, width=10)
        reminder_spin.set(1)
        reminder_spin.pack(anchor="w", pady=(0, 15))
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Erreur", "Le nom est obligatoire")
                return
            
            import sqlite3
            from config.settings import get_db_path
            
            try:
                db_path = get_db_path()
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO calendar_categories (name, color, default_reminder_days, is_system)
                    VALUES (?, ?, ?, 0)
                """, (name, color_var.get(), int(reminder_spin.get())))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Succès", f"Catégorie '{name}' ajoutée")
                dlg.destroy()
                self._load_categories()  # Reload categories
                reload_callback()  # Reload parent list
                self.refresh_list()  # Refresh calendar view
                
            except sqlite3.IntegrityError:
                messagebox.showerror("Erreur", "Cette catégorie existe déjà")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'ajout: {e}")
        
        save_btn = tk.Button(btn_frame, text="Ajouter", command=save,
                            bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'),
                            relief="flat", padx=30, pady=8)
        save_btn.pack(side="right")
        
        cancel_btn = tk.Button(btn_frame, text="Annuler", command=dlg.destroy,
                              bg="#9E9E9E", fg="white", font=('Arial', 10),
                              relief="flat", padx=30, pady=8)
        cancel_btn.pack(side="right", padx=(0, 10))
    
    def _edit_category_dialog(self, parent_dlg, cat_name, cat_color, cat_reminder, reload_callback):
        """Dialog to edit existing category."""
        dlg = tk.Toplevel(parent_dlg)
        dlg.grab_set()
        dlg.title(f"Modifier: {cat_name}")
        dlg.geometry("400x250")
        dlg.resizable(False, False)
        dlg.configure(bg='white')
        
        main_frame = ttk.Frame(dlg, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text=f"Catégorie: {cat_name}", 
                 font=('Arial', 12, 'bold')).pack(anchor="w", pady=(0, 15))
        
        # Color
        ttk.Label(main_frame, text="Couleur").pack(anchor="w", pady=(0, 5))
        color_frame = ttk.Frame(main_frame)
        color_frame.pack(fill="x", pady=(0, 15))
        
        color_var = tk.StringVar(value=cat_color)
        color_entry = ttk.Entry(color_frame, textvariable=color_var, width=10)
        color_entry.pack(side="left")
        
        color_preview = tk.Label(color_frame, bg=color_var.get(), width=3, height=1, relief="ridge")
        color_preview.pack(side="left", padx=(10, 0))
        
        def update_color_preview(*args):
            try:
                color_preview.config(bg=color_var.get())
            except:
                pass
        
        color_var.trace_add("write", update_color_preview)
        
        def choose_color():
            from tkinter import colorchooser
            color = colorchooser.askcolor(color_var.get())
            if color[1]:
                color_var.set(color[1])
        
        ttk.Button(color_frame, text="Choisir...", command=choose_color).pack(side="left", padx=(10, 0))
        
        # Reminder days
        ttk.Label(main_frame, text="Rappel par défaut (jours)").pack(anchor="w", pady=(0, 5))
        reminder_spin = ttk.Spinbox(main_frame, from_=1, to=90, width=10)
        reminder_spin.set(cat_reminder)
        reminder_spin.pack(anchor="w", pady=(0, 15))
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        def save():
            import sqlite3
            from config.settings import get_db_path
            
            try:
                db_path = get_db_path()
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE calendar_categories 
                    SET color = ?, default_reminder_days = ?
                    WHERE name = ?
                """, (color_var.get(), int(reminder_spin.get()), cat_name))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Succès", f"Catégorie '{cat_name}' mise à jour")
                dlg.destroy()
                self._load_categories()  # Reload categories
                reload_callback()  # Reload parent list
                self.refresh_list()
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la mise à jour: {e}")
        
        save_btn = tk.Button(btn_frame, text="Enregistrer", command=save,
                            bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'),
                            relief="flat", padx=30, pady=8)
        save_btn.pack(side="right")
        
        cancel_btn = tk.Button(btn_frame, text="Annuler", command=dlg.destroy,
                              bg="#9E9E9E", fg="white", font=('Arial', 10),
                              relief="flat", padx=30, pady=8)
        cancel_btn.pack(side="right", padx=(0, 10))

    # ✅ PHASE 2H MIGRATION: Helper methods for service layer abstraction
    def _get_all_events(self, categories=None, include_past=True, include_done=True):
        """Get all events using service layer or legacy module."""
        if self.calendar_service:
            return self.calendar_service.get_all_events(categories, include_past, include_done)
        else:
            # Fallback when no service available - return empty list
            return []

    def _find_event(self, date_str, category, title):
        """Find event using service layer or legacy module."""
        if self.calendar_service:
            return self.calendar_service.find_event(date_str, category, title)
        else:
            return self.calendar_service.find_event(date_str, category, title) if self.calendar_service else None

    def _add_event(self, title, date_str, category, description, done=0, reminder_days=1, repeat_pattern='none'):
        """Add event using service layer or legacy module."""
        result = False
        if self.calendar_service:
            result = self.calendar_service.create_event(title, date_str, category, description, done)
        else:
            result = self.calendar_service.add_event(title, date_str, category, description, done) if self.calendar_service else False
        
        # Update reminder_days and repeat_pattern using direct DB access
        if result:
            self._update_event_extra_fields(title, date_str, category, reminder_days, repeat_pattern)
        
        return result
    
    def _update_event_extra_fields(self, title, date_str, category, reminder_days, repeat_pattern='none'):
        """Update event reminder_days and repeat_pattern using direct DB access."""
        try:
            from config.settings import get_db_path
            import sqlite3
            
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE calendar_events 
                SET reminder_days = ?, repeat_pattern = ?
                WHERE title = ? AND date = ? AND category = ?
            """, (reminder_days, repeat_pattern, title, date_str, category))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[CALENDAR PAGE] Error updating extra fields: {e}")
    
    def _update_event_reminder_days(self, title, date_str, category, reminder_days):
        """Update event reminder_days using direct DB access."""
        try:
            from config.settings import get_db_path
            import sqlite3
            
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE calendar_events 
                SET reminder_days = ?
                WHERE title = ? AND date = ? AND category = ?
            """, (reminder_days, title, date_str, category))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[CALENDAR PAGE] Error updating reminder_days: {e}")

    def _update_event(self, event_id_or_data, title, date_str, category, description, done, reminder_days=1, repeat_pattern='none'):
        """Update event using service layer or legacy module."""
        event_id = None
        result = False
        
        if self.calendar_service:
            # If we have an event ID, use it directly
            if isinstance(event_id_or_data, (int, str)) and str(event_id_or_data).isdigit():
                event_id = int(event_id_or_data)
                result = self.calendar_service.update_event(event_id, title, date_str, category, description, done)
            else:
                # Find the event by data and get its ID
                event = event_id_or_data
                if event and 'id' in event:
                    event_id = event['id']
                    result = self.calendar_service.update_event(event_id, title, date_str, category, description, done)
        else:
            # Legacy module expects event ID
            if isinstance(event_id_or_data, dict) and 'id' in event_id_or_data:
                event_id = event_id_or_data['id']
                result = self.calendar_service.update_event(event_id, title, date_str, category, description, done) if self.calendar_service else False
            else:
                event_id = event_id_or_data
                result = self.calendar_service.update_event(event_id, title, date_str, category, description, done) if self.calendar_service else False
        
        # Update reminder_days and repeat_pattern using direct DB access
        if result and event_id:
            self._update_event_extra_fields_by_id(event_id, reminder_days, repeat_pattern)
        
        return result
    
    def _update_event_extra_fields_by_id(self, event_id, reminder_days, repeat_pattern='none'):
        """Update event reminder_days and repeat_pattern by ID using direct DB access."""
        try:
            from config.settings import get_db_path
            import sqlite3
            
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE calendar_events 
                SET reminder_days = ?, repeat_pattern = ?
                WHERE id = ?
            """, (reminder_days, repeat_pattern, event_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[CALENDAR PAGE] Error updating extra fields by ID: {e}")
    
    def _update_event_reminder_days_by_id(self, event_id, reminder_days):
        """Update event reminder_days by ID using direct DB access."""
        try:
            from config.settings import get_db_path
            import sqlite3
            
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE calendar_events 
                SET reminder_days = ?
                WHERE id = ?
            """, (reminder_days, event_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[CALENDAR PAGE] Error updating reminder_days by id: {e}")

    def _delete_event_by_keys(self, date_str, category, title):
        """Delete event by keys using service layer or legacy module."""
        if self.calendar_service:
            # Find the event first, then delete by ID
            event = self._find_event(date_str, category, title)
            if event and 'id' in event:
                return self.calendar_service.delete_event(event['id'])
            return False
        else:
            return self.calendar_service.delete_event_by_keys(date_str, category, title) if self.calendar_service else False

    def _is_event_in_period(self, event_date_str):
        """Check if event is within the selected past period."""
        from datetime import datetime, timedelta
        
        if not hasattr(self, 'past_period'):
            return True  # Default behavior if period not set
            
        period = self.past_period.get()
        if period == "all":
            return True
            
        today = date.today()
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        
        # Only apply period filter to past events
        if event_date >= today:
            return True
            
        # Calculate cutoff date based on period
        if period == "1_week":
            cutoff = today - timedelta(days=7)
        elif period == "1_month":
            cutoff = today - timedelta(days=30)
        elif period == "3_months":
            cutoff = today - timedelta(days=90)
        elif period == "6_months":
            cutoff = today - timedelta(days=180)
        elif period == "this_year":
            cutoff = date(today.year, 1, 1)
        else:
            return True  # Default to showing all
            
        return event_date >= cutoff

    def _setup_ui(self):
        """Setup the user interface components."""
        
        # ───────── Top: Compact Filters Bar ─────────
        top_bar = ttk.Frame(self)
        top_bar.pack(fill="x", padx=10, pady=(10, 5))
        
        # Filters section - HORIZONTAL layout
        filter_container = ttk.LabelFrame(top_bar, text="Filtres", style='CalendarFilter.TLabelframe', padding=5)
        filter_container.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        filters_row = ttk.Frame(filter_container)
        filters_row.pack(fill="x")
        
        self.filters = list(self.CATEGORY_COLORS.keys())
        self.filter_vars = {}

        # Create horizontal filter checkboxes with color indicators
        for idx, cat in enumerate(self.filters):
            var = tk.BooleanVar(value=True)
            
            cat_frame = ttk.Frame(filters_row)
            cat_frame.pack(side="left", padx=5, pady=2)
            
            # Color indicator box (bigger and to the left)
            color_box = tk.Label(cat_frame, bg=self.CATEGORY_COLORS[cat], width=3, height=1,
                               relief="solid", borderwidth=1)
            color_box.pack(side="left", padx=(0, 5))
            
            # Checkbox with category name
            chk = ttk.Checkbutton(cat_frame, text=cat, variable=var, command=self.refresh_list)
            chk.pack(side="left")
            
            self.filter_vars[cat] = var
        
        # Manage categories button - compact
        manage_cat_btn = tk.Button(filters_row, text="⚙️", 
                                   command=self._manage_categories_dialog,
                                   bg="#607D8B", fg="white", font=('Arial', 9, 'bold'),
                                   relief="flat", padx=8, pady=2, cursor="hand2")
        manage_cat_btn.pack(side="left", padx=10)
        
        # Quick tooltip
        from tkinter import messagebox
        def show_tooltip(event):
            # Simple hover effect
            manage_cat_btn.config(bg="#546E7A")
        def hide_tooltip(event):
            manage_cat_btn.config(bg="#607D8B")
        manage_cat_btn.bind("<Enter>", show_tooltip)
        manage_cat_btn.bind("<Leave>", hide_tooltip)

        # Show past events with period selector - COMPACT
        past_container = ttk.Frame(top_bar)
        past_container.pack(side="left")
        
        past_chk = ttk.Checkbutton(past_container, text="Passé", variable=self.show_past, 
                                  command=self.refresh_list)
        past_chk.pack(side="left", padx=5)
        
        # Period options
        self.past_period = tk.StringVar(value="1_week")
        period_options = [
            ("7j", "1_week"),
            ("30j", "1_month"), 
            ("3m", "3_months"),
            ("6m", "6_months"),
            ("Année", "this_year"),
            ("Tout", "all")
        ]
        
        period_combo = ttk.Combobox(past_container, textvariable=self.past_period, 
                                   values=[opt[0] for opt in period_options], 
                                   state="readonly", width=8)
        period_combo.pack(side="left", padx=5)
        
        # Bind period change to refresh
        period_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_list())
        
        # Store mapping for easy lookup
        self.period_mapping = dict(period_options)
        
        # ───────── Bottom: Calendar and Events (horizontal split) ─────────
        # IMPORTANT: Don't expand fully - leave room for universal bar!
        pw = ttk.Panedwindow(self, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=10, pady=(5, 5))

        # ───────── LEFT: Calendar (bigger now!) ─────────
        left = ttk.Frame(pw)
        pw.add(left, weight=3)  # Give calendar MORE space (was 1, now 3)

        # Calendar widget - Good size with readable header
        self.calendar = Calendar(left, selectmode="day", 
                               background='white', 
                               bordercolor='#e0e0e0', 
                               headersbackground='#2196F3',  # Blue background for header
                               headersforeground='white',     # White text for month/year
                               normalbackground='white', 
                               normalforeground='black',      # Black text for dates
                               weekendbackground='#f8f8f8',
                               weekendforeground='#D32F2F',   # Red for weekends
                               othermonthbackground='#f0f0f0', 
                               othermonthwebackground='#f0f0f0',
                               othermonthforeground='#BDBDBD', # Gray for other month dates
                               selectbackground='#4CAF50',     # Green selection
                               selectforeground='white',
                               font=('Arial', 10))  # Reasonable font
        # Don't expand fully - fixed reasonable height
        self.calendar.pack(fill="both", expand=False, padx=5, pady=5)
        
        # Bind calendar click to select event in list
        self.calendar.bind("<<CalendarSelected>>", self._on_calendar_date_click)

        # ───────── RIGHT: Events List (smaller but clearer) ─────────
        right = ttk.Frame(pw)
        pw.add(right, weight=2)  # Less space than calendar (was 1, now 2)

        # Header with icon
        header_frame = ttk.Frame(right)
        header_frame.pack(fill="x", pady=(0, 10))
        
        header_label = ttk.Label(header_frame, text="📅 Événements à venir", 
                                style='CalendarHeader.TLabel',
                                font=('Arial', 12, 'bold'))
        header_label.pack(side="left")
        
        # Event count label
        self.event_count_label = ttk.Label(header_frame, text="", 
                                          font=('Arial', 9), foreground='gray')
        self.event_count_label.pack(side="left", padx=10)

        # Treeview for events - CLEARER formatting
        tree_frame = ttk.Frame(right)
        tree_frame.pack(fill="both", expand=True, pady=5)

        # Configure treeview style for better readability
        style = ttk.Style()
        style.configure("Calendar.Treeview", 
                       rowheight=28,  # Bigger rows
                       font=('Arial', 10))  # Bigger font
        style.configure("Calendar.Treeview.Heading", 
                       font=('Arial', 10, 'bold'))

        # Reduce height to leave room for universal bar
        self.tree = ttk.Treeview(
            tree_frame, columns=("status", "date", "titre", "cat"),
            show="headings", height=12, style="Calendar.Treeview"
        )
        
        # Reorder columns for better readability: Status | Date | Title | Category
        self.tree.heading("status", text="✓")
        self.tree.heading("date",   text="Date")
        self.tree.heading("titre",  text="Titre")
        self.tree.heading("cat",    text="Catégorie")
        
        self.tree.column("status", width=35,  anchor="center")
        self.tree.column("date",   width=90,  anchor="center")
        self.tree.column("titre",  width=280, anchor="w")
        self.tree.column("cat",    width=110, anchor="center")
        
        # Add scrollbar
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")

        # Improved tag colors for better clarity
        self.tree.tag_configure("done", foreground="#4CAF50", font=("Arial", 10))
        self.tree.tag_configure("pending", foreground="#212121", font=("Arial", 10, "bold"))
        self.tree.tag_configure("overdue", foreground="#F44336", font=("Arial", 10, "bold"))
        self.tree.tag_configure("today", background="#FFF9C4", font=("Arial", 10, "bold"))
        self.tree.tag_configure("done_past", foreground="grey60", font=("Arial", 10, "italic"))
        
        self.tree.bind("<Double-1>", self._on_double_click)

        # Button bar - TWO ROWS to prevent shrinking
        btnbar_container = ttk.Frame(right)
        btnbar_container.pack(pady=10, fill="x")
        
        # First row: Action buttons
        btnbar_top = ttk.Frame(btnbar_container)
        btnbar_top.pack(fill="x", pady=(0, 5))
        
        add_btn = tk.Button(btnbar_top, text="➕ Ajouter", command=self._open_add_event_dialog,
                           bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'),
                           relief="flat", padx=20, pady=8, cursor="hand2", width=12)
        add_btn.pack(side="left", padx=3, fill="x", expand=True)
        
        edit_btn = tk.Button(btnbar_top, text="✏️ Modifier", command=self._open_edit_event_dialog,
                            bg="#2196F3", fg="white", font=('Arial', 10, 'bold'),
                            relief="flat", padx=20, pady=8, cursor="hand2", width=12)
        edit_btn.pack(side="left", padx=3, fill="x", expand=True)
        
        toggle_btn = tk.Button(btnbar_top, text="✔️ Fait", command=self._toggle_done,
                              bg="#FF9800", fg="white", font=('Arial', 10, 'bold'),
                              relief="flat", padx=20, pady=8, cursor="hand2", width=12)
        toggle_btn.pack(side="left", padx=3, fill="x", expand=True)
        
        # Second row: Delete and Return buttons
        btnbar_bottom = ttk.Frame(btnbar_container)
        btnbar_bottom.pack(fill="x")
        
        delete_btn = tk.Button(btnbar_bottom, text="🗑️ Supprimer", command=self._delete_event,
                              bg="#F44336", fg="white", font=('Arial', 10, 'bold'),
                              relief="flat", padx=20, pady=8, cursor="hand2")
        delete_btn.pack(side="left", padx=3, fill="x", expand=True)
        
        home_btn = tk.Button(btnbar_bottom, text="🏠 Retour", command=self.go_home,
                            bg="#9C27B0", fg="white", font=('Arial', 10, 'bold'),
                            relief="flat", padx=20, pady=8, cursor="hand2")
        home_btn.pack(side="left", padx=3, fill="x", expand=True)

        self.refresh_list()

    def _iso_to_disp(self, iso: str) -> str:
        try: 
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError) as e:
            print(f"[CALENDAR] Date conversion error: {e}")
            return iso

    def _disp_to_iso(self, disp: str) -> str | None:
        try: 
            return datetime.strptime(disp, "%d/%m/%Y").strftime("%Y-%m-%d")
        except (ValueError, TypeError) as e:
            print(f"[CALENDAR] Date conversion error: {e}")
            return None

    def _mark_events_on_calendar(self):
        self.calendar.calevent_remove('all')
        active = [c for c, v in self.filter_vars.items() if v.get()]
        events = self._get_all_events(active, include_past=True, include_done=True)
        today = date.today()

        for cat in active:
            self.calendar.tag_config(cat,
                background=self.CATEGORY_COLORS.get(cat, "#d3d3d3"),
                foreground="black")

        for e in events:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
            tag = e["category"]
            # Fade only future events marked as done
            if e["done"] and d >= today:
                tag = "done_future"
                self.calendar.tag_config(tag, background="#d3d3d3", foreground="black")
            try:
                self.calendar.calevent_create(d, "", tags=tag)
            except Exception as e:
                print(f"[CALENDAR] Error creating calendar event: {e}")
                continue

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        today = date.today().isoformat()
        cats = [c for c, v in self.filter_vars.items() if v.get()]
        show_old = self.show_past.get()

        # Get all events for the selected categories
        all_events = self._get_all_events(cats, include_past=True, include_done=True)
        
        displayed_count = 0
        pending_count = 0
        
        for rec in all_events:
            d = rec["date"]
            is_done = rec["done"]
            is_past = d < today
            is_today = d == today

            # Check if past event is within selected period (when showing past events)
            if is_past and show_old and is_done and not self._is_event_in_period(d):
                continue  # Skip done past events outside the selected period

            # Logic:
            # 1. Past events not marked as done: always shown (if in period)
            # 2. Past events marked as done: only shown if show_past is True AND in period
            # 3. Future events marked as done: shown but faded
            # 4. Future events not marked as done: shown normally

            if is_past:
                # Past events
                if is_done and not show_old:
                    continue 
            
            # Determine visual styling based on status
            if is_done:
                status_icon = "✅"
                tag = "done_past" if is_past else "done"
            else:
                status_icon = "⏳" if is_today else "○"
                if is_past and not is_done:
                    tag = "overdue"
                    pending_count += 1
                elif is_today:
                    tag = "today"
                    pending_count += 1
                else:
                    tag = "pending"
                    pending_count += 1
            
            # Get category color for visual indicator
            cat_color = self.CATEGORY_COLORS.get(rec["category"], "#95a5a6")
            
            # Insert with new column order: status | date | title | category
            self.tree.insert(
                "", "end",
                values=(
                    status_icon,
                    self._iso_to_disp(d),
                    rec["title"],
                    rec["category"]
                ),
                tags=(tag,)
            )
            displayed_count += 1

        # Update event count label
        if hasattr(self, 'event_count_label'):
            self.event_count_label.config(
                text=f"({displayed_count} événements, {pending_count} en attente)"
            )

        self._mark_events_on_calendar()

    def _open_add_event_dialog(self):
        sel = self.calendar.get_date()
        try: 
            pre = datetime.strptime(sel, "%m/%d/%y").strftime("%d/%m/%Y")
        except (ValueError, TypeError) as e:
            print(f"[CALENDAR] Date parsing error: {e}")
            pre = ""
        self._event_dialog("add", {
            "date": pre,
            "title": "",
            "category": self.filters[0],
            "description": "",
            "done": 0
        })

    def _open_edit_event_dialog(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo("Info", "Sélectionnez une ligne.")
        # New column order: status, date, titre, cat
        status, d_disp, title, cat = self.tree.item(sel[0])["values"]
        d_iso = self._disp_to_iso(d_disp)
        if d_iso is None:
            return messagebox.showerror("Erreur", "Date invalide.")
        row = self._find_event(d_iso, cat, title)
        if not row:
            return messagebox.showerror("Erreur", "Introuvable dans la base.")
        self._event_dialog("edit", row)

    def _event_dialog(self, mode: str, preset: dict):
        win = tk.Toplevel(self)
        win.grab_set()
        win.title("Événement")
        win.geometry("450x600")
        win.resizable(False, False)
        win.configure(bg='white')

        # Main container
        main_frame = ttk.Frame(win)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title section
        title_frame = ttk.LabelFrame(main_frame, text="Informations de base", padding=10)
        title_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(title_frame, text="Titre *").pack(anchor="w")
        e_title = ttk.Entry(title_frame, width=45)
        e_title.pack(fill="x", pady=(0, 10))

        # Date section
        ttk.Label(title_frame, text="Date (jj/mm/aaaa) *").pack(anchor="w")
        date_frame = ttk.Frame(title_frame)
        date_frame.pack(fill="x", pady=(0, 10))
        
        e_date = DateEntry(date_frame, width=25, date_pattern="dd/MM/yyyy")
        e_date.pack(side="left")

        # Category section
        ttk.Label(title_frame, text="Catégorie").pack(anchor="w")
        cat_var = tk.StringVar(value=self.filters[0])
        cat_combo = ttk.Combobox(title_frame, values=self.filters, textvariable=cat_var, 
                                state="readonly", width=42)
        cat_combo.pack(fill="x", pady=(0, 10))
        
        # Reminder section
        ttk.Label(title_frame, text="Rappel (jours avant)").pack(anchor="w")
        reminder_frame = ttk.Frame(title_frame)
        reminder_frame.pack(fill="x", pady=(0, 10))
        
        # Set default reminder based on category
        def get_default_reminder():
            cat = preset.get("category", self.filters[0]) if preset else self.filters[0]
            # Use loaded category defaults
            return self.category_reminder_defaults.get(cat, 1)
        
        reminder_var = tk.IntVar(value=preset.get("reminder_days", get_default_reminder()) if preset else get_default_reminder())
        reminder_spin = ttk.Spinbox(reminder_frame, from_=1, to=90, textvariable=reminder_var, width=10)
        reminder_spin.pack(side="left")
        ttk.Label(reminder_frame, text="jours").pack(side="left", padx=(5, 0))
        
        # Update reminder when category changes
        def on_category_change(*args):
            cat = cat_var.get()
            # Use loaded category defaults
            reminder_var.set(self.category_reminder_defaults.get(cat, 1))
        
        cat_var.trace_add("write", on_category_change)

        # Repeat pattern section
        ttk.Label(title_frame, text="Répétition").pack(anchor="w")
        repeat_options = [
            ("Aucune", "none"),
            ("Tous les jours", "daily"),
            ("Toutes les semaines", "weekly"),
            ("Tous les mois", "monthly"),
            ("Tous les ans", "yearly")
        ]
        repeat_var = tk.StringVar(value=preset.get("repeat_pattern", "none") if preset else "none")
        repeat_frame = ttk.Frame(title_frame)
        repeat_frame.pack(fill="x", pady=(0, 10))
        
        repeat_combo = ttk.Combobox(
            repeat_frame, 
            values=[label for label, _ in repeat_options], 
            state="readonly", 
            width=42
        )
        repeat_combo.pack(fill="x")
        
        # Set initial selection
        current_pattern = preset.get("repeat_pattern", "none") if preset else "none"
        for i, (label, value) in enumerate(repeat_options):
            if value == current_pattern:
                repeat_combo.current(i)
                break
        
        # Hint label
        hint_label = ttk.Label(
            repeat_frame, 
            text="💡 L'événement se répétera automatiquement",
            font=('Arial', 8),
            foreground='#666666'
        )
        hint_label.pack(anchor="w", pady=(2, 0))

        # Description section
        desc_frame = ttk.LabelFrame(main_frame, text="Description", padding=10)
        desc_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        e_desc = tk.Text(desc_frame, height=6, width=45, font=('Arial', 9))
        e_desc.pack(fill="both", expand=True)

        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="Statut", padding=10)
        status_frame.pack(fill="x", pady=(0, 10))
        
        is_done = tk.BooleanVar(value=preset.get("done", 0))
        ttk.Checkbutton(status_frame, text="Marquer comme terminé", variable=is_done).pack(anchor="w")

        # Pre-fill fields if editing
        if preset:
            e_title.insert(0, preset.get("title", ""))
            # For DateEntry, set the date properly instead of inserting text
            preset_date = preset.get("date", "")
            if preset_date:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(preset_date, "%Y-%m-%d").date()
                    e_date.set_date(date_obj)
                except ValueError:
                    pass  # Keep default date if invalid
            cat_var.set(preset.get("category", self.filters[0]))
            e_desc.insert("1.0", preset.get("description", "") or "")

        # Button section
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        def save():
            title = e_title.get().strip()
            d_iso = self._disp_to_iso(e_date.get().strip())
            if not title or not d_iso:
                return messagebox.showerror("Erreur", "Titre + date obligatoires.")
            
            reminder = reminder_var.get()
            
            # Get repeat pattern from combobox
            selected_label = repeat_combo.get()
            repeat_pattern = "none"
            for label, value in repeat_options:
                if label == selected_label:
                    repeat_pattern = value
                    break
            
            if mode == "add":
                self._add_event(
                    title,
                    d_iso,
                    cat_var.get(),
                    e_desc.get("1.0", "end").strip(),
                    1 if is_done.get() else 0,
                    reminder,
                    repeat_pattern
                )
            else:
                self._update_event(
                    preset,
                    title,
                    d_iso,
                    cat_var.get(),
                    e_desc.get("1.0", "end").strip(),
                    1 if is_done.get() else 0,
                    reminder,
                    repeat_pattern
                )
            win.destroy()
            self.refresh_list()

        save_btn = tk.Button(btn_frame, text="Enregistrer", command=save,
                            bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'),
                            relief="flat", padx=30, pady=8)
        save_btn.pack(side="right")

        cancel_btn = tk.Button(btn_frame, text="Annuler", command=win.destroy,
                              bg="#9E9E9E", fg="white", font=('Arial', 10),
                              relief="flat", padx=30, pady=8)
        cancel_btn.pack(side="right", padx=(0, 10))

    def _toggle_done(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo("Info", "Sélectionnez un événement.")
        # New column order: status, date, titre, cat
        status, d_disp, title, cat = self.tree.item(sel[0])["values"]
        d_iso = self._disp_to_iso(d_disp)
        if d_iso is None:
            return messagebox.showerror("Erreur", "Date invalide.")
        rec = self._find_event(d_iso, cat, title)
        if not rec:
            return messagebox.showerror("Erreur", "Introuvable dans la base.")
        self._update_event(
            rec,
            rec["title"],
            rec["date"],
            rec["category"],
            rec["description"],
            0 if rec["done"] else 1
        )
        self.refresh_list()

    def _delete_event(self):
        sel = self.tree.selection()
        if not sel:
            return
        # New column order: status, date, titre, cat
        status, d_disp, title, cat = self.tree.item(sel[0])["values"]
        if not messagebox.askyesno("Supprimer", f"Supprimer '{title}' ?"):
            return
        d_iso = self._disp_to_iso(d_disp)
        if d_iso is None:
            return messagebox.showerror("Erreur", "Date invalide.")
        self._delete_event_by_keys(d_iso, cat, title)
        self.refresh_list()
    
    def _on_calendar_date_click(self, event=None):
        """When user clicks a date on calendar, select first event for that date in the list."""
        try:
            # Get selected date from calendar
            selected_date = self.calendar.get_date()
            # Convert from m/d/y to d/m/Y format
            date_obj = datetime.strptime(selected_date, "%m/%d/%y")
            date_disp = date_obj.strftime("%d/%m/%Y")
            
            # Find first event with this date in the tree
            for item in self.tree.get_children():
                values = self.tree.item(item)["values"]
                if values and len(values) >= 2 and values[1] == date_disp:  # Column 1 is date
                    # Select and focus on this event
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    self.tree.see(item)  # Scroll to make it visible
                    break
        except Exception as e:
            print(f"[CALENDAR] Error selecting event from calendar: {e}")

    def _on_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        # New column order: status, date, titre, cat
        status, d_disp, title, cat = self.tree.item(sel[0])["values"]
        d_iso = self._disp_to_iso(d_disp)
        if d_iso is None:
            return messagebox.showerror("Erreur", "Date invalide.")
        rec = self._find_event(d_iso, cat, title)
        if not rec:
            return messagebox.showerror("Erreur", "Introuvable dans la base.")
        
        top = tk.Toplevel(self)
        top.grab_set()
        top.title("Détails de l'événement")
        top.geometry("450x400")
        top.configure(bg='white')

        # Main container
        main_frame = ttk.Frame(top)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        def L(label, text):
            label_frame = ttk.Frame(main_frame)
            label_frame.pack(fill="x", pady=5)
            
            ttk.Label(label_frame, text=label, font=('Arial', 10, 'bold')).pack(anchor="w")
            ttk.Label(label_frame, text=text, font=('Arial', 9)).pack(anchor="w", padx=10)

        L("Titre :", rec["title"])
        L("Date :", self._iso_to_disp(rec["date"]))
        L("Catégorie :", rec["category"])
        L("Description :", rec["description"] or "Aucune description")
        L("Statut :", "✅ Terminé" if rec["done"] else "❌ En cours")

        # Close button
        close_btn = tk.Button(main_frame, text="Fermer", command=top.destroy,
                             bg="#2196F3", fg="white", font=('Arial', 10, 'bold'),
                             relief="flat", padx=30, pady=8)
        close_btn.pack(pady=(20, 0))
