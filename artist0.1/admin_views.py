from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from .models import Artist, TierSettings, TierConfiguration
from .management.commands.recalculate_artist_tiers import Command as RecalculateCommand
from .management.commands.update_artist_tiers import Command as UpdateCommand

@staff_member_required
def admin_dashboard(request):
    context = {
        'total_artists': Artist.objects.count(),
        'pending_applications': Artist.objects.filter(application_status='PENDING').count(),
        'total_sales': Artist.objects.aggregate(Sum('total_sales'))['total_sales__sum'] or 0,
        'tier_configuration': TierConfiguration.objects.first(),
    }
    return render(request, 'admin/artist_dashboard.html', context)

@staff_member_required
def recalculate_tiers(request):
    if request.method == 'POST':
        command = RecalculateCommand()
        command.handle()
        messages.success(request, "Artist tiers have been recalculated.")
    return redirect('admin:artist_dashboard')

@staff_member_required
def update_tiers(request):
    if request.method == 'POST':
        command = UpdateCommand()
        command.handle()
        messages.success(request, "Artist tiers have been updated.")
    return redirect('admin:artist_dashboard')