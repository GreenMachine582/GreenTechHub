
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.html import escape
from django.views.generic import ListView, FormView

from .models import MapifyMarkerIcon, MapifyMarker, MapifyPlace
from .forms import MapifyMarkerIconForm, MapifyMarkerForm, MapifyPlaceForm

# Create your views here.

class MapifyMarkerIconListView(ListView):
    model = MapifyMarkerIcon
    template_name = "marker_icon_list.html"
    context_object_name = "records"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Session has expired.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return MapifyMarkerIcon.objects.all()


class MapifyMarkerIconFormView(FormView):
    form_class = MapifyMarkerIconForm
    template_name = "marker_icon_form.html"
    success_url = reverse_lazy("mapify-marker-icon-list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Session has expired.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        record_id = self.kwargs.get("record_id")
        if record_id:
            kwargs["instance"] = get_object_or_404(MapifyMarkerIcon, id=record_id)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["record"] = self.get_form_kwargs().get("instance")
        return context

    def form_valid(self, form):
        message = f"Icon {'updated' if form.instance.pk else 'added'} successfully."
        form.save()
        messages.success(self.request, message)
        return super().form_valid(form)

    def form_invalid(self, form):
        error_message = "<p>Failed to save record. Please correct the errors below: </p><ul>"
        for field, errors in form.errors.items():
            for error in errors:
                # Label the error with the field name if available
                field_name = form.fields[field].label if field in form.fields else "Error"
                error_message += f"<li><strong>{escape(field_name)}:</strong> {escape(error)}</li>"
        error_message += "</ul>"
        form.errors.clear()
        messages.error(self.request, error_message)
        return super().form_invalid(form)


def mapify_marker_icon_delete(request, record_id):
    if not request.user.is_authenticated:
        messages.error(request, "Session has expired.")
        return redirect("home")

    record = get_object_or_404(MapifyMarkerIcon, id=record_id)
    record.delete()
    messages.success(request, "Icon deleted successfully.")
    return redirect("mapify-marker-icon-list")


class MapifyMarkerListView(ListView):
    model = MapifyMarker
    template_name = "marker_list.html"
    context_object_name = "records"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Session has expired.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return MapifyMarker.objects.all()


class MapifyMarkerFormView(FormView):
    form_class = MapifyMarkerForm
    template_name = "marker_form.html"
    success_url = reverse_lazy("mapify-marker-list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Session has expired.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        record_id = self.kwargs.get("record_id")
        if record_id:
            kwargs["instance"] = get_object_or_404(MapifyMarker, id=record_id)
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["record"] = self.get_form_kwargs().get("instance")
        context["icons"] = MapifyMarkerIcon.objects.all()
        return context

    def form_valid(self, form):
        message = f"Marker {'updated' if form.instance.pk else 'added'} successfully."
        form.save()
        messages.success(self.request, message)
        return super().form_valid(form)

    def form_invalid(self, form):
        error_message = "<p>Failed to save record. Please correct the errors below: </p><ul>"
        for field, errors in form.errors.items():
            for error in errors:
                # Label the error with the field name if available
                field_name = form.fields[field].label if field in form.fields else "Error"
                error_message += f"<li><strong>{escape(field_name)}:</strong> {escape(error)}</li>"
        error_message += "</ul>"
        form.errors.clear()
        messages.error(self.request, error_message)
        return super().form_invalid(form)


def mapify_marker_delete(request, record_id):
    if not request.user.is_authenticated:
        messages.error(request, "Session has expired.")
        return redirect("home")

    record = get_object_or_404(MapifyMarker, id=record_id)
    record.delete()
    messages.success(request, "Marker deleted successfully.")
    return redirect("mapify-marker-list")


class MapifyPlaceListView(ListView):
    model = MapifyPlace
    template_name = "place_list.html"
    context_object_name = "records"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Session has expired.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return MapifyPlace.objects.all()


class MapifyPlaceFormView(FormView):
    form_class = MapifyPlaceForm
    template_name = "place_form.html"
    success_url = reverse_lazy("mapify-place-list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Session has expired.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        record_id = self.kwargs.get("record_id")
        if record_id:
            kwargs["instance"] = get_object_or_404(MapifyPlace, id=record_id)
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["record"] = self.get_form_kwargs().get("instance")
        context["markers"] = MapifyMarker.objects.all()
        return context

    def form_valid(self, form):
        message = f"Place {'updated' if form.instance.pk else 'added'} successfully."
        form.save()
        messages.success(self.request, message)
        return super().form_valid(form)

    def form_invalid(self, form):
        error_message = "<p>Failed to save record. Please correct the errors below: </p><ul>"
        for field, errors in form.errors.items():
            for error in errors:
                # Label the error with the field name if available
                field_name = form.fields[field].label if field in form.fields else "Error"
                error_message += f"<li><strong>{escape(field_name)}:</strong> {escape(error)}</li>"
        error_message += "</ul>"
        form.errors.clear()
        messages.error(self.request, error_message)
        return super().form_invalid(form)


def mapify_place_delete(request, record_id):
    if not request.user.is_authenticated:
        messages.error(request, "Session has expired.")
        return redirect("home")

    record = get_object_or_404(MapifyPlace, id=record_id)
    record.delete()
    messages.success(request, "Place deleted successfully.")
    return redirect("mapify-place-list")
