import os
from django.core.management.base import BaseCommand, CommandError
from billing_app.models import Invoice
from billing_app.pdf_generator import generate_invoice_pdf_bytes


class Command(BaseCommand):
    help = "Generate a certified Tax Invoice PDF using xhtml2pdf or ReportLab."

    def add_arguments(self, parser):
        parser.add_argument(
            'invoice_id',
            type=str,
            help='Database ID or Invoice Number of the invoice to render (or "first", "latest").'
        )
        parser.add_argument(
            '--engine',
            type=str,
            default='auto',
            choices=['auto', 'xhtml2pdf', 'reportlab'],
            help='PDF rendering engine to use (default: auto).'
        )
        parser.add_argument(
            '--qr-mode',
            type=str,
            default='text',
            choices=['text', 'upi', 'json'],
            help='Dynamic QR code payload format (default: text).'
        )
        parser.add_argument(
            '--qr-engine',
            type=str,
            default='auto',
            choices=['auto', 'qrcode', 'segno'],
            help='QR generation engine backend (default: auto).'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='',
            help='Output file path for saving the PDF (optional).'
        )

    def handle(self, *args, **options):
        inv_identifier = options['invoice_id'].strip()
        engine = options.get('engine', 'auto')
        qr_mode = options.get('qr_mode', 'text')
        qr_engine = options.get('qr_engine', 'auto')
        output_path = options.get('output', '').strip()

        # Resolve Invoice
        if inv_identifier.lower() in ('first', '1') and not Invoice.objects.filter(invoice_number=inv_identifier).exists():
            invoice = Invoice.objects.first()
        elif inv_identifier.lower() == 'latest':
            invoice = Invoice.objects.order_by('-created_at').first()
        elif inv_identifier.isdigit():
            invoice = Invoice.objects.filter(id=int(inv_identifier)).first()
        else:
            invoice = Invoice.objects.filter(invoice_number=inv_identifier).first()

        if not invoice:
            raise CommandError(f"Invoice '{inv_identifier}' not found in the database.")

        self.stdout.write(f"Generating PDF for Invoice #{invoice.invoice_number} (ID: {invoice.id}) [PDF Engine: '{engine}', QR Mode: '{qr_mode}']...")

        try:
            pdf_bytes = generate_invoice_pdf_bytes(invoice, engine=engine, qr_mode=qr_mode, qr_engine=qr_engine)
        except Exception as e:
            raise CommandError(f"PDF generation failed: {e}")

        if not pdf_bytes.startswith(b'%PDF-'):
            raise CommandError("Generated stream is not a valid PDF.")

        self.stdout.write(self.style.SUCCESS(f"✅ Generated valid PDF ({len(pdf_bytes)} bytes)."))

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            self.stdout.write(self.style.SUCCESS(f"Saved PDF to: {os.path.abspath(output_path)}"))
        else:
            default_name = f"Invoice_{invoice.invoice_number}.pdf"
            self.stdout.write(f"Default filename: {default_name}")

