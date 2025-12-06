"""
Document Management UI
Cloud-based file explorer with upload/download capabilities
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

# from stfoom.logicold.document_manager import document_manager  # DISABLED: migrated to service

# Import services
from app.stfoom.services.document_service import DocumentService
# from app.stfoom.core import service_registry  # TODO: Use when DocumentService is registered

class DocumentPage(ttk.Frame):
    """Main document management interface"""
    
    def __init__(self, parent, di_container=None, go_home=None):
        super().__init__(parent)
        self.go_home = go_home or (lambda: None)
        self.current_folder_id = None
        self.folder_path = []  # Breadcrumb navigation
        
        # Initialize document service through DI container
        if di_container:
            try:
                self.document_service = di_container.get('document_service')
                print("[DOCUMENT_PAGE] ✅ Using DocumentService from DI container")
            except (KeyError, AttributeError) as e:
                print(f"[DOCUMENT_PAGE] Warning: Document service not available from DI: {e}")
                self._fallback_to_direct_service()
        else:
            print("[DOCUMENT_PAGE] No DI container provided, using fallback")
            self._fallback_to_direct_service()
        
        # Initialize UI
        self.setup_ui()
        
        # Initial data load
        self.after(100, self.refresh_view)  # Delay to ensure UI is ready
        
    def _fallback_to_direct_service(self):
        """Fallback to direct DocumentService instantiation"""
        try:
            from app.stfoom.services.document_service import DocumentService
            self.document_service = DocumentService()
            print("[DOCUMENT_PAGE] ⚠️ Using fallback DocumentService")
        except ImportError as e:
            print(f"[DOCUMENT_PAGE] Error: Document service completely unavailable: {e}")
            # Create basic placeholder service
            self.document_service = self._create_mock_service()
    
    def _create_mock_service(self):
        """Create a mock document service when the real one is unavailable"""
        class MockDocumentService:
            def get_folders(self, parent_id=None):
                return []
            
            def get_documents(self, folder_id=None):
                return []
            
            def get_folder_contents(self, folder_id=None):
                return {"success": False, "folders": [], "documents": [], "error": "Service unavailable"}
            
            def upload_document(self, *args, **kwargs):
                return None
            
            def create_folder(self, *args, **kwargs):
                return None
            
            def search_documents(self, *args, **kwargs):
                return []
            
            def get_document(self, doc_id):
                return None
            
            def download_document(self, *args, **kwargs):
                return False
            
            def delete_document(self, *args, **kwargs):
                return False
        
        return MockDocumentService()
        
    def initialize_ui(self):
        """Initialize the user interface after service setup"""
        self.setup_ui()
        self.refresh_view()
    
    def setup_ui(self):
        """Setup the main UI layout"""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header section
        self.create_header(main_frame)
        
        # Toolbar section
        self.create_toolbar(main_frame)
        
        # Content area with explorer
        self.create_content_area(main_frame)
        
        # Status bar
        self.create_status_bar(main_frame)
    
    def create_header(self, parent):
        """Create header with title and navigation"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=(0, 10))
        
        # Back button
        back_btn = ttk.Button(
            header_frame, 
            text="🏠 Retour",
            command=self.go_home,
            style="Accent.TButton"
        )
        back_btn.pack(side="left")
        
        # Title
        title_label = ttk.Label(
            header_frame,
            text="📁 Gestionnaire de Documents",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(side="left", padx=(20, 0))
        
        # Navigation breadcrumb
        self.nav_frame = ttk.Frame(header_frame)
        self.nav_frame.pack(side="right", fill="x", expand=True)
        
        self.breadcrumb_label = ttk.Label(self.nav_frame, text="📍 Racine", font=("Segoe UI", 10))
        self.breadcrumb_label.pack(side="right")
    
    def create_toolbar(self, parent):
        """Create toolbar with action buttons"""
        toolbar_frame = ttk.LabelFrame(parent, text="Actions", padding=10)
        toolbar_frame.pack(fill="x", pady=(0, 10))
        
        # Upload section
        upload_frame = ttk.Frame(toolbar_frame)
        upload_frame.pack(side="left", fill="x", expand=True)
        
        ttk.Label(upload_frame, text="📤 Upload:", font=("Segoe UI", 10, "bold")).pack(side="left")
        
        upload_btn = ttk.Button(
            upload_frame,
            text="📄 Fichier",
            command=self.upload_file,
            style="Success.TButton"
        )
        upload_btn.pack(side="left", padx=(5, 0))
        
        upload_multiple_btn = ttk.Button(
            upload_frame,
            text="📄📄 Plusieurs",
            command=self.upload_multiple_files,
            style="Success.TButton"
        )
        upload_multiple_btn.pack(side="left", padx=(5, 0))
        
        # Folder section
        folder_frame = ttk.Frame(toolbar_frame)
        folder_frame.pack(side="left", fill="x", expand=True, padx=(20, 0))
        
        ttk.Label(folder_frame, text="📁 Dossier:", font=("Segoe UI", 10, "bold")).pack(side="left")
        
        new_folder_btn = ttk.Button(
            folder_frame,
            text="➕ Nouveau",
            command=self.create_new_folder,
            style="Primary.TButton"
        )
        new_folder_btn.pack(side="left", padx=(5, 0))
        
        # Search section
        search_frame = ttk.Frame(toolbar_frame)
        search_frame.pack(side="right")
        
        ttk.Label(search_frame, text="🔍 Recherche:", font=("Segoe UI", 10, "bold")).pack(side="left")
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side="left", padx=(5, 0))
        search_entry.bind("<Return>", lambda e: self.search_documents())
        
        search_btn = ttk.Button(
            search_frame,
            text="🔍",
            command=self.search_documents,
            width=3
        )
        search_btn.pack(side="left", padx=(2, 0))
    
    def create_content_area(self, parent):
        """Create main content area with file explorer"""
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill="both", expand=True)
        
        # Left panel - Folder tree
        left_frame = ttk.LabelFrame(content_frame, text="Dossiers", padding=5)
        left_frame.pack(side="left", fill="y", padx=(0, 5))
        left_frame.configure(width=250)  # Set frame width instead
        
        # Folder tree
        self.folder_tree = ttk.Treeview(left_frame)
        self.folder_tree.pack(fill="both", expand=True)
        self.folder_tree.bind("<<TreeviewSelect>>", self.on_folder_select)
        
        # Folder tree scrollbar
        folder_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.folder_tree.yview)
        self.folder_tree.configure(yscrollcommand=folder_scrollbar.set)
        
        # Right panel - File list
        right_frame = ttk.LabelFrame(content_frame, text="Contenu", padding=5)
        right_frame.pack(side="right", fill="both", expand=True)
        
        # File list with columns
        columns = ("name", "size", "type", "date", "author")
        self.file_tree = ttk.Treeview(right_frame, columns=columns, show="tree headings")
        
        # Configure columns
        self.file_tree.heading("#0", text="📄 Nom")
        self.file_tree.heading("name", text="Nom complet")
        self.file_tree.heading("size", text="Taille")
        self.file_tree.heading("type", text="Type")
        self.file_tree.heading("date", text="Date")
        self.file_tree.heading("author", text="Auteur")
        
        self.file_tree.column("#0", width=200)
        self.file_tree.column("name", width=250)
        self.file_tree.column("size", width=80)
        self.file_tree.column("type", width=100)
        self.file_tree.column("date", width=120)
        self.file_tree.column("author", width=100)
        
        self.file_tree.pack(fill="both", expand=True)
        
        # File list scrollbars
        file_v_scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.file_tree.yview)
        file_h_scrollbar = ttk.Scrollbar(right_frame, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=file_v_scrollbar.set, xscrollcommand=file_h_scrollbar.set)
        
        # Context menu for files
        self.setup_context_menu()
        
        # Double-click handlers
        self.file_tree.bind("<Double-1>", self.on_file_double_click)
        self.file_tree.bind("<Button-3>", self.show_context_menu)  # Right-click
    
    def setup_context_menu(self):
        """Setup right-click context menu"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="📥 Télécharger", command=self.download_selected_file)
        self.context_menu.add_command(label="ℹ️ Informations", command=self.show_file_info)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Supprimer", command=self.delete_selected_file)
    
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Prêt", relief="sunken")
        self.status_label.pack(side="left", fill="x", expand=True)
        
        self.file_count_label = ttk.Label(status_frame, text="0 éléments", relief="sunken")
        self.file_count_label.pack(side="right")
    
    def refresh_view(self):
        """Refresh the current view"""
        self.populate_folder_tree()
        self.populate_file_list()
        self.update_breadcrumb()
    
    def populate_folder_tree(self):
        """Populate the folder tree"""
        # Clear existing items
        for item in self.folder_tree.get_children():
            self.folder_tree.delete(item)
        
        # Add root
        root_item = self.folder_tree.insert("", "end", text="📁 Racine", values=("",), tags=("folder",))
        
        # Get folder tree from manager
        folder_tree = self.document_service.get_folders()
        
        def add_folder_to_tree(parent_item, folder_data):
            item_id = self.folder_tree.insert(
                parent_item, "end",
                text=f"{folder_data.get('icon', '📁')} {folder_data.get('folder_name', folder_data.get('name', 'Unnamed'))}",
                values=(folder_data['id'],),
                tags=("folder",)
            )
            return item_id
        
        # Add folders to tree
        for folder in folder_tree:
            add_folder_to_tree(root_item, folder)
        
        # Expand root
        self.folder_tree.item(root_item, open=True)
    
    def populate_file_list(self):
        """Populate the file list for current folder"""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Get folder contents
        contents = self.document_service.get_folder_contents(self.current_folder_id)
        
        if not contents["success"]:
            self.update_status(f"Erreur: {contents['error']}")
            return
        
        item_count = 0
        
        # Add folders first
        for folder in contents["folders"]:
            icon = folder.get("icon", "📁")
            folder_name = folder.get('folder_name', folder.get('name', 'Unnamed'))
            self.file_tree.insert(
                "", "end",
                text=f"{icon} {folder_name}",
                values=(folder_name, "Dossier", "Dossier", 
                       folder.get('created_date', '')[:10] if folder.get('created_date') else '', 
                       folder.get('created_by', '')),
                tags=("folder", folder['id'])
            )
            item_count += 1
        
        # Add documents
        for doc in contents["documents"]:
            # Format file size
            size = self.format_file_size(doc['file_size'])
            
            # Get file icon based on type
            icon = self.get_file_icon(doc.get('mime_type'))
            
            # Use correct field names from database
            filename = doc.get('filename', doc.get('name', 'Unknown'))
            original_filename = doc.get('original_filename', doc.get('original_name', filename))
            
            self.file_tree.insert(
                "", "end",
                text=f"{icon} {filename}",
                values=(original_filename, size, doc.get('mime_type', 'Inconnu'), 
                       doc.get('upload_date', '')[:10] if doc.get('upload_date') else '', 
                       doc.get('uploaded_by', '')),
                tags=("document", doc['id'])
            )
            item_count += 1
        
        self.file_count_label.config(text=f"{item_count} éléments")
        self.update_status("Prêt")
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = size_bytes
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def get_file_icon(self, mime_type: str) -> str:
        """Get appropriate icon for file type"""
        if not mime_type:
            return "📄"
        
        icon_map = {
            "image": "🖼️",
            "video": "🎥",
            "audio": "🎵",
            "text": "📝",
            "application/pdf": "📕",
            "application/msword": "📘",
            "application/vnd.ms-excel": "📗",
            "application/vnd.ms-powerpoint": "📙",
            "application/zip": "📦",
            "application/x-zip": "📦",
        }
        
        for key, icon in icon_map.items():
            if key in mime_type.lower():
                return icon
        
        return "📄"
    
    def update_breadcrumb(self):
        """Update breadcrumb navigation"""
        if not self.folder_path:
            self.breadcrumb_label.config(text="📍 Racine")
        else:
            path_text = " > ".join([f"📁 {folder['name']}" for folder in self.folder_path])
            self.breadcrumb_label.config(text=f"📍 Racine > {path_text}")
    
    def update_status(self, message: str):
        """Update status bar message"""
        self.status_label.config(text=message)
    
    def on_folder_select(self, event):
        """Handle folder selection in tree"""
        selection = self.folder_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.folder_tree.item(item, "values")
        
        if values and values[0]:
            self.current_folder_id = int(values[0])
        else:
            self.current_folder_id = None
        
        self.populate_file_list()
    
    def on_file_double_click(self, event):
        """Handle double-click on file/folder"""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.file_tree.item(item, "tags")
        
        if "folder" in tags:
            # Navigate to folder
            folder_id = int(tags[1])
            self.navigate_to_folder(folder_id)
        elif "document" in tags:
            # Download document
            document_id = int(tags[1])
            self.download_document(document_id)
    
    def navigate_to_folder(self, folder_id: int):
        """Navigate to a specific folder"""
        # Update current folder
        self.current_folder_id = folder_id
        
        # Update folder path for breadcrumb
        # TODO: Implement proper breadcrumb tracking
        
        self.populate_file_list()
    
    def upload_file(self):
        """Upload a single file"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier à télécharger",
            filetypes=[
                ("Tous les fichiers", "*.*"),
                ("Documents", "*.pdf;*.doc;*.docx;*.txt"),
                ("Images", "*.jpg;*.jpeg;*.png;*.gif;*.bmp"),
                ("Archives", "*.zip;*.rar;*.7z")
            ]
        )
        
        if file_path:
            self.upload_file_to_server(file_path)
    
    def upload_multiple_files(self):
        """Upload multiple files"""
        file_paths = filedialog.askopenfilenames(
            title="Sélectionner des fichiers à télécharger",
            filetypes=[("Tous les fichiers", "*.*")]
        )
        
        if file_paths:
            for file_path in file_paths:
                self.upload_file_to_server(file_path)
    
    def upload_file_to_server(self, file_path: str):
        """Upload a file to the server"""
        # Get upload details
        upload_dialog = FileUploadDialog(self, file_path)
        if upload_dialog.result:
            details = upload_dialog.result
            
            self.update_status(f"Téléchargement de {os.path.basename(file_path)}...")
            
            # Get current user
            # from stfoom.logic.access_control import auth_manager  # DISABLED: migrated to service
            uploaded_by = "System"  # TODO: Get from UserService
            
            # Upload file with correct parameters
            try:
                result = self.document_service.upload_document(
                    file_path=file_path,
                    original_filename=os.path.basename(file_path),  # Add missing parameter
                    folder_id=self.current_folder_id,
                    description=details.get("description", ""),
                    tags=details.get("tags", ""),
                    uploaded_by=uploaded_by
                )
                
                # The service returns an ID, so we need to check if it's successful
                if result and isinstance(result, int):
                    self.update_status(f"✅ Fichier téléchargé avec succès (ID: {result})")
                    self.refresh_view()
                else:
                    messagebox.showerror("Erreur", "Erreur lors du téléchargement: résultat inattendu")
                    self.update_status("Erreur de téléchargement")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du téléchargement: {str(e)}")
                self.update_status("Erreur de téléchargement")
    
    def download_document(self, document_id: int):
        """Download a document to Desktop"""
        # Get document info
        doc_info = self.document_service.get_document(document_id)
        if not doc_info:
            messagebox.showerror("Erreur", "Document non trouvé")
            return
        
        # Get correct field names from database
        original_filename = doc_info.get('original_filename', doc_info.get('original_name', 'document'))
        filename = doc_info.get('filename', doc_info.get('name', original_filename))
        
        # Default to Desktop
        desktop_path = Path.home() / "Desktop"
        
        # Choose download location (defaults to Desktop)
        download_path = filedialog.asksaveasfilename(
            title="Enregistrer sur Bureau",
            initialdir=str(desktop_path),
            initialfile=original_filename,
            defaultextension=Path(original_filename).suffix
        )
        
        if download_path:
            self.update_status(f"Téléchargement de {filename}...")
            
            # Get current user
            # from stfoom.logic.access_control import auth_manager  # DISABLED: migrated to service
            downloaded_by = "System"  # TODO: Get from UserService
            
            # Download file - service returns boolean, not dict
            try:
                success = self.document_service.download_document(
                    document_id=document_id,
                    download_path=download_path,
                    user=downloaded_by  # Use 'user' parameter not 'downloaded_by'
                )
                
                if success:
                    self.update_status(f"✅ Fichier téléchargé avec succès")
                    messagebox.showinfo("Succès", f"Fichier téléchargé: {download_path}")
                else:
                    messagebox.showerror("Erreur", "Erreur lors du téléchargement: fichier non trouvé")
                    self.update_status("Erreur de téléchargement")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du téléchargement: {str(e)}")
                self.update_status("Erreur de téléchargement")
    
    def download_selected_file(self):
        """Download currently selected file"""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.file_tree.item(item, "tags")
        
        if "document" in tags:
            document_id = int(tags[1])
            self.download_document(document_id)
    
    def create_new_folder(self):
        """Create a new folder"""
        dialog = FolderCreateDialog(self)
        if dialog.result:
            details = dialog.result
            
            # Get current user
            # from stfoom.logic.access_control import auth_manager  # DISABLED: migrated to service
            created_by = "System"  # TODO: Get from UserService
            
            result = self.document_service.create_folder(
                folder_name=details["name"],
                parent_id=self.current_folder_id,
                created_by=created_by,
                description=details.get("description", ""),
                color=details.get("color", "#4CAF50"),
                icon=details.get("icon", "📁")
            )
            
            if result["success"]:
                self.update_status(f"✅ {result['message']}")
                self.refresh_view()
            else:
                messagebox.showerror("Erreur", f"Erreur lors de la création: {result['error']}")
    
    def search_documents(self):
        """Search for documents"""
        query = self.search_var.get().strip()
        if not query:
            self.refresh_view()
            return
        
        self.update_status(f"Recherche de '{query}'...")
        
        results = self.document_service.search_documents(query)
        
        # Clear file list and show results
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        for doc in results:
            icon = self.get_file_icon(doc['mime_type'])
            size = self.format_file_size(doc['file_size'])
            
            self.file_tree.insert(
                "", "end",
                text=f"{icon} {doc['name']}",
                values=(doc['original_name'], size, doc['mime_type'] or "Inconnu",
                       doc['upload_date'][:10], doc['uploaded_by']),
                tags=("document", doc['id'])
            )
        
        self.file_count_label.config(text=f"{len(results)} résultats")
        self.update_status(f"Recherche terminée: {len(results)} résultats")
    
    def show_context_menu(self, event):
        """Show context menu on right-click"""
        # Select item under cursor
        item = self.file_tree.identify_row(event.y)
        if item:
            self.file_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def show_file_info(self):
        """Show detailed file information"""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.file_tree.item(item, "tags")
        
        if "document" in tags:
            document_id = int(tags[1])
            doc_info = self.document_service.get_document(document_id)
            if doc_info:
                FileInfoDialog(self, doc_info)
    
    def delete_selected_file(self):
        """Delete the selected file"""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.file_tree.item(item, "tags")
        
        if "document" in tags:
            document_id = int(tags[1])
            doc_info = self.document_service.get_document(document_id)
            
            if doc_info and messagebox.askyesno(
                "Confirmer suppression",
                f"Êtes-vous sûr de vouloir supprimer '{doc_info['name']}'?"
            ):
                # Get current user
                # from stfoom.logic.access_control import auth_manager  # DISABLED: migrated to service
                deleted_by = "System"  # TODO: Get from UserService
                
                result = self.document_service.delete_document(document_id, deleted_by)
                
                if result["success"]:
                    self.update_status(f"✅ {result['message']}")
                    self.refresh_view()
                else:
                    messagebox.showerror("Erreur", f"Erreur lors de la suppression: {result['error']}")


