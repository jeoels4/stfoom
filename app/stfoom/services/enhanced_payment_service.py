
"""
Enhanced PaymentService with payment calculations
Migrated from buried UI functions for proper separation of concerns
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from typing import Optional

class EnhancedPaymentService:
    def __init__(self, settings_service):
        self.settings_service = settings_service
        
    def format_dt(self, amount):
        """Format amount as DT with exactly 3 decimal places"""
        if amount is None:
            return "0.000 DT"
        decimal_amount = Decimal(str(amount)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        return f"{decimal_amount:.3f} DT"
    
    def calculate_retenu(self, montant, retenu_percentage=None):
        """
        Calculate retenu (retention) amount
        Migrated from buried UI function in payment_dialog.py:89
        """
        try:
            if montant is None or montant <= 0:
                return 0.0
            
            # Get retenu percentage from settings or parameter
            if retenu_percentage is None:
                retenu_percentage = self.settings_service.get_setting("retenu_percentage", 2.5)
            
            retenu_amount = Decimal(str(montant)) * Decimal(str(retenu_percentage)) / Decimal('100')
            
            return float(retenu_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
        except Exception as e:
            print(f"Error calculating retenu: {e}")
            return 0.0
    
    def get_payment_due_date(self, invoice_date, payment_terms_days=30):
        """
        Calculate payment due date based on invoice date and terms
        Migrated from buried UI function in facture_page.py:445
        """
        try:
            if isinstance(invoice_date, str):
                # Try to parse date string
                try:
                    invoice_date = datetime.strptime(invoice_date, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        invoice_date = datetime.strptime(invoice_date, '%d/%m/%Y').date()
                    except ValueError:
                        return None
            
            # Get payment terms from settings
            if payment_terms_days is None:
                payment_terms_days = self.settings_service.get_setting("default_payment_terms", 30)
            
            due_date = invoice_date + timedelta(days=int(payment_terms_days))
            return due_date.strftime('%Y-%m-%d')
        except Exception as e:
            print(f"Error calculating due date: {e}")
            return None
    
    def calculate_net_payment_amount(self, gross_amount, retenu_percentage=None):
        """
        Calculate net payment amount after retenu deduction
        """
        try:
            retenu_amount = self.calculate_retenu(gross_amount, retenu_percentage)
            net_amount = Decimal(str(gross_amount)) - Decimal(str(retenu_amount))
            
            return {
                'gross_amount': float(Decimal(str(gross_amount)).quantize(Decimal('0.001'))),
                'retenu_amount': float(Decimal(str(retenu_amount)).quantize(Decimal('0.001'))),
                'net_amount': float(net_amount.quantize(Decimal('0.001'))),
                'retenu_percentage': retenu_percentage or self.settings_service.get_setting("retenu_percentage", 2.5)
            }
        except Exception as e:
            print(f"Error calculating net payment: {e}")
            return {
                'gross_amount': float(gross_amount),
                'retenu_amount': 0.0,
                'net_amount': float(gross_amount),
                'retenu_percentage': 2.5
            }
