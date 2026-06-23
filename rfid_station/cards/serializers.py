from rest_framework import serializers
from decimal import Decimal
from .models import Card, Transaction, FareCategory


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model."""
    
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    direction_display = serializers.CharField(source='get_direction_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'type', 'type_display', 'amount', 'direction', 'direction_display',
            'note', 'created_at', 'created_by_username'
        ]
        read_only_fields = ['id', 'created_at']


class FareCategorySerializer(serializers.ModelSerializer):
    """Serializer for FareCategory model."""
    
    class Meta:
        model = FareCategory
        fields = ['name', 'discount_percentage', 'description']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Normalize display for well-known categories
        if data.get('name') == 'student':
            data['discount_percentage'] = str(Decimal('20.00'))
        elif data.get('name') == 'senior':
            data['discount_percentage'] = str(Decimal('25.00'))
        elif data.get('name') == 'pwd':
            data['discount_percentage'] = str(Decimal('20.00'))
        return data


class CardSerializer(serializers.ModelSerializer):
    """Serializer for Card model."""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    recent_transactions = TransactionSerializer(source='transactions', many=True, read_only=True)
    can_be_used = serializers.BooleanField(read_only=True)
    fare_category = FareCategorySerializer(read_only=True)
    
    class Meta:
        model = Card
        fields = [
            'uid', 'balance', 'status', 'status_display', 'passenger_name', 'passenger_email',
            'fare_category', 'created_at', 'updated_at', 'created_by_username', 'can_be_used', 'recent_transactions'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PurchaseCardSerializer(serializers.Serializer):
    """Serializer for purchasing a new card."""
    
    uid = serializers.CharField(max_length=64, help_text="RFID card UID")
    initial_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Initial balance (100, 200, or 300)"
    )
    passenger_name = serializers.CharField(
        max_length=100, 
        required=True, 
        help_text="Passenger name (required)"
    )
    passenger_email = serializers.EmailField(
        required=True, 
        help_text="Passenger email (required)"
    )
    fare_category = serializers.ChoiceField(
        choices=[('regular', 'Regular'), ('student', 'Student'), ('senior', 'Senior'), ('pwd', 'PWD (Person with Disability)')],
        required=True,
        help_text="Fare category for discounts"
    )
    
    def validate_initial_amount(self, value):
        """Validate that initial amount is one of the allowed values."""
        allowed_amounts = {Decimal('100.00'), Decimal('200.00'), Decimal('300.00')}
        if value not in allowed_amounts:
            raise serializers.ValidationError(
                f"Initial amount must be one of: {', '.join(map(str, allowed_amounts))}"
            )
        return value
    
    def validate_uid(self, value):
        """Validate UID format and uniqueness."""
        if not value or not value.strip():
            raise serializers.ValidationError("UID cannot be empty")
        
        # Check if card already exists
        if Card.objects.filter(uid=value).exists():
            raise serializers.ValidationError(f"Card with UID {value} already exists")
        
        return value.strip()
    
    def validate_passenger_email(self, value):
        """Validate email format if provided."""
        if value and not value.strip():
            return None
        return value.strip() if value else None
    
    def validate_passenger_name(self, value):
        """Validate name if provided."""
        if value and not value.strip():
            return None
        return value.strip() if value else None


class ReloadCardSerializer(serializers.Serializer):
    """Serializer for reloading a card."""
    
    amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Amount to reload"
    )
    
    def validate_amount(self, value):
        """Validate that amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value


class UpdateStatusSerializer(serializers.Serializer):
    """Serializer for updating card status."""
    
    status = serializers.ChoiceField(
        choices=Card.STATUS_CHOICES,
        help_text="New card status"
    )
    note = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional note for the status change"
    )


class CardDetailSerializer(CardSerializer):
    """Extended serializer for card details with full transaction history."""
    
    transactions = TransactionSerializer(many=True, read_only=True)
    
    class Meta(CardSerializer.Meta):
        fields = CardSerializer.Meta.fields + ['transactions']


class RideRequestSerializer(serializers.Serializer):
    """Serializer for ride requests (no additional data needed)."""
    station_id = serializers.IntegerField(required=False)


class UpdateFareCategorySerializer(serializers.Serializer):
    """Serializer to update a card's fare category."""
    fare_category = serializers.ChoiceField(
        choices=[('regular', 'Regular'), ('student', 'Student'), ('senior', 'Senior'), ('pwd', 'PWD (Person with Disability)')],
        help_text="New fare category (regular clears discount)"
    )


class UpdateCardSerializer(serializers.Serializer):
    """Serializer for updating card passenger information."""
    passenger_name = serializers.CharField(
        max_length=100, 
        required=True, 
        help_text="Updated passenger name"
    )
    passenger_email = serializers.EmailField(
        required=True, 
        help_text="Updated passenger email"
    )
    
    def validate_passenger_name(self, value):
        """Validate name if provided."""
        if value and not value.strip():
            raise serializers.ValidationError("Passenger name cannot be empty")
        return value.strip() if value else None
    
    def validate_passenger_email(self, value):
        """Validate email format if provided."""
        if value and not value.strip():
            raise serializers.ValidationError("Passenger email cannot be empty")
        return value.strip() if value else None
