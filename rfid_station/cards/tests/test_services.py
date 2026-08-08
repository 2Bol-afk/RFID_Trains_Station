from django.contrib.auth.models import User
from django.test import TestCase

from cards.models import Card, Transaction
from cards.services import charge_ride


class CardServiceCompatibilityTests(TestCase):
    def test_charge_ride_wrapper_records_the_actor_without_a_station(self):
        actor = User.objects.create_user("ride-actor")
        card = Card.objects.create(
            uid="WRAPPER001",
            balance="100.00",
            passenger_name="Wrapper Passenger",
            passenger_email="wrapper.passenger@example.com",
            created_by=actor,
        )

        updated_card = charge_ride(card.uid, created_by=actor)

        ride = Transaction.objects.get(card=card, type=Transaction.TYPE_RIDE)
        self.assertEqual(updated_card.balance, 80)
        self.assertEqual(ride.created_by, actor)
        self.assertIsNone(ride.station)
