import csv
from django.conf import settings
from django.db.backends.utils import logger
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import login
import logging

from django.contrib.auth.views import PasswordResetView
from django.http import HttpResponse, Http404, HttpRequest
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, NoReverseMatch
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.generic import CreateView, FormView
from .forms import StudentLoginForm, StudentRegistrationForm, HouseRandomizationForm
from .house_assignment import HouseRandomizer
from .models import Student


@method_decorator(csrf_exempt, name='dispatch')
class StudentLoginView(FormView):
    template_name = 'users/login.html'
    form_class = StudentLoginForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        user = form.get_user()
        if not user:
            form.add_error(None, "Authentication failed.")
            return self.form_invalid(form)

        # Explicitly supply the backend path to login() — safer than mutating user.backend.
        backend_path = 'apps.core.backends.HouseAuthenticationBackend'
        try:
            login(self.request, user, backend=backend_path)
        except Exception as e:
            # Log details so we can see what's wrong instead of swallowing it silently.
            logger.exception("Login failed for user %s: %s", getattr(user, 'matric_number', user), e)
            form.add_error(None, "Could not log you in. Contact admin.")
            return self.form_invalid(form)

        # Prefer the next param if provided
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return redirect(next_url)

        # Admin branch
        if getattr(user, 'role', None) == 'admin' or user.is_staff or user.is_superuser:
            messages.success(self.request, f'Welcome back, Administrator {user.name}!')
            try:
                # be explicit about the error type we expect
                return redirect('admin_dashboard:dashboard')
            except NoReverseMatch:
                # if the named URL doesn't exist, fallback to an admin known location
                try:
                    return redirect(reverse('admin:index'))
                except NoReverseMatch:
                    return redirect('home')

        # Student branch
        messages.success(self.request, f'Welcome to {user.house.name if user.house else "Your House"}, {user.name}!')
        # If you have a dedicated house dashboard, redirect there. Example:
        if getattr(user, 'house', None):
            try:
                return redirect('houses:dashboard', slug=user.house.slug)   # adjust to your URLconf
            except NoReverseMatch:
                return redirect('home')

        # Default fallback
        return redirect('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '')
        return context


class StudentRegistrationView(CreateView):
    model = Student
    form_class = StudentRegistrationForm
    template_name = 'users/register.html'

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password1'])
        user.save()
        #login(self.request, user)
        messages.success(self.request, f'Account created for {user.name}!')
        return redirect('houses:dashboard')


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')



from django.views.generic import TemplateView
from django.db import models, transaction

# Defensive imports — won't crash if models don't exist yet
try:
    from apps.events.models import Event
except Exception:
    Event = None

def safe_queryset(model, filter_kwargs=None, order_fields=None, limit=4):
    """
    Try to filter and order a queryset defensively:
      - if `filter_kwargs` contains invalid fields, ignore the filter.
      - try ordering by the first valid field in `order_fields`.
      - always return a sliced queryset (limit).
    """
    qs = model.objects.all()
    # apply filter if possible
    if filter_kwargs:
        try:
            qs = qs.filter(**filter_kwargs)
        except Exception:
            # invalid filter keys or other issues — ignore filter
            pass

    # attempt ordering by first valid order field
    if order_fields:
        for field in order_fields:
            # ensure field exists on model (handle dotted lookups too)
            try:
                # use model._meta.get_field to validate simple fields
                model._meta.get_field(field)
                qs = qs.order_by(field)
                break
            except Exception:
                # try without validation (covers annotate/related lookups) but swallow exceptions
                try:
                    qs = qs.order_by(field)
                    break
                except Exception:
                    continue

    # final fallback: no ordering applied -> let DB return something stable
    return qs[:limit]


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Upcoming events - fixed version
        try:
            # Get upcoming events (today or future)
            upcoming_events = Event.objects.filter(
                day__gte=timezone.localdate()
            ).order_by('day', 'time')[:4]

            ctx["upcoming_events"] = upcoming_events
        except Exception as e:
            # Fallback if there's any issue with Event model
            print(f"Error loading events: {e}")  # Remove in production
            ctx["upcoming_events"] = []

        # Houses logic (kept same as before)
        try:
            from apps.houses.models import House
            ctx["houses"] = House.objects.all()[:6]
        except Exception:
            ctx["houses"] = [
                {"name": "Red Lions", "slug": "#", "description": "Strength & heart"},
                {"name": "Blue Waves", "slug": "#", "description": "Speed & flow"},
                {"name": "Gold Eagles", "slug": "#", "description": "Precision & pride"},
            ]

        # Gallery logic - fixed to match your actual model
        try:
            from apps.gallery.models import Image  # Changed from Photo to Image based on your models
            ctx["gallery"] = Image.objects.filter(approved=True).order_by("-timestamp")[:6]
        except Exception as e:
            print(f"Error loading gallery: {e}")  # Remove in production
            ctx["gallery"] = []

        return ctx


class HouseRandomizationView(TemplateView):
    template_name = 'users/randomization.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = HouseRandomizationForm()
        context['house_stats'] = HouseRandomizer.get_house_stats()
        return context

    def post(self, request, *args, **kwargs):
        form = HouseRandomizationForm(request.POST)

        if not form.is_valid():
            context = self.get_context_data()
            context['form'] = form
            return render(request, self.template_name, context)

        name = form.cleaned_data['name']
        level = form.cleaned_data['level']
        department = form.cleaned_data['department']
        matric_number = form.cleaned_data['matric_number']

        # If already assigned: show results
        existing_student = HouseRandomizer.check_existing_assignment(
            name, level, department, matric_number
        )
        if existing_student:
            house_info = HouseRandomizer.get_house_info(
                (existing_student.house.name.lower() if existing_student.house else '')
            )
            return render(request, 'users/randomization_result.html', {
                'student': existing_student,
                'house_info': house_info,
                'existing': True
            })

        # Generate matric if missing
        if not matric_number:
            matric_number = HouseRandomizer.generate_matric_number()

        # Create or update student (without assigning house yet)
        student, created = Student.objects.get_or_create(
            matric_number=matric_number,
            defaults={
                'name': name,
                'level': level,
                'department': department,
                'role': 'student',
                'randomization_complete': False
            }
        )
        if not created:
            # update details if it already existed
            student.name = name
            student.level = level
            student.department = department
            student.randomization_complete = False
            student.save()

        # Optional: set a default password if newly created (be mindful of security)
        if created:
            default_password = matric_number
            student.set_password(default_password)
            student.save()

        # Assign house — use a transaction and update student properly
        try:
            with transaction.atomic():
                house = HouseRandomizer.assign_house(student)  # should return a House instance
                # mark as completed and save
                student.house = house
                student.randomization_complete = True
                student.save()
        except Exception as e:
            # Log or surface the error — don't let a crash create a confusing UX
            # import logging; logger.exception(...)
            messages.error(request, "Could not assign a house right now. Try again or contact admin.")
            context = self.get_context_data()
            context['form'] = form
            return render(request, self.template_name, context)

        # Get house info safely
        house_info = HouseRandomizer.get_house_info(house.name.lower() if house and house.name else '')

        # Optional: auto-login the user after randomization (uncomment if you want this behavior)
        # from django.conf import settings
        # backend_path = 'apps.core.backends.HouseAuthenticationBackend'
        # try:
        #     login(request, student, backend=backend_path)
        # except Exception:
        #     pass

        return render(request, 'users/randomization_result.html', {
            'student': student,
            'house_info': house_info,
            'existing': student.randomization_complete
        })


class RandomizationStatsView(View):
    """Admin view to see randomization statistics"""

    def get(self, request):
        if not request.user.is_authenticated or request.user.role != 'admin':
            messages.error(request, "Admin access required")
            return redirect('core:login')

        house_stats = HouseRandomizer.get_house_stats()
        total_students = Student.objects.filter(role='student', randomization_complete=True).count()

        context = {
            'house_stats': house_stats,
            'total_students': total_students,
        }
        return render(request, 'users/randomization_stats.html', context)


class ExportStudentsCSVView(View):
    """Export all students with house assignments to CSV"""

    def get(self, request):
        if not request.user.is_authenticated or request.user.role != 'admin':
            messages.error(request, "Admin access required")
            return redirect('core:login')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="student_house_assignments.csv"'

        writer = csv.writer(response)
        writer.writerow(['Matric Number', 'Name', 'Level', 'Department', 'House', 'Randomized At'])

        students = Student.objects.filter(
            role='student',
            randomization_complete=True
        ).select_related('house').order_by('house__name', 'matric_number')

        for student in students:
            writer.writerow([
                student.matric_number,
                student.name,
                student.level,
                student.department,
                student.house.name if student.house else 'Not Assigned',
                student.randomized_at.strftime('%Y-%m-%d %H:%M') if student.randomized_at else ''
            ])

        return response


@require_GET
def join_house_whatsapp(request: HttpRequest, house_code: str) -> HttpResponse:
    """
    Simple redirect to the house WhatsApp invite link.
    No tracking, no DB writes — purely a validated redirect.
    """
    if not house_code:
        raise Http404("House not found")

    house_code = house_code.lower().strip()
    whatsapp_link = HouseRandomizer.HOUSE_LINKS.get(house_code)

    if not whatsapp_link:
        # Friendly 404 for missing invite links
        raise Http404("WhatsApp group link not available for this house")

    # Direct redirect to the WhatsApp invite URL
    return redirect(whatsapp_link)