"""
Base Repository Pattern
======================
Abstract base class for all repository implementations.
Provides common database operations and enforces consistent interface.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Type, TypeVar, Generic
import sqlite3
from contextlib import contextmanager
# REMOVED: No more logic imports - using direct database access

from app.stfoom.logic.db_helpers import insert_row, update_row, soft_delete_row
from app.stfoom.logic.secure_database import _get_db_path

# Sync service will be lazily imported to avoid circular dependencies
_sync_service = None

def _get_sync_service():
    """Lazy load sync service to avoid circular imports"""
    global _sync_service
    if _sync_service is None:
        try:
            from app.stfoom.services.sync_service import SyncService
            _sync_service = SyncService()
        except Exception as e:
            print(f"[BASE_REPO] Warning: Could not initialize sync service: {e}")
            _sync_service = False  # Use False to indicate failed initialization
    return _sync_service if _sync_service is not False else None

# Generic type for repository entities
T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository class.
    
    Provides common database operations and enforces consistent interface
    for all data access operations.
    """
    
    def __init__(self, table_name: str):
        """
        Initialize repository with table name.
        
        Args:
            table_name: Name of the database table this repository manages
        """
        self.table_name = table_name
    
    @contextmanager
    def get_connection(self):
        """Get database connection directly using settings."""
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """
        Execute a SELECT query and return results.
        
        Args:
            sql: SQL query string
            params: Query parameters
            
        Returns:
            List of database rows
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            print(f"[REPO] Query error in {self.table_name}: {e}")
            return []
    
    def execute_command(self, sql: str, params: tuple = ()) -> bool:
        """
        Execute an INSERT, UPDATE, or DELETE command.
        Automatically tracks changes for sync.
        
        Args:
            sql: SQL command string
            params: Command parameters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(sql, params)
                conn.commit()
                
                # Track change for sync
                self._track_change(sql, params, cursor)
                
                return True
        except Exception as e:
            print(f"[REPO] Command error in {self.table_name}: {e}")
            return False
    
    def _track_change(self, sql: str, params: tuple, cursor):
        """Track database change for sync."""
        sync_service = _get_sync_service()
        if not sync_service:
            return
        
        try:
            sql_upper = sql.upper().strip()
            
            # Extract table name from SQL
            table_name = self.table_name  # default
            if 'INSERT INTO' in sql_upper:
                # Extract table from "INSERT INTO table_name"
                parts = sql_upper.split('INSERT INTO')[1].split('(')[0].strip()
                table_name = parts.split()[0].lower()
            elif 'UPDATE' in sql_upper:
                # Extract table from "UPDATE table_name SET"
                parts = sql_upper.split('UPDATE')[1].split('SET')[0].strip()
                table_name = parts.lower()
            elif 'DELETE FROM' in sql_upper:
                # Extract table from "DELETE FROM table_name"
                parts = sql_upper.split('DELETE FROM')[1].split('WHERE')[0].strip()
                table_name = parts.lower()
            
            # Determine operation type
            if sql_upper.startswith('INSERT'):
                operation = 'INSERT'
                record_id = str(cursor.lastrowid)
            elif sql_upper.startswith('UPDATE'):
                operation = 'UPDATE'
                # For UPDATE, record_id is usually in WHERE clause
                # Try to get it from params - often last param in "WHERE id = ?"
                record_id = str(params[-1]) if params else 'unknown'
            elif sql_upper.startswith('DELETE'):
                operation = 'DELETE'
                # For DELETE, record_id is in WHERE clause
                record_id = str(params[0]) if params else 'unknown'
            else:
                return  # Not a tracked operation
            
            # Create data dict from params
            data = {'params': str(params)}
            
            # Queue for sync
            sync_service.add_sync_change(
                table_name=table_name,
                record_id=record_id,
                data=data,
                operation=operation
            )
        except Exception as e:
            # Don't fail the operation if sync tracking fails
            print(f"[REPO] Sync tracking error: {e}")
            return False
    
    def get_by_id(self, id_value: Any, id_column: str = "id") -> Optional[Dict[str, Any]]:
        """
        Get a single record by ID.
        
        Args:
            id_value: The ID value to search for
            id_column: The column name for the ID (default: "id")
            
        Returns:
            Dictionary representation of the record, or None if not found
        """
        sql = f"SELECT * FROM {self.table_name} WHERE {id_column} = ? LIMIT 1"
        rows = self.execute_query(sql, (id_value,))
        return dict(rows[0]) if rows else None
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all records from the table.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of dictionary representations of records
        """
        sql = f"SELECT * FROM {self.table_name}"
        
        if limit is not None:
            sql += f" LIMIT {limit} OFFSET {offset}"
        
        rows = self.execute_query(sql)
        return [dict(row) for row in rows]
    
    def create(self, data: Dict[str, Any]) -> bool:
        """
        Create a new record using centralized DB helpers (with timestamps).
        """
        if not data:
            return False
        try:
            insert_row(self.table_name, data)
            return True
        except Exception as e:
            print(f"[REPO] Create error in {self.table_name}: {e}")
            return False
    
    def update(self, id_value: Any, data: Dict[str, Any], id_column: str = "id") -> bool:
        """
        Update an existing record using centralized DB helpers (with timestamps).
        """
        if not data:
            return False
        try:
            update_row(self.table_name, id_column, id_value, data)
            return True
        except Exception as e:
            print(f"[REPO] Update error in {self.table_name}: {e}")
            return False
    
    def delete(self, id_value: Any, id_column: str = "id") -> bool:
        """
        Soft delete a record by ID using centralized DB helpers (sets deleted=1, updates timestamp).
        """
        try:
            soft_delete_row(self.table_name, id_column, id_value)
            return True
        except Exception as e:
            print(f"[REPO] Delete error in {self.table_name}: {e}")
            return False
    
    def exists(self, id_value: Any, id_column: str = "id") -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            id_value: The ID value to check
            id_column: The column name for the ID (default: "id")
            
        Returns:
            True if record exists, False otherwise
        """
        sql = f"SELECT 1 FROM {self.table_name} WHERE {id_column} = ? LIMIT 1"
        rows = self.execute_query(sql, (id_value,))
        return len(rows) > 0
    
    def count(self, where_clause: str = "", params: tuple = ()) -> int:
        """
        Count records in the table.
        
        Args:
            where_clause: Optional WHERE clause (without the WHERE keyword)
            params: Parameters for the WHERE clause
            
        Returns:
            Number of records
        """
        sql = f"SELECT COUNT(*) FROM {self.table_name}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        
        rows = self.execute_query(sql, params)
        return rows[0][0] if rows else 0
    
    def find_by(self, **criteria) -> List[Dict[str, Any]]:
        """
        Find records by specified criteria.
        
        Args:
            **criteria: Key-value pairs for WHERE conditions
            
        Returns:
            List of matching records
        """
        if not criteria:
            return self.get_all()
        
        where_conditions = [f"{col} = ?" for col in criteria.keys()]
        where_str = ' AND '.join(where_conditions)
        values = tuple(criteria.values())
        
        sql = f"SELECT * FROM {self.table_name} WHERE {where_str}"
        rows = self.execute_query(sql, values)
        return [dict(row) for row in rows]
    
    # Abstract methods that concrete repositories can implement
    @abstractmethod
    def get_entity_name(self) -> str:
        """Return the name of the entity this repository manages."""
        pass
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate data before database operations.
        Override in concrete repositories for specific validation.
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        return True
    
    def transform_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform data before storing in database.
        Override in concrete repositories for specific transformations.
        
        Args:
            data: Data to transform
            
        Returns:
            Transformed data
        """
        return data
    
    def transform_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform data after retrieving from database.
        Override in concrete repositories for specific transformations.
        
        Args:
            data: Data from database
            
        Returns:
            Transformed data
        """
        return data
