"""
Comprehensive Logging Decorators for STFOOM
============================================
Automatic logging decorators that capture every method call with full context.
"""

import functools
import time
import inspect
from typing import Any, Callable, Dict, Optional, List, Union
from app.stfoom.services.detailed_activity_service import detailed_logger, log_database_operation, log_business_operation, log_ui_interaction, log_error_with_context


def log_method_call(
    action_type: str = "method_call",
    action_category: str = None,
    module_name: str = None,
    resource_type: str = None,
    capture_args: bool = True,
    capture_return: bool = True,
    capture_timing: bool = True,
    business_impact: str = None,
    priority_level: str = "normal",
    workflow_step: str = None
):
    """
    Decorator to automatically log method calls with full context
    
    Usage:
        @log_method_call(action_category="sales", module_name="vente", resource_type="vente")
        def create_vente(self, vente_data):
            # method implementation
            return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time() * 1000 if capture_timing else None
            
            # Extract method context
            method_name = func.__name__
            class_name = None
            if args and hasattr(args[0], '__class__'):
                class_name = args[0].__class__.__name__
            
            # Prepare operation parameters
            operation_params = {}
            if capture_args:
                # Capture args (skip 'self' parameter)
                if args[1:]:  # Skip self
                    operation_params['args'] = [str(arg) for arg in args[1:]]
                if kwargs:
                    operation_params['kwargs'] = {k: str(v) for k, v in kwargs.items()}
            
            # Determine resource ID if possible
            resource_id = None
            if kwargs.get('id'):
                resource_id = kwargs['id']
            elif len(args) > 1 and isinstance(args[1], (int, str)):
                resource_id = args[1]
            
            result = None
            error_occurred = None
            
            try:
                # Execute the method
                result = func(*args, **kwargs)
                
                # Calculate execution time
                execution_time = None
                if capture_timing and start_time:
                    execution_time = int((time.time() * 1000) - start_time)
                
                # Prepare result data
                result_data = None
                if capture_return and result is not None:
                    if isinstance(result, dict):
                        result_data = result
                    else:
                        result_data = {'return_value': str(result)}
                
                # Log successful operation
                detailed_logger.log_detailed_activity(
                    action_type=action_type,
                    action_category=action_category or "method_call",
                    action_name=method_name,
                    action_description=f"{class_name}.{method_name}() called" if class_name else f"{method_name}() called",
                    module_name=module_name or (class_name.lower().replace('service', '').replace('page', '') if class_name else 'system'),
                    feature_name=class_name.lower() if class_name else None,
                    component_name=f"{class_name}.{method_name}" if class_name else method_name,
                    resource_type=resource_type or (class_name.lower().replace('service', '').replace('page', '') if class_name else None),
                    resource_id=str(resource_id) if resource_id else None,
                    operation_method=method_name,
                    operation_parameters=operation_params if operation_params else None,
                    result_status="success",
                    result_data=result_data,
                    execution_time_ms=execution_time,
                    workflow_step=workflow_step,
                    business_impact=business_impact or f"{method_name} operation completed successfully",
                    priority_level=priority_level
                )
                
                return result
                
            except Exception as e:
                error_occurred = e
                
                # Calculate execution time even for errors
                execution_time = None
                if capture_timing and start_time:
                    execution_time = int((time.time() * 1000) - start_time)
                
                # Log error with full context
                log_error_with_context(
                    module=module_name or (class_name.lower() if class_name else 'system'),
                    operation=method_name,
                    error=e,
                    context={
                        'class_name': class_name,
                        'method_name': method_name,
                        'operation_params': operation_params,
                        'execution_time_ms': execution_time
                    }
                )
                
                # Re-raise the exception
                raise e
        
        return wrapper
    return decorator


def log_database_method(table_name: str, operation_type: str = None):
    """
    Decorator specifically for database operations
    
    Usage:
        @log_database_method("ventes", "create")
        def create_vente(self, vente_data):
            # implementation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time() * 1000
            
            # Try to extract before state for updates
            before_state = None
            record_id = None
            
            # Look for record ID in arguments
            if kwargs.get('id'):
                record_id = kwargs['id']
            elif len(args) > 1 and isinstance(args[1], (int, str)):
                record_id = args[1]
            
            # For update operations, try to get before state
            if operation_type == "update" and record_id:
                # This would require access to the database to get current state
                # For now, we'll capture what we can from the arguments
                pass
            
            try:
                result = func(*args, **kwargs)
                execution_time = int((time.time() * 1000) - start_time)
                
                # Extract after state from result or arguments
                after_state = None
                if isinstance(result, dict):
                    after_state = result
                elif len(args) > 1 and isinstance(args[1], dict):
                    after_state = args[1]
                
                # Determine affected records count
                affected_count = 1
                if isinstance(result, dict) and 'affected_rows' in result:
                    affected_count = result['affected_rows']
                
                log_database_operation(
                    operation=operation_type or func.__name__.replace('create_', '').replace('update_', '').replace('delete_', ''),
                    table_name=table_name,
                    record_id=str(record_id) if record_id else None,
                    before_data=before_state,
                    after_data=after_state,
                    affected_count=affected_count,
                    execution_time=execution_time
                )
                
                return result
                
            except Exception as e:
                execution_time = int((time.time() * 1000) - start_time)
                
                log_error_with_context(
                    module="database",
                    operation=f"{operation_type}_{table_name}",
                    error=e,
                    context={
                        'table_name': table_name,
                        'operation_type': operation_type,
                        'record_id': record_id,
                        'execution_time_ms': execution_time
                    }
                )
                
                raise e
        
        return wrapper
    return decorator


