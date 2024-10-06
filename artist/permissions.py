from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import Artist, TierSettings, CommissionRate


def create_permissions():
    models = [Artist, TierSettings, CommissionRate]
    for model in models:
        content_type = ContentType.objects.get_for_model(model)
        model_name = model.__name__.lower()
        
        permissions = [
            (f'view_{model_name}', f'Can view {model_name}'),
            (f'add_{model_name}', f'Can add {model_name}'),
            (f'change_{model_name}', f'Can change {model_name}'),
            (f'delete_{model_name}', f'Can delete {model_name}'),
        ]
        
        for codename, name in permissions:
            Permission.objects.get_or_create(
                codename=codename,
                name=name,
                content_type=content_type,
            )

def create_groups_with_permissions():
    groups = {
        'Artist Manager': [
            'view_artist', 'change_artist', 'delete_artist',
            'view_tiersettings', 'view_commissionrate',
        ],
        'Finance Manager': [
            'view_artist', 'view_tiersettings', 'change_tiersettings',
            'view_commissionrate', 'change_commissionrate',
        ],
        'Content Manager': [
            'view_artist', 'add_artist', 'change_artist',
        ],
        'Admin': [
            'view_artist', 'add_artist', 'change_artist', 'delete_artist',
            'view_tiersettings', 'add_tiersettings', 'change_tiersettings', 'delete_tiersettings',
            'view_commissionrate', 'add_commissionrate', 'change_commissionrate', 'delete_commissionrate',
        ],
    }

    for group_name, permission_codenames in groups.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        permissions = Permission.objects.filter(codename__in=permission_codenames)
        group.permissions.set(permissions)

def assign_user_to_group(user, group_name):
    group = Group.objects.get(name=group_name)
    user.groups.add(group)

def initialize_permissions():
    create_permissions()
    create_groups_with_permissions()