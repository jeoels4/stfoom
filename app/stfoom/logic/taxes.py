"""
Tax Management System
====================
JSON-based tax storage and management for STFOOM application.
Provides CRUD operations for tax rates used throughout the system.
"""

from typing import List, Dict, Optional
import json
import os

# JSON file-based tax storage
TAXES_FILE = "data/taxes_simple.json"

def ensure_taxes_file():
    """Ensure taxes file exists with default data including 3 tax types."""
    if not os.path.exists("data"):
        os.makedirs("data")
        
    if not os.path.exists(TAXES_FILE):
        default_taxes = [
            {
                "id": 1, 
                "name": "TVA 19%", 
                "value": 19.0, 
                "type": "percentage", 
                "description": "Standard VAT rate 19%"
            },
            {
                "id": 2, 
                "name": "TVA 7%", 
                "value": 7.0, 
                "type": "percentage", 
                "description": "Reduced VAT rate 7%"
            },
            {
                "id": 3, 
                "name": "TVA 0%", 
                "value": 0.0, 
                "type": "percentage", 
                "description": "Zero VAT rate 0%"
            },
            {
                "id": 4, 
                "name": "Droit de Timbre", 
                "value": 1.0, 
                "type": "fixed", 
                "description": "Fixed stamp duty 1 DT"
            },
            {
                "id": 5, 
                "name": "Fond de Soutien", 
                "value": 1.0, 
                "type": "per_quantity", 
                "description": "Support fund 1 DT per quantity unit"
            }
        ]
        
        with open(TAXES_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_taxes, f, indent=2, ensure_ascii=False)
        
        print(f"[TAX_SYSTEM] Created default taxes file with {len(default_taxes)} taxes including 3 types: {TAXES_FILE}")
    else:
        # Update existing taxes to include type and description if missing
        _update_existing_taxes()

def _update_existing_taxes():
    """Update existing taxes to include type and description fields if missing."""
    try:
        if not os.path.exists(TAXES_FILE):
            return
            
        with open(TAXES_FILE, 'r', encoding='utf-8') as f:
            taxes = json.load(f)
        
        updated = False
        for tax in taxes:
            if 'type' not in tax or 'description' not in tax:
                # Auto-detect type and add description based on name
                if 'TVA' in tax['name'] or '%' in tax['name']:
                    tax['type'] = 'percentage'
                    tax['description'] = f"{tax['name']} rate"
                elif 'Droit de Timbre' in tax['name']:
                    tax['type'] = 'fixed'
                    tax['description'] = 'Fixed stamp duty 1 DT'
                elif 'Fond de Soutien' in tax['name'] or 'fond de soutien' in tax['name']:
                    tax['type'] = 'per_quantity'
                    tax['description'] = 'Support fund 1 DT per quantity unit'
                else:
                    tax['type'] = 'percentage'  # Default
                    tax['description'] = tax['name']
                updated = True
        
        if updated:
            with open(TAXES_FILE, 'w', encoding='utf-8') as f:
                json.dump(taxes, f, indent=2, ensure_ascii=False)
            print(f"[TAX_SYSTEM] Updated {len(taxes)} existing taxes with type and description fields")
            
    except Exception as e:
        print(f"[TAX_SYSTEM] Error updating existing taxes: {e}")

def get_all_taxes() -> List[Dict]:
    """Get all taxes from storage."""
    try:
        ensure_taxes_file()
        with open(TAXES_FILE, 'r', encoding='utf-8') as f:
            taxes = json.load(f)
        print(f"[TAX_SYSTEM] Retrieved {len(taxes)} taxes")
        return taxes
    except Exception as e:
        print(f"[TAX_SYSTEM] Error getting taxes: {e}")
        return []

def get_tax_by_id(tax_id: int) -> Optional[Dict]:
    """Get tax by ID."""
    try:
        taxes = get_all_taxes()
        for tax in taxes:
            if tax['id'] == tax_id:
                print(f"[TAX_SYSTEM] Found tax by ID {tax_id}: {tax['name']}")
                return tax
        print(f"[TAX_SYSTEM] Tax not found with ID: {tax_id}")
        return None
    except Exception as e:
        print(f"[TAX_SYSTEM] Error getting tax by ID: {e}")
        return None

