from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from decimal import Decimal

from .models import Card, Transaction, TrainStation, Passenger, FareCategory
from .reports import ReportService
from .services import CardService
from .exceptions import (
    CardNotFoundError, CardNotActiveError, InsufficientBalanceError,
    InvalidAmountError, CardAlreadyExistsError, InvalidStatusError
)


@admin.register(TrainStation)
class TrainStationAdmin(admin.ModelAdmin):
    """Admin interface for train stations."""
    
    list_display = ['name', 'code', 'ride_cost', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code']
    ordering = ['name']
    
    fieldsets = (
        ('Station Information', {
            'fields': ('name', 'code', 'ride_cost')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('name')


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    """Admin interface for passengers."""
    
    list_display = ['full_name', 'email', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active', 'gender', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    ordering = ['last_name', 'first_name']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'gender', 'date_of_birth')
        }),
        ('Address', {
            'fields': ('address',)
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact', 'emergency_phone')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('last_name', 'first_name')


@admin.register(FareCategory)
class FareCategoryAdmin(admin.ModelAdmin):
    """Admin interface for fare categories."""
    
    list_display = ['name', 'discount_percentage', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description')
        }),
        ('Discount Settings', {
            'fields': ('discount_percentage',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('name')


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    """Admin interface for Card model."""
    
    list_display = [
        'uid', 'status_colored', 'balance_formatted', 'passenger_info', 'created_by', 
        'created_at', 'transaction_count', 'last_transaction'
    ]
    list_filter = ['status', 'created_at', 'created_by']
    search_fields = ['uid', 'passenger_name', 'passenger_email', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at', 'transaction_count', 'last_transaction']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Card Information', {
            'fields': ('uid', 'status', 'balance')
        }),
        ('Passenger Information', {
            'fields': ('passenger_name', 'passenger_email', 'passenger', 'fare_category'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('transaction_count', 'last_transaction'),
            'classes': ('collapse',)
        }),
    )
    
    def status_colored(self, obj):
        """Display status with color coding."""
        colors = {
            'active': 'green',
            'deactivated': 'orange', 
            'lost': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    
    def balance_formatted(self, obj):
        """Display balance with peso symbol."""
        return f"₱{obj.balance}"
    balance_formatted.short_description = 'Balance'
    
    def passenger_info(self, obj):
        """Display passenger information."""
        if obj.passenger_name:
            return f"{obj.passenger_name}"
        elif obj.passenger:
            return f"{obj.passenger.full_name}"
        return "No passenger info"
    passenger_info.short_description = 'Passenger'
    
    def transaction_count(self, obj):
        """Display number of transactions."""
        return obj.transactions.count()
    transaction_count.short_description = 'Transactions'
    
    def last_transaction(self, obj):
        """Display last transaction date."""
        last_txn = obj.transactions.first()
        return last_txn.created_at if last_txn else 'None'
    last_transaction.short_description = 'Last Transaction'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('created_by')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin interface for Transaction model."""
    
    list_display = [
        'id', 'card_uid', 'type_colored', 'amount_formatted', 
        'direction_colored', 'created_by', 'created_at'
    ]
    list_filter = ['type', 'direction', 'created_at', 'created_by']
    search_fields = ['card__uid', 'note', 'created_by__username']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('card', 'type', 'amount', 'direction', 'note')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def card_uid(self, obj):
        """Display card UID with link."""
        url = reverse('admin:cards_card_change', args=[obj.card.id])
        return format_html('<a href="{}">{}</a>', url, obj.card.uid)
    card_uid.short_description = 'Card UID'
    
    def type_colored(self, obj):
        """Display transaction type with color coding."""
        colors = {
            'purchase': 'blue',
            'ride': 'red',
            'reload': 'green',
            'deactivate': 'orange',
            'lost': 'red',
            'reactivate': 'green'
        }
        color = colors.get(obj.type, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_type_display()
        )
    type_colored.short_description = 'Type'
    
    def amount_formatted(self, obj):
        """Display amount with peso symbol or N/A."""
        if obj.amount:
            return f"₱{obj.amount}"
        return 'N/A'
    amount_formatted.short_description = 'Amount'
    
    def direction_colored(self, obj):
        """Display direction with color coding."""
        if not obj.direction:
            return 'N/A'
        
        colors = {
            'credit': 'green',
            'debit': 'red',
            'neutral': 'gray'
        }
        color = colors.get(obj.direction, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_direction_display()
        )
    direction_colored.short_description = 'Direction'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('card', 'created_by')


class ReportsAdmin(admin.ModelAdmin):
    """Custom admin for reports."""
    
    def get_urls(self):
        """Add custom URLs for reports."""
        urls = super().get_urls()
        custom_urls = [
            path('reports/summary/', self.admin_site.admin_view(self.summary_report), name='cards_summary_report'),
            path('reports/revenue/', self.admin_site.admin_view(self.revenue_report), name='cards_revenue_report'),
            path('reports/cards/', self.admin_site.admin_view(self.cards_report), name='cards_cards_report'),
        ]
        return custom_urls + urls
    
    def summary_report(self, request):
        """Display summary report."""
        try:
            data = ReportService.get_summary_report()
            return JsonResponse(data, json_dumps_params={'indent': 2})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def revenue_report(self, request):
        """Display revenue report."""
        try:
            days = int(request.GET.get('days', 30))
            data = ReportService.get_revenue_report(days)
            return JsonResponse(data, json_dumps_params={'indent': 2})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def cards_report(self, request):
        """Display cards report."""
        try:
            data = ReportService.get_cards_report()
            return JsonResponse(data, json_dumps_params={'indent': 2})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# Note: Custom admin views would need to be implemented differently in Django
# For now, we'll use the standard admin interface and API endpoints for reports


# Customize admin site
admin.site.site_header = "RFID Card Payment System"
admin.site.site_title = "RFID Admin"
admin.site.index_title = "System Administration"


# Create user groups and permissions
def create_user_groups():
    """Create user groups and assign permissions."""
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    
    # Create groups
    cashier_group, created = Group.objects.get_or_create(name='cashier')
    admin_group, created = Group.objects.get_or_create(name='admin')
    
    # Get content types
    card_ct = ContentType.objects.get_for_model(Card)
    transaction_ct = ContentType.objects.get_for_model(Transaction)
    
    # Cashier permissions (view and add only)
    cashier_permissions = [
        Permission.objects.get(codename='view_card', content_type=card_ct),
        Permission.objects.get(codename='add_card', content_type=card_ct),
        Permission.objects.get(codename='view_transaction', content_type=transaction_ct),
        Permission.objects.get(codename='add_transaction', content_type=transaction_ct),
    ]
    
    # Admin permissions (all permissions)
    admin_permissions = Permission.objects.filter(
        content_type__in=[card_ct, transaction_ct]
    )
    
    # Assign permissions
    cashier_group.permissions.set(cashier_permissions)
    admin_group.permissions.set(admin_permissions)
    
    return cashier_group, admin_group


# Custom admin actions
@admin.action(description='Mark selected cards as lost')
def mark_cards_as_lost(modeladmin, request, queryset):
    """Admin action to mark multiple cards as lost."""
    from .services import CardService
    
    count = 0
    for card in queryset:
        try:
            CardService.update_card_status(
                uid=card.uid,
                new_status=Card.STATUS_LOST,
                created_by=request.user,
                note="Marked as lost via admin action"
            )
            count += 1
        except Exception as e:
            modeladmin.message_user(request, f"Error marking {card.uid} as lost: {e}", level='ERROR')
    
    modeladmin.message_user(request, f"Successfully marked {count} cards as lost.")


@admin.action(description='Deactivate selected cards')
def deactivate_cards(modeladmin, request, queryset):
    """Admin action to deactivate multiple cards."""
    from .services import CardService
    
    count = 0
    for card in queryset:
        try:
            CardService.update_card_status(
                uid=card.uid,
                new_status=Card.STATUS_DEACTIVATED,
                created_by=request.user,
                note="Deactivated via admin action"
            )
            count += 1
        except Exception as e:
            modeladmin.message_user(request, f"Error deactivating {card.uid}: {e}", level='ERROR')
    
    modeladmin.message_user(request, f"Successfully deactivated {count} cards.")


@admin.action(description='Reactivate selected cards')
def reactivate_cards(modeladmin, request, queryset):
    """Admin action to reactivate multiple cards."""
    from .services import CardService
    
    count = 0
    for card in queryset:
        try:
            CardService.update_card_status(
                uid=card.uid,
                new_status=Card.STATUS_ACTIVE,
                created_by=request.user,
                note="Reactivated via admin action"
            )
            count += 1
        except Exception as e:
            modeladmin.message_user(request, f"Error reactivating {card.uid}: {e}", level='ERROR')
    
    modeladmin.message_user(request, f"Successfully reactivated {count} cards.")


# Add actions to CardAdmin
CardAdmin.actions = [mark_cards_as_lost, deactivate_cards, reactivate_cards]
