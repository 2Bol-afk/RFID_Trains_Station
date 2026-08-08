from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse


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
