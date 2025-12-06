"""
User Log Page for STFOOM
========================
Display activity logs of all users showing who did what work, when, and how.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sqlite3
import os
import sys

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services'))

class UserLogPage(ttk.Frame):
    """User activity log viewer with filtering and search capabilities"""
    
    def __init__(self, parent, go_home):
        super().__init__(parent)
        self.go_home = go_home
        self.pack(fill="both", expand=True)
        
        # Filter variables
        self.filter_user_var = tk.StringVar(value="Tous")
        self.filter_action_var = tk.StringVar(value="Toutes")
        self.filter_date_from_var = tk.StringVar()
        self.filter_date_to_var = tk.StringVar()
        self.search_var = tk.StringVar()
        
        # Set default date range (last 30 days)
        today = datetime.now()
        last_month = today - timedelta(days=30)
        self.filter_date_from_var.set(last_month.strftime("%d/%m/%Y"))
        self.filter_date_to_var.set(today.strftime("%d/%m/%Y"))
        
        self.setup_ui()
        self.load_logs()
        
        # Auto-refresh every 30 seconds
        self.auto_refresh()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Button(
            header_frame, 
            text="⬅️ Retour", 
            command=self.go_home
        ).pack(side="left")
        
        ttk.Label(
            header_frame, 
            text="📋 Journal des Utilisateurs", 
            font=("Segoe UI", 18, "bold")
        ).pack(side="left", padx=20)
        
        # Refresh button
        ttk.Button(
            header_frame,
            text="🔄 Actualiser",
            command=self.load_logs
        ).pack(side="right")
        
        # Stats frame
        self.create_stats_frame()
        
        # Filters
        self.create_filters_frame()
        
        # Log table
        self.create_log_table()
        
        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        self.status_label = ttk.Label(status_frame, text="Prêt")
        self.status_label.pack(side="left")
        
        self.count_label = ttk.Label(status_frame, text="")
        self.count_label.pack(side="right")
    
    def create_stats_frame(self):
        """Create statistics display frame"""
        stats_frame = ttk.LabelFrame(self, text="📊 Statistiques Rapides", padding=10)
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        # Stats grid
        self.stats_today_var = tk.StringVar(value="0")
        self.stats_week_var = tk.StringVar(value="0")
        self.stats_active_users_var = tk.StringVar(value="0")
        self.stats_total_actions_var = tk.StringVar(value="0")
        
        ttk.Label(stats_frame, text="Aujourd'hui:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Label(stats_frame, textvariable=self.stats_today_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        ttk.Label(stats_frame, text="Cette semaine:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        ttk.Label(stats_frame, textvariable=self.stats_week_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=3, sticky="w", padx=(0, 20))
        
        ttk.Label(stats_frame, text="Utilisateurs actifs:").grid(row=0, column=4, sticky="w", padx=(0, 5))
        ttk.Label(stats_frame, textvariable=self.stats_active_users_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=5, sticky="w", padx=(0, 20))
        
        ttk.Label(stats_frame, text="Actions totales:").grid(row=0, column=6, sticky="w", padx=(0, 5))
        ttk.Label(stats_frame, textvariable=self.stats_total_actions_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=7, sticky="w")
    
    def create_filters_frame(self):
        """Create filters section"""
        filters_frame = ttk.LabelFrame(self, text="🔍 Filtres", padding=10)
        filters_frame.pack(fill="x", padx=20, pady=10)
        
        # Row 1: User, Action, Search
        row1 = ttk.Frame(filters_frame)
        row1.pack(fill="x", pady=(0, 5))
        
        # User filter
        ttk.Label(row1, text="Utilisateur:").pack(side="left")
        user_combo = ttk.Combobox(row1, textvariable=self.filter_user_var, width=15)
        user_combo.pack(side="left", padx=(5, 20))
        user_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        
        # Action filter
        ttk.Label(row1, text="Action:").pack(side="left")
        action_combo = ttk.Combobox(row1, textvariable=self.filter_action_var, width=15)
        action_combo.pack(side="left", padx=(5, 20))
        action_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        
        # Search
        ttk.Label(row1, text="Recherche:").pack(side="left")
        search_entry = ttk.Entry(row1, textvariable=self.search_var, width=20)
        search_entry.pack(side="left", padx=(5, 10))
        search_entry.bind('<KeyRelease>', lambda e: self.apply_filters())
        
        ttk.Button(row1, text="🗑️ Effacer", command=self.clear_filters).pack(side="right")
        
        # Row 2: Date range
        row2 = ttk.Frame(filters_frame)
        row2.pack(fill="x")
        
        ttk.Label(row2, text="De:").pack(side="left")
        date_from_entry = ttk.Entry(row2, textvariable=self.filter_date_from_var, width=10)
        date_from_entry.pack(side="left", padx=(5, 20))
        date_from_entry.bind('<FocusOut>', lambda e: self.apply_filters())
        
        ttk.Label(row2, text="À:").pack(side="left")
        date_to_entry = ttk.Entry(row2, textvariable=self.filter_date_to_var, width=10)
        date_to_entry.pack(side="left", padx=(5, 20))
        date_to_entry.bind('<FocusOut>', lambda e: self.apply_filters())
        
        ttk.Button(row2, text="📅 Aujourd'hui", command=self.set_today_filter).pack(side="left", padx=(0, 5))
        ttk.Button(row2, text="📅 Cette semaine", command=self.set_week_filter).pack(side="left", padx=(0, 5))
        ttk.Button(row2, text="📅 Ce mois", command=self.set_month_filter).pack(side="left", padx=(0, 5))
        
        # Store comboboxes for updating
        self.user_combo = user_combo
        self.action_combo = action_combo
    
    def create_log_table(self):
        """Create the log display table"""
        table_frame = ttk.LabelFrame(self, text="📜 Journal d'Activité", padding=10)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create treeview with columns
        columns = ("datetime", "user", "action", "module", "details", "ip", "result")
        self.log_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        self.log_tree.heading("datetime", text="Date/Heure")
        self.log_tree.heading("user", text="Utilisateur")
        self.log_tree.heading("action", text="Action")
        self.log_tree.heading("module", text="Module")
        self.log_tree.heading("details", text="Détails")
        self.log_tree.heading("ip", text="IP")
        self.log_tree.heading("result", text="Résultat")
        
        # Configure column widths
        self.log_tree.column("datetime", width=120, anchor="center")
        self.log_tree.column("user", width=100, anchor="center")
        self.log_tree.column("action", width=120)
        self.log_tree.column("module", width=100, anchor="center")
        self.log_tree.column("details", width=300)
        self.log_tree.column("ip", width=100, anchor="center")
        self.log_tree.column("result", width=80, anchor="center")
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.log_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.log_tree.xview)
        self.log_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack tree and scrollbars
        self.log_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Configure row colors for different result types
        self.log_tree.tag_configure('success', background='#e8f5e8')
        self.log_tree.tag_configure('error', background='#ffebee')
        self.log_tree.tag_configure('warning', background='#fff9c4')
        
        # Bind double-click for details
        self.log_tree.bind("<Double-1>", self.show_log_details)
    
    def load_logs(self):
        """Load user activity logs from database"""
        self.status_label.config(text="Chargement des logs...")
        
        try:
            logs = self.get_user_logs()
            self.populate_log_table(logs)
            self.update_stats(logs)
            self.update_filter_options(logs)
            self.status_label.config(text="Logs chargés avec succès")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des logs: {e}")
            self.status_label.config(text="Erreur de chargement")
    
    def get_user_logs(self) -> List[Dict]:
        """Get user activity logs from various sources including detailed logs"""
        logs = []
        
        # Get detailed logs from enhanced logging system (PRIMARY SOURCE)
        try:
            from app.stfoom.services.detailed_activity_service import detailed_logger
            
            # Get detailed activities with comprehensive information
            detailed_activities = detailed_logger.get_detailed_activities(limit=1000)
            
            # Convert detailed activities to display format
            for activity in detailed_activities:
                # Create rich log entry with all details
                details_parts = []
                
                # Base description
                if activity.get('action_description'):
                    details_parts.append(activity['action_description'])
                
                # Add resource information
                if activity.get('resource_type') and activity.get('resource_id'):
                    details_parts.append(f"Resource: {activity['resource_type']} (ID: {activity['resource_id']})")
                
                # Add execution details
                if activity.get('execution_time_ms'):
                    details_parts.append(f"Execution: {activity['execution_time_ms']}ms")
                
                # Add memory/CPU usage
                if activity.get('memory_usage_mb'):
                    details_parts.append(f"Memory: {activity['memory_usage_mb']:.1f}MB")
                if activity.get('cpu_usage_percent'):
                    details_parts.append(f"CPU: {activity['cpu_usage_percent']:.1f}%")
                
                # Add business impact
                if activity.get('business_impact'):
                    details_parts.append(f"Impact: {activity['business_impact']}")
                
                # Add workflow information
                if activity.get('workflow_step'):
                    details_parts.append(f"Step: {activity['workflow_step']}")
                
                # Add feature/component information
                feature_parts = []
                if activity.get('feature_name'):
                    feature_parts.append(activity['feature_name'])
                if activity.get('page_name'):
                    feature_parts.append(f"page:{activity['page_name']}")
                if activity.get('component_name'):
                    feature_parts.append(f"component:{activity['component_name']}")
                
                if feature_parts:
                    details_parts.append(f"Context: {' > '.join(feature_parts)}")
                
                # Add error information if present
                if activity.get('error_message'):
                    details_parts.append(f"ERROR: {activity['error_message']}")
                
                # Add operation parameters if present
                if activity.get('operation_parameters'):
                    params = activity['operation_parameters']
                    if isinstance(params, dict):
                        param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
                        details_parts.append(f"Parameters: {param_str}")
                
                # Add before/after state changes
                if activity.get('changes_made'):
                    changes = activity['changes_made']
                    if isinstance(changes, list) and changes:
                        changes_count = len(changes)
                        details_parts.append(f"Changes: {changes_count} field(s) modified")
                
                # Combine all details
                combined_details = " | ".join(details_parts)
                
                # Determine priority-based result status
                result_status = activity.get('result_status', 'Success').title()
                priority = activity.get('priority_level', 'normal')
                if priority == 'critical':
                    result_status += " (Critical)"
                elif priority == 'high':
                    result_status += " (High)"
                
                logs.append({
                    'datetime': activity.get('timestamp', ''),
                    'user': f"{activity.get('user_name', activity.get('user_id', 'Unknown'))} ({activity.get('user_rank', 'N/A')})",
                    'action': f"{activity.get('action_category', 'N/A')}.{activity.get('action_name', 'N/A')}",
                    'module': activity.get('module_name', 'System'),
                    'details': combined_details,
                    'ip': activity.get('ip_address', 'N/A'),
                    'result': result_status,
                    '_raw_activity': activity  # Keep raw data for detail view
                })
                
        except Exception as e:
            print(f"Error loading detailed activity logs: {e}")
        
        # Get logs from old activity logger service (BACKUP SOURCE)
        try:
            from app.stfoom.services.user_activity_service import activity_logger
            
            # Get activities from the old database
            activities = activity_logger.get_activities(limit=500)
            
            # Convert to log format (only if we don't have detailed logs)
            for activity in activities:
                # Check if we already have this log from detailed system
                timestamp = activity.get('timestamp', '')
                user_id = activity.get('user_id', '')
                action = activity.get('action', '')
                
                # Simple duplicate detection
                duplicate_found = any(
                    log['datetime'].startswith(timestamp[:16]) and 
                    user_id in log['user'] and 
                    action in log['action']
                    for log in logs
                )
                
                if not duplicate_found:
                    logs.append({
                        'datetime': timestamp,
                        'user': activity.get('user_id', 'Unknown'),
                        'action': activity.get('action', 'N/A'),
                        'module': activity.get('module', 'System'),
                        'details': activity.get('details', 'N/A'),
                        'ip': activity.get('ip_address', 'N/A'),
                        'result': activity.get('result', 'Info').title(),
                        '_raw_activity': activity
                    })
        except Exception as e:
            print(f"Error loading old activity logs: {e}")
            # Fallback to file-based logs
            logs.extend(self.get_fallback_logs())
        
        # Get logs from security.log
        security_logs = self.get_security_logs()
        logs.extend(security_logs)
        
        # Get logs from application logs
        app_logs = self.get_application_logs()
        logs.extend(app_logs)
        
        # Sort by datetime (newest first)
        logs.sort(key=lambda x: x.get('datetime', ''), reverse=True)
        
        return logs
    
    def get_fallback_logs(self) -> List[Dict]:
        """Get logs from fallback activity log file"""
        logs = []
        fallback_file = "data/activity_fallback.log"
        
        if os.path.exists(fallback_file):
            try:
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            # Parse fallback log format
                            try:
                                parts = line.strip().split(' - ')
                                if len(parts) >= 4:
                                    logs.append({
                                        'datetime': parts[0],
                                        'user': parts[1],
                                        'action': parts[2].split('.')[-1] if '.' in parts[2] else parts[2],
                                        'module': parts[2].split('.')[0] if '.' in parts[2] else 'System',
                                        'details': ' - '.join(parts[3:]),
                                        'ip': 'N/A',
                                        'result': 'Info'
                                    })
                            except:
                                continue
            except Exception as e:
                print(f"Error reading fallback logs: {e}")
        
        return logs
    
    def get_security_logs(self) -> List[Dict]:
        """Read security logs from security.log file"""
        logs = []
        security_file = "data/security.log"
        
        if os.path.exists(security_file):
            try:
                with open(security_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            # Parse log line format: TIMESTAMP - USER - ACTION - DETAILS
                            try:
                                parts = line.strip().split(' - ')
                                if len(parts) >= 4:
                                    logs.append({
                                        'datetime': parts[0],
                                        'user': parts[1],
                                        'action': parts[2],
                                        'module': 'Sécurité',
                                        'details': ' - '.join(parts[3:]),
                                        'ip': 'N/A',
                                        'result': 'Info'
                                    })
                            except:
                                continue
            except Exception as e:
                print(f"Error reading security logs: {e}")
        
        return logs
    
    def get_database_logs(self) -> List[Dict]:
        """Get database activity logs"""
        logs = []
        
        # This would query database audit tables if they exist
        # For now, we'll create some sample entries based on recent database activity
        
        return logs
    
    def get_application_logs(self) -> List[Dict]:
        """Get application-specific logs"""
        logs = []
        
        # Check unified error log
        error_log_file = "data/error.log"
        if os.path.exists(error_log_file):
            try:
                with open(error_log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-100:]  # Last 100 lines
                    for line in lines:
                        if line.strip():
                            logs.append({
                                'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'user': 'System',
                                'action': 'Error Log',
                                'module': 'Système',
                                'details': line.strip()[:200] + "..." if len(line.strip()) > 200 else line.strip(),
                                'ip': '127.0.0.1',
                                'result': 'Error'
                            })
            except Exception as e:
                print(f"Error reading application logs: {e}")
        
        return logs
    
    def populate_log_table(self, logs: List[Dict]):
        """Populate the log table with data"""
        # Clear existing data
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        
        # Apply filters
        filtered_logs = self.filter_logs(logs)
        
        # Add logs to table
        for log in filtered_logs:
            # Determine row color based on result
            tag = ''
            result = log.get('result', '').lower()
            if 'success' in result or result == 'info':
                tag = 'success'
            elif 'error' in result or 'failed' in result:
                tag = 'error'
            elif 'warning' in result or 'warn' in result:
                tag = 'warning'
            
            # Format datetime for display
            dt_str = log.get('datetime', '')
            try:
                if len(dt_str) > 16:
                    dt_display = dt_str[:16]  # Show only date and time, no seconds
                else:
                    dt_display = dt_str
            except:
                dt_display = dt_str
            
            self.log_tree.insert("", "end", values=(
                dt_display,
                log.get('user', 'N/A'),
                log.get('action', 'N/A'),
                log.get('module', 'N/A'),
                log.get('details', 'N/A'),
                log.get('ip', 'N/A'),
                log.get('result', 'N/A')
            ), tags=(tag,))
        
        self.count_label.config(text=f"{len(filtered_logs)} entrées affichées")
    
    def filter_logs(self, logs: List[Dict]) -> List[Dict]:
        """Apply current filters to log data"""
        filtered = logs
        
        # User filter
        user_filter = self.filter_user_var.get()
        if user_filter != "Tous":
            filtered = [log for log in filtered if log.get('user', '') == user_filter]
        
        # Action filter
        action_filter = self.filter_action_var.get()
        if action_filter != "Toutes":
            filtered = [log for log in filtered if action_filter.lower() in log.get('action', '').lower()]
        
        # Search filter
        search_text = self.search_var.get().lower()
        if search_text:
            filtered = [log for log in filtered if 
                       search_text in log.get('user', '').lower() or
                       search_text in log.get('action', '').lower() or
                       search_text in log.get('details', '').lower() or
                       search_text in log.get('module', '').lower()]
        
        # Date range filter
        date_from = self.filter_date_from_var.get()
        date_to = self.filter_date_to_var.get()
        
        if date_from or date_to:
            # For now, we'll do basic date filtering
            # In production, you'd want proper date parsing
            pass
        
        return filtered
    
    def update_stats(self, logs: List[Dict]):
        """Update statistics display"""
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        # Count today's actions
        today_count = len([log for log in logs if log.get('datetime', '').startswith(today.strftime('%Y-%m-%d'))])
        
        # Count this week's actions  
        week_count = len([log for log in logs if self.is_within_week(log.get('datetime', ''), week_ago)])
        
        # Count active users (exclude System user)
        users = set(log.get('user', '') for log in logs if log.get('user', '') not in ['System', 'Unknown', ''])
        active_users = len(users)
        
        # Total actions
        total_actions = len(logs)
        
        self.stats_today_var.set(str(today_count))
        self.stats_week_var.set(str(week_count))
        self.stats_active_users_var.set(str(active_users))
        self.stats_total_actions_var.set(str(total_actions))
        
        # Try to get more accurate stats from activity service
        try:
            from app.stfoom.services.user_activity_service import activity_logger
            system_stats = activity_logger.get_system_statistics()
            
            # Override with more accurate data if available
            if system_stats.get('activities_today', 0) > today_count:
                self.stats_today_var.set(str(system_stats['activities_today']))
            if system_stats.get('activities_week', 0) > week_count:
                self.stats_week_var.set(str(system_stats['activities_week']))
            if system_stats.get('unique_users', 0) > active_users:
                self.stats_active_users_var.set(str(system_stats['unique_users']))
            if system_stats.get('total_activities', 0) > total_actions:
                self.stats_total_actions_var.set(str(system_stats['total_activities']))
        except Exception as e:
            print(f"Error getting system stats: {e}")
    
    def is_within_week(self, datetime_str: str, week_ago) -> bool:
        """Check if datetime is within the last week"""
        try:
            # Basic date checking - you'd want proper parsing in production
            return datetime_str >= week_ago.strftime('%Y-%m-%d')
        except:
            return False
    
    def update_filter_options(self, logs: List[Dict]):
        """Update filter combobox options based on available data"""
        # Get unique users
        users = sorted(set(log.get('user', '') for log in logs if log.get('user', '')))
        users.insert(0, "Tous")
        self.user_combo['values'] = users
        
        # Get unique actions
        actions = sorted(set(log.get('action', '') for log in logs if log.get('action', '')))
        actions.insert(0, "Toutes")
        self.action_combo['values'] = actions
    
    def apply_filters(self):
        """Apply current filters and refresh display"""
        logs = self.get_user_logs()
        self.populate_log_table(logs)
    
    def clear_filters(self):
        """Clear all filters"""
        self.filter_user_var.set("Tous")
        self.filter_action_var.set("Toutes")
        self.search_var.set("")
        today = datetime.now()
        last_month = today - timedelta(days=30)
        self.filter_date_from_var.set(last_month.strftime("%d/%m/%Y"))
        self.filter_date_to_var.set(today.strftime("%d/%m/%Y"))
        self.apply_filters()
    
    def set_today_filter(self):
        """Set filter to show only today's logs"""
        today = datetime.now().strftime("%d/%m/%Y")
        self.filter_date_from_var.set(today)
        self.filter_date_to_var.set(today)
        self.apply_filters()
    
    def set_week_filter(self):
        """Set filter to show this week's logs"""
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        self.filter_date_from_var.set(week_ago.strftime("%d/%m/%Y"))
        self.filter_date_to_var.set(today.strftime("%d/%m/%Y"))
        self.apply_filters()
    
    def set_month_filter(self):
        """Set filter to show this month's logs"""
        today = datetime.now()
        month_ago = today - timedelta(days=30)
        self.filter_date_from_var.set(month_ago.strftime("%d/%m/%Y"))
        self.filter_date_to_var.set(today.strftime("%d/%m/%Y"))
        self.apply_filters()
    
    def show_log_details(self, event):
        """Show comprehensive detailed information about selected log entry"""
        selection = self.log_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.log_tree.item(item, "values")
        
        if not values:
            return
        
        # Create detailed view window
        details_window = tk.Toplevel(self)
        details_window.title("📋 Détails Complets du Log")
        details_window.geometry("900x700")
        details_window.transient(self)
        
        # Create scrollable frame
        main_frame = ttk.Frame(details_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create notebook for tabbed interface
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)
        
        # Tab 1: Basic Information
        basic_frame = ttk.Frame(notebook, padding=20)
        notebook.add(basic_frame, text="📋 Informations Générales")
        
        # Basic info with better formatting
        basic_text = tk.Text(basic_frame, wrap="word", height=15, font=("Consolas", 10))
        basic_scroll = ttk.Scrollbar(basic_frame, orient="vertical", command=basic_text.yview)
        basic_text.configure(yscrollcommand=basic_scroll.set)
        
        basic_info = f"""🕐 HORODATAGE
Date/Heure: {values[0]}

👤 UTILISATEUR
Utilisateur: {values[1]}
Adresse IP: {values[5]}

⚡ ACTION
Action: {values[2]}
Module: {values[3]}
Résultat: {values[6]}

📝 DESCRIPTION
{values[4]}
"""
        
        # Try to get raw activity data for enhanced details
        try:
            # This is a bit hacky but works for getting the raw data
            # In a production system, you'd store the activity ID in the tree item
            raw_activity = None
            
            # Find the matching log entry (simplified approach)
            from app.stfoom.services.detailed_activity_service import detailed_logger
            activities = detailed_logger.get_detailed_activities(limit=50)
            
            for activity in activities:
                if (activity.get('timestamp', '').startswith(values[0][:16]) and
                    values[1] in activity.get('user_name', '') and
                    values[2] in f"{activity.get('action_category', '')}.{activity.get('action_name', '')}"):
                    raw_activity = activity
                    break
            
            if raw_activity:
                # Add enhanced details
                basic_info += f"""

🔧 DÉTAILS TECHNIQUES
ID Session: {raw_activity.get('session_id', 'N/A')}
Temps d'exécution: {raw_activity.get('execution_time_ms', 'N/A')} ms
Utilisation mémoire: {raw_activity.get('memory_usage_mb', 'N/A')} MB
Utilisation CPU: {raw_activity.get('cpu_usage_percent', 'N/A')} %

💼 CONTEXTE MÉTIER
Type d'action: {raw_activity.get('action_type', 'N/A')}
Méthode: {raw_activity.get('operation_method', 'N/A')}
Étape workflow: {raw_activity.get('workflow_step', 'N/A')}
Impact métier: {raw_activity.get('business_impact', 'N/A')}
Niveau de priorité: {raw_activity.get('priority_level', 'N/A')}

🎯 RESSOURCES AFFECTÉES
Type de ressource: {raw_activity.get('resource_type', 'N/A')}
ID ressource: {raw_activity.get('resource_id', 'N/A')}
Ressource parent: {raw_activity.get('parent_resource_type', 'N/A')} (ID: {raw_activity.get('parent_resource_id', 'N/A')})
Enregistrements affectés: {raw_activity.get('affected_records', 'N/A')}

🖥️ CONTEXTE INTERFACE
Page: {raw_activity.get('page_name', 'N/A')}
Fonctionnalité: {raw_activity.get('feature_name', 'N/A')}
Composant: {raw_activity.get('component_name', 'N/A')}

🌐 ENVIRONNEMENT SYSTÈME
Hostname: {raw_activity.get('hostname', 'N/A')}
Version application: {raw_activity.get('application_version', 'N/A')}
Version base de données: {raw_activity.get('database_version', 'N/A')}
"""
        except Exception as e:
            basic_info += f"\n\n⚠️ ERREUR: Impossible de récupérer les détails avancés: {e}"
        
        basic_text.insert("1.0", basic_info)
        basic_text.config(state="disabled")
        
        basic_text.pack(side="left", fill="both", expand=True)
        basic_scroll.pack(side="right", fill="y")
        
        # Tab 2: Technical Details (if available)
        if raw_activity:
            tech_frame = ttk.Frame(notebook, padding=20)
            notebook.add(tech_frame, text="🔧 Détails Techniques")
            
            tech_text = tk.Text(tech_frame, wrap="word", font=("Consolas", 9))
            tech_scroll = ttk.Scrollbar(tech_frame, orient="vertical", command=tech_text.yview)
            tech_text.configure(yscrollcommand=tech_scroll.set)
            
            tech_details = "🔧 INFORMATIONS TECHNIQUES AVANCÉES\n\n"
            
            # Operation parameters
            if raw_activity.get('operation_parameters'):
                tech_details += "📋 PARAMÈTRES D'OPÉRATION:\n"
                params = raw_activity['operation_parameters']
                if isinstance(params, dict):
                    for key, value in params.items():
                        tech_details += f"  • {key}: {value}\n"
                else:
                    tech_details += f"  {params}\n"
                tech_details += "\n"
            
            # Before/After states
            if raw_activity.get('before_state'):
                tech_details += "� ÉTAT AVANT:\n"
                before_state = raw_activity['before_state']
                if isinstance(before_state, dict):
                    for key, value in before_state.items():
                        tech_details += f"  • {key}: {value}\n"
                else:
                    tech_details += f"  {before_state}\n"
                tech_details += "\n"
            
            if raw_activity.get('after_state'):
                tech_details += "📤 ÉTAT APRÈS:\n"
                after_state = raw_activity['after_state']
                if isinstance(after_state, dict):
                    for key, value in after_state.items():
                        tech_details += f"  • {key}: {value}\n"
                else:
                    tech_details += f"  {after_state}\n"
                tech_details += "\n"
            
            # Changes made
            if raw_activity.get('changes_made'):
                tech_details += "� MODIFICATIONS APPORTÉES:\n"
                changes = raw_activity['changes_made']
                if isinstance(changes, list):
                    for i, change in enumerate(changes, 1):
                        tech_details += f"  {i}. {change}\n"
                else:
                    tech_details += f"  {changes}\n"
                tech_details += "\n"
            
            # Result data
            if raw_activity.get('result_data'):
                tech_details += "📊 DONNÉES DE RÉSULTAT:\n"
                result_data = raw_activity['result_data']
                if isinstance(result_data, dict):
                    for key, value in result_data.items():
                        tech_details += f"  • {key}: {value}\n"
                else:
                    tech_details += f"  {result_data}\n"
                tech_details += "\n"
            
            # Additional context
            if raw_activity.get('additional_context'):
                tech_details += "🔍 CONTEXTE ADDITIONNEL:\n"
                context = raw_activity['additional_context']
                if isinstance(context, dict):
                    for key, value in context.items():
                        tech_details += f"  • {key}: {value}\n"
                else:
                    tech_details += f"  {context}\n"
                tech_details += "\n"
            
            # Error details (if any)
            if raw_activity.get('error_message'):
                tech_details += "❌ INFORMATIONS D'ERREUR:\n"
                tech_details += f"  Type: {raw_activity.get('error_type', 'N/A')}\n"
                tech_details += f"  Message: {raw_activity.get('error_message', 'N/A')}\n"
                tech_details += f"  Code: {raw_activity.get('error_code', 'N/A')}\n"
                tech_details += f"  Action de récupération: {raw_activity.get('error_recovery_action', 'N/A')}\n"
                
                if raw_activity.get('error_stack_trace'):
                    tech_details += f"\n📚 STACK TRACE:\n{raw_activity['error_stack_trace']}\n"
                tech_details += "\n"
            
            # Tags
            if raw_activity.get('tags'):
                tech_details += f"🏷️ ÉTIQUETTES: {', '.join(raw_activity['tags']) if isinstance(raw_activity['tags'], list) else raw_activity['tags']}\n\n"
            
            # Compliance notes
            if raw_activity.get('compliance_notes'):
                tech_details += f"📋 NOTES DE CONFORMITÉ:\n{raw_activity['compliance_notes']}\n\n"
            
            tech_text.insert("1.0", tech_details)
            tech_text.config(state="disabled")
            
            tech_text.pack(side="left", fill="both", expand=True)
            tech_scroll.pack(side="right", fill="y")
        
        # Close button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(button_frame, text="📋 Copier les détails", 
                  command=lambda: self.copy_to_clipboard(basic_info)).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Fermer", command=details_window.destroy).pack(side="right")
    
    def copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()  # Ensure clipboard is updated
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
    
    def auto_refresh(self):
        """Auto-refresh logs every 30 seconds"""
        self.after(30000, lambda: (self.load_logs(), self.auto_refresh()))