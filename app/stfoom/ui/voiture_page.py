import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry

# from stfoom.logicold import voitures_base as vb  # DISABLED: migrated to VoitureService
from app.connection import sync

class VoiturePage(ttk.Frame):
    GENRES = ["voiture", "partner", "camion", "remorque"]

    DATE_FIELDS = [
        ("date_visite", "Visite"),
        ("date_assurance", "Assurance"),
        ("date_vignette", "Vignette"),
        ("date_premiere_mise", "1ʳᵉ mise en circ.")
    ]

    def __init__(self, parent, container_or_go_home, go_home=None):
        super().__init__(parent)
        
        # ✅ PHASE 2G MIGRATION: Support dependency injection
        if go_home is not None:
            # New signature: VoiturePage(parent, di_container, go_home)
            self.di_container = container_or_go_home
            self.go_home = go_home
            self.voiture_service = None
            self.calendar_service = None
            
            # Try to get services from container
            try:
                self.voiture_service = self.di_container.get('voiture_service')
                print("[VOITURE PAGE] Using VoitureService via dependency injection")
            except Exception as e:
                print(f"[VOITURE PAGE] Could not get VoitureService: {e}")
                print("[VOITURE PAGE] Falling back to legacy mode")
            
            # Get calendar service for syncing voiture dates
            try:
                self.calendar_service = self.di_container.get('calendar_service')
                print("[VOITURE PAGE] Calendar sync enabled")
            except Exception as e:
                print(f"[VOITURE PAGE] Calendar service not available: {e}")
        else:
            # Old signature: VoiturePage(parent, go_home)
            self.go_home = container_or_go_home  # go_home is first parameter in old signature
            self.di_container = None
            self.voiture_service = None
            print("[VOITURE PAGE] Using legacy mode (no dependency injection)")

        # Load data using appropriate method
        self._load_data_method = self._load_data_service if self.voiture_service else self._load_data_legacy

        # Configure style for this page
        style = ttk.Style()
        style.configure('VoiturePage.TFrame', background='white')
        style.configure('VoitureHeader.TLabel', font=('Arial', 18, 'bold'), background='white')
        
        self.configure(style='VoiturePage.TFrame')

        # Header
        header_label = ttk.Label(self, text="Parc véhicules", style='VoitureHeader.TLabel')
        header_label.pack(pady=10)

        # Main content frame
        content_frame = ttk.Frame(self)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Treeview with scrollbar
        tree_frame = ttk.Frame(content_frame)
        tree_frame.pack(fill="both", expand=True, pady=5)

        self.tree = ttk.Treeview(tree_frame, show="headings", height=16)
        cols = ["id", "genre", "utilisateur", "matricule",
                "date_visite", "date_assurance", "date_vignette",
                "date_premiere_mise", "age"]
        self.tree["columns"] = cols
        
        # Configure columns with better headers
        column_headers = {
            "id": "ID",
            "genre": "Genre",
            "utilisateur": "Utilisateur", 
            "matricule": "Matricule",
            "date_visite": "Visite",
            "date_assurance": "Assurance",
            "date_vignette": "Vignette",
            "date_premiere_mise": "1ʳᵉ mise",
            "age": "Âge"
        }
        
        for c in cols:
            self.tree.heading(c, text=column_headers.get(c, c))
            self.tree.column(c, anchor="center", width=120)
        
        # Add scrollbar
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")

        # Button bar
        btnbar = ttk.Frame(content_frame)
        btnbar.pack(pady=10, fill="x")
        
        # Action buttons with modern styling
        add_btn = tk.Button(btnbar, text="➕ Ajouter", command=self._add,
                           bg="#4CAF50", fg="white", font=('Arial', 9, 'bold'),
                           relief="flat", padx=15, pady=5)
        add_btn.pack(side="left", padx=5)
        
        edit_btn = tk.Button(btnbar, text="✏️ Modifier", command=self._edit,
                            bg="#2196F3", fg="white", font=('Arial', 9, 'bold'),
                            relief="flat", padx=15, pady=5)
        edit_btn.pack(side="left", padx=5)
        
        delete_btn = tk.Button(btnbar, text="❌ Supprimer", command=self._delete,
                              bg="#F44336", fg="white", font=('Arial', 9, 'bold'),
                              relief="flat", padx=15, pady=5)
        delete_btn.pack(side="left", padx=5)
        
        # Return button
        home_btn = tk.Button(btnbar, text="🏠 Retour", command=self.go_home,
                            bg="#9C27B0", fg="white", font=('Arial', 9, 'bold'),
                            relief="flat", padx=15, pady=5)
        home_btn.pack(side="right", padx=5)

        self._refresh()

    @staticmethod
    def _iso_to_disp(iso: str) -> str:
        try:
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return ""

    @staticmethod
    def _disp_to_iso(disp: str) -> str:
        try:
            return datetime.strptime(disp, "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            return ""

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        
        # Use appropriate data loading method
        voitures = self._load_data_method()
        
        for v in voitures:
            # Convert dates for display
            for fld, _ in self.DATE_FIELDS:
                v[fld] = self._iso_to_disp(v[fld])
            
            self.tree.insert("", "end", values=list(v.values()))
    
    def _load_data_service(self):
        """Load data using VoitureService."""
        try:
            voitures = self.voiture_service.get_all_voitures()
            print(f"[VOITURE PAGE] Loaded {len(voitures)} vehicles via VoitureService")
            return voitures
        except Exception as e:
            print(f"[VOITURE PAGE] Error loading via service: {e}")
            return []
    
    def _load_data_legacy(self):
        """Load data using legacy voitures_base module."""
        try:
            voitures = self.voiture_service.get_all_voitures() if self.voiture_service else []
            # Add age computation for legacy mode
            for v in voitures:
                v['age'] = self.voiture_service.compute_age(v.get('date_premiere_mise', '')) if self.voiture_service else 0
            print(f"[VOITURE PAGE] Loaded {len(voitures)} vehicles via legacy module")
            return voitures
        except Exception as e:
            print(f"[VOITURE PAGE] Error loading via legacy: {e}")
            return []

    def _form(self, mode: str, preset: dict | None = None):
        dlg = tk.Toplevel(self)
        dlg.title("Véhicule")
        dlg.grab_set()
        dlg.geometry("420x600")
        dlg.resizable(True, True)
        dlg.configure(bg='white')

        # --- Scrollable main content ---
        content_frame = ttk.Frame(dlg)
        content_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(content_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Vehicle information section ---
        info_frame = ttk.LabelFrame(scrollable_frame, text="Informations du véhicule", padding=15)
        info_frame.pack(fill="x", pady=(0, 15))
        widgets = {}
        ttk.Label(info_frame, text="Genre *").pack(anchor="w")
        genre_var = tk.StringVar(value=self.GENRES[0])
        genre_combo = ttk.Combobox(info_frame, values=self.GENRES, textvariable=genre_var,
                                  state="readonly", width=35)
        genre_combo.pack(fill="x", pady=(0, 10))
        widgets["genre"] = genre_var
        ttk.Label(info_frame, text="Utilisateur").pack(anchor="w")
        util_entry = ttk.Entry(info_frame, width=35)
        util_entry.pack(fill="x", pady=(0, 10))
        widgets["utilisateur"] = util_entry
        ttk.Label(info_frame, text="Matricule *").pack(anchor="w")
        mat_entry = ttk.Entry(info_frame, width=35)
        mat_entry.pack(fill="x", pady=(0, 10))
        widgets["matricule"] = mat_entry
        # Dates section
        dates_frame = ttk.LabelFrame(scrollable_frame, text="Dates importantes", padding=15)
        dates_frame.pack(fill="x", pady=(0, 15))
        for key, label in self.DATE_FIELDS:
            ttk.Label(dates_frame, text=label).pack(anchor="w")
            de = DateEntry(dates_frame, date_pattern="dd/mm/yyyy", width=33)
            de.pack(fill="x", pady=(0, 10))
            widgets[key] = de
        # Pre-fill fields if editing
        if preset:
            for k, w in widgets.items():
                if k not in preset:
                    continue
                if isinstance(w, tk.StringVar):
                    w.set(preset[k])
                elif isinstance(w, DateEntry):
                    # ✅ FIX: Show current date value, not today's date
                    if preset[k] and preset[k] != "" and preset[k] != "None":
                        try:
                            # Convert ISO date (YYYY-MM-DD) to display format (DD/MM/YYYY)
                            date_obj = datetime.strptime(str(preset[k]), "%Y-%m-%d")
                            w.set_date(date_obj)
                        except (ValueError, TypeError):
                            # If conversion fails, keep DateEntry at its default (today)
                            pass
                else:
                    w.insert(0, preset[k])
        # --- Button section (always visible at bottom) ---
        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill="x", pady=(10, 0), side="bottom")
        def _save():
            data = {}
            for k, w in widgets.items():
                if isinstance(w, tk.StringVar):
                    data[k] = w.get()
                elif isinstance(w, DateEntry):
                    data[k] = self._disp_to_iso(w.get())
                else:
                    data[k] = w.get().strip()
            if not data["matricule"]:
                messagebox.showerror("Erreur", "Matricule obligatoire.")
                return
            
            # ✅ PHASE 2G MIGRATION: Use service layer when available
            success = False
            voiture_id = None
            if self.voiture_service:
                try:
                    if mode == "add":
                        result = self.voiture_service.create_voiture(data)
                        success = result is not None
                        voiture_id = result if isinstance(result, int) else None
                    else:
                        if preset is not None:
                            success = self.voiture_service.update_voiture(preset["id"], data)
                            voiture_id = preset["id"]
                    
                    if not success:
                        messagebox.showerror("Erreur", "Échec de l'enregistrement du véhicule.")
                        return
                        
                except Exception as e:
                    print(f"[VOITURE PAGE] Service error: {e}")
                    messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement: {e}")
                    return
            else:
                # Legacy mode fallback
                try:
                    if mode == "add":
                        result = self.voiture_service.add_voiture(data) if self.voiture_service else False
                        success = result is not None
                        voiture_id = result if isinstance(result, int) else None
                    else:
                        if preset is not None:
                            success = self.voiture_service.update_voiture(preset["id"], data) if self.voiture_service else False
                            voiture_id = preset["id"]
                    
                    if not success:
                        messagebox.showerror("Erreur", "Échec de l'enregistrement du véhicule.")
                        return
                        
                except Exception as e:
                    print(f"[VOITURE PAGE] Legacy error: {e}")
                    messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement: {e}")
                    return
            
            # Sync with calendar
            if voiture_id is not None:
                self._sync_voiture_to_calendar(voiture_id, data, data.get('matricule', 'Unknown'))
            
            # Data saved successfully
            dlg.destroy()
            self._refresh()
        save_btn = tk.Button(btn_frame, text="Enregistrer", command=_save,
                            bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'),
                            relief="flat", padx=30, pady=8)
        save_btn.pack(side="right")
        cancel_btn = tk.Button(btn_frame, text="Annuler", command=dlg.destroy,
                              bg="#9E9E9E", fg="white", font=('Arial', 10),
                              relief="flat", padx=30, pady=8)
        cancel_btn.pack(side="right", padx=(0, 10))

    def _add(self):
        self._form("add")

    def _edit(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Sélectionnez une ligne.")
            return
        data = dict(zip(self.tree["columns"], self.tree.item(sel[0])["values"]))
        for fld, _ in self.DATE_FIELDS:
            data[fld] = self._disp_to_iso(data[fld])
        self._form("edit", preset=data)

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        if not messagebox.askyesno("Supprimer", "Supprimer ce véhicule ?"):
            return
        
        vid = int(self.tree.item(sel[0])["values"][0])
        
        # ✅ PHASE 2G MIGRATION: Use service layer when available
        success = False
        if self.voiture_service:
            try:
                success = self.voiture_service.delete_voiture(vid)
                if not success:
                    messagebox.showerror("Erreur", "Échec de la suppression du véhicule.")
                    return
            except Exception as e:
                print(f"[VOITURE PAGE] Service delete error: {e}")
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
                return
        else:
            # Legacy mode fallback
            try:
                success = self.voiture_service.delete_voiture(vid) if self.voiture_service else False
                if not success:
                    messagebox.showerror("Erreur", "Échec de la suppression du véhicule.")
                    return
            except Exception as e:
                print(f"[VOITURE PAGE] Legacy delete error: {e}")
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
                return
        
        # Delete associated calendar events
        self._delete_voiture_calendar_events(vid)
        
        # Data deleted successfully
        self._refresh()
    
    def _sync_voiture_to_calendar(self, voiture_id: int, data: dict, matricule: str):
        """Sync voiture dates to calendar events with reminders."""
        if not self.calendar_service:
            print("[VOITURE PAGE] Calendar service not available, skipping sync")
            return
        
        try:
            # Delete old calendar events for this voiture
            self._delete_voiture_calendar_events(voiture_id)
            
            # Create calendar events for each date field (if not empty)
            date_fields = {
                'date_visite': 'Visite Technique',
                'date_assurance': 'Assurance',
                'date_vignette': 'Vignette',
                'date_premiere_mise': 'Première Mise en Circulation'
            }
            
            for field, label in date_fields.items():
                date_value = data.get(field, '').strip()
                if date_value and date_value != '':
                    # Date is already in ISO format (YYYY-MM-DD) from _save
                    title = f"Voiture {matricule} - {label}"
                    description = f"Rappel pour {label.lower()} du véhicule {matricule}"
                    
                    # Note: CalendarService.create_event doesn't support source/source_id/reminder_days yet
                    # We'll need to add those directly to the repository for now
                    self.calendar_service.create_event(title, date_value, 'Cars', description, 0)
                    
                    # Now update the event with additional fields using direct DB access
                    self._update_event_reminder_info(title, date_value, voiture_id, 10)
                    
                    print(f"[VOITURE PAGE] Created calendar event: {title} on {date_value}")
        
        except Exception as e:
            print(f"[VOITURE PAGE] Error syncing voiture to calendar: {e}")
    
    def _update_event_reminder_info(self, title: str, date_value: str, voiture_id: int, reminder_days: int):
        """Update event with source, source_id, and reminder_days using direct DB access."""
        try:
            from config.settings import get_db_path
            import sqlite3
            
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE calendar_events 
                SET source = 'voiture', source_id = ?, reminder_days = ?
                WHERE title = ? AND date = ? AND category = 'Cars'
            """, (voiture_id, reminder_days, title, date_value))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[VOITURE PAGE] Error updating event reminder info: {e}")
    
    def _delete_voiture_calendar_events(self, voiture_id: int):
        """Delete all calendar events linked to this voiture."""
        if not self.calendar_service:
            return
        
        try:
            # Get all events
            all_events = self.calendar_service.get_all_events(include_past=True, include_done=True)
            for event in all_events:
                if event.get('source') == 'voiture' and event.get('source_id') == voiture_id:
                    self.calendar_service.delete_event(event['id'])
                    print(f"[VOITURE PAGE] Deleted calendar event: {event.get('title', 'Unknown')}")
        
        except Exception as e:
            print(f"[VOITURE PAGE] Error deleting voiture calendar events: {e}")
