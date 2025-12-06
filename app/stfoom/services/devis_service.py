"""
Devis Service
============
Business logic for devis operations.
"""

import os
import math
from datetime import datetime
from typing import List, Dict, Optional, Any
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.drawing.image import Image as XLImage
from copy import copy
from ..data.devis_repository import DevisRepository
import connection.sync_wrapper as sync

# Import tax system for dynamic rates
try:
    from ..logic.taxes import get_current_tva_rate, get_current_tva_percentage
except ImportError as e:
    print(f"[DEVIS_SERVICE] Tax system import failed: {e}")
    # Fallback functions
    def get_current_tva_rate(): return 0.19
    def get_current_tva_percentage(): return 19.0


class DevisService:
    """Service for devis business operations."""
    
    def __init__(self, devis_repository: DevisRepository):
        self.devis_repo = devis_repository
        self.setup_paths()
    
    def setup_paths(self):
        """Setup file paths for templates and output."""
        self.DATA_DIR = "core"
        self.TEMPLATE_BASE_DEVIS = os.path.join(self.DATA_DIR, "templates", "base devis.xlsx")
        self.TEMPLATE_BASE_DEVIS_HT = os.path.join(self.DATA_DIR, "templates", "base devis hors tunis.xlsx")
        self.LOGO_PATH = os.path.join(self.DATA_DIR, "logo", "stfoomlogo.jpg")
        
        self.DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
        self.OUTPUT_DIR = os.path.join(self.DESKTOP, "devis")
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
    
    def get_products(self):
        """Get all available products."""
        return self.devis_repo.get_products()
    
    def validate_devis_data(self, client_name: str, products: List[Dict], 
                           is_grand_tunis: bool, is_hors_grand_tunis: bool) -> Dict[str, Any]:
        """Validate devis data before generation."""
        errors = []
        
        # Validate client name
        if not client_name or not client_name.strip():
            errors.append("Le nom du client est requis")
        
        # Validate location selection
        if not (is_grand_tunis or is_hors_grand_tunis):
            errors.append("Veuillez choisir Grand Tunis ou Hors Grand Tunis")
        
        if is_grand_tunis and is_hors_grand_tunis:
            errors.append("Veuillez choisir soit Grand Tunis soit Hors Grand Tunis, pas les deux")
        
        # Validate products
        if not products:
            errors.append("Aucun produit sélectionné")
        
        # Validate product prices
        for product in products:
            if product.get("price") is not None:
                try:
                    price = float(product["price"])
                    if price < 0:
                        errors.append(f"Prix invalide pour {product['name']}: le prix ne peut pas être négatif")
                except (ValueError, TypeError):
                    errors.append(f"Prix invalide pour {product['name']}: format numérique requis")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def create_devis(self, client_name: str, products: List[Dict], 
                    is_grand_tunis: bool) -> Dict[str, Any]:
        """Create a new devis with business logic validation."""
        try:
            # Validate input
            validation = self.validate_devis_data(
                client_name, products, is_grand_tunis, not is_grand_tunis
            )
            if not validation["valid"]:
                return {
                    "success": False,
                    "errors": validation["errors"]
                }
            
            # Calculate totals
            total_ht = 0.0
            validated_products = []
            
            for product in products:
                # Get product details from database
                product_data = self.devis_repo.get_product_by_code(product["code"])
                if not product_data:
                    return {
                        "success": False,
                        "errors": [f"Produit {product['code']} non trouvé dans la base de données"]
                    }
                
                # Use custom price if provided, otherwise use database price
                price = product.get("price") or product_data["prix_ht"]
                quantity = product.get("quantity", 1)
                line_total = float(price) * quantity
                total_ht += line_total
                
                validated_products.append({
                    "code": product["code"],
                    "name": product["name"],
                    "price": float(price),
                    "quantity": quantity,
                    "total": line_total
                })
            
            # Calculate TVA and total TTC using dynamic rate from settings
            tva_rate = get_current_tva_rate()  # Dynamic TVA rate from settings
            total_tva = total_ht * tva_rate
            total_ttc = total_ht + total_tva
            
            # Create devis record
            devis_data = {
                "client_name": client_name.strip(),
                "is_grand_tunis": is_grand_tunis,
                "total_ht": total_ht,
                "total_ttc": total_ttc,
                "status": "draft"
            }
            
            # Save to database
            devis_id = self.devis_repo.create_devis(devis_data)
            if not devis_id:
                return {
                    "success": False,
                    "errors": ["Erreur lors de la sauvegarde du devis"]
                }
            
            # Save devis items
            if not self.devis_repo.save_devis_items(devis_id, validated_products):
                return {
                    "success": False,
                    "errors": ["Erreur lors de la sauvegarde des articles"]
                }
            
            # Generate Excel file
            devis_record = self.devis_repo.get_devis_by_id(devis_id)
            file_path = self.generate_excel_file(devis_record, validated_products)
            
            if file_path:
                # Update file path in database
                self.devis_repo.update_devis_file_path(devis_id, file_path)
                
                return {
                    "success": True,
                    "devis_id": devis_id,
                    "devis_number": devis_record["devis_number"],
                    "file_path": file_path,
                    "total_ht": total_ht,
                    "total_ttc": total_ttc,
                    "message": f"Devis {devis_record['devis_number']} créé avec succès"
                }
            else:
                return {
                    "success": False,
                    "errors": ["Erreur lors de la génération du fichier Excel"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "errors": [f"Erreur inattendue: {str(e)}"]
            }
    
    def generate_excel_file(self, devis_data: Dict, products: List[Dict]) -> Optional[str]:
        """Generate Excel file for the devis."""
        try:
            is_grand_tunis = devis_data["is_grand_tunis"]
            client_name = devis_data["client_name"]
            
            # Select template
            template_path = self.TEMPLATE_BASE_DEVIS if is_grand_tunis else self.TEMPLATE_BASE_DEVIS_HT
            
            if not os.path.exists(template_path):
                print(f"[DEVIS_SERVICE] Template not found: {template_path}")
                return None
            
            wb = load_workbook(template_path)
            ws = wb.active
            
            # Add logo if exists
            if os.path.exists(self.LOGO_PATH):
                img = XLImage(self.LOGO_PATH)
                img.width, img.height = 600, 80
                ws.add_image(img, "A1")
            
            # Set static fields
            self.safe_set(ws, "F2", datetime.today().strftime("%d/%m/%Y"))
            self.safe_set(ws, "B4", client_name)
            
            # Unmerge template header rows for product insertion
            for rng in list(ws.merged_cells.ranges):
                if 7 <= rng.min_row <= 8:
                    ws.unmerge_cells(str(rng))
            
            # Insert product lines
            self.insert_product_lines(ws, products)
            
            # Add footer
            self.add_footer(ws, is_grand_tunis, len(products))
            
            # Save file
            filename = f"Devis {client_name} - {devis_data['devis_number']}.xlsx"
            filename = filename.replace("/", "-").replace("\\", "-")
            file_path = os.path.join(self.OUTPUT_DIR, filename)
            
            wb.save(file_path)
            return file_path
            
        except Exception as e:
            print(f"[DEVIS_SERVICE] Error generating Excel: {e}")
            return None
    
    def safe_set(self, ws, coord: str, value):
        """Write value to cell even if it's part of a merged range."""
        cell = ws[coord]
        try:
            cell.value = value
        except AttributeError:
            for rng in ws.merged_cells.ranges:
                if coord in rng:
                    ws.cell(rng.min_row, rng.min_col).value = value
                    break
    
    def clone_row_style(self, ws, src_row: int, dst_row: int):
        """Clone styling from source row to destination row."""
        for c in range(1, ws.max_column + 1):
            if ws.cell(src_row, c).has_style:
                ws.cell(dst_row, c)._style = copy(ws.cell(src_row, c)._style)
    
    def insert_product_lines(self, ws, products: List[Dict]):
        """Insert product lines into the worksheet."""
        start_row = 7
        current_row = start_row
        
        for i, product in enumerate(products):
            if i > 0:
                current_row += 1
                ws.insert_rows(current_row)
                self.clone_row_style(ws, start_row, current_row)
            
            # Merge cells for product name
            ws.merge_cells(f"A{current_row}:B{current_row}")
            ws[f"A{current_row}"] = product["name"]
            ws[f"A{current_row}"].alignment = Alignment(wrap_text=True, vertical="top")
            
            # Set row height based on product name length
            lines = math.ceil(len(product["name"]) / 40)
            ws.row_dimensions[current_row].height = max(15, lines * 15)
            
            # Set unit (km for P004, m³ for others)
            unit = "km" if product["code"].lower() == "p004" else "1 m³"
            ws[f"C{current_row}"] = unit
            
            # Set amounts
            total_ht = product["total"]
            ws[f"D{current_row}"] = total_ht
            ws[f"E{current_row}"] = f"=D{current_row}*0.01"  # 1% FODEC
            
            # Use dynamic TVA rate for Excel formula
            tva_rate = get_current_tva_rate()
            ws[f"F{current_row}"] = f"=(D{current_row}+E{current_row})*{tva_rate}"  # Dynamic TVA
            ws[f"G{current_row}"] = f"=D{current_row}+E{current_row}+F{current_row}"  # Total TTC
    
    def add_footer(self, ws, is_grand_tunis: bool, product_count: int):
        """Add footer information to the worksheet."""
        current_row = 7 + product_count + 2
        
        footer_lines = [
            ("** Le client doit présenter la source d'eau.", "FF0000"),
            ("** La confirmation par bon de commande", "FF0000"),
            ("** Cette offre de prix est valable pour une durée de 15 jours", "FF0000"),
        ]
        
        if is_grand_tunis:
            footer_lines.append((
                "** Ces Offres sont valables uniquement pour les projets situés dans la grande Tunis", 
                "FF0000"
            ))
        
        footer_lines += [
            ("Nous restons à votre disposition pour toutes autres informations complémentaires.", "000080"),
            ("Veuillez agréer, Monsieur, nos sincères salutations.", "000000"),
        ]
        
        for text, color in footer_lines:
            ws.insert_rows(current_row)
            ws.merge_cells(f"A{current_row}:G{current_row}")
            ws[f"A{current_row}"].value = text
            ws[f"A{current_row}"].font = Font(color=color, bold=True, size=12)
            ws[f"A{current_row}"].alignment = Alignment(vertical="center")
            current_row += 1
        
        # Add signature
        ws.merge_cells(f"E{current_row}:G{current_row}")
        ws[f"E{current_row}"] = "la direction"
        ws[f"E{current_row}"].font = Font(bold=True, size=18, color="60497A")
        ws[f"E{current_row}"].alignment = Alignment(horizontal="center")
        current_row += 3
        
        # Add company footer
        self.add_company_footer(ws, current_row)
    
    def add_company_footer(self, ws, start_row: int):
        """Add company contact footer."""
        ws.merge_cells(f"A{start_row}:B{start_row}")
        ws[f"A{start_row}"] = "STFOOM"
        ws[f"A{start_row}"].font = Font(color="FFFFFF", bold=True)
        ws[f"A{start_row}"].fill = PatternFill("solid", start_color="1F4E78", end_color="1F4E78")
        
        contacts = [
            ("Forme de pente", "Tel : 79408408"),
            ("Sous revêtement", "Fax : 79408942"),
            ("Entre double cloison", "Mail : tunisfoom2001@yahoo.fr"),
            ("Chape de rattrapage", "Mail : tunisfoom2001@yahoo.fr"),
            ("Protection lourde", "Page Facebook : STFOOM Béton cellulaire"),
        ]
        
        current_row = start_row + 1
        for label, contact in contacts:
            ws.merge_cells(f"A{current_row}:C{current_row}")
            ws.merge_cells(f"D{current_row}:G{current_row}")
            ws[f"A{current_row}"] = label
            ws[f"D{current_row}"] = contact
            ws[f"A{current_row}"].font = ws[f"D{current_row}"].font = Font(bold=True, color="366092")
            ws[f"D{current_row}"].alignment = Alignment(horizontal="right")
            current_row += 1
    
    def get_all_devis(self) -> List[Dict[str, Any]]:
        """Get all devis records."""
        return self.devis_repo.get_all_devis()
    
    def get_devis_by_id(self, devis_id: int) -> Optional[Dict[str, Any]]:
        """Get devis by ID with items."""
        devis = self.devis_repo.get_devis_by_id(devis_id)
        if devis:
            devis["items"] = self.devis_repo.get_devis_items(devis_id)
        return devis
    
    def get_devis_by_client(self, client_name: str) -> List[Dict[str, Any]]:
        """Get all devis for a specific client."""
        return self.devis_repo.get_devis_by_client(client_name)
    
    def update_devis_status(self, devis_id: int, status: str) -> Dict[str, Any]:
        """Update devis status."""
        valid_statuses = ["draft", "sent", "accepted", "rejected", "expired"]
        if status not in valid_statuses:
            return {
                "success": False,
                "error": f"Status invalide. Options: {', '.join(valid_statuses)}"
            }
        
        success = self.devis_repo.update_devis_status(devis_id, status)
        return {
            "success": success,
            "message": f"Statut mis à jour: {status}" if success else "Erreur lors de la mise à jour"
        }
    
    def get_monthly_stats(self, year: int, month: int) -> Dict[str, Any]:
        """Get monthly devis statistics."""
        return self.devis_repo.get_monthly_devis_stats(year, month)
    
    def delete_devis(self, devis_id: int) -> Dict[str, Any]:
        """Delete a devis."""
        success = self.devis_repo.delete_devis(devis_id)
        return {
            "success": success,
            "message": "Devis supprimé avec succès" if success else "Erreur lors de la suppression"
        }
