from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class TrainStation(models.Model):
    """Model for train stations with different pricing."""
    
    name = models.CharField(max_length=100, unique=True, help_text="Station name")
    code = models.CharField(max_length=10, unique=True, help_text="Station code")
    ride_cost = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('20.00'),
        help_text="Ride cost from this station in pesos"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this station is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Train Station"
        verbose_name_plural = "Train Stations"
    
    def __str__(self):
        return f"{self.name} ({self.code}) - ₱{self.ride_cost}"
    
    @property
    def display_name(self):
        return f"{self.name} - ₱{self.ride_cost}"


class Passenger(models.Model):
    """Model for passenger information."""
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    first_name = models.CharField(max_length=50, help_text="Passenger's first name")
    last_name = models.CharField(max_length=50, help_text="Passenger's last name")
    email = models.EmailField(blank=True, null=True, help_text="Passenger's email address")
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Passenger's phone number")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True, help_text="Passenger's date of birth")
    address = models.TextField(blank=True, null=True, help_text="Passenger's address")
    emergency_contact = models.CharField(max_length=100, blank=True, null=True, help_text="Emergency contact person")
    emergency_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Emergency contact phone")
    is_active = models.BooleanField(default=True, help_text="Whether this passenger is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = "Passenger"
        verbose_name_plural = "Passengers"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def display_name(self):
        return f"{self.full_name} ({self.email or 'No email'})"


class FareCategory(models.Model):
    """Model for different fare categories (Regular, Student, Senior)."""
    
    CATEGORY_CHOICES = [
        ('regular', 'Regular'),
        ('student', 'Student'),
        ('senior', 'Senior'),
        ('pwd', 'PWD (Person with Disability)'),
    ]
    
    name = models.CharField(max_length=20, choices=CATEGORY_CHOICES, unique=True, help_text="Fare category name")
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Discount percentage (0.00 = no discount, 20.00 = 20% discount)"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this category is active")
    description = models.TextField(blank=True, help_text="Description of the category")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Fare Category"
        verbose_name_plural = "Fare Categories"
    
    def __str__(self):
        discount_text = f" ({self.discount_percentage}% discount)" if self.discount_percentage > 0 else ""
        return f"{self.get_name_display()}{discount_text}"
    
    @property
    def display_name(self):
        discount_text = f" - {self.discount_percentage}% off" if self.discount_percentage > 0 else ""
        return f"{self.get_name_display()}{discount_text}"
    
    def calculate_discounted_fare(self, base_fare):
        """Calculate the discounted fare for this category."""
        if self.discount_percentage <= 0:
            return base_fare
        discount_amount = base_fare * (self.discount_percentage / Decimal('100.00'))
        return base_fare - discount_amount


class Card(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_DEACTIVATED = 'deactivated'
    STATUS_LOST = 'lost'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_DEACTIVATED, 'Deactivated'),
        (STATUS_LOST, 'Lost'),
    ]

    uid = models.CharField(max_length=64, unique=True, help_text="RFID card UID")
    balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Current card balance in pesos"
    )
    # Direct passenger information fields for quick card purchase
    passenger_name = models.CharField(
        max_length=100, 
        blank=False, 
        null=False,
        help_text="Passenger name (required for card purchase)"
    )
    passenger_email = models.EmailField(
        blank=False, 
        null=False,
        help_text="Passenger email (required for card purchase)"
    )
    passenger = models.ForeignKey(
        Passenger,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Associated passenger (optional)"
    )
    fare_category = models.ForeignKey(
        FareCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        help_text="Fare category for discounts"
    )
    status = models.CharField(
        max_length=12, 
        choices=STATUS_CHOICES, 
        default=STATUS_ACTIVE,
        help_text="Current card status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="User who created this card"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "RFID Card"
        verbose_name_plural = "RFID Cards"

    def __str__(self):
        passenger_info = f" - {self.passenger.full_name}" if self.passenger else ""
        category_info = f" ({self.fare_category.name})" if self.fare_category else ""
        return f"{self.uid} ({self.status}){passenger_info}{category_info} - ₱{self.balance}"

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE

    @property
    def can_be_used(self):
        return self.is_active and self.balance >= Decimal('20.00')


class Transaction(models.Model):
    TYPE_PURCHASE = 'purchase'
    TYPE_RIDE = 'ride'
    TYPE_RELOAD = 'reload'
    TYPE_DEACTIVATE = 'deactivate'
    TYPE_LOST = 'lost'
    TYPE_REACTIVATE = 'reactivate'
    TRANSACTION_TYPE_CHOICES = [
        (TYPE_PURCHASE, 'Purchase'),
        (TYPE_RIDE, 'Ride'),
        (TYPE_RELOAD, 'Reload'),
        (TYPE_DEACTIVATE, 'Deactivate'),
        (TYPE_LOST, 'Lost'),
        (TYPE_REACTIVATE, 'Reactivate'),
    ]

    DIRECTION_CREDIT = 'credit'
    DIRECTION_DEBIT = 'debit'
    DIRECTION_NEUTRAL = 'neutral'
    DIRECTION_CHOICES = [
        (DIRECTION_CREDIT, 'Credit'),
        (DIRECTION_DEBIT, 'Debit'),
        (DIRECTION_NEUTRAL, 'Neutral'),
    ]

    card = models.ForeignKey(
        Card, 
        on_delete=models.CASCADE, 
        related_name='transactions',
        help_text="Associated RFID card"
    )
    station = models.ForeignKey(
        TrainStation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Station where transaction occurred"
    )
    type = models.CharField(
        max_length=12, 
        choices=TRANSACTION_TYPE_CHOICES,
        help_text="Type of transaction"
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Transaction amount (positive value)"
    )
    direction = models.CharField(
        max_length=7, 
        choices=DIRECTION_CHOICES, 
        null=True, 
        blank=True,
        help_text="Transaction direction"
    )
    note = models.TextField(
        blank=True,
        help_text="Additional notes about the transaction"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="User who created this transaction"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        amount_str = f"₱{self.amount}" if self.amount else "No amount"
        station_str = f" at {self.station.name}" if self.station else ""
        return f"{self.card.uid} - {self.get_type_display()}{station_str} - {amount_str}"

    @property
    def is_credit(self):
        return self.direction == self.DIRECTION_CREDIT

    @property
    def is_debit(self):
        return self.direction == self.DIRECTION_DEBIT

    @property
    def is_monetary(self):
        return self.amount is not None and self.amount > 0