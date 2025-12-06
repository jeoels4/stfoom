"""
Monthly Avoir Management Page
Displays and manages monthly 200T avoir system
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List
import threading

class MonthlyAvoirPage(ttk.Frame):
    """Page for managing monthly avoir (200T/month system)"""
    
    def __init__(self, parent, go_back_callback):
        super().__init__(parent)
        self.go_back = go_back_callback
        self.current_data = []
        
        self.create_widgets()
        self.refresh_data()
    
    def create_widgets(self):
        """Create the UI widgets"""
        
        # Header frame
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        # Title
        title_label = ttk.Label(header_frame, 
                              text="📊 Gestion des Avoirs Mensuels (200T/mois)", 
                              font=("Segoe UI", 18, "bold"))
        title_label.pack(side="left")
        
        # Back button
        back_btn = ttk.Button(header_frame, text="← Retour", 
                            command=self.go_back)
        back_btn.pack(side="right")
        
        # Info frame
        info_frame = ttk.LabelFrame(self, text="Information", padding=10)
        info_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        info_text = ("Système d'avoir mensuel: Lorsque vos factures mensuelles dépassent 200 tonnes,\n"
                    "vous êtes éligible pour un avoir calculé sur le total mensuel.")
        info_label = ttk.Label(info_frame, text=info_text, 
                             font=("Segoe UI", 10), foreground="#0066cc")
        info_label.pack()
        
        # Controls frame
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Refresh button
        refresh_btn = ttk.Button(controls_frame, text="🔄 Actualiser", 
                               command=self.refresh_data)
        refresh_btn.pack(side="left", padx=(0, 10))
        
        # Check current month button
        check_btn = ttk.Button(controls_frame, text="📅 Vérifier Mois Actuel", 
                             command=self.check_current_month)
        check_btn.pack(side="left", padx=(0, 10))
        
        # Force notification check
        notif_btn = ttk.Button(controls_frame, text="🔔 Vérifier Notifications", 
                             command=self.check_notifications)
        notif_btn.pack(side="left")
        
        # Main content frame
        content_frame = ttk.Frame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Create treeview for monthly data
        columns = ("month", "quantity", "threshold", "rate", "avoir", "status")
        self.tree = ttk.Treeview(content_frame, columns=columns, show="headings", height=12)
        
        # Define column headings and widths
        self.tree.heading("month", text="Mois")
        self.tree.heading("quantity", text="Quantité (T)")
        self.tree.heading("threshold", text="Seuil 200T")
        self.tree.heading("rate", text="Taux")
        self.tree.heading("avoir", text="Avoir (DT)")
        self.tree.heading("status", text="Statut")
        
        self.tree.column("month", width=100, anchor="center")
        self.tree.column("quantity", width=120, anchor="center")
        self.tree.column("threshold", width=100, anchor="center")
        self.tree.column("rate", width=80, anchor="center")
        self.tree.column("avoir", width=120, anchor="center")
        self.tree.column("status", width=150, anchor="center")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(content_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Details frame (shown when selecting a month)
        self.details_frame = ttk.LabelFrame(self, text="Détails du Mois Sélectionné", padding=10)
        self.details_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        self.details_text = tk.Text(self.details_frame, height=6, width=80, 
                                  font=("Consolas", 10), 
                                  bg="#f8f8f8", relief="sunken", bd=1)
        details_scrollbar = ttk.Scrollbar(self.details_frame, orient="vertical", 
                                        command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        
        self.details_text.pack(side="left", fill="both", expand=True)
        details_scrollbar.pack(side="right", fill="y")
        
        # Bind treeview selection
        self.tree.bind("<<TreeviewSelect>>", self.on_select_month)
        
        # Initially hide details
        self.details_frame.pack_forget()
    
    def refresh_data(self):
        """Refresh the monthly avoir data"""
        try:
            from stfoom.logic.monthly_avoir_manager import monthly_avoir_manager
            
            # Clear existing data
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Get all months summary
            months_data = monthly_avoir_manager.get_all_months_summary()
            self.current_data = months_data
            
            # Populate treeview
            for month_data in months_data:
                month = month_data['month']
                quantity = f"{month_data['total_quantity']:.3f}"
                threshold = "✓ Atteint" if month_data['threshold_met'] else "❌ Non atteint"
                
                # Get current rate
                from stfoom.logic.avoir_manager import avoir_manager
                config = avoir_manager.get_avoir_config()
                rate = config.get('total_factures_200t_month', {}).get('rate', 0.0)
                
                avoir = f"{month_data['total_avoir']:.3f}" if month_data['threshold_met'] else "0.00"
                
                # Status
                if not month_data['threshold_met']:
                    status = "< 200T"
                elif month_data['is_processed']:
                    status = "✓ Traité"
                elif month_data['notification_sent']:
                    status = "🔔 Notifié"
                else:
                    status = "⚠️ En attente"
                
                # Insert with color coding
                item_id = self.tree.insert("", "end", values=(
                    month, quantity, threshold, f"{rate:.3f}", avoir, status
                ))
                
                # Color coding
                if month_data['threshold_met']:
                    if month_data['is_processed']:
                        self.tree.set(item_id, "status", "✓ Traité")
                    elif not month_data['notification_sent']:
                        self.tree.set(item_id, "status", "⚠️ NOUVEAU!")
            
            print(f"[MONTHLY_AVOIR_PAGE] Loaded {len(months_data)} months")
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR_PAGE] Error refreshing data: {e}")
            messagebox.showerror("Erreur", f"Erreur lors du rafraîchissement: {e}")
    
    def check_current_month(self):
        """Check and update current month data"""
        try:
            from stfoom.logic.monthly_avoir_manager import monthly_avoir_manager
            
            # Get current month summary
            current_month = monthly_avoir_manager.get_current_month_key()
            summary = monthly_avoir_manager.get_monthly_summary(current_month)
            
            if summary.get('error'):
                messagebox.showerror("Erreur", f"Erreur: {summary['error']}")
                return
            
            # Show current month info
            message = f"Mois actuel: {current_month}\n"
            message += f"Quantité totale: {summary['total_quantity']:.3f}T\n"
            message += f"Seuil 200T: {'✓ Atteint' if summary['threshold_met'] else '❌ Non atteint'}\n"
            
            if summary['threshold_met']:
                message += f"Avoir éligible: {summary['total_avoir']:.3f}DT\n"
                message += f"Nombre de factures: {len(summary['factures'])}"
            
            messagebox.showinfo("Mois Actuel", message)
            
            # Refresh display
            self.refresh_data()
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR_PAGE] Error checking current month: {e}")
            messagebox.showerror("Erreur", f"Erreur: {e}")
    
    def check_notifications(self):
        """Manually check for pending notifications"""
        try:
            from stfoom.ui.monthly_avoir_notification import get_notification_system
            
            notification_system = get_notification_system()
            if notification_system:
                notification_system.manual_check()
                messagebox.showinfo("✓ Vérification", "Vérification des notifications effectuée!")
            else:
                messagebox.showwarning("Attention", "Système de notifications non initialisé")
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR_PAGE] Error checking notifications: {e}")
            messagebox.showerror("Erreur", f"Erreur: {e}")
    
    def on_select_month(self, event):
        """Handle month selection in treeview"""
        try:
            selection = self.tree.selection()
            if not selection:
                self.details_frame.pack_forget()
                return
            
            item = selection[0]
            values = self.tree.item(item, "values")
            selected_month = values[0]
            
            # Get detailed information for selected month
            from stfoom.logic.monthly_avoir_manager import monthly_avoir_manager
            summary = monthly_avoir_manager.get_monthly_summary(selected_month)
            
            if summary.get('error'):
                return
            
            # Show details frame
            self.details_frame.pack(fill="x", padx=20, pady=(10, 20))
            
            # Clear and populate details
            self.details_text.config(state="normal")
            self.details_text.delete(1.0, "end")
            
            details = f"📅 DÉTAILS MOIS {selected_month}\n"
            details += "=" * 50 + "\n\n"
            details += f"Quantité totale: {summary['total_quantity']:.3f} tonnes\n"
            details += f"Seuil 200T: {'✓ ATTEINT' if summary['threshold_met'] else '❌ NON ATTEINT'}\n"
            details += f"Taux avoir: {summary['avoir_rate']:.3f} DT/tonne\n"
            details += f"Avoir total: {summary['total_avoir']:.3f} DT\n"
            details += f"Notification envoyée: {'✓ Oui' if summary['notification_sent'] else '❌ Non'}\n\n"
            
            if summary['factures']:
                details += f"FACTURES CONTRIBUTIVES ({len(summary['factures'])}):\n"
                details += "-" * 30 + "\n"
                for facture in summary['factures']:
                    details += f"• Facture {facture['numero']} ({facture['date']}): {facture['quantity']:.3f}T\n"
            else:
                details += "Aucune facture pour ce mois.\n"
            
            self.details_text.insert(1.0, details)
            self.details_text.config(state="disabled")
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR_PAGE] Error showing details: {e}")
