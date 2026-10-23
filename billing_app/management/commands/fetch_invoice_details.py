import json
from django.core.management.base import BaseCommand, CommandError
from billing_app.models import Invoice
from billing_app.invoice_qr import fetch_invoice_details
from billing_app.invoice_seeder import ensure_invoice_data_exists


class Command(BaseCommand):
    help = 'Fetch complete invoice details (ID, customer name, total amount, date) from the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            'invoice_id',
            nargs='?',
            default=None,
            help='Numeric ID or Invoice Number (e.g. 1 or INV-2026-001). Defaults to first invoice.'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Fetch and display complete details for all invoices in the database.'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output the fetched invoice details as structured JSON.'
        )

    def handle(self, *args, **options):
        # Ensure database has invoice records
        ensure_invoice_data_exists(skip_in_test=False)

        inv_arg = options.get('invoice_id')
        fetch_all = options.get('all')
        as_json = options.get('json')

        if fetch_all:
            invoices = Invoice.objects.all().order_by('id')
            if not invoices.exists():
                raise CommandError('No invoices found in the database.')

            if as_json:
                data = [inv.get_complete_details() for inv in invoices]
                # Convert non-serializable datetimes
                for item in data:
                    item['created_at'] = str(item['created_at'])
                self.stdout.write(json.dumps(data, indent=2))
                return

            self.stdout.write(self.style.MIGRATE_HEADING(f'Fetching complete details for {invoices.count()} invoices from database:'))
            self.stdout.write('=' * 85)
            self.stdout.write(f"{'ID':<6} | {'INVOICE NO':<16} | {'CUSTOMER NAME':<26} | {'TOTAL (Rs.)':<12} | {'DATE'}")
            self.stdout.write('-' * 85)
            for inv in invoices:
                d = inv.get_complete_details()
                self.stdout.write(
                    f"#{d['id']:<5} | {d['invoice_number']:<16} | {d['customer_name'][:25]:<26} | "
                    f"Rs.{d['total']:<9.2f} | {d['date']}"
                )
            self.stdout.write('=' * 85)
            self.stdout.write(self.style.SUCCESS(f'Successfully fetched {invoices.count()} invoices from database.'))
            return

        # Single invoice fetch
        if inv_arg:
            try:
                data = fetch_invoice_details(inv_arg)
            except Invoice.DoesNotExist:
                raise CommandError(f"Invoice with ID or Number '{inv_arg}' not found.")
        else:
            first_inv = Invoice.objects.first()
            if not first_inv:
                raise CommandError('No invoices found in database.')
            data = fetch_invoice_details(first_inv)

        if as_json:
            out = {
                'id': data['invoice_id'],
                'invoice_number': data['invoice_number'],
                'customer_name': data['customer_name'],
                'customer_phone': data['customer_phone'],
                'total': data['total_amount'],
                'subtotal': data['subtotal'],
                'tax_amount': data['tax_amount'],
                'date': data['date'],
                'items': data['items'],
                'payment_status': data['payment_status'],
                'payment_method': data['payment_method'],
            }
            self.stdout.write(json.dumps(out, indent=2))
            return

        self.stdout.write('=' * 65)
        self.stdout.write(self.style.SUCCESS(f"COMPLETE INVOICE DETAILS FETCHED FROM DATABASE:"))
        self.stdout.write('=' * 65)
        self.stdout.write(f" 1. INVOICE ID    : #{data['invoice_id']} ({data['invoice_number']})")
        self.stdout.write(f" 2. CUSTOMER NAME : {data['customer_name']} (Phone: {data['customer_phone'] or 'N/A'})")
        self.stdout.write(f" 3. TOTAL AMOUNT  : Rs. {data['total_amount']:.2f} (Subtotal: Rs.{data['subtotal']:.2f}, Tax: Rs.{data['tax_amount']:.2f})")
        self.stdout.write(f" 4. CREATION DATE : {data['date']}")
        self.stdout.write(f" 5. PAYMENT STATUS: {data['payment_status']} via {data['payment_method']}")
        if data.get('items'):
            self.stdout.write('-' * 65)
            self.stdout.write(" ITEMS PURCHASED:")
            for idx, it in enumerate(data['items'], 1):
                self.stdout.write(f"    {idx}. {it['name']} x{it['quantity']} @ Rs.{it['unit_price']:.2f} = Rs.{it['total']:.2f}")
        self.stdout.write('=' * 65)
