from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import Card, Transaction, FareCategory
from .exceptions import (
    CardNotFoundError,
    CardNotActiveError,
    InsufficientBalanceError,
    InvalidAmountError,
    CardAlreadyExistsError,
    InvalidStatusError
)


# Constants
RIDE_COST = Decimal(str(settings.RIDE_COST))
ALLOWED_PURCHASES = {Decimal('100.00'), Decimal('200.00'), Decimal('300.00')}


class CardService:
    """Service class for card operations with atomic transactions and concurrency protection."""
    
    @staticmethod
    def purchase_card(uid: str, initial_amount: Decimal, created_by=None, passenger_name=None, passenger_email=None, fare_category=None):
        """
        Purchase a new card with initial balance and apply fare category discounts.
        
        Args:
            uid: RFID card UID
            initial_amount: Initial balance (must be 100, 200, or 300)
            created_by: User creating the card
            passenger_name: Required passenger name
            passenger_email: Required passenger email
            fare_category: Fare category (regular, student, senior) for discounts
            
        Returns:
            Card: The created card
            
        Raises:
            InvalidAmountError: If initial_amount is not allowed
            CardAlreadyExistsError: If card with UID already exists
        """
        if initial_amount not in ALLOWED_PURCHASES:
            raise InvalidAmountError(f"Initial amount must be one of: {', '.join(map(str, ALLOWED_PURCHASES))}")
        
        with transaction.atomic():
            # Check if card already exists
            if Card.objects.filter(uid=uid).exists():
                raise CardAlreadyExistsError(f"Card with UID {uid} already exists")
            
            # Get fare category object
            fare_cat_obj = None
            if fare_category and fare_category != 'regular':
                try:
                    fare_cat_obj = FareCategory.objects.get(name=fare_category, is_active=True)
                    # Normalize default discounts
                    if fare_category == 'student' and fare_cat_obj.discount_percentage != Decimal('20.00'):
                        fare_cat_obj.discount_percentage = Decimal('20.00')
                        fare_cat_obj.save(update_fields=['discount_percentage'])
                    elif fare_category == 'senior' and fare_cat_obj.discount_percentage != Decimal('25.00'):
                        fare_cat_obj.discount_percentage = Decimal('25.00')
                        fare_cat_obj.save(update_fields=['discount_percentage'])
                    elif fare_category == 'pwd' and fare_cat_obj.discount_percentage != Decimal('20.00'):
                        fare_cat_obj.discount_percentage = Decimal('20.00')
                        fare_cat_obj.save(update_fields=['discount_percentage'])
                except FareCategory.DoesNotExist:
                    # If fare category doesn't exist, create it with default discount
                    if fare_category == 'student':
                        discount = Decimal('20.00')  # 20% discount for students
                    elif fare_category == 'senior':
                        discount = Decimal('25.00')  # 25% discount for seniors
                    elif fare_category == 'pwd':
                        discount = Decimal('20.00')  # 20% discount for PWD
                    else:
                        discount = Decimal('0.00')
                    
                    fare_cat_obj = FareCategory.objects.create(
                        name=fare_category,
                        discount_percentage=discount,
                        description=f"{fare_category.title()} fare category",
                        is_active=True
                    )
            
            # Create the card
            card = Card.objects.create(
                uid=uid,
                balance=initial_amount,
                status=Card.STATUS_ACTIVE,
                passenger_name=passenger_name,
                passenger_email=passenger_email,
                fare_category=fare_cat_obj,
                created_by=created_by
            )
            
            # Record the purchase transaction
            note = f"Initial purchase with ₱{initial_amount} for {passenger_name}"
            
            Transaction.objects.create(
                card=card,
                type=Transaction.TYPE_PURCHASE,
                amount=initial_amount,
                direction=Transaction.DIRECTION_CREDIT,
                note=note,
                created_by=created_by
            )
            
            return card

    @staticmethod
    def reload_card(uid: str, amount: Decimal, created_by=None):
        """
        Reload a card with additional balance.
        
        Args:
            uid: RFID card UID
            amount: Amount to reload (must be positive)
            created_by: User performing the reload
            
        Returns:
            Card: The updated card
            
        Raises:
            CardNotFoundError: If card doesn't exist
            CardNotActiveError: If card is not active
            InvalidAmountError: If amount is not positive
        """
        if amount <= 0:
            raise InvalidAmountError("Reload amount must be positive")
        
        with transaction.atomic():
            card = Card.objects.select_for_update().get(uid=uid)
            
            if card.status != Card.STATUS_ACTIVE:
                raise CardNotActiveError(f"Card {uid} is not active (status: {card.status})")
            
            # Update balance
            card.balance = card.balance + amount
            card.save(update_fields=['balance'])
            
            # Record the reload transaction
            Transaction.objects.create(
                card=card,
                type=Transaction.TYPE_RELOAD,
                amount=amount,
                direction=Transaction.DIRECTION_CREDIT,
                note=f"Reloaded ₱{amount}",
                created_by=created_by
            )
            
            return card

    @staticmethod
    def charge_ride(uid: str, station=None, created_by=None):
        """
        Charge for a ride (deduct ride cost from balance).
        
        Args:
            uid: RFID card UID
            station: TrainStation instance (optional, uses default cost if not provided)
            created_by: User/system performing the charge
            
        Returns:
            Card: The updated card
            
        Raises:
            CardNotFoundError: If card doesn't exist
            CardNotActiveError: If card is not active
            InsufficientBalanceError: If balance is insufficient
        """
        # Determine ride cost based on station
        if station and hasattr(station, 'ride_cost'):
            ride_cost = station.ride_cost
        else:
            ride_cost = RIDE_COST
        
        with transaction.atomic():
            try:
                card = Card.objects.select_for_update().get(uid=uid)
            except Card.DoesNotExist:
                raise CardNotFoundError(f"Card with UID {uid} not found")
            
            if card.status != Card.STATUS_ACTIVE:
                raise CardNotActiveError(f"Card {uid} is not active (status: {card.status})")
            
            # Apply fare category discount at tap time
            if card.fare_category:
                ride_cost = card.fare_category.calculate_discounted_fare(ride_cost)
            
            if card.balance < ride_cost:
                raise InsufficientBalanceError(
                    f"Insufficient balance. Required: ₱{ride_cost}, Available: ₱{card.balance}"
                )
            
            # Update balance
            card.balance = card.balance - ride_cost
            card.save(update_fields=['balance'])
            
            # Record the ride transaction
            Transaction.objects.create(
                card=card,
                station=station,
                type=Transaction.TYPE_RIDE,
                amount=ride_cost,
                direction=Transaction.DIRECTION_DEBIT,
                note=f"Ride charge ₱{ride_cost}" + (f" at {station.name}" if station else ""),
                created_by=created_by
            )
            
            return card

    @staticmethod
    def update_card_status(uid: str, new_status: str, created_by=None, note=""):
        """
        Update card status (deactivate, mark as lost, reactivate).
        
        Args:
            uid: RFID card UID
            new_status: New status to set
            created_by: User performing the action
            note: Additional note for the transaction
            
        Returns:
            Card: The updated card
            
        Raises:
            CardNotFoundError: If card doesn't exist
            InvalidStatusError: If new_status is invalid
        """
        if new_status not in [Card.STATUS_ACTIVE, Card.STATUS_DEACTIVATED, Card.STATUS_LOST]:
            raise InvalidStatusError(f"Invalid status: {new_status}")
        
        with transaction.atomic():
            card = Card.objects.select_for_update().get(uid=uid)
            old_status = card.status
            
            # Update status
            card.status = new_status
            card.save(update_fields=['status'])
            
            # Determine transaction type and direction
            if new_status == Card.STATUS_DEACTIVATED:
                transaction_type = Transaction.TYPE_DEACTIVATE
                direction = Transaction.DIRECTION_NEUTRAL
                default_note = f"Card deactivated (was {old_status})"
            elif new_status == Card.STATUS_LOST:
                transaction_type = Transaction.TYPE_LOST
                direction = Transaction.DIRECTION_NEUTRAL
                default_note = f"Card marked as lost (was {old_status})"
            elif new_status == Card.STATUS_ACTIVE and old_status != Card.STATUS_ACTIVE:
                transaction_type = Transaction.TYPE_REACTIVATE
                direction = Transaction.DIRECTION_NEUTRAL
                default_note = f"Card reactivated (was {old_status})"
            else:
                # No transaction needed for same status
                return card
            
            # Record the status change transaction
            Transaction.objects.create(
                card=card,
                type=transaction_type,
                amount=None,
                direction=direction,
                note=note or default_note,
                created_by=created_by
            )
            
            return card

    @staticmethod
    def update_fare_category(uid: str, fare_category: str, created_by=None):
        """
        Update a card's fare category (regular, student, senior).
        Setting to 'regular' clears any category (no discount).
        """
        with transaction.atomic():
            try:
                card = Card.objects.select_for_update().get(uid=uid)
            except Card.DoesNotExist:
                raise CardNotFoundError(f"Card with UID {uid} not found")

            # Resolve fare category
            if fare_category == 'regular':
                card.fare_category = None
            else:
                try:
                    category_obj = FareCategory.objects.get(name=fare_category, is_active=True)
                    # Normalize default discounts
                    if fare_category == 'student' and category_obj.discount_percentage != Decimal('20.00'):
                        category_obj.discount_percentage = Decimal('20.00')
                        category_obj.save(update_fields=['discount_percentage'])
                    elif fare_category == 'senior' and category_obj.discount_percentage != Decimal('25.00'):
                        category_obj.discount_percentage = Decimal('25.00')
                        category_obj.save(update_fields=['discount_percentage'])
                    elif fare_category == 'pwd' and category_obj.discount_percentage != Decimal('20.00'):
                        category_obj.discount_percentage = Decimal('20.00')
                        category_obj.save(update_fields=['discount_percentage'])
                except FareCategory.DoesNotExist:
                    # Auto-create if missing (follow purchase logic defaults)
                    if fare_category == 'student':
                        discount = Decimal('20.00')
                    elif fare_category == 'senior':
                        discount = Decimal('25.00')
                    elif fare_category == 'pwd':
                        discount = Decimal('20.00')
                    else:
                        discount = Decimal('0.00')
                    category_obj = FareCategory.objects.create(
                        name=fare_category,
                        discount_percentage=discount,
                        description=f"{fare_category.title()} fare category",
                        is_active=True
                    )
                card.fare_category = category_obj

            card.save(update_fields=['fare_category'])

            # Log a neutral transaction for audit trail
            Transaction.objects.create(
                card=card,
                type=Transaction.TYPE_REACTIVATE,  # reuse neutral type; ideally a dedicated type
                amount=None,
                direction=Transaction.DIRECTION_NEUTRAL,
                note=f"Fare category updated to '{fare_category}'",
                created_by=created_by
            )

            return card

    @staticmethod
    def update_card_info(uid: str, passenger_name: str, passenger_email: str, created_by=None):
        """
        Update a card's passenger information (name and email).
        
        Args:
            uid: RFID card UID
            passenger_name: Updated passenger name
            passenger_email: Updated passenger email
            created_by: User performing the update
            
        Returns:
            Card: The updated card
            
        Raises:
            CardNotFoundError: If card doesn't exist
        """
        with transaction.atomic():
            try:
                card = Card.objects.select_for_update().get(uid=uid)
            except Card.DoesNotExist:
                raise CardNotFoundError(f"Card with UID {uid} not found")

            # Update passenger information
            card.passenger_name = passenger_name
            card.passenger_email = passenger_email
            card.save(update_fields=['passenger_name', 'passenger_email'])

            # Log a neutral transaction for audit trail
            Transaction.objects.create(
                card=card,
                type=Transaction.TYPE_REACTIVATE,  # reuse neutral type
                amount=None,
                direction=Transaction.DIRECTION_NEUTRAL,
                note=f"Card information updated: {passenger_name} ({passenger_email})",
                created_by=created_by
            )

            return card

    @staticmethod
    def get_card(uid: str):
        """
        Get a card by UID.
        
        Args:
            uid: RFID card UID
            
        Returns:
            Card: The card
            
        Raises:
            CardNotFoundError: If card doesn't exist
        """
        try:
            return Card.objects.get(uid=uid)
        except Card.DoesNotExist:
            raise CardNotFoundError(f"Card with UID {uid} not found")

    @staticmethod
    def get_card_transactions(uid: str, limit=50):
        """
        Get recent transactions for a card.
        
        Args:
            uid: RFID card UID
            limit: Maximum number of transactions to return
            
        Returns:
            QuerySet: Recent transactions for the card
        """
        card = CardService.get_card(uid)
        return card.transactions.all()[:limit]


# Convenience functions for backward compatibility
def purchase_card(uid: str, initial_amount: Decimal, created_by=None):
    return CardService.purchase_card(uid, initial_amount, created_by)


def reload_card(uid: str, amount: Decimal, created_by=None):
    return CardService.reload_card(uid, amount, created_by)


def charge_ride(uid: str, created_by=None):
    return CardService.charge_ride(uid, created_by=created_by)


def update_card_status(uid: str, new_status: str, created_by=None, note=""):
    return CardService.update_card_status(uid, new_status, created_by, note)
