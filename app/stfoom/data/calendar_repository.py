"""
Calendar Repository Layer - Data Access for Calendar Events
==========================================================
Handles all database operations for calendar events with connection pooling.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional, List, Dict, Any
import sqlite3
# Use centralized DB helpers
from app.stfoom.logic.db_helpers import insert_row, update_row, soft_delete_row

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CalendarRepository:
    """Repository layer for calendar event data access with connection pooling."""
    
    def __init__(self):
        """Initialize calendar repository."""
        from app.stfoom.logic.secure_database import _get_db_path
        self.db_path = _get_db_path()
        # Initialize database
        self.init_db()
        logger.info(f"[CALENDAR_REPOSITORY] Initialized with database: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection - using direct SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self) -> None:
        """Create calendar_events table and add done column if missing."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS calendar_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        date TEXT NOT NULL,           -- YYYY-MM-DD
                        category TEXT NOT NULL,
                        description TEXT,
                        done INTEGER DEFAULT 0         -- 0 = pending, 1 = completed
                    )
                """)
                
                # Add done column if it doesn't exist (for legacy databases)
                try:
                    conn.execute("ALTER TABLE calendar_events ADD COLUMN done INTEGER DEFAULT 0")
                except sqlite3.OperationalError:
                    # Column already exists
                    pass
                
                conn.commit()
                logger.info("[CALENDAR_REPOSITORY] Database initialized successfully")
                
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error initializing database: {e}")
            raise
    
    # ================================ CRUD Operations ================================
    
    def add_event(self, title: str, date_str: str, category: str, 
                  description: str = "", done: int = 0) -> None:
        """Add new calendar event using centralized DB helpers."""
        try:
            data = {
                'title': title,
                'start_date': date_str,
                'event_type': category,
                'description': description,
                'done': done
            }
            insert_row('calendar_events', data)
            logger.info(f"[CALENDAR_REPOSITORY] Added event: {title}")
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error adding event: {e}")
            raise
    
    def update_event(self, event_id: int, title: str, date_str: str, category: str,
                     description: str, done: int = 0, **kwargs) -> None:
        """Update existing calendar event using centralized DB helpers."""
        try:
            data = {
                'title': title,
                'start_date': date_str,
                'event_type': category,
                'description': description,
                'done': done
            }
            update_row('calendar_events', 'id', event_id, data)
            logger.info(f"[CALENDAR_REPOSITORY] Updated event: {event_id}")
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error updating event {event_id}: {e}")
            raise
    
    def delete_event(self, event_id: int) -> None:
        """Soft delete calendar event by ID using custom soft delete for deleted_at field."""
        try:
            # Custom soft delete for calendar_events table which uses deleted_at field
            from datetime import datetime
            now = datetime.now().isoformat()
            
            # Update using direct SQL since calendar_events table uses deleted_at field
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE calendar_events SET deleted_at = ?, updated_at = ? WHERE id = ?",
                    (now, now, event_id)
                )
                conn.commit()
            
            # Track the change for sync - skip BaseRepository instantiation
            # from app.stfoom.data.base_repository import BaseRepository
            # base_repo = BaseRepository()
            # base_repo._track_change('calendar_events', 'delete', {'id': event_id})
            
            logger.info(f"[CALENDAR_REPOSITORY] Soft deleted event: {event_id}")
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error deleting event {event_id}: {e}")
            raise
    
    def delete_event_by_keys(self, date_str: str, category: str, title: str) -> None:
        """Soft delete calendar event(s) by unique keys using custom soft delete for deleted_at field."""
        try:
            rows = self._query("""
                SELECT id FROM calendar_events 
                WHERE start_date=? AND event_type=? AND title=? AND (deleted = 0 OR deleted IS NULL)
            """, (date_str, category, title))
            
            from datetime import datetime
            now = datetime.now().isoformat()
            
            for row in rows:
                event_id = row["id"]
                # Custom soft delete for calendar_events table
                with self._get_connection() as conn:
                    conn.execute(
                        "UPDATE calendar_events SET deleted_at = ?, updated_at = ? WHERE id = ?",
                        (now, now, event_id)
                    )
                    conn.commit()
                
                    # Track the change for sync - skip BaseRepository instantiation
                    # from app.stfoom.data.base_repository import BaseRepository
                    # base_repo = BaseRepository()
                    # base_repo._track_change('calendar_events', 'delete', {'id': event_id})            logger.info(f"[CALENDAR_REPOSITORY] Soft deleted {len(rows)} events by keys: {title}")
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error deleting event by keys: {e}")
            raise
    
    # ================================ Query Operations ================================
    
    def _query(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute query and return results."""
        try:
            with self._get_connection() as conn:
                return conn.execute(sql, params).fetchall()
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Query error: {e}")
            raise
    
    def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Get single event by ID."""
        try:
            rows = self._query("SELECT * FROM calendar_events WHERE id=? AND (deleted = 0 OR deleted IS NULL)", (event_id,))
            if rows:
                return dict(rows[0])
            return None
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting event {event_id}: {e}")
            raise
    
    def find_event(self, date_str: str, category: str, title: str) -> Optional[Dict[str, Any]]:
        """Find event by unique keys."""
        try:
            rows = self._query("""
                SELECT * FROM calendar_events
                WHERE start_date=? AND event_type=? AND title=? AND (deleted = 0 OR deleted IS NULL)
            """, (date_str, category, title))
            
            if rows:
                return dict(rows[0])
            return None
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error finding event: {e}")
            raise
    
    def _filtered_rows(self, categories: Optional[List[str]], include_past: bool,
                       include_done: bool) -> List[Dict[str, Any]]:
        """Core filter helper for events."""
        try:
            conditions = ["(deleted = 0 OR deleted IS NULL)"]  # Always exclude soft-deleted events
            params = []
            
            # Category filter - handle empty list case
            if categories is not None:
                if len(categories) == 0:
                    # No categories selected = return no events
                    return []
                else:
                    # Categories selected = filter by those categories
                    placeholders = ",".join("?" * len(categories))
                    conditions.append(f"event_type IN ({placeholders})")
                    params.extend(categories)
            
            # Done filter
            if not include_done:
                conditions.append("done = 0 OR done IS NULL")
            
            # Past filter
            if not include_past:
                conditions.append("start_date >= ?")
                params.append(date.today().isoformat())
            
            where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            sql = f"SELECT * FROM calendar_events {where_clause} ORDER BY start_date ASC"
            
            rows = self._query(sql, tuple(params))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error in filtered query: {e}")
            raise
    
    def get_all_events(self, categories: Optional[List[str]] = None,
                       include_past: bool = True, include_done: bool = False) -> List[Dict[str, Any]]:
        """Get all events with filtering options."""
        return self._filtered_rows(categories, include_past, include_done)
    
    def get_upcoming_items_dict(self, categories: Optional[List[str]] = None,
                               show_past: bool = False) -> List[Dict[str, Any]]:
        """Get upcoming events dictionary (no done events)."""
        return self._filtered_rows(categories, include_past=show_past, include_done=False)
    
    def get_upcoming_items(self, categories: Optional[List[str]] = None,
                          show_past: bool = False) -> List[str]:
        """Get upcoming events as formatted strings."""
        try:
            records = self.get_upcoming_items_dict(categories, show_past)
            return [f"{r.get('start_date') or r.get('date','')} [{r.get('event_type') or r.get('category','')}] {r['title']}" for r in records]
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting upcoming items: {e}")
            raise
    
    def get_events_due_tomorrow(self) -> List[Dict[str, Any]]:
        """Get events due tomorrow for notifications."""
        try:
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            
            rows = self._query("""
                SELECT * FROM calendar_events
                WHERE start_date = ? AND (done = 0 OR done IS NULL) AND (deleted = 0 OR deleted IS NULL)
                ORDER BY title ASC
            """, (tomorrow,))
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting tomorrow's events: {e}")
            raise
    
    def get_pending_calendar_notifications(self) -> List[Dict[str, Any]]:
        """Get calendar events that should trigger notifications."""
        try:
            events_due_tomorrow = self.get_events_due_tomorrow()
            notifications = []
            
            for event in events_due_tomorrow:
                notifications.append({
                    'event_id': event['id'],
                    'title': event['title'],
                    'date': event.get('start_date') or event.get('date', ''),
                    'category': event.get('event_type') or event.get('category', ''),
                    'description': event.get('description', ''),
                    'message': f"⏰ Rappel: '{event['title']}' est prévu pour demain ({event.get('start_date') or event.get('date', '')})"
                })
            
            return notifications
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting notifications: {e}")
            raise
    
    # ================================ Advanced Queries ================================
    
    def get_events_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get events within specific date range."""
        try:
            rows = self._query("""
                SELECT * FROM calendar_events
                WHERE start_date BETWEEN ? AND ? AND (deleted = 0 OR deleted IS NULL)
                ORDER BY start_date ASC, title ASC
            """, (start_date, end_date))
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting events by date range: {e}")
            raise
    
    def get_events_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all events for specific category."""
        try:
            rows = self._query("""
                SELECT * FROM calendar_events
                WHERE category = ? AND (deleted = 0 OR deleted IS NULL)
                ORDER BY date ASC, title ASC
            """, (category,))
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting events by category: {e}")
            raise
    
    def get_completed_events(self) -> List[Dict[str, Any]]:
        """Get all completed events."""
        try:
            rows = self._query("""
                SELECT * FROM calendar_events
                WHERE done = 1 AND (deleted = 0 OR deleted IS NULL)
                ORDER BY date DESC, title ASC
            """, ())
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting completed events: {e}")
            raise
    
    def get_pending_events(self) -> List[Dict[str, Any]]:
        """Get all pending events."""
        try:
            rows = self._query("""
                SELECT * FROM calendar_events
                WHERE done = 0 AND (deleted = 0 OR deleted IS NULL)
                ORDER BY date ASC, title ASC
            """, ())
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting pending events: {e}")
            raise
    
    def get_overdue_events(self) -> List[Dict[str, Any]]:
        """Get events that are overdue (past due date and not done)."""
        try:
            today = date.today().isoformat()
            rows = self._query("""
                SELECT * FROM calendar_events
                WHERE start_date < ? AND (done = 0 OR done IS NULL) AND (deleted = 0 OR deleted IS NULL)
                ORDER BY start_date ASC, title ASC
            """, (today,))
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting overdue events: {e}")
            raise
    
    # ================================ Statistics & Analytics ================================
    
    def get_event_count(self) -> int:
        """Get total number of events."""
        try:
            rows = self._query("SELECT COUNT(*) as count FROM calendar_events WHERE (deleted = 0 OR deleted IS NULL)")
            return rows[0]["count"] if rows else 0
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting event count: {e}")
            return 0
    
    def get_completed_count(self) -> int:
        """Get number of completed events."""
        try:
            rows = self._query("SELECT COUNT(*) as count FROM calendar_events WHERE done = 1 AND (deleted = 0 OR deleted IS NULL)")
            return rows[0]["count"] if rows else 0
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting completed count: {e}")
            return 0
    
    def get_pending_count(self) -> int:
        """Get number of pending events."""
        try:
            rows = self._query("SELECT COUNT(*) as count FROM calendar_events WHERE done = 0 AND (deleted = 0 OR deleted IS NULL)")
            return rows[0]["count"] if rows else 0
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting pending count: {e}")
            return 0
    
    def get_category_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics by category."""
        try:
            rows = self._query("""
                SELECT category, done, COUNT(*) as count
                FROM calendar_events
                WHERE (deleted = 0 OR deleted IS NULL)
                GROUP BY category, done
                ORDER BY category
            """)
            
            stats = {}
            for row in rows:
                category = row.get("event_type") or row.get("category", "Other")
                if category not in stats:
                    stats[category] = {"total": 0, "completed": 0, "pending": 0}
                
                count = row["count"]
                stats[category]["total"] += count
                
                if row["done"]:
                    stats[category]["completed"] += count
                else:
                    stats[category]["pending"] += count
            
            return stats
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting category stats: {e}")
            return {}
    
    def get_unique_categories(self) -> List[str]:
        """Get list of unique categories."""
        try:
            rows = self._query("SELECT DISTINCT event_type FROM calendar_events WHERE (deleted = 0 OR deleted IS NULL) AND event_type IS NOT NULL ORDER BY event_type")
            return [row["event_type"] for row in rows]
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error getting categories: {e}")
            return []
    
    # ================================ Maintenance Operations ================================
    
    def cleanup_old_completed_events(self, days_old: int = 365) -> int:
        """Soft delete completed events older than specified days using custom soft delete for deleted_at field."""
        try:
            cutoff_date = (date.today() - timedelta(days=days_old)).isoformat()
            rows = self._query("""
                SELECT id FROM calendar_events
                WHERE done = 1 AND start_date < ? AND (deleted = 0 OR deleted IS NULL)
            """, (cutoff_date,))
            
            count_to_delete = len(rows)
            if count_to_delete > 0:
                from datetime import datetime
                now = datetime.now().isoformat()
                
                for row in rows:
                    event_id = row["id"]
                    # Custom soft delete for calendar_events table
                    with self._get_connection() as conn:
                        conn.execute(
                            "UPDATE calendar_events SET deleted_at = ?, updated_at = ? WHERE id = ?",
                            (now, now, event_id)
                        )
                        conn.commit()
                    
                    # Track the change for sync - skip BaseRepository instantiation
                    # from app.stfoom.data.base_repository import BaseRepository
                    # base_repo = BaseRepository()
                    # base_repo._track_change('calendar_events', 'delete', {'id': event_id})
                
                logger.info(f"[CALENDAR_REPOSITORY] Soft deleted {count_to_delete} old completed events")
            
            return count_to_delete
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error cleaning up old events: {e}")
            return 0
    
    def vacuum_database(self) -> bool:
        """Vacuum the database to reclaim space."""
        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM")
                conn.commit()
            
            logger.info("[CALENDAR_REPOSITORY] Database vacuumed successfully")
            return True
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Error vacuuming database: {e}")
            return False
    
    # ================================ Health Checks ================================
    
    def health_check(self) -> Dict[str, Any]:
        """Perform repository health check."""
        try:
            health = {
                'status': 'healthy',
                'connection_test': False,
                'table_exists': False,
                'total_events': 0,
                'errors': []
            }
            
            # Test connection
            try:
                with self._get_connection() as conn:
                    conn.execute("SELECT 1")
                health['connection_test'] = True
            except Exception as e:
                health['errors'].append(f"Connection test failed: {e}")
                health['status'] = 'unhealthy'
            
            # Check table exists
            try:
                rows = self._query("SELECT name FROM sqlite_master WHERE type='table' AND name='calendar_events'")
                health['table_exists'] = len(rows) > 0
                if not health['table_exists']:
                    health['errors'].append("calendar_events table does not exist")
                    health['status'] = 'unhealthy'
            except Exception as e:
                health['errors'].append(f"Table check failed: {e}")
                health['status'] = 'unhealthy'
            
            # Get event count
            try:
                health['total_events'] = self.get_event_count()
            except Exception as e:
                health['errors'].append(f"Event count failed: {e}")
                health['status'] = 'warning'
            
            logger.info(f"[CALENDAR_REPOSITORY] Health check: {health['status']}")
            return health
            
        except Exception as e:
            logger.error(f"[CALENDAR_REPOSITORY] Health check error: {e}")
            return {
                'status': 'error',
                'connection_test': False,
                'table_exists': False,
                'total_events': 0,
                'errors': [str(e)]
            }
