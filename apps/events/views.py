from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Event, Score
from apps.gallery.models import Image
from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Count, Avg, Max
from django.utils import timezone

from ..houses.models import House


def leaderboard(request):
    houses = House.objects.annotate(
        total_points=Sum('score__points')
    ).order_by('-total_points')

    # Calculate additional statistics
    total_events = Event.objects.count()
    total_points_awarded = Score.objects.aggregate(total=Sum('points'))['total'] or 0
    days_remaining = max(0, 5 - (timezone.now().date().day % 5))  # Simple calculation

    # Get max points for percentage calculation
    max_points = max([house.total_points or 0 for house in houses]) if houses else 1

    ranked_houses = []
    for i, house in enumerate(houses, 1):
        total_points = house.total_points or 0

        # Calculate additional metrics
        event_wins = Score.objects.filter(
            house=house,
            points__gt=0
        ).count()

        participated_events = Score.objects.filter(house=house).values('event').distinct().count()
        points_percentage = round((total_points / max_points) * 100) if max_points > 0 else 0
        points_per_day = round(total_points / max(1, days_remaining))
        participation_rate = round((participated_events / total_events) * 100) if total_events > 0 else 0

        # Determine trend (simplified - you could make this more sophisticated)
        recent_scores = Score.objects.filter(
            house=house,
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).aggregate(recent_points=Sum('points'))['recent_points'] or 0

        trend = 'up' if recent_scores > (total_points / max(1, days_remaining)) else 'stable'
        if total_points == 0:
            trend = 'stable'

        if i == 1:
            color = 'text-yellow-400'
            badge = '👑'
        elif i == 2:
            color = 'text-gray-300'
            badge = '🥈'
        elif i == 3:
            color = 'text-amber-600'
            badge = '🥉'
        else:
            color = 'text-white'
            badge = ''

        ranked_houses.append({
            'house': house,
            'rank': i,
            'total_points': total_points,
            'color': color,
            'badge': badge,
            'event_wins': event_wins,
            'participated_events': participated_events,
            'points_percentage': points_percentage,
            'points_per_day': points_per_day,
            'participation_rate': participation_rate,
            'trend': trend
        })

    # Event type breakdown
    event_types = [
        {'name': 'Major Events', 'type': 'major', 'icon': 'fas fa-star', 'color': 'yellow'},
        {'name': 'Minor Events', 'type': 'minor', 'icon': 'fas fa-certificate', 'color': 'blue'},
        {'name': 'Treasure Hunt', 'type': 'treasure', 'icon': 'fas fa-search', 'color': 'green'},
        {'name': 'Trivia', 'type': 'trivia', 'icon': 'fas fa-brain', 'color': 'purple'},
    ]

    event_type_breakdown = []
    for event_type in event_types:
        house_points = []
        for house in houses:
            points = Score.objects.filter(
                house=house,
                event__type=event_type['type']
            ).aggregate(total=Sum('points'))['total'] or 0
            house_points.append({'house': house, 'points': points})

        house_points.sort(key=lambda x: x['points'], reverse=True)
        event_type_breakdown.append({
            **event_type,
            'house_points': house_points[:3]  # Top 3 houses per event type
        })

    # Recent score updates
    recent_updates = Score.objects.select_related('event', 'house').order_by('-created_at')[:10]

    context = {
        'ranked_houses': ranked_houses,
        'total_events': total_events,
        'total_points_awarded': total_points_awarded,
        'days_remaining': days_remaining,
        'event_type_breakdown': event_type_breakdown,
        'recent_updates': recent_updates,
    }
    return render(request, 'events/leaderboard.html', context)


def event_schedule(request):
    events = Event.objects.all().order_by('day', 'time')

    # Group events by day with proper date formatting
    events_by_day = {}
    for event in events:
        # Format day as "Day X - Month Date" (e.g., "Day 1 - Oct 25")
        day_display = f"Day {event.day} - {event.day.strftime('%b %d')}"
        if day_display not in events_by_day:
            events_by_day[day_display] = []
        events_by_day[day_display].append(event)

    # Calculate statistics
    total_events = events.count()
    major_events = events.filter(type='major').count()
    minor_events = events.filter(type='minor').count()
    treasure_events = events.filter(type='treasure').count()
    trivia_events = events.filter(type='trivia').count()


    # Improved current day calculation
    today = timezone.localdate()
    current_day_number = 1  # Default to day 1

    # Find which day contains today's date
    unique_days = sorted(set(event.day for event in events))
    for i, day in enumerate(unique_days, 1):
        if day == today:
            current_day_number = i
            break
        elif day > today:
            # If we've passed today, use the previous day or first day
            current_day_number = max(1, i - 1)
            break
    else:
        # If all events are in the past, use the last day
        if unique_days:
            current_day_number = len(unique_days)

    context = {
        'events_by_day': events_by_day,
        'current_day': current_day_number,
        'total_events': total_events,
        'major_events': major_events,
        'minor_events': minor_events,
        'treasure_events': treasure_events,
        'trivia_events': trivia_events,
    }
    return render(request, 'events/schedule.html', context)


def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    scores = Score.objects.filter(event=event).select_related('house').order_by('-points')

    # Calculate statistics
    total_points = scores.aggregate(Sum('points'))['points__sum'] or 0
    max_points = scores.aggregate(Max('points'))['points__max'] or 0
    average_points = scores.aggregate(Avg('points'))['points__avg'] or 0

    # Calculate if event is completed
    event_datetime = timezone.datetime.combine(event.day, event.time)
    event_datetime = timezone.make_aware(event_datetime)
    is_completed = timezone.now() > event_datetime

    # Get related events
    related_events = Event.objects.filter(day=event.day).exclude(id=event.id).order_by('time')[:3]

    context = {
        'event': event,
        'scores': scores,
        'is_completed': is_completed,
        'max_points': max_points,
        'total_points': total_points,
        'average_points': round(average_points, 1),
        'related_events': related_events,
    }
    return render(request, 'events/event_detail.html', context)


def event_scores(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    scores = Score.objects.filter(event=event).select_related('house').order_by('-points')

    # Calculate statistics
    total_points = scores.aggregate(Sum('points'))['points__sum'] or 0
    average_points = scores.aggregate(Avg('points'))['points__avg'] or 0
    max_points = scores.aggregate(Max('points'))['points__max'] or 0

    # Add percentage for each score
    scored_scores = []
    for score in scores:
        percentage = round((score.points / max_points) * 100) if max_points > 0 else 0
        scored_scores.append({
            'house': score.house,
            'points': score.points,
            'percentage': percentage,
            'created_at': score.created_at
        })

    # Get related events
    related_events = Event.objects.exclude(id=event.id).order_by('day', 'time')[:6]

    context = {
        'event': event,
        'scores': scored_scores,
        'total_points': total_points,
        'average_points': round(average_points, 1),
        'max_points': max_points,
        'related_events': related_events,
    }
    return render(request, 'events/event_scores.html', context)
