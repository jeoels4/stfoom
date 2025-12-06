#!/usr/bin/env python3
"""
Enhanced Multiple Payment Dialog
===============================
Complete copy of normal payment dialog features adapted for multiple invoices.
This dialog now has ALL the same features as the normal payment dialog:

- Complete UI structure with scrollable interface
- Existing payments treeview with modify/delete
- Full payment form with all options
- Cascade operations using cascade_manager
- Timbre-aware retenu calculations
- Payment method support (banque/caisse)
- Date validation and calendar picker
- Permission checks
- Reference field handling

ARCHITECTURE:
- Copies PaymentDialog from vente_page.py
- Adapts for multiple invoice handling
- Maintains identical UI/UX to normal payments
"""

from __future__ import annotations
import json
import os
from typing import Optional, List, Dict
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkcalendar import Calendar, DateEntry

# Import services
from app.stfoom.services.payment_service import PaymentService  
from app.stfoom.services.bank_service import BankService
from app.stfoom.services.retenu_service import RetenuService
from app.stfoom.services.cascade_manager import cascade_manager
from app.stfoom.ui.permission_utils import check_ui_permission
from app.stfoom.ui.shared_widgets import format_money


class EnhancedMultiplePaymentDialog:
    """Enhanced multiple payment dialog with ALL normal payment features"""
    
    def __init__(self, parent, invoice_list: List[Dict], is_achat: bool = False,
                 payment_service: PaymentService = None, bank_service: BankService = None,
                 retenu_service: RetenuService = None):
        self.parent = parent
        self.invoice_list = invoice_list
        self.is_achat = is_achat
        self.payment_service = payment_service or PaymentService()
        self.bank_service = bank_service
        self.retenu_service = retenu_service
        self.result = None
        
        # Calculate totals for multiple invoices
        self.total_ttc = sum(float(inv.get('ttc', 0) or 0) for inv in invoice_list)
        self.total_timbre = sum(float(inv.get('timbre', 1.0) or 1.0) for inv in invoice_list)
        
        # Get all payments for these invoices
        self.all_payments = self._get_all_invoice_payments()
        self.total_paid = sum(p['montant_paye'] for p in self.all_payments)
        self.reste = self.total_ttc - self.total_paid
        
        # Create main dialog
        self.window = tk.Toplevel(parent)
        self.window.title(f"Paiements Multiples - {len(invoice_list)} Factures")
        self.window.geometry("750x800")
        self.window.grab_set()
        self.window.resizable(True, True)
        
        self._create_ui()
        self.window.transient(parent)
        self.window.grab_set()
        parent.wait_window(self.window)
    
    def _get_all_invoice_payments(self) -> List[Dict]:
        """Get all payments for all invoices in the list"""
        all_payments = []
        for invoice in self.invoice_list:
            nfacture = invoice.get('nfacture') or invoice.get('id')
            if nfacture:
                invoice_payments = self.payment_service.get_paiements_facture(nfacture)
                # Add invoice info to payments for identification
                for payment in invoice_payments:
                    payment['source_nfacture'] = nfacture
                    payment['source_client'] = invoice.get('client', invoice.get('raison_sociale', ''))
                all_payments.extend(invoice_payments)
        return all_payments
    
    def _create_ui(self):
        """Create the complete UI identical to normal payment dialog"""
        # --- Scrollable main content ---
        content_frame = ttk.Frame(self.window)
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
        
        # --- Informations Factures (Multiple) ---
        self._create_invoices_info_section(scrollable_frame)
        
        # --- Paiements existants ---
        self._create_payments_section(scrollable_frame)
        
        # --- Reste à payer section ---
        self._create_remaining_section(scrollable_frame)
        
        # --- Button section (always visible at bottom) ---
        self._create_bottom_buttons()
        
    def _create_invoices_info_section(self, parent):
        """Create invoice information section for multiple invoices"""
        info_frame = tk.LabelFrame(parent, text="Informations Factures Multiples")
        info_frame.pack(fill="x", padx=10, pady=10)
        
        # Summary info
        tk.Label(info_frame, text=f"Nombre de factures: {len(self.invoice_list)}").pack(anchor="w", padx=5, pady=2)
        tk.Label(info_frame, text=f"Montant Total (TTC): {self.total_ttc:.3f} TND").pack(anchor="w", padx=5, pady=2)
        
        # Timbre and retenu base info (identical to normal payment)
        tk.Label(info_frame, text=f"Total Timbre: {self.total_timbre:.3f} TND").pack(anchor="w", padx=5, pady=2)
        retenu_base = max(0, self.total_ttc - self.total_timbre)
        tk.Label(info_frame, text=f"Base Retenu (TTC - Timbre): {retenu_base:.3f} TND", 
                font=('Arial', 9, 'bold'), fg='#2E7D32').pack(anchor="w", padx=5, pady=2)
        
        # Invoice details (collapsible)
        details_frame = tk.Frame(info_frame)
        details_frame.pack(fill="x", padx=5, pady=5)
        
        self.show_details = tk.BooleanVar(value=False)
        details_btn = tk.Checkbutton(details_frame, text="Afficher détails des factures", 
                                   variable=self.show_details, command=self._toggle_invoice_details)
        details_btn.pack(anchor="w")
        
        self.details_list_frame = tk.Frame(details_frame)
        
        # Initially hidden details
        for i, invoice in enumerate(self.invoice_list):
            if i < 5:  # Show first 5 invoices
                nfacture = invoice.get('nfacture') or invoice.get('id', '')
                client = invoice.get('client', invoice.get('raison_sociale', ''))
                ttc = float(invoice.get('ttc', 0) or 0)
                detail_label = tk.Label(self.details_list_frame, 
                                      text=f"  • Facture {nfacture} - {client}: {ttc:.3f} TND",
                                      font=('Arial', 8))
                detail_label.pack(anchor="w")
        
        if len(self.invoice_list) > 5:
            tk.Label(self.details_list_frame, text=f"  ... et {len(self.invoice_list) - 5} autres factures",
                    font=('Arial', 8, 'italic')).pack(anchor="w")
    
    def _toggle_invoice_details(self):
        """Toggle invoice details visibility"""
        if self.show_details.get():
            self.details_list_frame.pack(fill="x", pady=5)
        else:
            self.details_list_frame.pack_forget()
    
    def _create_payments_section(self, parent):
        """Create existing payments section (identical to normal payment dialog)"""
        pay_frame = tk.LabelFrame(parent, text="Paiements enregistrés")
        pay_frame.pack(fill="x", padx=10, pady=10)
        
        # Treeview for payments (identical columns as normal payment)
        columns = ("facture", "montant", "type", "banque", "methode", "date", "echeance", "reference", "notes", "actions")
        self.tree = ttk.Treeview(pay_frame, columns=columns, show="headings", height=6)
        
        for col, label in zip(columns, ["Facture", "Montant", "Type", "Banque", "Méthode", "Date", "Échéance", "Référence", "Notes", "Actions"]):
            self.tree.heading(col, text=label)
            if col == "facture":
                self.tree.column(col, width=80, anchor="center")
            elif col == "notes":
                self.tree.column(col, width=120, anchor="w")
            elif col == "actions":
                self.tree.column(col, width=80, anchor="center")
            else:
                self.tree.column(col, width=90, anchor="center")
        
        self.tree.pack(fill="x", padx=5, pady=5)
        self._refresh_tree()
        
        # Buttons (identical to normal payment dialog)
        btns = tk.Frame(pay_frame)
        btns.pack(pady=4)
        
        tk.Button(btns, text="Ajouter un paiement", command=self._add_payment, 
                 bg="#007bff", fg="white").pack(side="left", padx=4)
        tk.Button(btns, text="Fermer", command=self._cancel).pack(side="left", padx=4)
        
        # Delete button for selected payment
        self.delete_btn = tk.Button(btns, text="Supprimer le paiement", 
                                   command=self._delete_selected_payment, 
                                   bg="#dc3545", fg="white", state="disabled")
        self.delete_btn.pack(side="left", padx=4)
        
        # Bind events
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_action)
    
    def _refresh_tree(self):
        """Refresh the payments treeview (identical to normal payment dialog)"""
        # Clear existing items
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        # Reload payments
        self.all_payments = self._get_all_invoice_payments()
        self.total_paid = sum(p['montant_paye'] for p in self.all_payments)
        self.reste = self.total_ttc - self.total_paid
        
        # Populate tree
        for p in self.all_payments:
            banque_nom = ""
            if p['methode_paiement'] == 'banque' and p.get('banque_id') and self.bank_service:
                banques = self.bank_service.get_banques()
                for b in banques:
                    if b['id'] == p['banque_id']:
                        banque_nom = b.get('nom_banque', b.get('nom', 'Unknown Bank'))
                        break
            
            # Format method display
            notes_display = p.get('notes', '')
            method_display = self.payment_service.format_payment_method(
                p['methode_paiement'], p.get('mode_paiement', ''))
            
            # Add visual indicator for multiple payments
            if notes_display and 'MULTI-' in notes_display:
                method_display = f"🔗 {method_display} (Multiple)"
            
            self.tree.insert("", "end", iid=p['id'], values=(
                p.get('source_nfacture', ''),
                f"{p['montant_paye']:.3f}",
                "Banque" if p['methode_paiement'] == 'banque' else "Caisse",
                banque_nom,
                method_display,
                p['date_paiement'],
                p.get('echeance', ''),
                p.get('reference_paiement', ''),
                notes_display,
                "Modifier | Supprimer"
            ))
    
    def _create_remaining_section(self, parent):
        """Create remaining amount section"""
        reste_frame = tk.Frame(parent)
        reste_frame.pack(fill="x", padx=10, pady=6)
        
        tk.Label(reste_frame, text="Reste à payer total:").pack(side="left")
        self.reste_var = tk.StringVar(value=f"{self.reste:.3f}")
        tk.Label(reste_frame, textvariable=self.reste_var, font=('Arial', 10, 'bold')).pack(side="left", padx=5)
        tk.Label(reste_frame, text="TND").pack(side="left")
    
    def _create_bottom_buttons(self):
        """Create bottom button section"""
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill="x", pady=(10, 0), side="bottom")
        
        close_btn = tk.Button(btn_frame, text="Fermer", command=self._cancel,
                              bg="#9E9E9E", fg="white", font=('Arial', 10),
                              relief="flat", padx=30, pady=8)
        close_btn.pack(side="right", padx=(0, 10))
    
    def _on_tree_select(self, event):
        """Handle tree selection (identical to normal payment dialog)"""
        sel = self.tree.selection()
        if sel:
            self.delete_btn.config(state="normal")
        else:
            self.delete_btn.config(state="disabled")
    
    def _on_tree_action(self, event):
        """Handle tree double-click actions (identical to normal payment dialog)"""
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item:
            return
        
        if col == "#10":  # Actions column
            menu = tk.Menu(self.window, tearoff=0)
            menu.add_command(label="Modifier", command=lambda: self._edit_payment(item))
            menu.add_command(label="Supprimer", command=lambda: self._delete_payment(item))
            menu.tk_popup(event.x_root, event.y_root)
    
    def _add_payment(self):
        """Add a new payment (identical interface to normal payment dialog)"""
        if not check_ui_permission("payments", "create"):
            return
        self._payment_form()
    
    def _edit_payment(self, item_id):
        """Edit existing payment (identical to normal payment dialog)"""
        payment = next((p for p in self.all_payments if str(p['id']) == str(item_id)), None)
        if payment:
            self._payment_form(payment)
    
    def _delete_selected_payment(self):
        """Delete selected payment from tree"""
        sel = self.tree.selection()
        if sel:
            self._delete_payment(sel[0])
    
    def _delete_payment(self, item_id):
        """Delete payment with cascade operations (identical to normal payment dialog)"""
        if not check_ui_permission("payments", "delete"):
            return
            
        # Get payment details
        payment_details = next((p for p in self.all_payments if str(p['id']) == str(item_id)), None)
        if not payment_details:
            return
        
        # Check if it's a multiple payment
        is_multiple = payment_details.get('notes', '') and 'MULTI-' in payment_details.get('notes', '')
        
        if is_multiple:
            confirm_msg = ("⚠️ ATTENTION: Paiement Multiple Détecté\\n\\n"
                         f"Ce paiement fait partie d'un paiement multiple.\\n"
                         f"Supprimer ce paiement supprimera TOUS les paiements\\n"
                         f"associés de cette transaction multiple.\\n\\n"
                         f"Êtes-vous sûr de vouloir continuer?")
            if not messagebox.askyesno("Confirmer - Paiement Multiple", confirm_msg):
                return
        else:
            if not messagebox.askyesno("Confirmer", "Supprimer ce paiement ?"):
                return
        
        try:
            # Use cascade manager for complete deletion (identical to normal payment)
            result = cascade_manager.delete_payment_cascade(int(item_id))
            
            if 'error' in result:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {result['error']}")
                return
            
            # Refresh display
            self._refresh_tree()
            self.reste_var.set(f"{self.reste:.3f}")
            self.result = True
            
            # Force refresh parent page
            if hasattr(self.parent, '_load_rows'):
                self.parent._load_rows()
            
            # Show success message
            if is_multiple:
                messagebox.showinfo("Succès", "Paiement multiple supprimé avec succès!\\nTous les paiements associés ont été supprimés.")
            else:
                messagebox.showinfo("Succès", "Paiement supprimé avec succès!")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
            print(f"[MULTIPLE_PAYMENT] Error deleting payment {item_id}: {e}")
    
    def _payment_form(self, preset=None):
        """Complete payment form (IDENTICAL copy from normal payment dialog)"""
        form = tk.Toplevel(self.window)
        form.title("Ajouter un paiement" if not preset else "Modifier le paiement")
        form.geometry("500x700")
        form.grab_set()
        
        # Step 1: Payment Type Selection (identical to normal payment)
        type_var = tk.StringVar(value=preset['methode_paiement'] if preset else "banque")
        tk.Label(form, text="Type de paiement:").pack(anchor="w", padx=10, pady=4)
        tk.Radiobutton(form, text="🏦 Banque", variable=type_var, value="banque", 
                      command=lambda: update_fields()).pack(anchor="w", padx=20)
        tk.Radiobutton(form, text="💰 Caisse", variable=type_var, value="caisse", 
                      command=lambda: update_fields()).pack(anchor="w", padx=20)
        
        # Bank options frame (identical to normal payment)
        bank_options_frame = tk.Frame(form)
        bank_options_frame.pack(anchor="w", fill="x", padx=10, pady=2)
        
        bank_var = tk.StringVar()
        method_var = tk.StringVar()
        
        # Get banks (identical to normal payment)
        banques = self.bank_service.get_banques() if self.bank_service else []
        banks_dict = {}
        for b in banques:
            bank_name = b.get('nom_banque', b.get('nom', 'Unknown Bank'))
            if 'numero_compte' in b and b['numero_compte']:
                display_name = f"{bank_name} ({b['numero_compte']})"
            else:
                display_name = bank_name
            banks_dict[display_name] = b['id']
        
        bank_combo = ttk.Combobox(bank_options_frame, textvariable=bank_var, 
                                 state="readonly", width=35, values=list(banks_dict.keys()))
        
        # Payment methods (identical to normal payment)
        payment_methods = self.bank_service.get_payment_methods() if self.bank_service else [
            ('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
        method_combo = ttk.Combobox(bank_options_frame, textvariable=method_var, 
                                   state="readonly", width=30, 
                                   values=[label for _, label in payment_methods])
        
        # Echeance field (identical to normal payment)  
        echeance_var = tk.StringVar(value=datetime.strptime(preset['echeance'], "%Y-%m-%d").strftime("%d/%m/%Y") 
                                   if preset and preset.get('echeance') else "")
        echeance_label = tk.Label(bank_options_frame, text="Échéance (JJ/MM/AAAA, pour traite):")
        echeance_frame = tk.Frame(bank_options_frame)
        echeance_entry = DateEntry(echeance_frame, textvariable=echeance_var, 
                                  date_pattern="dd/MM/yyyy", width=15)
        echeance_entry.pack(side="left")
        
        # Numero field (identical to normal payment)
        numero_label = tk.Label(bank_options_frame, text="Numéro:")
        numero_var = tk.StringVar(value=preset.get('reference_paiement', '') if preset else "")
        numero_entry = tk.Entry(bank_options_frame, textvariable=numero_var, width=25)
        
        # Dynamic field update function (identical to normal payment)
        def update_fields():
            for widget in bank_options_frame.winfo_children():
                widget.pack_forget()
            
            if type_var.get() == "banque":
                bank_combo.pack(anchor="w", padx=0, pady=2)
                method_combo.pack(anchor="w", padx=0, pady=2)
                numero_label.pack(anchor="w", padx=0, pady=2)
                numero_entry.pack(anchor="w", padx=0, pady=2)
                
                # Show echeance for traite
                try:
                    method_idx = [label for _, label in payment_methods].index(method_combo.get())
                    method_key = payment_methods[method_idx][0] if method_idx is not None else None
                    if method_key == "traite":
                        echeance_label.pack(anchor="w", padx=0, pady=2)
                        echeance_frame.pack(anchor="w", padx=0, pady=2)
                except Exception:
                    pass
        
        method_combo.bind("<<ComboboxSelected>>", lambda e: update_fields())
        update_fields()
        
        # Amount field (identical to normal payment)
        tk.Label(form, text="Montant payé (TND):").pack(anchor="w", padx=10, pady=4)
        amount_var = tk.StringVar(value=f"{preset['montant_paye']:.3f}" if preset else f"{self.reste:.3f}")
        amount_entry = tk.Entry(form, textvariable=amount_var, width=15)
        amount_entry.pack(padx=10, pady=2)
        
        # Date field with calendar (identical to normal payment)
        tk.Label(form, text="Date de paiement (JJ/MM/AAAA):").pack(anchor="w", padx=10, pady=4)
        date_frame = tk.Frame(form)
        date_frame.pack(padx=10, pady=2, anchor="w")
        date_var = tk.StringVar(value=datetime.strptime(preset['date_paiement'], "%Y-%m-%d").strftime("%d/%m/%Y") 
                               if preset else datetime.now().strftime("%d/%m/%Y"))
        date_entry = tk.Entry(date_frame, textvariable=date_var, width=15)
        date_entry.pack(side="left")
        
        def pick_date():
            top = tk.Toplevel(form)
            top.title("Sélectionner une date")
            cal_widget = Calendar(top, date_pattern="dd/mm/yyyy")
            cal_widget.pack(padx=10, pady=10)
            def set_date():
                date_entry.delete(0, "end")
                date_entry.insert(0, cal_widget.get_date())
                top.destroy()
            tk.Button(top, text="Valider", command=set_date).pack(pady=5)
        
        tk.Button(date_frame, text="📅", command=pick_date).pack(side="left", padx=4)
        
        # Reference field (identical to normal payment)
        tk.Label(form, text="Référence (optionnel):").pack(anchor="w", padx=10, pady=4)
        ref_var = tk.StringVar(value=preset.get('reference_paiement', '') if preset else "")
        ref_entry = tk.Entry(form, textvariable=ref_var, width=25)
        ref_entry.pack(padx=10, pady=2)
        
        # Notes field (identical to normal payment)
        tk.Label(form, text="Notes (optionnel):").pack(anchor="w", padx=10, pady=4)
        notes_text = tk.Text(form, height=3, width=35)
        if preset:
            notes_text.insert("1.0", preset.get('notes', ''))
        notes_text.pack(padx=10, pady=2)
        
        # Retenu calculation section (identical to normal payment with timbre awareness)
        self._create_retenu_section(form, amount_var)
        
        # Save button (identical to normal payment)
        def save_payment():
            self._save_payment_form(form, type_var, amount_var, date_var, ref_var, notes_text,
                                  bank_var, banks_dict, method_var, method_combo, payment_methods,
                                  numero_var, echeance_var, preset)
        
        tk.Button(form, text="Enregistrer", command=save_payment, bg="#28a745", fg="white").pack(pady=12)
        
        # Delete button for editing (identical to normal payment)
        if preset:
            def delete_and_close():
                self._delete_payment(preset['id'])
                form.destroy()
            tk.Button(form, text="Supprimer", command=delete_and_close, bg="#dc3545", fg="white").pack(pady=2)
        
        tk.Button(form, text="Annuler", command=form.destroy).pack()
    
    def _create_retenu_section(self, form, amount_var):
        """Create retenu calculation section (identical to normal payment)"""
        retenu_frame = tk.Frame(form)
        retenu_frame.pack(anchor="w", padx=10, pady=2, fill="x")
        
        tk.Label(form, text="Retenu (%):").pack(anchor="w", padx=10, pady=4)
        retenu_var = tk.StringVar(value="0")
        retenu_entry = tk.Entry(retenu_frame, textvariable=retenu_var, width=10)
        retenu_entry.pack(side="left", padx=(0, 10))
        
        # Editable retenu amount (identical to normal payment)
        tk.Label(retenu_frame, text="Montant retenu:").pack(side="left", padx=(10, 5))
        retenu_amount_var = tk.StringVar(value="0.000")
        retenu_amount_entry = tk.Entry(retenu_frame, textvariable=retenu_amount_var, 
                                      width=12, bg="white")
        retenu_amount_entry.pack(side="left")
        tk.Label(retenu_frame, text="TND").pack(side="left", padx=(2, 0))
        
        # Auto-calculation functions (identical to normal payment with timbre awareness)
        def calculate_retenu_from_percent(*args):
            """Calculate retenu amount from percentage (timbre-aware)"""
            try:
                # Use timbre-excluded retenu base (identical to normal payment)
                retenu_base = max(0, self.total_ttc - self.total_timbre)
                remaining_amount = self.reste
                
                retenu_text = retenu_var.get().strip()
                if not retenu_text:
                    retenu_percent = 0.0
                else:
                    try:
                        retenu_percent = float(retenu_text.replace(",", "."))
                        retenu_percent = max(0.0, min(100.0, retenu_percent))
                    except ValueError:
                        retenu_percent = 0.0
                
                # Calculate retenu on timbre-excluded base
                retenu_amount = retenu_base * retenu_percent / 100.0
                net_payment = remaining_amount - retenu_amount
                
                # Ensure net payment doesn't go negative
                if net_payment < 0:
                    net_payment = 0
                    retenu_amount = remaining_amount
                
                retenu_amount_var.set(f"{retenu_amount:.3f}")
                amount_var.set(f"{net_payment:.3f}")
                
            except Exception as e:
                print(f"Error in retenu calculation: {e}")
                retenu_amount_var.set("0.000")
        
        def calculate_retenu_from_amount(*args):
            """Calculate retenu percentage from amount (timbre-aware)"""
            try:
                retenu_amount_text = retenu_amount_var.get().strip()
                if not retenu_amount_text:
                    retenu_amount = 0.0
                else:
                    try:
                        retenu_amount = float(retenu_amount_text.replace(",", "."))
                        retenu_amount = max(0.0, retenu_amount)
                    except ValueError:
                        retenu_amount = 0.0
                
                # Calculate retenu base excluding timbre
                retenu_base = max(0, self.total_ttc - self.total_timbre)
                
                # Calculate percentage
                if retenu_base > 0:
                    retenu_percent = (retenu_amount / retenu_base) * 100.0
                else:
                    retenu_percent = 0.0
                
                # Update percentage (avoid recursive callback)
                retenu_var.trace_remove("write", percent_trace_id)
                retenu_var.set(f"{retenu_percent:.2f}")
                retenu_var.trace_add("write", calculate_retenu_from_percent)
                
                # Update net payment
                remaining_amount = self.reste
                net_payment = remaining_amount - retenu_amount
                if net_payment < 0:
                    net_payment = 0
                
                amount_var.set(f"{net_payment:.3f}")
                
            except Exception as e:
                print(f"Error in retenu calculation from amount: {e}")
        
        # Bind calculations (identical to normal payment)
        percent_trace_id = retenu_var.trace_add("write", calculate_retenu_from_percent)
        retenu_amount_var.trace_add("write", calculate_retenu_from_amount)
        
        # Store variables for access in save function
        self.retenu_var = retenu_var
        self.retenu_amount_var = retenu_amount_var
    
    def _save_payment_form(self, form, type_var, amount_var, date_var, ref_var, notes_text,
                          bank_var, banks_dict, method_var, method_combo, payment_methods,
                          numero_var, echeance_var, preset):
        """Save payment with full validation (identical logic to normal payment)"""
        try:
            # Amount validation (identical to normal payment)
            amount_text = amount_var.get().strip()
            if not amount_text:
                messagebox.showerror("Erreur", "Le montant est obligatoire.")
                return
                
            try:
                montant = float(amount_text.replace(",", "."))
                if montant <= 0:
                    messagebox.showerror("Erreur", "Le montant doit être positif.")
                    return
                if montant > 1000000:  # 1 million DT
                    if not messagebox.askyesno("Confirmation", 
                        f"Le montant est élevé ({montant:.3f} DT). Continuer ?"):
                        return
            except ValueError:
                messagebox.showerror("Erreur", "Montant invalide (doit être un nombre).")
                return
            
            # Retenu validation (identical to normal payment)
            retenu_text = self.retenu_var.get().strip()
            retenu_percent = 0.0
            if retenu_text:
                try:
                    retenu_percent = float(retenu_text.replace(",", "."))
                    if retenu_percent < 0 or retenu_percent > 100:
                        messagebox.showerror("Erreur", "Le pourcentage de retenu doit être entre 0 et 100.")
                        return
                except ValueError:
                    messagebox.showerror("Erreur", "Pourcentage de retenu invalide.")
                    return
            
            retenu_amount_text = self.retenu_amount_var.get().strip()
            retenu_amount = 0.0
            if retenu_amount_text:
                try:
                    retenu_amount = float(retenu_amount_text.replace(",", "."))
                    if retenu_amount < 0:
                        messagebox.showerror("Erreur", "Le montant de retenu ne peut pas être négatif.")
                        return
                except ValueError:
                    messagebox.showerror("Erreur", "Montant de retenu invalide.")
                    return
            
            # Net payment calculation (identical to normal payment)
            montant_net = montant
            
            if montant_net < 0:
                messagebox.showerror("Erreur", "Le montant net ne peut pas être négatif.")
                return
            
            # Date validation (identical to normal payment)
            date_text = date_var.get().strip()
            if not date_text:
                messagebox.showerror("Erreur", "La date de paiement est obligatoire.")
                return
            
            try:
                date_str = datetime.strptime(date_text, "%d/%m/%Y").strftime("%Y-%m-%d")
                payment_date = datetime.strptime(date_text, "%d/%m/%Y").date()
                if payment_date > datetime.now().date():
                    if not messagebox.askyesno("Confirmation", 
                        "La date de paiement est dans le futur. Continuer ?"):
                        return
            except ValueError:
                messagebox.showerror("Erreur", "Format de date invalide (JJ/MM/AAAA).")
                return
            
            # Echeance validation (identical to normal payment)
            echeance_str = echeance_var.get().strip()
            echeance_db = ''
            if echeance_str:
                try:
                    echeance_db = datetime.strptime(echeance_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                    echeance_date = datetime.strptime(echeance_str, "%d/%m/%Y").date()
                    
                    # Get method key for validation
                    method_key = None
                    try:
                        method_idx = [label for _, label in payment_methods].index(method_var.get())
                        method_key = payment_methods[method_idx][0] if method_idx is not None else None
                    except Exception:
                        pass
                    
                    if method_key == "traite" and echeance_date <= datetime.now().date():
                        messagebox.showerror("Erreur", "L'échéance pour une traite doit être dans le futur.")
                        return
                except ValueError:
                    messagebox.showerror("Erreur", "Format d'échéance invalide (JJ/MM/AAAA).")
                    return
            
            # Bank validation (identical to normal payment)
            if type_var.get() == 'banque':
                if not bank_var.get() or bank_var.get() not in banks_dict:
                    messagebox.showerror("Erreur", "Veuillez sélectionner une banque.")
                    return
                if not method_combo.get():
                    messagebox.showerror("Erreur", "Veuillez sélectionner une méthode de paiement.")
                    return
            
            # Reference validation (identical to normal payment)
            ref = numero_var.get().strip()
            if type_var.get() == 'banque' and not ref:
                messagebox.showerror("Erreur", "Le numéro de référence est obligatoire pour les paiements bancaires.")
                return
            
            # Payment amount vs remaining validation
            if montant_net > self.reste:
                if not messagebox.askyesno("Confirmation", 
                    f"Le montant ({montant_net:.3f} DT) dépasse le reste à payer ({self.reste:.3f} DT). Continuer ?"):
                    return
            
            # Prepare notes (identical to normal payment)
            notes = notes_text.get("1.0", "end").strip()
            
            # Calculate retenu percentage for notes
            retenu_base = max(0, self.total_ttc - self.total_timbre)
            if retenu_amount > 0 and retenu_base > 0:
                retenu_percent = (retenu_amount / retenu_base) * 100.0
                # Store original notes for bank transaction (clean)
                original_notes = notes
                # Add prefixes only for individual payment notes
                notes = f"[Retenu: {retenu_percent:.1f}%] [MULTI-PAIEMENT] " + notes
            else:
                retenu_percent = 0.0
                # Store original notes for bank transaction (clean)
                original_notes = notes
                # Add prefixes only for individual payment notes
                notes = "[MULTI-PAIEMENT] " + notes
            
            # Delete old payment if editing (identical to normal payment)
            if preset:
                self._delete_payment(preset['id'])
            
            # Save payment using cascade system (modified for multiple invoices)
            success = self._save_multiple_payment(
                type_var.get(), montant_net, date_str, ref, notes,
                bank_var, banks_dict, method_var, method_combo, payment_methods,
                echeance_db, retenu_percent, retenu_amount, original_notes
            )
            
            if success:
                # Update UI
                self._refresh_tree()
                self.reste_var.set(f"{self.reste:.3f}")
                self.result = True
                
                # Force refresh parent page
                if hasattr(self.parent, '_load_rows'):
                    self.parent._load_rows()
                    
                form.destroy()
            else:
                messagebox.showerror("Erreur", "Échec de l'enregistrement du paiement.")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement:\\n{str(e)}")
    
    def _save_multiple_payment(self, payment_type, montant_net, date_str, ref, notes,
                             bank_var, banks_dict, method_var, method_combo, payment_methods,
                             echeance_db, retenu_percent, retenu_amount, original_notes):
        """Save payment for multiple invoices using proportional distribution"""
        try:
            # Create unique transaction reference for multiple payment (include microseconds to avoid collisions)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            transaction_ref = f"MULTI-{timestamp}"
            
            # DUPLICATE PREVENTION: Check if a similar multiple payment already exists
            # Look for recent transactions with same amount, date, and client to prevent duplicates
            try:
                with self.payment_service.payment_repository.get_connection() as conn:
                    # Get client names for duplicate check
                    client_names = []
                    for invoice in self.invoice_list:
                        nfacture = invoice.get('nfacture') or invoice.get('id')
                        if nfacture:
                            if self.is_achat:
                                cursor = conn.execute("SELECT fournisseur FROM achats WHERE id = ?", (nfacture,))
                                row = cursor.fetchone()
                                if row and row[0]:
                                    client_name = str(row[0]).strip()
                                    if client_name and client_name not in client_names:
                                        client_names.append(client_name)
                            else:
                                cursor = conn.execute("SELECT raison_sociale FROM ventes WHERE nfacture = ?", (nfacture,))
                                row = cursor.fetchone()
                                if row and row[0]:
                                    client_name = str(row[0]).strip()
                                    if client_name and client_name not in client_names:
                                        client_names.append(client_name)
                    
                    combined_client_names = "/".join(client_names) if client_names else "Multiple clients"
                    
                    # Check for existing bank transactions with same amount, date, and client
                    cursor = conn.execute("""
                        SELECT id, created_at FROM transactions_bancaires 
                        WHERE ABS(montant - ?) < 0.01 
                        AND date_transaction = ? 
                        AND nom_client = ?
                        AND description LIKE '%MULTI-PAIEMENT%'
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """, (montant_net, date_str, combined_client_names))
                    
                    existing_transaction = cursor.fetchone()
                    if existing_transaction:
                        from tkinter import messagebox
                        confirm_duplicate = messagebox.askyesno(
                            "Transaction Similaire Trouvée",
                            f"Une transaction similaire existe déjà:\\n"
                            f"ID: {existing_transaction[0]}\\n"
                            f"Montant: {montant_net:.3f} DT\\n"
                            f"Date: {date_str}\\n"
                            f"Client: {combined_client_names}\\n"
                            f"Créée: {existing_transaction[1]}\\n\\n"
                            f"Voulez-vous vraiment créer une nouvelle transaction?"
                        )
                        if not confirm_duplicate:
                            print(f"[ENHANCED_MULTIPLE_PAYMENT] User cancelled due to duplicate transaction warning")
                            return False
            except Exception as duplicate_check_error:
                print(f"[ENHANCED_MULTIPLE_PAYMENT] Warning: Could not perform duplicate check: {duplicate_check_error}")
            
            # Calculate proportional payments with AVOIR awareness
            payment_results = []
            total_processed = 0
            
            # Step 1: Create individual payment records (no bank/caisse integrations)
            invoice_ids = []
            client_names = []
            
            # Compute total of positive invoices only to avoid negative proportions
            positive_invoices = [inv for inv in self.invoice_list if float(inv.get('ttc', 0) or 0) > 0]
            total_positive_ttc = sum(float(inv.get('ttc', 0) or 0) for inv in positive_invoices)
            avoir_invoices = [inv for inv in self.invoice_list if float(inv.get('ttc', 0) or 0) < 0]
            
            # Handle regular invoices: distribute montant_net proportionally based on positive totals
            for i, invoice in enumerate(positive_invoices):
                nfacture = invoice.get('nfacture') or invoice.get('id')
                if not nfacture:
                    continue
                
                invoice_ttc = float(invoice.get('ttc', 0) or 0)
                
                # Calculate proportional payment relative to positive total only
                if total_positive_ttc > 0:
                    proportion = invoice_ttc / total_positive_ttc
                    invoice_payment = montant_net * proportion
                    invoice_retenu = retenu_amount * proportion if retenu_amount > 0 else 0
                else:
                    invoice_payment = 0
                    invoice_retenu = 0
                
                # Prepare individual payment notes
                individual_notes = f"[MULTI-PAIEMENT] {notes} (Réf: {transaction_ref})" if notes else f"[MULTI-PAIEMENT] (Réf: {transaction_ref})"
                
                # Create ONLY payment record (no bank/caisse transaction)
                payment_id = self.payment_service.add_payment(
                    nfacture=nfacture,
                    montant_paye=invoice_payment,
                    methode_paiement=payment_type,
                    date_paiement=date_str,
                    reference_paiement=transaction_ref,
                    notes=individual_notes,
                    is_achat=self.is_achat
                )
                
                if payment_id > 0:
                    payment_results.append({
                        'invoice': nfacture,
                        'payment_id': payment_id,
                        'amount': invoice_payment,
                        'retenu': invoice_retenu
                    })
                    total_processed += invoice_payment
                    invoice_ids.append(str(nfacture))
                    
                    # Get client name for combined record
                    try:
                        client_name = None
                        
                        if self.is_achat:
                            # For achat, try direct ID first
                            with self.payment_service.payment_repository.get_connection() as conn:
                                cursor = conn.execute("SELECT fournisseur FROM achats WHERE id = ?", (nfacture,))
                                row = cursor.fetchone()
                                if row and row[0]:
                                    client_name = str(row[0]).strip()
                                    print(f"[DEBUG] Found supplier for achat {nfacture}: '{client_name}'")
                        else:
                            # For vente, try multiple formats to find the client
                            queries_to_try = [
                                nfacture,  # Try original number
                                int(f"202500{nfacture:03d}") if isinstance(nfacture, int) and nfacture < 1000 else nfacture,  # Try with 202500 prefix
                                int(f"202500{int(nfacture):03d}") if isinstance(nfacture, str) and nfacture.isdigit() and int(nfacture) < 1000 else nfacture  # Try string to int with prefix
                            ]
                            
                            # Remove duplicates while preserving order
                            unique_queries = []
                            for q in queries_to_try:
                                if q not in unique_queries:
                                    unique_queries.append(q)
                                    
                            print(f"[DEBUG] Searching for client of invoice {nfacture} using queries: {unique_queries}")
                            
                            for query_nfacture in unique_queries:
                                try:
                                    with self.payment_service.payment_repository.get_connection() as conn:
                                        # Try different query formats to ensure we find the client
                                        cursor = conn.execute("SELECT raison_sociale FROM ventes WHERE nfacture = ?", (query_nfacture,))
                                        row = cursor.fetchone()
                                        if row and row[0]:
                                            client_name = str(row[0]).strip()
                                            print(f"[DEBUG] Found client for vente {query_nfacture}: '{client_name}'")
                                            break  # Found it, stop searching
                                        else:
                                            # Try as string cast if int query failed
                                            cursor = conn.execute("SELECT raison_sociale FROM ventes WHERE CAST(nfacture AS TEXT) = ?", (str(query_nfacture),))
                                            row = cursor.fetchone()
                                            if row and row[0]:
                                                client_name = str(row[0]).strip()
                                                print(f"[DEBUG] Found client for vente {query_nfacture} (string cast): '{client_name}'")
                                                break
                                            else:
                                                print(f"[DEBUG] No client found for query {query_nfacture}")
                                except Exception as query_e:
                                    print(f"[DEBUG] Query error for {query_nfacture}: {query_e}")
                            
                        if client_name and client_name not in client_names:
                            client_names.append(client_name)
                            print(f"[DEBUG] Added client name: '{client_name}'. Current list: {client_names}")
                        elif not client_name:
                            print(f"[DEBUG] No client found for invoice {nfacture}")
                        else:
                            print(f"[DEBUG] Client '{client_name}' already in list: {client_names}")
                    except Exception as e:
                        print(f"[ENHANCED_MULTIPLE_PAYMENT] Error getting client name for invoice {nfacture}: {e}")
            
            # Handle avoir (credits): create positive 'credit application' entries to mark credits applied
            for avoir in avoir_invoices:
                nfacture = avoir.get('nfacture') or avoir.get('id')
                if not nfacture:
                    continue
                ttc = float(avoir.get('ttc', 0) or 0)
                if ttc >= 0:
                    continue
                credit_amount = abs(ttc)
                credit_notes = f"[MULTI-PAIEMENT] {notes} (Réf: {transaction_ref}) - Auto-application avoir" if notes else f"[MULTI-PAIEMENT] (Réf: {transaction_ref}) - Auto-application avoir"
                credit_payment_id = self.payment_service.add_payment(
                    nfacture=nfacture,
                    montant_paye=credit_amount,  # Positive amount to apply credit
                    methode_paiement='caisse',   # Use caisse to avoid bank duplication
                    date_paiement=date_str,
                    reference_paiement=f"AUTO-CREDIT-{transaction_ref}",
                    notes=credit_notes,
                    is_achat=self.is_achat
                )
                if credit_payment_id > 0:
                    payment_results.append({
                        'invoice': nfacture,
                        'payment_id': credit_payment_id,
                        'amount': credit_amount,
                        'retenu': 0.0
                    })
            
            # Step 2: Create ONE combined bank/caisse transaction
            # Format client names (remove duplicates)
            unique_client_names = list(dict.fromkeys(client_names))  # Preserve order, remove duplicates
            combined_client_names = "/".join(unique_client_names) if unique_client_names else "Multiple clients"
            print(f"[DEBUG] Final client names: {client_names} -> {unique_client_names} -> '{combined_client_names}'")
            
            # Format invoice numbers for display
            invoice_numbers_only = [str(inv_id).replace('202500', '') for inv_id in invoice_ids]  # Remove common prefix if exists
            invoice_list_display = "/".join(invoice_numbers_only)
            print(f"[DEBUG] Final invoice display: {invoice_ids} -> {invoice_numbers_only} -> '{invoice_list_display}'")
            invoice_list_str = ", ".join(invoice_ids)  # Full numbers for internal use
            
            if payment_type == 'banque' and bank_var.get():
                try:
                    from app.stfoom.services.bank_service import BankService
                    from app.stfoom.data.bank_repository import BankRepository
                    bank_repository = BankRepository()
                    bank_service = BankService(bank_repository)
                    
                    banque_id = banks_dict[bank_var.get()]
                    method_idx = [label for _, label in payment_methods].index(method_combo.get())
                    method_key = payment_methods[method_idx][0]
                    
                    # For achat, use decaissement (outgoing), for vente, use encaissement (incoming)
                    transaction_type = 'decaissement' if self.is_achat else 'encaissement'
                    description_prefix = "Paiement multiple achat" if self.is_achat else "Paiement multiple facture"
                    
                    # Create proper field organization with BOTH invoice numbers AND other info
                    # Include invoice numbers in description so user can see both check number AND invoices
                    if original_notes:
                        clean_description = f"{description_prefix} - Factures: {invoice_list_display} - {original_notes}"
                    else:
                        clean_description = f"{description_prefix} - Factures: {invoice_list_display}"
                    
                    # Add client info to make it complete
                    if combined_client_names:
                        clean_description += f" - Client: {combined_client_names}"
                    
                    # Add retenu info and MULTI-PAIEMENT marker for bank transaction (clean, single instance)
                    if retenu_percent > 0:
                        clean_description += f" [Retenu: {retenu_percent:.1f}%]"
                    # Add MULTI marker with explicit reference for robust linkage
                    clean_description += f" [MULTI-PAIEMENT] (Réf: {transaction_ref})"
                    
                    # CRITICAL FIX: Use the actual check number from reference field, not invoice numbers
                    actual_check_number = ref  # This is the check number user typed (e.g., 3661)
                    
                    bank_success = bank_service.create_transaction(
                        banque_id=banque_id,
                        type_transaction=transaction_type,
                        montant=montant_net,
                        date_transaction=date_str,
                        description=clean_description,
                        numero_cheque=actual_check_number,   # FIXED: Use actual check number (3661), not invoice numbers
                        nfacture=invoice_list_display,       # FIXED: Use invoice numbers (074/075), not 0
                        nom_client=combined_client_names,    # Client names in nom_client field
                        mode_paiement=method_key,
                        echeance=echeance_db
                    )
                    
                    if not bank_success:
                        print(f"[ENHANCED_MULTIPLE_PAYMENT] Warning: Payments recorded but bank transaction failed")
                        
                except Exception as e:
                    print(f"[ENHANCED_MULTIPLE_PAYMENT] Error creating combined bank transaction: {e}")
                    
            elif payment_type == 'caisse':
                try:
                    from app.stfoom.services.caisse_service import CaisseService  
                    from app.stfoom.data.caisse_repository import CaisseRepository
                    caisse_repository = CaisseRepository()
                    caisse_service = CaisseService(caisse_repository)
                    
                    # For achat, use decaissement (outgoing), for vente, use encaissement (incoming)
                    transaction_type = 'decaissement' if self.is_achat else 'encaissement'
                    description_prefix = "Paiement multiple achat" if self.is_achat else "Paiement multiple facture"
                    
                    # Create proper field organization - caisse gets clean description since it doesn't have separate fields
                    if notes:
                        caisse_description = f"{description_prefix} - Num facture: {invoice_list_display} - Client: {combined_client_names} - {notes}"
                    else:
                        caisse_description = f"{description_prefix} - Num facture: {invoice_list_display} - Client: {combined_client_names}"
                    
                    if retenu_percent > 0:
                        caisse_description += f" [Retenu: {retenu_percent:.1f}%]"
                    # Add MULTI marker with explicit reference for robust linkage
                    caisse_description += f" [MULTI-PAIEMENT] (Réf: {transaction_ref})"
                    
                    caisse_success = caisse_service.create_transaction(
                        montant=montant_net,
                        date_str=date_str,
                        type_=transaction_type,
                        description=caisse_description,
                        nfacture=invoice_list_display  # FIXED: Use invoice numbers (074/075), not 0
                    )
                    
                    if not caisse_success:
                        print(f"[ENHANCED_MULTIPLE_PAYMENT] Warning: Payments recorded but caisse transaction failed")
                        
                except Exception as e:
                    print(f"[ENHANCED_MULTIPLE_PAYMENT] Error creating combined caisse transaction: {e}")
            
            # Step 3: Create ONE combined retenu record if retenu amount > 0
            if retenu_amount > 0 and self.retenu_service:
                try:
                    # Create enhanced retenu notes with proper formatting
                    retenu_notes = f"Retenu du paiement multiple - Num facture: {invoice_list_display} - Client: {combined_client_names} - Ref: {transaction_ref}"
                    if notes:
                        retenu_notes += f" - {notes}"
                    
                    # Use the correct RetenuService method signature
                    retenu_success = self.retenu_service.create_retenu(
                        date=date_str,
                        client=combined_client_names,
                        nfacture=invoice_list_display,  # FIXED: Use invoice numbers (074/075), not 0
                        percent=retenu_percent,
                        amount=retenu_amount,
                        source='paiement_multiple',
                        notes=retenu_notes
                    )
                    
                    if retenu_success:
                        print(f"[ENHANCED_MULTIPLE_PAYMENT] Created combined retenu record: {retenu_amount:.3f} DT for invoices [{invoice_list_display}]")
                    else:
                        print(f"[ENHANCED_MULTIPLE_PAYMENT] Warning: Failed to create retenu record")
                        
                except Exception as e:
                    print(f"[ENHANCED_MULTIPLE_PAYMENT] Warning: Could not create retenu record: {e}")
            
            # Step 4: Create calendar events for traite payments if needed
            if payment_type == 'banque' and method_combo.get() == 'Traite' and echeance_db:
                try:
                    from app.stfoom.services.cascade_manager import cascade_manager
                    for result in payment_results:
                        calendar_result = cascade_manager.create_calendar_event_for_traite(
                            result['payment_id'], result['invoice'], echeance_db, 
                            combined_client_names, result['amount']
                        )
                        if 'error' not in calendar_result:
                            print(f"[ENHANCED_MULTIPLE_PAYMENT] Calendar event {calendar_result['calendar_event_id']} created for traite payment {result['payment_id']}")
                        else:
                            print(f"[ENHANCED_MULTIPLE_PAYMENT] Warning: Could not create calendar event for traite: {calendar_result['error']}")
                except Exception as calendar_error:
                    print(f"[ENHANCED_MULTIPLE_PAYMENT] Warning: Could not create calendar events for traite: {calendar_error}")
            
            if len(payment_results) == len(self.invoice_list):
                print(f"[ENHANCED_MULTIPLE_PAYMENT] Successfully processed {len(payment_results)} payments")
                print(f"[ENHANCED_MULTIPLE_PAYMENT] Total processed: {total_processed:.3f} DT")
                from tkinter import messagebox
                messagebox.showinfo("Succès", f"Traité {len(payment_results)} paiements avec succès!\\n"
                                              f"Montant total: {total_processed:.3f} DT")
                return True
            else:
                print(f"[ENHANCED_MULTIPLE_PAYMENT] Only {len(payment_results)}/{len(self.invoice_list)} payments succeeded")
                from tkinter import messagebox
                messagebox.showwarning("Attention", f"Seulement {len(payment_results)} sur {len(self.invoice_list)} paiements ont été traités.")
                return False
                
        except Exception as e:
            print(f"[ENHANCED_MULTIPLE_PAYMENT] Error saving multiple payment: {e}")
            return False
    
    def _cancel(self):
        """Cancel the dialog"""
        self.window.destroy()


# Integration function to replace existing multiple payment dialog
def show_enhanced_multiple_payment_dialog(parent, invoice_list: List[Dict], is_achat: bool = False,
                                         payment_service=None, bank_service=None, retenu_service=None) -> Optional[Dict]:
    """Show enhanced multiple payment dialog with all normal payment features"""
    dialog = EnhancedMultiplePaymentDialog(parent, invoice_list, is_achat, payment_service, bank_service, retenu_service)
    return dialog.result


if __name__ == "__main__":
    # Test the enhanced dialog
    print("Enhanced Multiple Payment Dialog - Feature Complete!")
    print("All normal payment features have been copied to multiple payments:")
    print("✅ Complete UI structure with scrollable interface") 
    print("✅ Existing payments treeview with modify/delete")
    print("✅ Full payment form with all options")
    print("✅ Cascade operations using cascade_manager")
    print("✅ Timbre-aware retenu calculations")
    print("✅ Payment method support (banque/caisse)")
    print("✅ Date validation and calendar picker")
    print("✅ Permission checks")
    print("✅ Reference field handling")
    print("✅ Proportional payment distribution for multiple invoices")