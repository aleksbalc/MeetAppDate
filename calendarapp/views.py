# views.py
from django import template
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.utils.dateparse import parse_date
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import loader
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from . import forms
import json
import random
from .forms import EventForm, GuestAvailabilityForm, PasswordForm
from .models import Event, AvailableDate, GuestAvailability
from datetime import timedelta, datetime, date
from django.core.mail import send_mail
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

def edit_event(request, access_code):
    """Allows event editing. Checks if the user is an authenticated host, else requests OTP verification."""
    event = get_object_or_404(Event, access_code=access_code)
    host_session_key = f'host_authenticated_{access_code}'
    otp_cache_key = f'otp_{event.email}'

    if request.session.get(host_session_key):
        if request.method == "POST":
            form = EventForm(request.POST, instance=event)
            if form.is_valid():
                form.save()
                return redirect('show_event', access_code=event.access_code)  # Redirect to event details
            else:
                print(form.errors)
        else:
            form = EventForm(instance=event)

        return render(request, 'edit_event.html', {'form': form, 'event': event})  # Show errors if form is invalid

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            otp_entered = data.get("otp")

            cached_otp = cache.get(otp_cache_key)
            if str(cached_otp) == otp_entered:
                cache.delete(otp_cache_key)
                request.session[host_session_key] = True
                request.session.set_expiry(900)
                return JsonResponse({"success": True, "message": "OTP verified. You can now edit the event."})

            return JsonResponse({"success": False, "message": "Invalid OTP. Please try again."})
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Invalid request format."})

    if not cache.get(otp_cache_key):
        otp = random.randint(100000, 999999)
        cache.set(otp_cache_key, otp, timeout=300)

        send_mail(
            "Your Event Edit OTP",
            f"Your OTP for editing event '{event.name}' is {otp}. It expires in 5 minutes.",
            settings.EMAIL_HOST_USER,
            [event.email],
            fail_silently=False,
        )

    return render(request, 'verify_host.html', {'event': event})


def add_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event_instance = form.save()

            # Store session key for host authentication 
            host_session_key = f'host_authenticated_{event_instance.access_code}'
            request.session[host_session_key] = True

            # Store session key for event access
            access_key = f'event_access_{event_instance.access_code}'
            access_time_key = f'event_access_time_{event_instance.access_code}'

            request.session[access_key] = True
            request.session[access_time_key] = datetime.now().isoformat()
            request.session.set_expiry(1800)  # 30 minutes

            return redirect('show_event', access_code=event_instance.access_code)
        else:
            print(form.errors)

    else:
        form = EventForm()
    return render(request, 'add_event.html', {'form': form})

