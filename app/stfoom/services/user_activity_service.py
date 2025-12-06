"""
User Activity Logger Service for STFOOM
=======================================
Service for tracking all user activities across the system.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import threading


class UserActivityLogger:
    """Service for logging user activities across all modules"""
    
    def __init__(self, db_path: str = "data/user_activity.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.current_user = None
        self.current_ip = "127.0.0.1"  # Default for local app
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize the user activity database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    module TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    details TEXT,
                    ip_address TEXT,
                    session_id TEXT,
                    result TEXT DEFAULT 'success',
                    execution_time_ms INTEGER,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            
            # Create indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_activities_user_timestamp 
                ON user_activities(user_id, timestamp DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_activities_module_action 
                ON user_activities(module, action)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_activities_timestamp 
                ON user_activities(timestamp DESC)
            """)
    
    def set_current_user(self, user_id: str, ip_address: str = "127.0.0.1"):
        """Set the current user for logging"""
        self.current_user = user_id
        self.current_ip = ip_address
        
        # Log login activity
        self.log_activity(
            action="user_login",
            module="authentication",
            details=f"User {user_id} logged in"
        )
    
    def clear_current_user(self):
        """Clear current user (for logout)"""
        if self.current_user:
            # Log logout activity
            self.log_activity(
                action="user_logout",
                module="authentication",
                details=f"User {self.current_user} logged out"
            )
        
        self.current_user = None
        self.current_ip = "127.0.0.1"
    
    def log_activity(
        self,
        action: str,
        module: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        result: str = "success",
        execution_time_ms: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Log a user activity
        
        Args:
            action: The action performed (e.g., 'create', 'update', 'delete', 'view')
            module: The module where action was performed (e.g., 'facture', 'vente', 'achat')
            resource_type: Type of resource (e.g., 'facture', 'client', 'payment')
            resource_id: ID of the resource affected
            details: Human-readable description of the activity
            result: Result of the action ('success', 'error', 'warning')
            execution_time_ms: Time taken to execute the action in milliseconds
            extra_data: Additional metadata to store with the activity
        """
        if not self.current_user:
            return  # No user logged in, skip logging
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare details with extra data
        if extra_data:
            details_dict = {
                "description": details or "",
                "extra": extra_data
            }
            details_json = json.dumps(details_dict, ensure_ascii=False)
        else:
            details_json = details or ""
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO user_activities 
                        (timestamp, user_id, action, module, resource_type, resource_id, 
                         details, ip_address, result, execution_time_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        timestamp, self.current_user, action, module, resource_type,
                        resource_id, details_json, self.current_ip, result, execution_time_ms
                    ))
            except Exception as e:
                # Fallback logging to file if database fails
                self._fallback_log(timestamp, action, module, details or "", str(e))
    
    def _fallback_log(self, timestamp: str, action: str, module: str, details: str, error: str):
        """Fallback logging to text file if database fails"""
        try:
            log_file = "data/activity_fallback.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} - {self.current_user} - {module}.{action} - {details} (DB_ERROR: {error})\n")
        except Exception:
            pass  # Last resort - ignore if we can't even write to file
    
    def get_activities(
        self,
        user_id: Optional[str] = None,
        module: Optional[str] = None,
        action: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user activities with filtering
        
        Returns:
            List of activity dictionaries
        """
        query = "SELECT * FROM user_activities WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if module:
            query += " AND module = ?"
            params.append(module)
        
        if action:
            query += " AND action LIKE ?"
            params.append(f"%{action}%")
        
        if date_from:
            query += " AND timestamp >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND timestamp <= ?"
            params.append(date_to)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert to dictionaries
                activities = []
                for row in rows:
                    activity = dict(row)
                    # Try to parse details as JSON
                    try:
                        if activity['details'] and activity['details'].startswith('{'):
                            details_dict = json.loads(activity['details'])
                            activity['details'] = details_dict.get('description', activity['details'])
                            activity['extra_data'] = details_dict.get('extra')
                    except (json.JSONDecodeError, KeyError):
                        pass  # Keep original details string
                    
                    activities.append(activity)
                
                return activities
        except Exception as e:
            print(f"Error retrieving activities: {e}")
            return []
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a specific user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total activities
                total = conn.execute(
                    "SELECT COUNT(*) FROM user_activities WHERE user_id = ?", 
                    (user_id,)
                ).fetchone()[0]
                
                # Activities today
                today = datetime.now().strftime("%Y-%m-%d")
                today_count = conn.execute(
                    "SELECT COUNT(*) FROM user_activities WHERE user_id = ? AND timestamp LIKE ?",
                    (user_id, f"{today}%")
                ).fetchone()[0]
                
                # Most used module
                most_used_module = conn.execute("""
                    SELECT module, COUNT(*) as count 
                    FROM user_activities 
                    WHERE user_id = ? 
                    GROUP BY module 
                    ORDER BY count DESC 
                    LIMIT 1
                """, (user_id,)).fetchone()
                
                # Most common action
                most_common_action = conn.execute("""
                    SELECT action, COUNT(*) as count 
                    FROM user_activities 
                    WHERE user_id = ? 
                    GROUP BY action 
                    ORDER BY count DESC 
                    LIMIT 1
                """, (user_id,)).fetchone()
                
                return {
                    'total_activities': total,
                    'activities_today': today_count,
                    'most_used_module': most_used_module[0] if most_used_module else 'N/A',
                    'most_common_action': most_common_action[0] if most_common_action else 'N/A'
                }
        except Exception as e:
            print(f"Error getting user statistics: {e}")
            return {
                'total_activities': 0,
                'activities_today': 0,
                'most_used_module': 'N/A',
                'most_common_action': 'N/A'
            }
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide activity statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total activities
                total = conn.execute("SELECT COUNT(*) FROM user_activities").fetchone()[0]
                
                # Unique users
                unique_users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM user_activities").fetchone()[0]
                
                # Activities today
                today = datetime.now().strftime("%Y-%m-%d")
                today_count = conn.execute(
                    "SELECT COUNT(*) FROM user_activities WHERE timestamp LIKE ?",
                    (f"{today}%",)
                ).fetchone()[0]
                
                # Activities this week
                from datetime import timedelta
                week_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                week_ago = (week_ago - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                week_count = conn.execute(
                    "SELECT COUNT(*) FROM user_activities WHERE timestamp >= ?",
                    (week_ago,)
                ).fetchone()[0]
                
                return {
                    'total_activities': total,
                    'unique_users': unique_users,
                    'activities_today': today_count,
                    'activities_week': week_count
                }
        except Exception as e:
            print(f"Error getting system statistics: {e}")
            return {
                'total_activities': 0,
                'unique_users': 0,
                'activities_today': 0,
                'activities_week': 0
            }
    
    def cleanup_old_activities(self, days_to_keep: int = 365):
        """Clean up old activity records"""
        cutoff_date = datetime.now() - datetime.timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "DELETE FROM user_activities WHERE timestamp < ?",
                    (cutoff_str,)
                )
                deleted_count = result.rowcount
                
                # Vacuum database to reclaim space
                conn.execute("VACUUM")
                
                return deleted_count
        except Exception as e:
            print(f"Error cleaning up activities: {e}")
            return 0


# Global instance
activity_logger = UserActivityLogger()


# Convenience functions for common actions
def log_user_action(action: str, module: str, details: str = None, **kwargs):
    """Convenience function to log user action"""
    activity_logger.log_activity(action=action, module=module, details=details, **kwargs)


def log_data_operation(operation: str, module: str, resource_type: str, resource_id: str = None, details: str = None):
    """Log data operations (create, read, update, delete)"""
    activity_logger.log_activity(
        action=f"data_{operation}",
        module=module,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or f"{operation.title()} {resource_type}" + (f" (ID: {resource_id})" if resource_id else "")
    )


def log_page_access(page_name: str):
    """Log page access"""
    activity_logger.log_activity(
        action="page_access",
        module="navigation",
        resource_type="page",
        resource_id=page_name,
        details=f"Accessed {page_name} page"
    )


def log_export_operation(export_type: str, module: str, file_name: str = None):
    """Log export operations"""
    activity_logger.log_activity(
        action="export",
        module=module,
        resource_type=export_type,
        details=f"Exported {export_type}" + (f" to {file_name}" if file_name else "")
    )


def log_import_operation(import_type: str, module: str, file_name: str = None, records_count: int = None):
    """Log import operations"""
    details = f"Imported {import_type}"
    if file_name:
        details += f" from {file_name}"
    if records_count:
        details += f" ({records_count} records)"
    
    activity_logger.log_activity(
        action="import",
        module=module,
        resource_type=import_type,
        details=details
    )


def log_error(module: str, action: str, error_message: str):
    """Log error events"""
    activity_logger.log_activity(
        action=action,
        module=module,
        details=f"Error: {error_message}",
        result="error"
    )


def log_warning(module: str, action: str, warning_message: str):
    """Log warning events"""
    activity_logger.log_activity(
        action=action,
        module=module,
        details=f"Warning: {warning_message}",
        result="warning"
    )