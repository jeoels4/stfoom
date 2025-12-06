#!/usr/bin/env python3
"""
STFOOM - Network Path Security Framework
========================================

This module provides comprehensive security for network path handling,
preventing path traversal attacks, unauthorized server access, and
malicious path injection.

Features:
- Network path validation with strict whitelist
- Path traversal prevention
- UNC path security validation
- Environment variable security
- Configuration file protection

Author: STFOOM Security Team
Date: July 30, 2025
"""

import os
import re
import logging
import socket
import ipaddress
from typing import List, Dict, Optional, Tuple, Union
from pathlib import Path, PureWindowsPath
from dataclasses import dataclass
from enum import Enum


class NetworkPathError(Exception):
    """Exception raised for network path security violations."""
    pass


class PathType(Enum):
    """Types of network paths."""
    UNC_PATH = "unc"
    LOCAL_PATH = "local"
    INVALID = "invalid"


@dataclass
class PathValidationResult:
    """Result of path validation."""
    is_valid: bool
    path_type: PathType
    normalized_path: str
    errors: List[str]
    warnings: List[str]
    security_score: int  # 0-100, higher is more secure


class NetworkPathValidator:
    """
    Comprehensive network path security validator.
    
    This class validates network paths to prevent:
    - Path traversal attacks
    - Unauthorized server access
    - Malicious UNC path injection
    - Environment variable injection
    """
    
    # Whitelist of allowed servers (configure for your environment)
    ALLOWED_SERVERS = {
        "DESKTOP-BKIB183",  # Current server
        "STFOOM-SERVER",    # Production server
        "BACKUP-SERVER",    # Backup server
        "localhost",        # Local development
        "127.0.0.1"        # Local IP
    }
    
    # Whitelist of allowed base paths
    ALLOWED_BASE_PATHS = {
        "data",
        "backups", 
        "documents",
        "exports",
        "shared"
    }
    
    # Dangerous path patterns
    DANGEROUS_PATTERNS = [
        r"\.\.[\\/]",           # Path traversal
        r"[\\/]\.\.[\\/]",      # Path traversal in middle
        r"[\\/]\.\.$",          # Path traversal at end
        r"[<>:\"|?*]",          # Windows invalid chars
        r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$",  # Windows reserved names
        r"admin\$",             # Administrative shares
        r"c\$",                 # System drive shares
        r"ipc\$",               # IPC shares
        r"print\$",             # Print shares
        r"\\\\[^\\]+\\[^\\]*\$",  # Administrative UNC shares
    ]
    
    # Valid UNC path pattern
    UNC_PATTERN = re.compile(r"^\\\\([a-zA-Z0-9\-_.]+)\\([a-zA-Z0-9\-_.\\]+)$")
    
    # Valid local path pattern (Windows)
    LOCAL_PATTERN = re.compile(r"^[a-zA-Z]:[\\\/]([a-zA-Z0-9\-_.\\ \/]+)$")
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_network_path(self, path: str) -> PathValidationResult:
        """
        Comprehensive validation of network paths.
        
        Args:
            path: The network path to validate
            
        Returns:
            PathValidationResult with detailed validation results
        """
        errors = []
        warnings = []
        security_score = 100
        
        if not isinstance(path, str):
            return PathValidationResult(
                False, PathType.INVALID, "", 
                ["Path must be a string"], [], 0
            )
        
        if not path.strip():
            return PathValidationResult(
                False, PathType.INVALID, "", 
                ["Path cannot be empty"], [], 0
            )
        
        # Normalize the path
        try:
            normalized_path = os.path.normpath(path).replace("/", "\\")
        except Exception as e:
            return PathValidationResult(
                False, PathType.INVALID, path,
                [f"Path normalization failed: {e}"], [], 0
            )
        
        # Determine path type
        path_type = self._determine_path_type(normalized_path)
        
        # Validate against dangerous patterns
        security_score -= self._check_dangerous_patterns(normalized_path, errors, warnings)
        
        # Validate path structure
        security_score -= self._validate_path_structure(normalized_path, path_type, errors, warnings)
        
        # Validate server access (for UNC paths)
        if path_type == PathType.UNC_PATH:
            security_score -= self._validate_server_access(normalized_path, errors, warnings)
        
        # Validate path components
        security_score -= self._validate_path_components(normalized_path, errors, warnings)
        
        # Check for suspicious characteristics
        security_score -= self._check_suspicious_characteristics(normalized_path, warnings)
        
        # Ensure security score doesn't go below 0
        security_score = max(0, security_score)
        
        is_valid = len(errors) == 0 and security_score >= 50
        
        return PathValidationResult(
            is_valid, path_type, normalized_path,
            errors, warnings, security_score
        )
    
    def _determine_path_type(self, path: str) -> PathType:
        """Determine the type of path."""
        if path.startswith("\\\\"):
            return PathType.UNC_PATH
        elif re.match(r"^[a-zA-Z]:", path):
            return PathType.LOCAL_PATH
        else:
            return PathType.INVALID
    
    def _check_dangerous_patterns(self, path: str, errors: List[str], warnings: List[str]) -> int:
        """Check for dangerous path patterns."""
        penalty = 0
        
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                errors.append(f"Dangerous pattern detected: {pattern}")
                penalty += 50
        
        return penalty
    
    def _validate_path_structure(self, path: str, path_type: PathType, 
                                errors: List[str], warnings: List[str]) -> int:
        """Validate path structure based on type."""
        penalty = 0
        
        if path_type == PathType.UNC_PATH:
            if not self.UNC_PATTERN.match(path):
                errors.append("Invalid UNC path format")
                penalty += 30
        elif path_type == PathType.LOCAL_PATH:
            if not self.LOCAL_PATTERN.match(path):
                errors.append("Invalid local path format")
                penalty += 30
        else:
            errors.append("Unrecognized path format")
            penalty += 50
        
        return penalty
    
    def _validate_server_access(self, path: str, errors: List[str], warnings: List[str]) -> int:
        """Validate server access for UNC paths."""
        penalty = 0
        
        match = self.UNC_PATTERN.match(path)
        if not match:
            return penalty
        
        server_name = match.group(1)
        
        # Check against whitelist
        if server_name not in self.ALLOWED_SERVERS:
            errors.append(f"Server '{server_name}' not in allowed servers list")
            penalty += 40
        
        # Check if server name is suspicious
        if self._is_suspicious_server_name(server_name):
            warnings.append(f"Server name '{server_name}' looks suspicious")
            penalty += 10
        
        # Validate server accessibility (optional security check)
        if not self._is_server_reachable(server_name):
            warnings.append(f"Server '{server_name}' is not reachable")
            penalty += 5
        
        return penalty
    
    def _validate_path_components(self, path: str, errors: List[str], warnings: List[str]) -> int:
        """Validate individual path components."""
        penalty = 0
        
        # Split path into components
        if path.startswith("\\\\"):
            # UNC path: \\server\share\path
            parts = path[2:].split("\\")
            if len(parts) >= 2:
                server, share = parts[0], parts[1]
                remaining_path = "\\".join(parts[2:]) if len(parts) > 2 else ""
                
                # Validate share name
                if share and share not in self.ALLOWED_BASE_PATHS:
                    warnings.append(f"Share '{share}' not in allowed base paths")
                    penalty += 5
                
                # Validate remaining path components
                if remaining_path:
                    penalty += self._validate_path_depth(remaining_path, warnings)
        else:
            # Local path
            parts = path.split("\\")[1:]  # Skip drive letter
            if parts:
                penalty += self._validate_path_depth("\\".join(parts), warnings)
        
        return penalty
    
    def _validate_path_depth(self, path: str, warnings: List[str]) -> int:
        """Validate path depth for security."""
        penalty = 0
        depth = len(path.split("\\")) if path else 0
        
        if depth > 10:
            warnings.append(f"Path depth ({depth}) is very deep")
            penalty += 5
        elif depth > 5:
            warnings.append(f"Path depth ({depth}) is moderately deep")
            penalty += 2
        
        return penalty
    
    def _is_suspicious_server_name(self, server_name: str) -> bool:
        """Check if server name looks suspicious."""
        suspicious_patterns = [
            r"^\d+\.\d+\.\d+\.\d+$",  # IP addresses (could be suspicious)
            r"[<>:\"|?*]",            # Invalid characters
            r"^(localhost|127\.0\.0\.1)$",  # Local references
        ]
        
        return any(re.match(pattern, server_name, re.IGNORECASE) for pattern in suspicious_patterns)
    
    def _is_server_reachable(self, server_name: str) -> bool:
        """Check if server is reachable (basic connectivity check)."""
        try:
            # Try to resolve hostname
            socket.gethostbyname(server_name)
            return True
        except (socket.gaierror, socket.herror):
            return False
    
    def _check_suspicious_characteristics(self, path: str, warnings: List[str]) -> int:
        """Check for other suspicious characteristics."""
        penalty = 0
        
        # Check for very long paths
        if len(path) > 260:  # Windows MAX_PATH limit
            warnings.append("Path exceeds Windows MAX_PATH limit")
            penalty += 10
        elif len(path) > 200:
            warnings.append("Path is very long")
            penalty += 5
        
        # Check for unusual characters
        unusual_chars = set(path) - set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\\.-_ ")
        if unusual_chars:
            warnings.append(f"Path contains unusual characters: {unusual_chars}")
            penalty += 5
        
        return penalty