class FileUploadDialog:
    """Dialog for file upload details"""
    
    def __init__(self, parent, file_path: str):
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Détails du téléchargement")
        self.window.geometry("400x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center the window
        self.window.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_ui(file_path)
        
        # Wait for dialog to close
        self.window.wait_window()
    
    def setup_ui(self, file_path: str):
        """Setup dialog UI"""
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # File info
        info_frame = ttk.LabelFrame(main_frame, text="Informations du fichier", padding=10)
        info_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(info_frame, text=f"Fichier: {os.path.basename(file_path)}", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(info_frame, text=f"Chemin: {file_path}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Taille: {self.format_file_size(os.path.getsize(file_path))}").pack(anchor="w")
        
        # Description
        desc_frame = ttk.LabelFrame(main_frame, text="Description (optionnel)", padding=10)
        desc_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.description_text = tk.Text(desc_frame, height=4, wrap="word")
        self.description_text.pack(fill="both", expand=True)
        
        # Tags
        tags_frame = ttk.LabelFrame(main_frame, text="Tags (séparés par des virgules)", padding=10)
        tags_frame.pack(fill="x", pady=(0, 10))
        
        self.tags_var = tk.StringVar()
        tags_entry = ttk.Entry(tags_frame, textvariable=self.tags_var)
        tags_entry.pack(fill="x")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="Annuler", command=self.cancel).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Télécharger", command=self.upload, style="Accent.TButton").pack(side="right")
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = size_bytes
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def upload(self):
        """Process upload"""
        self.result = {
            "description": self.description_text.get("1.0", "end-1c"),
            "tags": self.tags_var.get()
        }
        self.window.destroy()
    
    def cancel(self):
        """Cancel upload"""
        self.result = None
        self.window.destroy()


class FolderCreateDialog:
    """Dialog for creating new folders"""
    
    def __init__(self, parent):
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Nouveau dossier")
        self.window.geometry("350x250")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center the window
        self.window.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        self.setup_ui()
        
        # Wait for dialog to close
        self.window.wait_window()
    
    def setup_ui(self):
        """Setup dialog UI"""
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Name
        name_frame = ttk.LabelFrame(main_frame, text="Nom du dossier", padding=10)
        name_frame.pack(fill="x", pady=(0, 10))
        
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var, font=("Segoe UI", 11))
        name_entry.pack(fill="x")
        name_entry.focus()
        
        # Icon selection
        icon_frame = ttk.LabelFrame(main_frame, text="Icône", padding=10)
        icon_frame.pack(fill="x", pady=(0, 10))
        
        self.icon_var = tk.StringVar(value="📁")
        icon_options = ["📁", "📂", "🗂️", "📊", "📋", "🔧", "📸", "🎵", "🎥", "📦"]
        
        for i, icon in enumerate(icon_options):
            row, col = divmod(i, 5)
            ttk.Radiobutton(icon_frame, text=icon, variable=self.icon_var, value=icon).grid(row=row, column=col, padx=5, pady=2)
        
        # Color selection
        color_frame = ttk.LabelFrame(main_frame, text="Couleur", padding=10)
        color_frame.pack(fill="x", pady=(0, 10))
        
        self.color_var = tk.StringVar(value="#4CAF50")
        colors = [("#4CAF50", "Vert"), ("#2196F3", "Bleu"), ("#FF9800", "Orange"), 
                 ("#9C27B0", "Violet"), ("#F44336", "Rouge"), ("#607D8B", "Gris")]
        
        for i, (color_code, color_name) in enumerate(colors):
            row, col = divmod(i, 3)
            ttk.Radiobutton(color_frame, text=color_name, variable=self.color_var, value=color_code).grid(row=row, column=col, padx=5, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(button_frame, text="Annuler", command=self.cancel).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Créer", command=self.create, style="Accent.TButton").pack(side="right")
        
        # Bind Enter key
        self.window.bind("<Return>", lambda e: self.create())
    
    def create(self):
        """Create folder"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Erreur", "Le nom du dossier est requis")
            return
        
        self.result = {
            "name": name,
            "icon": self.icon_var.get(),
            "color": self.color_var.get()
        }
        self.window.destroy()
    
    def cancel(self):
        """Cancel creation"""
        self.result = None
        self.window.destroy()


class FileInfoDialog:
    """Dialog showing detailed file information"""
    
    def __init__(self, parent, doc_info: Dict):
        self.window = tk.Toplevel(parent)
        self.window.title("Informations du fichier")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center the window
        self.window.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_ui(doc_info)
    
    def setup_ui(self, doc_info: Dict):
        """Setup dialog UI"""
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # File icon and name
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 15))
        
        icon = self.get_file_icon(doc_info.get('mime_type', ''))
        ttk.Label(header_frame, text=icon, font=("Segoe UI", 24)).pack(side="left")
        ttk.Label(header_frame, text=doc_info['name'], font=("Segoe UI", 16, "bold")).pack(side="left", padx=(10, 0))
        
        # Information notebook
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=(0, 15))
        
        # General tab
        general_frame = ttk.Frame(notebook, padding=15)
        notebook.add(general_frame, text="Général")
        
        info_items = [
            ("Nom original:", doc_info['original_name']),
            ("Taille:", self.format_file_size(doc_info['file_size'])),
            ("Type MIME:", doc_info.get('mime_type', 'Inconnu')),
            ("Téléchargé par:", doc_info['uploaded_by']),
            ("Date d'upload:", doc_info['upload_date']),
            ("Dossier:", doc_info.get('folder_name', 'Racine')),
            ("Téléchargements:", str(doc_info.get('download_count', 0))),
            ("Dernier accès:", doc_info.get('last_accessed', 'Jamais'))
        ]
        
        for i, (label, value) in enumerate(info_items):
            ttk.Label(general_frame, text=label, font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="w", pady=2)
            ttk.Label(general_frame, text=value).grid(row=i, column=1, sticky="w", padx=(10, 0), pady=2)
        
        # Description tab
        if doc_info.get('description'):
            desc_frame = ttk.Frame(notebook, padding=15)
            notebook.add(desc_frame, text="Description")
            
            desc_text = tk.Text(desc_frame, wrap="word", state="disabled")
            desc_text.pack(fill="both", expand=True)
            desc_text.config(state="normal")
            desc_text.insert("1.0", doc_info['description'])
            desc_text.config(state="disabled")
        
        # Tags tab
        if doc_info.get('tags'):
            tags_frame = ttk.Frame(notebook, padding=15)
            notebook.add(tags_frame, text="Tags")
            
            tags_label = ttk.Label(tags_frame, text=doc_info['tags'], wraplength=400)
            tags_label.pack(anchor="w")
        
        # Close button
        ttk.Button(main_frame, text="Fermer", command=self.window.destroy).pack()
    
    def get_file_icon(self, mime_type: str) -> str:
        """Get file icon based on MIME type"""
        if not mime_type:
            return "📄"
        
        icon_map = {
            "image": "🖼️",
            "video": "🎥", 
            "audio": "🎵",
            "text": "📝",
            "application/pdf": "📕",
            "application/msword": "📘",
            "application/vnd.ms-excel": "📗",
            "application/vnd.ms-powerpoint": "📙",
            "application/zip": "📦",
        }
        
        for key, icon in icon_map.items():
            if key in mime_type.lower():
                return icon
        
        return "📄"
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = size_bytes
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
