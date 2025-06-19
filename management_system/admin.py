from django.contrib import admin
from .models import Appointments, Notification


@admin.register(Appointments)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'patient_first_name', 'patient_last_name', 'patient_purpose', 
                    'doctor_selected', 'appointment_creation_date', 'appointment_scheduled_date',
                    'diagnosis', 'doctor_notes', 'prescription', 'doctor_notes', 'status')

@admin.register(Notification)   
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user')