class SecurePathManager:
    """
    Secure path manager for STFOOM application.
    
    This class provides secure methods for handling network paths
    with comprehensive validation and security controls.
    """
    
    def __init__(self):
        self.validator = NetworkPathValidator()
        self.logger = logging.getLogger(__name__)
    
    def validate_and_normalize_path(self, path: str) -> Tuple[bool, str, List[str]]:
        """
        Validate and normalize a network path.
        
        Args:
            path: The path to validate
            
        Returns:
            Tuple of (is_valid, normalized_path, error_messages)
        """
        result = self.validator.validate_network_path(path)
        
        if not result.is_valid:
            self.logger.warning(f"Path validation failed: {path}")
            self.logger.warning(f"Errors: {result.errors}")
            return False, path, result.errors
        
        if result.warnings:
            self.logger.info(f"Path validation warnings: {result.warnings}")
        
        self.logger.info(f"Path validated successfully: {result.normalized_path}")
        return True, result.normalized_path, []
    
    def secure_path_join(self, base_path: str, *components: str) -> str:
        """
        Securely join path components.
        
        Args:
            base_path: The base path
            *components: Path components to join
            
        Returns:
            Secure joined path
            
        Raises:
            NetworkPathError: If path construction would create security risk
        """
        # Validate base path
        is_valid, base_path, errors = self.validate_and_normalize_path(base_path)
        if not is_valid:
            raise NetworkPathError(f"Invalid base path: {'; '.join(errors)}")
        
        # Validate and join components
        full_path = base_path
        for component in components:
            # Validate individual component
            if not component or not isinstance(component, str):
                raise NetworkPathError(f"Invalid path component: {component}")
            
            # Check for path traversal in component
            if ".." in component or "/" in component or "\\" in component:
                raise NetworkPathError(f"Path traversal detected in component: {component}")
            
            # Join component
            full_path = os.path.join(full_path, component)
        
        # Final validation
        is_valid, normalized_path, errors = self.validate_and_normalize_path(full_path)
        if not is_valid:
            raise NetworkPathError(f"Final path validation failed: {'; '.join(errors)}")
        
        return normalized_path
    
    def is_path_within_allowed_directory(self, path: str, allowed_base: str) -> bool:
        """
        Check if path is within an allowed base directory.
        
        Args:
            path: The path to check
            allowed_base: The allowed base directory
            
        Returns:
            True if path is within allowed directory
        """
        try:
            # Normalize both paths
            norm_path = os.path.normpath(path)
            norm_base = os.path.normpath(allowed_base)
            
            # Check if path starts with base
            return norm_path.startswith(norm_base)
        except Exception:
            return False
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename for safe use.
        
        Args:
            filename: The filename to sanitize
            
        Returns:
            Sanitized filename
        """
        if not filename or not isinstance(filename, str):
            return "default"
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        
        # Limit length
        sanitized = sanitized[:255]
        
        # Ensure not empty or reserved name
        if not sanitized or sanitized.upper() in ['CON', 'PRN', 'AUX', 'NUL']:
            sanitized = f"file_{hash(filename) % 10000}"
        
        return sanitized


def validate_environment_path(env_var_name: str) -> Optional[str]:
    """
    Safely validate and retrieve path from environment variable.
    
    Args:
        env_var_name: Name of environment variable
        
    Returns:
        Validated path or None if invalid
    """
    path = os.getenv(env_var_name)
    if not path:
        return None
    
    manager = SecurePathManager()
    is_valid, normalized_path, errors = manager.validate_and_normalize_path(path)
    
    if is_valid:
        return normalized_path
    else:
        logging.warning(f"Environment variable {env_var_name} contains invalid path: {errors}")
        return None


def get_secure_server_path(fallback_path: str = None) -> str:
    """
    Get secure server path with validation.
    
    Args:
        fallback_path: Fallback path if environment/config not available
        
    Returns:
        Validated server path
        
    Raises:
        NetworkPathError: If no valid path can be determined
    """
    manager = SecurePathManager()
    
    # Try environment variable first
    env_path = validate_environment_path('STFOOM_SERVER_PATH')
    if env_path:
        return env_path
    
    # Try config file
    try:
        import connection.sync_config as sync_config
        config_path = sync_config.get_server_path()
        is_valid, normalized_path, errors = manager.validate_and_normalize_path(config_path)
        if is_valid:
            return normalized_path
    except Exception:
        pass
    
    # Try fallback
    if fallback_path:
        is_valid, normalized_path, errors = manager.validate_and_normalize_path(fallback_path)
        if is_valid:
            return normalized_path
    
    # No valid path found
    raise NetworkPathError("No valid server path found in environment, config, or fallback")


def main():
    """Test the network path security system."""
    print("🛡️  Testing Network Path Security System")
    print("=" * 50)
    
    validator = NetworkPathValidator()
    
    # Test cases
    test_paths = [
        r"\\DESKTOP-BKIB183\data",
        r"\\DESKTOP-BKIB183\data\backups",
        r"\\malicious-server\data",
        r"\\DESKTOP-BKIB183\admin$",
        r"\\DESKTOP-BKIB183\data\..\windows",
        r"C:\data\stfoom",
        r"invalid_path",
        "",
        None
    ]
    
    for path in test_paths:
        print(f"\nTesting: {path}")
        try:
            if path is None:
                result = validator.validate_network_path("")
            else:
                result = validator.validate_network_path(path)
            
            print(f"  Valid: {result.is_valid}")
            print(f"  Type: {result.path_type.value}")
            print(f"  Security Score: {result.security_score}/100")
            if result.errors:
                print(f"  Errors: {result.errors}")
            if result.warnings:
                print(f"  Warnings: {result.warnings}")
        except Exception as e:
            print(f"  Exception: {e}")


if __name__ == "__main__":
    main()
