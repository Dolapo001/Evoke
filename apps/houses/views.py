from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.core.models import Student
from apps.events.models import Score, Event
from apps.gallery.models import Image
from apps.houses.models import House
from apps.notifications.models import Notification
from apps.treasure_hunt.models import QRScan


@login_required
def dashboard(request):
    # Since Student IS the user model, request.user is already a Student instance
    student = request.user

    # No need to query Student.objects.get() since request.user is the Student

    house = getattr(student, 'house', None)
    if house is None:
        # The user doesn't belong to a house yet — render a special template/state
        context = {
            'house': None,
            'members': Student.objects.none(),
            'members_count': 0,
            'total_points': 0,
            'event_wins': 0,
            'house_rank': None,
            'points_to_next': None,
            'recent_activity': [],
            'recent_scores': Score.objects.none(),
            'user': request.user,
        }
        return render(request, 'houses/no_house.html', context)

    # Rest of your existing logic remains the same...
    members = Student.objects.filter(house=house)
    event_wins = Score.objects.filter(house=house, points__gt=0).count()

    houses = House.objects.annotate(total_points_annotated=Sum('score__points')).order_by('-total_points_annotated')

    house_rank = 1
    for i, h in enumerate(houses, 1):
        if getattr(h, 'pk', None) == house.pk:
            house_rank = i
            break

    def _get_total_points(h_obj):
        annotated = getattr(h_obj, 'total_points_annotated', None)
        if annotated is not None:
            try:
                return int(annotated or 0)
            except Exception:
                try:
                    return int(float(annotated))
                except Exception:
                    return 0

        maybe_method = getattr(h_obj, 'total_points', None)
        if callable(maybe_method):
            try:
                result = maybe_method()
                return int(result or 0)
            except Exception:
                pass

        agg = Score.objects.filter(house=h_obj).aggregate(total=Sum('points'))['total'] or 0
        return int(agg)

    points_to_next = 0
    if house_rank > 1:
        next_house = houses[house_rank - 2]
        points_to_next = max(0, _get_total_points(next_house) - _get_total_points(house))

    recent_activity = []
    recent_scores = Score.objects.filter(house=house).select_related('event').order_by('-created_at')[:5]
    for score in recent_scores:
        recent_activity.append({
            'type': 'score',
            'message': f"Earned {score.points} points in {score.event.title}",
            'timestamp': score.created_at,
            'icon': 'fas fa-trophy',
            'color': 'green'
        })

    if members.exists():
        recent_activity.append({
            'type': 'member',
            'message': f"Welcome to our newest member!",
            'timestamp': timezone.now(),
            'icon': 'fas fa-user-plus',
            'color': 'blue'
        })

    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:5]

    context = {
        'house': house,
        'members': members,
        'members_count': members.count(),
        'total_points': _get_total_points(house),
        'event_wins': event_wins,
        'house_rank': house_rank,
        'points_to_next': points_to_next,
        'recent_activity': recent_activity,
        'recent_scores': recent_scores,
        'user': request.user,
    }
    return render(request, 'houses/dashboard.html', context)

class HouseDetailView(DetailView):
    model = House
    template_name = 'houses/detail.html'
    context_object_name = 'house'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        house = self.object

        # Basic data
        context['members'] = Student.objects.filter(house=house)
        context['scores'] = Score.objects.filter(house=house).select_related('event')

        # Calculate house rank
        houses = House.objects.annotate(
            total_points=Sum('score__points')
        ).order_by('-total_points')

        house_rank = 1
        for i, h in enumerate(houses, 1):
            if h == house:
                house_rank = i
                break
        context['house_rank'] = house_rank

        # Event wins count
        context['event_wins'] = Score.objects.filter(
            house=house,
            points__gt=0
        ).count()

        # Points by event type
        points_by_type = []
        event_types = ['major', 'minor', 'treasure', 'trivia']
        colors = ['yellow', 'blue', 'green', 'purple']

        for event_type, color in zip(event_types, colors):
            points = Score.objects.filter(
                house=house,
                event__type=event_type
            ).aggregate(total=Sum('points'))['total'] or 0
            points_by_type.append({
                'name': event_type.title(),
                'points': points,
                'color': color
            })
        context['points_by_type'] = points_by_type

        # Recent scores
        context['recent_scores'] = Score.objects.filter(
            house=house
        ).select_related('event').order_by('-created_at')[:5]

        # Recent images from house gallery
        context['recent_images'] = Image.objects.filter(
            house=house,
            approved=True
        ).order_by('-timestamp')[:4]

        # Recent performance (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_points = Score.objects.filter(
            house=house,
            created_at__gte=week_ago
        ).aggregate(total=Sum('points'))['total'] or 0
        context['recent_points'] = recent_points

        # Simple trend calculation
        context['trend'] = 'up' if recent_points > 0 else 'stable'

        # Best event (most points in a single event)
        best_score = Score.objects.filter(house=house).order_by('-points').first()
        context['best_event'] = best_score.event if best_score else None

        # Participation rate
        total_events = Event.objects.count()
        participated_events = Score.objects.filter(house=house).values('event').distinct().count()
        context['participation_rate'] = round((participated_events / total_events) * 100) if total_events > 0 else 0

        return context


