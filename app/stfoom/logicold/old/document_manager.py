"""
Document Management System
Cloud-based file sharing with folder organization
Files are stored on the server for multi-user access
"""

import os
import sqlite3
import shutil
import hashlib
import mimetypes
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from stfoom.logicold import secure_database as db
import connection.sync_wrapper as sync

class DocumentManager:
    """Manages cloud-based document storage and organization"""
    
    def __init__(self):
        self.init_document_tables()
        self.server_documents_path = self._get_server_documents_path()
        self.local_cache_path = self._get_local_cache_path()
        self._ensure_directories()
    
    def _get_server_documents_path(self) -> str:
        """Get the server path for document storage"""
        try:
            # Try to get server path from sync system
            import connection.smart_sync as smart_sync
            server_base = smart_sync.get_server_path()
            if server_base and os.path.exists(server_base):
                return os.path.join(server_base, "documents")
        except:
            pass
        
        # Fallback to local storage if server not available
        return os.path.join(os.getcwd(), "data", "documents")
    
    def _get_local_cache_path(self) -> str:
        """Get local cache path for temporary files"""
        return os.path.join(os.getcwd(), "data", "document_cache")
    
    def _ensure_directories(self):
        """Ensure document directories exist"""
        for path in [self.server_documents_path, self.local_cache_path]:
            os.makedirs(path, exist_ok=True)
    
    def init_document_tables(self):
        """Initialize document management tables"""
        try:
            # Use direct database connection without authentication context during startup
            import sqlite3
            import os
            
            # Get database path
            db_path = "data/stfoom.db"
            if not os.path.exists(db_path):
                # If main db doesn't exist, create basic structure
                os.makedirs("data", exist_ok=True)
            
            with sqlite3.connect(db_path, timeout=10) as conn:
                # Main documents table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    mime_type TEXT,
                    folder_id INTEGER,
                    uploaded_by TEXT NOT NULL,
                    upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    tags TEXT,
                    version INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    download_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    FOREIGN KEY (folder_id) REFERENCES document_folders(id)
                )
                """)
                
                # Folders table for organization
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS document_folders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        parent_id INTEGER,
                        created_by TEXT NOT NULL,
                        created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        description TEXT,
                        color TEXT DEFAULT '#4CAF50',
                        icon TEXT DEFAULT '📁',
                        is_public BOOLEAN DEFAULT 1,
                        FOREIGN KEY (parent_id) REFERENCES document_folders(id)
                    )
                """)
                
                # Access permissions table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS document_permissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER,
                        folder_id INTEGER,
                        user_id TEXT,
                        permission_type TEXT NOT NULL, -- 'read', 'write', 'admin'
                        granted_by TEXT NOT NULL,
                        granted_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents(id),
                        FOREIGN KEY (folder_id) REFERENCES document_folders(id)
                    )
                """)
                
                # Download history table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS document_downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER NOT NULL,
                        downloaded_by TEXT NOT NULL,
                        download_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        ip_address TEXT,
                        FOREIGN KEY (document_id) REFERENCES documents(id)
                    )
                """)
                
                # Create default folders if they don't exist
                self._create_default_folders(conn)
                
        except Exception as e:
            print(f"[DOCUMENTS] Error initializing tables: {e}")
    
    def _create_default_folders(self, conn):
        """Create default folder structure"""
        default_folders = [
            ("📄 Documents Généraux", None, "Système", "Documents généraux de l'entreprise", "#2196F3"),
            ("📊 Rapports", None, "Système", "Rapports et analyses", "#FF9800"),
            ("📋 Procédures", None, "Système", "Procédures et instructions", "#9C27B0"),
            ("📸 Images", None, "Système", "Images et photos", "#4CAF50"),
            ("📁 Archives", None, "Système", "Documents archivés", "#607D8B"),
            ("⚙️ Technique", None, "Système", "Documentation technique", "#F44336"),
        ]
        
        for name, parent_id, created_by, description, color in default_folders:
            existing = conn.execute(
                "SELECT id FROM document_folders WHERE name = ? AND parent_id IS NULL", 
                (name,)
            ).fetchone()
            
            if not existing:
                conn.execute("""
                    INSERT INTO document_folders (name, parent_id, created_by, description, color)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, parent_id, created_by, description, color))
    
    def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""
    
    def upload_document(self, file_path: str, folder_id: Optional[int] = None, 
                       description: str = "", tags: str = "", uploaded_by: str = "Unknown") -> Dict:
        """Upload a document to the server"""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": "File not found"}
            
            # Get file info
            original_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_hash = self.get_file_hash(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # Check if file already exists (by hash)
            with db.get_connection() as conn:
                existing = conn.execute(
                    "SELECT id, name FROM documents WHERE file_hash = ? AND is_active = 1",
                    (file_hash,)
                ).fetchone()
                
                if existing:
                    return {
                        "success": False, 
                        "error": f"File already exists: {existing[1]}"
                    }
            
            # Generate unique filename for server storage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = Path(file_path).suffix
            unique_filename = f"{timestamp}_{file_hash[:8]}{file_extension}"
            
            # Copy file to server location
            server_file_path = os.path.join(self.server_documents_path, unique_filename)
            shutil.copy2(file_path, server_file_path)
            
            # Save to database
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO documents 
                    (name, original_name, file_path, file_size, file_hash, mime_type, 
                     folder_id, uploaded_by, description, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    original_name, original_name, unique_filename, file_size, 
                    file_hash, mime_type, folder_id, uploaded_by, description, tags
                ))
                
                document_id = cursor.lastrowid
                conn.commit()
            
            # Sync to server
            sync.insert_with_sync("documents", {
                "id": document_id,
                "name": original_name,
                "original_name": original_name,
                "file_path": unique_filename,
                "file_size": file_size,
                "file_hash": file_hash,
                "mime_type": mime_type,
                "folder_id": folder_id,
                "uploaded_by": uploaded_by,
                "description": description,
                "tags": tags,
                "upload_date": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "document_id": document_id,
                "message": f"Document '{original_name}' uploaded successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def download_document(self, document_id: int, download_path: str, 
                         downloaded_by: str = "Unknown") -> Dict:
        """Download a document from server to local path"""
        try:
            with db.get_connection() as conn:
                doc = conn.execute("""
                    SELECT name, original_name, file_path, file_size 
                    FROM documents WHERE id = ? AND is_active = 1
                """, (document_id,)).fetchone()
                
                if not doc:
                    return {"success": False, "error": "Document not found"}
                
                name, original_name, file_path, file_size = doc
                server_file_path = os.path.join(self.server_documents_path, file_path)
                
                if not os.path.exists(server_file_path):
                    return {"success": False, "error": "File not found on server"}
                
                # Ensure download directory exists
                os.makedirs(os.path.dirname(download_path), exist_ok=True)
                
                # Copy file to download location
                shutil.copy2(server_file_path, download_path)
                
                # Update download statistics
                conn.execute("""
                    UPDATE documents 
                    SET download_count = download_count + 1, last_accessed = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (document_id,))
                
                # Record download history
                conn.execute("""
                    INSERT INTO document_downloads (document_id, downloaded_by)
                    VALUES (?, ?)
                """, (document_id, downloaded_by))
                
                conn.commit()
            
            return {
                "success": True,
                "message": f"Document '{original_name}' downloaded successfully",
                "file_path": download_path
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_folder(self, name: str, parent_id: Optional[int] = None, 
                     created_by: str = "Unknown", description: str = "", 
                     color: str = "#4CAF50", icon: str = "📁") -> Dict:
        """Create a new folder"""
        try:
            with db.get_connection() as conn:
                # Check if folder name already exists in same parent
                existing = conn.execute("""
                    SELECT id FROM document_folders 
                    WHERE name = ? AND parent_id = ?
                """, (name, parent_id)).fetchone()
                
                if existing:
                    return {"success": False, "error": "Folder name already exists"}
                
                cursor = conn.execute("""
                    INSERT INTO document_folders 
                    (name, parent_id, created_by, description, color, icon)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, parent_id, created_by, description, color, icon))
                
                folder_id = cursor.lastrowid
                conn.commit()
            
            # Sync to server
            sync.insert_with_sync("document_folders", {
                "id": folder_id,
                "name": name,
                "parent_id": parent_id,
                "created_by": created_by,
                "description": description,
                "color": color,
                "icon": icon,
                "created_date": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "folder_id": folder_id,
                "message": f"Folder '{name}' created successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_folder_contents(self, folder_id: Optional[int] = None) -> Dict:
        """Get contents of a folder (subfolders and documents)"""
        try:
            with db.get_connection() as conn:
                # Get subfolders
                folders = conn.execute("""
                    SELECT id, name, description, color, icon, created_by, created_date
                    FROM document_folders 
                    WHERE parent_id = ? OR (parent_id IS NULL AND ? IS NULL)
                    ORDER BY name
                """, (folder_id, folder_id)).fetchall()
                
                # Get documents in folder
                documents = conn.execute("""
                    SELECT id, name, original_name, file_size, mime_type, uploaded_by, 
                           upload_date, description, tags, download_count, last_accessed
                    FROM documents 
                    WHERE folder_id = ? AND is_active = 1
                    ORDER BY upload_date DESC
                """, (folder_id,)).fetchall()
                
                return {
                    "success": True,
                    "folders": [dict(folder) for folder in folders],
                    "documents": [dict(doc) for doc in documents]
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_documents(self, query: str, folder_id: Optional[int] = None) -> List[Dict]:
        """Search documents by name, description, or tags"""
        try:
            with db.get_connection() as conn:
                sql = """
                    SELECT d.id, d.name, d.original_name, d.file_size, d.mime_type, 
                           d.uploaded_by, d.upload_date, d.description, d.tags,
                           f.name as folder_name
                    FROM documents d
                    LEFT JOIN document_folders f ON d.folder_id = f.id
                    WHERE d.is_active = 1 AND (
                        d.name LIKE ? OR d.description LIKE ? OR d.tags LIKE ?
                    )
                """
                params = [f"%{query}%"] * 3
                
                if folder_id:
                    sql += " AND d.folder_id = ?"
                    params.append(folder_id)
                
                sql += " ORDER BY d.upload_date DESC"
                
                results = conn.execute(sql, params).fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            print(f"[DOCUMENTS] Search error: {e}")
            return []
    
    def delete_document(self, document_id: int, deleted_by: str = "Unknown") -> Dict:
        """Soft delete a document"""
        try:
            with db.get_connection() as conn:
                # Mark as inactive
                conn.execute("""
                    UPDATE documents 
                    SET is_active = 0, last_accessed = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (document_id,))
                conn.commit()
            
            # Sync deletion
            sync.update_with_sync("documents", str(document_id), {
                "is_active": 0,
                "deleted_by": deleted_by,
                "deleted_date": datetime.now().isoformat()
            })
            
            return {"success": True, "message": "Document deleted successfully"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_document_info(self, document_id: int) -> Optional[Dict]:
        """Get detailed information about a document"""
        try:
            with db.get_connection() as conn:
                doc = conn.execute("""
                    SELECT d.*, f.name as folder_name
                    FROM documents d
                    LEFT JOIN document_folders f ON d.folder_id = f.id
                    WHERE d.id = ? AND d.is_active = 1
                """, (document_id,)).fetchone()
                
                if doc:
                    return dict(doc)
                return None
                
        except Exception as e:
            print(f"[DOCUMENTS] Error getting document info: {e}")
            return None
    
    def get_folder_tree(self) -> List[Dict]:
        """Get complete folder hierarchy"""
        try:
            with db.get_connection() as conn:
                folders = conn.execute("""
                    SELECT id, name, parent_id, description, color, icon, created_by
                    FROM document_folders 
                    ORDER BY parent_id, name
                """).fetchall()
                
                # Build tree structure
                folder_dict = {f[0]: dict(f) for f in folders}
                tree = []
                
                for folder in folders:
                    folder_data = dict(folder)
                    if folder_data['parent_id'] is None:
                        tree.append(folder_data)
                
                return tree
                
        except Exception as e:
            print(f"[DOCUMENTS] Error getting folder tree: {e}")
            return []

# Global instance
document_manager = DocumentManager()