def get_tax_by_name(name: str) -> Optional[Dict]:
    """Get tax by name (case insensitive)."""
    try:
        taxes = get_all_taxes()
        for tax in taxes:
            if tax['name'].lower() == name.lower():
                print(f"[TAX_SYSTEM] Found tax by name '{name}': {tax}")
                return tax
        print(f"[TAX_SYSTEM] Tax not found with name: {name}")
        return None
    except Exception as e:
        print(f"[TAX_SYSTEM] Error getting tax by name: {e}")
        return None

def add_tax(name: str, value: float, tax_type: str = "percentage", description: str = None) -> bool:
    """Add a new tax with type and description."""
    try:
        if not name or not name.strip():
            print("[TAX_SYSTEM] Cannot add tax: name is required")
            return False
        
        if value < 0:
            print("[TAX_SYSTEM] Cannot add tax: value cannot be negative")
            return False
        
        # Validate tax type
        valid_types = ["percentage", "fixed", "per_quantity"]
        if tax_type not in valid_types:
            print(f"[TAX_SYSTEM] Invalid tax type: {tax_type}. Must be one of: {valid_types}")
            return False
        
        taxes = get_all_taxes()
        
        # Check if tax with same name already exists
        for tax in taxes:
            if tax['name'].lower() == name.strip().lower():
                print(f"[TAX_SYSTEM] Tax with name '{name}' already exists")
                return False
        
        # Get next ID
        next_id = max([t['id'] for t in taxes]) + 1 if taxes else 1
        
        # Auto-generate description if not provided
        if description is None:
            if tax_type == "percentage":
                description = f"{name} rate"
            elif tax_type == "fixed":
                description = f"Fixed {name}"
            elif tax_type == "per_quantity":
                description = f"{name} per quantity unit"
        
        new_tax = {
            "id": next_id,
            "name": name.strip(),
            "value": float(value),
            "type": tax_type,
            "description": description
        }
        
        taxes.append(new_tax)
        
        with open(TAXES_FILE, 'w', encoding='utf-8') as f:
            json.dump(taxes, f, indent=2, ensure_ascii=False)
        
        print(f"[TAX_SYSTEM] Added tax: {name} = {value} ({tax_type}) - {description}")
        return True
        
    except Exception as e:
        print(f"[TAX_SYSTEM] Error adding tax: {e}")
        return False

