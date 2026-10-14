import base64
import os
import re
from io import BytesIO
from urllib.parse import urlparse, parse_qs
from PIL import Image
import numpy as np

# Optional / Primary Computer Vision Engines
try:
    import cv2
except ImportError:
    cv2 = None

try:
    # Attempt loading pyzbar if available
    from pyzbar import pyzbar
except Exception:
    pyzbar = None

import json
import qrcode
from qrcode import util, base
from qrcode.main import QRCode


def parse_invoice_items(items_raw) -> list:
    """
    Parses product/item strings or JSON structures into normalized list of item dictionaries:
    [{'name': '...', 'quantity': 1, 'unit_price': ..., 'total': ...}]
    Handles patterns such as:
    - "Thermal Receipt Printer 80mm (x1), Wireless Barcode Scanner Pro (x1)"
    - "Apple (x2), Milk (x1)"
    - "Product A - Rs.500 (x2), Product B - Rs.250 (x1)"
    - Multiline or JSON lists of items
    """
    if not items_raw:
        return []

    if isinstance(items_raw, list):
        items = []
        for it in items_raw:
            if isinstance(it, dict):
                name = it.get('name') or it.get('product_name') or it.get('title') or 'Item'
                qty = it.get('quantity') or it.get('qty') or 1
                try:
                    qty = int(qty)
                except (ValueError, TypeError):
                    qty = 1
                price = it.get('unit_price') or it.get('price') or it.get('rate')
                tot = it.get('total') or it.get('amount')
                items.append({
                    'name': str(name).strip(),
                    'quantity': qty,
                    'unit_price': price,
                    'total': tot
                })
            elif isinstance(it, str):
                items.extend(parse_invoice_items(it))
        return items

    if not isinstance(items_raw, str):
        return []

    items = []
    # Split by comma, semicolon, pipe, or newline
    raw_lines = [l.strip() for l in re.split(r'[,;\n|]+', items_raw) if l.strip()]

    for line in raw_lines:
        qty = 1
        unit_price = None
        line_total = None

        # Extract quantity like (x2), (2), x2, qty: 2
        qty_match = re.search(r'\((?:x\s*)?(\d+)\s*\)|(?:^|\s)x\s*(\d+)(?:\s|$)|qty:\s*(\d+)', line, re.IGNORECASE)
        if qty_match:
            for g in qty_match.groups():
                if g:
                    try:
                        qty = int(g)
                        break
                    except ValueError:
                        pass
            line = re.sub(r'\((?:x\s*)?(\d+)\s*\)|(?:^|\s)x\s*(\d+)(?:\s|$)|qty:\s*(\d+)', '', line, flags=re.IGNORECASE).strip()

        # Extract price if present, e.g. - Rs.500 or @ 500 or ₹500
        price_match = re.search(r'(?:[-@]|price:)\s*(?:Rs\.?|₹)?\s*([\d\.,]+)', line, re.IGNORECASE)
        if price_match:
            try:
                unit_price = float(price_match.group(1).replace(',', ''))
                line_total = round(unit_price * qty, 2)
            except ValueError:
                pass
            line = re.sub(r'(?:[-@]|price:)\s*(?:Rs\.?|₹)?\s*[\d\.,]+', '', line, flags=re.IGNORECASE).strip()

        clean_name = line.strip(' -:|,')
        if clean_name and clean_name.lower() not in ['total', 'bill', 'customer']:
            items.append({
                'name': clean_name,
                'quantity': qty,
                'unit_price': unit_price,
                'total': line_total
            })

    return items