@login_required
def house_members(request, pk):
    house = get_object_or_404(House, pk=pk)
    members = Student.objects.filter(house=house).order_by('name')

    # Calculate member statistics
    admins_count = members.filter(role='admin').count()
    students_count = members.filter(role='student').count()

    # Calculate activity metrics for each member
    active_members = 0
    total_photos_uploaded = 0
    total_qr_scans = 0

    for member in members:
        # Count photos uploaded by member
        photos_count = Image.objects.filter(uploader=member).count()
        member.images_uploaded = photos_count
        total_photos_uploaded += photos_count

        # Count QR scans by member
        qr_scans = QRScan.objects.filter(student=member).count()
        member.qr_scans = qr_scans
        total_qr_scans += qr_scans

        # Consider member active if they have any activity
        if photos_count > 0 or qr_scans > 0:
            active_members += 1

    # Calculate average activity percentage
    average_activity = round((active_members / members.count()) * 100) if members.count() > 0 else 0

    # New members today (simplified - you might want to use actual registration date)
    new_members_today = 0  # This would typically come from registration date

    context = {
        'house': house,
        'members': members,
        'admins_count': admins_count,
        'students_count': students_count,
        'active_members': active_members,
        'total_photos_uploaded': total_photos_uploaded,
        'total_qr_scans': total_qr_scans,
        'average_activity': average_activity,
        'new_members_today': new_members_today,
    }
    return render(request, 'houses/members.html', context)


@login_required
def house_scores(request, pk):
    house = get_object_or_404(House, pk=pk)
    scores = Score.objects.filter(house=house).select_related('event').order_by('-created_at')

    # Calculate basic statistics
    total_points = house.total_points()
    events_participated = scores.values('event').distinct().count()
    event_wins = 0  # This would need to be calculated based on event rankings

    # Calculate average score
    average_score = scores.aggregate(avg=Sum('points'))['avg'] or 0
    if scores.count() > 0:
        average_score = round(average_score / scores.count(), 1)

    # Highest score
    highest_score = scores.aggregate(max=Sum('points'))['max'] or 0

    # Participation rate
    total_events = Event.objects.count()
    participation_rate = round((events_participated / total_events) * 100) if total_events > 0 else 0

    # Points by event type
    points_by_type = []
    event_types_data = [
        {'type': 'major', 'name': 'Major Events', 'icon': 'fas fa-star', 'color': 'yellow'},
        {'type': 'minor', 'name': 'Minor Events', 'icon': 'fas fa-certificate', 'color': 'blue'},
        {'type': 'treasure', 'name': 'Treasure Hunt', 'icon': 'fas fa-search', 'color': 'green'},
        {'type': 'trivia', 'name': 'Trivia', 'icon': 'fas fa-brain', 'color': 'purple'},
    ]

    for event_type in event_types_data:
        type_scores = scores.filter(event__type=event_type['type'])
        type_points = type_scores.aggregate(total=Sum('points'))['total'] or 0
        type_count = type_scores.count()
        type_percentage = round((type_points / total_points) * 100) if total_points > 0 else 0

        points_by_type.append({
            **event_type,
            'points': type_points,
            'count': type_count,
            'percentage': type_percentage
        })

    # Add position to each score (this is simplified)
    for score in scores:
        # This would typically come from the actual event ranking
        score.position = 1  # Placeholder

    # Performance trends (simplified)
    current_streak = 1
    best_streak = 3
    best_event_type = "Major Events"
    average_points_per_event = round(total_points / max(1, events_participated))
    recent_performance = "Excellent"

    context = {
        'house': house,
        'scores': scores,
        'total_points': total_points,
        'events_participated': events_participated,
        'event_wins': event_wins,
        'average_score': average_score,
        'highest_score': highest_score,
        'participation_rate': participation_rate,
        'points_by_type': points_by_type,
        'current_streak': current_streak,
        'best_streak': best_streak,
        'best_event_type': best_event_type,
        'average_points_per_event': average_points_per_event,
        'recent_performance': recent_performance,
    }
    return render(request, 'houses/scores.html', context)