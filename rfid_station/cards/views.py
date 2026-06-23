from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Card, Transaction, TrainStation, FareCategory
from .serializers import (
    CardSerializer, CardDetailSerializer, PurchaseCardSerializer,
    ReloadCardSerializer, UpdateStatusSerializer, RideRequestSerializer, UpdateFareCategorySerializer, UpdateCardSerializer
)
from .services import CardService
from .exceptions import (
    CardNotFoundError, CardNotActiveError, InsufficientBalanceError,
    InvalidAmountError, CardAlreadyExistsError, InvalidStatusError
)
from .permissions import IsCashierOrAdmin, IsAdminOnly, IsRfidBridge, is_cashier, is_admin
from .reports import ReportService
from .authentication import CSRFExemptSessionAuthentication


# Template Views
@login_required
@user_passes_test(is_cashier)
def cashier_view(request):
    """Cashier interface for card operations."""
    # Get active stations for dropdown
    stations = TrainStation.objects.filter(is_active=True).order_by('name')
    # Get active fare categories for dropdown
    fare_categories = FareCategory.objects.filter(is_active=True).order_by('name')
    
    context = {
        'stations': stations,
        'fare_categories': fare_categories,
    }
    return render(request, 'cards/cashier.html', context)


def passenger_view(request):
    """Passenger tap simulator interface."""
    # Auto-logout any authenticated user when accessing passenger interface
    if request.user.is_authenticated:
        from django.contrib.auth import logout
        logout(request)
        # Set session flag to show logout notification
        request.session['logged_out_from_passenger'] = True
    
    # Get active stations for dropdown
    stations = TrainStation.objects.filter(is_active=True).order_by('name')
    
    context = {
        'stations': stations,
    }
    return render(request, 'cards/passenger.html', context)


def home_view(request):
    """Home page with navigation to different interfaces."""
    return render(request, 'cards/home.html')





@login_required
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    """Custom admin dashboard separate from Django admin."""
    from .reports import ReportService
    
    # Get summary data
    summary_data = ReportService.get_summary_report()
    
    # Get recent transactions
    from .models import Transaction
    recent_transactions = Transaction.objects.select_related('card', 'created_by').order_by('-created_at')[:10]
    
    # Get cards by status
    from .models import Card
    cards_by_status = {
        'active': Card.objects.filter(status=Card.STATUS_ACTIVE).count(),
        'deactivated': Card.objects.filter(status=Card.STATUS_DEACTIVATED).count(),
        'lost': Card.objects.filter(status=Card.STATUS_LOST).count(),
    }
    
    context = {
        'summary': summary_data,
        'recent_transactions': recent_transactions,
        'cards_by_status': cards_by_status,
    }
    
    return render(request, 'cards/admin_dashboard.html', context)


@login_required
@user_passes_test(is_cashier)
def cashier_dashboard_view(request):
    """Cashier dashboard with recent transactions and basic reports."""
    from .models import Transaction, Card
    from .reports import ReportService
    
    # Get recent transactions for cashier (last 20 transactions)
    recent_transactions = Transaction.objects.select_related('card', 'created_by').order_by('-created_at')[:20]
    
    # Get basic card statistics
    cards_by_status = {
        'active': Card.objects.filter(status=Card.STATUS_ACTIVE).count(),
        'deactivated': Card.objects.filter(status=Card.STATUS_DEACTIVATED).count(),
        'lost': Card.objects.filter(status=Card.STATUS_LOST).count(),
    }
    
    # Get today's transactions
    from django.utils import timezone
    today = timezone.now().date()
    today_transactions = Transaction.objects.filter(
        created_at__date=today
    ).select_related('card', 'created_by').order_by('-created_at')
    
    # Calculate today's summary
    today_summary = {
        'total_transactions': today_transactions.count(),
        'ride_transactions': today_transactions.filter(type=Transaction.TYPE_RIDE).count(),
        'purchase_transactions': today_transactions.filter(type=Transaction.TYPE_PURCHASE).count(),
        'reload_transactions': today_transactions.filter(type=Transaction.TYPE_RELOAD).count(),
        'total_revenue': sum(t.amount for t in today_transactions if t.amount and t.direction == Transaction.DIRECTION_CREDIT),
        'total_rides': sum(t.amount for t in today_transactions if t.type == Transaction.TYPE_RIDE and t.amount),
    }
    
    context = {
        'recent_transactions': recent_transactions,
        'cards_by_status': cards_by_status,
        'today_summary': today_summary,
        'today_transactions': today_transactions[:10],  # Show last 10 today
    }
    
    return render(request, 'cards/cashier_dashboard.html', context)


