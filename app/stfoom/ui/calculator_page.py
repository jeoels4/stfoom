import tkinter as tk
from tkinter import messagebox, ttk
# from stfoom.logicold.calculator import calculate_tax, convert_time  # DISABLED: migrated to utility functions

# Import tax system for dynamic rates
try:
    from ..logic.taxes import get_current_tva_rate, get_current_tva_percentage, get_current_tva_name
except ImportError as e:
    print(f"[CALCULATOR] Tax system import failed: {e}")
    # Fallback functions
    def get_current_tva_rate(): return 0.19
    def get_current_tva_percentage(): return 19.0
    def get_current_tva_name(): return "TVA 19%"

# Simple utility functions replacing logicold.calculator
def calculate_tax(amount_ht, tax_rate=None):
    """Calculate tax amount and total including tax using dynamic rate"""
    try:
        amount_ht = float(amount_ht)
        # Use dynamic tax rate if not specified
        if tax_rate is None:
            tax_rate = get_current_tva_percentage()
        
        tax_amount = amount_ht * (tax_rate / 100)
        total_ttc = amount_ht + tax_amount
        return {
            "amount_ht": amount_ht,
            "tax_amount": tax_amount,
            "total_ttc": total_ttc,
            "tax_rate": tax_rate
        }
    except (ValueError, TypeError):
        return None

def convert_time(min_str: str, hr_str: str):
    """Convert between minutes and hours"""
    try:
        if min_str:
            mins = float(min_str)
            return {"hrs": mins / 60}
        elif hr_str:
            hrs = float(hr_str)
            return {"mins": hrs * 60}
        return None
    except (ValueError, TypeError):
        return None

def calculate_tax(ht, ttc, remise_pct=0.0):
    """Calculate tax for calculator with HT/TTC and remise - using dynamic TVA rate"""
    try:
        # Get dynamic TVA rate
        tva_rate = get_current_tva_rate()
        
        # Handle calculation based on whether HT or TTC is provided
        if ht and ht.strip():
            # Calculate from HT
            ht_val = float(ht)
            
            # Apply remise if any
            if remise_pct > 0:
                ht_val = ht_val * (1 - remise_pct / 100)
            
            # Calculate FODEC (1%)
            fodec = ht_val * 0.01
            
            # Calculate TVA using dynamic rate
            tva = (ht_val + fodec) * tva_rate
            
            # Calculate TTC
            ttc_val = ht_val + fodec + tva
            
            return {
                "ht": ht_val,
                "fodec": fodec,
                "tva": tva,
                "ttc": ttc_val
            }
            
        elif ttc and ttc.strip():
            # Calculate from TTC (reverse calculation)
            ttc_val = float(ttc)
            
            # Reverse calculation: TTC = HT + FODEC + TVA = HT + (HT * 0.01) + ((HT + HT * 0.01) * tva_rate)
            # TTC = HT * (1 + 0.01 + tva_rate + 0.01 * tva_rate)
            # TTC = HT * (1.01 + tva_rate * 1.01)
            # TTC = HT * (1.01 * (1 + tva_rate))
            divisor = 1.01 * (1 + tva_rate)
            ht_val = ttc_val / divisor
            
            # Apply remise if any
            if remise_pct > 0:
                ht_val = ht_val / (1 - remise_pct / 100)
            
            fodec = ht_val * 0.01
            tva = (ht_val + fodec) * tva_rate
            
            return {
                "ht": ht_val,
                "fodec": fodec,
                "tva": tva,
                "ttc": ttc_val
            }
        else:
            return None
            
    except (ValueError, TypeError):
        return None

