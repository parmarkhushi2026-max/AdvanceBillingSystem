from django.core.management.base import BaseCommand
from billing_app.invoice_seeder import ensure_invoice_data_exists
from billing_app.models import Invoice


class Command(BaseCommand):
    help = 'Ensure representative invoice data exists in the database (ID, Customer name, Total amount, and Date).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-seeding even if invoices already exist.'
        )

    def handle(self, *args, **options):
        if options.get('force'):
            Invoice.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing invoices (--force).'))

        count = ensure_invoice_data_exists(skip_in_test=False)
        total = Invoice.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully ensured invoice data exists! (Created: {count}, Total Invoices in DB: {total})'
            )
        )
        for inv in Invoice.objects.all()[:5]:
            self.stdout.write(
                f'  • Invoice ID: #{inv.id} | Number: {inv.invoice_number} | Customer: {inv.customer_name} | Amount: ₹{inv.grand_total} | Date: {inv.created_at.strftime("%Y-%m-%d")}'
            )
