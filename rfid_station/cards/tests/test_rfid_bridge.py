from unittest.mock import Mock

from django.test import SimpleTestCase

from rfid_bridge import RfidBridge


class RfidBridgeTests(SimpleTestCase):
    def test_unusable_card_is_rejected_without_posting_a_ride(self):
        bridge = RfidBridge.__new__(RfidBridge)
        bridge.logger = Mock()
        bridge.get_card_balance = Mock(
            return_value={
                "balance": "0.00",
                "status": "active",
                "can_be_used": False,
            }
        )
        bridge.post_ride_charge = Mock()

        bridge.process_uid("DEMO001")

        bridge.post_ride_charge.assert_not_called()
