"""
STFOOM - SQL Injection Prevention System
=======================================

This module provides comprehensive SQL injection prevention for the STFOOM application.
It includes:

1. Secure query builders with parameterized statements
2. Input validation and sanitization
3. Table/column name validation
4. SQL injection detection and prevention
5. Safe query construction utilities

Author: STFOOM Security Team
Date: July 30, 2025
"""

import re
import sqlite3
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class QueryType(Enum):
    """Enumeration of supported SQL query types."""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class SecurityValidationResult:
    """Result of security validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class SQLInjectionError(Exception):
    """Exception raised when SQL injection attempt is detected."""
    pass


class SqlSecurityValidator:
    """
    Validates SQL inputs to prevent injection attacks.
    
    This class provides comprehensive validation for:
    - Table names
    - Column names
    - SQL parameters
    - Query structure
    """
    
    # Valid table names in STFOOM application
    VALID_TABLES = {
        'users', 'permissions', 'permission_types', 'rank_permissions',
        'user_sessions', 'activity_log', 'activity_logs', 'sync_changes', 'bl', 'facture',
        'devis', 'achat', 'avoir', 'ciment_commandes', 'ciment_livraisons',
        'ciment_reglements', 'documents', 'document_categories', 'calendar_events',
        # Adding missing business tables
        'clients', 'products', 'factures', 'bon_livraison', 'ventes', 'banques', 
        'achats', 'fournisseurs', 'voitures', 'caisse_transactions', 'paiements_factures',
        'transactions_bancaires', 'retenus', 'devis_items', 'taxes', 'payment_methods',
        'monthly_avoir_factures', 'monthly_avoir_tracking', 'avoir_applications', 'avoir_config',
        'document_downloads', 'document_folders', 'document_permissions'
    }
    
    # Valid column patterns (letters, numbers, underscores only)
    VALID_COLUMN_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')
    VALID_TABLE_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')
    
    # SQL injection detection patterns
    INJECTION_PATTERNS = [
        r"(union|UNION)\s+(select|SELECT)",
        r"(drop|DROP)\s+(table|TABLE)",
        r"(delete|DELETE)\s+(from|FROM)",
        r"(insert|INSERT)\s+(into|INTO)",
        r"(update|UPDATE)\s+\w+\s+(set|SET)",
        r"(exec|EXEC|execute|EXECUTE)\s*\(",
        r"(xp_|sp_|fn_)",
        r"(--|\/\*|\*\/|;)",
        r"('.*'.*=.*'.*')",
        r"(\d+\s*=\s*\d+)",
        r"(or|OR)\s+(\d+\s*=\s*\d+|'.*'.*=.*'.*')",
        r"(and|AND)\s+(\d+\s*=\s*\d+|'.*'.*=.*'.*')",
        # Enhanced patterns for better detection
        r"'\s*(or|OR)\s*'1'\s*=\s*'1",
        r"'\s*(or|OR)\s*'a'\s*=\s*'a",
        r"'\s*(or|OR)\s*'\w+'\s*=\s*'\w+",
        r"(or|OR)\s+'1'\s*=\s*'1",
        r"(or|OR)\s+'a'\s*=\s*'a",
        r"(select|SELECT).*from.*information_schema",
        r"(select|SELECT).*from.*sys\.",
        r"(select|SELECT).*from.*sqlite_master"
    ]
    
    @classmethod
    def validate_table_name(cls, table_name: str) -> SecurityValidationResult:
        """
        Validate table name for security.
        
        Args:
            table_name: The table name to validate
            
        Returns:
            SecurityValidationResult with validation results
        """
        errors = []
        warnings = []
        
        if not table_name:
            errors.append("Table name cannot be empty")
            return SecurityValidationResult(False, errors, warnings)
        
        # Check against whitelist
        if table_name not in cls.VALID_TABLES:
            errors.append(f"Table '{table_name}' is not in the approved table list")
        
        # Check format
        if not cls.VALID_TABLE_PATTERN.match(table_name):
            errors.append(f"Table name '{table_name}' contains invalid characters")
        
        # Check for SQL injection patterns
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, table_name, re.IGNORECASE):
                errors.append(f"Table name '{table_name}' contains suspicious SQL pattern")
                break
        
        return SecurityValidationResult(len(errors) == 0, errors, warnings)
    
    @classmethod
    def validate_column_name(cls, column_name: str) -> SecurityValidationResult:
        """
        Validate column name for security.
        
        Args:
            column_name: The column name to validate
            
        Returns:
            SecurityValidationResult with validation results
        """
        errors = []
        warnings = []
        
        if not column_name:
            errors.append("Column name cannot be empty")
            return SecurityValidationResult(False, errors, warnings)
        
        # Check format
        if not cls.VALID_COLUMN_PATTERN.match(column_name):
            errors.append(f"Column name '{column_name}' contains invalid characters")
        
        # Check for SQL injection patterns
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, column_name, re.IGNORECASE):
                errors.append(f"Column name '{column_name}' contains suspicious SQL pattern")
                break
        
        # Check for reserved words
        reserved_words = {
            'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'union', 'where', 'from', 'into', 'values', 'set', 'and', 'or',
            'not', 'null', 'true', 'false', 'table', 'database', 'schema'
        }
        
        if column_name.lower() in reserved_words:
            warnings.append(f"Column name '{column_name}' is a SQL reserved word")
        
        return SecurityValidationResult(len(errors) == 0, errors, warnings)
    
    @classmethod
    def validate_query_parameters(cls, params: Tuple) -> SecurityValidationResult:
        """
        Validate query parameters for security.
        
        Args:
            params: The parameters to validate
            
        Returns:
            SecurityValidationResult with validation results
        """
        errors = []
        warnings = []
        
        if not isinstance(params, (tuple, list)):
            errors.append("Parameters must be a tuple or list")
            return SecurityValidationResult(False, errors, warnings)
        
        for i, param in enumerate(params):
            if isinstance(param, str):
                # Check for SQL injection patterns in string parameters
                for pattern in cls.INJECTION_PATTERNS:
                    if re.search(pattern, param, re.IGNORECASE):
                        errors.append(f"Parameter {i} contains suspicious SQL pattern: {param}")
                        break
        
        return SecurityValidationResult(len(errors) == 0, errors, warnings)


class SecureQueryBuilder:
    """
    Secure SQL query builder that prevents injection attacks.
    
    This class provides methods to build SQL queries safely using
    parameterized statements and validated inputs.
    """
    
    def __init__(self):
        self.validator = SqlSecurityValidator()
        self.logger = logging.getLogger(__name__)
    
    def validate_inputs(self, table: str, columns: List[str] = None) -> None:
        """
        Validate table and column names.
        
        Args:
            table: Table name to validate
            columns: List of column names to validate
            
        Raises:
            SQLInjectionError: If validation fails
        """
        # Validate table name
        table_result = self.validator.validate_table_name(table)
        if not table_result.is_valid:
            raise SQLInjectionError(f"Invalid table name: {', '.join(table_result.errors)}")
        
        # Validate column names if provided
        if columns:
            for column in columns:
                column_result = self.validator.validate_column_name(column)
                if not column_result.is_valid:
                    raise SQLInjectionError(f"Invalid column name '{column}': {', '.join(column_result.errors)}")
    
    def build_select(self, table: str, columns: List[str] = None, 
                    where_conditions: Dict[str, Any] = None,
                    order_by: str = None, limit: int = None) -> Tuple[str, Tuple]:
        """
        Build a secure SELECT query.
        
        Args:
            table: Table name
            columns: List of columns to select (None for *)
            where_conditions: Dictionary of column:value pairs for WHERE clause
            order_by: Column name for ORDER BY
            limit: LIMIT value
            
        Returns:
            Tuple of (sql_query, parameters)
            
        Raises:
            SQLInjectionError: If validation fails
        """
        # Validate inputs
        self.validate_inputs(table, columns)
        
        if where_conditions:
            self.validate_inputs(table, list(where_conditions.keys()))
        
        if order_by:
            order_result = self.validator.validate_column_name(order_by)
            if not order_result.is_valid:
                raise SQLInjectionError(f"Invalid ORDER BY column: {', '.join(order_result.errors)}")
        
        # Build query
        if columns:
            columns_str = ", ".join(columns)
        else:
            columns_str = "*"
        
        sql = f"SELECT {columns_str} FROM {table}"
        params = []
        
        # Add WHERE clause
        if where_conditions:
            where_parts = []
            for column, value in where_conditions.items():
                where_parts.append(f"{column} = ?")
                params.append(value)
            sql += f" WHERE {' AND '.join(where_parts)}"
        
        # Add ORDER BY
        if order_by:
            sql += f" ORDER BY {order_by}"
        
        # Add LIMIT
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        
        return sql, tuple(params)
    
    def build_insert(self, table: str, data: Dict[str, Any]) -> Tuple[str, Tuple]:
        """
        Build a secure INSERT query.
        
        Args:
            table: Table name
            data: Dictionary of column:value pairs to insert
            
        Returns:
            Tuple of (sql_query, parameters)
            
        Raises:
            SQLInjectionError: If validation fails
        """
        if not data:
            raise SQLInjectionError("No data provided for INSERT")
        
        # Validate inputs
        columns = list(data.keys())
        self.validate_inputs(table, columns)
        
        # Build query
        placeholders = ", ".join("?" for _ in columns)
        columns_str = ", ".join(columns)
        
        sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        params = tuple(data.values())
        
        return sql, params
    
    def build_update(self, table: str, data: Dict[str, Any], 
                    where_conditions: Dict[str, Any]) -> Tuple[str, Tuple]:
        """
        Build a secure UPDATE query.
        
        Args:
            table: Table name
            data: Dictionary of column:value pairs to update
            where_conditions: Dictionary of column:value pairs for WHERE clause
            
        Returns:
            Tuple of (sql_query, parameters)
            
        Raises:
            SQLInjectionError: If validation fails
        """
        if not data:
            raise SQLInjectionError("No data provided for UPDATE")
        
        if not where_conditions:
            raise SQLInjectionError("WHERE conditions required for UPDATE")
        
        # Validate inputs
        update_columns = list(data.keys())
        where_columns = list(where_conditions.keys())
        self.validate_inputs(table, update_columns + where_columns)
        
        # Build query
        set_clause = ", ".join(f"{column} = ?" for column in update_columns)
        where_clause = " AND ".join(f"{column} = ?" for column in where_columns)
        
        sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = tuple(list(data.values()) + list(where_conditions.values()))
        
        return sql, params
    
    def build_delete(self, table: str, where_conditions: Dict[str, Any]) -> Tuple[str, Tuple]:
        """
        Build a secure DELETE query.
        
        Args:
            table: Table name
            where_conditions: Dictionary of column:value pairs for WHERE clause
            
        Returns:
            Tuple of (sql_query, parameters)
            
        Raises:
            SQLInjectionError: If validation fails
        """
        if not where_conditions:
            raise SQLInjectionError("WHERE conditions required for DELETE")
        
        # Validate inputs
        where_columns = list(where_conditions.keys())
        self.validate_inputs(table, where_columns)
        
        # Build query
        where_clause = " AND ".join(f"{column} = ?" for column in where_columns)
        
        sql = f"DELETE FROM {table} WHERE {where_clause}"
        params = tuple(where_conditions.values())
        
        return sql, params


class SecureDatabaseWrapper:
    """
    Secure database wrapper that prevents SQL injection.
    
    This class wraps database operations to ensure all queries
    use parameterized statements and validated inputs.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.query_builder = SecureQueryBuilder()
        self.logger = logging.getLogger(__name__)
    
    def execute_secure(self, sql: str, params: Tuple = ()) -> bool:
        """
        Execute a SQL statement securely.
        
        Args:
            sql: The SQL statement (must be parameterized)
            params: Parameters for the SQL statement
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            SQLInjectionError: If validation fails
        """
        # Validate parameters
        param_result = SqlSecurityValidator.validate_query_parameters(params)
        if not param_result.is_valid:
            raise SQLInjectionError(f"Invalid parameters: {', '.join(param_result.errors)}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(sql, params)
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Database execution error: {e}")
            return False
    
    def select_secure(self, table: str, columns: List[str] = None,
                     where_conditions: Dict[str, Any] = None,
                     order_by: str = None, limit: int = None) -> List[Dict]:
        """
        Execute a secure SELECT query.
        
        Args:
            table: Table name
            columns: List of columns to select
            where_conditions: WHERE conditions
            order_by: ORDER BY column
            limit: LIMIT value
            
        Returns:
            List of dictionaries representing rows
            
        Raises:
            SQLInjectionError: If validation fails
        """
        sql, params = self.query_builder.build_select(
            table, columns, where_conditions, order_by, limit
        )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Secure SELECT error: {e}")
            raise SQLInjectionError(f"Database query failed: {e}")
    
    def insert_secure(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        """
        Execute a secure INSERT query.
        
        Args:
            table: Table name
            data: Data to insert
            
        Returns:
            ID of inserted record, or None if failed
            
        Raises:
            SQLInjectionError: If validation fails
        """
        sql, params = self.query_builder.build_insert(table, data)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, params)
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Secure INSERT error: {e}")
            raise SQLInjectionError(f"Database insert failed: {e}")
    
    def update_secure(self, table: str, data: Dict[str, Any],
                     where_conditions: Dict[str, Any]) -> int:
        """
        Execute a secure UPDATE query.
        
        Args:
            table: Table name
            data: Data to update
            where_conditions: WHERE conditions
            
        Returns:
            Number of affected rows
            
        Raises:
            SQLInjectionError: If validation fails
        """
        sql, params = self.query_builder.build_update(table, data, where_conditions)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, params)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Secure UPDATE error: {e}")
            raise SQLInjectionError(f"Database update failed: {e}")
    
    def delete_secure(self, table: str, where_conditions: Dict[str, Any]) -> int:
        """
        Execute a secure DELETE query.
        
        Args:
            table: Table name
            where_conditions: WHERE conditions
            
        Returns:
            Number of deleted rows
            
        Raises:
            SQLInjectionError: If validation fails
        """
        sql, params = self.query_builder.build_delete(table, where_conditions)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, params)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Secure DELETE error: {e}")
            raise SQLInjectionError(f"Database delete failed: {e}")
    
    def close(self):
        """Close database connection (for compatibility)."""
        # Using context managers, so no persistent connection to close
        pass


