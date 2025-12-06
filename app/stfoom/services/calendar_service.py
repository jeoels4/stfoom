"""
Calendar Service Layer - Business Logic for Calendar Events
===========================================================
Handles calendar event operations, validation, and business rules.
"""

from __future__ import annotations
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CalendarService:
    """Service layer for calendar event management with business logic and validation."""
    
    def __init__(self, calendar_repository):
        """Initialize with calendar repository dependency."""
        self.calendar_repository = calendar_repository
        logger.info("[CALENDAR_SERVICE] Initialized with repository dependency")
    
    # ================================ CRUD Operations ================================
    
    def get_all_events(self, categories: Optional[List[str]] = None, 
                      include_past: bool = True, include_done: bool = False) -> List[Dict[str, Any]]:
        """Get all calendar events with filtering options."""
        try:
            logger.debug(f"[CALENDAR_SERVICE] Getting all events: categories={categories}, past={include_past}, done={include_done}")
            events = self.calendar_repository.get_all_events(categories, include_past, include_done)
            
            # Enhance events with computed fields
            enhanced_events = []
            for event in events:
                enhanced_event = self._enhance_event(event)
                enhanced_events.append(enhanced_event)
            
            logger.info(f"[CALENDAR_SERVICE] Retrieved {len(enhanced_events)} events")
            return enhanced_events
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error getting all events: {e}")
            raise
    
    def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Get single event by ID with enhanced data."""
        try:
            event = self.calendar_repository.get_event_by_id(event_id)
            if event:
                return self._enhance_event(event)
            return None
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error getting event {event_id}: {e}")
            raise
    
    def create_event(self, title: str, date_str: str, category: str, 
                    description: str = "", done: int = 0) -> bool:
        """Create new calendar event with validation."""
        try:
            # Validate event data
            validation_result = self.validate_event_data({
                'title': title,
                'date': date_str,
                'category': category,
                'description': description,
                'done': done
            })
            
            if not validation_result['valid']:
                logger.warning(f"[CALENDAR_SERVICE] Invalid event data: {validation_result['errors']}")
                return False
            
            # Check for duplicates
            existing = self.calendar_repository.find_event(date_str, category, title)
            if existing:
                logger.warning(f"[CALENDAR_SERVICE] Event already exists: {title} on {date_str}")
                return False
            
            # Create event
            self.calendar_repository.add_event(title, date_str, category, description, done)
            logger.info(f"[CALENDAR_SERVICE] Created event: {title} on {date_str}")
            return True
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error creating event: {e}")
            raise
    
    def update_event(self, event_id: int, title: str, date_str: str, category: str,
                    description: str, done: int = 0) -> bool:
        """Update existing calendar event with validation."""
        try:
            # Validate event data
            validation_result = self.validate_event_data({
                'title': title,
                'date': date_str,
                'category': category,
                'description': description,
                'done': done
            })
            
            if not validation_result['valid']:
                logger.warning(f"[CALENDAR_SERVICE] Invalid update data: {validation_result['errors']}")
                return False
            
            # Check if event exists
            existing = self.calendar_repository.get_event_by_id(event_id)
            if not existing:
                logger.warning(f"[CALENDAR_SERVICE] Event not found for update: {event_id}")
                return False
            
            # Update event
            self.calendar_repository.update_event(event_id, title, date_str, category, description, done)
            logger.info(f"[CALENDAR_SERVICE] Updated event {event_id}: {title}")
            return True
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error updating event {event_id}: {e}")
            raise
    
    def delete_event(self, event_id: int) -> bool:
        """Delete calendar event by ID."""
        try:
            # Check if event exists
            existing = self.calendar_repository.get_event_by_id(event_id)
            if not existing:
                logger.warning(f"[CALENDAR_SERVICE] Event not found for deletion: {event_id}")
                return False
            
            # Delete event
            self.calendar_repository.delete_event(event_id)
            logger.info(f"[CALENDAR_SERVICE] Deleted event {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error deleting event {event_id}: {e}")
            raise
    
    def find_event(self, date_str: str, category: str, title: str) -> Optional[Dict[str, Any]]:
        """Find calendar event by unique keys."""
        try:
            event = self.calendar_repository.find_event(date_str, category, title)
            if event:
                enhanced_event = self._enhance_event(event)
                logger.debug(f"[CALENDAR_SERVICE] Found event: {title} on {date_str}")
                return enhanced_event
            else:
                logger.warning(f"[CALENDAR_SERVICE] Event not found: {title} on {date_str}")
                return None
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error finding event: {e}")
            raise

    def delete_event_by_keys(self, date_str: str, category: str, title: str) -> bool:
        """Delete calendar event by unique keys."""
        try:
            # Find matching events
            existing = self.calendar_repository.find_event(date_str, category, title)
            if not existing:
                logger.warning(f"[CALENDAR_SERVICE] Event not found for deletion: {title} on {date_str}")
                return False
            
            # Delete event
            self.calendar_repository.delete_event_by_keys(date_str, category, title)
            logger.info(f"[CALENDAR_SERVICE] Deleted event by keys: {title} on {date_str}")
            return True
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error deleting event by keys: {e}")
            raise
    
    # ================================ Business Logic ================================
    
    def get_upcoming_events(self, categories: Optional[List[str]] = None, 
                           show_past: bool = False) -> List[Dict[str, Any]]:
        """Get upcoming events respecting UI toggles (no done events)."""
        try:
            events = self.calendar_repository.get_upcoming_items_dict(categories, show_past)
            
            # Enhance and sort events
            enhanced_events = []
            for event in events:
                enhanced_event = self._enhance_event(event)
                enhanced_events.append(enhanced_event)
            
            # Sort by date and priority
            enhanced_events.sort(key=lambda x: (x['date'], x['priority']))
            
            logger.info(f"[CALENDAR_SERVICE] Retrieved {len(enhanced_events)} upcoming events")
            return enhanced_events
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error getting upcoming events: {e}")
            raise
    
    def get_upcoming_events_formatted(self, categories: Optional[List[str]] = None,
                                    show_past: bool = False) -> List[str]:
        """Get upcoming events as formatted strings for simple display."""
        try:
            events = self.get_upcoming_events(categories, show_past)
            formatted = []
            
            for event in events:
                status = "✓" if event['done'] else "○"
                priority_indicator = self._get_priority_indicator(event['priority'])
                formatted.append(f"{status} {event['formatted_date']} [{event['category']}] {priority_indicator}{event['title']}")
            
            return formatted
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error formatting upcoming events: {e}")
            raise
    
    def get_events_due_tomorrow(self) -> List[Dict[str, Any]]:
        """Get events due tomorrow for notifications."""
        try:
            events = self.calendar_repository.get_events_due_tomorrow()
            
            enhanced_events = []
            for event in events:
                enhanced_event = self._enhance_event(event)
                enhanced_events.append(enhanced_event)
            
            logger.info(f"[CALENDAR_SERVICE] Found {len(enhanced_events)} events due tomorrow")
            return enhanced_events
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error getting tomorrow's events: {e}")
            raise
    
    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Get calendar events that should trigger notifications."""
        try:
            notifications = self.calendar_repository.get_pending_calendar_notifications()
            
            # Enhance notification data
            enhanced_notifications = []
            for notification in notifications:
                enhanced_notification = {
                    **notification,
                    'priority': self._calculate_priority(notification),
                    'formatted_date': self.format_date_display(notification['date']),
                    'urgency_level': self._calculate_urgency(notification['date'])
                }
                enhanced_notifications.append(enhanced_notification)
            
            # Sort by priority and urgency
            enhanced_notifications.sort(key=lambda x: (x['urgency_level'], x['priority']))
            
            logger.info(f"[CALENDAR_SERVICE] Generated {len(enhanced_notifications)} notifications")
            return enhanced_notifications
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error getting notifications: {e}")
            raise
    
    def mark_event_done(self, event_id: int) -> bool:
        """Mark event as completed."""
        try:
            event = self.calendar_repository.get_event_by_id(event_id)
            if not event:
                return False
            
            return self.update_event(
                event_id, event['title'], event['date'], 
                event['category'], event['description'], 1
            )
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error marking event done: {e}")
            raise
    
    def mark_event_pending(self, event_id: int) -> bool:
        """Mark event as pending."""
        try:
            event = self.calendar_repository.get_event_by_id(event_id)
            if not event:
                return False
            
            return self.update_event(
                event_id, event['title'], event['date'],
                event['category'], event['description'], 0
            )
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error marking event pending: {e}")
            raise
    
    # ================================ Filtering & Reporting ================================
    
    def get_events_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all events for specific category."""
        return self.get_all_events(categories=[category], include_past=True, include_done=True)
    
    def get_events_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get events within date range."""
        try:
            all_events = self.get_all_events(include_past=True, include_done=True)
            filtered_events = []
            
            for event in all_events:
                if start_date <= event['date'] <= end_date:
                    filtered_events.append(event)
            
            filtered_events.sort(key=lambda x: x['date'])
            logger.info(f"[CALENDAR_SERVICE] Found {len(filtered_events)} events in range {start_date} to {end_date}")
            return filtered_events
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error filtering by date range: {e}")
            raise
    
    def get_overdue_events(self) -> List[Dict[str, Any]]:
        """Get events that are overdue (past due date and not done)."""
        try:
            today = date.today().isoformat()
            all_events = self.get_all_events(include_past=True, include_done=False)
            
            overdue_events = []
            for event in all_events:
                if event['date'] < today and not event['done']:
                    enhanced_event = self._enhance_event(event)
                    enhanced_event['days_overdue'] = self._calculate_days_overdue(event['date'])
                    overdue_events.append(enhanced_event)
            
            # Sort by days overdue (most overdue first)
            overdue_events.sort(key=lambda x: x['days_overdue'], reverse=True)
            
            logger.info(f"[CALENDAR_SERVICE] Found {len(overdue_events)} overdue events")
            return overdue_events
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error getting overdue events: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive calendar statistics."""
        try:
            all_events = self.get_all_events(include_past=True, include_done=True)
            
            stats = {
                'total_events': len(all_events),
                'completed_events': len([e for e in all_events if e['done']]),
                'pending_events': len([e for e in all_events if not e['done']]),
                'overdue_events': len(self.get_overdue_events()),
                'upcoming_events': len(self.get_upcoming_events()),
                'events_due_tomorrow': len(self.get_events_due_tomorrow())
            }
            
            # Category breakdown
            category_stats = {}
            for event in all_events:
                category = event['category']
                if category not in category_stats:
                    category_stats[category] = {'total': 0, 'completed': 0, 'pending': 0}
                category_stats[category]['total'] += 1
                if event['done']:
                    category_stats[category]['completed'] += 1
                else:
                    category_stats[category]['pending'] += 1
            
            stats['category_breakdown'] = category_stats
            
            # Completion rate
            if stats['total_events'] > 0:
                stats['completion_rate'] = round((stats['completed_events'] / stats['total_events']) * 100, 1)
            else:
                stats['completion_rate'] = 0.0
            
            logger.info(f"[CALENDAR_SERVICE] Generated statistics: {stats['total_events']} total events")
            return stats
            
        except Exception as e:
            logger.error(f"[CALENDAR_SERVICE] Error generating statistics: {e}")
            raise
    
    # ================================ Validation ================================
    
    def validate_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate calendar event data."""
        errors = []
        
        # Required fields
        if not event_data.get('title', '').strip():
            errors.append("Title is required")
        
        if not event_data.get('date', '').strip():
            errors.append("Date is required")
        
        if not event_data.get('category', '').strip():
            errors.append("Category is required")
        
        # Date format validation
        if event_data.get('date'):
            if not self.validate_date_format(event_data['date']):
                errors.append("Date must be in YYYY-MM-DD format")
        
        # Title length
        title = event_data.get('title', '')
        if len(title) > 200:
            errors.append("Title must be 200 characters or less")
        
        # Category validation
        category = event_data.get('category', '')
        valid_categories = self.get_category_list()
        if category and category not in valid_categories:
            errors.append(f"Category must be one of: {', '.join(valid_categories)}")
        
        # Done status validation
        done = event_data.get('done', 0)
        if done not in [0, 1]:
            errors.append("Done status must be 0 (pending) or 1 (completed)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_date_format(self, date_str: str) -> bool:
        """Validate date string format (YYYY-MM-DD)."""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    # ================================ Utilities ================================
    
    def format_date_display(self, date_str: str) -> str:
        """Format date for display in UI."""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%d/%m/%Y')
        except ValueError:
            return date_str
    
    def format_date_iso(self, date_str: str) -> str:
        """Ensure date is in ISO format."""
        try:
            # Try parsing common formats
            formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            return date_str
        except Exception:
            return date_str
    
    def get_category_list(self) -> List[str]:
        """Get list of available categories."""
        return ["Cars", "Paiement", "Facturation", "Other"]
    
    def _enhance_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance event with computed fields."""
        enhanced = event.copy()
        
        # Get date field (support both old and new schema)
        event_date = event.get('start_date') or event.get('date', '')
        event_category = event.get('event_type') or event.get('category', 'Other')
        
        # Add formatted date
        enhanced['formatted_date'] = self.format_date_display(event_date)
        enhanced['date'] = event_date  # Add for backward compatibility
        enhanced['category'] = event_category  # Add for backward compatibility
        
        # Calculate priority based on date and category
        enhanced['priority'] = self._calculate_priority(enhanced)
        
        # Calculate days until/since event
        enhanced['days_until'] = self._calculate_days_until(event_date)
        
        # Add urgency level
        enhanced['urgency_level'] = self._calculate_urgency(event_date)
        
        return enhanced
    
    def _calculate_priority(self, event: Dict[str, Any]) -> int:
        """Calculate event priority (1=highest, 5=lowest)."""
        try:
            # Base priority by category
            category_priority = {
                "Cars": 2,
                "Paiement": 1,
                "Facturation": 1,
                "Other": 3
            }
            
            base_priority = category_priority.get(event['category'], 3)
            
            # Adjust based on date proximity
            days_until = self._calculate_days_until(event['date'])
            
            if days_until < 0:  # Overdue
                return 1
            elif days_until <= 1:  # Due tomorrow or today
                return max(1, base_priority - 1)
            elif days_until <= 7:  # Due this week
                return base_priority
            else:  # Future
                return min(5, base_priority + 1)
                
        except Exception:
            return 3
    
    def _calculate_days_until(self, event_date: str) -> int:
        """Calculate days until event (negative if overdue)."""
        try:
            event_date_obj = datetime.strptime(event_date, '%Y-%m-%d').date()
            today = date.today()
            return (event_date_obj - today).days
        except Exception:
            return 0
    
    def _calculate_days_overdue(self, event_date: str) -> int:
        """Calculate days overdue (positive number)."""
        days_until = self._calculate_days_until(event_date)
        return abs(days_until) if days_until < 0 else 0
    
    def _calculate_urgency(self, event_date: str) -> int:
        """Calculate urgency level (1=most urgent, 5=least urgent)."""
        days_until = self._calculate_days_until(event_date)
        
        if days_until < 0:  # Overdue
            return 1
        elif days_until == 0:  # Due today
            return 2
        elif days_until == 1:  # Due tomorrow
            return 3
        elif days_until <= 7:  # Due this week
            return 4
        else:  # Future
            return 5
    
    def _get_priority_indicator(self, priority: int) -> str:
        """Get visual indicator for priority."""
        indicators = {
            1: "🔴 ",  # High priority
            2: "🟡 ",  # Medium-high priority
            3: "🟢 ",  # Normal priority
            4: "🔵 ",  # Low priority
            5: "⚪ "   # Very low priority
        }
        return indicators.get(priority, "🟢 ")
