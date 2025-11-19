from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from django.utils import timezone
from django.db.models import Sum, Count

from .models import QRCode, QRScan, TreasureHuntProgress
from apps.events.models import Event, Score
from apps.houses.models import House


@login_required
def treasure_hunt_home(request):
    progress, created = TreasureHuntProgress.objects.get_or_create(student=request.user)
    scans = QRScan.objects.filter(student=request.user).select_related('qr_code')

    total_qr_codes = QRCode.objects.filter(is_active=True).count()

    # Calculate progress percentage
    progress_percentage = round((progress.total_scans / total_qr_codes) * 100) if total_qr_codes > 0 else 0

    # Get user rank
    all_progress = TreasureHuntProgress.objects.order_by('-total_points')
    user_rank = 1
    for i, p in enumerate(all_progress, 1):
        if p.student == request.user:
            user_rank = i
            break

    # Get treasure locations with scan status
    treasure_locations = []
    all_qr_codes = QRCode.objects.filter(is_active=True)
    user_scans = QRScan.objects.filter(student=request.user).values_list('qr_code_id', flat=True)
    total_qr_codes = int(total_qr_codes or 0)
    scans_done = int(getattr(progress, "total_scans", 0) or 0)

    remaining_treasures = max(0, total_qr_codes - scans_done)

    for qr_code in all_qr_codes:
        treasure_locations.append({
            'name': qr_code.location_name,
            'points': qr_code.points,
            'scanned': qr_code.id in user_scans
        })

    context = {
        'progress': progress,
        'scans': scans,
        'total_qr_codes': total_qr_codes,
        'progress_percentage': progress_percentage,
        'user_rank': user_rank,
        'total_participants': TreasureHuntProgress.objects.count(),
        'treasure_locations': treasure_locations,
        'remaining_treasures': remaining_treasures,
    }
    return render(request, 'treasure_hunt/home.html', context)


def scan_qr_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            qr_code_value = data.get('qr_code')

            if not qr_code_value:
                return JsonResponse({
                    'success': False,
                    'message': 'No QR code provided!'
                })

            qr_code = QRCode.objects.get(code=qr_code_value, is_active=True)

            # Check if already scanned
            if QRScan.objects.filter(student=request.user, qr_code=qr_code).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'You have already scanned this QR code!',
                    'clue': qr_code.clue
                })

            # Record the scan
            QRScan.objects.create(student=request.user, qr_code=qr_code)

            # Update progress
            progress, created = TreasureHuntProgress.objects.get_or_create(student=request.user)
            progress.total_scans += 1
            progress.total_points += qr_code.points
            progress.last_scan = timezone.now()
            progress.save()

            # Add points to house
            treasure_event, created = Event.objects.get_or_create(
                title="Treasure Hunt",
                defaults={
                    'description': 'QR Code Treasure Hunt',
                    'day': 1,
                    'type': 'treasure',
                    'time': timezone.now().time()
                }
            )

            Score.objects.create(
                event=treasure_event,
                house=request.user.house,
                points=qr_code.points
            )

            return JsonResponse({
                'success': True,
                'message': f'QR Code scanned successfully! +{qr_code.points} points',
                'clue': qr_code.clue,
                'location': qr_code.location_name,
                'points': qr_code.points,
                'total_points': progress.total_points
            })

        except QRCode.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid QR code! This code is not recognized.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error processing QR code: {str(e)}'
            })

    return render(request, 'treasure_hunt/scan.html')


@login_required
def treasure_hunt_leaderboard(request):
    progress_list = TreasureHuntProgress.objects.select_related('student', 'student__house').order_by('-total_points')

    # Add ranks
    ranked_progress = []
    for i, progress in enumerate(progress_list, 1):
        ranked_progress.append({
            'rank': i,
            'progress': progress,
            'is_current_user': progress.student == request.user
        })

    # Calculate house rankings
    houses = House.objects.all()
    house_rankings = []

    for house in houses:
        house_progress = TreasureHuntProgress.objects.filter(student__house=house)
        total_points = house_progress.aggregate(total=Sum('total_points'))['total'] or 0
        total_scans = house_progress.aggregate(total=Sum('total_scans'))['total'] or 0
        participants = house_progress.count()

        house_rankings.append({
            'name': house.name,
            'crest': house.crest,
            'total_points': total_points,
            'total_scans': total_scans,
            'participants': participants,
            'rank': 1  # Will be calculated below
        })

    # Sort and rank houses
    house_rankings.sort(key=lambda x: x['total_points'], reverse=True)
    for i, house in enumerate(house_rankings, 1):
        house['rank'] = i

    context = {
        'ranked_progress': ranked_progress,
        'house_rankings': house_rankings,
    }
    return render(request, 'treasure_hunt/leaderboard.html', context)