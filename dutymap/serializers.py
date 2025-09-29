from rest_framework import serializers
from .models import Trip

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'

class PlanTripInputSerializer(serializers.Serializer):
    current_location = serializers.CharField()
    pickup_location = serializers.CharField()
    dropoff_location = serializers.CharField()
    current_cycle_used_hours = serializers.FloatField()
