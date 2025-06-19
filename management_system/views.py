from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import AppointmentForm
from .models import Appointments, Notification, CustomUser
from django.http import HttpResponseNotAllowed
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa


class RoleRequiredMixin:
    allowed_roles = []

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if hasattr(request.user, 'role') and request.user.role not in self.allowed_roles:
            return redirect('not_authorized')
        return super().dispatch(request, *args, **kwargs)

class HomeView(TemplateView):
    template_name = 'management_system/home.html'

class PatientView(RoleRequiredMixin, TemplateView):
    template_name = 'management_system/patient-dashboard.html'
    allowed_roles = ['patient']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AppointmentForm()
        context['appointments'] = Appointments.objects.filter(
            user=self.request.user,
            status__in=['accepted']
        ).order_by('-appointment_creation_date')[:3]
        return context

    def post(self, request, *args, **kwargs):
        form = AppointmentForm(request.POST)
        if form.is_valid():
            patient_purpose = form.cleaned_data['patient_purpose']
            doctor_selected = form.cleaned_data['doctor_selected']

            appointment = Appointments.objects.create(
                user=request.user,
                patient_first_name=request.user.first_name,
                patient_last_name=request.user.last_name,
                patient_purpose=patient_purpose,
                doctor_selected=doctor_selected
            )

            Notification.objects.create(
                user=doctor_selected,
                message="You have received a new appointment!",
                appointment=appointment
            )

            messages.success(request, "Appointment booked successfully.")
            return self.render_to_response(self.get_context_data(success=True))

        return self.render_to_response(self.get_context_data(form=form))


class MedicalHistoryView(RoleRequiredMixin, TemplateView):
    template_name = 'management_system/medical-history.html'
    allowed_roles = ['patient']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AppointmentForm()
        context['appointments'] = Appointments.objects.filter(
            user=self.request.user
        ).order_by('-appointment_creation_date')
        return context

class MedicalReportView(RoleRequiredMixin, TemplateView):
    template_name = 'management_system/medical-report.html'
    allowed_roles = ['patient']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AppointmentForm()
        context['appointments'] = Appointments.objects.filter(
            user=self.request.user,
            status__in=['completed']
        ).order_by('-appointment_creation_date')
        return context

class AiAssistantView(RoleRequiredMixin, TemplateView):
    template_name = 'management_system/AI-assistant.html'
    allowed_roles = ['patient']

class InsightsView(RoleRequiredMixin, TemplateView):
    template_name = 'management_system/insights.html'
    allowed_roles = ['patient']

class PatientNotificationsView(RoleRequiredMixin, TemplateView):
    template_name = 'management_system/patient-notifications.html'
    allowed_roles = ['patient']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notifications'] = Notification.objects.filter(
            user=self.request.user
        ).order_by('-date_created')
        return context

def download_report(request, appointment_id):
    appointment = get_object_or_404(Appointments, id=appointment_id)
    user = appointment.user

    template_path = 'management_system/report_template.html'
    context = {
        'appointment': appointment,
        'user': user,
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="medical_report_{appointment.id}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response



# Doctor's view

class DoctorAppointmentsView(RoleRequiredMixin, TemplateView):

    template_name = 'management_system/doctor-appointments.html'
    allowed_roles = ['doctor']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointments'] = Appointments.objects.filter(
            doctor_selected=self.request.user,
            status__in=['pending']
        ).order_by('-appointment_creation_date')[:10]
        context['accepted_appointments'] = Appointments.objects.filter(
            doctor_selected=self.request.user,
            status__in=['accepted']
        ).order_by('-appointment_scheduled_date')[:10]
        context['ended_appointments'] = Appointments.objects.filter(
            doctor_selected=self.request.user,
            status__in=['completed']
        ).order_by('-appointment_creation_date')[:10]
        return context

@login_required
def not_authorized(request):
    return render(request, 'management_system/not-authorized.html')

def handle_appointment(request, appointment_id, accepted_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    action = request.GET.get('action')
    appointment = get_object_or_404(Appointments, id=appointment_id)

    scheduled_date = request.POST.get('appointment_scheduled_date')

    message = None

    if action == 'accept':
        appointment.status = 'accepted'
        message = "The Doctor has accepted your appointment."

    elif action == 'reject':
        appointment.status = 'rejected'
        message = "The Doctor has rejected your appointment."

    elif action == 'complete':
        appointment.status = 'completed'
        message = "The Doctor has ended your appointment."

    elif action == 'setDate':
        if scheduled_date:
            appointment.appointment_scheduled_date = scheduled_date
            message = f"Your appointment has been scheduled for {scheduled_date}."

    if message:
        Notification.objects.create(
            user=appointment.user,
            message=message,
            appointment=appointment
        )

    appointment.save()
    return redirect('doctor-appointments')

class DoctorView(RoleRequiredMixin, TemplateView):
    template_name = 'management_system/doctor-dashboard.html'
    allowed_roles = ['doctor']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointments'] = Appointments.objects.filter(
            doctor_selected=self.request.user,
            status__in=['accepted']
        ).order_by('-appointment_creation_date')[:5]
        return context
    

    def post(self, request):
        appointment_id = request.POST.get('appointment_id')
        diagnosis = request.POST.get('diagnosis')
        prescription = request.POST.get('prescription')
        doctor_notes = request.POST.get('doctor_notes')
        doctor_result = request.POST.get('doctor_result')

        try:
            appointment = Appointments.objects.get(id=appointment_id, doctor_selected=request.user, status='accepted')
        except Appointments.DoesNotExist:
            messages.error(request, "Appointment not found or access denied.")
            return redirect(request.path)

        appointment.diagnosis = diagnosis
        appointment.prescription = prescription
        appointment.doctor_notes = doctor_notes
        appointment.doctor_result = doctor_result
        appointment.save()

        Notification.objects.create(
            user=appointment.user,
            message="The Doctor has given a diagnosis for your appointment.",
            appointment=appointment
            )

        messages.success(request, "Diagnosis successfully added.")
        return redirect('doctor-dashboard')
    
class DoctorNotificationsView(RoleRequiredMixin, TemplateView):
    template_name = 'management_system/doctor-notifications.html'
    allowed_roles = ['doctor']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notifications'] = Notification.objects.filter(
            user=self.request.user,
        ).order_by('-date_created')
        return context


def patient_delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    return redirect('patient-notifications')

def doctor_delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    return redirect('doctorsnotifications')

class DoctorInventoryView(RoleRequiredMixin, TemplateView):
    template_name = 'management_system/inventory-manager.html'
    allowed_roles = ['doctor']

class AnalyticsAndReportsView(RoleRequiredMixin, TemplateView):
    template_name = 'management_system/analytics-and-reports.html'
    allowed_roles = ['doctor']
    

class PatientRecordsView(RoleRequiredMixin, ListView):
    model = CustomUser
    template_name = 'management_system/patient-records.html'
    context_object_name = 'patients'
    allowed_roles = ['doctor']

    def get_queryset(self):
        return CustomUser.objects.filter(role='patient')

class PatientDetailView(RoleRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'management_system/view-patient-records.html'
    context_object_name = 'patient'
    allowed_roles = ['doctor']

    def get_queryset(self):
        return CustomUser.objects.filter(role='patient')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointments'] = self.object.patient.order_by('-appointment_creation_date')
        return context
