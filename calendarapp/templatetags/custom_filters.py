from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def date_range(start_date, end_date):
    # Generate all dates between start_date and end_date (inclusive)
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)
