"""
Enhanced Detailed Activity Logger Service for STFOOM
====================================================
Comprehensive logging system that captures every single user action with maximum detail.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
import json
import threading
import traceback
import inspect
import platform
import psutil
import uuid


class DetailedActivityLogger:
    """
    Ultra-detailed activity logger that captures:
    - Complete user context (ID, name, rank, session, IP)
    - Full action details (operation, parameters, before/after states)
    - System context (timestamp, execution time, memory usage, CPU)
    - Error details (stack traces, error codes, recovery attempts)
    - Data context (record IDs, values changed, relationships affected)
    - Business context (module, feature, workflow step)
    """
    
    def __init__(self, db_path: str = "data/detailed_activity.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.current_user = None
        self.current_session = None
        self.session_id = str(uuid.uuid4())
        
        # System information
        self.hostname = platform.node()
        self.platform = platform.platform()
        self.python_version = platform.python_version()
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize the detailed activity database with comprehensive schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Main activity log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS detailed_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- Timestamp information
                    timestamp TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    timezone TEXT,
                    
                    -- User context
                    user_id TEXT NOT NULL,
                    user_name TEXT,
                    user_rank TEXT,
                    user_email TEXT,
                    session_id TEXT,
                    
                    -- Network context
                    ip_address TEXT,
                    user_agent TEXT,
                    hostname TEXT,
                    
                    -- Action identification
                    action_type TEXT NOT NULL,
                    action_category TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    action_description TEXT,
                    
                    -- Module/Feature context
                    module_name TEXT NOT NULL,
                    feature_name TEXT,
                    page_name TEXT,
                    component_name TEXT,
                    
                    -- Data context
                    resource_type TEXT,
                    resource_id TEXT,
                    parent_resource_type TEXT,
                    parent_resource_id TEXT,
                    
                    -- Operation details
                    operation_method TEXT,
                    operation_parameters TEXT,
                    
                    -- State information
                    before_state TEXT,
                    after_state TEXT,
                    changes_made TEXT,
                    affected_records INTEGER DEFAULT 0,
                    
                    -- Execution context
                    execution_time_ms INTEGER,
                    memory_usage_mb REAL,
                    cpu_usage_percent REAL,
                    
                    -- Result information
                    result_status TEXT NOT NULL DEFAULT 'success',
                    result_message TEXT,
                    result_data TEXT,
                    
                    -- Error information
                    error_type TEXT,
                    error_message TEXT,
                    error_code TEXT,
                    error_stack_trace TEXT,
                    error_recovery_action TEXT,
                    
                    -- Business context
                    workflow_step TEXT,
                    business_impact TEXT,
                    compliance_notes TEXT,
                    
                    -- Additional metadata
                    additional_context TEXT,
                    tags TEXT,
                    priority_level TEXT DEFAULT 'normal',
                    
                    -- System tracking
                    created_at TEXT DEFAULT (datetime('now')),
                    application_version TEXT,
                    database_version TEXT
                )
            """)
            
            # User sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    activities_count INTEGER DEFAULT 0,
                    last_activity_time TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Data change history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_change_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_id INTEGER,
                    table_name TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    change_type TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (activity_id) REFERENCES detailed_activities (id)
                )
            """)
            
            # System events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_category TEXT,
                    event_description TEXT,
                    severity_level TEXT DEFAULT 'info',
                    system_component TEXT,
                    additional_data TEXT,
                    user_id TEXT,
                    session_id TEXT
                )
            """)
            
            # Performance metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    unit TEXT,
                    context TEXT,
                    user_id TEXT,
                    session_id TEXT
                )
            """)
            
            # Create comprehensive indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_detailed_timestamp ON detailed_activities(timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_detailed_user ON detailed_activities(user_id, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_detailed_action ON detailed_activities(action_type, action_name)",
                "CREATE INDEX IF NOT EXISTS idx_detailed_module ON detailed_activities(module_name, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_detailed_resource ON detailed_activities(resource_type, resource_id)",
                "CREATE INDEX IF NOT EXISTS idx_detailed_session ON detailed_activities(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_detailed_status ON detailed_activities(result_status)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id, start_time DESC)",
                "CREATE INDEX IF NOT EXISTS idx_changes_activity ON data_change_history(activity_id)",
                "CREATE INDEX IF NOT EXISTS idx_changes_record ON data_change_history(table_name, record_id)",
                "CREATE INDEX IF NOT EXISTS idx_system_events ON system_events(timestamp DESC, event_type)",
                "CREATE INDEX IF NOT EXISTS idx_performance ON performance_metrics(timestamp DESC, metric_type)"
            ]
            
            for index in indexes:
                conn.execute(index)
    
    def set_user_session(self, user_id: str, user_name: str = None, user_rank: str = None, 
                          user_email: str = None, ip_address: str = "127.0.0.1", user_agent: str = None):
        """Start a new user session with full context"""
        self.current_user = {
            'user_id': user_id,
            'user_name': user_name or user_id,
            'user_rank': user_rank or 'user',
            'user_email': user_email,
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        
        self.session_id = str(uuid.uuid4())
        
        # Record session start
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO user_sessions 
                (session_id, user_id, start_time, ip_address, user_agent, status)
                VALUES (?, ?, ?, ?, ?, 'active')
            """, (self.session_id, user_id, datetime.now().isoformat(), ip_address, user_agent))
        
        # Log login activity
        self.log_detailed_activity(
            action_type="authentication",
            action_category="user_management", 
            action_name="user_login",
            action_description=f"User {user_name or user_id} logged into the system",
            module_name="authentication",
            feature_name="login",
            operation_method="login",
            business_impact="User session started",
            priority_level="high"
        )
    
    def end_user_session(self):
        """End the current user session"""
        if self.current_user and self.session_id:
            # Log logout
            self.log_detailed_activity(
                action_type="authentication",
                action_category="user_management",
                action_name="user_logout",
                action_description=f"User {self.current_user.get('user_name', 'Unknown')} logged out",
                module_name="authentication",
                feature_name="logout",
                business_impact="User session ended",
                priority_level="high"
            )
            
            # Update session record
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE user_sessions 
                    SET end_time = ?, status = 'ended'
                    WHERE session_id = ?
                """, (datetime.now().isoformat(), self.session_id))
        
        self.current_user = None
        self.session_id = None
    
    def log_detailed_activity(
        self,
        action_type: str,
        action_category: str,
        action_name: str,
        action_description: str = None,
        module_name: str = "system",
        feature_name: str = None,
        page_name: str = None,
        component_name: str = None,
        resource_type: str = None,
        resource_id: str = None,
        parent_resource_type: str = None,
        parent_resource_id: str = None,
        operation_method: str = None,
        operation_parameters: Dict[str, Any] = None,
        before_state: Dict[str, Any] = None,
        after_state: Dict[str, Any] = None,
        changes_made: List[Dict[str, Any]] = None,
        affected_records: int = 0,
        result_status: str = "success",
        result_message: str = None,
        result_data: Dict[str, Any] = None,
        error_details: Dict[str, Any] = None,
        workflow_step: str = None,
        business_impact: str = None,
        compliance_notes: str = None,
        additional_context: Dict[str, Any] = None,
        tags: List[str] = None,
        priority_level: str = "normal",
        execution_time_ms: int = None,
        capture_system_metrics: bool = True
    ) -> int:
        """
        Log a detailed activity with comprehensive information
        
        Returns:
            activity_id: The ID of the logged activity
        """
        if not self.current_user:
            return 0  # No user session active
        
        timestamp = datetime.now()
        
        # System metrics
        memory_usage = 0
        cpu_usage = 0
        if capture_system_metrics:
            try:
                process = psutil.Process()
                memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                cpu_usage = process.cpu_percent()
            except:
                pass
        
        # Get caller information for better context
        caller_frame = inspect.currentframe().f_back
        caller_info = {
            'filename': caller_frame.f_code.co_filename,
            'function': caller_frame.f_code.co_name,
            'line_number': caller_frame.f_lineno
        } if caller_frame else {}
        
        # Prepare data for insertion
        activity_data = {
            'timestamp': timestamp.isoformat(),
            'date': timestamp.date().isoformat(),
            'time': timestamp.time().isoformat(),
            'timezone': str(timestamp.astimezone().tzinfo),
            
            'user_id': self.current_user['user_id'],
            'user_name': self.current_user['user_name'],
            'user_rank': self.current_user['user_rank'],
            'user_email': self.current_user.get('user_email'),
            'session_id': self.session_id,
            
            'ip_address': self.current_user.get('ip_address', '127.0.0.1'),
            'user_agent': self.current_user.get('user_agent'),
            'hostname': self.hostname,
            
            'action_type': action_type,
            'action_category': action_category,
            'action_name': action_name,
            'action_description': action_description or f"{action_category}.{action_name}",
            
            'module_name': module_name,
            'feature_name': feature_name,
            'page_name': page_name,
            'component_name': component_name,
            
            'resource_type': resource_type,
            'resource_id': str(resource_id) if resource_id else None,
            'parent_resource_type': parent_resource_type,
            'parent_resource_id': str(parent_resource_id) if parent_resource_id else None,
            
            'operation_method': operation_method,
            'operation_parameters': json.dumps(operation_parameters, ensure_ascii=False) if operation_parameters else None,
            
            'before_state': json.dumps(before_state, ensure_ascii=False) if before_state else None,
            'after_state': json.dumps(after_state, ensure_ascii=False) if after_state else None,
            'changes_made': json.dumps(changes_made, ensure_ascii=False) if changes_made else None,
            'affected_records': affected_records,
            
            'execution_time_ms': execution_time_ms,
            'memory_usage_mb': memory_usage,
            'cpu_usage_percent': cpu_usage,
            
            'result_status': result_status,
            'result_message': result_message,
            'result_data': json.dumps(result_data, ensure_ascii=False) if result_data else None,
            
            'workflow_step': workflow_step,
            'business_impact': business_impact,
            'compliance_notes': compliance_notes,
            
            'additional_context': json.dumps({
                **caller_info,
                **(additional_context or {})
            }, ensure_ascii=False),
            
            'tags': json.dumps(tags) if tags else None,
            'priority_level': priority_level,
            'application_version': "1.0.0",  # You can make this dynamic
            'database_version': "1.0.0"
        }
        
        # Handle error details
        if error_details:
            activity_data.update({
                'error_type': error_details.get('error_type'),
                'error_message': error_details.get('error_message'),
                'error_code': error_details.get('error_code'),
                'error_stack_trace': error_details.get('stack_trace'),
                'error_recovery_action': error_details.get('recovery_action')
            })
        
        activity_id = 0
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        INSERT INTO detailed_activities 
                        (timestamp, date, time, timezone, user_id, user_name, user_rank, user_email, session_id,
                         ip_address, user_agent, hostname, action_type, action_category, action_name, action_description,
                         module_name, feature_name, page_name, component_name, resource_type, resource_id,
                         parent_resource_type, parent_resource_id, operation_method, operation_parameters,
                         before_state, after_state, changes_made, affected_records, execution_time_ms,
                         memory_usage_mb, cpu_usage_percent, result_status, result_message, result_data,
                         error_type, error_message, error_code, error_stack_trace, error_recovery_action,
                         workflow_step, business_impact, compliance_notes, additional_context, tags,
                         priority_level, application_version, database_version)
                        VALUES 
                        (:timestamp, :date, :time, :timezone, :user_id, :user_name, :user_rank, :user_email, :session_id,
                         :ip_address, :user_agent, :hostname, :action_type, :action_category, :action_name, :action_description,
                         :module_name, :feature_name, :page_name, :component_name, :resource_type, :resource_id,
                         :parent_resource_type, :parent_resource_id, :operation_method, :operation_parameters,
                         :before_state, :after_state, :changes_made, :affected_records, :execution_time_ms,
                         :memory_usage_mb, :cpu_usage_percent, :result_status, :result_message, :result_data,
                         :error_type, :error_message, :error_code, :error_stack_trace, :error_recovery_action,
                         :workflow_step, :business_impact, :compliance_notes, :additional_context, :tags,
                         :priority_level, :application_version, :database_version)
                    """, activity_data)
                    activity_id = cursor.lastrowid
                    
                    # Update session activity count
                    conn.execute("""
                        UPDATE user_sessions 
                        SET activities_count = activities_count + 1, last_activity_time = ?
                        WHERE session_id = ?
                    """, (timestamp.isoformat(), self.session_id))
                
                # Log data changes if provided
                if changes_made and activity_id:
                    self._log_data_changes(activity_id, changes_made)
                
            except Exception as e:
                # Fallback logging
                self._fallback_log(activity_data, str(e))
        
        return activity_id
    
    def _log_data_changes(self, activity_id: int, changes: List[Dict[str, Any]]):
        """Log detailed data changes"""
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            for change in changes:
                conn.execute("""
                    INSERT INTO data_change_history
                    (activity_id, table_name, record_id, field_name, old_value, new_value, change_type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    activity_id,
                    change.get('table_name'),
                    change.get('record_id'),
                    change.get('field_name'),
                    json.dumps(change.get('old_value'), ensure_ascii=False) if change.get('old_value') is not None else None,
                    json.dumps(change.get('new_value'), ensure_ascii=False) if change.get('new_value') is not None else None,
                    change.get('change_type', 'update'),
                    timestamp
                ))
    
    def log_system_event(self, event_type: str, event_category: str = "system",
                        event_description: str = None, severity_level: str = "info",
                        system_component: str = None, additional_data: Dict[str, Any] = None):
        """Log system-level events"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO system_events
                (timestamp, event_type, event_category, event_description, severity_level,
                 system_component, additional_data, user_id, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                event_type,
                event_category,
                event_description,
                severity_level,
                system_component,
                json.dumps(additional_data, ensure_ascii=False) if additional_data else None,
                self.current_user['user_id'] if self.current_user else None,
                self.session_id
            ))
    
    def log_performance_metric(self, metric_type: str, metric_name: str, metric_value: float,
                              unit: str = None, context: str = None):
        """Log performance metrics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO performance_metrics
                (timestamp, metric_type, metric_name, metric_value, unit, context, user_id, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                metric_type,
                metric_name,
                metric_value,
                unit,
                context,
                self.current_user['user_id'] if self.current_user else None,
                self.session_id
            ))
    
    def _fallback_log(self, activity_data: Dict[str, Any], error: str):
        """Fallback logging when database fails"""
        try:
            log_file = "data/detailed_activity_fallback.log"
            with open(log_file, "a", encoding="utf-8") as f:
                log_entry = {
                    'timestamp': activity_data.get('timestamp'),
                    'user_id': activity_data.get('user_id'),
                    'action': f"{activity_data.get('module_name')}.{activity_data.get('action_name')}",
                    'description': activity_data.get('action_description'),
                    'error': f"DB_ERROR: {error}"
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # Last resort - ignore if we can't write to fallback
    
    def get_detailed_activities(self, filters: Dict[str, Any] = None, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """Get detailed activities with advanced filtering"""
        query = "SELECT * FROM detailed_activities WHERE 1=1"
        params = []
        
        if filters:
            if filters.get('user_id'):
                query += " AND user_id = ?"
                params.append(filters['user_id'])
            
            if filters.get('action_type'):
                query += " AND action_type = ?"
                params.append(filters['action_type'])
            
            if filters.get('module_name'):
                query += " AND module_name = ?"
                params.append(filters['module_name'])
            
            if filters.get('result_status'):
                query += " AND result_status = ?"
                params.append(filters['result_status'])
            
            if filters.get('date_from'):
                query += " AND date >= ?"
                params.append(filters['date_from'])
            
            if filters.get('date_to'):
                query += " AND date <= ?"
                params.append(filters['date_to'])
            
            if filters.get('search'):
                query += " AND (action_description LIKE ? OR result_message LIKE ? OR additional_context LIKE ?)"
                search_term = f"%{filters['search']}%"
                params.extend([search_term, search_term, search_term])
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                activities = []
                for row in rows:
                    activity = dict(row)
                    
                    # Parse JSON fields
                    for json_field in ['operation_parameters', 'before_state', 'after_state', 'changes_made', 
                                     'result_data', 'additional_context', 'tags']:
                        if activity.get(json_field):
                            try:
                                activity[json_field] = json.loads(activity[json_field])
                            except json.JSONDecodeError:
                                pass
                    
                    activities.append(activity)
                
                return activities
        except Exception as e:
            print(f"Error retrieving detailed activities: {e}")
            return []


# Global instance
detailed_logger = DetailedActivityLogger()


# Convenience functions for comprehensive logging

def log_page_navigation(page_name: str, from_page: str = None, navigation_method: str = "menu"):
    """Log page navigation with full context"""
    detailed_logger.log_detailed_activity(
        action_type="navigation",
        action_category="ui_interaction",
        action_name="page_access",
        action_description=f"Navigated to {page_name} page" + (f" from {from_page}" if from_page else ""),
        module_name="navigation",
        feature_name="page_navigation",
        page_name=page_name,
        operation_method=navigation_method,
        additional_context={"from_page": from_page} if from_page else None,
        business_impact="User accessed new functionality",
        priority_level="normal"
    )

def log_database_operation(operation: str, table_name: str, record_id: str = None, 
                          before_data: Dict = None, after_data: Dict = None,
                          affected_count: int = 1, execution_time: int = None):
    """Log database operations with before/after states"""
    changes_made = []
    if before_data and after_data:
        for field, new_value in after_data.items():
            old_value = before_data.get(field)
            if old_value != new_value:
                changes_made.append({
                    'table_name': table_name,
                    'record_id': record_id,
                    'field_name': field,
                    'old_value': old_value,
                    'new_value': new_value,
                    'change_type': 'update'
                })
    
    detailed_logger.log_detailed_activity(
        action_type="database",
        action_category="data_operation",
        action_name=f"db_{operation}",
        action_description=f"{operation.title()} operation on {table_name}" + (f" (ID: {record_id})" if record_id else ""),
        module_name="database",
        resource_type=table_name,
        resource_id=record_id,
        operation_method=operation,
        before_state=before_data,
        after_state=after_data,
        changes_made=changes_made,
        affected_records=affected_count,
        execution_time_ms=execution_time,
        business_impact=f"Data {operation} completed",
        priority_level="high" if operation in ["create", "update", "delete"] else "normal"
    )

def log_ui_interaction(component_name: str, action: str, page_name: str = None,
                      interaction_data: Dict = None, result: str = "success"):
    """Log UI interactions (button clicks, form submissions, etc.)"""
    detailed_logger.log_detailed_activity(
        action_type="ui_interaction",
        action_category="user_input",
        action_name=f"ui_{action}",
        action_description=f"User {action} on {component_name}",
        module_name="ui",
        feature_name="user_interface",
        page_name=page_name,
        component_name=component_name,
        operation_method=action,
        operation_parameters=interaction_data,
        result_status=result,
        business_impact="User interacted with interface",
        priority_level="low"
    )

def log_business_operation(module: str, operation: str, resource_type: str = None,
                          resource_id: str = None, details: str = None,
                          before_state: Dict = None, after_state: Dict = None,
                          workflow_step: str = None, business_impact: str = None):
    """Log business operations (sales, purchases, invoicing, etc.)"""
    detailed_logger.log_detailed_activity(
        action_type="business_operation",
        action_category=module,
        action_name=operation,
        action_description=details or f"{operation} in {module} module",
        module_name=module,
        resource_type=resource_type,
        resource_id=resource_id,
        before_state=before_state,
        after_state=after_state,
        workflow_step=workflow_step,
        business_impact=business_impact or f"{operation} operation completed",
        priority_level="high"
    )

def log_error_with_context(module: str, operation: str, error: Exception, context: Dict = None,
                          recovery_action: str = None):
    """Log errors with full context and stack traces"""
    error_details = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'stack_trace': traceback.format_exc(),
        'recovery_action': recovery_action
    }
    
    detailed_logger.log_detailed_activity(
        action_type="error",
        action_category="system_error",
        action_name=f"error_{operation}",
        action_description=f"Error during {operation} in {module}",
        module_name=module,
        operation_method=operation,
        result_status="error",
        result_message=str(error),
        error_details=error_details,
        additional_context=context,
        business_impact="Operation failed - user may need assistance",
        priority_level="critical"
    )

def log_security_event(event_type: str, details: str, severity: str = "medium",
                      additional_context: Dict = None):
    """Log security-related events"""
    detailed_logger.log_detailed_activity(
        action_type="security",
        action_category="security_event",
        action_name=event_type,
        action_description=details,
        module_name="security",
        additional_context=additional_context,
        business_impact="Security event recorded",
        priority_level="critical" if severity == "high" else "high" if severity == "medium" else "normal"
    )