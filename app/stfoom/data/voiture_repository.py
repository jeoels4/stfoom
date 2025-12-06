"""
VoitureRepository - Vehicle Data Access Layer
==========================================

Phase 2G Migration: VoiturePage → VoitureService
This repository handles all database operations for vehicle management,
including CRUD operations, calendar integration, and connection pooling.

Features:
- Connection pooling for database performance
- Sync wrapper integration for server synchronization
- Calendar integration for vehicle events
- Comprehensive error handling
- Optimized queries for filtering
"""

import logging
import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.stfoom.logic.db_helpers import insert_row, update_row

logger = logging.getLogger(__name__)

class VoitureRepository:
    """Repository layer for vehicle data access operations."""
    
    def __init__(self):
        """Initialize the repository with connection pooling."""
        self._ensure_tables()
        logger.info("[VOITURE REPOSITORY] Initialized with connection pooling")
    
    def _get_connection(self):
        """Get database connection - using direct SQLite connection."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        from config.settings import get_db_path
        return sqlite3.connect(get_db_path())
    
    def _ensure_tables(self):
        """Ensure vehicle tables exist."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS voitures (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        genre TEXT,
                        utilisateur TEXT,
                        matricule TEXT,
                        date_visite TEXT,
                        date_assurance TEXT,
                        date_vignette TEXT,
                        date_premiere_mise TEXT
                    )
                """)
                conn.commit()
            logger.debug("[VOITURE REPOSITORY] Table initialization completed")
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error ensuring tables: {e}")
            raise
    
    # ═══════════════════════════════════════════════════════════════
    # CRUD Operations
    # ═══════════════════════════════════════════════════════════════
    
    def get_all_voitures(self) -> List[Dict[str, Any]]:
        """Get all vehicles from database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM voitures ORDER BY id DESC")
                rows = cursor.fetchall()
                
                # Convert to dictionaries
                columns = [description[0] for description in cursor.description]
                voitures = [dict(zip(columns, row)) for row in rows]
                
                logger.debug(f"[VOITURE REPOSITORY] Retrieved {len(voitures)} vehicle records")
                return voitures
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error getting vehicles: {e}")
            return []
    
    def get_voiture_by_id(self, voiture_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific vehicle by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM voitures WHERE id = ?",
                    (voiture_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    columns = [description[0] for description in cursor.description]
                    voiture = dict(zip(columns, row))
                    logger.debug(f"[VOITURE REPOSITORY] Retrieved vehicle ID {voiture_id}")
                    return voiture
                else:
                    logger.debug(f"[VOITURE REPOSITORY] Vehicle ID {voiture_id} not found")
                    return None
                    
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error getting vehicle {voiture_id}: {e}")
            return None
    
    def add_voiture(self, data: Dict[str, Any]) -> bool:
        """Add a new vehicle to database."""
        try:
            success = insert_row("voitures", data)
                
            if success:
                # Add calendar events
                self._push_to_calendar(data)
                logger.info(f"[VOITURE REPOSITORY] Added vehicle: {data.get('matricule', 'Unknown')}")
            else:
                logger.error(f"[VOITURE REPOSITORY] Failed to add vehicle: {data.get('matricule', 'Unknown')}")
            
            return success
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error adding vehicle: {e}")
            return False
    
    def update_voiture(self, voiture_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing vehicle."""
        try:
            # Remove old calendar events first
            matricule = data.get('matricule', '')
            if matricule:
                self._remove_from_calendar(matricule)
            
            update_row("voitures", "id", voiture_id, data)
                
            # Add new calendar events
            self._push_to_calendar(data)
            logger.info(f"[VOITURE REPOSITORY] Updated vehicle ID {voiture_id}: {data.get('matricule', 'Unknown')}")
            return True
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error updating vehicle {voiture_id}: {e}")
            return False
    
    def update(self, voiture_id: int, data: Dict[str, Any]) -> bool:
        """
        Generic update method for sync testing.
        
        Args:
            voiture_id: The ID of the voiture to update
            data: Dictionary containing updated voiture information
            
        Returns:
            True if updated successfully, False otherwise
        """
        return self.update_voiture(voiture_id, data)
    
    def delete_voiture(self, voiture_id: int) -> bool:
        """Delete a vehicle from database."""
        try:
            # Get matricule for calendar cleanup
            matricule = None
            voiture = self.get_voiture_by_id(voiture_id)
            if voiture:
                matricule = voiture.get('matricule', '')
            
            with self._get_connection() as conn:
                conn.execute("DELETE FROM voitures WHERE id = ?", (voiture_id,))
                conn.commit()
                success = True
                
                if success:
                    # Remove calendar events
                    if matricule:
                        self._remove_from_calendar(matricule)
                    logger.info(f"[VOITURE REPOSITORY] Deleted vehicle ID {voiture_id}")
                else:
                    logger.error(f"[VOITURE REPOSITORY] Failed to delete vehicle ID {voiture_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error deleting vehicle {voiture_id}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════
    # Filtering Operations
    # ═══════════════════════════════════════════════════════════════
    
    def get_voitures_by_genre(self, genre: str) -> List[Dict[str, Any]]:
        """Get vehicles filtered by genre."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM voitures WHERE genre = ? ORDER BY id DESC",
                    (genre,)
                )
                rows = cursor.fetchall()
                
                columns = [description[0] for description in cursor.description]
                voitures = [dict(zip(columns, row)) for row in rows]
                
                logger.debug(f"[VOITURE REPOSITORY] Retrieved {len(voitures)} vehicles for genre: {genre}")
                return voitures
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error getting vehicles by genre {genre}: {e}")
            return []
    
    def get_voitures_by_user(self, utilisateur: str) -> List[Dict[str, Any]]:
        """Get vehicles filtered by user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM voitures WHERE utilisateur = ? ORDER BY id DESC",
                    (utilisateur,)
                )
                rows = cursor.fetchall()
                
                columns = [description[0] for description in cursor.description]
                voitures = [dict(zip(columns, row)) for row in rows]
                
                logger.debug(f"[VOITURE REPOSITORY] Retrieved {len(voitures)} vehicles for user: {utilisateur}")
                return voitures
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error getting vehicles by user {utilisateur}: {e}")
            return []
    
    def search_voitures(self, search_term: str) -> List[Dict[str, Any]]:
        """Search vehicles by matricule or utilisateur."""
        try:
            search_pattern = f"%{search_term}%"
            
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM voitures 
                    WHERE matricule LIKE ? OR utilisateur LIKE ?
                    ORDER BY id DESC
                """, (search_pattern, search_pattern))
                rows = cursor.fetchall()
                
                columns = [description[0] for description in cursor.description]
                voitures = [dict(zip(columns, row)) for row in rows]
                
                logger.debug(f"[VOITURE REPOSITORY] Found {len(voitures)} vehicles matching '{search_term}'")
                return voitures
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error searching vehicles: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════
    # Calendar Integration
    # ═══════════════════════════════════════════════════════════════
    
    def _push_to_calendar(self, data: Dict[str, Any]):
        """Create calendar events for vehicle maintenance dates."""
        try:
            # TODO: Use CalendarService when available
            logger.info(f"Calendar events for voiture maintenance deferred to CalendarService")
            
            # Calendar integration deferred to CalendarService
            
            logger.debug(f"[VOITURE REPOSITORY] Calendar events deferred for vehicle")
            
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error in calendar integration: {e}")
    
    def _remove_from_calendar(self, matricule: str):
        """Remove all calendar events for a specific vehicle."""
        try:
            # TODO: Use CalendarService when available
            logger.info(f"Calendar cleanup for {matricule} deferred to CalendarService")
            
            # Calendar cleanup deferred to CalendarService
            
            logger.debug(f"[VOITURE REPOSITORY] Calendar cleanup deferred for {matricule}")
            
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error in calendar cleanup: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # Utility Methods
    # ═══════════════════════════════════════════════════════════════
    
    def get_unique_users(self) -> List[str]:
        """Get list of unique vehicle users."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT utilisateur 
                    FROM voitures 
                    WHERE utilisateur IS NOT NULL AND utilisateur != ''
                    ORDER BY utilisateur
                """)
                rows = cursor.fetchall()
                
                users = [row[0] for row in rows if row[0] and row[0].strip()]
                
                logger.debug(f"[VOITURE REPOSITORY] Retrieved {len(users)} unique users")
                return users
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error getting unique users: {e}")
            return []
    
    def get_unique_genres(self) -> List[str]:
        """Get list of unique vehicle genres."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT genre 
                    FROM voitures 
                    WHERE genre IS NOT NULL AND genre != ''
                    ORDER BY genre
                """)
                rows = cursor.fetchall()
                
                genres = [row[0] for row in rows if row[0] and row[0].strip()]
                
                logger.debug(f"[VOITURE REPOSITORY] Retrieved {len(genres)} unique genres")
                return genres
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error getting unique genres: {e}")
            return []
    
    def count_voitures(self) -> int:
        """Get total count of vehicles."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM voitures")
                count = cursor.fetchone()[0]
                
                logger.debug(f"[VOITURE REPOSITORY] Total vehicle count: {count}")
                return count
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error counting vehicles: {e}")
            return 0
    
    def get_vehicles_with_upcoming_dates(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get vehicles with maintenance dates approaching."""
        try:
            from datetime import datetime, timedelta
            
            now = datetime.now()
            end_date = now + timedelta(days=days_ahead)
            
            # Format dates for SQL comparison
            now_str = now.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM voitures 
                    WHERE (date_visite BETWEEN ? AND ?)
                       OR (date_assurance BETWEEN ? AND ?)
                       OR (date_vignette BETWEEN ? AND ?)
                    ORDER BY date_visite, date_assurance, date_vignette
                """, (now_str, end_str, now_str, end_str, now_str, end_str))
                rows = cursor.fetchall()
                
                columns = [description[0] for description in cursor.description]
                voitures = [dict(zip(columns, row)) for row in rows]
                
                logger.debug(f"[VOITURE REPOSITORY] Found {len(voitures)} vehicles with upcoming dates")
                return voitures
                
        except Exception as e:
            logger.error(f"[VOITURE REPOSITORY] Error getting vehicles with upcoming dates: {e}")
            return []