def extract_invoice_info(raw_text: str, fields: dict = None) -> dict | None:
    """
    Extracts high-level normalized invoice information from raw QR text or parsed key-values.
    Works with system invoice QR text, invoice URLs, JSON invoice payloads, and UPI QR codes referencing invoices.
    """
    fields = fields or {}
    raw_text = (raw_text or '').strip()

    invoice_number = None
    date_str = None
    customer_name = None
    customer_phone = None
    total_bill = None
    subtotal = None
    tax_amount = None
    discount = None
    payment_method = None
    payment_status = None
    notes = None
    items_raw = None

    # 1. Parse from key-value fields
    for k, v in fields.items():
        k_clean = k.lower().replace('-', '_').replace(' ', '_')
        if k_clean in ['invoice_no', 'invoice_number', 'invoice', 'inv_no', 'bill_no', 'bill_number', 'invoice_id']:
            if not invoice_number and v:
                invoice_number = str(v).strip()
        elif k_clean in ['date', 'invoice_date', 'datetime', 'time', 'created_at', 'billing_date']:
            if not date_str and v:
                date_str = str(v).strip()
        elif k_clean in ['customer', 'customer_name', 'client', 'buyer', 'billed_to', 'name']:
            if not customer_name and v:
                customer_name = str(v).strip()
        elif k_clean in ['customer_phone', 'phone', 'mobile', 'contact']:
            if not customer_phone and v:
                customer_phone = str(v).strip()
        elif k_clean in ['total_bill', 'grand_total', 'total', 'bill_total', 'amount', 'net_payable', 'final_amount']:
            if not total_bill and v:
                total_bill = str(v).strip()
        elif k_clean in ['subtotal', 'sub_total']:
            if not subtotal and v:
                subtotal = str(v).strip()
        elif k_clean in ['tax', 'tax_amount', 'gst', 'gst_amount', 'tax_total']:
            if not tax_amount and v:
                tax_amount = str(v).strip()
        elif k_clean in ['discount']:
            if not discount and v:
                discount = str(v).strip()
        elif k_clean in ['payment_method', 'payment_mode', 'mode']:
            if not payment_method and v:
                payment_method = str(v).strip()
        elif k_clean in ['payment_status', 'status']:
            if not payment_status and v:
                payment_status = str(v).strip()
        elif k_clean in ['products', 'items', 'particulars', 'product_list', 'item_list']:
            if not items_raw and v:
                items_raw = v
        elif k_clean in ['notes', 'note', 'remarks']:
            if not notes and v:
                notes = str(v).strip()

    # 2. Regex fallback for invoice number
    if not invoice_number:
        inv_match = re.search(r'\b(INV-?[A-Za-z0-9_-]+)\b', raw_text, re.IGNORECASE)
        if inv_match:
            invoice_number = inv_match.group(1).upper()

    # 3. Regex URL inspection (e.g., /invoice/1/ or /invoice/verify/INV-2026-8801)
    invoice_id = None
    if '/invoice/' in raw_text or 'invoice' in raw_text.lower():
        url_id_match = re.search(r'/invoice/(\d+)(?:/|$)', raw_text)
        if url_id_match:
            invoice_id = int(url_id_match.group(1))
        url_inv_match = re.search(r'/invoice/(?:verify/)?(INV-[A-Za-z0-9_-]+)', raw_text, re.IGNORECASE)
        if url_inv_match and not invoice_number:
            invoice_number = url_inv_match.group(1).upper()

    # 4. UPI transaction note / ref inspection
    if raw_text.lower().startswith('upi://pay'):
        note = str(fields.get('note', '') or fields.get('tn', ''))
        t_ref = str(fields.get('transaction_ref', '') or fields.get('tr', ''))
        combined_ref = f"{note} {t_ref}"
        upi_inv_match = re.search(r'\b(INV-?[A-Za-z0-9_-]+)\b', combined_ref, re.IGNORECASE)
        if upi_inv_match and not invoice_number:
            invoice_number = upi_inv_match.group(1).upper()
        if not total_bill and fields.get('amount'):
            total_bill = fields.get('amount')
        if not customer_name and fields.get('payee_name'):
            notes = f"Payee: {fields.get('payee_name')}"

    # Verify if this constitutes invoice data
    is_invoice = bool(
        invoice_number or
        invoice_id or
        ('Invoice' in raw_text and (total_bill or customer_name)) or
        'Total Bill:' in raw_text or
        (items_raw and total_bill)
    )

    if not is_invoice:
        return None

    # Parse items list
    items = parse_invoice_items(items_raw)

    def _clean_amount(val):
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        m = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)', str(val))
        if m:
            try:
                return float(m.group(1).replace(',', ''))
            except ValueError:
                return None
        return None

    num_total = _clean_amount(total_bill)
    num_subtotal = _clean_amount(subtotal)
    num_tax = _clean_amount(tax_amount)
    num_discount = _clean_amount(discount)

    formatted_total = f"₹{num_total:,.2f}" if num_total is not None else (f"₹{total_bill}" if total_bill else "₹0.00")

    return {
        'is_invoice': True,
        'invoice_number': invoice_number or (f"INV-{invoice_id}" if invoice_id else "N/A"),
        'invoice_id': invoice_id,
        'date': date_str or 'N/A',
        'customer_name': customer_name or 'Walk-in Customer',
        'customer_phone': customer_phone or '',
        'items': items,
        'items_count': len(items),
        'total_bill': num_total if num_total is not None else total_bill,
        'formatted_total': formatted_total,
        'subtotal': num_subtotal if num_subtotal is not None else subtotal,
        'tax_amount': num_tax if num_tax is not None else tax_amount,
        'discount': num_discount if num_discount is not None else discount,
        'payment_method': payment_method or 'UPI QR Code',
        'payment_status': payment_status or 'PAID',
        'notes': notes or '',
    }


