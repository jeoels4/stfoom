"""
Cheque Print Service
====================
Renders and prints cheques based on a configurable layout (positions in mm).
Supports Windows printing via the shell (os.startfile(..., 'print')).
"""
from __future__ import annotations
import os
import io
import math
import tempfile
import platform
from datetime import datetime
from typing import Dict, Tuple, List, Optional

from PIL import Image, ImageDraw, ImageFont
try:
    # Optional for exact-size Windows printing
    from PIL import ImageWin  # type: ignore
except Exception:
    ImageWin = None  # type: ignore

from app.stfoom.data.cheque_print_repository import ChequePrintRepository


class ChequePrintService:
    def __init__(self, repo: ChequePrintRepository | None = None, dpi: int = 300) -> None:
        self.repo = repo or ChequePrintRepository()
        self.dpi = dpi
        # Default font setup
        # Larger for better readability on cheque paper
        # You can fine-tune these later if needed
        self.font_regular = self._load_font(36)
        # Default bold (date/lieu)
        self.font_bold = self._load_font(42, bold=True)
        # Per-field bold sizes
        self.font_bold_numbers = self._load_font(63, bold=True)      # montant_number (x1.5)
        self.font_bold_letters = self._load_font(48, bold=True)      # montant_letters and beneficiaire
        # Small bold label for overlays (e.g., DT above decimal point)
        self.font_bold_small_label = self._load_font(20, bold=True)

    def _load_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        # Try Windows fonts first
        candidates = []
        if platform.system().lower() == 'windows':
            win_dir = os.environ.get('WINDIR', r'C:\\Windows')
            if bold:
                candidates.extend([
                    os.path.join(win_dir, 'Fonts', 'arialbd.ttf'),
                    os.path.join(win_dir, 'Fonts', 'segoeuib.ttf'),
                ])
            else:
                candidates.extend([
                    os.path.join(win_dir, 'Fonts', 'arial.ttf'),
                    os.path.join(win_dir, 'Fonts', 'segoeui.ttf'),
                ])
        # Fallbacks
        candidates.extend([
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
        ])
        for path in candidates:
            try:
                if os.path.exists(path):
                    return ImageFont.truetype(path, size=size)
            except Exception:
                continue
        return ImageFont.load_default()

    @staticmethod
    def mm_to_px(mm: float, dpi: int) -> int:
        return int(round(mm * dpi / 25.4))

    def _page_size_px(self) -> Tuple[int, int]:
        # Page size from repository with env overrides
        try:
            width_mm, height_mm = self.repo.get_page_size_mm()
        except Exception:
            width_mm, height_mm = 175.0, 80.0
        # Allow environment overrides for quick tuning
        try:
            env_w = os.environ.get('STFOOM_CHEQUE_WIDTH_MM')
            env_h = os.environ.get('STFOOM_CHEQUE_HEIGHT_MM')
            if env_w:
                width_mm = float(env_w)
            if env_h:
                height_mm = float(env_h)
        except Exception:
            pass
        return self.mm_to_px(width_mm, self.dpi), self.mm_to_px(height_mm, self.dpi)

    def render_cheque_image(self, data: Dict[str, str]) -> Image.Image:
        """
        data keys: montant_number, montant_letters, beneficiaire, date, lieu
        returns PIL Image ready for printing (RGB, white background)
        """
        width_px, height_px = self._page_size_px()
        img = Image.new('RGB', (width_px, height_px), 'white')
        draw = ImageDraw.Draw(img)

        layout = self.repo.get_layout()

        def _text_width_px(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                return max(0, int(bbox[2] - bbox[0]))
            except Exception:
                try:
                    return int(font.getlength(text))  # type: ignore[attr-defined]
                except Exception:
                    try:
                        return int(draw.textlength(text, font=font))  # type: ignore[attr-defined]
                    except Exception:
                        return len(text) * 8

        def _fit_line_to_width(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_w_px: int) -> tuple[str, str]:
            words = text.split()
            if not words:
                return "", ""
            acc: list[str] = []
            for w in words:
                candidate = (" ".join(acc + [w])).strip()
                if _text_width_px(candidate, font) <= max_w_px:
                    acc.append(w)
                else:
                    break
            first = " ".join(acc).strip()
            if not first:
                return "", text.strip()
            remainder = " ".join(words[len(acc):]).strip()
            return first, remainder

        def place_text(key: str, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont):
            pos = layout.get(key, {"x": 10.0, "y": 10.0})
            x = self.mm_to_px(float(pos.get("x", 10.0)), self.dpi)
            y = self.mm_to_px(float(pos.get("y", 10.0)), self.dpi)
            draw.text((x, y), text, fill='black', font=font)

        # Per-field font sizes
        montant_number_text = data.get('montant_number', '') or ''
        place_text('montant_number', montant_number_text, self.font_bold_numbers)
        # If there's a decimal point in montant_number, draw a small 'DT' above it
        try:
            dot_idx = montant_number_text.find('.')
            if dot_idx != -1:
                pos_num = layout.get('montant_number', {"x": 10.0, "y": 10.0})
                base_x = self.mm_to_px(float(pos_num.get('x', 10.0)), self.dpi)
                base_y = self.mm_to_px(float(pos_num.get('y', 10.0)), self.dpi)
                # Measure width up to the dot and width of the dot itself to find center
                pre_text = montant_number_text[:dot_idx]
                bbox_pre = draw.textbbox((0, 0), pre_text, font=self.font_bold_numbers)
                pre_w = max(0, int(bbox_pre[2] - bbox_pre[0]))
                bbox_dot = draw.textbbox((0, 0), '.', font=self.font_bold_numbers)
                dot_w = max(1, int(bbox_dot[2] - bbox_dot[0]))
                dot_center_x = base_x + pre_w + (dot_w // 2)
                # Size and position for the 'DT' overlay
                label = 'DT'
                bbox_label = draw.textbbox((0, 0), label, font=self.font_bold_small_label)
                label_w = max(0, int(bbox_label[2] - bbox_label[0]))
                # Place a bit above the number line (approx 2mm)
                y_offset = self.mm_to_px(2.0, self.dpi)
                dt_x = int(dot_center_x - (label_w // 2))
                dt_y = int(base_y - y_offset)
                draw.text((dt_x, dt_y), label, fill='black', font=self.font_bold_small_label)
        except Exception:
            # Non-fatal: if anything goes wrong, skip the overlay
            pass
        # Two-line amount in letters with adjustable box widths
        letters_full = (data.get('montant_letters') or '').strip()
        box1 = layout.get('montant_letters_1', {"x": 18.0, "y": 26.0, "w": 100.0, "h": 10.0})
        box2 = layout.get('montant_letters_2', {"x": 18.0, "y": 38.0, "w": 140.0, "h": 10.0})
        max_w1_px = self.mm_to_px(float(box1.get('w', 100.0)), self.dpi)
        max_w2_px = self.mm_to_px(float(box2.get('w', 140.0)), self.dpi)
        line1, remainder = _fit_line_to_width(letters_full, self.font_bold_letters, max_w1_px)
        line2, _ = _fit_line_to_width(remainder, self.font_bold_letters, max_w2_px)
        place_text('montant_letters_1', line1, self.font_bold_letters)
        place_text('montant_letters_2', line2, self.font_bold_letters)
        place_text('beneficiaire', data.get('beneficiaire', ''), self.font_bold_letters)
        # Normalize date to dd/mm/yyyy before placing
        _date_raw = data.get('date', '') or ''
        try:
            _date_fmt = self._format_date_ddmmyyyy(_date_raw)
        except Exception:
            _date_fmt = _date_raw
        place_text('date', _date_fmt, self.font_bold)
        place_text('lieu', data.get('lieu', ''), self.font_bold)

        return img

    def _format_date_ddmmyyyy(self, value: str) -> str:
        """Best-effort formatting to dd/mm/yyyy. Keeps original if parsing fails."""
        if not value:
            return value
        s = value.strip()
        # Quick path: already dd/mm/yyyy (allow single-digit d/m and normalize)
        from datetime import datetime as _dt
        # Normalize common separators to '/'
        norm = s.replace('-', '/').replace('.', '/').replace(' ', '/').replace('\u200f', '')
        # Try common formats
        fmts = [
            '%d/%m/%Y', '%Y/%m/%d', '%d/%m/%y', '%Y/%m/%d',
            '%d%m%Y', '%Y%m%d',
        ]
        for fmt in fmts:
            try:
                if 'm' in fmt and '/' in fmt:
                    dt = _dt.strptime(norm, fmt)
                else:
                    # For compact formats without separators
                    comp = ''.join(ch for ch in s if ch.isdigit())
                    if len(comp) != 8:
                        raise ValueError('not compact 8 digits')
                    dt = _dt.strptime(comp, fmt)
                return f"{dt.day:02d}/{dt.month:02d}/{dt.year:04d}"
            except Exception:
                continue
        # Heuristic: handle cases like 1/9/25 -> dd/mm/20yy
        try:
            parts = [p for p in norm.split('/') if p]
            if len(parts) == 3:
                d, m, y = parts
                d_i = int(d)
                m_i = int(m)
                y_i = int(y)
                if y_i < 100:
                    y_i += 2000 if y_i < 70 else 1900
                if 1 <= d_i <= 31 and 1 <= m_i <= 12 and 1900 <= y_i <= 2100:
                    return f"{d_i:02d}/{m_i:02d}/{y_i:04d}"
        except Exception:
            pass
        # Fallback: return original
        return s

    # Basic French number to words for dinars/millimes up to 999 999
    def amount_to_words_fr(self, amount: float) -> str:
        # Normalize to avoid floating point artifacts and ensure 3 decimals
        dinars = int(math.floor(amount + 1e-9))
        frac = round(amount - dinars, 3)
        millimes = int(round(frac * 1000))
        # Handle cases like 12.9995 -> 13.000 after rounding
        if millimes == 1000:
            dinars += 1
            millimes = 0
        parts = []
        parts.append(f"{self._number_to_french(dinars)} dinar{'s' if dinars != 1 else ''}")
        if millimes > 0:
            parts.append(f"et {millimes:03d} millime{'s' if millimes != 1 else ''}")
        return ' '.join(parts)

    def _number_to_french(self, n: int) -> str:
        if n == 0:
            return 'zéro'
        units = ['','un','deux','trois','quatre','cinq','six','sept','huit','neuf']
        teens = ['dix','onze','douze','treize','quatorze','quinze','seize','dix-sept','dix-huit','dix-neuf']
        tens = ['','dix','vingt','trente','quarante','cinquante','soixante','soixante','quatre-vingt','quatre-vingt']

        def under_hundred(x: int) -> str:
            if x < 10:
                return units[x]
            if x < 20:
                return teens[x-10]
            t = x // 10
            u = x % 10
            if t == 7:
                # 70-79: soixante-dix ... soixante-dix-neuf
                return 'soixante' + ('-' + teens[u] if u else '-dix')
            if t == 9:
                # 90-99: quatre-vingt-dix ... quatre-vingt-dix-neuf
                return 'quatre-vingt' + ('-' + teens[u] if u else '-dix')
            base = tens[t]
            if t == 8:
                base = 'quatre-vingts' if u == 0 else 'quatre-vingt'
            if u == 1 and t not in (8, 9):
                return base + '-et-un'
            return base + ('-' + units[u] if u else '')

        def under_thousand(x: int) -> str:
            if x < 100:
                return under_hundred(x)
            h = x // 100
            r = x % 100
            if h == 1:
                prefix = 'cent'
            else:
                prefix = units[h] + ' cent'
            # plural 'cents' if no remainder
            if r == 0 and h > 1:
                prefix += 's'
            return prefix if r == 0 else prefix + ' ' + under_hundred(r)

        # Handle large numbers by scales: milliard, million, mille
        parts: list[str] = []
        for scale_name, scale_value in (("milliard", 1_000_000_000), ("million", 1_000_000), ("mille", 1_000)):
            if n >= scale_value:
                count = n // scale_value
                n = n % scale_value
                if scale_name == 'mille':
                    if count == 1:
                        parts.append('mille')
                    else:
                        parts.append(under_thousand(count) + ' mille')
                else:
                    if count == 1:
                        parts.append('un ' + scale_name)
                    else:
                        parts.append(under_thousand(count) + f' {scale_name}s')
        if n > 0:
            parts.append(under_thousand(n))
        return ' '.join(parts)

    def print_cheque(self, data: Dict[str, str], preview_only: bool = False, orientation: str | None = None, printer_name: Optional[str] = None, rotate_deg: Optional[int] = None) -> Dict[str, str]:
        """
        Renders the cheque and prints via OS. When preview_only=True, opens the image.
        Returns a dict with success and path.
        """
        img = self.render_cheque_image(data)
        # Load settings (page size, margins/shift/orientation/rotation)
        settings = {}
        try:
            settings = self.repo.get_settings()
        except Exception:
            settings = {}
        # Orientation handling: 'portrait' or 'landscape'
        # Orientation used for downstream printer handling; default to portrait
        orient = (orientation or data.get('orientation') or os.environ.get('STFOOM_PRINT_ORIENTATION') or settings.get('orientation') or 'portrait')
        orient = str(orient).strip().lower()
        # Rotation: prefer explicit rotate_deg from caller; else fallback to env or settings
        angle = 0
        if rotate_deg is not None:
            try:
                angle = int(rotate_deg)
            except Exception:
                angle = 0
        else:
            rot_env = (os.environ.get('STFOOM_PRINT_ROTATE') or str(settings.get('rotate_deg') or 'none')).strip().lower()  # ccw|cw|none or numeric
            if rot_env == 'cw':
                angle = -90  # PIL rotates CCW for positive angles; CW is -90
            elif rot_env == 'ccw':
                angle = 90
            elif rot_env == '180':
                angle = 180
            else:
                # Support numeric via settings
                try:
                    angle = int(rot_env)
                except Exception:
                    angle = 0
        if angle:
            img = img.rotate(angle, expand=True)
        # Save to temp under LocalAppData/STFOOM/prints
        base_dir = os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()
        out_dir = os.path.join(base_dir, 'STFOOM', 'prints')
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(out_dir, f'cheque_{ts}.png')
        img.save(out_path, format='PNG')

        action = 'open' if preview_only else 'print'
        try:
            if platform.system().lower() == 'windows':
                # Optional alternative backends for more consistent printing
                backend_env = (os.environ.get('STFOOM_PRINT_BACKEND') or '').strip().lower()
                backend = backend_env if preview_only else (backend_env or 'win32')
                if not preview_only and backend == 'win32':
                    # Pass desired orientation to GDI so printer device rotates accordingly
                    desired = orient if orient in ('portrait', 'landscape') else None
                    ok, err = self._print_windows_win32(img, printer_name=printer_name, force_orientation=desired)
                    if ok:
                        return {"success": True, "path": out_path}
                    else:
                        return {"success": False, "error": err or 'win32 print failed', "path": out_path}
                if not preview_only and backend == 'mspaint':
                    paint = os.path.join(os.environ.get('WINDIR', r'C:\\Windows'), 'System32', 'mspaint.exe')
                    if os.path.exists(paint):
                        import subprocess
                        # /pt: print to default printer and exit
                        subprocess.run([paint, '/pt', out_path], check=False)
                        return {"success": True, "path": out_path}
                # Default shell action
                os.startfile(out_path, action)  # type: ignore[attr-defined]
            else:
                # On non-Windows, just open the file for manual printing
                os.system(f'xdg-open "{out_path}"')
            return {"success": True, "path": out_path}
        except Exception as e:
            return {"success": False, "error": str(e), "path": out_path}

    def _print_windows_win32(self, img: Image.Image, printer_name: Optional[str] = None, force_orientation: Optional[str] = None) -> Tuple[bool, str | None]:
        """
        Print using Windows GDI at an exact physical size (175 x 80 mm).
        Requires pywin32. Returns (success, errorMessage).
        """
        try:
            import win32print  # type: ignore
            import win32ui  # type: ignore
            # Constants (avoid win32con import)
            LOGPIXELSX = 88
            LOGPIXELSY = 90
            HORZRES = 8
            VERTRES = 10
            PHYSICALWIDTH = 110
            PHYSICALHEIGHT = 111
            PHYSICALOFFSETX = 112
            PHYSICALOFFSETY = 113
            DM_ORIENTATION = 0x00000001
            DMORIENT_PORTRAIT = 1
            DMORIENT_LANDSCAPE = 2

            printer_to_use = printer_name or win32print.GetDefaultPrinter()
            if not printer_to_use:
                return False, 'No default printer found'

            # Create DC using printer name, then attempt to apply DEVMODE via ResetDC
            hDC = win32ui.CreateDC()
            hDC.CreatePrinterDC(printer_to_use)
            # Try to force device orientation via DEVMODE (ResetDC)
            try:
                if force_orientation in ('portrait', 'landscape'):
                    hPrinter = win32print.OpenPrinter(printer_to_use)
                    try:
                        props = win32print.GetPrinter(hPrinter, 2)
                        devmode = props.get('pDevMode') if isinstance(props, dict) else None
                        if devmode is not None:
                            devmode.Fields = getattr(devmode, 'Fields', 0) | DM_ORIENTATION
                            devmode.Orientation = DMORIENT_PORTRAIT if force_orientation == 'portrait' else DMORIENT_LANDSCAPE
                            try:
                                hDC.ResetDC(devmode)
                            except Exception:
                                # Some drivers may not support ResetDC change; we'll rely on image rotation
                                pass
                    finally:
                        try:
                            win32print.ClosePrinter(hPrinter)
                        except Exception:
                            pass
            except Exception:
                pass

            # Start document
            hDC.StartDoc('STFOOM Cheque')
            hDC.StartPage()

            dpi_x = hDC.GetDeviceCaps(LOGPIXELSX)
            dpi_y = hDC.GetDeviceCaps(LOGPIXELSY)
            # Printable width/height (excludes physical non-printable margins)
            printable_w = hDC.GetDeviceCaps(HORZRES)
            printable_h = hDC.GetDeviceCaps(VERTRES)
            off_x = hDC.GetDeviceCaps(PHYSICALOFFSETX)
            off_y = hDC.GetDeviceCaps(PHYSICALOFFSETY)

            # Target physical size in printer pixels based on configured cheque size (mm)
            try:
                page_w_mm, page_h_mm = self.repo.get_page_size_mm()
            except Exception:
                page_w_mm, page_h_mm = 175.0, 80.0
            # Environment overrides for quick iteration
            try:
                env_w = os.environ.get('STFOOM_CHEQUE_WIDTH_MM')
                env_h = os.environ.get('STFOOM_CHEQUE_HEIGHT_MM')
                if env_w:
                    page_w_mm = float(env_w)
                if env_h:
                    page_h_mm = float(env_h)
            except Exception:
                pass
            # If the image is landscape, use (w,h); if portrait, swap to keep orientation consistent
            if img.width >= img.height:
                target_w_mm, target_h_mm = page_w_mm, page_h_mm
            else:
                target_w_mm, target_h_mm = page_h_mm, page_w_mm
            width_px = int(round(target_w_mm * dpi_x / 25.4))
            height_px = int(round(target_h_mm * dpi_y / 25.4))

            # Draw image scaled into this rectangle starting at printable origin
            if ImageWin is None:
                # PIL ImageWin missing
                hDC.EndPage(); hDC.EndDoc(); hDC.DeleteDC()
                return False, 'PIL.ImageWin not available'
            dib = ImageWin.Dib(img)
            # Margins: set to zero so drawing starts at absolute device origin.
            # Note: some printers have non-printable hardware margins; content in those zones will be clipped by the device.
            # You can revert to printable-area origin by setting env STFOOM_PRINT_MARGINS=physical.
            settings = {}
            try:
                settings = self.repo.get_settings()
            except Exception:
                settings = {}
            margins_mode = (os.environ.get('STFOOM_PRINT_MARGINS') or str(settings.get('margins_mode') or 'zero')).strip().lower()
            center_flag_env = (os.environ.get('STFOOM_PRINT_CENTER') or '').strip().lower()
            center_on_page = bool(settings.get('center_on_page')) or center_flag_env in ('1','true','yes','on')
            # Vertical alignment setting (top|center|bottom)
            valign = str(settings.get('vertical_align', 'top')).strip().lower()
            valign_env = (os.environ.get('STFOOM_PRINT_VALIGN') or '').strip().lower()
            if valign_env in ('top','center','bottom'):
                valign = valign_env
            if margins_mode == 'physical':
                left = int(off_x)
                top = int(off_y)
            elif margins_mode == 'custom':
                # Use custom margins in mm (converted to device px)
                try:
                    ml_mm = float(settings.get('margin_left_mm') or 0.0)
                    mt_mm = float(settings.get('margin_top_mm') or 0.0)
                except Exception:
                    ml_mm, mt_mm = 0.0, 0.0
                left = int(round(ml_mm * dpi_x / 25.4))
                top = int(round(mt_mm * dpi_y / 25.4))
            else:
                left = 0
                top = 0
            # Center within printable area if requested (overrides base left/top)
            if center_on_page:
                try:
                    left = int(off_x + (printable_w - width_px) // 2)
                    if valign == 'extreme-top':
                        top = int(0)
                    elif valign == 'bottom':
                        top = int(off_y + (printable_h - height_px))
                    elif valign == 'center':
                        top = int(off_y + (printable_h - height_px) // 2)
                    else:  # top
                        top = int(off_y)
                    # Clamp to device origin (avoid negatives)
                    left = max(0, left)
                    top = max(0, top)
                except Exception:
                    pass
            # Horizontal shift: apply fraction override or absolute mm shift from settings/env
            try:
                xshift_frac_env = os.environ.get('STFOOM_PRINT_XSHIFT_FRAC')
                xshift_frac = float(xshift_frac_env) if xshift_frac_env else 0.0
            except Exception:
                xshift_frac = 0.0
            # Absolute shift in mm from settings (overrides frac if non-zero)
            try:
                shift_x_mm = float(settings.get('shift_x_mm') or 0.0)
                shift_y_mm = float(settings.get('shift_y_mm') or 0.0)
            except Exception:
                shift_x_mm, shift_y_mm = 0.0, 0.0
            # Allow env mm overrides to win if present
            try:
                sxmm_env = os.environ.get('STFOOM_PRINT_SHIFT_X_MM')
                symm_env = os.environ.get('STFOOM_PRINT_SHIFT_Y_MM')
                if sxmm_env is not None:
                    shift_x_mm = float(sxmm_env)
                if symm_env is not None:
                    shift_y_mm = float(symm_env)
            except Exception:
                pass
            # Additional vertical offset specifically for centering/top alignment
            try:
                vo_mm = float(settings.get('vertical_offset_mm') or 0.0)
            except Exception:
                vo_mm = 0.0
            vo_env = os.environ.get('STFOOM_PRINT_VERTICAL_OFFSET_MM')
            if vo_env is not None:
                try:
                    vo_mm = float(vo_env)
                except Exception:
                    pass
            xshift_px = int(round(width_px * xshift_frac)) if xshift_frac else int(round(shift_x_mm * dpi_x / 25.4))
            yshift_px = int(round((shift_y_mm + vo_mm) * dpi_y / 25.4))
            left_final = left + xshift_px
            top_final = top + yshift_px
            rect = (left_final, top_final, left_final + width_px, top_final + height_px)
            dib.draw(hDC.GetHandleOutput(), rect)

            hDC.EndPage()
            hDC.EndDoc()
            hDC.DeleteDC()
            return True, None
        except ImportError:
            return False, 'pywin32 not installed (set STFOOM_PRINT_BACKEND=mspaint or install pywin32)'
        except Exception as e:
            try:
                # Attempt to finalize DC if something started
                hDC.EndPage(); hDC.EndDoc(); hDC.DeleteDC()  # type: ignore
            except Exception:
                pass
            return False, str(e)

    def list_printers(self) -> List[str]:
        """Return a list of available printer names on Windows. Empty if unavailable."""
        if platform.system().lower() != 'windows':
            return []
        try:
            import win32print  # type: ignore
            flags = 2 | 4  # PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS
            names: List[str] = []
            # Try level 4 (friendly info) then level 2/1
            for level in (4, 2, 1):
                try:
                    items = win32print.EnumPrinters(flags, None, level)
                    for it in items:
                        try:
                            if level == 4:
                                # (pPrinterName, pServerName, Attributes)
                                pname = it[0]
                            elif level == 2:
                                # dict-like PRINTER_INFO_2 with 'pPrinterName'
                                pname = it.get('pPrinterName') if isinstance(it, dict) else it[2]
                            else:
                                # level 1 tuple (flags, description, name, comment)
                                pname = it[2]
                            if pname:
                                names.append(str(pname))
                        except Exception:
                            continue
                except Exception:
                    continue
            # Default printer first, then unique others
            try:
                default_name = win32print.GetDefaultPrinter()
            except Exception:
                default_name = None
            ordered: List[str] = []
            if default_name:
                ordered.append(default_name)
            seen = set(ordered)
            for n in names:
                if n not in seen:
                    ordered.append(n); seen.add(n)
            return ordered
        except Exception:
            return []

    def get_default_printer(self) -> Optional[str]:
        if platform.system().lower() != 'windows':
            return None
        try:
            import win32print  # type: ignore
            return win32print.GetDefaultPrinter()
        except Exception:
            return None