@login_required
@user_passes_test(lambda u: is_cashier(u) or is_admin(u))
def reports_view(request):
    """Reports page accessible by both cashier and admin."""
    from .reports import ReportService
    
    report_type = request.GET.get('type', 'summary')
    days = int(request.GET.get('days', 30))
    
    if report_type == 'summary':
        data = ReportService.get_summary_report()
    elif report_type == 'revenue':
        data = ReportService.get_revenue_report(days)
    elif report_type == 'cards':
        data = ReportService.get_cards_report()
    elif report_type == 'transactions':
        data = ReportService.get_transaction_history(days=days)
    else:
        data = ReportService.get_summary_report()
    
    context = {
        'report_type': report_type,
        'days': days,
        'data': data,
        'is_admin': request.user.groups.filter(name='admin').exists() or request.user.is_superuser,
    }
    
    return render(request, 'cards/reports.html', context)


@login_required
@user_passes_test(lambda u: is_cashier(u) or is_admin(u))
def lost_card_management_view(request):
    """View for managing lost cards by searching name or email and deactivating cards."""
    from django.db.models import Q
    from .models import Passenger, Card

    context = {}

    # Handle search via GET query param
    query = request.GET.get('q', '').strip()
    if query:
        # Search cards of any status by direct passenger fields or UID
        cards_qs = Card.objects.filter(
            Q(passenger_name__icontains=query) |
            Q(passenger_email__icontains=query) |
            Q(uid__icontains=query)
        )
        # Also include cards linked to Passenger records that match by name/email
        passenger_matches = Passenger.objects.filter(is_active=True).filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query)
        )
        if passenger_matches.exists():
            cards_qs = cards_qs | Card.objects.filter(passenger__in=passenger_matches)

        context['search_query'] = query
        context['search_cards'] = cards_qs.select_related('passenger').order_by('-created_at')[:100]
    
    # Handle actions via POST
    if request.method == 'POST':
        action = request.POST.get('action')
        card_uid = request.POST.get('card_uid')
        if action and card_uid:
            try:
                if action == 'mark_lost':
                    CardService.update_card_status(
                        uid=card_uid,
                        new_status=Card.STATUS_LOST,
                        created_by=request.user,
                        note=f"Card marked as lost - managed by {request.user.username}"
                    )
                    messages.success(request, f"Card {card_uid} has been marked as lost.")
                elif action == 'deactivate':
                    CardService.update_card_status(
                        uid=card_uid,
                        new_status=Card.STATUS_DEACTIVATED,
                        created_by=request.user,
                        note=f"Card deactivated - managed by {request.user.username}"
                    )
                    messages.success(request, f"Card {card_uid} has been deactivated.")
                elif action == 'activate':
                    CardService.update_card_status(
                        uid=card_uid,
                        new_status=Card.STATUS_ACTIVE,
                        created_by=request.user,
                        note=f"Card reactivated - managed by {request.user.username}"
                    )
                    messages.success(request, f"Card {card_uid} has been reactivated.")
            except Exception as e:
                messages.error(request, f"Error updating card: {str(e)}")
        # After POST, redirect to GET to avoid resubmission and preserve search if present
        redirect_url = request.path
        if query:
            redirect_url = f"{redirect_url}?q={query}"
        return redirect(redirect_url)

    return render(request, 'cards/lost_card_management.html', context)


