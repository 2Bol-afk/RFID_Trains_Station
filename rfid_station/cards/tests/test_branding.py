from django.test import TestCase
from django.urls import reverse


class BrandingTemplateTests(TestCase):
    logo_path = "/static/cards/images/rfid-train-station-logo.png"

    def test_home_uses_logo_in_navigation_and_hero(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.content.decode().count(self.logo_path), 2)
        self.assertContains(response, 'rel="icon"')

    def test_login_page_uses_project_logo(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.logo_path)
        self.assertContains(response, 'rel="icon"')