def log_ui_method(component_type: str = "component", page_name: str = None):
    """
    Decorator for UI interactions and page methods
    
    Usage:
        @log_ui_method("button", "vente_page")
        def on_create_button_click(self):
            # implementation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time() * 1000
            
            method_name = func.__name__
            class_name = None
            if args and hasattr(args[0], '__class__'):
                class_name = args[0].__class__.__name__
            
            # Determine page name from class name if not provided
            resolved_page_name = page_name
            if not resolved_page_name and class_name and 'page' in class_name.lower():
                resolved_page_name = class_name.lower().replace('page', '')
            
            try:
                result = func(*args, **kwargs)
                execution_time = int((time.time() * 1000) - start_time)
                
                # Determine action type from method name
                action = "interaction"
                if "click" in method_name.lower():
                    action = "click"
                elif "submit" in method_name.lower():
                    action = "submit"
                elif "select" in method_name.lower():
                    action = "select"
                elif "edit" in method_name.lower():
                    action = "edit"
                
                log_ui_interaction(
                    component_name=component_type,
                    action=action,
                    page_name=resolved_page_name,
                    interaction_data={
                        'method_name': method_name,
                        'class_name': class_name,
                        'execution_time_ms': execution_time
                    },
                    result="success"
                )
                
                return result
                
            except Exception as e:
                execution_time = int((time.time() * 1000) - start_time)
                
                log_ui_interaction(
                    component_name=component_type,
                    action=method_name,
                    page_name=resolved_page_name,
                    interaction_data={
                        'method_name': method_name,
                        'class_name': class_name,
                        'error': str(e),
                        'execution_time_ms': execution_time
                    },
                    result="error"
                )
                
                raise e
        
        return wrapper
    return decorator


def log_business_method(module: str, operation_category: str = None):
    """
    Decorator for business operation methods
    
    Usage:
        @log_business_method("ventes", "sale_creation")
        def create_sale(self, sale_data):
            # implementation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time() * 1000
            
            method_name = func.__name__
            
            # Extract business context from arguments
            before_state = None
            after_state = None
            resource_id = None
            
            # Look for data in arguments
            if len(args) > 1 and isinstance(args[1], dict):
                before_state = args[1].copy()
                resource_id = args[1].get('id')
            
            try:
                result = func(*args, **kwargs)
                execution_time = int((time.time() * 1000) - start_time)
                
                # Extract after state from result
                if isinstance(result, dict):
                    after_state = result
                    if 'id' in result:
                        resource_id = result['id']
                
                # Determine business impact
                business_impact = f"{operation_category or method_name} operation completed"
                if "create" in method_name.lower():
                    business_impact = f"New {module.rstrip('s')} created"
                elif "update" in method_name.lower():
                    business_impact = f"{module.rstrip('s')} updated"
                elif "delete" in method_name.lower():
                    business_impact = f"{module.rstrip('s')} deleted"
                
                log_business_operation(
                    module=module,
                    operation=operation_category or method_name,
                    resource_type=module.rstrip('s'),  # Remove 's' from plural module names
                    resource_id=str(resource_id) if resource_id else None,
                    details=f"{method_name} operation in {module} module",
                    before_state=before_state,
                    after_state=after_state,
                    business_impact=business_impact
                )
                
                return result
                
            except Exception as e:
                log_error_with_context(
                    module=module,
                    operation=method_name,
                    error=e,
                    context={
                        'operation_category': operation_category,
                        'resource_id': resource_id,
                        'before_state': before_state
                    }
                )
                
                raise e
        
        return wrapper
    return decorator


