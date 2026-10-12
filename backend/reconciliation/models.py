from django.db import models

# Create your models here.

class Location(models.Model):
    location_id = models.CharField(max_length=50, primary_key=True)
    org_id = models.CharField(max_length=50)
    location_name = models.CharField(max_length=150)
    def __str__(self):
        return f"{self.location_name} ({self.location_id} -> {self.org_id})"

class SystemARecord(models.Model):
    record_id = models.CharField(max_length=50, primary_key=True)
    location_id = models.CharField(max_length=50)
    event_date = models.DateField(null=True, blank=True)
    raw_event_date = models.CharField(max_length=50, blank=True)
    category_code = models.CharField(max_length=50, blank=True)
    actor_id = models.CharField(max_length=50, null=True, blank=True)

    base_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    raw_base_value = models.CharField(max_length=50, blank=True)
    
    adjustment = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    raw_adjustment = models.CharField(max_length=50, blank=True)
    
    total_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    raw_total_value = models.CharField(max_length=50, blank=True)
    
    state = models.CharField(max_length=50, blank=True)
    def __str__(self):
        return f"SystemA: {self.record_id} (Total: {self.total_value})"

class SystemBEntry(models.Model):
    """
    One row per entry as recorded by System B.
    Multiple entries can reference the same System A record.
    Source: system_b.csv
    """
    entry_id = models.CharField(max_length=50, primary_key=True)
    
    # Both raw reference (e.g. ' REC - 1070 ') and normalized reference (e.g. 'REC-1070')
    record_ref_raw = models.CharField(max_length=100)
    record_ref_normalized = models.CharField(max_length=100, db_index=True)
    
    location_id = models.CharField(max_length=50)
    
    # Recorded date
    recorded_on = models.DateField(null=True, blank=True)
    raw_recorded_on = models.CharField(max_length=50, blank=True)
    
    # Value: parsed decimal alongside raw text
    value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    raw_value = models.CharField(max_length=50, blank=True)
    
    label = models.CharField(max_length=255, blank=True)
    def __str__(self):
        return f"SystemB: {self.entry_id} -> Ref: {self.record_ref_normalized} (Val: {self.value})"

