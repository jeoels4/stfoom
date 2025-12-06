"""
stfoom.ui.backup_page
=====================
Backup management UI page for STFOOM.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import simpledialog
from datetime import datetime
import threading
import os
import json

from connection import backup_system

class BackupPage(ttk.Frame):
    """Backup management page."""
    
    def __init__(self, parent, go_home):
        super().__init__(parent)
        self.go_home = go_home
        self.setup_ui()
        self.refresh_backups()
        
        # Start periodic refresh
        self.after(30000, self.periodic_refresh)  # Refresh every 30 seconds
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="🔄 Gestion des Sauvegardes",
            font=("Segoe UI", 24, "bold"),
            fg="#2c3e50"
        )
        title_label.pack(pady=(0, 20))
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Statut du Système de Sauvegarde", padding=15)
        status_frame.pack(fill="x", pady=(0, 20))
        
        self.status_label = tk.Label(
            status_frame,
            text="Chargement...",
            font=("Segoe UI", 12),
            fg="#34495e"
        )
        self.status_label.pack()
        
        # Server status frame
        self.server_status_frame = ttk.LabelFrame(main_frame, text="Statut du Serveur de Sauvegarde", padding=15)
        self.server_status_frame.pack(fill="x", pady=(0, 20))
        
        self.server_status_label = tk.Label(
            self.server_status_frame,
            text="Chargement...",
            font=("Segoe UI", 12),
            fg="#34495e"
        )
        self.server_status_label.pack()
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(0, 20))
        
        # Configure button frame to expand
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)
        btn_frame.columnconfigure(3, weight=1)
        btn_frame.columnconfigure(4, weight=1)
        btn_frame.columnconfigure(5, weight=1)
        
        # Create backup button
        create_btn = tk.Button(
            btn_frame,
            text="💾 Créer Sauvegarde",
            command=self.create_manual_backup,
            font=("Segoe UI", 12, "bold"),
            bg="#27ae60",
            fg="#fff",
            activebackground="#219150",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        create_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew", ipadx=10, ipady=5)
        
        # Restore button
        restore_btn = tk.Button(
            btn_frame,
            text="🔄 Restaurer",
            command=self.restore_backup,
            font=("Segoe UI", 12, "bold"),
            bg="#e67e22",
            fg="#fff",
            activebackground="#d35400",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        restore_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew", ipadx=10, ipady=5)
        
        # Check integrity button
        integrity_btn = tk.Button(
            btn_frame,
            text="🔍 Intégrité",
            command=self.check_integrity,
            font=("Segoe UI", 12, "bold"),
            bg="#3498db",
            fg="#fff",
            activebackground="#2980b9",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        integrity_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew", ipadx=10, ipady=5)
        
        # Cleanup button
        cleanup_btn = tk.Button(
            btn_frame,
            text="🧹 Nettoyer",
            command=self.cleanup_backups,
            font=("Segoe UI", 12, "bold"),
            bg="#95a5a6",
            fg="#fff",
            activebackground="#7f8c8d",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        cleanup_btn.grid(row=0, column=3, padx=5, pady=5, sticky="ew", ipadx=10, ipady=5)
        
        # Sync to server button
        sync_server_btn = tk.Button(
            btn_frame,
            text="🔄 Serveur",
            command=self.sync_to_server,
            font=("Segoe UI", 12, "bold"),
            bg="#9b59b6",
            fg="#fff",
            activebackground="#8e44ad",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        sync_server_btn.grid(row=0, column=4, padx=5, pady=5, sticky="ew", ipadx=10, ipady=5)
        
        # Back button
        back_btn = tk.Button(
            btn_frame,
            text="← Retour",
            command=self.go_home,
            font=("Segoe UI", 12, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50",
            activebackground="#bdc3c7",
            activeforeground="#2c3e50",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        back_btn.grid(row=0, column=5, padx=5, pady=5, sticky="ew", ipadx=10, ipady=5)
        
        # Backups list frame
        list_frame = ttk.LabelFrame(main_frame, text="Historique des Sauvegardes", padding=15)
        list_frame.pack(fill="both", expand=True)
        
        # Create treeview for backups
        columns = ("Date", "Type", "Taille", "Statut", "Description")
        self.backup_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        self.backup_tree.heading("Date", text="Date")
        self.backup_tree.heading("Type", text="Type")
        self.backup_tree.heading("Taille", text="Taille")
        self.backup_tree.heading("Statut", text="Statut")
        self.backup_tree.heading("Description", text="Description")
        
        self.backup_tree.column("Date", width=150)
        self.backup_tree.column("Type", width=100)
        self.backup_tree.column("Taille", width=100)
        self.backup_tree.column("Statut", width=100)
        self.backup_tree.column("Description", width=300)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.backup_tree.yview)
        self.backup_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.backup_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind double-click to restore
        self.backup_tree.bind("<Double-1>", self.on_backup_double_click)
        
        # Right-click menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Restaurer", command=self.restore_selected)
        self.context_menu.add_command(label="Supprimer", command=self.delete_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Voir Détails", command=self.show_backup_details)
        
        self.backup_tree.bind("<Button-3>", self.show_context_menu)
    
    def refresh_backups(self):
        """Refresh the backups list."""
        try:
            # Clear existing items
            for item in self.backup_tree.get_children():
                self.backup_tree.delete(item)
            
            # Get backups
            backups = backup_system.list_backups()
            
            # Add to treeview
            for backup in backups:
                date_str = datetime.fromtimestamp(backup.timestamp).strftime("%d/%m/%Y %H:%M")
                size_str = f"{backup.size_bytes / (1024*1024):.1f} MB"
                status_str = "✅ OK" if backup.success else "❌ Erreur"
                
                self.backup_tree.insert("", "end", values=(
                    date_str,
                    backup.backup_type.title(),
                    size_str,
                    status_str,
                    backup.description
                ), tags=(backup.filename,))
            
            # Update status
            self.update_status()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des sauvegardes: {e}")
    
    def update_status(self):
        """Update the status display."""
        try:
            status = backup_system.get_backup_status()
            
            if status['status'] == 'no_backups':
                status_text = "Aucune sauvegarde trouvée"
            else:
                last_backup = datetime.fromtimestamp(status['last_backup']).strftime("%d/%m/%Y %H:%M")
                next_backup = datetime.fromtimestamp(status['next_auto_backup']).strftime("%d/%m/%Y %H:%M")
                
                status_text = f"""
                Dernière sauvegarde: {last_backup}
                Prochaine sauvegarde automatique: {next_backup}
                Nombre total de sauvegardes: {status['backup_count']}
                Taille totale: {status['total_size_mb']} MB
                """
            
            self.status_label.config(text=status_text)
            
            # Update server status
            self.update_server_status()
            
        except Exception as e:
            self.status_label.config(text=f"Erreur de statut: {e}")
    
    def update_server_status(self):
        """Update the server status display."""
        try:
            server_status = backup_system.get_server_backup_status()
            
            if not server_status['server_online']:
                status_text = "Serveur hors ligne"
                self.server_status_frame.configure(text="Statut du Serveur de Sauvegarde (Hors Ligne)")
            elif server_status['status'] == 'no_backups':
                status_text = "Aucune sauvegarde sur le serveur"
                self.server_status_frame.configure(text="Statut du Serveur de Sauvegarde")
            else:
                last_backup = datetime.fromtimestamp(server_status['last_backup']).strftime("%d/%m/%Y %H:%M")
                status_text = f"""
                Dernière sauvegarde serveur: {last_backup}
                Nombre total de sauvegardes serveur: {server_status['backup_count']}
                Taille totale serveur: {server_status['total_size_mb']} MB
                """
                self.server_status_frame.configure(text="Statut du Serveur de Sauvegarde")
            
            self.server_status_label.config(text=status_text)
            
        except Exception as e:
            self.server_status_label.config(text=f"Erreur de statut serveur: {e}")
    
    def create_manual_backup(self):
        """Create a manual backup."""
        try:
            # Get description from user
            description = simpledialog.askstring(
                "Sauvegarde Manuelle",
                "Description de la sauvegarde (optionnel):"
            )
            
            if description is None:  # User cancelled
                return
            
            # Create backup in background thread
            def backup_thread():
                try:
                    backup_info = backup_system.create_backup("manual", description or "")
                    
                    # Update UI in main thread
                    self.after(0, lambda: self.on_backup_complete(backup_info))
                    
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}"))
            
            threading.Thread(target=backup_thread, daemon=True).start()
            
            # Show progress message
            messagebox.showinfo("Sauvegarde", "Sauvegarde en cours...")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la création de la sauvegarde: {e}")
    
    def on_backup_complete(self, backup_info):
        """Called when backup is complete."""
        if backup_info.success:
            messagebox.showinfo("Succès", f"Sauvegarde créée avec succès!\nFichier: {backup_info.filename}")
        else:
            messagebox.showerror("Erreur", f"Échec de la sauvegarde: {backup_info.error_message}")
        
        self.refresh_backups()
    
    def restore_backup(self):
        """Restore a backup."""
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner une sauvegarde à restaurer.")
            return
        
        item = selection[0]
        backup_filename = self.backup_tree.item(item, "tags")[0]
        
        # Confirm restore
        result = messagebox.askyesno(
            "Confirmer Restauration",
            f"Êtes-vous sûr de vouloir restaurer la sauvegarde '{backup_filename}'?\n\n"
            "ATTENTION: Cela remplacera les données actuelles!"
        )
        
        if not result:
            return
        
        try:
            # Restore in background thread
            def restore_thread():
                try:
                    success = backup_system.restore_backup(backup_filename)
                    
                    # Update UI in main thread
                    self.after(0, lambda: self.on_restore_complete(success))
                    
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Erreur", f"Erreur lors de la restauration: {e}"))
            
            threading.Thread(target=restore_thread, daemon=True).start()
            
            # Show progress message
            messagebox.showinfo("Restauration", "Restauration en cours...")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la restauration: {e}")
    
    def on_restore_complete(self, success):
        """Called when restore is complete."""
        if success:
            messagebox.showinfo("Succès", "Restauration terminée avec succès!\nL'application va redémarrer.")
            # Restart the application
            self.after(2000, self.restart_application)
        else:
            messagebox.showerror("Erreur", "Échec de la restauration.")
    
    def restart_application(self):
        """Restart the application."""
        import sys
        import subprocess
        
        try:
            # Restart the current script
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de redémarrer l'application: {e}")
    
    def check_integrity(self):
        """Check database integrity."""
        try:
            integrity = backup_system.check_database_integrity()
            
            if integrity['status'] == 'ok':
                messagebox.showinfo("Intégrité", "La base de données est en bon état.")
            elif integrity['status'] == 'corrupted':
                error_msg = "La base de données est corrompue:\n\n"
                for error in integrity['errors']:
                    error_msg += f"• {error}\n"
                
                result = messagebox.askyesno(
                    "Base de Données Corrompue",
                    error_msg + "\nVoulez-vous tenter une réparation?"
                )
                
                if result:
                    self.repair_database()
            else:
                messagebox.showerror("Erreur", f"Erreur lors de la vérification: {integrity['message']}")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la vérification d'intégrité: {e}")
    
    def repair_database(self):
        """Repair the database."""
        try:
            result = messagebox.askyesno(
                "Réparation",
                "Une sauvegarde sera créée avant la réparation.\nContinuer?"
            )
            
            if not result:
                return
            
            # Repair in background thread
            def repair_thread():
                try:
                    success = backup_system.repair_database()
                    
                    # Update UI in main thread
                    self.after(0, lambda: self.on_repair_complete(success))
                    
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Erreur", f"Erreur lors de la réparation: {e}"))
            
            threading.Thread(target=repair_thread, daemon=True).start()
            
            # Show progress message
            messagebox.showinfo("Réparation", "Réparation en cours...")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la réparation: {e}")
    
    def on_repair_complete(self, success):
        """Called when repair is complete."""
        if success:
            messagebox.showinfo("Succès", "Réparation terminée avec succès!")
        else:
            messagebox.showerror("Erreur", "Échec de la réparation.")
    
    def cleanup_backups(self):
        """Clean up old backups."""
        try:
            result = messagebox.askyesno(
                "Nettoyage",
                "Supprimer les anciennes sauvegardes?\n\n"
                "Cela supprimera:\n"
                "• Les sauvegardes locales de plus de 30 jours\n"
                "• Les sauvegardes locales en excès (plus de 50)\n"
                "• Les sauvegardes serveur de plus de 90 jours\n"
                "• Les sauvegardes serveur en excès (plus de 200)"
            )
            
            if not result:
                return
            
            # Cleanup in background thread
            def cleanup_thread():
                try:
                    # Clean local backups
                    backup_system.cleanup_old_backups()
                    
                    # Clean server backups
                    backup_system.cleanup_server_backups()
                    
                    # Update UI in main thread
                    self.after(0, lambda: self.on_cleanup_complete())
                    
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Erreur", f"Erreur lors du nettoyage: {e}"))
            
            threading.Thread(target=cleanup_thread, daemon=True).start()
            
            # Show progress message
            messagebox.showinfo("Nettoyage", "Nettoyage en cours...")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du nettoyage: {e}")
    
    def on_cleanup_complete(self):
        """Called when cleanup is complete."""
        messagebox.showinfo("Succès", "Nettoyage terminé!")
        self.refresh_backups()
    
    def sync_to_server(self):
        """Sync all local backups to server."""
        try:
            result = messagebox.askyesno(
                "Synchronisation Serveur",
                "Synchroniser toutes les sauvegardes locales vers le serveur?\n\n"
                "Cela copiera toutes les sauvegardes locales vers le serveur."
            )
            
            if not result:
                return
            
            # Sync in background thread
            def sync_thread():
                try:
                    backups = backup_system.list_backups()
                    synced_count = 0
                    
                    for backup in backups:
                        backup_path = os.path.join(backup_system.BACKUP_DIR, backup.filename)
                        info_path = backup_system.get_backup_info_filepath(backup.filename)
                        
                        if os.path.exists(backup_path):
                            success = backup_system.sync_backup_to_server(backup.filename, backup_path, info_path)
                            if success:
                                synced_count += 1
                    
                    # Update UI in main thread
                    self.after(0, lambda: self.on_sync_complete(synced_count, len(backups)))
                    
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Erreur", f"Erreur lors de la synchronisation: {e}"))
            
            threading.Thread(target=sync_thread, daemon=True).start()
            
            # Show progress message
            messagebox.showinfo("Synchronisation", "Synchronisation vers le serveur en cours...")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la synchronisation: {e}")
    
    def on_sync_complete(self, synced_count, total_count):
        """Called when sync is complete."""
        messagebox.showinfo("Succès", f"Synchronisation terminée!\n{synced_count}/{total_count} sauvegardes synchronisées.")
        self.refresh_backups()
    
    def on_backup_double_click(self, event):
        """Handle double-click on backup item."""
        self.restore_selected()
    
    def restore_selected(self):
        """Restore the selected backup."""
        self.restore_backup()
    
    def delete_selected(self):
        """Delete the selected backup."""
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner une sauvegarde à supprimer.")
            return
        
        item = selection[0]
        backup_filename = self.backup_tree.item(item, "tags")[0]
        
        result = messagebox.askyesno(
            "Confirmer Suppression",
            f"Êtes-vous sûr de vouloir supprimer la sauvegarde '{backup_filename}'?"
        )
        
        if result:
            try:
                backup_path = os.path.join(backup_system.BACKUP_DIR, backup_filename)
                info_path = backup_system.get_backup_info_filepath(backup_filename)
                
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                if os.path.exists(info_path):
                    os.remove(info_path)
                
                messagebox.showinfo("Succès", "Sauvegarde supprimée!")
                self.refresh_backups()
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
    
    def show_backup_details(self):
        """Show details of the selected backup."""
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner une sauvegarde.")
            return
        
        item = selection[0]
        backup_filename = self.backup_tree.item(item, "tags")[0]
        
        try:
            info_path = backup_system.get_backup_info_filepath(backup_filename)
            if os.path.exists(info_path):
                with open(info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                
                details = f"""
                Fichier: {info['filename']}
                Date: {datetime.fromtimestamp(info['timestamp']).strftime('%d/%m/%Y %H:%M:%S')}
                Type: {info['backup_type']}
                Taille: {info['size_bytes'] / (1024*1024):.3f} MB
                Checksum: {info['checksum']}
                Description: {info['description']}
                Statut: {'✅ OK' if info['success'] else '❌ Erreur'}
                """
                
                if info.get('error_message'):
                    details += f"\nErreur: {info['error_message']}"
                
                messagebox.showinfo("Détails de la Sauvegarde", details)
            else:
                messagebox.showinfo("Détails", "Informations détaillées non disponibles pour cette sauvegarde.")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'affichage des détails: {e}")
    
    def show_context_menu(self, event):
        """Show context menu for backup items."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def periodic_refresh(self):
        """Periodically refresh the backups list."""
        self.refresh_backups()
        self.after(30000, self.periodic_refresh)  # Refresh every 30 seconds 