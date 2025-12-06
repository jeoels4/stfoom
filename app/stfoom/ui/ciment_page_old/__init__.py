"""
Ciment Page - Component-Based Architecture
==========================================
Main orchestrator for the refactored Ciment management system

This replaces the monolithic 1,888-line ciment_page_simple.py with:
- Clean component-based architecture
- Dependency injection for services
- Lightweight coordination between components
- Single responsibility principle

Components:
- CimentService: Business logic and data operations
- BLManager: Bon de Livraison UI operations
- FactureManager: Invoice generation and management
- AvoirManager: Credit note calculations and tracking

Benefits:
- 90% reduction in main class size (1,888 → ~200 lines)
- Better maintainability and testability
- Component reusability across different contexts
- Cleaner separation of concerns
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from typing import Optional

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import unified logger
try:
    from unified_logger import log_ui_error, log_ui_info
except ImportError:
    def log_ui_error(component, message, context=None, exception=None):
        print(f"[UI ERROR] {component}: {message}")
    def log_ui_info(component, message, context=None):
        print(f"[UI INFO] {component}: {message}")

# Import service and components
from stfoom.ui.ciment_page.services.ciment_service import CimentService, get_ciment_service
from stfoom.ui.ciment_page.components.bl_manager import BLManager, create_bl_manager
from stfoom.ui.ciment_page.components.facture_manager import FactureManager, create_facture_manager
from stfoom.ui.ciment_page.components.avoir_manager import AvoirManager, create_avoir_manager

class CimentPage:
    """
    Main Ciment Page - Component Orchestrator
    
    This class coordinates the ciment management components:
    - BL Manager for delivery note operations
    - Facture Manager for invoice operations  
    - Avoir Manager for credit note operations
    
    Responsibilities:
    - Component initialization and coordination
    - Inter-component communication
    - User authentication and permissions
    - Main UI layout and navigation
    """
    
    def __init__(self, parent, di_container=None, go_back=None):
        """Initialize the Ciment Page with component-based architecture."""
        try:
            self.parent = parent
            self.di_container = di_container
            self.go_back = go_back
            
            # Initialize service
            self.service = get_ciment_service()
            
            # Set current user from authentication system
            self._set_current_user()
            
            # Component instances
            self.bl_manager: Optional[BLManager] = None
            self.facture_manager: Optional[FactureManager] = None
            self.avoir_manager: Optional[AvoirManager] = None
            
            # Main frame
            self.main_frame = ttk.Frame(parent)
            
            # Create UI
            self._create_header()
            self._create_main_content()
            self._setup_component_communication()
            
            log_ui_info("CimentPage", "Component-based Ciment Page initialized successfully")
            
        except Exception as e:
            log_ui_error("CimentPage", "Error initializing Ciment Page", None, e)
            messagebox.showerror("Erreur", f"Erreur lors de l'initialisation: {str(e)}")
    
    def pack(self, **kwargs):
        """Pack the main frame."""
        self.main_frame.pack(**kwargs)
    
    def _set_current_user(self):
        """Set current user for the service."""
        try:
            from stfoom.logic.access_control import auth_manager
            if auth_manager.current_user:
                user_id = auth_manager.current_user.id
                self.service.set_current_user(str(user_id))
                log_ui_info("CimentPage", f"Set current user: {user_id}")
            else:
                log_ui_error("CimentPage", "No authenticated user found")
        except Exception as e:
            log_ui_error("CimentPage", "Error setting current user", None, e)
    
    def _create_header(self):
        """Create the page header with navigation."""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Back button
        if self.go_back:
            back_btn = ttk.Button(header_frame, text="← Retour", command=self.go_back)
            back_btn.pack(side="left")
        
        # Title
        title_label = ttk.Label(header_frame, text="🏗️ Ciment / Matière Première", 
                               font=("Segoe UI", 16, "bold"))
        title_label.pack(side="left", padx=(20, 0))
        
        # Status indicator
        self.status_label = ttk.Label(header_frame, text="✅ Système opérationnel", 
                                     font=("Segoe UI", 10))
        self.status_label.pack(side="right")
        
        # Separator
        separator = ttk.Separator(self.main_frame, orient="horizontal")
        separator.pack(fill="x", padx=10, pady=5)
    
    def _create_main_content(self):
        """Create the main content area with components."""
        try:
            # Create notebook for tabbed interface
            self.notebook = ttk.Notebook(self.main_frame)
            self.notebook.pack(fill="both", expand=True, padx=10, pady=(5, 10))
            
            # Tab 1: Bon de Livraison Management
            bl_tab = ttk.Frame(self.notebook)
            self.notebook.add(bl_tab, text="📝 Bons de Livraison")
            
            self.bl_manager = create_bl_manager(bl_tab, self.service)
            bl_section = self.bl_manager.create_bl_section(bl_tab)
            bl_section.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Tab 2: Facture Management
            facture_tab = ttk.Frame(self.notebook)
            self.notebook.add(facture_tab, text="📄 Factures")
            
            self.facture_manager = create_facture_manager(facture_tab, self.service)
            facture_section = self.facture_manager.create_facture_section(facture_tab)
            facture_section.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Tab 3: Avoir Management
            avoir_tab = ttk.Frame(self.notebook)
            self.notebook.add(avoir_tab, text="💰 Avoirs")
            
            self.avoir_manager = create_avoir_manager(avoir_tab, self.service)
            avoir_section = self.avoir_manager.create_avoir_section(avoir_tab)
            avoir_section.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Tab 4: Statistics and Reports (placeholder for future)
            stats_tab = ttk.Frame(self.notebook)
            self.notebook.add(stats_tab, text="📊 Statistiques")
            
            self._create_statistics_tab(stats_tab)
            
            log_ui_info("CimentPage", "All components created successfully")
            
        except Exception as e:
            log_ui_error("CimentPage", "Error creating main content", None, e)
            # Create minimal error content
            error_label = ttk.Label(self.main_frame, 
                                  text="❌ Erreur lors du chargement des composants",
                                  font=("Segoe UI", 12))
            error_label.pack(expand=True)
    
    def _create_statistics_tab(self, parent):
        """Create statistics and reporting tab (placeholder)."""
        # This is a placeholder for future statistics implementation
        placeholder_frame = ttk.Frame(parent)
        placeholder_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(placeholder_frame, 
                 text="📊 Statistiques et Rapports", 
                 font=("Segoe UI", 16, "bold")).pack(pady=(0, 20))
        
        ttk.Label(placeholder_frame, 
                 text="Cette section contiendra :\n"
                      "• Graphiques de performance mensuelle\n"
                      "• Analyses des fournisseurs\n"
                      "• Rapports d'avoir automatisés\n"
                      "• Export vers Excel/PDF\n\n"
                      "🚧 En cours de développement...",
                 font=("Segoe UI", 10),
                 justify="left").pack(anchor="w")
        
        # Quick stats button
        ttk.Button(placeholder_frame, 
                  text="📈 Statistiques rapides", 
                  command=self._show_quick_stats).pack(pady=(20, 0), anchor="w")
    
    def _setup_component_communication(self):
        """Setup communication between components."""
        try:
            if self.bl_manager and self.facture_manager:
                # When BL is created, refresh facture manager's BL selection
                def on_bl_created(bl):
                    if self.facture_manager:
                        self.facture_manager.refresh_bl_selection()
                
                # When BL is deleted, refresh facture manager's BL selection  
                def on_bl_deleted(bl_id):
                    if self.facture_manager:
                        self.facture_manager.refresh_bl_selection()
                
                self.bl_manager.on_bl_created = on_bl_created
                self.bl_manager.on_bl_deleted = on_bl_deleted
            
            if self.facture_manager and self.avoir_manager:
                # When facture is created, could trigger avoir calculations
                def on_facture_created(facture):
                    if self.avoir_manager:
                        self.avoir_manager.refresh_monthly_avoir()
                
                self.facture_manager.on_facture_created = on_facture_created
            
            log_ui_info("CimentPage", "Component communication setup completed")
            
        except Exception as e:
            log_ui_error("CimentPage", "Error setting up component communication", None, e)
    
    def _show_quick_stats(self):
        """Show quick statistics dialog."""
        try:
            from datetime import date
            current_date = date.today()
            
            # Get current month statistics
            stats = self.service.calculate_monthly_statistics(current_date.month, current_date.year)
            
            if not stats:
                messagebox.showinfo("Statistiques", "Aucune donnée disponible pour ce mois")
                return
            
            # Format statistics message
            stats_text = f"📊 Statistiques {current_date.month}/{current_date.year}\n\n"
            stats_text += f"Total BLs: {stats.get('total_bls', 0)}\n"
            stats_text += f"Quantité totale: {stats.get('total_quantity', 0):.3f}\n"
            stats_text += f"Valeur totale: {stats.get('total_value', 0):.3f} DA\n\n"
            
            fournisseurs = stats.get('fournisseurs', {})
            if fournisseurs:
                stats_text += "Top fournisseurs:\n"
                sorted_fournisseurs = sorted(fournisseurs.items(), 
                                           key=lambda x: x[1]['value'], 
                                           reverse=True)[:3]
                for fournisseur, data in sorted_fournisseurs:
                    stats_text += f"• {fournisseur}: {data['value']:.3f} DA\n"
            
            messagebox.showinfo("Statistiques Rapides", stats_text)
            
        except Exception as e:
            log_ui_error("CimentPage", "Error showing quick stats", None, e)
            messagebox.showerror("Erreur", f"Erreur lors du calcul des statistiques: {str(e)}")
    
    def refresh_all_components(self):
        """Refresh all components data."""
        try:
            if self.bl_manager:
                self.bl_manager.refresh_bl_list()
            
            if self.facture_manager:
                self.facture_manager.refresh_facture_list()
                self.facture_manager.refresh_bl_selection()
            
            if self.avoir_manager:
                self.avoir_manager.refresh_monthly_avoir()
                self.avoir_manager.refresh_avoir_history()
            
            self.status_label.config(text="🔄 Données actualisées")
            self.main_frame.after(2000, lambda: self.status_label.config(text="✅ Système opérationnel"))
            
            log_ui_info("CimentPage", "All components refreshed successfully")
            
        except Exception as e:
            log_ui_error("CimentPage", "Error refreshing components", None, e)
            self.status_label.config(text="❌ Erreur de rafraîchissement")

# Export the class for compatibility with main.py
__all__ = ['CimentPage']
