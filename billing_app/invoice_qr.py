"""
Invoice QR Code Generator & Verification Service
------------------------------------------------
Fetches core invoice data from the saved Invoice database model:
- Invoice ID & Invoice Number
- Customer Name
- Total Amount (Grand Total)
- Invoice Date

Encodes these values into standard, high-resolution QR codes (PNG, Base64 Data URI, Bytes)
supporting both human/scanner-readable key-value text and structured JSON payloads.
"""

import base64
import json
from io import BytesIO
from typing import Dict, Any, Union, Optional
from django.utils import timezone
import qrcode
from qrcode.constants import ERROR_CORRECT_M


def fetch_invoice_data(invoice_or_id) -> Dict[str, Any]:
    """
    Fetch core attributes from the saved Invoice model instance or database ID:
    - ID (primary key) and Invoice Number
    - Customer Name (& contact)
    - Total Amount (grand_total)
    - Creation Date (created_at)
    - Line Items summary & financial breakdown
    """
    from .models import Invoice

    if isinstance(invoice_or_id, Invoice):
        invoice = invoice_or_id
    elif isinstance(invoice_or_id, (int, str)):
        # Support numeric ID or alphanumeric invoice_number like 'INV-2026-001'
        if str(invoice_or_id).isdigit():
            invoice = Invoice.objects.filter(id=int(invoice_or_id)).first()
            if not invoice:
                invoice = Invoice.objects.filter(invoice_number=str(invoice_or_id)).first()
        else:
            invoice = Invoice.objects.filter(invoice_number=str(invoice_or_id)).first()
            if not invoice and str(invoice_or_id).startswith('#'):
                cand_id = str(invoice_or_id).lstrip('#')
                if cand_id.isdigit():
                    invoice = Invoice.objects.filter(id=int(cand_id)).first()
        if not invoice:
            raise Invoice.DoesNotExist(f"Invoice with ID or Number '{invoice_or_id}' was not found in database.")
    else:
        raise ValueError("Invalid invoice parameter; must be an Invoice model instance, integer ID, or invoice number.")

    # Extract formatted date
    date_val = invoice.created_at or timezone.now()
    formatted_date = date_val.strftime('%Y-%m-%d %H:%M')
    iso_date = date_val.isoformat()

    # Build products summary if items exist
    items_qs = invoice.items.all() if hasattr(invoice, 'items') else []
    items_list = []
    for it in items_qs:
        items_list.append({
            'name': it.product_name,
            'quantity': it.quantity,
            'unit_price': float(it.unit_price) if it.unit_price is not None else 0.0,
            'total': float(it.total) if it.total is not None else 0.0,
            'tax_rate': float(it.tax_rate) if it.tax_rate is not None else 18.0
        })

    products_summary = ", ".join([f"{it['name']} (x{it['quantity']})" for it in items_list])

    return {
        'invoice': invoice,
        'invoice_id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'customer_name': invoice.customer_name,
        'customer_phone': invoice.customer_phone or '',
        'total_amount': float(invoice.grand_total) if invoice.grand_total is not None else 0.0,
        'subtotal': float(invoice.subtotal) if invoice.subtotal is not None else 0.0,
        'tax_amount': float(invoice.tax_amount) if invoice.tax_amount is not None else 0.0,
        'discount': float(invoice.discount) if invoice.discount is not None else 0.0,
        'grand_total_str': f"{invoice.grand_total:.2f}" if invoice.grand_total is not None else "0.00",
        'date': formatted_date,
        'iso_date': iso_date,
        'created_at': date_val,
        'payment_status': invoice.payment_status or 'PAID',
        'payment_method': invoice.payment_method or 'UPI QR Code',
        'items': items_list,
        'products_summary': products_summary,
        'notes': invoice.notes or ''
    }


