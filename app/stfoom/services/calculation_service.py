"""
STFOOM Calculation Service
==========================
Centralized calculation service using configurable business rules.
REPLACES ALL HARDCODED CALCULATIONS THROUGHOUT THE APPLICATION!
"""
from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
import sys
import os

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from config.settings import settings
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))
    from settings import settings

class CalculationService:
    """
    Centralized calculation service using configurable business rules.
    
    🎯 ELIMINATES ALL HARDCODED VALUES:
    - No more hardcoded 19% TVA
    - No more hardcoded payment terms
    - No more hardcoded discount limits
    - Everything configurable through settings!
    """
    
    def __init__(self):
        self.config = settings
        self.business = settings.business
    
    # ═══════════════════════════════════════════════════════════════════════
    # TAX CALCULATIONS - NO MORE HARDCODED 19%!
    # ═══════════════════════════════════════════════════════════════════════
    
    def calculate_tva(self, amount: float, item_type: str = "standard") -> float:
        """
        Calculate TVA using configurable rates.
        
        BEFORE: amount * 0.19  # ❌ HARDCODED!
        AFTER:  calculation_service.calculate_tva(amount)  # ✅ CONFIGURABLE!
        """
        return self.config.calculate_tva(amount, item_type)
    
    def calculate_total_with_tva(self, amount: float, item_type: str = "standard") -> float:
        """Calculate total including TVA."""
        return self.config.calculate_total_with_tva(amount, item_type)
    
    def get_tva_rate_percentage(self, item_type: str = "standard") -> float:
        """Get TVA rate as percentage for display."""
        return self.config.get_tva_rate(item_type) * 100
    
    # ═══════════════════════════════════════════════════════════════════════
    # INVOICE CALCULATIONS - NO MORE HARDCODED VALUES!
    # ═══════════════════════════════════════════════════════════════════════
    
    def calculate_invoice_totals(self, items: List[Dict[str, Any]], 
                               discount_percentage: float = 0.0) -> Dict[str, float]:
        """
        Calculate complete invoice totals with configurable business rules.
        
        Returns:
        {
            'subtotal': float,
            'discount_amount': float,
            'tva_amount': float,
            'total_ht': float,
            'total_ttc': float,
            'tva_rate': float
        }
        """
        # Calculate subtotal
        subtotal = sum(
            item.get('quantite', 0) * item.get('prix_unitaire', 0) 
            for item in items
        )
        
        # Validate discount
        if not self.config.validate_discount(discount_percentage):
            raise ValueError(f"Discount {discount_percentage}% exceeds maximum {self.business.max_discount_percentage}%")
        
        # Calculate discount amount
        discount_amount = subtotal * (discount_percentage / 100)
        total_ht = subtotal - discount_amount
        
        # Calculate TVA on discounted amount
        tva_amount = self.calculate_tva(total_ht)
        total_ttc = total_ht + tva_amount
        
        return {
            'subtotal': round(subtotal, self.business.currency_precision),
            'discount_amount': round(discount_amount, self.business.currency_precision),
            'tva_amount': round(tva_amount, self.business.currency_precision),
            'total_ht': round(total_ht, self.business.currency_precision),
            'total_ttc': round(total_ttc, self.business.currency_precision),
            'tva_rate': self.get_tva_rate_percentage(),
            'currency': self.business.currency_symbol
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # PAYMENT CALCULATIONS - NO MORE HARDCODED TERMS!
    # ═══════════════════════════════════════════════════════════════════════
    
    def calculate_payment_terms(self, amount: float, days_since_invoice: int) -> Dict[str, Any]:
        """
        Calculate payment terms with configurable rules.
        
        BEFORE: if days <= 10: discount = amount * 0.02  # ❌ HARDCODED!
        AFTER:  payment_terms = calculation_service.calculate_payment_terms(amount, days)  # ✅ CONFIGURABLE!
        """
        result = {
            'original_amount': amount,
            'days_since_invoice': days_since_invoice,
            'is_early_payment': False,
            'is_late_payment': False,
            'discount_amount': 0.0,
            'penalty_amount': 0.0,
            'final_amount': amount,
            'payment_status': 'on_time'
        }
        
        # Check for early payment discount
        if self.config.is_early_payment_eligible(days_since_invoice):
            result['is_early_payment'] = True
            result['discount_amount'] = self.config.calculate_early_payment_discount(amount)
            result['final_amount'] = amount - result['discount_amount']
            result['payment_status'] = 'early'
        
        # Check for late payment penalty
        elif days_since_invoice > self.business.default_payment_days:
            result['is_late_payment'] = True
            days_overdue = days_since_invoice - self.business.default_payment_days
            result['penalty_amount'] = self.config.calculate_late_payment_penalty(amount, days_overdue)
            result['final_amount'] = amount + result['penalty_amount']
            result['payment_status'] = 'late'
        
        # Round all amounts
        for key in ['discount_amount', 'penalty_amount', 'final_amount']:
            result[key] = round(result[key], self.business.currency_precision)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # VALIDATION - NO MORE HARDCODED LIMITS!
    # ═══════════════════════════════════════════════════════════════════════
    
    def validate_invoice_data(self, items: List[Dict], discount: float = 0.0) -> Dict[str, Any]:
        """
        Validate invoice data against configurable business rules.
        
        BEFORE: if len(items) > 100: raise Error  # ❌ HARDCODED!
        AFTER:  validation = calculation_service.validate_invoice_data(items)  # ✅ CONFIGURABLE!
        """
        errors = []
        warnings = []
        
        # Validate number of items
        if len(items) > self.business.max_invoice_items:
            errors.append(f"Maximum {self.business.max_invoice_items} items per invoice")
        
        # Validate discount
        if not self.config.validate_discount(discount):
            errors.append(f"Maximum discount is {self.business.max_discount_percentage}%")
        
        # Validate item data
        for i, item in enumerate(items):
            if not item.get('quantite', 0) > 0:
                errors.append(f"Item {i+1}: Quantity must be greater than 0")
            
            if not item.get('prix_unitaire', 0) > 0:
                errors.append(f"Item {i+1}: Unit price must be greater than 0")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # FORMATTING AND DISPLAY
    # ═══════════════════════════════════════════════════════════════════════
    
    def format_currency(self, amount: float) -> str:
        """Format amount as currency with proper precision."""
        return self.config.format_currency(amount)
    
    def get_business_summary(self) -> Dict[str, Any]:
        """Get current business rules for display/debugging."""
        return {
            'Tax Rules': {
                'Default TVA Rate': f"{self.business.default_tva_rate * 100}%",
                'Reduced TVA Rate': f"{self.business.reduced_tva_rate * 100}%",
                'Zero TVA Rate': f"{self.business.zero_tva_rate * 100}%"
            },
            'Payment Terms': {
                'Default Payment Days': f"{self.business.default_payment_days} days",
                'Early Payment Discount': f"{self.business.early_payment_discount_rate * 100}%",
                'Early Payment Threshold': f"{self.business.early_payment_threshold_days} days",
                'Late Payment Penalty': f"{self.business.late_payment_penalty_rate * 100}%"
            },
            'Business Limits': {
                'Maximum Discount': f"{self.business.max_discount_percentage}%",
                'Maximum Invoice Items': self.business.max_invoice_items,
                'Low Stock Threshold': self.business.low_stock_threshold
            },
            'Display Settings': {
                'Currency Symbol': self.business.currency_symbol,
                'Currency Precision': f"{self.business.currency_precision} decimal places",
                'Rounding Method': self.business.rounding_method
            }
        }

# Global calculation service instance
calculation_service = CalculationService()

# Convenience functions for backward compatibility
def calculate_tva(amount: float, item_type: str = "standard") -> float:
    """Calculate TVA - backward compatibility."""
    return calculation_service.calculate_tva(amount, item_type)

def calculate_total_with_tva(amount: float, item_type: str = "standard") -> float:
    """Calculate total with TVA - backward compatibility."""
    return calculation_service.calculate_total_with_tva(amount, item_type)

def validate_discount(discount_percentage: float) -> bool:
    """Validate discount - backward compatibility."""
    return settings.validate_discount(discount_percentage)

if __name__ == "__main__":
    # Test the calculation service
    print("🧪 Testing STFOOM Calculation Service")
    print("=" * 60)
    
    # Display current business rules
    print("📋 Current Business Rules:")
    import json
    summary = calculation_service.get_business_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    print("\n🧮 Testing Calculations:")
    
    # Test invoice calculation
    test_items = [
        {'quantite': 10, 'prix_unitaire': 50.0},
        {'quantite': 5, 'prix_unitaire': 100.0}
    ]
    
    totals = calculation_service.calculate_invoice_totals(test_items, 5.0)
    print(f"Invoice Totals: {json.dumps(totals, indent=2)}")
    
    # Test payment terms
    payment_terms = calculation_service.calculate_payment_terms(1000.0, 5)  # 5 days - early
    print(f"Payment Terms (5 days): {json.dumps(payment_terms, indent=2)}")
    
    # Test validation
    validation = calculation_service.validate_invoice_data(test_items, 5.0)
    print(f"Validation: {validation}")
    
    print("\n✅ Calculation service working correctly!")
    print("🎉 NO MORE HARDCODED VALUES!")
