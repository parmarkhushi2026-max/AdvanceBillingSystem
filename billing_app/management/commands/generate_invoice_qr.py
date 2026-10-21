from django.core.management.base import BaseCommand, CommandError
from billing_app.models import Invoice
from billing_app.invoice_qr import fetch_invoice_data, build_invoice_qr_payload, generate_invoice_qr
from billing_app.invoice_seeder import ensure_invoice_data_exists


class Command(BaseCommand):
    help = 'Fetch invoice data from the saved model and generate a QR code encoding these values.'

    def add_arguments(self, parser):
        parser.add_argument(
            'invoice_id',
            nargs='?',
            default=None,
            help='ID or Invoice Number (e.g. 1 or INV-2026-001). Defaults to first available invoice.'
        )
        parser.add_argument(
            '--format',
            default='text',
            choices=['text', 'json'],
            help='Encoding payload format: text (human/scanner readable key-values) or json.'
        )
        parser.add_argument(
            '--save',
            default=None,
            help='Optional filesystem path to save the generated QR code PNG image.'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate QR codes for all saved invoices in the database.'
        )

    def handle(self, *args, **options):
        # Ensure database has invoice records
        ensure_invoice_data_exists(skip_in_test=False)

        inv_arg = options.get('invoice_id')
        fmt = options.get('format', 'text')
        save_path = options.get('save')
        gen_all = options.get('all')

        if gen_all:
            invoices = Invoice.objects.all().order_by('id')
            if not invoices.exists():
                raise CommandError('No invoices found in database.')
            self.stdout.write(self.style.MIGRATE_HEADING(f'Generating QR codes for {invoices.count()} invoices...'))
            for inv in invoices:
                self._process_single_invoice(inv, fmt, None)
            self.stdout.write(self.style.SUCCESS(f'Successfully generated QR codes for {invoices.count()} invoices.'))
            return

        if inv_arg:
            try:
                data = fetch_invoice_data(inv_arg)
                invoice = data['invoice']
            except (Invoice.DoesNotExist, ValueError) as err:
                raise CommandError(str(err))
        else:
            invoice = Invoice.objects.order_by('id').first()
            if not invoice:
                raise CommandError('No invoices found in database.')

        self._process_single_invoice(invoice, fmt, save_path)

    def _process_single_invoice(self, invoice, fmt, save_path):
        data = fetch_invoice_data(invoice)
        payload = build_invoice_qr_payload(data, payload_format=fmt)
        qr_bytes = generate_invoice_qr(invoice, payload_format=fmt, as_base64=False)

        self.stdout.write(self.style.SUCCESS('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'))
        self.stdout.write(self.style.SUCCESS(f'✅ Fetched Saved Invoice Model: #{invoice.id} ({invoice.invoice_number})'))
        self.stdout.write(self.style.SUCCESS('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'))
        self.stdout.write(f'  • Invoice ID:    #{data["invoice_id"]}')
        self.stdout.write(f'  • Invoice Number:{data["invoice_number"]}')
        self.stdout.write(f'  • Customer Name: {data["customer_name"]}')
        self.stdout.write(f'  • Total Amount:  ₹{data["grand_total_str"]}')
        self.stdout.write(f'  • Date:          {data["date"]}')
        if data.get('customer_phone'):
            self.stdout.write(f'  • Phone:         {data["customer_phone"]}')
        if data.get('products_summary'):
            self.stdout.write(f'  • Products:      {data["products_summary"]}')
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_LABEL('Encoded QR Code Payload:'))
        self.stdout.write(payload)
        self.stdout.write(f'QR Code PNG Size: {len(qr_bytes)} bytes')

        if save_path:
            with open(save_path, 'wb') as f:
                f.write(qr_bytes)
            self.stdout.write(self.style.SUCCESS(f'Saved QR PNG to: {save_path}'))
