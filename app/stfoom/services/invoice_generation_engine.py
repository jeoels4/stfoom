"""
Invoice Generation Engine - Phase 2I Migration
===============================================
Complete invoice generation logic with Excel templates, tax calculations,
and precise column mappings. Migrated from logic/invoice_gen.py.

⚠️ CRITICAL: This module handles sensitive Excel generation with specific
column mappings, tax calculations, and template formats.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
import pandas as pd

# Import tax system for dynamic rates
try:
    from ..logic.taxes import get_current_tva_rate, get_current_tva_percentage
except ImportError as e:
    print(f"[INVOICE_ENGINE] Tax system import failed: {e}")
    # Fallback functions
    def get_current_tva_rate(): return 0.19
    def get_current_tva_percentage(): return 19.0

class InvoiceGenerator:
    """Complete invoice generation engine with Excel support."""
    
    def __init__(self, facture_repository):
        """Initialize invoice generator with repository dependency."""
        self.facture_repo = facture_repository
        
        # Setup paths - CRITICAL for Excel templates and output
        self._setup_paths()
        
        # Validate critical files exist
        self._validate_critical_files()
    
    def _setup_paths(self):
        """Setup all critical paths for templates, output, and assets."""
        # Data directories
        self.DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "core"))
        self.DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
        self.OUTPUT_DIR = os.path.join(self.DESKTOP, "factures")
        
        # Ensure output directory exists
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        
        # Template paths - CRITICAL for Excel generation
        self.TEMPL_DIR = os.path.join(self.DATA_DIR, "templates")
        self.template_sans = os.path.join(self.TEMPL_DIR, "facture sans remise.xlsx")
        self.template_rem = os.path.join(self.TEMPL_DIR, "facture avec remise.xlsx")
        
        # Logo path
        self.LOGO_PATH = os.path.join(self.DATA_DIR, "logo", "stfoomlogo.jpg")
        
        print(f"[INVOICE GEN] Paths initialized:")
        print(f"  - Templates: {self.TEMPL_DIR}")
        print(f"  - Output: {self.OUTPUT_DIR}")
        print(f"  - Logo: {self.LOGO_PATH}")
    
    def _validate_critical_files(self):
        """Validate that all critical files exist."""
        critical_files = [
            (self.template_sans, "Template sans remise"),
            (self.template_rem, "Template avec remise"),
        ]
        
        missing_files = []
        for file_path, description in critical_files:
            if not os.path.exists(file_path):
                missing_files.append(f"{description}: {file_path}")
        
        if missing_files:
            # Auto-create minimal templates to avoid crashing the app
            print(f"[INVOICE GEN] Missing templates detected, creating minimal placeholders...")
            try:
                os.makedirs(self.TEMPL_DIR, exist_ok=True)
                from openpyxl import Workbook
                def _create_min_template(path: str, with_remise: bool):
                    wb = Workbook()
                    ws = wb.active
                    # Basic headers placeholders matching code below
                    ws["A2"] = "Facture XXXX-YYYY"
                    ws["A4"] = datetime.today().strftime("%d/%m/%Y")
                    ws["A6"] = "CODE"
                    ws["D3"] = "RAISON SOCIALE"
                    ws["D4"] = "ADRESSE"
                    ws["D5"] = "TVA"
                    ws["D6"] = "TEL"
                    ws["F4"] = "CHANTIER"
                    # Reserve rows for items and totals around 9-18
                    ws["B15"] = 0
                    ws["B16"] = 0
                    ws["B17"] = 0
                    ws["C15"] = 0
                    ws["C16"] = 0
                    ws["C17"] = 0
                    if with_remise:
                        ws["F13"] = 0
                        ws["F14"] = 0
                        ws["F15"] = 0
                        ws["F16"] = 0
                        ws["F17"] = 0
                        ws["F18"] = 0
                    else:
                        ws["F13"] = 0
                        ws["F14"] = 0
                        ws["F16"] = 0
                        ws["F18"] = 0
                    wb.save(path)
                if not os.path.exists(self.template_sans):
                    _create_min_template(self.template_sans, with_remise=False)
                if not os.path.exists(self.template_rem):
                    _create_min_template(self.template_rem, with_remise=True)
                print("[INVOICE GEN] Minimal templates created successfully")
            except Exception as ce:
                raise FileNotFoundError(
                    "Critical template files missing and auto-creation failed:\n" + "\n".join(missing_files) + f"\nError: {ce}"
                )
        
        print("[INVOICE GEN] All critical template files validated")
    
    def get_products_df(self) -> pd.DataFrame:
        """Get products DataFrame from repository."""
        try:
            products_data = self.facture_repo.get_all_products()
            
            if not products_data:
                print("[INVOICE GEN] No products data received from repository")
                
                # Fallback: Try direct database access (for emergency situations)
                print("[INVOICE GEN] Attempting fallback to direct database access...")
                try:
                    from stfoom.logic import db_core
                    fallback_df = db_core.load_products()
                    if not fallback_df.empty:
                        print(f"[INVOICE GEN] Fallback successful: {len(fallback_df)} products loaded")
                        return fallback_df
                except Exception as fallback_error:
                    print(f"[INVOICE GEN] Fallback failed: {fallback_error}")
                
                return pd.DataFrame()
                
            df = pd.DataFrame(products_data)
            print(f"[INVOICE GEN] Created DataFrame with {len(df)} rows and columns: {list(df.columns)}")
            
            # Ensure DataFrame has expected columns
            if df.empty:
                print("[INVOICE GEN] DataFrame is empty after creation")
                return pd.DataFrame()
                
            if 'code' not in df.columns:
                print(f"[INVOICE GEN] CRITICAL ERROR: DataFrame missing 'code' column. Available: {list(df.columns)}")
                return pd.DataFrame()
                
            return df
            
        except Exception as e:
            print(f"[INVOICE GEN] Error creating products DataFrame: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def _safe_remise_pct(self, raw: Any) -> float:
        """Safely convert remise percentage to float."""
        try:
            val = float(raw)
            return 0.0 if val != val else val  # NaN guard
        except (ValueError, TypeError):
            return 0.0
    
    def _resolve_price(self, client: Dict, prod_row: Dict, chantier_remises: Dict = None) -> float:
        """Resolve product price with chantier-specific pricing (preferred) or client-specific pricing."""
        code = prod_row["code"].upper()
        
        # First priority: chantier-specific pricing
        if chantier_remises and code in chantier_remises:
            chantier_prix = chantier_remises[code].get('prix_specifique', 0)
            if chantier_prix and chantier_prix > 0:
                return float(chantier_prix)
        
        # Second priority: client-specific pricing (legacy)
        code_lower = prod_row["code"].lower()
        specific = client.get(f"specific_{code_lower}")
        
        # Handle specific price conversion and validation
        try:
            if specific is not None and str(specific).lower() not in ['nan', 'none', '']:
                specific_float = float(specific)
                if specific_float > 0:
                    return specific_float
        except (ValueError, TypeError):
            pass  # Fall back to default price
        
        # Return default product price
        try:
            return float(prod_row["prix_ht"])
        except (ValueError, TypeError):
            return 0.0
    
    def generate_invoice(self, client: Dict, chantier: str, selection: List[Dict], 
                        nfacture_int: int, date_facture: Optional[str] = None) -> str:
        """
        Main invoice generation method - returns absolute path of the saved .xlsx invoice.
        
        ⚠️ CRITICAL: This method handles sensitive Excel generation with specific
        column mappings, tax calculations, and template formats.
        """
        print(f"[INVOICE GEN] Starting generation for invoice {nfacture_int}")
        
        # Validate inputs
        if not client:
            raise ValueError("Client information is required.")
        
        if not selection or len(selection) == 0:
            raise ValueError("At least one product must be selected.")
        
        has_rem = False
        product_rows = []
        transport_base = 0    # gross HT of product P004
        transport_remise = 0  # discount amount given on P004
        
        # Get products DataFrame for price resolution
        products_df = self.get_products_df()
        
        # Validate products DataFrame before using it
        if products_df.empty:
            error_msg = "Products DataFrame is empty - authentication may have failed or no products in database"
            print(f"[INVOICE GEN] CRITICAL ERROR: {error_msg}")
            raise ValueError(error_msg)
            
        if 'code' not in products_df.columns:
            error_msg = f"Products DataFrame missing 'code' column. Available columns: {list(products_df.columns)}"
            print(f"[INVOICE GEN] CRITICAL ERROR: {error_msg}")
            raise ValueError(error_msg)
            
        print(f"[INVOICE GEN] Products DataFrame validated: {len(products_df)} products with columns {list(products_df.columns)}")

                # Load chantier remises if chantier is provided
        chantier_remises = {}
        if chantier:
            try:
                from stfoom.services.chantier_remise_service import ChantierRemiseService
                chantier_service = ChantierRemiseService()
                chantier_remises = chantier_service.get_chantier_remises(chantier)
            except Exception as e:
                print(f"[INVOICE] Could not load chantier remises: {e}")

        # ---------- Build product rows ----------
        for item in selection:
            # Find product data
            try:
                product_data = products_df[products_df["code"] == item["code"]]
                if product_data.empty:
                    raise ValueError(f"Product {item['code']} not found in products DataFrame")
            except KeyError as e:
                error_msg = f"KeyError accessing 'code' column in products DataFrame: {e}. DataFrame columns: {list(products_df.columns)}, DataFrame shape: {products_df.shape}"
                print(f"[INVOICE GEN] CRITICAL ERROR: {error_msg}")
                raise ValueError(error_msg)

            row = product_data.iloc[0]
            qty = item["qty"]
            pu = self._resolve_price(client, row, chantier_remises)
            
            # Calculate remise - Enhanced logic for double-sided behavior
            product_code = row["code"].upper()
            remise_pct = 0
            
            # Check chantier remise first
            if chantier_remises and product_code in chantier_remises:
                chantier_remise = self._safe_remise_pct(chantier_remises[product_code].get('remise_percentage', 0))
                if chantier_remise > 0:
                    # Use chantier remise if it exists and > 0
                    remise_pct = chantier_remise
                else:
                    # Chantier exists but no remise (0%) - check if universal remise can be used
                    universal_remise = self._safe_remise_pct(client.get(f"remise_{row['code'].lower()}", 0))
                    if universal_remise > 0:
                        # Double-sided behavior: Use universal remise with chantier pricing
                        remise_pct = universal_remise
            else:
                # No chantier entry - use universal remise (legacy behavior)
                remise_pct = self._safe_remise_pct(client.get(f"remise_{row['code'].lower()}", 0))
            
            has_rem = has_rem or remise_pct > 0
            
            # Calculate amounts
            mt_htva = qty * pu
            remise_amt = mt_htva * remise_pct / 100
            net_htva = mt_htva - remise_amt
            
            # Special handling for transport (P004)
            if row["code"] == "P004":
                transport_base = mt_htva
                transport_remise = remise_amt
            
            product_rows.append({
                "code": row["code"],
                "designation": row["designation"],
                "qty": qty,
                "pu": pu,
                "mt_htva": mt_htva,
                "remise_pct": remise_pct,
                "remise_amt": remise_amt,
                "net_htva": net_htva,
            })
        
        # ---------- Choose template ----------
        template_path = self.template_rem if has_rem else self.template_sans
        
        print(f"[INVOICE GEN] Using template: {'avec remise' if has_rem else 'sans remise'}")
        
        # Load Excel workbook
        try:
            wb = load_workbook(template_path)
            ws = wb.active
            if ws is None:
                raise ValueError(f"Active worksheet is None in template: {template_path}")
        except Exception as e:
            raise Exception(f"Failed to load template {template_path}: {str(e)}")
        
        # ---------- Fill header information ----------
        inv_no = nfacture_int
        year_part = str(inv_no)[:4]
        sequence_num = int(str(inv_no)[4:].rjust(5, '0'))
        inv_name = f"Facture {sequence_num:05}-{year_part}"
        facture_date = date_facture or datetime.today().strftime("%d/%m/%Y")
        
        # CRITICAL: Specific cell mappings for header
        ws["A2"] = inv_name
        ws["A4"] = facture_date  
        ws["A6"] = client["code_client"]
        ws["D3"] = client["raison_sociale"]
        ws["D4"] = client["adresse"]
        ws["D5"] = client["tva"]
        ws["D6"] = str(client["tel"])
        ws["F4"] = chantier
        
        # Add logo if available
        if os.path.exists(self.LOGO_PATH):
            img = XLImage(self.LOGO_PATH)
            img.width, img.height = 600, 80
            ws.add_image(img, "A1")
        
        # ---------- Fill product data ----------
        # More robust mapping: place products sequentially starting at row 9
        start_row = 9
        base_ht_net = 0
        total_rem = 0
        for idx, p in enumerate(product_rows):
            r = start_row + idx
            ws[f"A{r}"] = p["designation"]
            ws[f"D{r}"] = p["qty"]
            ws[f"E{r}"] = p["pu"]
            ws[f"F{r}"] = p["mt_htva"]
            
            if has_rem and p["remise_pct"] > 0:
                ws[f"G{r}"] = f"{int(p['remise_pct'])}%"
            
            base_ht_net += p["net_htva"] if has_rem else p["mt_htva"]
            total_rem += p["remise_amt"]
        
        # ---------- Calculate taxes (CRITICAL CALCULATIONS) ----------
        # Transport remise excluded from tax bases
        adjusted_base_ht = base_ht_net + transport_remise  # add back P004 remise only
        
        # FODEC calculation (1% on base minus transport)
        fodec_base = adjusted_base_ht - transport_base
        fodec = fodec_base * 0.01
        
        # TVA calculation using dynamic rate from settings (on base + fodec minus transport)
        tva_base = adjusted_base_ht + fodec - transport_base
        tva_rate = get_current_tva_rate()  # Dynamic TVA rate from settings
        tva19 = tva_base * tva_rate
        
        # TVA 7% on transport only
        tva7 = transport_base * 0.07
        
        # Get timbre from settings service (configurable via admin)
        try:
            from ..services.settings_service import SettingsService
            settings_service = SettingsService()
            # Try both possible keys for timbre settings
            timbre = settings_service.get_setting("taxes", "timbre_amount", {})
            if timbre is None:
                timbre = settings_service.get_setting("taxes", "timbre_fiscal", {})
            if timbre is None:
                timbre = 1.0  # Default fallback
                print(f"[INVOICE GEN] No timbre setting found, using default: {timbre} DT")
            else:
                print(f"[INVOICE GEN] Using timbre from settings: {timbre} DT")
        except Exception as e:
            print(f"[INVOICE GEN] Error loading timbre from settings: {e}")
            timbre = 1.0  # Fallback value
            print(f"[INVOICE GEN] Using fallback timbre: {timbre} DT")
        
        # Total calculations
        # 🔧 CRITICAL FIX: Include transport_base in TTC calculation
        total_ttc = base_ht_net + transport_base + fodec + tva19 + tva7 + timbre
        total_tax = fodec + tva19 + tva7
        
        # Clear transport line in summary if no transport
        if transport_base == 0:
            ws["A17"] = ws["B17"] = ws["C17"] = ""
        
        # Clear any formulas so our numbers stick
        for c in ("C15", "C16", "C17"):
            ws[c].value = None
        
        # ---------- Fill tax and total sections (CRITICAL CELL MAPPINGS) ----------
        if has_rem:
            ws["F14"] = total_rem                     # show remise as positive
        
        # Tax base columns
        ws["B15"] = fodec_base
        ws["B16"] = tva_base  
        ws["B17"] = transport_base
        
        # Tax amount columns
        ws["C15"] = fodec
        ws["C16"] = tva19
        ws["C17"] = tva7
        
        # Total columns
        if has_rem:
            ws["F13"] = base_ht_net + total_rem       # gross HT before remise
            ws["F15"] = base_ht_net                   # HT net (after remise)
            ws["F16"] = total_tax
            ws["F17"] = timbre
            ws["F18"] = total_ttc
        else:
            ws["F13"] = base_ht_net
            ws["F14"] = total_tax
            ws["F16"] = timbre
            ws["F18"] = total_ttc
        
        # ---------- Save Excel file ----------
        out_path = os.path.join(self.OUTPUT_DIR, f"{inv_name}.xlsx")
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)  # Ensure output folder exists
        wb.save(out_path)
        
        print(f"[INVOICE GEN] Excel file saved: {out_path}")
        
        # ---------- Save to database ----------
        # Prepare enhanced details with pricing information for regeneration
        enhanced_details = []
        for item in selection:
            product_data = products_df[products_df["code"] == item["code"]].iloc[0]
            enhanced_item = {
                "code": item["code"],
                "qty": item["qty"],
                "original_price": self._resolve_price(client, product_data),
                "original_remise_pct": self._safe_remise_pct(client.get(f"remise_{product_data['code'].lower()}", 0))
            }
            enhanced_details.append(enhanced_item)
        
        # Check if invoice already exists in database
        if not self._invoice_exists_in_db(inv_no):
            # Use provided date_facture or default to today's date
            db_date = date_facture
            if db_date:
                # Convert from dd/mm/yyyy to yyyy-mm-dd for database storage
                try:
                    db_date = datetime.strptime(db_date, "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError:
                    # Fallback to today if date parsing fails
                    db_date = datetime.today().strftime("%Y-%m-%d")
            else:
                db_date = datetime.today().strftime("%Y-%m-%d")
            
            # Calculate individual product amounts
            mt_ht_p001 = next((p["net_htva"] for p in product_rows if p["code"] == "P001"), 0)
            mt_ht_p002 = next((p["net_htva"] for p in product_rows if p["code"] == "P002"), 0)
            mt_ht_p003 = next((p["net_htva"] for p in product_rows if p["code"] == "P003"), 0)
            
            # Calculate total mt_ht from all products
            total_mt_ht = mt_ht_p001 + mt_ht_p002 + mt_ht_p003
            
            vente = {
                "nfacture": inv_no,
                "date_facture": db_date,
                "code_client": client["code_client"],
                "raison_sociale": client["raison_sociale"],
                "mt_ht_p001": mt_ht_p001,
                "mt_ht_p002": mt_ht_p002,
                "mt_ht_p003": mt_ht_p003,
                "fodec": fodec,
                "tva19": tva19,
                "transport_p004": transport_base,
                "tva7": tva7,
                "timbre": timbre,
                "ttc": total_ttc,
                "chantier": chantier or "",
                "details": json.dumps(enhanced_details, ensure_ascii=False),
            }
            
            try:
                self._insert_in_ventes(vente)
                print(f"[INVOICE GEN] Invoice {inv_no} saved to database successfully")
            except Exception as e:
                print(f"[INVOICE GEN] Error saving to database: {e}")
                # Continue anyway since the file was generated
        else:
            print(f"[INVOICE GEN] Invoice {inv_no} already exists in database, skipping insert")
        
        return out_path
    
    def _invoice_exists_in_db(self, nfacture_int: int) -> bool:
        """Check if invoice exists in database."""
        return self.facture_repo.invoice_exists(nfacture_int)
    
    def _insert_in_ventes(self, row: Dict):
        """Insert vente record into database."""
        import sqlite3
        from config.settings import get_db_path
        
        try:
            with sqlite3.connect(get_db_path()) as conn:
                cols = ", ".join(row.keys())
                placeholders = ", ".join(f":{k}" for k in row)
                query = f"INSERT INTO ventes ({cols}) VALUES ({placeholders})"
                cursor = conn.cursor()
                cursor.execute(query, row)
                conn.commit()
        except Exception as e:
            print(f"[INVOICE GEN] Database write error: {e}")
            raise
    
    def regenerate_invoice(self, nfacture_int: int) -> Optional[str]:
        """
        Regenerate an existing invoice using stored details.
        
        Args:
            nfacture_int: Invoice number to regenerate
            
        Returns:
            Optional[str]: Path to regenerated file or None if failed
        """
        try:
            # Get vente record
            vente = self.facture_repo.get_vente_by_invoice_number(nfacture_int)
            if not vente:
                print(f"[INVOICE GEN] Invoice {nfacture_int} not found for regeneration")
                return None
            
            # Get client
            client = self.facture_repo.get_client_by_code(vente["code_client"])
            if client is None:
                print(f"[INVOICE GEN] Client {vente['code_client']} not found")
                return None
            
            # Parse details
            try:
                selection = json.loads(vente.get("details", "[]"))
            except Exception as e:
                print(f"[INVOICE GEN] Error parsing details: {e}")
                selection = []
            
            if not selection:
                print(f"[INVOICE GEN] No product details found for regeneration")
                return None
            
            # Regenerate invoice
            path = self.generate_invoice(
                client=client,
                chantier=vente.get("chantier", ""),
                selection=selection,
                nfacture_int=nfacture_int,
                date_facture=vente.get("date_facture"),
            )
            
            print(f"[INVOICE GEN] Invoice {nfacture_int} regenerated: {path}")
            return path
            
        except Exception as e:
            print(f"[INVOICE GEN] Error regenerating invoice {nfacture_int}: {e}")
            return None
