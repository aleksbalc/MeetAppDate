# views.py
from django import template
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import loader
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from . import forms
import hashlib
from .forms import EventForm, GuestAvailabilityForm, NameForm, PasswordForm
from .models import Event, AvailableDate, GuestAvailability, Name
from datetime import timedelta, datetime
from django.core.mail import send_mail

def add_name(request):
    if request.method == 'POST':
        form = NameForm(request.POST)
        if form.is_valid():
            name_instance = form.save()  # Save the form and get the instance
            return redirect('show_event', access_code=name_instance.access_code)  # Redirect to event/<access_code>/
    else:
        form = NameForm()
    return render(request, 'add_name.html', {'form': form})

def show_event(request, access_code):
    try:
        name = Name.objects.get(access_code=access_code)
    except Name.DoesNotExist:
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
                return render(request, 'show_event.html', {'name': name})

        # If access has expired, remove the session keys
        del request.session[access_key]
        del request.session[access_time_key]

    # Handle password submission
    if request.method == 'POST':
        form = PasswordForm(request.POST)
        if form.is_valid():
            entered_password = form.cleaned_data['password']

            if check_password(entered_password, name.password):  # Use Django's check_password
                # Save the access flag and timestamp in the session
                request.session[access_key] = True
                request.session[access_time_key] = datetime.now().isoformat()  # Save the current time
                return redirect('show_event', access_code=access_code)
            else:
                form.add_error('password', 'Incorrect password. Please try again.')
    else:
        form = PasswordForm()

    return render(request, 'enter_password.html', {'form': form, 'access_code': access_code})


def show_name(request):
    name_id = request.session.get('last_name_id')
    if not name_id:
        raise Http404("No submitted name found in the session.")
    try:
        name = Name.objects.get(id=name_id)
    except Name.DoesNotExist:
        raise Http404("The record does not exist.")
    return render(request, 'show_name.html', {'name': name})


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
