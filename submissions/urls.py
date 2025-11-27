from django.urls import path
from . import views

urlpatterns = [
    path("new/", views.new_submission, name="new_submission"),
    path("<int:submission_id>/edit/", views.edit_submission, name="edit_submission"),
    path("upload/<int:upload_id>/replace/", views.replace_upload_inline, name="replace_upload_inline"),

    # 대주 리뷰
    path("submission/<int:submission_id>/review/", views.submission_review, name="submission_review"),
]