class LoggedClass:
    """
    Base class that automatically logs all method calls
    
    Usage:
        class VenteService(LoggedClass):
            _log_config = {
                'module_name': 'ventes',
                'action_category': 'sales',
                'resource_type': 'vente'
            }
            
            def create_vente(self, data):
                # This will be automatically logged
                pass
    """
    
    _log_config = {
        'module_name': 'system',
        'action_category': 'operation',
        'resource_type': None,
        'log_private_methods': False,
        'capture_args': True,
        'capture_return': True
    }
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        # Auto-wrap methods with logging
        for name, method in cls.__dict__.items():
            if callable(method) and not name.startswith('__'):
                # Skip private methods unless configured otherwise
                if name.startswith('_') and not cls._log_config.get('log_private_methods', False):
                    continue
                
                # Apply logging decorator
                wrapped_method = log_method_call(
                    action_category=cls._log_config.get('action_category', 'operation'),
                    module_name=cls._log_config.get('module_name', 'system'),
                    resource_type=cls._log_config.get('resource_type'),
                    capture_args=cls._log_config.get('capture_args', True),
                    capture_return=cls._log_config.get('capture_return', True),
                    priority_level="high" if any(op in name.lower() for op in ['create', 'update', 'delete']) else "normal"
                )(method)
                
                setattr(cls, name, wrapped_method)


def log_performance_critical(threshold_ms: int = 1000):
    """
    Decorator to log performance-critical operations
    Logs detailed performance metrics if execution time exceeds threshold
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time() * 1000
            
            result = func(*args, **kwargs)
            
            execution_time = int((time.time() * 1000) - start_time)
            
            if execution_time > threshold_ms:
                method_name = func.__name__
                class_name = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
                
                detailed_logger.log_performance_metric(
                    metric_type="execution_time",
                    metric_name=f"{class_name}.{method_name}" if class_name else method_name,
                    metric_value=execution_time,
                    unit="milliseconds",
                    context=f"Performance threshold exceeded (>{threshold_ms}ms)"
                )
                
                # Also log as a detailed activity
                detailed_logger.log_detailed_activity(
                    action_type="performance",
                    action_category="slow_operation",
                    action_name=method_name,
                    action_description=f"Slow operation detected: {method_name} took {execution_time}ms",
                    module_name=class_name.lower() if class_name else 'system',
                    execution_time_ms=execution_time,
                    result_status="warning",
                    business_impact=f"Operation completed but was slower than expected ({threshold_ms}ms threshold)",
                    priority_level="medium"
                )
            
            return result
        
        return wrapper
    return decorator