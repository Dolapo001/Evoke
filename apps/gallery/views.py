from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
import zipfile
import io
import os

from .models import Image, DailyHighlight
from .forms import ImageUploadForm
from apps.houses.models import House
from apps.notifications.models import Notification


@login_required
def gallery_home(request):
    images = Image.objects.filter(approved=True).select_related('uploader', 'house')
    daily_highlights = DailyHighlight.objects.filter(is_active=True)

    # Get all houses for filter
    houses = House.objects.all()

    # Get filter parameters
    house_filter = request.GET.get('house')
    day_filter = request.GET.get('day')

    if house_filter:
        images = images.filter(house_id=house_filter)
    if day_filter:
        # Filter by day based on timestamp (simplified)
        # You might want to add a day field to Image model for better filtering
        pass

    # Add like status for current user
    for image in images:
        image.is_liked = image.is_liked_by(request.user)

    context = {
        'images': images,
        'daily_highlights': daily_highlights,
        'total_images': images.count(),
        'houses': houses,
    }
    return render(request, 'gallery/home.html', context)


@login_required
def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                image = form.save(commit=False)
                image.uploader = request.user
                image.house = request.user.house
                image.save()

                # Notify admins
                Notification.objects.create(
                    message=f"New image uploaded by {request.user.name} - needs approval",
                    type='media'
                )

                messages.success(request, 'Image uploaded successfully! Waiting for admin approval.')
                return redirect('gallery:home')

            except Exception as e:
                messages.error(request, f'Error uploading image: {str(e)}')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ImageUploadForm()

    context = {
        'form': form,
    }
    return render(request, 'gallery/upload.html', context)


@require_POST
@login_required
def like_image(request, image_id):
    try:
        image = get_object_or_404(Image, id=image_id, approved=True)

        if image.likes.filter(id=request.user.id).exists():
            image.likes.remove(request.user)
            liked = False
        else:
            image.likes.add(request.user)
            liked = True

        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': image.like_count()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def download_image(request, image_id):
    try:
        image = get_object_or_404(Image, id=image_id, approved=True)

        # Get the image file content
        if image.file and hasattr(image.file, 'read'):
            image_file = image.file.read()
        else:
            # Fallback if file is not accessible
            messages.error(request, 'Image file not found.')
            return redirect('gallery:detail', image_id=image_id)

        # Create safe filename
        if image.description:
            safe_filename = f"{image.description.replace(' ', '_')}_{image.id}.jpg"
        else:
            safe_filename = f"evoke_memory_{image.id}.jpg"

        # Clean filename
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in ('_', '-', '.'))

        # Create response with appropriate content type
        response = HttpResponse(image_file, content_type='image/jpeg')
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'

        return response

    except Exception as e:
        messages.error(request, f'Error downloading image: {str(e)}')
        return redirect('gallery:detail', image_id=image_id)


@login_required
def download_all_memories(request):
    """Generate zip file of all approved images"""
    try:
        images = Image.objects.filter(approved=True)

        if not images.exists():
            messages.error(request, 'No images available for download.')
            return redirect('gallery:home')

        # Create in-memory zip file
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for image in images:
                try:
                    if image.file and hasattr(image.file, 'read'):
                        image_data = image.file.read()

                        # Create a safe filename
                        if image.description:
                            safe_name = f"{image.description.replace(' ', '_')}_{image.id}.jpg"
                        else:
                            safe_name = f"memory_{image.uploader.name.replace(' ', '_')}_{image.id}.jpg"

                        # Clean filename
                        safe_name = "".join(c for c in safe_name if c.isalnum() or c in ('_', '-', '.'))
                        filename = f"evoke_memories/{safe_name}"

                        zip_file.writestr(filename, image_data)

                except Exception as e:
                    print(f"Error processing image {image.id}: {e}")
                    continue

        zip_buffer.seek(0)

        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="evoke_sports_week_memories.zip"'
        return response

    except Exception as e:
        messages.error(request, f'Error creating zip file: {str(e)}')
        return redirect('gallery:home')


@login_required
def image_detail(request, image_id):
    try:
        image = get_object_or_404(Image, id=image_id, approved=True)
        related_images = Image.objects.filter(
            approved=True,
            house=image.house
        ).exclude(id=image_id)[:6]

        # Add statistics
        total_views = 0  # You might want to implement view counting
        image.uploader.images_uploaded = Image.objects.filter(uploader=image.uploader, approved=True).count()
        image.house.images_uploaded = Image.objects.filter(house=image.house, approved=True).count()

        # Split tags for display
        if image.tags:
            image.tags_split = [tag.strip() for tag in image.tags.split(',')]
        else:
            image.tags_split = []

        context = {
            'image': image,
            'related_images': related_images,
            'is_liked': image.is_liked_by(request.user),
            'total_views': total_views,
        }
        return render(request, 'gallery/detail.html', context)

    except Exception as e:
        messages.error(request, f'Error loading image: {str(e)}')
        return redirect('gallery:home')