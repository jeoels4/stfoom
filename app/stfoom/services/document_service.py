"""
Document Service - Business Logic Layer
====================================
Handles all document management operations with clean service architecture.
Migrated from app.stfoom.logic.document_manager
"""

from __future__ import annotations
import os
import sqlite3
import shutil
import hashlib
import mimetypes
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
from app.stfoom.data.base_repository import BaseRepository
from app.stfoom.utils.logging_decorators import log_method_call, log_database_method, log_business_method

class DocumentRepository(BaseRepository):
    """Data access layer for document operations"""
    
    def __init__(self):
        super().__init__("documents")
    
    def get_entity_name(self) -> str:
        """Return the name of the entity this repository manages."""
        return "documents"
    
    def init_tables(self) -> None:
        """Initialize document management tables"""
        with self.get_connection() as conn:
            # Documents table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    mime_type TEXT,
                    folder_id INTEGER,
                    uploaded_by TEXT,
                    upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    tags TEXT,
                    is_public BOOLEAN DEFAULT 0,
                    FOREIGN KEY (folder_id) REFERENCES document_folders (id)
                )
            """)
            
            # Document folders table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_name TEXT NOT NULL,
                    parent_folder_id INTEGER,
                    folder_path TEXT NOT NULL,
                    created_by TEXT,
                    created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    FOREIGN KEY (parent_folder_id) REFERENCES document_folders (id)
                )
            """)
            
            # Document access log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    accessed_by TEXT,
                    access_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    access_type TEXT, -- 'view', 'download', 'edit', 'delete'
                    ip_address TEXT,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
            """)
            
            conn.commit()

    def add_document(self, doc_data: Dict[str, Any]) -> int:
        """Add a new document record"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO documents 
                (filename, original_filename, file_path, file_size, file_hash, 
                 mime_type, folder_id, uploaded_by, description, tags, is_public)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_data['filename'],
                doc_data['original_filename'],
                doc_data['file_path'],
                doc_data['file_size'],
                doc_data['file_hash'],
                doc_data.get('mime_type'),
                doc_data.get('folder_id'),
                doc_data.get('uploaded_by'),
                doc_data.get('description'),
                doc_data.get('tags'),
                doc_data.get('is_public', 0)
            ))
            conn.commit()
            return cursor.lastrowid

    def get_documents_by_folder(self, folder_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all documents in a folder"""
        with self.get_connection() as conn:
            if folder_id:
                cursor = conn.execute("""
                    SELECT * FROM documents WHERE folder_id = ? 
                    ORDER BY upload_date DESC
                """, (folder_id,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM documents WHERE folder_id IS NULL 
                    ORDER BY upload_date DESC
                """)
            
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_document_by_id(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM documents WHERE id = ?
            """, (document_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                return dict(zip(columns, row))
            return None

    def delete_document(self, document_id: int) -> bool:
        """Delete a document record"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            conn.commit()
            return conn.changes > 0

    def add_folder(self, folder_data: Dict[str, Any]) -> int:
        """Add a new folder"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO document_folders 
                (folder_name, parent_folder_id, created_by, description)
                VALUES (?, ?, ?, ?)
            """, (
                folder_data['folder_name'],
                folder_data.get('parent_id'),
                folder_data.get('created_by'),
                folder_data.get('description')
            ))
            conn.commit()
            return cursor.lastrowid

    def get_folders(self, parent_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get folders by parent"""
        with self.get_connection() as conn:
            if parent_id:
                cursor = conn.execute("""
                    SELECT * FROM document_folders WHERE parent_folder_id = ?
                    ORDER BY folder_name
                """, (parent_id,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM document_folders WHERE parent_folder_id IS NULL
                    ORDER BY folder_name
                """)
            
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def log_access(self, document_id: int, user: str, access_type: str, ip: Optional[str] = None):
        """Log document access"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO document_access_log 
                (document_id, accessed_by, access_type, ip_address)
                VALUES (?, ?, ?, ?)
            """, (document_id, user, access_type, ip))
            conn.commit()

