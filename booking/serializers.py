from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Room, Booking


class RoomSerializer(serializers.ModelSerializer):
    name = serializers.CharField(help_text="Room name")
    capacity = serializers.IntegerField(help_text="Maximum capacity")
    floor = serializers.IntegerField(help_text="Floor number")

    class Meta:
        model = Room
        fields = '__all__'
        read_only_fields = ['id']


class BookingSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault(),
        help_text="ID of the user who created the booking"
    )
    room = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        help_text="ID of the room to book"
    )
    date = serializers.DateField(help_text="Booking date (YYYY-MM-DD)")
    start_time = serializers.TimeField(format="%H:%M:%S", help_text="Start time (HH:MM:SS)")
    end_time = serializers.TimeField(format="%H:%M:%S", help_text="End time (HH:MM:SS)")

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['id']

    def validate(self, data):
        # При частичном обновлении подставляем отсутствующие поля из instance
        if self.instance:
            for field in self.instance._meta.fields:
                name = field.name
                if name not in data:
                    data[name] = getattr(self.instance, name)

        data.pop('user', None)
        user = self.context['request'].user
        booking = Booking(user=user, **data)
        if self.instance:
            booking.pk = self.instance.pk

        booking.clean()
        return data


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
