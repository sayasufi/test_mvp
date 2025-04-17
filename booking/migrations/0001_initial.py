# Generated by Django 4.2.20 on 2025-04-17 10:42

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import psqlextra.backend.migrations.operations.add_default_partition
import psqlextra.backend.migrations.operations.create_partitioned_model
import psqlextra.manager.manager
import psqlextra.models.partitioned
import psqlextra.types


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        psqlextra.backend.migrations.operations.create_partitioned_model.PostgresCreatePartitionedModel(
            name='Booking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
            ],
            options={
                'ordering': ['date', 'start_time'],
            },
            partitioning_options={
                'method': psqlextra.types.PostgresPartitioningMethod['RANGE'],
                'key': ['date'],
            },
            bases=(psqlextra.models.partitioned.PostgresPartitionedModel,),
            managers=[
                ('objects', psqlextra.manager.manager.PostgresManager()),
            ],
        ),
        psqlextra.backend.migrations.operations.add_default_partition.PostgresAddDefaultPartition(
            model_name='Booking',
            name='default',
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('capacity', models.PositiveIntegerField()),
                ('floor', models.IntegerField()),
            ],
            options={
                'ordering': ['floor', 'name'],
            },
        ),
        migrations.AddField(
            model_name='booking',
            name='room',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='booking.room'),
        ),
        migrations.AddField(
            model_name='booking',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['room', 'date', 'start_time', 'end_time'], name='idx_room_date_time'),
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['user', 'date', 'start_time', 'end_time'], name='idx_user_date_time'),
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['date', 'start_time', 'end_time', 'room'], name='idx_date_start_end_room'),
        ),
        migrations.AlterUniqueTogether(
            name='booking',
            unique_together={('room', 'date', 'start_time', 'end_time')},
        ),
    ]
