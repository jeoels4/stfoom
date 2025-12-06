"""
connection.secure_backup_wrapper
===============================
Secure wrapper for backup operations with path traversal protection.
Replaces vulnerable backup functions with secure alternatives.
"""

import os
import shutil
import zipfile
import json
import tempfile
import logging
from typing import Optional, List
from pathlib import Path

# Import our path security system
from stfoom.logicold.path_security import (
    SecurePathValidator, 
    SecureFileOperations, 
    PathSecurityError,
    validate_backup_path,
    secure_backup_path,
    log_security_event
)

# Import secure hashing system
try:
    from stfoom.logicold.secure_hashing import secure_file_hash, verify_file_integrity
except ImportError:
    # Fallback functions if secure hashing module not available
    def secure_file_hash(filepath):
        import hashlib
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def verify_file_integrity(filepath, expected_hash):
        return secure_file_hash(filepath) == expected_hash

logger = logging.getLogger(__name__)

class SecureBackupManager:
    """Secure backup manager with path traversal protection"""
    
    def __init__(self, backup_dir: str, data_dir: str):
        """
        Initialize secure backup manager
        
        Args:
            backup_dir: Directory for storing backups
            data_dir: Directory containing data to backup
        """
        self.backup_dir = os.path.abspath(backup_dir)
        self.data_dir = os.path.abspath(data_dir)
        
        # Initialize path validator with our specific directories
        # The backup_dir is already correct (app/backups), so use that directly
        self.validator = SecurePathValidator([
            self.backup_dir,  # This is already C:\...\STFOOM\app\backups
            self.data_dir,    # This is already C:\...\STFOOM\data
            os.path.join(os.path.dirname(self.backup_dir), "output"),  # app/output
            os.path.join(os.path.dirname(self.backup_dir), "core")     # app/core
        ])
        
        self.file_ops = SecureFileOperations(self.validator)
        
        # Ensure directories exist
        self.file_ops.secure_makedirs(self.backup_dir)
        self.file_ops.secure_makedirs(self.data_dir)
        
        logger.info(f"SecureBackupManager initialized: backup_dir={self.backup_dir}, data_dir={self.data_dir}")
    
    def secure_create_backup(self, backup_filename: str, description: str = "") -> bool:
        """
        Create a backup with secure path handling
        
        Args:
            backup_filename: Name of the backup file (validated)
            description: Description of the backup
            
        Returns:
            True if backup created successfully, False otherwise
        """
        try:
            # Validate and sanitize backup filename
            safe_filename = self._sanitize_backup_filename(backup_filename)
            
            # Create secure backup path
            backup_path = self.validator.secure_join(self.backup_dir, safe_filename)
            
            # Validate backup path
            result = validate_backup_path(backup_path)
            if not result.is_valid:
                log_security_event("BACKUP_PATH_VIOLATION", backup_path, result.error_message)
                logger.error(f"Backup path validation failed: {result.error_message}")
                return False
            
            logger.info(f"Creating secure backup: {backup_path}")
            
            # Create backup in temporary location first
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                temp_backup_path = temp_file.name
            
            try:
                # Create the backup archive
                with zipfile.ZipFile(temp_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    self._add_files_to_backup(zipf)
                
                # Move temporary backup to final location
                shutil.move(temp_backup_path, backup_path)
                
                # Create backup info file
                self._create_backup_info(backup_path, description)
                
                logger.info(f"Backup created successfully: {backup_path}")
                return True
                
            except Exception as e:
                # Clean up temporary file if something went wrong
                if os.path.exists(temp_backup_path):
                    os.remove(temp_backup_path)
                raise
                
        except PathSecurityError as e:
            log_security_event("BACKUP_SECURITY_VIOLATION", backup_filename, str(e))
            logger.error(f"Security violation during backup creation: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False
    
    def secure_restore_backup(self, backup_filename: str, restore_path: Optional[str] = None) -> bool:
        """
        Restore from backup with secure path handling
        
        Args:
            backup_filename: Name of the backup file (validated)
            restore_path: Optional custom restore path (validated)
            
        Returns:
            True if restore successful, False otherwise
        """
        try:
            # Validate backup filename
            safe_filename = self._sanitize_backup_filename(backup_filename)
            
            # Create secure backup path
            backup_path = self.validator.secure_join(self.backup_dir, safe_filename)
            
            # Validate backup exists and is accessible
            if not self.file_ops.secure_exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Determine restore path
            if restore_path is None:
                target_restore_path = self.data_dir
            else:
                # Validate custom restore path
                result = self.validator.validate_path(restore_path)
                if not result.is_valid:
                    log_security_event("RESTORE_PATH_VIOLATION", restore_path, result.error_message)
                    logger.error(f"Restore path validation failed: {result.error_message}")
                    return False
                target_restore_path = result.normalized_path
            
            logger.info(f"Restoring backup {backup_path} to {target_restore_path}")
            
            # Verify backup integrity before extraction
            if not self._verify_backup_integrity(backup_path):
                logger.error(f"Backup integrity verification failed: {backup_path}")
                return False
            
            # Create restore directory
            self.file_ops.secure_makedirs(target_restore_path)
            
            # Extract backup with security checks
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                self._secure_extract_backup(zipf, target_restore_path)
            
            logger.info(f"Backup restored successfully: {backup_path}")
            return True
            
        except PathSecurityError as e:
            log_security_event("RESTORE_SECURITY_VIOLATION", backup_filename, str(e))
            logger.error(f"Security violation during restore: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            return False
    
    def secure_list_backups(self) -> List[dict]:
        """
        List available backups with secure path handling
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        try:
            if not self.file_ops.secure_exists(self.backup_dir):
                return backups
            
            for filename in os.listdir(self.backup_dir):
                if not filename.endswith('.zip') or not filename.startswith('stfoom_backup_'):
                    continue
                
                try:
                    # Validate backup filename
                    backup_path = self.validator.secure_join(self.backup_dir, filename)
                    
                    # Get backup info
                    info = self._get_backup_info(backup_path)
                    if info:
                        backups.append(info)
                        
                except PathSecurityError:
                    log_security_event("LIST_BACKUPS_SECURITY_VIOLATION", filename, "Invalid backup filename")
                    logger.warning(f"Skipping invalid backup file: {filename}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing backup file {filename}: {str(e)}")
                    continue
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"Error listing backups: {str(e)}")
            return []
    
    def secure_delete_backup(self, backup_filename: str) -> bool:
        """
        Delete a backup file with secure path handling
        
        Args:
            backup_filename: Name of the backup file to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # Validate backup filename
            safe_filename = self._sanitize_backup_filename(backup_filename)
            
            # Create secure backup path
            backup_path = self.validator.secure_join(self.backup_dir, safe_filename)
            
            # Check if backup exists
            if not self.file_ops.secure_exists(backup_path):
                logger.warning(f"Backup file not found for deletion: {backup_path}")
                return False
            
            # Delete backup file
            self.file_ops.secure_remove(backup_path)
            
            # Delete associated info file if it exists
            info_path = backup_path.replace('.zip', '.json')
            if self.file_ops.secure_exists(info_path):
                self.file_ops.secure_remove(info_path)
            
            logger.info(f"Backup deleted successfully: {backup_path}")
            return True
            
        except PathSecurityError as e:
            log_security_event("DELETE_BACKUP_SECURITY_VIOLATION", backup_filename, str(e))
            logger.error(f"Security violation during backup deletion: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error deleting backup: {str(e)}")
            return False
    
    def _sanitize_backup_filename(self, filename: str) -> str:
        """
        Sanitize backup filename to prevent path traversal
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
            
        Raises:
            PathSecurityError: If filename is invalid
        """
        if not filename:
            raise PathSecurityError("Backup filename cannot be empty")
        
        # Remove any path separators
        safe_name = os.path.basename(filename)
        
        # Ensure it's a valid backup filename
        if not (safe_name.endswith('.zip') and safe_name.startswith('stfoom_backup_')):
            # Generate a safe backup filename
            base_name = ''.join(c for c in safe_name if c.isalnum() or c in '._-')
            if not base_name:
                raise PathSecurityError("Invalid backup filename")
            safe_name = f"stfoom_backup_{base_name}"
            if not safe_name.endswith('.zip'):
                safe_name += '.zip'
        
        # Final validation
        result = validate_backup_path(os.path.join(self.backup_dir, safe_name))
        if not result.is_valid:
            raise PathSecurityError(f"Sanitized filename still invalid: {result.error_message}")
        
        return safe_name
    
    def _add_files_to_backup(self, zipf: zipfile.ZipFile):
        """
        Add files to backup archive with security checks
        
        Args:
            zipf: ZipFile object to add files to
        """
        # Add main database
        db_path = os.path.join(self.data_dir, "stfoom.db")
        if self.file_ops.secure_exists(db_path):
            zipf.write(db_path, "stfoom.db")
        
        # Add sync database if it exists
        sync_db_path = os.path.join(self.data_dir, "sync_tracking.db")
        if self.file_ops.secure_exists(sync_db_path):
            zipf.write(sync_db_path, "sync_tracking.db")
        
        # Add configuration files
        config_files = ["settings.json", "backup_config.json"]
        for config_file in config_files:
            config_path = os.path.join(os.path.dirname(self.data_dir), config_file)
            if self.file_ops.secure_exists(config_path):
                try:
                    result = self.validator.validate_path(config_path, "config")
                    if result.is_valid:
                        zipf.write(config_path, config_file)
                except PathSecurityError:
                    logger.warning(f"Skipping config file due to security validation: {config_file}")
        
        # Add output directory if it exists
        output_dir = os.path.join(os.path.dirname(self.data_dir), "output")
        if self.file_ops.secure_exists(output_dir):
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        result = self.validator.validate_path(file_path)
                        if result.is_valid:
                            arcname = os.path.relpath(file_path, os.path.dirname(self.data_dir))
                            zipf.write(file_path, arcname)
                    except PathSecurityError:
                        logger.warning(f"Skipping file due to security validation: {file_path}")
    
    def _secure_extract_backup(self, zipf: zipfile.ZipFile, extract_path: str):
        """
        Securely extract backup files with path validation
        
        Args:
            zipf: ZipFile object to extract from
            extract_path: Path to extract files to
        """
        for member in zipf.namelist():
            # Validate each member path
            target_path = os.path.join(extract_path, member)
            
            try:
                result = self.validator.validate_path(target_path)
                if not result.is_valid:
                    log_security_event("EXTRACT_PATH_VIOLATION", member, result.error_message)
                    logger.warning(f"Skipping extraction of {member}: {result.error_message}")
                    continue
                
                # Ensure target directory exists
                target_dir = os.path.dirname(result.normalized_path)
                self.file_ops.secure_makedirs(target_dir)
                
                # Extract the file
                with zipf.open(member) as source, self.file_ops.secure_open(result.normalized_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                
            except PathSecurityError as e:
                log_security_event("EXTRACT_SECURITY_VIOLATION", member, str(e))
                logger.warning(f"Security violation during extraction of {member}: {str(e)}")
                continue
            except Exception as e:
                logger.warning(f"Error extracting {member}: {str(e)}")
                continue
    
    def _verify_backup_integrity(self, backup_path: str) -> bool:
        """
        Verify backup file integrity using secure checksum and ZIP validation
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if integrity check passes, False otherwise
        """
        try:
            # First check if backup info exists with checksum
            info_path = backup_path.replace('.zip', '.json')
            backup_info = None
            
            if self.file_ops.secure_exists(info_path):
                try:
                    with self.file_ops.secure_open(info_path, 'r', 'config') as f:
                        backup_info = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not read backup info: {e}")
            
            # Verify checksum if available
            if backup_info and 'checksum' in backup_info:
                stored_checksum = backup_info['checksum']
                algorithm = backup_info.get('checksum_algorithm', 'SHA-256')
                
                logger.info(f"Verifying backup integrity using {algorithm} checksum...")
                
                if verify_file_integrity(backup_path, stored_checksum):
                    logger.info("Backup checksum verification PASSED")
                else:
                    logger.error("Backup checksum verification FAILED - file may be corrupted")
                    return False
            else:
                logger.warning("No checksum available for backup verification")
            
            # Try to open and validate the ZIP file structure
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Test the ZIP file integrity
                bad_file = zipf.testzip()
                if bad_file:
                    logger.error(f"Corrupted file in backup: {bad_file}")
                    return False
                
                # Check if backup contains expected files
                expected_files = ["stfoom.db"]
                for expected in expected_files:
                    if expected not in zipf.namelist():
                        logger.warning(f"Expected file {expected} not found in backup")
                
                logger.info("Backup ZIP structure verification PASSED")
                return True
                
        except zipfile.BadZipFile:
            logger.error(f"Invalid ZIP file: {backup_path}")
            return False
        except Exception as e:
            logger.error(f"Error verifying backup integrity: {str(e)}")
            return False
    
    def _create_backup_info(self, backup_path: str, description: str):
        """
        Create backup information file with secure checksum
        
        Args:
            backup_path: Path to backup file
            description: Backup description
        """
        try:
            info_path = backup_path.replace('.zip', '.json')
            
            # Calculate secure SHA-256 checksum
            checksum = secure_file_hash(backup_path)
            
            backup_info = {
                "filename": os.path.basename(backup_path),
                "description": description,
                "timestamp": int(os.path.getmtime(backup_path)),
                "size": os.path.getsize(backup_path),
                "checksum": checksum,
                "checksum_algorithm": "SHA-256",
                "created_by": "SecureBackupManager",
                "security_version": "2.0"
            }
            
            with self.file_ops.secure_open(info_path, 'w', 'config') as f:
                json.dump(backup_info, f, indent=2)
                
            logger.info(f"Backup info created with SHA-256 checksum: {checksum[:16]}...")
                
        except Exception as e:
            logger.warning(f"Could not create backup info file: {str(e)}")
    
    def _get_backup_info(self, backup_path: str) -> Optional[dict]:
        """
        Get backup information
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Backup info dictionary or None if not available
        """
        try:
            info_path = backup_path.replace('.zip', '.json')
            
            if self.file_ops.secure_exists(info_path):
                with self.file_ops.secure_open(info_path, 'r', 'config') as f:
                    return json.load(f)
            else:
                # Create basic info from file stats
                return {
                    "filename": os.path.basename(backup_path),
                    "description": "Legacy backup",
                    "timestamp": int(os.path.getmtime(backup_path)),
                    "size": os.path.getsize(backup_path),
                    "created_by": "Legacy"
                }
                
        except Exception as e:
            logger.warning(f"Could not get backup info: {str(e)}")
            return None
