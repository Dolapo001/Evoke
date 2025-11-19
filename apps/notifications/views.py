import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from pywebpush import webpush, WebPushException
from django.conf import settings
from .models import PushSubscription, Notification


@require_POST
@csrf_exempt
@login_required
def save_subscription(request):
    try:
        data = json.loads(request.body)
        subscription_data = data.get('subscription')

        # Save subscription
        PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=subscription_data['endpoint'],
            defaults={
                'p256dh': subscription_data['keys']['p256dh'],
                'auth': subscription_data['keys']['auth']
            }
        )

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def send_push_notification(user, message, url=''):
    """Send push notification to a specific user"""
    subscriptions = PushSubscription.objects.filter(user=user)

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth
                    }
                },
                data=json.dumps({
                    "title": "Evoke Sports Week",
                    "message": message,
                    "url": url
                }),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": "mailto:admin@evoke.com",
                }
            )
        except WebPushException as ex:
            print("Web push failed: {}", repr(ex))
            # Delete invalid subscription
            if ex.response.status_code == 410:
                subscription.delete()


@login_required
def user_notifications(request):
    notifications = Notification.objects.filter(user=request.user)[:20]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return JsonResponse({
        'notifications': [
            {
                'message': n.message,
                'type': n.type,
                'timestamp': n.timestamp.isoformat(),
                'url': n.url,
                'is_read': n.is_read
            }
            for n in notifications
        ],
        'unread_count': unread_count
    })


@require_POST
@login_required
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error'})