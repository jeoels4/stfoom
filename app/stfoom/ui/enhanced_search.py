"""
Enhanced Search System for STFOOM
================================
This module provides a comprehensive search system with:
- Page-specific search within individual modules
- Global search across all modules with permission awareness
- Modern UI with click navigation to results
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Callable, Any, Optional, Union
import threading
import time
from datetime import datetime
from abc import ABC, abstractmethod

class BaseSearchComponent(ABC):
    """Base class for search components with consistent UI and behavior."""
    
    def __init__(self, parent: tk.Widget, title: str = "Recherche", placeholder: str = "Rechercher..."):
        self.parent = parent
        self.title = title
        self.placeholder = placeholder
        self.search_debounce_id = None
        self.current_results = []
        self.results_visible = False
        
        # Create UI
        self._create_search_ui()
        
    def _create_search_ui(self):
        """Create the search UI components with modern styling."""
        # Main search container
        self.search_container = ttk.Frame(self.parent)
        self.search_container.pack(fill="x", padx=10, pady=5)
        
        # Search header with icon and title
        header_frame = ttk.Frame(self.search_container)
        header_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(header_frame, text="🔍", font=('Segoe UI', 14)).pack(side="left", padx=(0, 5))
        ttk.Label(header_frame, text=self.title, font=('Segoe UI', 11, 'bold')).pack(side="left")
        
        # Search input frame
        input_frame = ttk.Frame(self.search_container)
        input_frame.pack(fill="x", pady=(0, 5))
        
        # Search entry with modern styling
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            input_frame, 
            textvariable=self.search_var, 
            font=('Segoe UI', 10),
            width=50
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Search button
        self.search_btn = ttk.Button(
            input_frame, 
            text="Rechercher", 
            command=self._perform_search,
            width=12
        )
        self.search_btn.pack(side="right", padx=(5, 0))
        
        # Clear button
        self.clear_btn = ttk.Button(
            input_frame, 
            text="✕", 
            width=3,
            command=self._clear_search
        )
        self.clear_btn.pack(side="right")
        
        # Results frame (initially hidden)
        self.results_frame = ttk.LabelFrame(
            self.search_container, 
            text="Résultats de recherche", 
            padding=10
        )
        
        # Results treeview
        self._create_results_tree()
        
        # Status label
        self.status_label = ttk.Label(
            self.search_container, 
            text=f"Tapez pour rechercher...", 
            font=('Segoe UI', 9), 
            foreground='gray'
        )
        self.status_label.pack(pady=(5, 0))
        
        # Bind events
        self._bind_search_events()
        self._set_placeholder_behavior()
        
    def _create_results_tree(self):
        """Create the results treeview with columns."""
        # Create treeview with columns
        columns = self.get_result_columns()
        self.results_tree = ttk.Treeview(
            self.results_frame, 
            columns=columns,
            show="tree headings", 
            height=8
        )
        
        # Configure columns
        self.results_tree.heading("#0", text="🔍")
        self.results_tree.column("#0", width=30, minwidth=30)
        
        for col in columns:
            self.results_tree.heading(col, text=col.title())
            self.results_tree.column(col, width=150, minwidth=100)
        
        # Scrollbar for results
        scrollbar = ttk.Scrollbar(
            self.results_frame, 
            orient="vertical", 
            command=self.results_tree.yview
        )
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.results_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def _bind_search_events(self):
        """Bind search-related events."""
        # Real-time search on typing
        self.search_var.trace('w', self._on_search_change)
        
        # Search on Enter key
        self.search_entry.bind('<Return>', lambda e: self._perform_search())
        
        # Double-click to select result
        self.results_tree.bind('<Double-Button-1>', self._on_result_double_click)
        
        # Single click to preview result (optional)
        self.results_tree.bind('<Button-1>', self._on_result_single_click)
        
    def _set_placeholder_behavior(self):
        """Set placeholder text behavior for search entry."""
        def on_focus_in(event):
            if self.search_var.get() == self.placeholder:
                self.search_var.set("")
                self.search_entry.config(foreground='black')
        
        def on_focus_out(event):
            if self.search_var.get().strip() == "":
                self.search_var.set(self.placeholder)
                self.search_entry.config(foreground='gray')
        
        # Set initial placeholder
        self.search_var.set(self.placeholder)
        self.search_entry.config(foreground='gray')
        
        # Bind focus events
        self.search_entry.bind('<FocusIn>', on_focus_in)
        self.search_entry.bind('<FocusOut>', on_focus_out)
        
    def _on_search_change(self, *args):
        """Handle search input change with debouncing."""
        # Cancel previous debounced search
        if self.search_debounce_id is not None:
            self.search_entry.after_cancel(self.search_debounce_id)
        
        query = self.search_var.get().strip()
        
        # Skip if empty or placeholder
        if not query or query == self.placeholder:
            self._hide_results()
            return
        
        # Update status
        self._update_status("🔄 Recherche en cours...", 'blue')
        
        # Debounce search
        self.search_debounce_id = self.search_entry.after(500, self._perform_search)
        
    def _perform_search(self):
        """Perform the actual search."""
        query = self.search_var.get().strip()
        
        # Skip if empty or placeholder
        if not query or query == self.placeholder:
            self._hide_results()
            return
        
        # Update status
        self._update_status("🔍 Recherche en cours...", 'blue')
        
        # Perform search in background
        def background_search():
            try:
                results = self.perform_search_query(query)
                # Update UI in main thread
                self.search_entry.after(0, lambda: self._display_results(results, query))
            except Exception as e:
                error_msg = f"Erreur de recherche: {str(e)}"
                self.search_entry.after(0, lambda: self._update_status(f"❌ {error_msg}", 'red'))
                print(f"[SEARCH] Error: {e}")
        
        # Run search in background thread
        search_thread = threading.Thread(target=background_search, daemon=True)
        search_thread.start()
        
    def _display_results(self, results: List[Dict], query: str):
        """Display search results in the UI."""
        self.current_results = results
        
        # Clear previous results
        self.results_tree.delete(*self.results_tree.get_children())
        
        if not results:
            # No results found
            self.results_tree.insert(
                "", "end", 
                text="❌", 
                values=self._format_no_results(query)
            )
            self._update_status("❌ Aucun résultat trouvé", 'red')
        else:
            # Display results
            for i, result in enumerate(results[:100]):  # Limit to 100 results
                try:
                    formatted_result = self._format_result(result, i)
                    self.results_tree.insert(
                        "", "end",
                        text=formatted_result.get('icon', '📄'),
                        values=formatted_result.get('values', []),
                        tags=(f"result_{i}",)
                    )
                except Exception as e:
                    print(f"[SEARCH] Error formatting result {i}: {e}")
            
            # Update status
            count = len(results)
            self._update_status(f"✅ {count} résultat(s) trouvé(s)", 'green')
        
        # Show results
        self._show_results()
        
    def _show_results(self):
        """Show the results frame."""
        if not self.results_visible:
            self.results_frame.pack(fill="both", expand=True, pady=(5, 0))
            self.results_visible = True
        
    def _hide_results(self):
        """Hide the results frame."""
        if self.results_visible:
            self.results_frame.pack_forget()
            self.results_visible = False
        self._update_status("Tapez pour rechercher...", 'gray')
        
    def _clear_search(self):
        """Clear the search and hide results."""
        self.search_var.set("")
        self.search_entry.config(foreground='black')
        self._hide_results()
        self.current_results = []
        self.search_entry.focus_set()
        
    def _update_status(self, message: str, color: str = 'black'):
        """Update the status label."""
        self.status_label.config(text=message, foreground=color)
        
    def _on_result_single_click(self, event):
        """Handle single click on search result."""
        selection = self.results_tree.selection()
        if selection:
            item_id = selection[0]
            result_data = self._get_result_data(item_id)
            if result_data:
                self.on_result_preview(result_data)
                
    def _on_result_double_click(self, event):
        """Handle double-click on search result."""
        selection = self.results_tree.selection()
        if selection:
            item_id = selection[0]
            result_data = self._get_result_data(item_id)
            if result_data:
                self.on_result_select(result_data)
                
    def _get_result_data(self, item_id: str) -> Optional[Dict]:
        """Get result data from tree item."""
        try:
            # Extract result index from tags
            tags = self.results_tree.item(item_id, 'tags')
            for tag in tags:
                if tag.startswith('result_'):
                    index = int(tag.split('_')[1])
                    if 0 <= index < len(self.current_results):
                        return self.current_results[index]
        except (ValueError, IndexError):
            pass
        return None
    
    # Abstract methods to be implemented by subclasses
    @abstractmethod
    def get_result_columns(self) -> List[str]:
        """Return list of column names for results display."""
        pass
    
    @abstractmethod
    def perform_search_query(self, query: str) -> List[Dict]:
        """Perform the actual search and return results."""
        pass
    
    @abstractmethod
    def _format_result(self, result: Dict, index: int) -> Dict:
        """Format a result for display in the treeview."""
        pass
    
    @abstractmethod
    def _format_no_results(self, query: str) -> List[str]:
        """Format the no results message."""
        pass
    
    # Optional methods for subclasses to override
    def on_result_preview(self, result: Dict):
        """Called when user single-clicks a result (optional)."""
        pass
    
    def on_result_select(self, result: Dict):
        """Called when user double-clicks a result."""
        pass


class PageSpecificSearch(BaseSearchComponent):
    """Page-specific search component for individual modules."""
    
    def __init__(self, parent: tk.Widget, module_name: str, search_function: Callable):
        self.module_name = module_name
        self.search_function = search_function
        
        title = f"Recherche {module_name}"
        placeholder = f"Rechercher dans {module_name.lower()}..."
        
        super().__init__(parent, title, placeholder)
        
    def get_result_columns(self) -> List[str]:
        """Return columns for page-specific results."""
        return ["type", "contenu", "détails"]
    
    def perform_search_query(self, query: str) -> List[Dict]:
        """Perform search using the provided search function."""
        return self.search_function(query)
    
    def _format_result(self, result: Dict, index: int) -> Dict:
        """Format result for page-specific display."""
        return {
            'icon': result.get('icon', '📄'),
            'values': [
                result.get('type', 'Item'),
                result.get('content', 'No content'),
                result.get('details', 'No details')
            ]
        }
    
    def _format_no_results(self, query: str) -> List[str]:
        """Format no results message for page-specific search."""
        return ["Aucun résultat", f"Aucun élément trouvé dans {self.module_name} pour '{query}'", ""]


class GlobalSearch(BaseSearchComponent):
    """Global search component that searches across all modules."""
    
    def __init__(self, parent: tk.Widget, search_providers: Dict[str, Callable] = None):
        self.search_providers = search_providers or {}
        self.permission_service = None
        self.current_user = None
        
        # Initialize permission checking
        self._init_permissions()
        
        super().__init__(parent, "Recherche Globale", "Rechercher dans tous les modules...")
        
    def _init_permissions(self):
        """Initialize permission checking."""
        try:
            from app.stfoom.logic.basic_permission_service import BasicPermissionService
            self.permission_service = BasicPermissionService()
            
            # Set default user info (will be set from main app context)
            self.current_user = {'rank': 'admin'}  # Default for now
        except Exception as e:
            print(f"[GLOBAL_SEARCH] Permission init error: {e}")
    
    def add_search_provider(self, module_name: str, search_function: Callable, permission: str = None):
        """Add a search provider for a module."""
        self.search_providers[module_name] = {
            'function': search_function,
            'permission': permission
        }
    
    def get_result_columns(self) -> List[str]:
        """Return columns for global search results."""
        return ["module", "type", "contenu", "détails"]
    
    def perform_search_query(self, query: str) -> List[Dict]:
        """Perform search across all permitted modules."""
        all_results = []
        
        for module_name, provider_info in self.search_providers.items():
            # Check permissions
            if not self._can_access_module(module_name, provider_info.get('permission')):
                continue
                
            try:
                # Perform search in module
                results = provider_info['function'](query)
                
                # Add module info to results
                for result in results:
                    result['module'] = module_name
                    all_results.append(result)
                    
            except Exception as e:
                print(f"[GLOBAL_SEARCH] Error searching {module_name}: {e}")
        
        # Sort results by relevance (could be enhanced)
        return sorted(all_results, key=lambda x: x.get('relevance', 0), reverse=True)
    
    def _can_access_module(self, module_name: str, permission: str = None) -> bool:
        """Check if current user can access a module."""
        if not self.permission_service or not self.current_user:
            # Fallback to allowing access
            return True
        
        if not permission:
            # No specific permission required
            return True
        
        try:
            user_rank = self.current_user.get('rank', 'viewer')
            return self.permission_service.user_has_permission(user_rank, permission)
        except Exception as e:
            print(f"[GLOBAL_SEARCH] Permission check error: {e}")
            return False
    
    def _format_result(self, result: Dict, index: int) -> Dict:
        """Format result for global search display."""
        return {
            'icon': result.get('icon', '📄'),
            'values': [
                result.get('module', 'Unknown'),
                result.get('type', 'Item'),
                result.get('content', 'No content'),
                result.get('details', 'No details')
            ]
        }
    
    def _format_no_results(self, query: str) -> List[str]:
        """Format no results message for global search."""
        return ["Aucun résultat", f"Aucun résultat trouvé pour '{query}'", "", ""]
    
    def on_result_select(self, result: Dict):
        """Handle navigation when user selects a global search result."""
        try:
            # Get navigation callback from result
            callback = result.get('navigate_callback')
            if callback:
                callback(result)
            else:
                # Default navigation behavior
                self._default_navigate(result)
        except Exception as e:
            print(f"[GLOBAL_SEARCH] Navigation error: {e}")
            messagebox.showerror("Erreur", f"Impossible d'accéder à l'élément: {e}")
    
    def _default_navigate(self, result: Dict):
        """Default navigation behavior for search results."""
        module = result.get('module')
        item_type = result.get('type')
        
        # This would be implemented to navigate to the appropriate module
        # For now, show a message
        messagebox.showinfo(
            "Navigation",
            f"Navigation vers:\nModule: {module}\nType: {item_type}\nContenu: {result.get('content', 'N/A')}"
        )


def create_page_search(parent: tk.Widget, module_name: str, search_function: Callable):
    """
    Create a page-specific search widget.
    
    Args:
        parent: Parent widget
        module_name: Name of the module (e.g., "Ventes", "Achats")
        search_function: Function to perform the search
    
    Returns:
        PageSpecificSearch instance
    """
    return PageSpecificSearch(parent, module_name, search_function)


def create_global_search(parent: tk.Widget, search_providers: Dict[str, Dict] = None):
    """
    Create a global search widget.
    
    Args:
        parent: Parent widget
        search_providers: Dictionary of search providers with permissions
    
    Returns:
        GlobalSearch instance
    """
    return GlobalSearch(parent, search_providers)