class DocumentService:
    """Service layer for document management"""
    
    def __init__(self, document_repository: Optional[DocumentRepository] = None):
        self.document_repository = document_repository or DocumentRepository()
        self.server_documents_path = self._get_server_documents_path()
        self.local_cache_path = self._get_local_cache_path()
        
        # Initialize tables and directories
        self.document_repository.init_tables()
        self._ensure_directories()

    def _get_server_documents_path(self) -> str:
        """Get the server path for document storage"""
        # Always use data/documents as the central storage location
        # This ensures all PCs access the same location
        try:
            from app.core.path_manager import path_manager
            data_dir = path_manager.get_data_dir()
            documents_path = os.path.join(data_dir, "documents")
        except:
            # Fallback if PathManager not available
            base_dir = Path(__file__).parent.parent.parent.parent
            documents_path = os.path.join(base_dir, "data", "documents")
        
        return documents_path

    def _get_local_cache_path(self) -> str:
        """Get local cache path for temporary files"""
        return os.path.join(os.getcwd(), "data", "document_cache")

    def _ensure_directories(self):
        """Ensure document directories exist"""
        for path in [self.server_documents_path, self.local_cache_path]:
            os.makedirs(path, exist_ok=True)

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    @log_business_method("documents", "file_upload")
    def upload_document(self, file_path: str, original_filename: str,
                       folder_id: Optional[int] = None, 
                       uploaded_by: Optional[str] = None,
                       description: Optional[str] = None,
                       tags: Optional[str] = None,
                       is_public: bool = False) -> int:
        """Upload a document to the server (data/documents)"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Generate unique filename
        file_ext = os.path.splitext(original_filename)[1]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{original_filename}"
        
        # Determine subfolder if folder_id provided
        subfolder_name = ""
        if folder_id:
            folders = self.document_repository.get_folders()
            for folder in folders:
                if folder['id'] == folder_id:
                    subfolder_name = folder.get('folder_name', '')
                    break
        
        # Server file path - directly in server_documents_path, not nested
        if subfolder_name:
            server_file_path = os.path.join(self.server_documents_path, subfolder_name, unique_filename)
        else:
            server_file_path = os.path.join(self.server_documents_path, unique_filename)
        
        os.makedirs(os.path.dirname(server_file_path), exist_ok=True)
        
        # Copy file to server
        shutil.copy2(file_path, server_file_path)
        
        # Get file info
        file_size = os.path.getsize(server_file_path)
        file_hash = self._calculate_file_hash(server_file_path)
        mime_type = mimetypes.guess_type(original_filename)[0]
        
        # Store in database
        doc_data = {
            'filename': unique_filename,
            'original_filename': original_filename,
            'file_path': server_file_path,
            'file_size': file_size,
            'file_hash': file_hash,
            'mime_type': mime_type,
            'folder_id': folder_id,
            'uploaded_by': uploaded_by,
            'description': description,
            'tags': tags,
            'is_public': is_public
        }
        
        return self.document_repository.add_document(doc_data)

    def get_documents(self, folder_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get documents in a folder"""
        return self.document_repository.get_documents_by_folder(folder_id)

    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        return self.document_repository.get_document_by_id(document_id)

    @log_business_method("documents", "file_download")
    def download_document(self, document_id: int, download_path: str,
                         user: Optional[str] = None) -> bool:
        """Download document to local path"""
        doc = self.get_document(document_id)
        if not doc:
            return False
        
        # Check if server file exists
        if not os.path.exists(doc['file_path']):
            return False
        
        # Copy to download location
        shutil.copy2(doc['file_path'], download_path)
        
        # Log access
        if user:
            self.document_repository.log_access(document_id, user, 'download')
        
        return True

    @log_business_method("documents", "document_deletion")
    def delete_document(self, document_id: int, user: Optional[str] = None) -> bool:
        """Delete a document"""
        doc = self.get_document(document_id)
        if not doc:
            return False
        
        # Delete physical file
        try:
            if os.path.exists(doc['file_path']):
                os.remove(doc['file_path'])
        except OSError:
            pass  # Continue even if file deletion fails
        
        # Delete from database
        success = self.document_repository.delete_document(document_id)
        
        # Log access
        if user and success:
            self.document_repository.log_access(document_id, user, 'delete')
        
        return success

    @log_business_method("documents", "folder_creation")
    def create_folder(self, folder_name: str, parent_id: Optional[int] = None,
                     created_by: Optional[str] = None,
                     description: Optional[str] = None,
                     color: Optional[str] = None,
                     icon: Optional[str] = None) -> Dict[str, Any]:
        """Create a new folder in data/documents"""
        # Build folder path
        if parent_id:
            # Get parent folder to build nested path
            parent_folders = self.document_repository.get_folders()
            parent_folder = next((f for f in parent_folders if f['id'] == parent_id), None)
            if parent_folder:
                folder_path = os.path.join(parent_folder.get('folder_path', ''), folder_name)
            else:
                folder_path = folder_name
        else:
            folder_path = folder_name
        
        # Create physical directory
        full_path = os.path.join(self.server_documents_path, folder_name)
        try:
            os.makedirs(full_path, exist_ok=True)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create directory: {str(e)}"
            }
        
        folder_data = {
            'folder_name': folder_name,
            'parent_id': parent_id,
            'folder_path': folder_path,
            'created_by': created_by,
            'description': description
        }
        
        try:
            folder_id = self.document_repository.add_folder(folder_data)
            return {
                "success": True,
                "message": f"Folder '{folder_name}' created successfully",
                "folder_id": folder_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to save folder to database: {str(e)}"
            }

    def get_folders(self, parent_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get folders by parent"""
        return self.document_repository.get_folders(parent_id)

    def get_folder_contents(self, folder_id: Optional[int] = None) -> Dict[str, Any]:
        """Get both folders and documents in a folder with proper UI format"""
        try:
            folders = self.get_folders(folder_id)
            documents = self.get_documents(folder_id)
            
            return {
                "success": True,
                "folders": folders,
                "documents": documents,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "folders": [],
                "documents": [],
                "error": str(e)
            }

    def search_documents(self, query: str) -> List[Dict[str, Any]]:
        """Search documents by filename or tags"""
        all_docs = self.get_documents()
        
        # Simple search implementation
        results = []
        query_lower = query.lower()
        
        for doc in all_docs:
            if (query_lower in doc['original_filename'].lower() or 
                (doc['tags'] and query_lower in doc['tags'].lower()) or
                (doc['description'] and query_lower in doc['description'].lower())):
                results.append(doc)
        
        return results

# Global instance for backward compatibility
document_manager = DocumentService()