@login_required
@user_passes_test(lambda u: is_admin(u))
def station_management_view(request):
    """View for managing train stations."""
    context = {
        'stations': TrainStation.objects.all().order_by('name'),
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            name = request.POST.get('name')
            code = request.POST.get('code')
            ride_cost = request.POST.get('ride_cost')
            is_active = request.POST.get('is_active') == 'on'
            
            if name and code and ride_cost:
                try:
                    TrainStation.objects.create(
                        name=name,
                        code=code,
                        ride_cost=ride_cost,
                        is_active=is_active
                    )
                    messages.success(request, f"Station '{name}' added successfully.")
                except Exception as e:
                    messages.error(request, f"Error adding station: {str(e)}")
        
        elif action == 'edit':
            station_id = request.POST.get('station_id')
            name = request.POST.get('name')
            code = request.POST.get('code')
            ride_cost = request.POST.get('ride_cost')
            is_active = request.POST.get('is_active') == 'on'
            
            if station_id and name and code and ride_cost:
                try:
                    station = TrainStation.objects.get(id=station_id)
                    station.name = name
                    station.code = code
                    station.ride_cost = ride_cost
                    station.is_active = is_active
                    station.save()
                    messages.success(request, f"Station '{name}' updated successfully.")
                except TrainStation.DoesNotExist:
                    messages.error(request, "Station not found.")
                except Exception as e:
                    messages.error(request, f"Error updating station: {str(e)}")
        
        elif action == 'delete':
            station_id = request.POST.get('station_id')
            if station_id:
                try:
                    station = TrainStation.objects.get(id=station_id)
                    station_name = station.name
                    station.delete()
                    messages.success(request, f"Station '{station_name}' deleted successfully.")
                except TrainStation.DoesNotExist:
                    messages.error(request, "Station not found.")
                except Exception as e:
                    messages.error(request, f"Error deleting station: {str(e)}")
    
    return render(request, 'cards/station_management.html', context)


class PurchaseCardView(APIView):
    """
    Purchase a new RFID card with initial balance.
    Requires cashier or admin permissions.
    """
    authentication_classes = [CSRFExemptSessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsCashierOrAdmin]
    
    def post(self, request):
        serializer = PurchaseCardSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            card = CardService.purchase_card(
                uid=serializer.validated_data['uid'],
                initial_amount=serializer.validated_data['initial_amount'],
                created_by=request.user,
                passenger_name=serializer.validated_data['passenger_name'],
                passenger_email=serializer.validated_data['passenger_email'],
                fare_category=serializer.validated_data['fare_category']
            )
            return Response(
                CardSerializer(card).data, 
                status=status.HTTP_201_CREATED
            )
        except (InvalidAmountError, CardAlreadyExistsError) as e:
            # Provide field-specific error for existing UID
            if isinstance(e, CardAlreadyExistsError):
                return Response({'uid': [str(e)]}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'initial_amount': [str(e)]}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReloadCardView(APIView):
    """
    Reload an existing card with additional balance.
    Requires cashier or admin permissions.
    """
    authentication_classes = [CSRFExemptSessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsCashierOrAdmin]
    
    def post(self, request, uid):
        serializer = ReloadCardSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            card = CardService.reload_card(
                uid=uid,
                amount=serializer.validated_data['amount'],
                created_by=request.user
            )
            return Response(CardSerializer(card).data)
        except (CardNotFoundError, CardNotActiveError, InvalidAmountError) as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RideView(APIView):
    """
    Process a ride charge (deduct ride cost from card balance).
    Can be called by RFID bridge or authenticated users.
    """
    authentication_classes = [CSRFExemptSessionAuthentication]
    permission_classes = [IsRfidBridge | permissions.IsAuthenticated]
    
    def post(self, request, uid):
        serializer = RideRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get station if provided
            station = None
            station_id = request.data.get('station_id')
            if station_id:
                try:
                    station = TrainStation.objects.get(id=station_id, is_active=True)
                except TrainStation.DoesNotExist:
                    return Response(
                        {'error': 'Invalid or inactive station'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            card = CardService.charge_ride(
                uid=uid,
                station=station,
                created_by=request.user if request.user.is_authenticated else None
            )
            return Response(CardSerializer(card).data)
        except (CardNotFoundError, CardNotActiveError, InsufficientBalanceError) as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class CardStatusView(APIView):
    """
    Update card status (deactivate, mark as lost, reactivate).
    Requires admin permissions.
    """
    authentication_classes = [CSRFExemptSessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsAdminOnly]
    
    def post(self, request, uid):
        serializer = UpdateStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            card = CardService.update_card_status(
                uid=uid,
                new_status=serializer.validated_data['status'],
                created_by=request.user,
                note=serializer.validated_data.get('note', '')
            )
            return Response(CardSerializer(card).data)
        except (CardNotFoundError, InvalidStatusError) as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class UpdateFareCategoryView(APIView):
    """
    Update a card's fare category (regular, student, senior).
    Requires cashier or admin permissions.
    """
    authentication_classes = [CSRFExemptSessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsCashierOrAdmin]

    def post(self, request, uid):
        serializer = UpdateFareCategorySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            card = CardService.update_fare_category(
                uid=uid,
                fare_category=serializer.validated_data['fare_category'],
                created_by=request.user
            )
            return Response(CardSerializer(card).data)
        except CardNotFoundError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateCardView(APIView):
    """
    Update card passenger information (name and email).
    Requires cashier or admin permissions.
    """
    authentication_classes = [CSRFExemptSessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsCashierOrAdmin]

    def post(self, request, uid):
        serializer = UpdateCardSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            card = CardService.update_card_info(
                uid=uid,
                passenger_name=serializer.validated_data['passenger_name'],
                passenger_email=serializer.validated_data['passenger_email'],
                created_by=request.user
            )
            return Response(CardSerializer(card).data)
        except CardNotFoundError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CardDetailView(APIView):
    """
    Get detailed information about a specific card including transaction history.
    Requires cashier or admin permissions.
    """
    permission_classes = [permissions.IsAuthenticated, IsCashierOrAdmin]
    
    def get(self, request, uid):
        try:
            card = CardService.get_card(uid)
            return Response(CardDetailSerializer(card).data)
        except CardNotFoundError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )


class CardListView(APIView):
    """
    List all cards with optional filtering.
    Requires admin permissions.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminOnly]
    
    def get(self, request):
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        
        queryset = Card.objects.all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if search:
            queryset = queryset.filter(uid__icontains=search)
        
        # Limit to recent cards for performance
        queryset = queryset.order_by('-created_at')[:100]
        
        serializer = CardSerializer(queryset, many=True)
        return Response(serializer.data)


class ReportsView(APIView):
    """
    Get system reports and statistics.
    Requires admin or cashier permissions.
    """
    permission_classes = [permissions.IsAuthenticated, IsCashierOrAdmin]
    
    def get(self, request):
        report_type = request.query_params.get('type', 'summary')
        
        if report_type == 'summary':
            data = ReportService.get_summary_report()
        elif report_type == 'revenue':
            data = ReportService.get_revenue_report()
        elif report_type == 'cards':
            data = ReportService.get_cards_report()
        else:
            return Response(
                {'error': 'Invalid report type'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCashierOrAdmin])
def card_balance(request, uid):
    """
    Quick endpoint to get just the card balance.
    Useful for RFID bridge or quick checks.
    """
    try:
        card = CardService.get_card(uid)
        fare_category = None
        if card.fare_category:
            fare_category = {
                'name': card.fare_category.name,
                'discount_percentage': card.fare_category.discount_percentage
            }
        return Response({
            'uid': card.uid,
            'balance': card.balance,
            'status': card.status,
            'can_be_used': card.can_be_used,
            'fare_category': fare_category
        })
    except CardNotFoundError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([])  # No authentication required
def public_card_balance(request, uid):
    """
    Public endpoint to get card balance for passenger interface.
    No authentication required.
    """
    try:
        card = CardService.get_card(uid)
        fare_category = None
        if card.fare_category:
            fare_category = {
                'name': card.fare_category.name,
                'discount_percentage': card.fare_category.discount_percentage
            }
        return Response({
            'uid': card.uid,
            'balance': card.balance,
            'status': card.status,
            'can_be_used': card.can_be_used,
            'fare_category': fare_category
        })
    except CardNotFoundError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([])  # No authentication required
def clear_passenger_session(request):
    """Clear the passenger session flag."""
    if 'logged_out_from_passenger' in request.session:
        del request.session['logged_out_from_passenger']
    return Response({'status': 'cleared'})


@api_view(['POST'])
@permission_classes([])  # No authentication required
def public_ride_charge(request, uid):
    """Public endpoint for ride charges from passenger interface."""
    serializer = RideRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Require station for public taps
        station_id = serializer.validated_data.get('station_id')
        if not station_id:
            return Response({'error': 'Please select a station before tapping.'}, status=status.HTTP_400_BAD_REQUEST)
        # Resolve station
        try:
            station = TrainStation.objects.get(id=station_id, is_active=True)
        except TrainStation.DoesNotExist:
            return Response({'error': 'Invalid or inactive station'}, status=status.HTTP_400_BAD_REQUEST)

        card = CardService.charge_ride(
            uid=uid,
            station=station,
            created_by=None  # No user for public interface
        )
        return Response(CardSerializer(card).data)
    except (CardNotFoundError, CardNotActiveError, InsufficientBalanceError) as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCashierOrAdmin])
def recent_transactions(request):
    """
    Get recent transactions for the cashier interface.
    Returns the last 10 transactions.
    """
    from .models import Transaction
    
    # Get recent cashier transactions (exclude rides) - last 10
    transactions = Transaction.objects.select_related('card', 'created_by')\
        .exclude(type=Transaction.TYPE_RIDE)\
        .order_by('-created_at')[:10]
    
    # Serialize transactions
    transaction_data = []
    for transaction in transactions:
        transaction_data.append({
            'id': transaction.id,
            'card_uid': transaction.card.uid,
            'type': transaction.type,
            'type_display': transaction.get_type_display(),
            'amount': float(transaction.amount) if transaction.amount else None,
            'direction': transaction.direction,
            'note': transaction.note,
            'created_at': transaction.created_at.isoformat(),
            'created_by': transaction.created_by.username if transaction.created_by else 'System'
        })
    
    return Response({
        'transactions': transaction_data,
        'count': len(transaction_data)
    })


@api_view(['GET'])
@permission_classes([])  # No authentication required
def public_card_transactions(request, uid):
    """
    Public endpoint to get card transaction history for passenger interface.
    No authentication required.
    """
    try:
        card = CardService.get_card(uid)
        transactions = CardService.get_card_transactions(uid, limit=10)
        
        # Serialize transactions
        transaction_data = []
        for transaction in transactions:
            transaction_data.append({
                'id': transaction.id,
                'type': transaction.type,
                'amount': float(transaction.amount) if transaction.amount else None,
                'direction': transaction.direction,
                'note': transaction.note,
                'created_at': transaction.created_at.isoformat(),
                'created_by': transaction.created_by.username if transaction.created_by else None
            })
        
        return Response({
            'uid': card.uid,
            'transactions': transaction_data
        })
    except CardNotFoundError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdminOnly])
def system_health(request):
    """
    System health check endpoint.
    """
    try:
        # Basic system checks
        total_cards = Card.objects.count()
        active_cards = Card.objects.filter(status=Card.STATUS_ACTIVE).count()
        total_transactions = Transaction.objects.count()
        
        # Check for any cards with negative balance (shouldn't happen)
        negative_balance_cards = Card.objects.filter(balance__lt=0).count()
        
        health_status = {
            'status': 'healthy',
            'total_cards': total_cards,
            'active_cards': active_cards,
            'total_transactions': total_transactions,
            'negative_balance_cards': negative_balance_cards,
            'ride_cost': settings.RIDE_COST,
            'bridge_token_configured': bool(settings.RFID_BRIDGE_TOKEN)
        }
        
        if negative_balance_cards > 0:
            health_status['status'] = 'warning'
            health_status['warning'] = f'{negative_balance_cards} cards have negative balance'
        
        return Response(health_status)
    except Exception as e:
        return Response(
            {'status': 'error', 'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )