from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from cards.models import Card, Transaction


class ReportRouteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "route-cashier",
            password="test-pass",
        )
        group, _ = Group.objects.get_or_create(name="cashier")
        self.user.groups.add(group)
        self.client.force_login(self.user)

    def test_report_page_and_json_api_have_distinct_routes(self):
        page = self.client.get(reverse("reports"))
        api = self.client.get(reverse("reports-api"), {"type": "summary"})

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "System Reports")
        self.assertEqual(api.status_code, 200)
        self.assertEqual(api["Content-Type"], "application/json")


class AdminDashboardTests(TestCase):
    def test_dashboard_renders_report_service_revenue_values(self):
        admin = User.objects.create_superuser(
            "dashboard-admin",
            "dashboard-admin@example.com",
            "test-pass",
        )
        card = Card.objects.create(
            uid="DASHBOARD001",
            balance="130.00",
            passenger_name="Demo Passenger",
            passenger_email="demo.passenger@example.com",
            created_by=admin,
        )
        for transaction_type, amount, direction in (
            (Transaction.TYPE_PURCHASE, "100.00", Transaction.DIRECTION_CREDIT),
            (Transaction.TYPE_RELOAD, "50.00", Transaction.DIRECTION_CREDIT),
            (Transaction.TYPE_RIDE, "20.00", Transaction.DIRECTION_DEBIT),
        ):
            Transaction.objects.create(
                card=card,
                type=transaction_type,
                amount=amount,
                direction=direction,
                created_by=admin,
            )
        self.client.force_login(admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('<span class="text-primary">₱100.00</span>', html)
        self.assertIn('<h3 class="mt-2">₱50.00</h3>', html)
        self.assertIn('<h3 class="mt-2">₱20.00</h3>', html)