def parse_qr_payload(raw_text: str) -> dict:
    """
    Analyzes the decoded QR string and extracts structured metadata
    such as UPI payment fields, invoice references, URLs, or plain text.
    """
    raw_text = raw_text.strip()
    result = {
        'type': 'TEXT',
        'summary': raw_text[:80] + ('...' if len(raw_text) > 80 else ''),
        'fields': {},
        'invoice_info': None
    }

    # 1. UPI Payment URI
    if raw_text.lower().startswith('upi://pay'):
        result['type'] = 'UPI_PAYMENT'
        try:
            parsed = urlparse(raw_text)
            params = parse_qs(parsed.query)
            clean_params = {k: v[0] for k, v in params.items() if v}
            result['fields'] = {
                'upi_id': clean_params.get('pa', ''),
                'payee_name': clean_params.get('pn', ''),
                'amount': clean_params.get('am', ''),
                'currency': clean_params.get('cu', 'INR'),
                'note': clean_params.get('tn', ''),
                'transaction_ref': clean_params.get('tr', ''),
            }
            if clean_params.get('pa'):
                result['summary'] = f"UPI Payee: {clean_params.get('pn', clean_params['pa'])} | Rs.{clean_params.get('am', '0.00')}"
            inv_info = extract_invoice_info(raw_text, result['fields'])
            if inv_info:
                result['invoice_info'] = inv_info
        except Exception:
            pass
        return result

    # 2. Web URL
    if raw_text.startswith('http://') or raw_text.startswith('https://'):
        result['type'] = 'URL'
        try:
            parsed = urlparse(raw_text)
            result['fields'] = {
                'url': raw_text,
                'domain': parsed.netloc,
                'path': parsed.path,
                'scheme': parsed.scheme
            }
            result['summary'] = f"Web Link: {parsed.netloc}"
            inv_info = extract_invoice_info(raw_text, result['fields'])
            if inv_info:
                result['invoice_info'] = inv_info
                result['type'] = 'INVOICE'
        except Exception:
            pass
        return result

    # 3. System Invoice Pattern
    if 'Invoice No:' in raw_text or raw_text.startswith('INV-') or 'Total Bill:' in raw_text or 'Bill No:' in raw_text:
        result['type'] = 'INVOICE'
        fields = {}
        for line in raw_text.splitlines():
            line = line.strip()
            if ':' in line:
                key, val = line.split(':', 1)
                k_norm = key.strip().lower().replace(' ', '_')
                fields[k_norm] = val.strip()
            elif '|' in line:
                for part in line.split('|'):
                    if ':' in part:
                        k, v = part.split(':', 1)
                        fields[k.strip().lower().replace(' ', '_')] = v.strip()
        result['fields'] = fields
        inv_info = extract_invoice_info(raw_text, fields)
        result['invoice_info'] = inv_info
        inv_num = (inv_info and inv_info.get('invoice_number')) or fields.get('invoice_no') or fields.get('invoice_number') or fields.get('invoice')
        if inv_num:
            result['summary'] = f"Invoice: {inv_num} - {fields.get('customer', inv_info.get('customer_name') if inv_info else '')}"
        return result

    # 4. JSON payload
    if (raw_text.startswith('{') and raw_text.endswith('}')) or (raw_text.startswith('[') and raw_text.endswith(']')):
        try:
            data = json.loads(raw_text)
            result['type'] = 'JSON'
            result['fields'] = data if isinstance(data, dict) else {'items': data}
            result['summary'] = f"Structured JSON data with {len(data)} keys"
            inv_info = extract_invoice_info(raw_text, result['fields'])
            if inv_info:
                result['invoice_info'] = inv_info
                result['type'] = 'INVOICE'
            return result
        except Exception:
            pass

    # 5. Generic Text fallback with invoice check
    inv_info = extract_invoice_info(raw_text, result['fields'])
    if inv_info:
        result['invoice_info'] = inv_info
        result['type'] = 'INVOICE'
        if inv_info.get('invoice_number'):
            result['summary'] = f"Invoice: {inv_info['invoice_number']} - {inv_info.get('customer_name', '')}"


