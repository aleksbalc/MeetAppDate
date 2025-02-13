# Generated by Django 3.2.6 on 2025-02-13 13:18

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('calendarapp', '0005_auto_20250213_1301'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='availabledate',
            name='event',
        ),
        migrations.RemoveField(
            model_name='guestavailability',
            name='available_dates',
        ),
        migrations.RemoveField(
            model_name='guestavailability',
            name='created_at',
        ),
        migrations.AddField(
            model_name='availabledate',
            name='guest',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='calendarapp.guestavailability'),
        ),
        migrations.AlterField(
            model_name='availabledate',
            name='date',
            field=models.DateField(default=datetime.date.today),
        ),
        migrations.AlterField(
            model_name='guestavailability',
            name='name',
            field=models.CharField(default='', max_length=100),
        ),
    ]
