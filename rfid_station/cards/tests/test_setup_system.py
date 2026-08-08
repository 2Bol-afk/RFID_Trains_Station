from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase

from cards.models import Card, FareCategory, TrainStation, Transaction


class SetupSystemCommandTests(TestCase):
    def test_creates_complete_synthetic_demo(self):
        call_command("setup_system", create_users=True, create_demo_data=True)

        self.assertTrue(Group.objects.filter(name="cashier").exists())
        self.assertTrue(Group.objects.filter(name="admin").exists())
        self.assertTrue(User.objects.filter(username="cashier").exists())
        self.assertTrue(User.objects.filter(username="admin").exists())
        self.assertEqual(
            set(FareCategory.objects.values_list("name", flat=True)),
            {"regular", "student", "senior", "pwd"},
        )
        self.assertTrue(TrainStation.objects.filter(is_active=True).exists())
        self.assertEqual(Card.objects.count(), 3)
        self.assertFalse(Card.objects.filter(passenger_name="").exists())
        self.assertFalse(Card.objects.filter(passenger_email="").exists())
        self.assertGreaterEqual(Transaction.objects.count(), 8)