def update_tax(tax_id: int, name: str, value: float, tax_type: str = None, description: str = None) -> bool:
    """Update an existing tax."""
    try:
        if not name or not name.strip():
            print("[TAX_SYSTEM] Cannot update tax: name is required")
            return False
        
        if value < 0:
            print("[TAX_SYSTEM] Cannot update tax: value cannot be negative")
            return False
        
        # Validate tax type if provided
        if tax_type is not None:
            valid_types = ["percentage", "fixed", "per_quantity"]
            if tax_type not in valid_types:
                print(f"[TAX_SYSTEM] Invalid tax type: {tax_type}. Must be one of: {valid_types}")
                return False
        
        taxes = get_all_taxes()
        
        for i, tax in enumerate(taxes):
            if tax['id'] == tax_id:
                # Check if new name conflicts with other taxes
                for other_tax in taxes:
                    if other_tax['id'] != tax_id and other_tax['name'].lower() == name.strip().lower():
                        print(f"[TAX_SYSTEM] Cannot update: tax name '{name}' already exists")
                        return False
                
                old_name = tax['name']
                
                # Update fields, keeping existing values if not provided
                updated_tax = {
                    "id": tax_id,
                    "name": name.strip(),
                    "value": float(value),
                    "type": tax_type if tax_type is not None else tax.get('type', 'percentage'),
                    "description": description if description is not None else tax.get('description', name.strip())
                }
                
                taxes[i] = updated_tax
                
                with open(TAXES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(taxes, f, indent=2, ensure_ascii=False)
                
                print(f"[TAX_SYSTEM] Updated tax {tax_id}: '{old_name}' → '{name}' = {value} ({updated_tax['type']})")
                return True
        
        print(f"[TAX_SYSTEM] Tax not found for update: ID {tax_id}")
        return False
        
    except Exception as e:
        print(f"[TAX_SYSTEM] Error updating tax: {e}")
        return False

def delete_tax(tax_id: int) -> bool:
    """Delete a tax."""
    try:
        taxes = get_all_taxes()
        
        for i, tax in enumerate(taxes):
            if tax['id'] == tax_id:
                removed = taxes.pop(i)
                
                with open(TAXES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(taxes, f, indent=2, ensure_ascii=False)
                
                print(f"[TAX_SYSTEM] Deleted tax: {removed['name']} ({removed['value']}%)")
                return True
        
        print(f"[TAX_SYSTEM] Tax not found for deletion: ID {tax_id}")
        return False
        
    except Exception as e:
        print(f"[TAX_SYSTEM] Error deleting tax: {e}")
        return False

def get_taxes_by_type(tax_type: str) -> List[Dict]:
    """Get all taxes of a specific type."""
    try:
        taxes = get_all_taxes()
        filtered_taxes = [tax for tax in taxes if tax.get('type', 'percentage') == tax_type]
        print(f"[TAX_SYSTEM] Found {len(filtered_taxes)} taxes of type '{tax_type}'")
        return filtered_taxes
    except Exception as e:
        print(f"[TAX_SYSTEM] Error getting taxes by type: {e}")
        return []

def get_tax_rate_by_name(name: str) -> Optional[float]:
    """Get tax rate by name (for easy percentage calculations)."""
    try:
        tax = get_tax_by_name(name)
        if tax:
            return tax['value']
        return None
    except Exception as e:
        print(f"[TAX_SYSTEM] Error getting tax rate: {e}")
        return None

def get_tax_statistics() -> Dict:
    """Get tax system statistics."""
    try:
        taxes = get_all_taxes()
        
        stats = {
            "total_count": len(taxes),
            "average_rate": 0.0,
            "min_rate": 0.0,
            "max_rate": 0.0,
            "zero_rate_count": 0
        }
        
        if taxes:
            rates = [tax['value'] for tax in taxes]
            stats["average_rate"] = sum(rates) / len(rates)
            stats["min_rate"] = min(rates)
            stats["max_rate"] = max(rates)
            stats["zero_rate_count"] = len([r for r in rates if r == 0.0])
        
        print(f"[TAX_SYSTEM] Generated statistics: {stats['total_count']} taxes")
        return stats
        
    except Exception as e:
        print(f"[TAX_SYSTEM] Error getting statistics: {e}")
        return {"total_count": 0, "average_rate": 0.0, "min_rate": 0.0, "max_rate": 0.0, "zero_rate_count": 0}

def get_current_tva_rate() -> float:
    """Get current TVA rate as decimal (e.g., 0.19 for 19%)."""
    try:
        # Look for TVA 19% first, then fallback to any percentage tax with "TVA" in name
        tva_tax = get_tax_by_name("TVA 19%")
        if not tva_tax:
            # Look for any TVA percentage tax
            percentage_taxes = get_taxes_by_type("percentage")
            for tax in percentage_taxes:
                if "TVA" in tax.get("name", "").upper():
                    tva_tax = tax
                    break
        
        if tva_tax:
            rate = tva_tax['value'] / 100.0
            print(f"[TAX_SYSTEM] Current TVA rate: {tva_tax['name']} = {rate} ({tva_tax['value']}%)")
            return rate
        else:
            print(f"[TAX_SYSTEM] No TVA tax found, using fallback 19%")
            return 0.19
    except Exception as e:
        print(f"[TAX_SYSTEM] Error getting TVA rate: {e}, using fallback 19%")
        return 0.19

def get_current_tva_percentage() -> float:
    """Get current TVA rate as percentage (e.g., 19.0 for 19%)."""
    return get_current_tva_rate() * 100.0

def get_current_tva_name() -> str:
    """Get current TVA tax name for UI display."""
    try:
        tva_tax = get_tax_by_name("TVA 19%")
        if not tva_tax:
            percentage_taxes = get_taxes_by_type("percentage")
            for tax in percentage_taxes:
                if "TVA" in tax.get("name", "").upper():
                    tva_tax = tax
                    break
        
        if tva_tax:
            return tva_tax['name']
        else:
            return "TVA 19%"  # fallback
    except Exception as e:
        print(f"[TAX_SYSTEM] Error getting TVA name: {e}")
        return "TVA 19%"  # fallback

# Initialize on import
ensure_taxes_file()
print("[TAX_SYSTEM] Tax management system ready")