@csrf_exempt
def send_otp(request):
    """Sends OTP to the provided email with a cooldown to prevent abuse."""
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")

        if not email:
            return JsonResponse({"success": False, "message": "Email is required."})

        # Check if OTP was sent recently (cooldown period: 2 minutes)
        last_sent_time = cache.get(f'otp_time_{email}')
        cooldown_seconds = 120  # 2 minutes

        if last_sent_time:
            time_since_last_otp = (datetime.now() - last_sent_time).total_seconds()
            if time_since_last_otp < cooldown_seconds:
                remaining_time = int(cooldown_seconds - time_since_last_otp)
                return JsonResponse({
                    "success": False, 
                    "message": f"Please wait {remaining_time} seconds before requesting a new OTP."
                })

        # Generate a new OTP
        otp = random.randint(100000, 999999)
        cache.set(f'otp_{email}', otp, timeout=300)  # 5 minutes expiry
        cache.set(f'otp_time_{email}', datetime.now(), timeout=cooldown_seconds)  # Store last OTP request time

        # Send the OTP via email
        send_mail(
            "Your OTP Code",
            f"Your OTP is {otp}. It will expire in 5 minutes.",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return JsonResponse({"success": True, "message": "OTP sent successfully."})
    
    return JsonResponse({"success": False, "message": "Invalid request."})


def verify_otp(request):
    """Verifies if the OTP is correct."""
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")
        otp = data.get("otp")

        if not email or not otp:
            return JsonResponse({"success": False, "message": "Email and OTP are required."})

        cached_otp = cache.get(f'otp_{email}')

        if str(cached_otp) == otp:
            cache.delete(f'otp_{email}')  # Remove OTP after successful verification
            return JsonResponse({"success": True, "message": "OTP verified successfully."})
        
        return JsonResponse({"success": False, "message": "Invalid OTP."})
    
    return JsonResponse({"success": False, "message": "Invalid request."})

def show_event(request, access_code):
    try:
        event = Event.objects.get(access_code=access_code)
    except Event.DoesNotExist:
        raise Http404("Event not found.")

    # Check if the user is already authenticated for this event
    access_key = f'event_access_{access_code}'
    access_time_key = f'event_access_time_{access_code}'
    session_expiry_minutes = 30  # Set the session validity duration (e.g., 30 minutes)

    # Check if the access flag and timestamp exist
    if request.session.get(access_key):
        access_time = request.session.get(access_time_key)
        if access_time:
            access_time = datetime.fromisoformat(access_time)
            # Check if the access is still valid
            if datetime.now() - access_time < timedelta(minutes=session_expiry_minutes):
                guest_availabilities = AvailableDate.objects.filter(guest__event=event).select_related('guest')

                availability_data = {}  # Store date-wise guest availability
                guest_names = sorted([guest.name for guest in GuestAvailability.objects.filter(event=event)])

                for availability in guest_availabilities:
                    date_str = availability.date.strftime("%Y-%m-%d")
                    if date_str not in availability_data:
                        availability_data[date_str] = []
                    availability_data[date_str].append(availability.guest.name)

                # Find Perfect and Great Dates
                perfect_dates = []
                great_dates = {}

                for dates, guests in availability_data.items():
                    if sorted(guests) == guest_names:  # Check if all guests are available
                        perfect_dates.append(dates)
                    else:
                        great_dates[dates] = guests  # Store guests available on each date

                # Sort great dates by most available guests
                sorted_great_dates = sorted(great_dates.items(), key=lambda x: len(x[1]), reverse=True)

                return render(request, 'show_event.html', {
                    'event': event,
                    'today': date.today(),
                    'availability_data': json.dumps(availability_data),
                    'perfect_dates': perfect_dates,
                    'great_dates': sorted_great_dates[:5],
                    'guest_names': guest_names  # Send full guest list for availability checking
                })

        # If access has expired, remove the session keys
        del request.session[access_key]
        del request.session[access_time_key]

    # Handle password submission
    if request.method == 'POST':
        form = PasswordForm(request.POST)
        if form.is_valid():
            entered_password = form.cleaned_data['password']

            if check_password(entered_password, event.password):  # Use Django's check_password
                # Save the access flag and timestamp in the session
                request.session[access_key] = True
                request.session[access_time_key] = datetime.now().isoformat()  # Save the current time
                return redirect('show_event', access_code=access_code)
            else:
                form.add_error('password', 'Incorrect password. Please try again.')
    else:
        form = PasswordForm()

    return render(request, 'enter_password.html', {'form': form, 'access_code': access_code})

def add_availability(request, access_code):
    event = get_object_or_404(Event, access_code=access_code)

    # Ensure user is authenticated for this event
    access_key = f'event_access_{access_code}'
    access_time_key = f'event_access_time_{access_code}'
    session_expiry_minutes = 30

    if not request.session.get(access_key):
        return redirect('show_event', access_code=access_code)

    access_time = request.session.get(access_time_key)
    if access_time:
        access_time = datetime.fromisoformat(access_time)
        if datetime.now() - access_time > timedelta(minutes=session_expiry_minutes):
            del request.session[access_key]
            del request.session[access_time_key]
            return redirect('show_event', access_code=access_code)

    if request.method == "POST":
        guest_name = request.POST.get("guest_name", "").strip()
        selected_dates_str = request.POST.get("available_dates", "")

        if not guest_name or not selected_dates_str:
            return render(request, "add_availability.html", {
                "event": event,
                "error": "Please fill in all fields."
            })

        guest = GuestAvailability.objects.create(event=event, name=guest_name)

        selected_dates = selected_dates_str.split(",")
        for date_str in selected_dates:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if event.start_date <= parsed_date <= event.end_date:
                    AvailableDate.objects.create(guest=guest, date=parsed_date)
            except ValueError:
                print(f"Invalid date: {date_str}")

        return redirect("show_event", access_code=access_code)

    return render(request, "add_availability.html", {"event": event})


def submit_availability(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if request.method == "POST":
        password = request.POST.get("password")
    if not event.check_password(password):
        return render(request, "submit_availability.html", {"event": event, "error": "Invalid password"})
    form = GuestAvailabilityForm(request.POST)
    if form.is_valid():
        guest_availability = form.save(commit=False)
        guest_availability.event = event
        guest_availability.save()
        form.save_m2m()  # Save Many-to-Many relationships
        return redirect("availability_submitted")
    else:
        form = GuestAvailabilityForm()
        return render(request, "submit_availability.html", {"event": event, "form": form})

def post_event(request):
    if request.method == 'POST':
        form = forms.CreateEvent(request.POST)
        if form.is_valid():
            new_event = form.save(commit=False)
            new_event.save()
            return redirect('create-event')
    else:
        form = forms.CreateEvent()
    return render(request, 'events/post_event.html', {'form':form})

def index(request):
    context = {'segment': 'index'}

    html_template = loader.get_template('home.html')
    return HttpResponse(html_template.render(context, request))


def pages(request):
    context = {}
    # All resource paths end in .html.
    # Pick out the html file name from the url. And load that template.
    try:

        load_template = request.path.split('/')[-1]

        if load_template == 'admin':
            return HttpResponseRedirect(reverse('admin:index'))
        context['segment'] = load_template

        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))

def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('success_url')  # Replace 'success_url' with the URL where you want to redirect after successful form submission
    else:
        form = EventForm()
    
    return render(request, 'create_event.html', {'form': form})
