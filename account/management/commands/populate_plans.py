from django.core.management.base import BaseCommand
from account.models import Plan


class Command(BaseCommand):
    help = 'Populate the database with subscription plans'

    def handle(self, *args, **options):
        plans_data = [
            {
                'plan_key': 'trial',
                'name': 'Trial Plan',
                'description': 'Perfect to start - 50 bills to try out our service',
                'price': 199.00,
                'billing_requests': 50,
                'duration_days': 30,
                'has_unlimited_bills': False,
                'has_cloud_storage': True,
                'has_gst_compliance': True,
                'has_multi_device': True,
                'has_cloud_backup': False,
                'has_24x7_support': False,
                'has_inventory_management': False,
                'has_insights_dashboard': False,
                'has_sales_reports': False,
                'has_inventory_reports': False,
                'has_excel_export': False,
            },
            {
                'plan_key': '1month',
                'name': '1 Month Plan',
                'description': 'Try it out - unlimited bills for a month',
                'price': 399.00,
                'billing_requests': 0,  # unlimited
                'duration_days': 30,
                'has_unlimited_bills': True,
                'has_cloud_storage': True,
                'has_gst_compliance': True,
                'has_multi_device': True,
                'has_cloud_backup': False,
                'has_24x7_support': False,
                'has_inventory_management': False,
                'has_insights_dashboard': False,
                'has_sales_reports': False,
                'has_inventory_reports': False,
                'has_excel_export': False,
            },
            {
                'plan_key': '3months',
                'name': '3 Months Plan',
                'description': 'Most popular - save 17% with unlimited bills',
                'price': 999.00,
                'billing_requests': 0,  # unlimited
                'duration_days': 90,
                'has_unlimited_bills': True,
                'has_cloud_storage': True,
                'has_gst_compliance': True,
                'has_multi_device': True,
                'has_cloud_backup': True,
                'has_24x7_support': True,
                'has_inventory_management': False,
                'has_insights_dashboard': False,
                'has_sales_reports': False,
                'has_inventory_reports': False,
                'has_excel_export': False,
            },
            {
                'plan_key': '6months',
                'name': '6 Months Plan',
                'description': 'Great value - save 29% plus inventory management',
                'price': 1699.00,
                'billing_requests': 0,  # unlimited
                'duration_days': 180,
                'has_unlimited_bills': True,
                'has_cloud_storage': True,
                'has_gst_compliance': True,
                'has_multi_device': True,
                'has_cloud_backup': True,
                'has_24x7_support': True,
                'has_inventory_management': True,
                'has_insights_dashboard': False,
                'has_sales_reports': False,
                'has_inventory_reports': False,
                'has_excel_export': False,
            },
            {
                'plan_key': '12months',
                'name': '12 Months Plan',
                'description': 'Best deal - save 42% with all premium features',
                'price': 2799.00,
                'billing_requests': 0,  # unlimited
                'duration_days': 365,
                'has_unlimited_bills': True,
                'has_cloud_storage': True,
                'has_gst_compliance': True,
                'has_multi_device': True,
                'has_cloud_backup': True,
                'has_24x7_support': True,
                'has_inventory_management': True,
                'has_insights_dashboard': True,
                'has_sales_reports': True,
                'has_inventory_reports': True,
                'has_excel_export': True,
            },
        ]

        for plan_data in plans_data:
            plan, created = Plan.objects.update_or_create(
                plan_key=plan_data['plan_key'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created plan: {plan.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Updated plan: {plan.name}'))

        self.stdout.write(self.style.SUCCESS('Successfully populated plans!'))
