
"""
Enhanced TaxService with centralized tax calculations
Migrated from buried UI functions for proper separation of concerns
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

class EnhancedTaxService:
    def __init__(self, settings_service):
        self.settings_service = settings_service
        
    def format_dt(self, amount):
        """Format amount as DT with exactly 3 decimal places"""
        if amount is None:
            return "0.000 DT"
        decimal_amount = Decimal(str(amount)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        return f"{decimal_amount:.3f} DT"
    
    def get_current_tva_rate(self, tva_type="19"):
        """
        Get current TVA rate from settings - SINGLE SOURCE OF TRUTH
        Migrated from buried UI function in facture_page.py:203
        """
        try:
            if tva_type == "19":
                rate = self.settings_service.get_setting("tva_rate_19", 19.0)
            elif tva_type == "7":
                rate = self.settings_service.get_setting("tva_rate_7", 7.0)
            else:
                rate = 19.0  # Default
                
            return float(rate)
        except Exception as e:
            print(f"Error getting TVA rate: {e}")
            return 19.0 if tva_type == "19" else 7.0
    
    def calculate_tax(self, amount_ht, tva_type="19"):
        """
        Calculate tax amount based on HT amount and TVA type
        Migrated from buried UI function in calculator_page.py:156
        Uses settings for TVA rate - no more hardcoded values!
        """
        try:
            if amount_ht is None or amount_ht <= 0:
                return 0.0
            
            tva_rate = self.get_current_tva_rate(tva_type)
            tax_amount = Decimal(str(amount_ht)) * Decimal(str(tva_rate)) / Decimal('100')
            
            return float(tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
        except Exception as e:
            print(f"Error calculating tax: {e}")
            return 0.0
    
    def apply_timbre_fiscal(self, has_timbre=True):
        """
        Apply timbre fiscal based on settings
        Migrated from various UI files - now centralized!
        """
        try:
            if not has_timbre:
                return 0.0
                
            timbre_amount = self.settings_service.get_setting("timbre_fiscal", 0.3)
            return float(timbre_amount)
        except Exception as e:
            print(f"Error applying timbre: {e}")
            return 0.3  # Default fallback
    
    def calculate_total_ttc(self, amount_ht, transport_ht=0.0, has_timbre=True):
        """
        Calculate complete TTC amount with all taxes
        Centralized calculation to ensure consistency
        """
        try:
            # Calculate TVA19 on main amount
            tva19_amount = self.calculate_tax(amount_ht, "19")
            
            # Calculate TVA7 on transport
            tva7_amount = self.calculate_tax(transport_ht, "7")
            
            # Apply timbre
            timbre_amount = self.apply_timbre_fiscal(has_timbre)
            
            # Calculate TTC
            total_ht = Decimal(str(amount_ht)) + Decimal(str(transport_ht))
            total_tax = Decimal(str(tva19_amount)) + Decimal(str(tva7_amount))
            total_timbre = Decimal(str(timbre_amount))
            
            ttc = total_ht + total_tax + total_timbre
            
            return float(ttc.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
        except Exception as e:
            print(f"Error calculating TTC: {e}")
            return float(amount_ht) + float(transport_ht)
