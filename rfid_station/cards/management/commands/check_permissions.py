from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from cards.models import Card, Transaction, TrainStation, Passenger, FareCategory


class Command(BaseCommand):
    help = 'Check and create necessary user groups and permissions'

    def handle(self, *args, **options):
        self.stdout.write('Checking user groups and permissions...')
        
        # Create cashier group if it doesn't exist
        cashier_group, created = Group.objects.get_or_create(name='cashier')
        if created:
            self.stdout.write(self.style.SUCCESS('Created cashier group'))
        else:
            self.stdout.write('Cashier group already exists')
        
        # Create admin group if it doesn't exist
        admin_group, created = Group.objects.get_or_create(name='admin')
        if created:
            self.stdout.write(self.style.SUCCESS('Created admin group'))
        else:
            self.stdout.write('Admin group already exists')
        
        # Get content types
        card_ct = ContentType.objects.get_for_model(Card)
        transaction_ct = ContentType.objects.get_for_model(Transaction)
        station_ct = ContentType.objects.get_for_model(TrainStation)
        passenger_ct = ContentType.objects.get_for_model(Passenger)
        fare_ct = ContentType.objects.get_for_model(FareCategory)
        
        # Cashier permissions (view and add only)
        cashier_permissions = [
            Permission.objects.get(codename='view_card', content_type=card_ct),
            Permission.objects.get(codename='add_card', content_type=card_ct),
            Permission.objects.get(codename='view_transaction', content_type=transaction_ct),
            Permission.objects.get(codename='add_transaction', content_type=transaction_ct),
            Permission.objects.get(codename='view_trainstation', content_type=station_ct),
            Permission.objects.get(codename='view_passenger', content_type=passenger_ct),
            Permission.objects.get(codename='view_farecategory', content_type=fare_ct),
        ]
        
        # Admin permissions (all permissions)
        admin_permissions = Permission.objects.filter(
            content_type__in=[card_ct, transaction_ct, station_ct, passenger_ct, fare_ct]
        )
        
        # Assign permissions to groups
        cashier_group.permissions.set(cashier_permissions)
        admin_group.permissions.set(admin_permissions)
        
        self.stdout.write(self.style.SUCCESS('Permissions assigned successfully'))
        
        # List all groups and their permissions
        self.stdout.write('\nCurrent groups and permissions:')
        for group in Group.objects.all():
            self.stdout.write(f'\n{group.name}:')
            for perm in group.permissions.all():
                self.stdout.write(f'  - {perm}')
        
        self.stdout.write(self.style.SUCCESS('\nPermission check completed!'))
