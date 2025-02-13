# views.py
from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import loader
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from . import forms
from .forms import EventForm, GuestAvailabilityForm, NameForm
from .models import Event, AvailableDate, GuestAvailability, Name
from datetime import timedelta
from django.core.mail import send_mail

def add_name(request):
    if request.method == 'POST':
        form = NameForm(request.POST)
        if form.is_valid():
            name_instance = form.save()  # Save the form and get the instance
            request.session['last_name_id'] = name_instance.id  # Store the id in session
            return redirect('show_name')
    else:
        form = NameForm()
    return render(request, 'add_name.html', {'form': form})

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
