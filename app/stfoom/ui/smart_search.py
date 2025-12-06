"""
Universal Smart Search Component for STFOOM
==========================================
This component provides intelligent search functionality across all pages,
searching through all relevant data and displaying contextual results.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Callable, Any, Optional
import threading
import time
from datetime import datetime

class SmartSearchWidget:
    """Universal smart search widget that can search across multiple data sources."""
    
    def __init__(self, parent: tk.Widget, search_providers: Dict[str, Callable] = None):
        """
        Initialize the smart search widget.
        
        Args:
            parent: Parent widget
            search_providers: Dictionary mapping category names to search functions
        """
        self.parent = parent
        self.search_providers = search_providers or {}
        self.search_debounce_id = None
        self.current_results = []
        
        # Create UI components
        self._create_ui()
        
    def _create_ui(self):
        """Create the smart search UI components."""
        # Main container with modern styling
        self.container = ttk.Frame(self.parent)
        self.container.pack(fill="x", pady=5, padx=10)
        
        # Search header frame
        header_frame = ttk.Frame(self.container)
        header_frame.pack(fill="x", pady=(0, 5))
        
        # Search icon and title
        ttk.Label(header_frame, text="🔍", font=('Arial', 16)).pack(side="left", padx=(0, 5))
        ttk.Label(header_frame, text="Recherche Intelligente", font=('Arial', 12, 'bold')).pack(side="left")
        
        # Search entry frame
        entry_frame = ttk.Frame(self.container)
        entry_frame.pack(fill="x", pady=(0, 5))
        
        # Search entry
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(entry_frame, textvariable=self.search_var, 
                                     font=('Arial', 11), width=50)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Search button
        self.search_btn = ttk.Button(entry_frame, text="Rechercher", 
                                    command=self._perform_search, width=12)
        self.search_btn.pack(side="right", padx=(5, 0))
        
        # Clear button
        self.clear_btn = ttk.Button(entry_frame, text="✕", width=3,
                                   command=self._clear_search)
        self.clear_btn.pack(side="right")
        
        # Results frame (initially hidden)
        self.results_frame = ttk.LabelFrame(self.container, text="Résultats de recherche", padding=10)
        
        # Results treeview
        self.results_tree = ttk.Treeview(self.results_frame, show="tree headings", height=8)
        self.results_tree["columns"] = ("type", "content", "details")
        
        # Configure columns
        self.results_tree.heading("#0", text="🔍")
        self.results_tree.heading("type", text="Type")
        self.results_tree.heading("content", text="Contenu")
        self.results_tree.heading("details", text="Détails")
        
        self.results_tree.column("#0", width=30, minwidth=30)
        self.results_tree.column("type", width=100, minwidth=80)
        self.results_tree.column("content", width=300, minwidth=200)
        self.results_tree.column("details", width=200, minwidth=150)
        
        # Results scrollbar
        results_scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", 
                                         command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_tree.pack(side="left", fill="both", expand=True)
        results_scrollbar.pack(side="right", fill="y")
        
        # Status label
        self.status_label = ttk.Label(self.container, text="Tapez pour rechercher dans tous les modules", 
                                     font=('Arial', 9), foreground='gray')
        self.status_label.pack(pady=(5, 0))
        
        # Bind events
        self.search_var.trace('w', self._on_search_change)
        self.search_entry.bind('<Return>', lambda e: self._perform_search())
        self.results_tree.bind('<Double-Button-1>', self._on_result_select)
        
        # Set placeholder behavior
        self._set_placeholder()
        
    def _set_placeholder(self):
        """Set placeholder text behavior."""
        placeholder_text = "Rechercher clients, fournisseurs, factures, achats..."
        
        def on_entry_click(event):
            if self.search_var.get() == placeholder_text:
                self.search_var.set("")
                self.search_entry.config(foreground='black')
        
        def on_focusout(event):
            if self.search_var.get() == "":
                self.search_var.set(placeholder_text)
                self.search_entry.config(foreground='gray')
        
        # Set initial placeholder
        self.search_var.set(placeholder_text)
        self.search_entry.config(foreground='gray')
        
        # Bind placeholder events
        self.search_entry.bind('<FocusIn>', on_entry_click)
        self.search_entry.bind('<FocusOut>', on_focusout)
        
    def add_search_provider(self, category: str, search_function: Callable):
        """Add a search provider for a specific category."""
        self.search_providers[category] = search_function
        
    def _on_search_change(self, *args):
        """Handle search input change with debouncing."""
        if self.search_debounce_id is not None:
            self.search_entry.after_cancel(self.search_debounce_id)
        
        query = self.search_var.get().strip()
        
        # Skip if placeholder text
        if query in ["", "Rechercher clients, fournisseurs, factures, achats..."]:
            self._hide_results()
            return
            
        # Update status
        self.status_label.config(text="🔄 Recherche en cours...", foreground='blue')
        
        # Debounce search
        self.search_debounce_id = self.search_entry.after(500, self._perform_search)
        
    def _perform_search(self):
        """Perform the actual search across all providers."""
        query = self.search_var.get().strip()
        
        # Skip if empty or placeholder
        if not query or query == "Rechercher clients, fournisseurs, factures, achats...":
            self._hide_results()
            return
            
        # Clear previous results
        self.current_results = []
        self.results_tree.delete(*self.results_tree.get_children())
        
        # Update status
        self.status_label.config(text="🔍 Recherche en cours...", foreground='blue')
        
        # Search in background to avoid UI freeze
        def background_search():
            all_results = []
            
            for category, search_func in self.search_providers.items():
                try:
                    # Call search function with query
                    results = search_func(query)
                    if results:
                        for result in results:
                            all_results.append({
                                'category': category,
                                'result': result
                            })
                except Exception as e:
                    print(f"[SMART_SEARCH] Error in {category}: {e}")
                    
            # Update UI in main thread
            self.search_entry.after(0, lambda: self._display_results(all_results, query))
            
        # Run search in background thread
        search_thread = threading.Thread(target=background_search, daemon=True)
        search_thread.start()
        
    def _display_results(self, results: List[Dict], query: str):
        """Display search results in the UI."""
        self.current_results = results
        
        if not results:
            # No results found
            self.results_tree.insert("", "end", text="❌", values=("Aucun résultat", f"Aucun résultat pour '{query}'", ""))
            self.status_label.config(text="❌ Aucun résultat trouvé", foreground='red')
        else:
            # Group results by category
            categories = {}
            for result in results:
                category = result['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append(result['result'])
            
            # Insert category nodes
            for category, category_results in categories.items():
                # Get category icon
                category_icon = self._get_category_icon(category)
                
                # Insert category parent node
                category_node = self.results_tree.insert("", "end", text=category_icon,
                                                        values=(category, f"{len(category_results)} résultat(s)", ""))
                
                # Insert results under category
                for result in category_results:
                    content = result.get('content', str(result))
                    details = result.get('details', '')
                    result_type = result.get('type', category)
                    
                    self.results_tree.insert(category_node, "end", text="📄",
                                           values=(result_type, content, details))
            
            # Expand all categories
            for item in self.results_tree.get_children():
                self.results_tree.item(item, open=True)
                
            # Update status
            total_results = len(results)
            self.status_label.config(text=f"✅ {total_results} résultat(s) trouvé(s)", foreground='green')
        
        # Show results frame
        self._show_results()
        
    def _get_category_icon(self, category: str) -> str:
        """Get icon for category."""
        icons = {
            'clients': '👥',
            'fournisseurs': '🏢',
            'factures': '📄',
            'devis': '📋',
            'achats': '🛒',
            'ventes': '💰',
            'voitures': '🚗',
            'bank': '🏦',
            'caisse': '💵',
            'documents': '📁',
            'calendar': '📅',
            'ciment': '🏗️',
            'materials': '🧱'
        }
        return icons.get(category.lower(), '📂')
        
    def _show_results(self):
        """Show the results frame."""
        self.results_frame.pack(fill="both", expand=True, pady=(5, 0))
        
    def _hide_results(self):
        """Hide the results frame."""
        self.results_frame.pack_forget()
        self.status_label.config(text="Tapez pour rechercher dans tous les modules", foreground='gray')
        
    def _clear_search(self):
        """Clear the search and hide results."""
        self.search_var.set("")
        self.search_entry.config(foreground='black')
        self._hide_results()
        self.current_results = []
        self.search_entry.focus_set()
        
    def _on_result_select(self, event):
        """Handle double-click on search result."""
        selection = self.results_tree.selection()
        if not selection:
            return
            
        item = self.results_tree.item(selection[0])
        values = item['values']
        
        if len(values) >= 3:
            result_type = values[0]
            content = values[1]
            details = values[2]
            
            # Find the actual result data
            for result in self.current_results:
                if result['result'].get('content') == content:
                    # Execute callback if available
                    callback = result['result'].get('callback')
                    if callback:
                        callback(result['result'])
                    break

def create_default_search_providers():
    """Create default search providers for common STFOOM modules."""
    providers = {}
    
    # Clients search provider
    def search_clients(query):
        try:
            from stfoom.logicold import clients_selector as client_db
            df = client_db.load_clients()
            query_lower = query.lower()
            
            # Search in multiple fields
            mask = (
                df['raison_sociale'].str.lower().str.contains(query_lower, na=False) |
                df['code_client'].str.lower().str.contains(query_lower, na=False)
            )
            
            results = []
            for _, row in df[mask].head(20).iterrows():
                results.append({
                    'type': 'Client',
                    'content': f"{row['code_client']} - {row['raison_sociale']}",
                    'details': f"Code: {row['code_client']}",
                    'data': row.to_dict()
                })
            
            return results
        except Exception as e:
            print(f"[SEARCH] Clients search error: {e}")
            return []
    
    # Fournisseurs search provider  
    def search_fournisseurs(query):
        try:
            from stfoom.logicold import fournisseurs_selector as fournisseur_db
            df = fournisseur_db.load_fournisseurs()
            query_lower = query.lower()
            
            # Search in multiple fields
            mask = (
                df['nom_fournisseur'].str.lower().str.contains(query_lower, na=False) |
                df['code_fournisseur'].str.lower().str.contains(query_lower, na=False)
            )
            
            results = []
            for _, row in df[mask].head(20).iterrows():
                results.append({
                    'type': 'Fournisseur',
                    'content': f"{row['code_fournisseur']} - {row['nom_fournisseur']}",
                    'details': f"Code: {row['code_fournisseur']}",
                    'data': row.to_dict()
                })
            
            return results
        except Exception as e:
            print(f"[SEARCH] Fournisseurs search error: {e}")
            return []
    
    # Add more search providers as needed
    providers['clients'] = search_clients
    providers['fournisseurs'] = search_fournisseurs
    
    return providers

def create_smart_search(parent: tk.Widget, additional_providers: Dict[str, Callable] = None):
    """
    Create a smart search widget with default and additional providers.
    
    Args:
        parent: Parent widget
        additional_providers: Additional search providers to include
        
    Returns:
        SmartSearchWidget instance
    """
    # Get default providers
    providers = create_default_search_providers()
    
    # Add additional providers if provided
    if additional_providers:
        providers.update(additional_providers)
    
    # Create and return smart search widget
    return SmartSearchWidget(parent, providers)