class CalculatorPage(ttk.Frame):
    def __init__(self, parent, go_home):
        super().__init__(parent, style="FactureMain.TFrame")
        self.pack(fill="both", expand=True)
        self.go_home = go_home

        # ---------- header ----------
        header_frame = ttk.Frame(self, style="FactureHeader.TFrame")
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(header_frame, text="⬅️ Retour", command=go_home, style="FactureBack.TButton").pack(side="left", padx=(10, 20), pady=18)
        ttk.Label(header_frame, text="Calculateur & Convertisseur", font=("Segoe UI", 22, "bold"), style="FactureHeader.TLabel").pack(side="left", pady=18)

        # TAX Calculator Section
        tax_frame = ttk.LabelFrame(self, text="Calculateur TVA", style="FactureSection.TLabelframe")
        tax_frame.pack(fill="x", padx=30, pady=(0, 10), ipadx=8, ipady=8)
        frame1 = ttk.Frame(tax_frame)
        frame1.pack(pady=5, padx=10)

        self.ht_var, self.fodec_var, self.tva_var, self.ttc_var = (tk.StringVar() for _ in range(4))
        self.remise_var = tk.BooleanVar(value=False)
        self.remise_pct_var = tk.StringVar()

        def clear_tax_boxes(except_var):
            if except_var in (self.remise_pct_var,):
                return
            if except_var is not self.ht_var:    self.ht_var.set("")
            if except_var is not self.fodec_var: self.fodec_var.set("")
            if except_var is not self.tva_var:   self.tva_var.set("")
            if except_var is not self.ttc_var:   self.ttc_var.set("")

        # Remise Checkbox and Entry
        remise_frame = ttk.Frame(tax_frame)
        remise_frame.pack(pady=5, padx=10, anchor="w")
        ttk.Checkbutton(remise_frame, text="Remise", variable=self.remise_var, command=self.on_remise_toggle).pack(side="left")
        self.remise_entry = ttk.Entry(remise_frame, textvariable=self.remise_pct_var, width=5, state="disabled")
        self.remise_entry.pack(side="left", padx=5)

        ttk.Label(frame1, text="HT").grid(row=0, column=0, padx=5)
        ht_entry = ttk.Entry(frame1, textvariable=self.ht_var, width=12)
        ht_entry.grid(row=1, column=0, padx=5)
        ht_entry.bind("<KeyRelease>", lambda e: clear_tax_boxes(self.ht_var))

        ttk.Label(frame1, text="FODEC (1%)").grid(row=0, column=1, padx=5)
        fodec_entry = ttk.Entry(frame1, textvariable=self.fodec_var, width=12, state="readonly")
        fodec_entry.grid(row=1, column=1, padx=5)

        # Dynamic TVA label from settings
        try:
            tva_label_text = get_current_tva_name()
        except:
            tva_label_text = "TVA (19%)"
        
        ttk.Label(frame1, text=tva_label_text).grid(row=0, column=2, padx=5)
        tva_entry = ttk.Entry(frame1, textvariable=self.tva_var, width=12, state="readonly")
        tva_entry.grid(row=1, column=2, padx=5)

        ttk.Label(frame1, text="TTC").grid(row=0, column=3, padx=5)
        ttc_entry = ttk.Entry(frame1, textvariable=self.ttc_var, width=12)
        ttc_entry.grid(row=1, column=3, padx=5)
        ttc_entry.bind("<KeyRelease>", lambda e: clear_tax_boxes(self.ttc_var))

        # Calcul button (green)
        calc_btn = tk.Button(
            tax_frame,
            text="Calcul",
            command=self.on_calcul,
            font=("Segoe UI", 15, "bold"),
            bg="#27ae60",
            fg="#fff",
            activebackground="#219150",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        calc_btn.pack(pady=18, ipadx=24, ipady=8)

        # Time Converter Section
        time_frame = ttk.LabelFrame(self, text="Convertisseur Temps", style="FactureSection.TLabelframe")
        time_frame.pack(fill="x", padx=30, pady=(0, 10), ipadx=8, ipady=8)
        frame2 = ttk.Frame(time_frame)
        frame2.pack(pady=5, padx=10)

        self.min_to_hr_var, self.hr_to_min_var = (tk.StringVar() for _ in range(2))

        def clear_time_boxes(except_var):
            if except_var is self.min_to_hr_var:
                self.hr_to_min_var.set("")
            elif except_var is self.hr_to_min_var:
                self.min_to_hr_var.set("")

        ttk.Label(frame2, text="Minutes").grid(row=0, column=0, padx=30)
        min_entry = ttk.Entry(frame2, textvariable=self.min_to_hr_var, width=15)
        min_entry.grid(row=1, column=0, padx=10)
        min_entry.bind("<KeyRelease>", lambda e: clear_time_boxes(self.min_to_hr_var))

        ttk.Label(frame2, text="Heures").grid(row=0, column=1, padx=30)
        hr_entry = ttk.Entry(frame2, textvariable=self.hr_to_min_var, width=15)
        hr_entry.grid(row=1, column=1, padx=10)
        hr_entry.bind("<KeyRelease>", lambda e: clear_time_boxes(self.hr_to_min_var))

        # Convertir Temps button (blue)
        convert_btn = tk.Button(
            time_frame,
            text="Convertir Temps",
            command=self.on_convert_time,
            font=("Segoe UI", 15, "bold"),
            bg="#0074d9",
            fg="#fff",
            activebackground="#005fa3",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        convert_btn.pack(pady=18, ipadx=24, ipady=8)

    def on_remise_toggle(self):
        if self.remise_var.get():
            self.remise_entry.config(state="normal")
        else:
            self.remise_entry.config(state="disabled")
            self.remise_pct_var.set("")
            self.ht_var.set("")
            self.fodec_var.set("")
            self.tva_var.set("")
            self.ttc_var.set("")

    def on_calcul(self):
        try:
            ht = self.ht_var.get()
            ttc = self.ttc_var.get()
            remise_pct = 0.0
            if self.remise_var.get():
                try:
                    remise_pct = float(self.remise_pct_var.get())
                    if not (0 <= remise_pct <= 100):
                        raise ValueError
                except:
                    messagebox.showerror("Erreur", "Remise % invalide (doit être entre 0 et 100)")
                    return
            result = calculate_tax(ht, ttc, remise_pct)
            if result is None:
                messagebox.showwarning("Erreur", "Saisissez HT ou TTC")
                return
            if ht.strip() != "":
                self.ht_var.set(str(round(result["ht"], 2)))
                self.ttc_var.set(str(round(result["ttc"], 2)))
            elif ttc.strip() != "":
                self.ht_var.set(str(round(result["ht"], 2)))
            self.fodec_var.set(str(round(result["fodec"], 2)))
            self.tva_var.set(str(round(result["tva"], 2)))
        except ValueError:
            messagebox.showerror("Erreur", "Entrée invalide")

    def on_convert_time(self):
        try:
            mins = self.min_to_hr_var.get()
            hrs = self.hr_to_min_var.get()
            result = convert_time(mins, hrs)
            if result is None:
                messagebox.showinfo("Info", "Entrez un champ au moins")
                return
            if "mins" in result:
                self.hr_to_min_var.set(str(round(result["mins"], 2)))
            if "hrs" in result:
                self.min_to_hr_var.set(str(round(result["hrs"], 2)))
        except ValueError:
            messagebox.showerror("Erreur", "Entrée invalide")
