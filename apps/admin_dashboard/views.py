from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, CreateView, DetailView
from django.db.models import Sum, Count
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from apps.houses.models import House
from apps.events.models import Event, Score
from apps.gallery.models import Image
from apps.notifications.models import Notification
from .forms import ScoreForm, EventForm
from ..core.models import Student


def admin_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (u.role == 'admin' or u.is_staff),
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


class AdminDashboardView(TemplateView):
    template_name = 'admin/dashboard.html'

    @method_decorator(login_required)
    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_houses'] = House.objects.count()
        context['total_images'] = Image.objects.count()
        context['pending_approvals'] = Image.objects.filter(approved=False).count()
        context['recent_activity'] = Notification.objects.order_by('-timestamp')[:10]

        context['house_stats'] = House.objects.annotate(
            total_points=Coalesce(Sum('score__points'), 0),
            total_members=Count('students', distinct=True)
        ).order_by('-total_points')

        return context

class ScoreEntryView(CreateView):
    model = Score
    form_class = ScoreForm
    template_name = 'admin/score_entry.html'
    success_url = reverse_lazy('admin_dashboard:dashboard')

    @method_decorator(login_required)
    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request,
                         f"Successfully added {form.cleaned_data['points']} points to {form.cleaned_data['house'].name}!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_scores'] = Score.objects.select_related('event', 'house').order_by('-created_at')[:10]
        return context


class ImageApprovalListView(ListView):
    model = Image
    template_name = 'admin/image_approval.html'
    context_object_name = 'pending_images'

    @method_decorator(login_required)
    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        return Image.objects.filter(approved=False).select_related('uploader', 'uploader__house').order_by('timestamp')


@login_required
@admin_required
def approve_image(request, pk):
    image = get_object_or_404(Image, pk=pk)
    image.approved = True
    image.save()

    # Send notification to uploader
    Notification.objects.create(
        user=image.uploader,
        message=f"Your image '{image.description or 'photo'}' has been approved!",
        type='media_approved'
    )

    messages.success(request, 'Image approved successfully!')
    return redirect('admin_dashboard:image_approval')


@login_required
@admin_required
def reject_image(request, pk):
    image = get_object_or_404(Image, pk=pk)
    image_description = image.description or "image"
    image.delete()

    messages.success(request, f'Image "{image_description}" rejected and deleted.')
    return redirect('admin_dashboard:image_approval')


class EventCreateView(CreateView):
    model = Event
    form_class = EventForm
    template_name = 'admin/create_event.html'
    success_url = reverse_lazy('admin_dashboard:dashboard')

    @method_decorator(login_required)
    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Event '{form.cleaned_data['title']}' created successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['upcoming_events'] = Event.objects.filter(
            day__gte=timezone.localdate()
        ).order_by('day', 'time')[:5]
        return context


@login_required
@admin_required
def send_notification(request):
    total_users = Student.objects.count()

    if request.method == 'POST':
        message = request.POST.get('message')
        notification_type = request.POST.get('type', 'general')

        if not message:
            messages.error(request, "Please enter a notification message.")
            return render(request, 'admin/send_notification.html', {
                'total_users': total_users,
                'recent_notifications': Notification.objects.order_by('-timestamp')[:10]
            })

        # Create notification for all users
        users = Student.objects.all()
        notification_count = 0

        for user in users:
            Notification.objects.create(
                user=user,
                message=message,
                type=notification_type
            )
            notification_count += 1

        # Send push notifications (you'll need to implement this)
        # send_push_notification_to_all(message)

        messages.success(request, f"Notification sent to {notification_count} users!")
        return redirect('admin_dashboard:dashboard')

    return render(request, 'admin/send_notification.html', {
        'total_users': total_users,
        'recent_notifications': Notification.objects.order_by('-timestamp')[:10]
    })