def validate_sql_injection_attempt(user_input: str) -> bool:
    """
    Check if user input contains SQL injection attempts.
    
    Args:
        user_input: The input to validate
        
    Returns:
        True if injection attempt detected, False otherwise
    """
    if not isinstance(user_input, str):
        return False
    
    for pattern in SqlSecurityValidator.INJECTION_PATTERNS:
        if re.search(pattern, user_input, re.IGNORECASE):
            return True
    
    return False


def sanitize_string_input(user_input: str) -> str:
    """
    Sanitize string input to prevent SQL injection.
    
    Args:
        user_input: The input to sanitize
        
    Returns:
        Sanitized string
    """
    if not isinstance(user_input, str):
        return str(user_input)
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r"['\";\\]", "", user_input)
    
    # Remove SQL comments
    sanitized = re.sub(r"--.*$", "", sanitized)
    sanitized = re.sub(r"/\*.*?\*/", "", sanitized, flags=re.DOTALL)
    
    return sanitized.strip()


def main():
    """Test the SQL injection prevention system."""
    print("🛡️  Testing SQL Injection Prevention System")
    print("=" * 50)
    
    # Test validation
    validator = SqlSecurityValidator()
    
    # Test valid table name
    result = validator.validate_table_name("users")
    print(f"Valid table 'users': {result.is_valid}")
    
    # Test invalid table name
    result = validator.validate_table_name("users'; DROP TABLE users; --")
    print(f"Invalid table name: {result.is_valid}")
    print(f"Errors: {result.errors}")
    
    # Test query builder
    builder = SecureQueryBuilder()
    
    try:
        sql, params = builder.build_select("users", ["id", "username"])
        print(f"✅ Safe SELECT: {sql}")
        print(f"   Parameters: {params}")
    except SQLInjectionError as e:
        print(f"❌ Query blocked: {e}")
    
    print("\n🔐 SQL injection prevention system ready!")


if __name__ == "__main__":
    main()