def build_invoice_qr_payload(data: Dict[str, Any], payload_format: str = 'text') -> str:
    """
    Constructs the QR payload string encoding the fetched invoice values:
    Invoice ID, Customer name, Total amount, and Date.
    """
    fmt = (payload_format or 'text').lower()

    if fmt == 'json':
        payload_dict = {
            'invoice_id': data['invoice_id'],
            'invoice_number': data['invoice_number'],
            'customer_name': data['customer_name'],
            'total_amount': data['total_amount'],
            'date': data['date'],
            'payment_status': data['payment_status'],
            'payment_method': data['payment_method'],
        }
        if data.get('customer_phone'):
            payload_dict['customer_phone'] = data['customer_phone']
        if data.get('items'):
            payload_dict['items'] = [f"{it['name']} (x{it['quantity']})" for it in data['items']]
        return json.dumps(payload_dict, indent=2)

    # Standard clean key-value text payload compliant with scanners and qr_decoder
    lines = [
        f"Invoice No: {data['invoice_number']}",
        f"Invoice ID: #{data['invoice_id']}",
        f"Customer: {data['customer_name']}",
        f"Date: {data['date']}",
        f"Total Amount: Rs.{data['grand_total_str']}",
    ]
    if data.get('customer_phone'):
        lines.append(f"Phone: {data['customer_phone']}")
    if data.get('products_summary'):
        lines.append(f"Products: {data['products_summary']}")
    if data.get('payment_method'):
        lines.append(f"Payment Method: {data['payment_method']}")
    if data.get('payment_status'):
        lines.append(f"Status: {data['payment_status']}")

    return "\n".join(lines)


def generate_invoice_qr(
    invoice_or_id,
    payload_format: str = 'text',
    box_size: int = 6,
    border: int = 2,
    as_base64: bool = True
) -> Union[str, bytes]:
    """
    Fetch data from the saved Invoice model and generate a QR code encoding these values.
    
    Args:
        invoice_or_id: Invoice model instance, int primary key, or invoice_number string.
        payload_format: 'text' (default) or 'json'.
        box_size: Pixel size of each QR box.
        border: Quiet zone border width (minimum 2).
        as_base64: If True, returns 'data:image/png;base64,...' string suitable for HTML <img>.
                   If False, returns raw PNG bytes.

    Returns:
        Data URI string or raw PNG bytes.
    """
    data = fetch_invoice_data(invoice_or_id)
    payload_text = build_invoice_qr_payload(data, payload_format=payload_format)

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload_text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    raw_bytes = buffer.getvalue()

    if as_base64:
        encoded_b64 = base64.b64encode(raw_bytes).decode('utf-8')
        return f"data:image/png;base64,{encoded_b64}"

    return raw_bytes


def generate_invoice_qr_bundle(invoice_or_id, box_size: int = 6, border: int = 2) -> Dict[str, Any]:
    """
    Convenience function that fetches the saved invoice model and generates
    all representations: text payload, json payload, base64 data URI, raw bytes,
    and extracted core values for easy rendering and API responses.
    """
    data = fetch_invoice_data(invoice_or_id)
    text_payload = build_invoice_qr_payload(data, payload_format='text')
    json_payload = build_invoice_qr_payload(data, payload_format='json')

    # Generate QR image for text payload
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text_payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    b64_str = base64.b64encode(png_bytes).decode('utf-8')
    data_uri = f"data:image/png;base64,{b64_str}"

    return {
        'invoice': data['invoice'],
        'invoice_id': data['invoice_id'],
        'invoice_number': data['invoice_number'],
        'customer_name': data['customer_name'],
        'customer_phone': data['customer_phone'],
        'total_amount': data['total_amount'],
        'grand_total_str': data['grand_total_str'],
        'date': data['date'],
        'created_at': data['created_at'],
        'text_payload': text_payload,
        'json_payload': json_payload,
        'qr_base64': data_uri,
        'raw_b64': b64_str,
        'qr_bytes': png_bytes,
        'items': data['items'],
        'products_summary': data['products_summary']
    }