def _decode_with_opencv(pil_img: Image.Image) -> tuple[str | None, list | None]:
    """
    Decodes QR code using OpenCV (cv2.QRCodeDetector).
    Applies multiple adaptive vision strategies (color, grayscale, contrast enhancement).
    """
    if cv2 is None:
        return None, None

    try:
        # Convert PIL to BGR OpenCV format
        rgb_arr = np.array(pil_img.convert('RGB'))
        bgr_img = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)

        detector = cv2.QRCodeDetector()

        # Strategy 1: Standard color image
        data, bbox, _ = detector.detectAndDecode(bgr_img)
        if data and data.strip():
            bbox_list = bbox.tolist() if bbox is not None else None
            return data.strip(), bbox_list

        # Strategy 2: Grayscale image
        gray_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        data, bbox, _ = detector.detectAndDecode(gray_img)
        if data and data.strip():
            bbox_list = bbox.tolist() if bbox is not None else None
            return data.strip(), bbox_list

        # Strategy 3: Otsu thresholding
        _, otsu_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        data, bbox, _ = detector.detectAndDecode(otsu_img)
        if data and data.strip():
            bbox_list = bbox.tolist() if bbox is not None else None
            return data.strip(), bbox_list

        # Strategy 4: Inverted Otsu (for white-on-dark QR codes)
        inv_otsu = cv2.bitwise_not(otsu_img)
        data, bbox, _ = detector.detectAndDecode(inv_otsu)
        if data and data.strip():
            bbox_list = bbox.tolist() if bbox is not None else None
            return data.strip(), bbox_list

    except Exception:
        pass

    return None, None


def _decode_with_pyzbar(pil_img: Image.Image) -> str | None:
    """
    Decodes QR code using pyzbar if available.
    """
    if pyzbar is None:
        return None

    try:
        decoded_objs = pyzbar.decode(pil_img)
        for obj in decoded_objs:
            if obj.type == 'QRCODE' and obj.data:
                return obj.data.decode('utf-8', errors='replace').strip()
    except Exception:
        pass

    return None


