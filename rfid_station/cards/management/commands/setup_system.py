from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal

from cards.models import Card, Transaction
from cards.services import CardService


class Command(BaseCommand):
    help = 'Set up the RFID card payment system with initial data and user groups'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-demo-data',
            action='store_true',
            help='Create demo cards and transactions',
        )
        parser.add_argument(
            '--create-users',
            action='store_true',
            help='Create demo users (cashier and admin)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up RFID Card Payment System...'))
        
        # Create user groups
        self.create_user_groups()
        
        # Create demo users if requested
        if options['create_users']:
            self.create_demo_users()
        
        # Create demo data if requested
        if options['create_demo_data']:
            self.create_demo_data()
        
        self.stdout.write(self.style.SUCCESS('Setup completed successfully!'))

    def create_user_groups(self):
        """Create user groups and assign permissions."""
        self.stdout.write('Creating user groups...')
        
        # Create groups
        cashier_group, created = Group.objects.get_or_create(name='cashier')
        admin_group, created = Group.objects.get_or_create(name='admin')
        
        if created:
            self.stdout.write(f'  Created group: {cashier_group.name}')
            self.stdout.write(f'  Created group: {admin_group.name}')
        
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
        
        self.stdout.write(f'  Assigned {len(cashier_permissions)} permissions to cashier group')
        self.stdout.write(f'  Assigned {len(admin_permissions)} permissions to admin group')

    def create_demo_users(self):
        """Create demo users for testing."""
        self.stdout.write('Creating demo users...')
        
        # Create cashier user
        cashier_user, created = User.objects.get_or_create(
            username='cashier',
            defaults={
                'email': 'cashier@example.com',
                'first_name': 'Demo',
                'last_name': 'Cashier',
                'is_staff': True,
            }
        )
        if created:
            cashier_user.set_password('cashier123')
            cashier_user.save()
            cashier_group = Group.objects.get(name='cashier')
            cashier_user.groups.add(cashier_group)
            self.stdout.write('  Created cashier user (password: cashier123)')
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'first_name': 'Demo',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            admin_group = Group.objects.get(name='admin')
            admin_user.groups.add(admin_group)
            self.stdout.write('  Created admin user (password: admin123)')

    def create_demo_data(self):
        """Create demo cards and transactions."""
        self.stdout.write('Creating demo data...')
        
        # Get or create demo user
        demo_user, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@example.com',
                'first_name': 'Demo',
                'last_name': 'User',
            }
        )
        if created:
            demo_user.set_password('demo123')
            demo_user.save()
        
        # Create demo cards
        demo_cards = [
            {'uid': 'DEMO001', 'amount': Decimal('200.00')},
            {'uid': 'DEMO002', 'amount': Decimal('100.00')},
            {'uid': 'DEMO003', 'amount': Decimal('300.00')},
        ]
        
        for card_data in demo_cards:
            try:
                card = CardService.purchase_card(
                    uid=card_data['uid'],
                    initial_amount=card_data['amount'],
                    created_by=demo_user
                )
                self.stdout.write(f'  Created card: {card.uid} with ₱{card.balance}')
                
                # Add some transactions for demo
                if card_data['uid'] == 'DEMO001':
                    # Take a few rides
                    for _ in range(3):
                        CardService.charge_ride(uid=card.uid, created_by=demo_user)
                    self.stdout.write(f'    Added 3 ride transactions')
                
                elif card_data['uid'] == 'DEMO002':
                    # Reload the card
                    CardService.reload_card(
                        uid=card.uid,
                        amount=Decimal('50.00'),
                        created_by=demo_user
                    )
                    self.stdout.write(f'    Added reload transaction')
                
                elif card_data['uid'] == 'DEMO003':
                    # Deactivate the card
                    CardService.update_card_status(
                        uid=card.uid,
                        new_status=Card.STATUS_DEACTIVATED,
                        created_by=demo_user,
                        note='Demo deactivation'
                    )
                    self.stdout.write(f'    Deactivated card for demo')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  Could not create card {card_data["uid"]}: {e}')
                )
        
        self.stdout.write('Demo data creation completed!')
        self.stdout.write('')
        self.stdout.write('Demo credentials:')
        self.stdout.write('  Cashier: cashier / cashier123')
        self.stdout.write('  Admin: admin / admin123')
        self.stdout.write('  Demo User: demo / demo123')
        self.stdout.write('')
        self.stdout.write('Demo cards:')
        self.stdout.write('  DEMO001: ₱140.00 (3 rides taken)')
        self.stdout.write('  DEMO002: ₱150.00 (reloaded once)')
        self.stdout.write('  DEMO003: ₱300.00 (deactivated)')
