from django.db import models

class Trip(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    driver_name = models.CharField(max_length=128, blank=True)
    current_location = models.CharField(max_length=256)
    pickup_location = models.CharField(max_length=256)
    dropoff_location = models.CharField(max_length=256)
    current_cycle_used_hours = models.FloatField(default=0.0)
    plan_result = models.JSONField(null=True, blank=True)  # store route+logs
    def __str__(self):
        return f"Trip {self.id} - {self.driver_name or 'anonymous'}"
