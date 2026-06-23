from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Card, Transaction


class ReportService:
    """Service class for generating various reports and statistics."""
    
    @staticmethod
    def get_summary_report():
        """
        Get a comprehensive summary report of the system.
        
        Returns:
            dict: Summary statistics including card counts, revenue, and transaction totals
        """
        # Card statistics
        card_counts = Card.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status=Card.STATUS_ACTIVE)),
            lost=Count('id', filter=Q(status=Card.STATUS_LOST)),
            deactivated=Count('id', filter=Q(status=Card.STATUS_DEACTIVATED)),
        )
        
        # Revenue statistics
        revenue_stats = Transaction.objects.aggregate(
            total_purchase_amount=Sum('amount', filter=Q(type=Transaction.TYPE_PURCHASE)),
            total_reload_amount=Sum('amount', filter=Q(type=Transaction.TYPE_RELOAD)),
            total_ride_revenue=Sum('amount', filter=Q(type=Transaction.TYPE_RIDE)),
            total_transactions=Count('id'),
            ride_count=Count('id', filter=Q(type=Transaction.TYPE_RIDE)),
            purchase_count=Count('id', filter=Q(type=Transaction.TYPE_PURCHASE)),
            reload_count=Count('id', filter=Q(type=Transaction.TYPE_RELOAD)),
        )
        
        # Calculate average values
        avg_purchase = Decimal('0.00')
        avg_reload = Decimal('0.00')
        
        if revenue_stats['purchase_count'] and revenue_stats['total_purchase_amount']:
            avg_purchase = revenue_stats['total_purchase_amount'] / revenue_stats['purchase_count']
        
        if revenue_stats['reload_count'] and revenue_stats['total_reload_amount']:
            avg_reload = revenue_stats['total_reload_amount'] / revenue_stats['reload_count']
        
        return {
            'cards': card_counts,
            'revenue': {
                'total_purchase_amount': revenue_stats['total_purchase_amount'] or Decimal('0.00'),
                'total_reload_amount': revenue_stats['total_reload_amount'] or Decimal('0.00'),
                'total_ride_revenue': revenue_stats['total_ride_revenue'] or Decimal('0.00'),
                'total_revenue': (revenue_stats['total_purchase_amount'] or Decimal('0.00')) + 
                               (revenue_stats['total_reload_amount'] or Decimal('0.00')),
                'avg_purchase_amount': avg_purchase,
                'avg_reload_amount': avg_reload,
            },
            'transactions': {
                'total_count': revenue_stats['total_transactions'],
                'ride_count': revenue_stats['ride_count'],
                'purchase_count': revenue_stats['purchase_count'],
                'reload_count': revenue_stats['reload_count'],
            },
            'generated_at': timezone.now().isoformat()
        }
    
    @staticmethod
    def get_revenue_report(days=30):
        """
        Get detailed revenue report for the specified number of days.
        
        Args:
            days: Number of days to include in the report (default: 30)
            
        Returns:
            dict: Daily revenue breakdown
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Daily revenue breakdown
        daily_revenue = []
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            next_date = current_date + timedelta(days=1)
            
            day_stats = Transaction.objects.filter(
                created_at__gte=current_date,
                created_at__lt=next_date
            ).aggregate(
                ride_revenue=Sum('amount', filter=Q(type=Transaction.TYPE_RIDE)),
                purchase_revenue=Sum('amount', filter=Q(type=Transaction.TYPE_PURCHASE)),
                reload_revenue=Sum('amount', filter=Q(type=Transaction.TYPE_RELOAD)),
                ride_count=Count('id', filter=Q(type=Transaction.TYPE_RIDE)),
                purchase_count=Count('id', filter=Q(type=Transaction.TYPE_PURCHASE)),
                reload_count=Count('id', filter=Q(type=Transaction.TYPE_RELOAD)),
            )
            
            daily_revenue.append({
                'date': current_date.date().isoformat(),
                'ride_revenue': day_stats['ride_revenue'] or Decimal('0.00'),
                'purchase_revenue': day_stats['purchase_revenue'] or Decimal('0.00'),
                'reload_revenue': day_stats['reload_revenue'] or Decimal('0.00'),
                'total_revenue': (day_stats['ride_revenue'] or Decimal('0.00')) + 
                               (day_stats['purchase_revenue'] or Decimal('0.00')) + 
                               (day_stats['reload_revenue'] or Decimal('0.00')),
                'ride_count': day_stats['ride_count'],
                'purchase_count': day_stats['purchase_count'],
                'reload_count': day_stats['reload_count'],
            })
        
        # Overall period statistics
        period_stats = Transaction.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        ).aggregate(
            total_ride_revenue=Sum('amount', filter=Q(type=Transaction.TYPE_RIDE)),
            total_purchase_revenue=Sum('amount', filter=Q(type=Transaction.TYPE_PURCHASE)),
            total_reload_revenue=Sum('amount', filter=Q(type=Transaction.TYPE_RELOAD)),
            total_rides=Count('id', filter=Q(type=Transaction.TYPE_RIDE)),
            total_purchases=Count('id', filter=Q(type=Transaction.TYPE_PURCHASE)),
            total_reloads=Count('id', filter=Q(type=Transaction.TYPE_RELOAD)),
        )
        
        # Order days from latest to oldest
        daily_revenue = list(reversed(daily_revenue))

        return {
            'period': {
                'start_date': start_date.date().isoformat(),
                'end_date': end_date.date().isoformat(),
                'days': days
            },
            'daily_breakdown': daily_revenue,
            'period_totals': {
                'total_ride_revenue': period_stats['total_ride_revenue'] or Decimal('0.00'),
                'total_purchase_revenue': period_stats['total_purchase_revenue'] or Decimal('0.00'),
                'total_reload_revenue': period_stats['total_reload_revenue'] or Decimal('0.00'),
                'total_revenue': (period_stats['total_ride_revenue'] or Decimal('0.00')) + 
                               (period_stats['total_purchase_revenue'] or Decimal('0.00')) + 
                               (period_stats['total_reload_revenue'] or Decimal('0.00')),
                'total_rides': period_stats['total_rides'],
                'total_purchases': period_stats['total_purchases'],
                'total_reloads': period_stats['total_reloads'],
            },
            'generated_at': timezone.now().isoformat()
        }
    
    @staticmethod
    def get_cards_report():
        """
        Get detailed report about cards and their usage patterns.
        
        Returns:
            dict: Card statistics and usage patterns
        """
        # Card status distribution
        status_distribution = {}
        for status_choice in Card.STATUS_CHOICES:
            status_code = status_choice[0]
            status_name = status_choice[1]
            count = Card.objects.filter(status=status_code).count()
            status_distribution[status_code] = {
                'name': status_name,
                'count': count
            }
        
        # Balance distribution
        balance_ranges = [
            ('0-20', Q(balance__gte=0, balance__lt=20)),
            ('20-50', Q(balance__gte=20, balance__lt=50)),
            ('50-100', Q(balance__gte=50, balance__lt=100)),
            ('100-200', Q(balance__gte=100, balance__lt=200)),
            ('200+', Q(balance__gte=200)),
        ]
        
        balance_distribution = {}
        for range_name, query in balance_ranges:
            count = Card.objects.filter(query).count()
            balance_distribution[range_name] = count
        
        # Most active cards (by transaction count)
        most_active_cards = Card.objects.annotate(
            transaction_count=Count('transactions')
        ).order_by('-transaction_count')[:10]
        
        # Cards with highest balances
        highest_balance_cards = Card.objects.filter(
            status=Card.STATUS_ACTIVE
        ).order_by('-balance')[:10]
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_activity = Transaction.objects.filter(
            created_at__gte=week_ago
        ).aggregate(
            total_transactions=Count('id'),
            ride_transactions=Count('id', filter=Q(type=Transaction.TYPE_RIDE)),
            purchase_transactions=Count('id', filter=Q(type=Transaction.TYPE_PURCHASE)),
            reload_transactions=Count('id', filter=Q(type=Transaction.TYPE_RELOAD)),
        )
        
        return {
            'status_distribution': status_distribution,
            'balance_distribution': balance_distribution,
            'most_active_cards': [
                {
                    'uid': card.uid,
                    'status': card.status,
                    'balance': card.balance,
                    'transaction_count': card.transaction_count,
                    'created_at': card.created_at.isoformat()
                }
                for card in most_active_cards
            ],
            'highest_balance_cards': [
                {
                    'uid': card.uid,
                    'balance': card.balance,
                    'status': card.status,
                    'created_at': card.created_at.isoformat()
                }
                for card in highest_balance_cards
            ],
            'recent_activity': {
                'period_days': 7,
                'total_transactions': recent_activity['total_transactions'],
                'ride_transactions': recent_activity['ride_transactions'],
                'purchase_transactions': recent_activity['purchase_transactions'],
                'reload_transactions': recent_activity['reload_transactions'],
            },
            'generated_at': timezone.now().isoformat()
        }
    
    @staticmethod
    def get_transaction_history(uid=None, days=30):
        """
        Get transaction history for a specific card or all cards.
        
        Args:
            uid: Card UID to filter by (optional)
            days: Number of days to include (default: 30)
            
        Returns:
            dict: Transaction history data
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        queryset = Transaction.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        )
        
        if uid:
            queryset = queryset.filter(card__uid=uid)
        
        transactions = queryset.select_related('card', 'created_by').order_by('-created_at')
        
        return {
            'period': {
                'start_date': start_date.date().isoformat(),
                'end_date': end_date.date().isoformat(),
                'days': days
            },
            'card_uid': uid,
            'transactions': [
                {
                    'id': txn.id,
                    'card_uid': txn.card.uid,
                    'type': txn.type,
                    'type_display': txn.get_type_display(),
                    'amount': txn.amount,
                    'direction': txn.direction,
                    'direction_display': txn.get_direction_display(),
                    'note': txn.note,
                    'created_at': txn.created_at.isoformat(),
                    'created_by': txn.created_by.username if txn.created_by else None
                }
                for txn in transactions
            ],
            'total_count': transactions.count(),
            'generated_at': timezone.now().isoformat()
        }

