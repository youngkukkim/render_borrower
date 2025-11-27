from django.contrib import admin
from .models import Submission, Upload, SubmissionEvent, SubmissionField


class UploadInline(admin.TabularInline):
    model = Upload
    extra = 0
    readonly_fields = ("original_name", "uploaded_at")


class SubmissionEventInline(admin.TabularInline):
    model = SubmissionEvent
    extra = 0
    readonly_fields = (
        "actor",
        "event_type",
        "field_name",
        "message",
        "from_status",
        "to_status",
        "created_at",
    )


class SubmissionFieldInline(admin.TabularInline):
    model = SubmissionField
    extra = 0
    readonly_fields = ("name", "label", "value", "data_type", "order", "created_at")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "borrower", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "borrower__username", "borrower__email")
    date_hierarchy = "created_at"
    inlines = [UploadInline, SubmissionFieldInline, SubmissionEventInline]


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "original_name", "uploaded_at")
    search_fields = (
        "original_name",
        "submission__title",
        "submission__borrower__username",
    )
    date_hierarchy = "uploaded_at"


@admin.register(SubmissionEvent)
class SubmissionEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "submission",
        "event_type",
        "actor",
        "field_name",
        "from_status",
        "to_status",
        "created_at",
    )
    list_filter = ("event_type", "from_status", "to_status", "created_at")
    search_fields = ("submission__title", "actor__username", "message")
    date_hierarchy = "created_at"


@admin.register(SubmissionField)
class SubmissionFieldAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "name", "label", "data_type", "value", "order")
    list_filter = ("data_type",)
    search_fields = ("name", "label", "submission__title")
