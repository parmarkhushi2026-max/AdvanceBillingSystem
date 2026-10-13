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

import qrcode
from qrcode import util, base
from qrcode.main import QRCode


def parse_qr_payload(raw_text: str) -> dict:
    """
    Analyzes the decoded QR string and extracts structured metadata
    such as UPI payment fields, invoice references, URLs, or plain text.
    """
    raw_text = raw_text.strip()
    result = {
        'type': 'TEXT',
        'summary': raw_text[:80] + ('...' if len(raw_text) > 80 else ''),
        'fields': {}
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
        except Exception:
            pass
        return result

    # 3. System Invoice Pattern
    if 'Invoice No:' in raw_text or raw_text.startswith('INV-') or 'Total Bill:' in raw_text:
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
        inv_num = fields.get('invoice_no') or fields.get('invoice_number') or fields.get('invoice')
        if inv_num:
            result['summary'] = f"Invoice: {inv_num} - {fields.get('customer', '')}"
        return result

    # 4. JSON payload
    if (raw_text.startswith('{') and raw_text.endswith('}')) or (raw_text.startswith('[') and raw_text.endswith(']')):
        import json
        try:
            data = json.loads(raw_text)
            result['type'] = 'JSON'
            result['fields'] = data if isinstance(data, dict) else {'items': data}
            result['summary'] = f"Structured JSON data with {len(data)} keys"
            return result
        except Exception:
            pass

    return result


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
    """
    try:
        if isinstance(img_input, str):
            if img_input.startswith('data:image'):
                img_input = img_input.split(',', 1)[1]
            img_bytes = base64.b64decode(img_input)
            img = Image.open(BytesIO(img_bytes))
        elif isinstance(img_input, bytes):
            img = Image.open(BytesIO(img_input))
        elif hasattr(img_input, 'read'):
            img_input.seek(0)
            img = Image.open(BytesIO(img_input.read()))
        elif isinstance(img_input, Image.Image):
            img = img_input
        else:
            return {'success': False, 'error': 'Invalid image format provided.'}
    except Exception as e:
        return {'success': False, 'error': f'Failed to open image: {str(e)}'}

    w, h = img.size
    if w < 20 or h < 20:
        return {'success': False, 'error': 'Image is too small to contain a valid QR code.'}

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

    if decoded_text:
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
            'image_size': f'{w}x{h}',
            'bounding_box': bounding_box,
        }

    return {
        'success': False,
        'error': 'No QR code could be decoded from the uploaded image. Please ensure the QR code is clearly visible and uncorrupted.'
    }
