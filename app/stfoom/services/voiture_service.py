"""
VoitureService - Vehicle Management Business Logic Layer
=====================================================

Phase 2G Migration: VoiturePage → VoitureService
This service handles all vehicle management business logic, providing a clean interface
for CRUD operations and enhanced functionality.

Features:
- Vehicle CRUD operations with validation
- Calendar integration for important dates
- Age calculation and formatting utilities
- Connection pooling for performance
- Enhanced error handling and logging
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class VoitureService:
    """Service layer for vehicle management operations."""
    
    def __init__(self, voiture_repository):
        """Initialize the service with a repository."""
        self.repository = voiture_repository
        logger.info("[VOITURE SERVICE] Initialized with repository")
    
    # ═══════════════════════════════════════════════════════════════
    # CRUD Operations
    # ═══════════════════════════════════════════════════════════════
    
    def get_all_voitures(self) -> List[Dict[str, Any]]:
        """Get all vehicles with computed age and formatted data."""
        try:
            voitures = self.repository.get_all_voitures()
            
            # Add computed fields
            for voiture in voitures:
                voiture['age'] = self.compute_age(voiture.get('date_premiere_mise', ''))
            
            logger.info(f"[VOITURE SERVICE] Retrieved {len(voitures)} vehicles")
            return voitures
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error getting vehicles: {e}")
            raise
    
    def get_voiture_by_id(self, voiture_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific vehicle by ID."""
        try:
            voiture = self.repository.get_voiture_by_id(voiture_id)
            if voiture:
                voiture['age'] = self.compute_age(voiture.get('date_premiere_mise', ''))
                logger.info(f"[VOITURE SERVICE] Retrieved vehicle ID {voiture_id}")
            else:
                logger.warning(f"[VOITURE SERVICE] Vehicle ID {voiture_id} not found")
            return voiture
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error getting vehicle {voiture_id}: {e}")
            raise
    
    def create_voiture(self, data: Dict[str, Any]) -> bool:
        """Create a new vehicle with validation."""
        try:
            # Validate data
            if not self.validate_voiture_data(data):
                return False
            
            # Create vehicle
            success = self.repository.add_voiture(data)
            
            if success:
                logger.info(f"[VOITURE SERVICE] Created vehicle: {data.get('matricule', 'Unknown')}")
            else:
                logger.error(f"[VOITURE SERVICE] Failed to create vehicle: {data.get('matricule', 'Unknown')}")
            
            return success
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error creating vehicle: {e}")
            return False
    
    def update_voiture(self, voiture_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing vehicle with validation."""
        try:
            # Validate data
            if not self.validate_voiture_data(data):
                return False
            
            # Update vehicle
            success = self.repository.update_voiture(voiture_id, data)
            
            if success:
                logger.info(f"[VOITURE SERVICE] Updated vehicle ID {voiture_id}: {data.get('matricule', 'Unknown')}")
            else:
                logger.error(f"[VOITURE SERVICE] Failed to update vehicle ID {voiture_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error updating vehicle {voiture_id}: {e}")
            return False
    
    def delete_voiture(self, voiture_id: int) -> bool:
        """Delete a vehicle."""
        try:
            success = self.repository.delete_voiture(voiture_id)
            
            if success:
                logger.info(f"[VOITURE SERVICE] Deleted vehicle ID {voiture_id}")
            else:
                logger.error(f"[VOITURE SERVICE] Failed to delete vehicle ID {voiture_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error deleting vehicle {voiture_id}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════
    # Business Logic & Utilities
    # ═══════════════════════════════════════════════════════════════
    
    def validate_voiture_data(self, data: Dict[str, Any]) -> bool:
        """Validate vehicle data before saving."""
        try:
            # Required fields
            if not data.get('matricule', '').strip():
                logger.warning("[VOITURE SERVICE] Validation failed: Missing matricule")
                return False
            
            # Optional: Validate genre if provided
            valid_genres = ["voiture", "partner", "camion", "remorque"]
            genre = data.get('genre', '').strip().lower()
            if genre and genre not in valid_genres:
                logger.warning(f"[VOITURE SERVICE] Validation failed: Invalid genre '{genre}'")
                return False
            
            # Validate date formats if provided
            date_fields = ['date_visite', 'date_assurance', 'date_vignette', 'date_premiere_mise']
            for field in date_fields:
                date_value = data.get(field, '')
                if date_value and not self.validate_date_format(date_value):
                    logger.warning(f"[VOITURE SERVICE] Validation failed: Invalid date format for {field}: {date_value}")
                    return False
            
            logger.debug("[VOITURE SERVICE] Data validation passed")
            return True
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error during validation: {e}")
            return False
    
    def validate_date_format(self, date_string: str) -> bool:
        """Validate date string format (YYYY-MM-DD)."""
        if not date_string.strip():
            return True  # Empty dates are allowed
        
        try:
            datetime.strptime(date_string, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    def compute_age(self, date_str: str) -> str:
        """Compute vehicle age in years from first registration date."""
        try:
            if not date_str or not date_str.strip():
                return ""
            
            dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            now = datetime.now()
            age = now.year - dt.year - ((now.month, now.day) < (dt.month, dt.day))
            
            return str(max(age, 0))
            
        except Exception:
            return ""
    
    def format_date_display(self, iso_date: str) -> str:
        """Convert ISO date (YYYY-MM-DD) to display format (DD/MM/YYYY)."""
        try:
            if not iso_date or not iso_date.strip():
                return ""
            return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return ""
    
    def format_date_iso(self, display_date: str) -> str:
        """Convert display date (DD/MM/YYYY) to ISO format (YYYY-MM-DD)."""
        try:
            if not display_date or not display_date.strip():
                return ""
            return datetime.strptime(display_date, "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            return ""
    
    # ═══════════════════════════════════════════════════════════════
    # Filtering & Reporting
    # ═══════════════════════════════════════════════════════════════
    
    def get_voitures_by_genre(self, genre: str) -> List[Dict[str, Any]]:
        """Get vehicles filtered by genre."""
        try:
            voitures = self.repository.get_voitures_by_genre(genre)
            
            # Add computed fields
            for voiture in voitures:
                voiture['age'] = self.compute_age(voiture.get('date_premiere_mise', ''))
            
            logger.info(f"[VOITURE SERVICE] Retrieved {len(voitures)} vehicles for genre: {genre}")
            return voitures
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error getting vehicles by genre {genre}: {e}")
            return []
    
    def get_voitures_by_user(self, utilisateur: str) -> List[Dict[str, Any]]:
        """Get vehicles filtered by user."""
        try:
            voitures = self.repository.get_voitures_by_user(utilisateur)
            
            # Add computed fields
            for voiture in voitures:
                voiture['age'] = self.compute_age(voiture.get('date_premiere_mise', ''))
            
            logger.info(f"[VOITURE SERVICE] Retrieved {len(voitures)} vehicles for user: {utilisateur}")
            return voitures
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error getting vehicles by user {utilisateur}: {e}")
            return []
    
    def get_upcoming_events(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get vehicles with upcoming maintenance events."""
        try:
            from datetime import datetime, timedelta
            
            voitures = self.get_all_voitures()
            upcoming = []
            
            now = datetime.now()
            cutoff_date = datetime(now.year, now.month, now.day)
            end_date = datetime(now.year, now.month, now.day) + timedelta(days=days_ahead)
            
            for voiture in voitures:
                for date_field in ['date_visite', 'date_assurance', 'date_vignette']:
                    date_value = voiture.get(date_field, '')
                    if date_value:
                        try:
                            event_date = datetime.strptime(date_value, "%Y-%m-%d")
                            if cutoff_date <= event_date <= end_date:
                                upcoming.append({
                                    'matricule': voiture.get('matricule', ''),
                                    'utilisateur': voiture.get('utilisateur', ''),
                                    'event_type': date_field.replace('date_', ''),
                                    'event_date': date_value,
                                    'days_until': (event_date - cutoff_date).days
                                })
                        except ValueError:
                            continue
            
            # Sort by event date
            upcoming.sort(key=lambda x: x['event_date'])
            
            logger.info(f"[VOITURE SERVICE] Found {len(upcoming)} upcoming events in next {days_ahead} days")
            return upcoming
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error getting upcoming events: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vehicle statistics and summary information."""
        try:
            voitures = self.get_all_voitures()
            
            # Basic counts
            total_count = len(voitures)
            
            # Genre breakdown
            genre_counts = {}
            user_counts = {}
            age_groups = {'0-5': 0, '6-10': 0, '11-15': 0, '16+': 0, 'unknown': 0}
            
            for voiture in voitures:
                # Genre stats
                genre = voiture.get('genre', 'unknown')
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
                
                # User stats
                user = voiture.get('utilisateur', 'unknown')
                user_counts[user] = user_counts.get(user, 0) + 1
                
                # Age stats
                age_str = voiture.get('age', '')
                try:
                    age = int(age_str) if age_str else None
                    if age is None:
                        age_groups['unknown'] += 1
                    elif age <= 5:
                        age_groups['0-5'] += 1
                    elif age <= 10:
                        age_groups['6-10'] += 1
                    elif age <= 15:
                        age_groups['11-15'] += 1
                    else:
                        age_groups['16+'] += 1
                except ValueError:
                    age_groups['unknown'] += 1
            
            # Upcoming events
            upcoming_events = self.get_upcoming_events(30)
            
            stats = {
                'total_vehicles': total_count,
                'genre_breakdown': genre_counts,
                'user_breakdown': user_counts,
                'age_breakdown': age_groups,
                'upcoming_events_count': len(upcoming_events),
                'upcoming_events': upcoming_events[:5],  # Top 5 upcoming
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"[VOITURE SERVICE] Generated statistics for {total_count} vehicles")
            return stats
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error generating statistics: {e}")
            return {
                'total_vehicles': 0,
                'genre_breakdown': {},
                'user_breakdown': {},
                'age_breakdown': {},
                'upcoming_events_count': 0,
                'upcoming_events': [],
                'error': str(e)
            }
    
    # ═══════════════════════════════════════════════════════════════
    # UI Support Methods
    # ═══════════════════════════════════════════════════════════════
    
    def get_genre_list(self) -> List[str]:
        """Get list of available vehicle genres."""
        return ["voiture", "partner", "camion", "remorque"]
    
    def get_user_list(self) -> List[str]:
        """Get list of vehicle users for selection."""
        try:
            voitures = self.repository.get_all_voitures()
            users = set()
            
            for voiture in voitures:
                user = voiture.get('utilisateur', '').strip()
                if user:
                    users.add(user)
            
            user_list = sorted(list(users))
            logger.debug(f"[VOITURE SERVICE] Retrieved {len(user_list)} unique users")
            return user_list
            
        except Exception as e:
            logger.error(f"[VOITURE SERVICE] Error getting user list: {e}")
            return []