def _decode_qr_matrix_fallback(grid: list[list[bool]], v: int, best_mask: int, ec_level: int) -> str | None:
    """
    Pure Python fallback bitstream decoder for sampled QR module grids.
    """
    N = len(grid)
    ec_map = {
        0: qrcode.constants.ERROR_CORRECT_M,
        1: qrcode.constants.ERROR_CORRECT_L,
        2: qrcode.constants.ERROR_CORRECT_H,
        3: qrcode.constants.ERROR_CORRECT_Q
    }
    primary_ec = ec_map.get(ec_level, qrcode.constants.ERROR_CORRECT_M)
    ec_candidates = [primary_ec] + [c for c in ec_map.values() if c != primary_ec]

    blank_qr = QRCode(version=v, error_correction=primary_ec)
    blank_qr.modules_count = N
    blank_qr.modules = [[None] * N for _ in range(N)]
    blank_qr.setup_position_probe_pattern(0, 0)
    blank_qr.setup_position_probe_pattern(N - 7, 0)
    blank_qr.setup_position_probe_pattern(0, N - 7)
    blank_qr.setup_position_adjust_pattern()
    blank_qr.setup_timing_pattern()
    blank_qr.setup_type_info(False, best_mask)
    if v >= 7:
        blank_qr.setup_type_number(False)

    mask_func = util.mask_func(best_mask)

    raw_bits = []
    inc = -1
    row = N - 1
    for col in range(N - 1, 0, -2):
        if col <= 6:
            col -= 1
        col_range = (col, col - 1)
        while True:
            for c in col_range:
                if blank_qr.modules[row][c] is None:
                    dark = grid[row][c]
                    if mask_func(row, c):
                        dark = not dark
                    raw_bits.append(1 if dark else 0)
            row += inc
            if row < 0 or N <= row:
                row -= inc
                inc = -inc
                break

    raw_bytes = []
    for i in range(0, len(raw_bits) - 7, 8):
        byte_val = 0
        for bit in raw_bits[i:i + 8]:
            byte_val = (byte_val << 1) | bit
        raw_bytes.append(byte_val)

    for candidate_ec in ec_candidates:
        try:
            rs_blocks = base.rs_blocks(v, candidate_ec)
            max_dc = max(b.data_count for b in rs_blocks)

            dcdata = [[] for _ in rs_blocks]
            byte_idx = 0
            for i in range(max_dc):
                for bi, block in enumerate(rs_blocks):
                    if i < block.data_count:
                        if byte_idx < len(raw_bytes):
                            dcdata[bi].append(raw_bytes[byte_idx])
                            byte_idx += 1

            all_data_bytes = []
            for block_dc in dcdata:
                all_data_bytes.extend(block_dc)

            bit_str = ''.join(f'{b:08b}' for b in all_data_bytes)
            pos = 0
            decoded_chunks = []
            valid = True

            while pos + 4 <= len(bit_str):
                mode = int(bit_str[pos:pos + 4], 2)
                pos += 4
                if mode == 0:
                    break
                elif mode == util.MODE_8BIT_BYTE:
                    c_len_bits = util.length_in_bits(mode, v)
                    if pos + c_len_bits > len(bit_str):
                        valid = False
                        break
                    count = int(bit_str[pos:pos + c_len_bits], 2)
                    pos += c_len_bits
                    if pos + count * 8 > len(bit_str):
                        valid = False
                        break
                    byte_vals = [int(bit_str[pos + i * 8:pos + (i + 1) * 8], 2) for i in range(count)]
                    pos += count * 8
                    decoded_chunks.append(bytes(byte_vals).decode('utf-8', errors='replace'))
                elif mode == util.MODE_NUMBER:
                    c_len_bits = util.length_in_bits(mode, v)
                    if pos + c_len_bits > len(bit_str):
                        valid = False
                        break
                    count = int(bit_str[pos:pos + c_len_bits], 2)
                    pos += c_len_bits
                    digits = ''
                    while count >= 3:
                        if pos + 10 > len(bit_str):
                            valid = False
                            break
                        digits += f'{int(bit_str[pos:pos + 10], 2):03d}'
                        pos += 10
                        count -= 3
                    if count == 2:
                        if pos + 7 > len(bit_str):
                            valid = False
                            break
                        digits += f'{int(bit_str[pos:pos + 7], 2):02d}'
                        pos += 7
                    elif count == 1:
                        if pos + 4 > len(bit_str):
                            valid = False
                            break
                        digits += f'{int(bit_str[pos:pos + 4], 2):01d}'
                        pos += 4
                    decoded_chunks.append(digits)
                elif mode == util.MODE_ALPHA_NUM:
                    c_len_bits = util.length_in_bits(mode, v)
                    if pos + c_len_bits > len(bit_str):
                        valid = False
                        break
                    count = int(bit_str[pos:pos + c_len_bits], 2)
                    pos += c_len_bits
                    chars = ''
                    alpha_chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:'
                    while count >= 2:
                        if pos + 11 > len(bit_str):
                            valid = False
                            break
                        val = int(bit_str[pos:pos + 11], 2)
                        pos += 11
                        chars += alpha_chars[val // 45] + alpha_chars[val % 45]
                        count -= 2
                    if count == 1:
                        if pos + 6 > len(bit_str):
                            valid = False
                            break
                        chars += alpha_chars[int(bit_str[pos:pos + 6], 2)]
                        pos += 6
                    decoded_chunks.append(chars)
                else:
                    break

            if valid and decoded_chunks:
                return ''.join(decoded_chunks)
        except Exception:
            continue

    return None


def _decode_native_grid(img_gray: Image.Image) -> tuple[str | None, int, str, int]:
    """
    Detects and samples QR grid using pure Python PIL module analysis.
    """
    w, h = img_gray.size
    min_val, max_val = img_gray.getextrema()
    if min_val == max_val:
        return None, 0, "", 0

    polarities = [False, True]
    for invert in polarities:
        pixels = img_gray.load()
        threshold = (min_val + max_val) // 2

        min_x, min_y = w, h
        max_x, max_y = 0, 0
        for y in range(h):
            for x in range(w):
                is_dark = (pixels[x, y] > threshold) if invert else (pixels[x, y] < threshold)
                if is_dark:
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y

        if max_x <= min_x or max_y <= min_y:
            continue

        qr_w = max_x - min_x + 1
        qr_h = max_y - min_y + 1

        best_N = None
        best_v = None
        best_score = -1

        for version in range(1, 41):
            N = 17 + 4 * version
            m_size_x = qr_w / N
            m_size_y = qr_h / N
            if m_size_x < 1 or m_size_y < 1:
                break

            timing_matches = 0
            total_timing = 0
            for c in range(8, N - 8):
                sx = int(min_x + (c + 0.5) * m_size_x)
                sy = int(min_y + (6 + 0.5) * m_size_y)
                if 0 <= sx < w and 0 <= sy < h:
                    is_dark = (pixels[sx, sy] > threshold) if invert else (pixels[sx, sy] < threshold)
                    if is_dark == (c % 2 == 0):
                        timing_matches += 1
                    total_timing += 1

            for r in range(8, N - 8):
                sx = int(min_x + (6 + 0.5) * m_size_x)
                sy = int(min_y + (r + 0.5) * m_size_y)
                if 0 <= sx < w and 0 <= sy < h:
                    is_dark = (pixels[sx, sy] > threshold) if invert else (pixels[sx, sy] < threshold)
                    if is_dark == (r % 2 == 0):
                        timing_matches += 1
                    total_timing += 1

            if total_timing > 0:
                score = timing_matches / total_timing
                if score >= 0.85 and score > best_score:
                    best_score = score
                    best_N = N
                    best_v = version
                    if score == 1.0:
                        break

        if not best_N:
            continue

        N = best_N
        v = best_v
        m_size_x = qr_w / N
        m_size_y = qr_h / N

        grid = []
        for r in range(N):
            row = []
            for c in range(N):
                cx = min_x + (c + 0.5) * m_size_x
                cy = min_y + (r + 0.5) * m_size_y
                sample_points = [
                    (int(cx), int(cy)),
                    (int(cx - m_size_x * 0.25), int(cy)),
                    (int(cx + m_size_x * 0.25), int(cy)),
                    (int(cx), int(cy - m_size_y * 0.25)),
                    (int(cx), int(cy + m_size_y * 0.25)),
                ]
                dark_count = 0
                for sx, sy in sample_points:
                    if 0 <= sx < w and 0 <= sy < h:
                        is_dark = (pixels[sx, sy] > threshold) if invert else (pixels[sx, sy] < threshold)
                        if is_dark:
                            dark_count += 1
                row.append(dark_count >= 3)
            grid.append(row)

        format_coords = [
            (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)
        ]
        raw_fmt = 0
        for r, c in format_coords:
            raw_fmt = (raw_fmt << 1) | (1 if grid[r][c] else 0)
        unmasked_fmt = raw_fmt ^ util.G15_MASK
        best_mask = (unmasked_fmt >> 10) & 0b111
        ec_level = (unmasked_fmt >> 13) & 0b11

        decoded_text = _decode_qr_matrix_fallback(grid, v, best_mask, ec_level)
        if decoded_text is not None:
            return decoded_text, v, f'{N}x{N}', best_mask

    return None, 0, "", 0


def decode_qr_image(img_input) -> dict:
    """
    Decodes a QR code from an uploaded image using OpenCV (cv2.QRCodeDetector) or pyzbar,
    with an automatic pure-Python fallback.
    Returns structured JSON with decoded payload, parser metadata, and engine details.
    Handles empty, blank, corrupt, or invalid image inputs gracefully.
    """
    if img_input is None:
        return {'success': False, 'error': 'No image input provided. Please upload a valid image file.'}

    try:
        if isinstance(img_input, str):
            clean_str = img_input.strip()
            if not clean_str:
                return {'success': False, 'error': 'Image data is empty.'}
            if clean_str.startswith('data:image'):
                parts = clean_str.split(',', 1)
                if len(parts) < 2 or not parts[1].strip():
                    return {'success': False, 'error': 'Base64 image payload contains no image data.'}
                clean_str = parts[1]
            try:
                img_bytes = base64.b64decode(clean_str)
            except Exception as b64_err:
                return {'success': False, 'error': f'Invalid base64 encoded image data: {str(b64_err)}'}
            if not img_bytes or len(img_bytes) == 0:
                return {'success': False, 'error': 'Decoded image data is empty (0 bytes).'}
            img = Image.open(BytesIO(img_bytes))
        elif isinstance(img_input, bytes):
            if not img_input or len(img_input) == 0:
                return {'success': False, 'error': 'The provided image byte stream is empty (0 bytes).'}
            img = Image.open(BytesIO(img_input))
        elif hasattr(img_input, 'read'):
            img_input.seek(0)
            file_bytes = img_input.read()
            if not file_bytes or len(file_bytes) == 0:
                return {'success': False, 'error': 'The uploaded file is empty (0 bytes).'}
            img = Image.open(BytesIO(file_bytes))
        elif isinstance(img_input, Image.Image):
            img = img_input
        else:
            return {'success': False, 'error': 'Unsupported image format provided.'}
    except Exception as e:
        err_msg = str(e)
        if 'cannot identify image file' in err_msg.lower() or 'unidentified' in err_msg.lower():
            return {'success': False, 'error': 'Unsupported or corrupt image file. Please upload a valid PNG, JPG, JPEG, or WEBP image.'}
        return {'success': False, 'error': f'Failed to open image: {err_msg}'}

    try:
        w, h = img.size
    except Exception:
        return {'success': False, 'error': 'Unable to determine image dimensions.'}

    if w < 20 or h < 20:
        return {'success': False, 'error': 'Image is too small to contain a valid QR code (minimum 20x20 pixels required).'}

    # Check for blank / solid color images (zero contrast)
    try:
        img_gray = img.convert('L')
        extrema = img_gray.getextrema()
        if extrema and extrema[0] == extrema[1]:
            return {
                'success': False,
                'error': 'The uploaded image appears completely blank (solid color) with no QR code pattern.'
            }
    except Exception:
        pass

    decoded_text = None
    engine_used = None
    bounding_box = None
    version = None
    grid_size = None
    mask_pattern = None

    # Step 1: Attempt decoding using OpenCV (cv2.QRCodeDetector)
    if cv2 is not None:
        cv_text, cv_bbox = _decode_with_opencv(img)
        if cv_text:
            decoded_text = cv_text
            engine_used = f"OpenCV {cv2.__version__} (cv2.QRCodeDetector)"
            bounding_box = cv_bbox

    # Step 2: Attempt decoding using pyzbar (if available and not yet decoded)
    if not decoded_text and pyzbar is not None:
        pz_text = _decode_with_pyzbar(img)
        if pz_text:
            decoded_text = pz_text
            engine_used = "pyzbar"

    # Step 3: Attempt decoding using Native Pure-Python Matrix Scanner
    if not decoded_text:
        img_gray = img.convert('L')
        native_text, v, g_size, mask = _decode_native_grid(img_gray)
        if native_text:
            decoded_text = native_text
            engine_used = "Native Matrix Engine"
            version = v
            grid_size = g_size
            mask_pattern = mask

    if decoded_text is not None:
        if not decoded_text.strip():
            return {
                'success': False,
                'error': 'A QR code was detected, but it contains an empty payload with no data.'
            }
        parsed_meta = parse_qr_payload(decoded_text)
        return {
            'success': True,
            'data': decoded_text,
            'decoded_by': engine_used,
            'format': 'QR_CODE',
            'version': version,
            'grid_size': grid_size,
            'mask_pattern': mask_pattern,
            'payload_type': parsed_meta['type'],
            'summary': parsed_meta['summary'],
            'parsed': parsed_meta['fields'],
            'invoice_info': parsed_meta.get('invoice_info'),
            'image_size': f'{w}x{h}',
            'bounding_box': bounding_box,
        }

    return {
        'success': False,
        'error': 'No QR code could be detected in the uploaded image. Please ensure the QR code is clearly visible, in focus, and not obscured or distorted.'
    }
