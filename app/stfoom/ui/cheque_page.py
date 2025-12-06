"""
Cheque Page UI
==============
Complete UI for cheque management with bank integration.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, List
import logging
from datetime import datetime, date
from tkcalendar import DateEntry

from ..services.cheque_service import ChequeService
from ..services.bank_service import BankService
from ..services.cheque_print_service import ChequePrintService
from ..data.cheque_print_repository import ChequePrintRepository
from ..data.bank_repository import BankRepository
from ..ui.shared_widgets import format_money
from ..ui.permission_utils import check_ui_permission

logger = logging.getLogger(__name__)

# Forward declaration to satisfy static analyzers; real class is defined later
try:
    PrintChequeDialog  # type: ignore[name-defined]
except Exception:
    class PrintChequeDialog:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            pass

class ChequePage(ttk.Frame):
    """Complete cheque management interface"""
    
    def __init__(self, parent, container=None, go_home=None):
        super().__init__(parent)
        
        # Store go_home callback
        self.go_home = go_home
        
        # Services
        self.cheque_service = ChequeService()
        self.cheque_print_service = ChequePrintService(ChequePrintRepository())
        
        # Try to get bank service from container
        if container and hasattr(container, 'get'):
            try:
                self.bank_service = container.get('bank_service')
                logger.info("ChequeService connected to bank service via container")
            except Exception:
                self.bank_service = BankService(BankRepository())
                logger.info("ChequeService created fallback bank service")
        else:
            self.bank_service = BankService(BankRepository())
        
        # UI state
        self.selected_bank_id = None
        self.banks_list = []
        
        # Create UI
        self.create_ui()
        self.load_banks()
        
        logger.info("ChequePage initialized")
    
    def create_ui(self):
        """Create the complete UI"""
        # Header with return button
        header_frame = tk.Frame(self, bg="#34495e")
        header_frame.pack(fill="x")
        
        # Return button
        if self.go_home:
            tk.Button(header_frame, text="⬅️ Retour", command=self.go_home,
                     bg="#34495e", fg="white", font=("Arial", 10, "bold"),
                     relief="flat", padx=15, pady=5).pack(side="left", padx=10, pady=5)
        
        # Main title
        tk.Label(header_frame, text="🏦 Gestion des Chèques", 
                font=("Arial", 16, "bold"), fg="white", bg="#34495e").pack(side="left", padx=10, pady=10)
        
        # Top controls: Bank selection and quick stats
        self.create_top_controls()
        
        # Quick action buttons
        self.create_action_buttons()
        
        # Cheque statistics and alerts
        self.create_stats_section()
        
        # Main cheque list
        self.create_cheque_list()
        
        # Bottom status
        self.create_status_bar()
    
    def create_top_controls(self):
        """Create bank selection and quick controls"""
        controls_frame = tk.LabelFrame(self, text="🏛️ Sélection de Banque")
        controls_frame.pack(fill="x", padx=10, pady=5)
        
        # Bank selection row
        bank_row = tk.Frame(controls_frame)
        bank_row.pack(fill="x", padx=10, pady=5)
        
        tk.Label(bank_row, text="Banque:", font=("Arial", 10, "bold")).pack(side="left")
        
        self.bank_var = tk.StringVar()
        self.bank_combo = ttk.Combobox(bank_row, textvariable=self.bank_var, 
                                      state="readonly", width=30)
        self.bank_combo.pack(side="left", padx=(5, 10))
        self.bank_combo.bind("<<ComboboxSelected>>", self.on_bank_changed)
        
        # Quick info labels
        self.bank_info_label = tk.Label(bank_row, text="", fg="#2980b9")
        self.bank_info_label.pack(side="left", padx=10)
        
        # Config button
        tk.Button(bank_row, text="⚙️ Config Carnet", command=self.configure_carnet,
                 bg="#f39c12", fg="white").pack(side="right", padx=5)
    
    def create_action_buttons(self):
        """Create quick action buttons"""
        actions_frame = tk.Frame(self)
        actions_frame.pack(fill="x", padx=10, pady=5)

        # Left side buttons
        left_buttons = tk.Frame(actions_frame)
        left_buttons.pack(side="left")

        tk.Button(
            left_buttons,
            text="✅ Nouveau Chèque",
            command=self.nouveau_cheque,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack(side="left", padx=2)

        tk.Button(
            left_buttons,
            text="❌ Annuler Chèque",
            command=self.annuler_cheque,
            bg="#e74c3c",
            fg="white",
        ).pack(side="left", padx=2)

        tk.Button(
            left_buttons,
            text="💰 Marquer Encaissé",
            command=self.marquer_encaisse,
            bg="#8e44ad",
            fg="white",
        ).pack(side="left", padx=2)

        # Create encours (pending) cheque without known amount
        tk.Button(
            left_buttons,
            text="🟨 Chèque 'En cours'",
            command=self.nouveau_cheque_encours,
            bg="#f1c40f",
            fg="black",
        ).pack(side="left", padx=2)

        # Middle buttons - Bank import
        middle_buttons = tk.Frame(actions_frame)
        middle_buttons.pack(side="left", padx=(20, 10))

        tk.Button(
            middle_buttons,
            text="📥 Importer de la Banque",
            command=self.import_from_bank,
            bg="#f39c12",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack(side="left", padx=2)

        # Right side buttons
        right_buttons = tk.Frame(actions_frame)
        right_buttons.pack(side="right")

        tk.Button(
            right_buttons,
            text="📊 Statistiques",
            command=self.show_statistics,
            bg="#3498db",
            fg="white",
        ).pack(side="right", padx=2)

        tk.Button(
            right_buttons,
            text="🖨️ Imprimer",
            command=self.print_cheque_dialog,
            bg="#2ecc71",
            fg="white",
        ).pack(side="right", padx=2)

        tk.Button(
            right_buttons,
            text="🧩 Plan Feuille",
            command=self.open_plan_editor,
            bg="#e67e22",
            fg="white",
        ).pack(side="right", padx=2)

        tk.Button(
            right_buttons,
            text="🔄 Actualiser",
            command=self.refresh_data,
            bg="#95a5a6",
            fg="white",
        ).pack(side="right", padx=2)
    
    def create_stats_section(self):
        """Create statistics and alert section"""
        self.stats_frame = tk.LabelFrame(self, text="📈 État du Carnet")
        self.stats_frame.pack(fill="x", padx=10, pady=5)
        
        # Alert area
        self.alert_frame = tk.Frame(self.stats_frame)
        self.alert_frame.pack(fill="x", padx=5, pady=2)
        
        # Stats labels
        stats_row = tk.Frame(self.stats_frame)
        stats_row.pack(fill="x", padx=5, pady=2)
        
        self.next_cheque_label = tk.Label(stats_row, text="", font=("Arial", 9, "bold"))
        self.next_cheque_label.pack(side="left")
        
        self.remaining_label = tk.Label(stats_row, text="", font=("Arial", 9))
        self.remaining_label.pack(side="right")
    
    def create_cheque_list(self):
        """Create the main cheque list with treeview"""
        list_frame = tk.LabelFrame(self, text="📋 Liste des Chèques (du plus récent au plus ancien)")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create treeview
        columns = ("numero", "date", "montant", "fournisseur", "beneficiaire", "statut", "notes")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # Define headings and columns
        headings = {
            "numero": "N° Chèque",
            "date": "Date",
            "montant": "Montant (TND)",
            "fournisseur": "Fournisseur",
            "beneficiaire": "Bénéficiaire",
            "statut": "Statut",
            "notes": "Notes"
        }
        
        for col, heading in headings.items():
            self.tree.heading(col, text=heading)
            if col == "numero":
                self.tree.column(col, width=80, anchor="center")
            elif col == "date":
                self.tree.column(col, width=90, anchor="center")
            elif col == "montant":
                self.tree.column(col, width=100, anchor="e")
            elif col == "fournisseur":
                self.tree.column(col, width=150, anchor="w")
            elif col == "beneficiaire":
                self.tree.column(col, width=120, anchor="w")
            elif col == "statut":
                self.tree.column(col, width=80, anchor="center")
            elif col == "notes":
                self.tree.column(col, width=120, anchor="w")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Configure tags for colors
        # Normal/paid in green, cancelled in red, encours in yellow
        self.tree.tag_configure("normal", background="#e8f5e8", foreground="#2e7d32")
        self.tree.tag_configure("cancelled", background="#ffebee", foreground="#c62828")
        self.tree.tag_configure("paid", background="#e8f5e8", foreground="#2e7d32")
        self.tree.tag_configure("pending", background="#fff8e1", foreground="#f57f17")

        # Bind double-click
        self.tree.bind("<Double-1>", self.on_cheque_double_click)
    
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = tk.Label(self, text="Prêt", relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")
    
    def load_banks(self):
        """Load available banks"""
        try:
            self.banks_list = self.bank_service.get_all_banks()
            
            bank_names = []
            for bank in self.banks_list:
                name = bank.get('nom_banque', f'Banque {bank["id"]}')
                bank_names.append(name)
            
            self.bank_combo['values'] = bank_names
            
            if self.banks_list:
                self.bank_combo.set(bank_names[0])
                self.selected_bank_id = self.banks_list[0]['id']
                self.on_bank_changed()
            
        except Exception as e:
            logger.error(f"Error loading banks: {e}")
            messagebox.showerror("Erreur", f"Impossible de charger les banques: {e}")
    
    def on_bank_changed(self, event=None):
        """Handle bank selection change"""
        selected_name = self.bank_var.get()
        
        # Find selected bank
        for bank in self.banks_list:
            if bank.get('nom_banque', f'Banque {bank["id"]}') == selected_name:
                self.selected_bank_id = bank['id']
                break
        
        if self.selected_bank_id:
            self.refresh_data()
            # Start periodic auto-refresh
            self._schedule_refresh()
    
    def refresh_data(self):
        """Refresh all data for selected bank"""
        if not self.selected_bank_id:
            return
        try:
            # Sync with bank transactions so cheque module reflects changes
            try:
                self.cheque_service.sync_with_bank(self.selected_bank_id)
            except Exception as e:
                logger.warning(f"Cheque sync failed: {e}")
            # Update bank info
            self.update_bank_info()
            # Update cheque list
            self.update_cheque_list()
            # Update stats
            self.update_statistics()
            # Status text
            self.status_bar.config(text=f"Données actualisées - {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            self.status_bar.config(text=f"Erreur: {e}")
        finally:
            # Reschedule next auto refresh regardless of success
            self._schedule_refresh()

    def _schedule_refresh(self, interval_ms: int = 8000):
        """Schedule periodic auto-refresh of the cheque list"""
        try:
            if hasattr(self, '_refresh_job') and self._refresh_job:
                self.after_cancel(self._refresh_job)
        except Exception:
            pass
        self._refresh_job = self.after(interval_ms, self.refresh_data)
    
    def update_bank_info(self):
        """Update bank information display"""
        try:
            # Get bank details
            bank_name = self.bank_var.get()
            
            # Get cheque availability
            availability = self.cheque_service.check_cheque_availability(self.selected_bank_id)
            
            if availability.get('needs_config'):
                info_text = "⚠️ Configuration requise"
                self.bank_info_label.config(text=info_text, fg="#e67e22")
            else:
                next_num = availability['next_number']
                remaining = availability['cheques_remaining']
                info_text = f"Prochain: #{next_num} | Reste: {remaining}"
                
                if availability.get('need_alert'):
                    self.bank_info_label.config(text=info_text, fg="#e74c3c")
                else:
                    self.bank_info_label.config(text=info_text, fg="#27ae60")
                
        except Exception as e:
            logger.error(f"Error updating bank info: {e}")
    
    def update_cheque_list(self):
        """Update the cheque list"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Get cheques for selected bank
            cheques = self.cheque_service.get_all_cheques(self.selected_bank_id)
            
            # Populate tree
            for cheque in cheques:
                values = (
                    cheque['numero_cheque'],
                    cheque['date_formatted'],
                    cheque['montant_formatted'],
                    cheque['fournisseur'],
                    cheque['beneficiaire'] or '',
                    cheque['statut_formatted'],
                    cheque['notes'] or ''
                )
                
                self.tree.insert("", "end", values=values, tags=[cheque['color_tag']])
            
        except Exception as e:
            logger.error(f"Error updating cheque list: {e}")
    
    def update_statistics(self):
        """Update statistics section"""
        try:
            # Clear alerts
            for widget in self.alert_frame.winfo_children():
                widget.destroy()
            
            # Check for alerts
            availability = self.cheque_service.check_cheque_availability(self.selected_bank_id)
            
            if availability.get('need_alert'):
                alert_msg = availability.get('alert_message', '')
                alert_label = tk.Label(self.alert_frame, text=alert_msg, 
                                     fg="#e74c3c", font=("Arial", 9, "bold"),
                                     wraplength=600)
                alert_label.pack()
            
            # Update next cheque info
            if not availability.get('needs_config'):
                suggestion = self.cheque_service.get_next_cheque_suggestion(self.selected_bank_id)
                self.next_cheque_label.config(text=suggestion['message'])
                
                remaining = availability['cheques_remaining']
                self.remaining_label.config(text=f"Chèques restants: {remaining}")
            else:
                self.next_cheque_label.config(text="Configuration requise")
                self.remaining_label.config(text="")
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    def nouveau_cheque(self):
        """Create new cheque dialog"""
        if not self.selected_bank_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une banque")
            return
        
        dialog = ChequeDialog(self, self.cheque_service, self.selected_bank_id)
        if dialog.result:
            self.refresh_data()
    
    def annuler_cheque(self):
        """Cancel selected cheque"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attention", "Veuillez sélectionner un chèque")
            return
        
        # Get cheque info
        item = self.tree.item(selected[0])
        numero = item['values'][0]
        
        # Confirm cancellation
        if messagebox.askyesno("Confirmation", 
                              f"Êtes-vous sûr de vouloir annuler le chèque #{numero}?"):
            
            motif = tk.simpledialog.askstring("Motif d'annulation", 
                                             "Motif de l'annulation (optionnel):")
            
            # Find cheque ID
            cheques = self.cheque_service.get_all_cheques(self.selected_bank_id)
            cheque_id = None
            for cheque in cheques:
                if cheque['numero_cheque'] == numero:
                    cheque_id = cheque['id']
                    break
            
            if cheque_id:
                result = self.cheque_service.annuler_cheque(cheque_id, motif or '')
                if result['success']:
                    messagebox.showinfo("Succès", result['message'])
                    self.refresh_data()
                else:
                    messagebox.showerror("Erreur", result['error'])
    
    def marquer_encaisse(self):
        """Mark cheque as cashed"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attention", "Veuillez sélectionner un chèque")
            return
        # Find cheque id by numero
        item = self.tree.item(selected[0])
        numero = item['values'][0]
        cheques = self.cheque_service.get_all_cheques(self.selected_bank_id)
        cheque_id = None
        for cheque in cheques:
            if cheque['numero_cheque'] == numero:
                cheque_id = cheque['id']
                break
        if not cheque_id:
            messagebox.showerror("Erreur", "Chèque introuvable")
            return
        res = self.cheque_service.marquer_encaisse(cheque_id)
        if res.get('success'):
            messagebox.showinfo("Succès", res.get('message'))
            self.refresh_data()
        else:
            messagebox.showerror("Erreur", res.get('error'))

    def nouveau_cheque_encours(self):
        """Create a new 'encours' cheque (unknown amount)"""
        if not self.selected_bank_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une banque")
            return
        # Simple prompt
        win = tk.Toplevel(self)
        win.title("Nouveau Chèque (En cours)")
        win.geometry("380x260")
        win.grab_set()
        win.resizable(False, False)
        frm = tk.Frame(win)
        frm.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(frm, text="Numéro:").grid(row=0, column=0, sticky="w")
        num_var = tk.StringVar()
        tk.Entry(frm, textvariable=num_var).grid(row=0, column=1, sticky="ew")
        tk.Label(frm, text="Date:").grid(row=1, column=0, sticky="w", pady=(8,0))
        date_entry = DateEntry(frm, date_pattern='dd/mm/yyyy')
        date_entry.grid(row=1, column=1, sticky="ew", pady=(8,0))
        tk.Label(frm, text="Fournisseur:").grid(row=2, column=0, sticky="w", pady=(8,0))
        four_var = tk.StringVar()
        tk.Entry(frm, textvariable=four_var).grid(row=2, column=1, sticky="ew", pady=(8,0))
        tk.Label(frm, text="Notes:").grid(row=3, column=0, sticky="w", pady=(8,0))
        notes = tk.Text(frm, height=3)
        notes.grid(row=3, column=1, sticky="ew", pady=(8,0))
        frm.columnconfigure(1, weight=1)
        btns = tk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12,0))
        def do_save():
            try:
                numero = int(num_var.get().strip())
            except Exception:
                messagebox.showerror("Erreur", "Numéro invalide")
                return
            fournisseur = four_var.get().strip()
            if not fournisseur:
                messagebox.showerror("Erreur", "Fournisseur requis")
                return
            res = self.cheque_service.creer_cheque_encours(numero, self.selected_bank_id, date_entry.get(), fournisseur, notes.get("1.0", "end-1c"))
            if res.get('success'):
                messagebox.showinfo("Succès", res.get('message'))
                win.destroy()
                self.refresh_data()
            else:
                messagebox.showerror("Erreur", res.get('error'))
        tk.Button(btns, text="Annuler", command=win.destroy).pack(side="right", padx=(6,0))
        tk.Button(btns, text="Créer", command=do_save, bg="#f1c40f").pack(side="right")
    
    def configure_carnet(self):
        """Configure cheque carnet"""
        if not self.selected_bank_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une banque")
            return
        
        dialog = CarnetConfigDialog(self, self.cheque_service, self.selected_bank_id)
        if dialog.result:
            self.refresh_data()
    
    def show_statistics(self):
        """Show detailed statistics"""
        if not self.selected_bank_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner une banque")
            return
        
        dialog = ChequeStatsDialog(self, self.cheque_service, self.selected_bank_id)
    
    def import_from_bank(self):
        """Import outgoing cheques from bank transactions"""
        try:
            # Show confirmation dialog
            result = messagebox.askyesno(
                "Importation des Chèques",
                "Cette opération va importer automatiquement tous les chèques sortants "
                "depuis les transactions bancaires.\n\n"
                "Les chèques déjà existants ne seront pas importés à nouveau.\n"
                "Seuls les chèques avec numéros valides seront importés.\n\n"
                "Continuer?"
            )
            
            if not result:
                return
            
            # Show progress
            progress_window = tk.Toplevel(self)
            progress_window.title("Importation en cours...")
            progress_window.geometry("400x150")
            progress_window.grab_set()
            progress_window.resizable(False, False)
            progress_window.transient(self)
            
            # Center progress window
            progress_window.update_idletasks()
            x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
            y = (progress_window.winfo_screenheight() // 2) - (150 // 2)
            progress_window.geometry(f"400x150+{x}+{y}")
            
            # Progress content
            progress_frame = tk.Frame(progress_window)
            progress_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            tk.Label(progress_frame, text="🏦 Importation des chèques de la banque...",
                    font=("Arial", 12, "bold")).pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
            progress_bar.pack(fill="x", pady=10)
            progress_bar.start()
            
            status_label = tk.Label(progress_frame, text="Analyse des transactions bancaires...",
                                   font=("Arial", 10))
            status_label.pack(pady=5)
            
            # Update UI
            progress_window.update()
            
            # Perform import
            import_result = self.cheque_service.import_outgoing_cheques_from_bank(self.selected_bank_id)
            
            # Stop progress
            progress_bar.stop()
            progress_window.destroy()
            
            # Show results
            if import_result['success']:
                details = import_result.get('details', {})
                message = f"Importation terminée!\n\n"
                message += f"• Chèques trouvés: {details.get('total_found', 0)}\n"
                message += f"• Chèques importés: {details.get('imported', 0)}\n"
                message += f"• Chèques ignorés: {details.get('skipped', 0)}\n"
                
                if details.get('errors', 0) > 0:
                    message += f"• Erreurs: {details.get('errors', 0)}\n"
                
                if import_result.get('errors'):
                    message += f"\nDétails des erreurs:\n"
                    for error in import_result['errors'][:5]:  # Show max 5 errors
                        message += f"- {error}\n"
                    if len(import_result['errors']) > 5:
                        message += f"... et {len(import_result['errors']) - 5} autres erreurs"
                
                messagebox.showinfo("Importation Terminée", message)
                
                # Refresh the UI if any cheques were imported
                if details.get('imported', 0) > 0:
                    self.refresh_data()
            else:
                messagebox.showerror("Erreur d'Importation", 
                                   f"Erreur lors de l'importation:\n{import_result.get('error', 'Erreur inconnue')}")
            
        except Exception as e:
            logger.error(f"Error in import_from_bank: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de l'importation: {str(e)}")
    
    def on_cheque_double_click(self, event):
        """Handle double-click on cheque"""
        selected = self.tree.selection()
        if selected:
            # Show cheque details or edit dialog
            messagebox.showinfo("Info", "Fonction à implémenter: Édition de chèque")

    def open_plan_editor(self):
        PlanSheetEditor(self, self.cheque_print_service)

    def print_cheque_dialog(self):
        PrintChequeDialog(self, self.cheque_print_service)


class ChequeDialog:
    """Dialog for creating/editing cheques"""
    
    def __init__(self, parent, cheque_service: ChequeService, banque_id: int, cheque_data: Dict = None):
        self.parent = parent
        self.cheque_service = cheque_service
        self.banque_id = banque_id
        self.cheque_data = cheque_data
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Nouveau Chèque" if not cheque_data else "Modifier Chèque")
        self.window.geometry("400x450")
        self.window.grab_set()
        self.window.resizable(False, False)
        
        self.create_ui()
        self.window.transient(parent)
        
        # Focus on first field
        self.numero_entry.focus()
        
        parent.wait_window(self.window)
    
    def create_ui(self):
        """Create dialog UI"""
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Get next suggested number
        suggestion = self.cheque_service.get_next_cheque_suggestion(self.banque_id)
        
        # Cheque number
        tk.Label(main_frame, text="Numéro de chèque:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.numero_var = tk.StringVar()
        self.numero_entry = tk.Entry(main_frame, textvariable=self.numero_var, font=("Arial", 11))
        self.numero_entry.pack(fill="x", pady=(2, 10))
        
        if not suggestion.get('needs_config'):
            self.numero_var.set(str(suggestion['suggested_number']))
            
        # Suggestion label
        if not suggestion.get('needs_config'):
            suggestion_text = suggestion['message']
            color = "#e67e22" if suggestion.get('is_filling_gap') else "#27ae60"
            tk.Label(main_frame, text=suggestion_text, fg=color, font=("Arial", 8)).pack(anchor="w")
        
        # Date
        tk.Label(main_frame, text="Date du chèque:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 2))
        self.date_entry = DateEntry(main_frame, date_pattern='dd/mm/yyyy', font=("Arial", 11))
        self.date_entry.pack(fill="x", pady=(2, 10))
        
        # Amount
        tk.Label(main_frame, text="Montant (TND):", font=("Arial", 10, "bold")).pack(anchor="w")
        self.montant_var = tk.StringVar()
        self.montant_entry = tk.Entry(main_frame, textvariable=self.montant_var, font=("Arial", 11))
        self.montant_entry.pack(fill="x", pady=(2, 10))
        
        # Fournisseur
        tk.Label(main_frame, text="Fournisseur:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.fournisseur_var = tk.StringVar()
        self.fournisseur_entry = tk.Entry(main_frame, textvariable=self.fournisseur_var, font=("Arial", 11))
        self.fournisseur_entry.pack(fill="x", pady=(2, 10))
        
        # Beneficiaire
        tk.Label(main_frame, text="Bénéficiaire (optionnel):", font=("Arial", 10)).pack(anchor="w")
        self.beneficiaire_var = tk.StringVar()
        self.beneficiaire_entry = tk.Entry(main_frame, textvariable=self.beneficiaire_var, font=("Arial", 11))
        self.beneficiaire_entry.pack(fill="x", pady=(2, 10))
        
        # Notes
        tk.Label(main_frame, text="Notes (optionnel):", font=("Arial", 10)).pack(anchor="w")
        self.notes_text = tk.Text(main_frame, height=3, font=("Arial", 10))
        self.notes_text.pack(fill="x", pady=(2, 15))
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        tk.Button(button_frame, text="Annuler", command=self.cancel,
                 bg="#95a5a6", fg="white").pack(side="right", padx=(5, 0))
        
        tk.Button(button_frame, text="Créer Chèque", command=self.save,
                 bg="#27ae60", fg="white", font=("Arial", 10, "bold")).pack(side="right")
    
    def save(self):
        """Save the cheque"""
        try:
            # Validate inputs
            numero_text = self.numero_var.get().strip()
            if not numero_text:
                messagebox.showerror("Erreur", "Le numéro de chèque est requis")
                return
            
            try:
                numero = int(numero_text)
            except ValueError:
                messagebox.showerror("Erreur", "Le numéro de chèque doit être un nombre")
                return
            
            montant_text = self.montant_var.get().strip().replace(',', '.')
            if not montant_text:
                messagebox.showerror("Erreur", "Le montant est requis")
                return
            
            try:
                montant = float(montant_text)
            except ValueError:
                messagebox.showerror("Erreur", "Le montant doit être un nombre")
                return
            
            fournisseur = self.fournisseur_var.get().strip()
            if not fournisseur:
                messagebox.showerror("Erreur", "Le fournisseur est requis")
                return
            
            # Get other values
            date_cheque = self.date_entry.get()
            beneficiaire = self.beneficiaire_var.get().strip()
            notes = self.notes_text.get("1.0", "end-1c").strip()
            
            # Create cheque
            result = self.cheque_service.create_cheque(
                numero, self.banque_id, date_cheque, montant,
                fournisseur, beneficiaire, notes
            )
            
            if result['success']:
                messagebox.showinfo("Succès", result['message'])
                self.result = result
                self.window.destroy()
            else:
                messagebox.showerror("Erreur", result['error'])
                
        except Exception as e:
            logger.error(f"Error saving cheque: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
    
    def cancel(self):
        """Cancel dialog"""
        self.window.destroy()


class CarnetConfigDialog:
    """Dialog for configuring cheque carnet"""
    
    def __init__(self, parent, cheque_service: ChequeService, banque_id: int):
        self.parent = parent
        self.cheque_service = cheque_service
        self.banque_id = banque_id
        self.result = None
        
        # Get current config
        self.current_config = cheque_service.cheque_repository.get_cheque_config(banque_id)
        
        self.window = tk.Toplevel(parent)
        self.window.title("Configuration du Carnet de Chèques")
        self.window.geometry("400x300")
        self.window.grab_set()
        self.window.resizable(False, False)
        
        self.create_ui()
        self.window.transient(parent)
        
        parent.wait_window(self.window)
    
    def create_ui(self):
        """Create dialog UI"""
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        tk.Label(main_frame, text="Configuration du Carnet", 
                font=("Arial", 14, "bold"), fg="#2c3e50").pack(pady=(0, 15))
        
        # Current config info
        if self.current_config:
            info_frame = tk.LabelFrame(main_frame, text="Configuration actuelle")
            info_frame.pack(fill="x", pady=(0, 15))
            
            tk.Label(info_frame, text=f"Dernier numéro: {self.current_config['carne_dernier_numero']}").pack(anchor="w", padx=5, pady=2)
            tk.Label(info_frame, text=f"Alerte mini chèques: {self.current_config['mini_cheque_alert']}").pack(anchor="w", padx=5, pady=2)
        
        # New config
        config_frame = tk.LabelFrame(main_frame, text="Nouvelle configuration")
        config_frame.pack(fill="x", pady=(0, 15))
        
        # Last number
        tk.Label(config_frame, text="Dernier numéro du carnet:", font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=(5, 2))
        self.last_number_var = tk.StringVar()
        self.last_number_entry = tk.Entry(config_frame, textvariable=self.last_number_var, font=("Arial", 11))
        self.last_number_entry.pack(fill="x", padx=5, pady=(2, 5))
        
        if self.current_config:
            self.last_number_var.set(str(self.current_config['carne_dernier_numero']))
        
        # Mini cheque alert
        tk.Label(config_frame, text="Alerte mini chèques:", font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=(5, 2))
        self.mini_alert_var = tk.StringVar()
        self.mini_alert_entry = tk.Entry(config_frame, textvariable=self.mini_alert_var, font=("Arial", 11))
        self.mini_alert_entry.pack(fill="x", padx=5, pady=(2, 5))
        
        if self.current_config:
            self.mini_alert_var.set(str(self.current_config['mini_cheque_alert']))
        else:
            self.mini_alert_var.set("10")
        
        # Help text
        help_text = "L'alerte vous préviendra quand il ne restera que ce nombre de chèques."
        tk.Label(config_frame, text=help_text, font=("Arial", 8), fg="#7f8c8d").pack(anchor="w", padx=5, pady=(0, 5))
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        tk.Button(button_frame, text="Annuler", command=self.cancel,
                 bg="#95a5a6", fg="white").pack(side="right", padx=(5, 0))
        
        tk.Button(button_frame, text="Enregistrer", command=self.save,
                 bg="#27ae60", fg="white", font=("Arial", 10, "bold")).pack(side="right")
    
    def save(self):
        """Save configuration"""
        try:
            # Validate inputs
            last_number_text = self.last_number_var.get().strip()
            if not last_number_text:
                messagebox.showerror("Erreur", "Le dernier numéro est requis")
                return
            
            try:
                last_number = int(last_number_text)
            except ValueError:
                messagebox.showerror("Erreur", "Le dernier numéro doit être un nombre")
                return
            
            mini_alert_text = self.mini_alert_var.get().strip()
            if not mini_alert_text:
                messagebox.showerror("Erreur", "L'alerte mini chèques est requise")
                return
            
            try:
                mini_alert = int(mini_alert_text)
            except ValueError:
                messagebox.showerror("Erreur", "L'alerte mini chèques doit être un nombre")
                return
            
            # Save configuration
            result = self.cheque_service.configure_cheque_carnet(
                self.banque_id, last_number, mini_alert
            )
            
            if result['success']:
                messagebox.showinfo("Succès", result['message'])
                self.result = result
                self.window.destroy()
            else:
                messagebox.showerror("Erreur", result['error'])
                
        except Exception as e:
            logger.error(f"Error saving carnet config: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
    
    def cancel(self):
        """Cancel dialog"""
        self.window.destroy()


class ChequeStatsDialog:
    """Dialog showing detailed cheque statistics"""
    
    def __init__(self, parent, cheque_service: ChequeService, banque_id: int):
        self.parent = parent
        self.cheque_service = cheque_service
        self.banque_id = banque_id
        
        self.window = tk.Toplevel(parent)
        self.window.title("Statistiques des Chèques")
        self.window.geometry("500x400")
        self.window.grab_set()
        
        self.create_ui()
        self.window.transient(parent)
        
        parent.wait_window(self.window)
    
    def create_ui(self):
        """Create statistics UI"""
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Get statistics
        stats = self.cheque_service.get_cheque_statistics(self.banque_id)
        
        # Title
        tk.Label(main_frame, text="📊 Statistiques des Chèques", 
                font=("Arial", 16, "bold"), fg="#2c3e50").pack(pady=(0, 15))
        
        # Statistics grid
        stats_frame = tk.Frame(main_frame)
        stats_frame.pack(fill="x", pady=(0, 15))
        
        # Create stats display
        stats_data = [
            ("Total chèques:", stats['total_cheques']),
            ("Chèques émis:", stats['cheques_emis']),
            ("Chèques annulés:", stats['cheques_annules']),
            ("Chèques encaissés:", stats['cheques_encaisses']),
            ("Montant total:", stats['montant_total_formatted']),
            ("Montant annulé:", stats['montant_annule_formatted'])
        ]
        
        for i, (label, value) in enumerate(stats_data):
            row = i // 2
            col = i % 2
            
            stat_frame = tk.Frame(stats_frame)
            stat_frame.grid(row=row, column=col, sticky="ew", padx=5, pady=2)
            
            tk.Label(stat_frame, text=label, font=("Arial", 10)).pack(side="left")
            tk.Label(stat_frame, text=str(value), font=("Arial", 10, "bold")).pack(side="right")
        
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        
        # Missing numbers
        if stats['has_missing_numbers']:
            missing_frame = tk.LabelFrame(main_frame, text="⚠️ Numéros manquants")
            missing_frame.pack(fill="x", pady=(15, 0))
            
            missing_text = ", ".join(map(str, stats['missing_numbers'][:10]))
            if len(stats['missing_numbers']) > 10:
                missing_text += f" ... (+{len(stats['missing_numbers']) - 10} autres)"
            
            tk.Label(missing_frame, text=missing_text, wraplength=450, 
                    fg="#e67e22", font=("Arial", 9)).pack(padx=5, pady=5)
        
        # Close button
        tk.Button(main_frame, text="Fermer", command=self.window.destroy,
                 bg="#95a5a6", fg="white").pack(pady=(15, 0))


class PlanSheetEditor:
    """Dialog to configure positions of 5 fields on an 8 x 17.5 cm sheet"""
    def __init__(self, parent, print_service: ChequePrintService):
        self.parent = parent
        self.print_service = print_service
        self.repo = print_service.repo
        self.result = None

        self.window = tk.Toplevel(parent)
        self.window.title("Plan Feuille Chèque (8 x 17.5 cm)")
        self.window.geometry("1000x580")
        self.window.grab_set()
        self.window.resizable(False, False)
        self.window.transient(parent)
        # Track unsaved changes
        self._dirty = False

        self._create_ui()
        # Close handling and shortcuts
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.bind('<Control-s>', lambda e: self._save())
        parent.wait_window(self.window)

    def _create_ui(self):
        main = tk.Frame(self.window)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # Printer selection at top
        printer_frame = tk.LabelFrame(main, text="Imprimante")
        printer_frame.pack(fill="x", pady=(0,10))
        
        inner_frame = tk.Frame(printer_frame)
        inner_frame.pack(fill="x", padx=10, pady=8)
        
        tk.Label(inner_frame, text="Sélectionner l'imprimante:").pack(side="left", padx=(0,8))
        self.var_printer = tk.StringVar()
        printers = []
        try:
            printers = self.print_service.list_printers()
        except Exception:
            printers = []
        self.cmb_printer = ttk.Combobox(inner_frame, textvariable=self.var_printer, values=printers, state="readonly", width=40)
        self.cmb_printer.pack(side="left", padx=(0,8))
        self.cmb_printer.bind('<<ComboboxSelected>>', self._load_printer_settings)
        
        if printers:
            self.cmb_printer.current(0)
            self._load_printer_settings()
        
        tk.Button(inner_frame, text="🔄 Rafraîchir", command=self._refresh_printers).pack(side="left")

        # Settings section
        settings_frame = tk.LabelFrame(main, text="Paramètres d'impression")
        settings_frame.pack(fill="x", pady=(0,10))
        
        settings_inner = tk.Frame(settings_frame)
        settings_inner.pack(fill="x", padx=10, pady=8)
        
        # Load current settings
        try:
            current_settings = self.repo.get_settings()
        except Exception:
            current_settings = {}
        
        # Page size
        size_frame = tk.LabelFrame(settings_inner, text="Taille du chèque (mm)")
        size_frame.grid(row=0, column=0, sticky="ew", padx=(0,5), pady=(0,5))
        tk.Label(size_frame, text="Largeur:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.var_page_w = tk.StringVar(value=str(current_settings.get('page_width_mm', 175.0)))
        tk.Entry(size_frame, textvariable=self.var_page_w, width=8).grid(row=0, column=1, sticky="w", padx=5)
        tk.Label(size_frame, text="Hauteur:").grid(row=0, column=2, sticky="w", padx=5)
        self.var_page_h = tk.StringVar(value=str(current_settings.get('page_height_mm', 80.0)))
        tk.Entry(size_frame, textvariable=self.var_page_h, width=8).grid(row=0, column=3, sticky="w", padx=5)
        
        # Orientation & Rotation
        or_frame = tk.LabelFrame(settings_inner, text="Orientation & Rotation")
        or_frame.grid(row=0, column=1, sticky="ew", padx=(0,0), pady=(0,5))
        tk.Label(or_frame, text="Orientation:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.var_page_orient = tk.StringVar(value=str(current_settings.get('orientation', 'portrait')))
        ttk.Combobox(or_frame, textvariable=self.var_page_orient, values=["portrait","landscape"], state="readonly", width=10).grid(row=0, column=1, sticky="w", padx=5)
        tk.Label(or_frame, text="Rotation:").grid(row=0, column=2, sticky="w", padx=5)
        self.var_page_rot = tk.StringVar(value=str(current_settings.get('rotate_deg', 0)))
        tk.Entry(or_frame, textvariable=self.var_page_rot, width=6).grid(row=0, column=3, sticky="w", padx=5)
        
        # Special options
        self.var_sideways_montant = tk.BooleanVar(value=bool(current_settings.get('sideways_from_montant', False)))
        tk.Checkbutton(or_frame, text="Sideways from montant", variable=self.var_sideways_montant).grid(row=1, column=0, columnspan=2, sticky="w", padx=5)
        self.var_center_page = tk.BooleanVar(value=bool(current_settings.get('center_on_page', False)))
        tk.Checkbutton(or_frame, text="Center on page", variable=self.var_center_page).grid(row=1, column=2, columnspan=2, sticky="w", padx=5)
        
        # Vertical align
        tk.Label(or_frame, text="V-align:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.var_valign = tk.StringVar(value=str(current_settings.get('vertical_align', 'extreme-top')))
        ttk.Combobox(or_frame, textvariable=self.var_valign, values=["extreme-top","top","center","bottom"], state="readonly", width=10).grid(row=2, column=1, sticky="w", padx=5)
        tk.Label(or_frame, text="V-offset:").grid(row=2, column=2, sticky="w", padx=5)
        self.var_voffset = tk.StringVar(value=str(current_settings.get('vertical_offset_mm', 0.0)))
        tk.Entry(or_frame, textvariable=self.var_voffset, width=6).grid(row=2, column=3, sticky="w", padx=5)
        
        # Margins & Shift
        ms_frame = tk.LabelFrame(settings_inner, text="Marges et Décalage (mm)")
        ms_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,5))
        tk.Label(ms_frame, text="Mode marges:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.var_margins_mode = tk.StringVar(value=str(current_settings.get('margins_mode', 'zero')))
        ttk.Combobox(ms_frame, textvariable=self.var_margins_mode, values=["zero","physical","custom"], state="readonly", width=10).grid(row=0, column=1, sticky="w", padx=5)
        
        tk.Label(ms_frame, text="Marge gauche:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.var_margin_l = tk.StringVar(value=str(current_settings.get('margin_left_mm', 0.0)))
        tk.Entry(ms_frame, textvariable=self.var_margin_l, width=8).grid(row=1, column=1, sticky="w", padx=5)
        tk.Label(ms_frame, text="Marge haut:").grid(row=1, column=2, sticky="w", padx=5)
        self.var_margin_t = tk.StringVar(value=str(current_settings.get('margin_top_mm', 0.0)))
        tk.Entry(ms_frame, textvariable=self.var_margin_t, width=8).grid(row=1, column=3, sticky="w", padx=5)
        
        tk.Label(ms_frame, text="Décalage X:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.var_shift_x = tk.StringVar(value=str(current_settings.get('shift_x_mm', 0.0)))
        tk.Entry(ms_frame, textvariable=self.var_shift_x, width=8).grid(row=2, column=1, sticky="w", padx=5)
        tk.Label(ms_frame, text="Décalage Y:").grid(row=2, column=2, sticky="w", padx=5)
        self.var_shift_y = tk.StringVar(value=str(current_settings.get('shift_y_mm', 0.0)))
        tk.Entry(ms_frame, textvariable=self.var_shift_y, width=8).grid(row=2, column=3, sticky="w", padx=5)
        
        settings_inner.columnconfigure(0, weight=1)
        settings_inner.columnconfigure(1, weight=1)

        # Left: canvas scaled preview
        preview_frame = tk.LabelFrame(main, text="Aperçu")
        preview_frame.pack(side="left", padx=(0,10), pady=5)

        # Use a scale for px per mm to simulate a sheet; 5 px/mm = ~127 dpi preview
        self.scale_px_mm = 5
        # Landscape sheet: 175 x 80 mm
        self.sheet_w_mm, self.sheet_h_mm = 175.0, 80.0
        self.canvas_w = int(self.sheet_w_mm * self.scale_px_mm)
        self.canvas_h = int(self.sheet_h_mm * self.scale_px_mm)

        self.canvas = tk.Canvas(preview_frame, width=self.canvas_w, height=self.canvas_h, bg="white")
        self.canvas.pack(padx=6, pady=6)
        # Border
        self.canvas.create_rectangle(2, 2, self.canvas_w-2, self.canvas_h-2, outline="#bdc3c7")

        # Right: controls
        control = tk.LabelFrame(main, text="Contrôles")
        control.pack(side="left", fill="y")

        tk.Button(control, text="↩️ Réinitialiser", command=self._reset).pack(fill="x", padx=6, pady=(8,4))
        tk.Button(control, text="⏮️ Restaurer (DB → JSON)", command=self._restore_from_db).pack(fill="x", padx=6, pady=4)
        tk.Button(control, text="💾 Save", command=self._save).pack(fill="x", padx=6, pady=4)
        tk.Button(control, text="✅ Save & Close", command=self._save_and_close).pack(fill="x", padx=6, pady=4)
        tk.Button(control, text="👁️ Prévisualiser (auto-save)", command=self._preview).pack(fill="x", padx=6, pady=4)
        tk.Button(control, text="Fermer", command=self._on_close).pack(fill="x", padx=6, pady=(4,8))

        # Status label
        self.status_label = tk.Label(control, text="Ready", anchor="w", fg="#2c3e50")
        self.status_label.pack(fill="x", padx=6, pady=(8,4))

        # Draggable and resizable field boxes
        self.items = {}
        layout = self.repo.get_layout()
        fields = [
            ("montant_number", "Montant (123,456.789)"),
            ("montant_letters_1", "Montant lettres (ligne 1)"),
            ("montant_letters_2", "Montant lettres (ligne 2)"),
            ("beneficiaire", "Bénéficiaire"),
            ("date", "Date"),
            ("lieu", "Lieu"),
        ]
        for key, label in fields:
            cfg = layout.get(key, {"x": 10.0, "y": 10.0, "w": 60.0, "h": 10.0})
            x = int(float(cfg.get("x", 10.0)) * self.scale_px_mm)
            y = int(float(cfg.get("y", 10.0)) * self.scale_px_mm)
            w = int(float(cfg.get("w", 60.0)) * self.scale_px_mm)
            h = int(float(cfg.get("h", 10.0)) * self.scale_px_mm)
            item = self.canvas.create_rectangle(x, y, x+w, y+h, outline="#2ecc71")
            text = self.canvas.create_text(x+4, y+min(12, h//2), text=label, anchor="w")
            handle = self.canvas.create_rectangle(x+w-6, y+h-6, x+w, y+h, fill="#2ecc71", outline="#2ecc71")
            self.items[key] = (item, text, handle)
            self._bind_drag(item)
            self._bind_drag(text)
            self._bind_resize(handle, key)

        # Drag state
        self._drag_item = None
        self._drag_start = (0,0)

    def _bind_drag(self, item_id):
        self.canvas.tag_bind(item_id, "<ButtonPress-1>", self._on_press)
        self.canvas.tag_bind(item_id, "<B1-Motion>", self._on_drag)
        self.canvas.tag_bind(item_id, "<ButtonRelease-1>", self._on_release)

    def _on_press(self, event):
        self._drag_item = self.canvas.find_closest(event.x, event.y)[0]
        self._drag_start = (event.x, event.y)

    def _on_drag(self, event):
        if not self._drag_item:
            return
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        # Move selected and its pair (rect/text)
        for rect, text, handle in self.items.values():
            if self._drag_item in (rect, text):
                other = rect if self._drag_item == text else text
                # move selected, the other, and the resize handle together
                self.canvas.move(self._drag_item, dx, dy)
                self.canvas.move(other, dx, dy)
                self.canvas.move(handle, dx, dy)
                break
        self._drag_start = (event.x, event.y)
        # Mark as dirty
        self._dirty = True
        if hasattr(self, 'status_label'):
            self.status_label.config(text="Modified (unsaved)", fg="#e67e22")

    def _on_release(self, event):
        self._drag_item = None

    def _reset(self):
        # Reset to defaults with adjustable sizes and two letter lines
        layout = {
            "montant_number": {"x": 130.0, "y": 12.0, "w": 40.0, "h": 10.0},
            "montant_letters_1": {"x": 18.0, "y": 26.0, "w": 100.0, "h": 10.0},
            "montant_letters_2": {"x": 18.0, "y": 38.0, "w": 140.0, "h": 10.0},
            "beneficiaire": {"x": 18.0, "y": 20.0, "w": 120.0, "h": 10.0},
            "date": {"x": 130.0, "y": 20.0, "w": 40.0, "h": 10.0},
            "lieu": {"x": 18.0, "y": 12.0, "w": 60.0, "h": 10.0},
        }
        self.repo.save_layout(layout)
        # Move and resize existing items to defaults without recreating the UI
        for key, (rect, text, handle) in self.items.items():
            x_px = int(layout[key]["x"] * self.scale_px_mm)
            y_px = int(layout[key]["y"] * self.scale_px_mm)
            w_px = int(layout[key]["w"] * self.scale_px_mm)
            h_px = int(layout[key]["h"] * self.scale_px_mm)
            self.canvas.coords(rect, x_px, y_px, x_px + w_px, y_px + h_px)
            self.canvas.coords(text, x_px + 4, y_px + min(12, h_px//2))
            self.canvas.coords(handle, x_px + w_px - 6, y_px + h_px - 6, x_px + w_px, y_px + h_px)
        self._dirty = True
        if hasattr(self, 'status_label'):
            self.status_label.config(text="Reset done (unsaved)", fg="#e67e22")

    def _gather_positions(self):
        layout = {}
        for key, (rect, text, handle) in self.items.items():
            x1, y1, x2, y2 = self.canvas.coords(rect)
            x_mm = round(x1 / self.scale_px_mm, 2)
            y_mm = round(y1 / self.scale_px_mm, 2)
            w_mm = round((x2 - x1) / self.scale_px_mm, 2)
            h_mm = round((y2 - y1) / self.scale_px_mm, 2)
            layout[key] = {"x": x_mm, "y": y_mm, "w": w_mm, "h": h_mm}
        return layout

    def _bind_resize(self, handle_id, key):
        state = {"drag": False, "start": (0,0)}
        def on_press(event):
            state["drag"] = True
            state["start"] = (event.x, event.y)
        def on_motion(event):
            if not state["drag"]:
                return
            dx = event.x - state["start"][0]
            dy = event.y - state["start"][1]
            rect, text, handle = self.items[key]
            x1, y1, x2, y2 = self.canvas.coords(rect)
            new_w = max(20, (x2 - x1) + dx)
            new_h = max(12, (y2 - y1) + dy)
            self.canvas.coords(rect, x1, y1, x1 + new_w, y1 + new_h)
            self.canvas.coords(text, x1 + 4, y1 + min(12, int(new_h)//2))
            self.canvas.coords(handle, x1 + new_w - 6, y1 + new_h - 6, x1 + new_w, y1 + new_h)
            state["start"] = (event.x, event.y)
            self._dirty = True
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Modified (unsaved)", fg="#e67e22")
        def on_release(event):
            state["drag"] = False
        self.canvas.tag_bind(handle_id, "<ButtonPress-1>", on_press)
        self.canvas.tag_bind(handle_id, "<B1-Motion>", on_motion)
        self.canvas.tag_bind(handle_id, "<ButtonRelease-1>", on_release)

    def _refresh_printers(self):
        """Refresh the list of printers"""
        printers = []
        try:
            printers = self.print_service.list_printers()
        except Exception:
            printers = []
        self.cmb_printer['values'] = printers
        if printers:
            self.cmb_printer.current(0)
            self._load_printer_settings()

    def _load_printer_settings(self, event=None):
        """Load settings for the selected printer"""
        printer_name = self.var_printer.get().strip()
        if not printer_name:
            return
        
        # Load printer-specific settings
        try:
            all_settings = self.repo.get_settings()
            printer_key = f"printer_{printer_name}"
            if printer_key in all_settings:
                # Printer has specific settings saved
                settings = all_settings[printer_key]
                if hasattr(self, 'status_label'):
                    self.status_label.config(text=f"Chargé: {printer_name}", fg="#3498db")
            else:
                # Use default settings
                settings = all_settings
                if hasattr(self, 'status_label'):
                    self.status_label.config(text=f"{printer_name} (défaut)", fg="#95a5a6")
            
            # Update all settings fields
            self.var_page_w.set(str(settings.get('page_width_mm', 175.0)))
            self.var_page_h.set(str(settings.get('page_height_mm', 80.0)))
            self.var_page_orient.set(str(settings.get('orientation', 'portrait')))
            self.var_page_rot.set(str(settings.get('rotate_deg', 0)))
            self.var_sideways_montant.set(bool(settings.get('sideways_from_montant', False)))
            self.var_center_page.set(bool(settings.get('center_on_page', False)))
            self.var_valign.set(str(settings.get('vertical_align', 'extreme-top')))
            self.var_voffset.set(str(settings.get('vertical_offset_mm', 0.0)))
            self.var_margins_mode.set(str(settings.get('margins_mode', 'zero')))
            self.var_margin_l.set(str(settings.get('margin_left_mm', 0.0)))
            self.var_margin_t.set(str(settings.get('margin_top_mm', 0.0)))
            self.var_shift_x.set(str(settings.get('shift_x_mm', 0.0)))
            self.var_shift_y.set(str(settings.get('shift_y_mm', 0.0)))
            
        except Exception as e:
            print(f"Error loading settings: {e}")

    def _save(self):
        """Save layout and settings for the selected printer"""
        printer_name = self.var_printer.get().strip()
        
        # Save layout (this is global for now)
        layout = self._gather_positions()
        self.repo.save_layout(layout)
        
        # Collect all settings from the form
        try:
            page_w = float(self.var_page_w.get().strip())
        except Exception:
            page_w = 175.0
        try:
            page_h = float(self.var_page_h.get().strip())
        except Exception:
            page_h = 80.0
        try:
            rot = int(self.var_page_rot.get().strip())
        except Exception:
            rot = 0
        try:
            ml = float(self.var_margin_l.get().strip())
        except Exception:
            ml = 0.0
        try:
            mt = float(self.var_margin_t.get().strip())
        except Exception:
            mt = 0.0
        try:
            sx = float(self.var_shift_x.get().strip())
        except Exception:
            sx = 0.0
        try:
            sy = float(self.var_shift_y.get().strip())
        except Exception:
            sy = 0.0
        try:
            vo = float(self.var_voffset.get().strip())
        except Exception:
            vo = 0.0
        
        settings = {
            'page_width_mm': page_w,
            'page_height_mm': page_h,
            'orientation': self.var_page_orient.get().strip(),
            'rotate_deg': rot,
            'sideways_from_montant': bool(self.var_sideways_montant.get()),
            'center_on_page': bool(self.var_center_page.get()),
            'vertical_align': self.var_valign.get().strip(),
            'vertical_offset_mm': vo,
            'margins_mode': self.var_margins_mode.get().strip(),
            'margin_left_mm': ml,
            'margin_top_mm': mt,
            'shift_x_mm': sx,
            'shift_y_mm': sy
        }
        
        # If sideways-from-montant is requested, compute rotation
        if settings.get('sideways_from_montant'):
            settings['orientation'] = 'landscape'
            try:
                pos_num = layout.get('montant_number', {"x": 10.0})
                x_mm = float(pos_num.get('x', 10.0))
                center = page_w / 2.0
                settings['rotate_deg'] = 90 if x_mm >= center else -90
            except Exception:
                pass
        
        # If a printer is selected, save settings for that printer
        if printer_name:
            try:
                all_settings = self.repo.get_settings()
                printer_key = f"printer_{printer_name}"
                all_settings[printer_key] = settings
                self.repo.save_settings(all_settings)
                
                if hasattr(self, 'status_label'):
                    self.status_label.config(text=f"Enregistré pour: {printer_name}", fg="#27ae60")
            except Exception as e:
                print(f"Error saving printer settings: {e}")
                if hasattr(self, 'status_label'):
                    self.status_label.config(text="Erreur lors de la sauvegarde", fg="#e74c3c")
        else:
            # No printer selected, save as default
            try:
                self.repo.save_settings(settings)
                if hasattr(self, 'status_label'):
                    self.status_label.config(text="Enregistré (défaut)", fg="#27ae60")
            except Exception as e:
                print(f"Error saving settings: {e}")
        
        self._dirty = False
        try:
            # Non-blocking UX; keep info light
            self.window.bell()
        except Exception:
            pass

    def _restore_from_db(self):
        try:
            p = self.repo.restore_user_json_from_db(backup_existing=True)
            # Reload layout from repository and apply to canvas
            layout = self.repo.get_layout()
            for key, (rect, text, handle) in self.items.items():
                cfg = layout.get(key, {"x": 10.0, "y": 10.0, "w": 60.0, "h": 10.0})
                x_px = int(float(cfg.get("x", 10.0)) * self.scale_px_mm)
                y_px = int(float(cfg.get("y", 10.0)) * self.scale_px_mm)
                w_px = int(float(cfg.get("w", 60.0)) * self.scale_px_mm)
                h_px = int(float(cfg.get("h", 10.0)) * self.scale_px_mm)
                self.canvas.coords(rect, x_px, y_px, x_px + w_px, y_px + h_px)
                self.canvas.coords(text, x_px + 4, y_px + min(12, h_px//2))
                self.canvas.coords(handle, x_px + w_px - 6, y_px + h_px - 6, x_px + w_px, y_px + h_px)
            self._dirty = False
            if hasattr(self, 'status_label'):
                self.status_label.config(text=f"Restored from DB → JSON{f' ({p.name})' if p else ''}", fg="#27ae60")
            try:
                self.window.bell()
            except Exception:
                pass
            messagebox.showinfo("Plan Feuille", "Plan et paramètres restaurés depuis la base de données.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de restaurer: {e}")

    def _save_and_close(self):
        self._save()
        self.window.destroy()

    def _preview(self):
        # Save current positions and settings first so preview reflects them
        try:
            # Collect settings
            try:
                page_w = float(self.var_page_w.get().strip())
            except Exception:
                page_w = 175.0
            try:
                page_h = float(self.var_page_h.get().strip())
            except Exception:
                page_h = 80.0
            try:
                rot = int(self.var_page_rot.get().strip())
            except Exception:
                rot = 0
            try:
                ml = float(self.var_margin_l.get().strip())
            except Exception:
                ml = 0.0
            try:
                mt = float(self.var_margin_t.get().strip())
            except Exception:
                mt = 0.0
            try:
                sx = float(self.var_shift_x.get().strip())
            except Exception:
                sx = 0.0
            try:
                sy = float(self.var_shift_y.get().strip())
            except Exception:
                sy = 0.0
            try:
                vo = float(self.var_voffset.get().strip())
            except Exception:
                vo = 0.0
            
            layout = self._gather_positions()
            
            temp_settings = {
                'page_width_mm': page_w,
                'page_height_mm': page_h,
                'orientation': self.var_page_orient.get().strip(),
                'rotate_deg': rot,
                'sideways_from_montant': bool(self.var_sideways_montant.get()),
                'center_on_page': bool(self.var_center_page.get()),
                'vertical_align': self.var_valign.get().strip(),
                'vertical_offset_mm': vo,
                'margins_mode': self.var_margins_mode.get().strip(),
                'margin_left_mm': ml,
                'margin_top_mm': mt,
                'shift_x_mm': sx,
                'shift_y_mm': sy
            }
            
            # If sideways-from-montant is requested, compute rotation
            if temp_settings.get('sideways_from_montant'):
                temp_settings['orientation'] = 'landscape'
                try:
                    pos_num = layout.get('montant_number', {"x": 10.0})
                    x_mm = float(pos_num.get('x', 10.0))
                    center = page_w / 2.0
                    temp_settings['rotate_deg'] = 90 if x_mm >= center else -90
                except Exception:
                    pass
            
            # Save temporarily
            self.repo.save_layout(layout)
            original_settings = self.repo.get_settings()
            self.repo.save_settings(temp_settings)
            
            self._dirty = False
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Auto-saved before preview", fg="#27ae60")
        except Exception as e:
            print(f"Error saving before preview: {e}")
            original_settings = None
        
        # Build sample data
        data = {
            'montant_number': '# 1 234.567 #',
            'montant_letters': 'mille deux cent trente-quatre dinars et 567 millimes',
            'beneficiaire': 'SOCIETE TUNISIENNE',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'lieu': 'TUNIS',
        }
        
        try:
            self.print_service.print_cheque(data, preview_only=True, orientation=None)
        finally:
            # Restore original settings
            if original_settings:
                try:
                    self.repo.save_settings(original_settings)
                except Exception:
                    pass

    def _on_close(self):
        if getattr(self, '_dirty', False):
            if messagebox.askyesno("Enregistrer les modifications", "Voulez-vous enregistrer les changements?"):
                try:
                    self._save()
                except Exception:
                    pass
        self.window.destroy()

class PrintChequeDialog:
    """Dialog to input cheque fields and print using configured layout"""
    def __init__(self, parent, print_service: ChequePrintService):
        self.parent = parent
        self.print_service = print_service
        self.repo = print_service.repo
        self.window = tk.Toplevel(parent)
        self.window.title("Imprimer Chèque")
        self.window.geometry("460x320")
        self.window.grab_set()
        self.window.resizable(False, False)
        self.window.transient(parent)
        self._create_ui()
        parent.wait_window(self.window)

    def _create_ui(self):
        f = tk.Frame(self.window)
        f.pack(fill="both", expand=True, padx=14, pady=14)
        
        # Amount number
        tk.Label(f, text="Montant (nombre):").grid(row=0, column=0, sticky="w")
        self.var_amount = tk.StringVar()
        tk.Entry(f, textvariable=self.var_amount).grid(row=0, column=1, sticky="ew")
        
        # Printer selection
        tk.Label(f, text="Imprimante:").grid(row=1, column=0, sticky="w")
        self.var_printer = tk.StringVar()
        printers = []
        try:
            printers = self.print_service.list_printers()
        except Exception:
            printers = []
        self.cmb_printer = ttk.Combobox(f, textvariable=self.var_printer, values=printers, state="readonly")
        self.cmb_printer.grid(row=1, column=1, sticky="ew")
        
        if printers:
            self.cmb_printer.current(0)
        else:
            try:
                default_name = self.print_service.get_default_printer()
            except Exception:
                default_name = None
            if default_name:
                self.var_printer.set(default_name)
            else:
                self.var_printer.set("")
                tk.Label(f, text="(Aucune imprimante détectée)", fg="#c0392b").grid(row=1, column=2, sticky="w")
        
        # Refresh button
        tk.Button(f, text="Rafraîchir", command=self._refresh_printers).grid(row=1, column=2, sticky="e")
        # Hint below
        tk.Label(f, text="Astuce: Vous pouvez taper #100#").grid(row=2, column=1, sticky="w")
        # Beneficiary
        tk.Label(f, text="Bénéficiaire:").grid(row=3, column=0, sticky="w", pady=(8,0))
        self.var_benef = tk.StringVar()
        tk.Entry(f, textvariable=self.var_benef).grid(row=3, column=1, sticky="ew", pady=(8,0))
        # Date
        tk.Label(f, text="Date:").grid(row=4, column=0, sticky="w", pady=(8,0))
        self.var_date = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        tk.Entry(f, textvariable=self.var_date).grid(row=4, column=1, sticky="ew", pady=(8,0))
        # Location
        tk.Label(f, text="Lieu:").grid(row=5, column=0, sticky="w", pady=(8,0))
        self.var_lieu = tk.StringVar(value="TUNIS")
        tk.Entry(f, textvariable=self.var_lieu).grid(row=5, column=1, sticky="ew", pady=(8,0))

        f.columnconfigure(1, weight=1)

        # Bottom buttons
        btns = tk.Frame(f)
        btns.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14,0))
        # Right side: preview/print
        tk.Button(btns, text="Aperçu", command=self._preview).pack(side="right", padx=(6,0))
        tk.Button(btns, text="Imprimer", command=self._print, bg="#2ecc71", fg="white").pack(side="right")

    def _refresh_printers(self):
        printers = []
        try:
            printers = self.print_service.list_printers()
        except Exception:
            printers = []
        self.cmb_printer['values'] = printers
        if printers:
            self.cmb_printer.current(0)
        else:
            try:
                default_name = self.print_service.get_default_printer()
            except Exception:
                default_name = None
            if default_name:
                self.var_printer.set(default_name)
            else:
                self.var_printer.set("")

    def _build_data(self) -> Dict[str, str]:
        raw = self.var_amount.get().strip()
        # Accept formats like '#100#', '1 234.567', '1234,567' and normalize
        clean = raw.replace('#', '').replace(' ', '').replace(',', '.')
        try:
            amt = float(clean)
        except Exception:
            amt = 0.0
        letters = self.print_service.amount_to_words_fr(amt)
        # Use space as thousands separator and dot for decimals
        formatted = f"{amt:,.3f}".replace(',', ' ')
        display = f"# {formatted} #"
        return {
            'montant_number': display,
            'montant_letters': letters,
            'beneficiaire': self.var_benef.get().strip(),
            'date': self.var_date.get().strip(),
            'lieu': self.var_lieu.get().strip(),
        }

    def _preview(self):
        data = self._build_data()
        printer = self.var_printer.get().strip() or None
        
        # Load printer-specific settings if available
        if printer:
            settings = self._get_printer_settings(printer)
            original_settings = self.repo.get_settings()
            try:
                self.repo.save_settings(settings)
                res = self.print_service.print_cheque(data, preview_only=True, 
                                                     orientation=None, printer_name=printer, rotate_deg=None)
                if not res.get('success'):
                    messagebox.showerror("Erreur", f"Aperçu impossible: {res.get('error')}")
            finally:
                self.repo.save_settings(original_settings)
        else:
            res = self.print_service.print_cheque(data, preview_only=True, 
                                                 orientation=None, printer_name=None, rotate_deg=None)
            if not res.get('success'):
                messagebox.showerror("Erreur", f"Aperçu impossible: {res.get('error')}")

    def _print(self):
        data = self._build_data()
        printer = self.var_printer.get().strip() or None
        
        # Load printer-specific settings if available
        if printer:
            settings = self._get_printer_settings(printer)
            original_settings = self.repo.get_settings()
            try:
                self.repo.save_settings(settings)
                res = self.print_service.print_cheque(data, preview_only=False, 
                                                     orientation=None, printer_name=printer, rotate_deg=None)
                if res.get('success'):
                    messagebox.showinfo("Impression", "Chèque envoyé à l'imprimante.")
                    self.window.destroy()
                else:
                    messagebox.showerror("Erreur", f"Impression impossible: {res.get('error')}")
            finally:
                self.repo.save_settings(original_settings)
        else:
            res = self.print_service.print_cheque(data, preview_only=False, 
                                                 orientation=None, printer_name=None, rotate_deg=None)
            if res.get('success'):
                messagebox.showinfo("Impression", "Chèque envoyé à l'imprimante.")
                self.window.destroy()
            else:
                messagebox.showerror("Erreur", f"Impression impossible: {res.get('error')}")
    
    def _get_printer_settings(self, printer_name: str) -> Dict:
        """Get settings for a specific printer"""
        try:
            all_settings = self.repo.get_settings()
            printer_key = f"printer_{printer_name}"
            if printer_key in all_settings:
                return all_settings[printer_key]
            return all_settings
        except Exception:
            return {}


class PrintSettingsDialog:
    """Dialog to configure print settings: size, margins, shifts, orientation, rotation"""
    def __init__(self, parent, print_service: ChequePrintService):
        self.parent = parent
        self.print_service = print_service
        self.repo = print_service.repo
        self.window = tk.Toplevel(parent)
        self.window.title("Paramètres d'impression du chèque")
        self.window.geometry("520x420")
        self.window.grab_set()
        self.window.resizable(False, False)
        self.window.transient(parent)
        self._create_ui()
        parent.wait_window(self.window)

    def _create_ui(self):
        try:
            settings = self.repo.get_settings()
        except Exception:
            settings = {}

        f = tk.Frame(self.window)
        f.pack(fill="both", expand=True, padx=14, pady=14)

        # Page size
        size_frame = tk.LabelFrame(f, text="Taille du chèque (mm)")
        size_frame.pack(fill="x", pady=(0,8))
        tk.Label(size_frame, text="Largeur (mm):").grid(row=0, column=0, sticky="w")
        tk.Label(size_frame, text="Hauteur (mm):").grid(row=0, column=2, sticky="w")
        self.var_w = tk.StringVar(value=str(settings.get('page_width_mm', 175.0)))
        self.var_h = tk.StringVar(value=str(settings.get('page_height_mm', 80.0)))
        tk.Entry(size_frame, textvariable=self.var_w, width=8).grid(row=0, column=1, sticky="w", padx=(4,12))
        tk.Entry(size_frame, textvariable=self.var_h, width=8).grid(row=0, column=3, sticky="w", padx=(4,0))

        # Orientation & Rotation
        or_frame = tk.LabelFrame(f, text="Orientation & Rotation")
        or_frame.pack(fill="x", pady=(0,8))
        tk.Label(or_frame, text="Orientation:").grid(row=0, column=0, sticky="w")
        self.var_orient = tk.StringVar(value=str(settings.get('orientation', 'portrait')))
        cmb_or = ttk.Combobox(or_frame, textvariable=self.var_orient, values=["portrait","landscape"], state="readonly", width=12)
        cmb_or.grid(row=0, column=1, sticky="w", padx=(4,12))
        tk.Label(or_frame, text="Rotation (deg):").grid(row=0, column=2, sticky="w")
        self.var_rot = tk.StringVar(value=str(settings.get('rotate_deg', 0)))
        tk.Entry(or_frame, textvariable=self.var_rot, width=6).grid(row=0, column=3, sticky="w", padx=(4,0))
        # Sideways from montant side
        self.var_sideways_montant = tk.BooleanVar(value=bool(settings.get('sideways_from_montant', False)))
        tk.Checkbutton(or_frame, text="Sideways from montant side", variable=self.var_sideways_montant).grid(row=1, column=0, columnspan=4, sticky="w", pady=(6,0))
        # Center on page
        self.var_center_on_page = tk.BooleanVar(value=bool(settings.get('center_on_page', False)))
        tk.Checkbutton(or_frame, text="Center on page", variable=self.var_center_on_page).grid(row=2, column=0, columnspan=4, sticky="w")
        # Vertical align when centered
        tk.Label(or_frame, text="Vertical align:").grid(row=3, column=0, sticky="w")
        self.var_valign = tk.StringVar(value=str(settings.get('vertical_align', 'extreme-top')))
        ttk.Combobox(or_frame, textvariable=self.var_valign, values=["extreme-top","top","center","bottom"], state="readonly", width=12).grid(row=3, column=1, sticky="w", padx=(4,12))
        tk.Label(or_frame, text="Vertical offset (mm):").grid(row=3, column=2, sticky="w")
        self.var_vo = tk.StringVar(value=str(settings.get('vertical_offset_mm', 0.0)))
        tk.Entry(or_frame, textvariable=self.var_vo, width=8).grid(row=3, column=3, sticky="w", padx=(4,0))

        # Margins & Shift
        ms_frame = tk.LabelFrame(f, text="Marges et Décalage (mm)")
        ms_frame.pack(fill="x", pady=(0,8))
        tk.Label(ms_frame, text="Mode marges:").grid(row=0, column=0, sticky="w")
        self.var_mmode = tk.StringVar(value=str(settings.get('margins_mode', 'zero')))
        cmb_mm = ttk.Combobox(ms_frame, textvariable=self.var_mmode, values=["zero","physical","custom"], state="readonly", width=12)
        cmb_mm.grid(row=0, column=1, sticky="w", padx=(4,12))
        tk.Label(ms_frame, text="Marge gauche:").grid(row=1, column=0, sticky="w")
        tk.Label(ms_frame, text="Marge haut:").grid(row=1, column=2, sticky="w")
        self.var_ml = tk.StringVar(value=str(settings.get('margin_left_mm', 0.0)))
        self.var_mt = tk.StringVar(value=str(settings.get('margin_top_mm', 0.0)))
        self.ent_ml = tk.Entry(ms_frame, textvariable=self.var_ml, width=8)
        self.ent_mt = tk.Entry(ms_frame, textvariable=self.var_mt, width=8)
        self.ent_ml.grid(row=1, column=1, sticky="w", padx=(4,12))
        self.ent_mt.grid(row=1, column=3, sticky="w", padx=(4,0))
        tk.Label(ms_frame, text="Décalage X:").grid(row=2, column=0, sticky="w")
        tk.Label(ms_frame, text="Décalage Y:").grid(row=2, column=2, sticky="w")
        self.var_sx = tk.StringVar(value=str(settings.get('shift_x_mm', 0.0)))
        self.var_sy = tk.StringVar(value=str(settings.get('shift_y_mm', 0.0)))
        tk.Entry(ms_frame, textvariable=self.var_sx, width=8).grid(row=2, column=1, sticky="w", padx=(4,12))
        tk.Entry(ms_frame, textvariable=self.var_sy, width=8).grid(row=2, column=3, sticky="w", padx=(4,0))

        for c in (1,3):
            size_frame.columnconfigure(c, weight=0)
            or_frame.columnconfigure(c, weight=0)
            ms_frame.columnconfigure(c, weight=0)

        # Buttons
        btns = tk.Frame(f)
        btns.pack(fill="x", pady=(8,0))
        tk.Button(btns, text="Annuler", command=self.window.destroy).pack(side="right")
        tk.Button(btns, text="💾 Enregistrer", command=self._save, bg="#27ae60", fg="white").pack(side="right", padx=(6,0))
        tk.Button(btns, text="👁️ Aperçu Test", command=self._preview_test).pack(side="left")
        tk.Button(btns, text="⏮️ Restaurer (DB → JSON)", command=self._restore_settings_from_db).pack(side="left", padx=(8,0))
        tk.Button(btns, text="↩️ Réinitialiser par défaut", command=self._reset_defaults).pack(side="left", padx=(8,0))

    def _collect(self) -> Dict[str, object]:
        try:
            w = float(self.var_w.get().strip())
        except Exception:
            w = 175.0
        try:
            h = float(self.var_h.get().strip())
        except Exception:
            h = 80.0
        try:
            rot = int(self.var_rot.get().strip())
        except Exception:
            rot = 0
        try:
            ml = float(self.var_ml.get().strip())
        except Exception:
            ml = 0.0
        try:
            mt = float(self.var_mt.get().strip())
        except Exception:
            mt = 0.0
        try:
            sx = float(self.var_sx.get().strip())
        except Exception:
            sx = 0.0
        try:
            sy = float(self.var_sy.get().strip())
        except Exception:
            sy = 0.0
        settings = {
            "page_width_mm": w,
            "page_height_mm": h,
            "margins_mode": self.var_mmode.get().strip().lower(),
            "margin_left_mm": ml,
            "margin_top_mm": mt,
            "shift_x_mm": sx,
            "shift_y_mm": sy,
            "orientation": self.var_orient.get().strip().lower(),
            "rotate_deg": rot,
            "sideways_from_montant": bool(self.var_sideways_montant.get()),
            "center_on_page": bool(self.var_center_on_page.get()),
            "vertical_align": self.var_valign.get().strip().lower(),
            "vertical_offset_mm": float(self.var_vo.get().strip() or 0.0),
        }
        return settings

    def _save(self):
        settings = self._collect()
        # If sideways-from-montant is requested, compute rotation so montant edge leads in landscape
        try:
            if settings.get('sideways_from_montant'):
                # Ensure landscape
                settings['orientation'] = 'landscape'
                # Determine montant x vs page center to choose rotation direction
                layout = self.repo.get_layout()
                pos_num = layout.get('montant_number', {"x": 10.0})
                x_mm = float(pos_num.get('x', 10.0))
                page_w = float(settings.get('page_width_mm', 175.0))
                center = page_w / 2.0
                # If montant is on the right side, rotate CCW so the right becomes top; else rotate CW
                settings['rotate_deg'] = 90 if x_mm >= center else -90
        except Exception:
            pass
        try:
            self.repo.save_settings(settings)
            messagebox.showinfo("Paramètres", "Paramètres enregistrés.")
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'enregistrer: {e}")

    def _preview_test(self):
        # Save then preview a sample
        try:
            self.repo.save_settings(self._collect())
        except Exception:
            pass
        sample = {
            'montant_number': '# 1 234.567 #',
            'montant_letters': 'mille deux cent trente-quatre dinars et 567 millimes',
            'beneficiaire': 'SOCIETE TUNISIENNE',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'lieu': 'TUNIS',
        }
        self.print_service.print_cheque(sample, preview_only=True, orientation=None, rotate_deg=None)

    def _reset_defaults(self):
        try:
            defaults = self.repo.get_default_settings()
            # Update UI controls
            self.var_w.set(str(defaults.get('page_width_mm', 175.0)))
            self.var_h.set(str(defaults.get('page_height_mm', 80.0)))
            self.var_mmode.set(str(defaults.get('margins_mode', 'zero')))
            self.var_ml.set(str(defaults.get('margin_left_mm', 0.0)))
            self.var_mt.set(str(defaults.get('margin_top_mm', 0.0)))
            self.var_sx.set(str(defaults.get('shift_x_mm', 0.0)))
            self.var_sy.set(str(defaults.get('shift_y_mm', 0.0)))
            self.var_orient.set(str(defaults.get('orientation', 'portrait')))
            self.var_rot.set(str(defaults.get('rotate_deg', 0)))
            self.var_sideways_montant.set(bool(defaults.get('sideways_from_montant', False)))
            self.var_center_on_page.set(bool(defaults.get('center_on_page', True)))
            self.var_valign.set(str(defaults.get('vertical_align', 'extreme-top')))
            self.var_vo.set(str(defaults.get('vertical_offset_mm', 0.0)))
            # Persist immediately
            self.repo.save_settings(defaults)
            messagebox.showinfo("Paramètres", "Paramètres réinitialisés aux valeurs par défaut.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de réinitialiser: {e}")

    def _restore_settings_from_db(self):
        try:
            self.repo.restore_user_json_from_db(backup_existing=True)
            settings = self.repo.get_settings()
            # Update form with restored settings
            self.var_w.set(str(settings.get('page_width_mm', 175.0)))
            self.var_h.set(str(settings.get('page_height_mm', 80.0)))
            self.var_mmode.set(str(settings.get('margins_mode', 'zero')))
            self.var_ml.set(str(settings.get('margin_left_mm', 0.0)))
            self.var_mt.set(str(settings.get('margin_top_mm', 0.0)))
            self.var_sx.set(str(settings.get('shift_x_mm', 0.0)))
            self.var_sy.set(str(settings.get('shift_y_mm', 0.0)))
            self.var_orient.set(str(settings.get('orientation', 'portrait')))
            self.var_rot.set(str(settings.get('rotate_deg', 0)))
            self.var_sideways_montant.set(bool(settings.get('sideways_from_montant', False)))
            self.var_center_on_page.set(bool(settings.get('center_on_page', True)))
            self.var_valign.set(str(settings.get('vertical_align', 'extreme-top')))
            self.var_vo.set(str(settings.get('vertical_offset_mm', 0.0)))
            messagebox.showinfo("Paramètres", "Paramètres restaurés depuis la base de données.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de restaurer: {e}")
