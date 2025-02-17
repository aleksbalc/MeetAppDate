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
import hashlib
from .forms import EventForm, GuestAvailabilityForm, PasswordForm
from .models import Event, AvailableDate, GuestAvailability
from datetime import timedelta, datetime, date
from django.core.mail import send_mail

def add_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event_instance = form.save()  # Save the form and get the instance
            return redirect('show_event', access_code=event_instance.access_code)  # Redirect to event/<access_code>/
    else:
        form = EventForm()
    return render(request, 'add_event.html', {'form': form})

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
                return render(request, 'show_event.html', {'event': event, "today":date.today()})

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

    # Session-based authentication check
    access_key = f'event_access_{access_code}'
    access_time_key = f'event_access_time_{access_code}'
    session_expiry_minutes = 30  # Set session timeout

    if not request.session.get(access_key):
        return redirect('show_event', access_code=access_code)  # Redirect to password page if not authenticated

    # Check session expiration
    access_time = request.session.get(access_time_key)
    if access_time:
        access_time = datetime.fromisoformat(access_time)
        if datetime.now() - access_time > timedelta(minutes=session_expiry_minutes):
            del request.session[access_key]
            del request.session[access_time_key]
            return redirect('show_event', access_code=access_code)  # Redirect to re-enter password

    if request.method == "POST":
        guest_name = request.POST.get("guest_name", "").strip()
        selected_dates = request.POST.getlist("available_dates")

        if not guest_name or not selected_dates:
            return render(request, "add_availability.html", {
                "event": event,
                "error": "Please fill in all fields."
            })

        guest = GuestAvailability.objects.create(event=event, name=guest_name)

        for date_str in selected_dates:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
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

    html_template = loader.get_template('home/index.html')
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
