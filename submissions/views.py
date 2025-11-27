from decimal import Decimal, InvalidOperation
import re

import openpyxl
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from users.models import User
from .forms import (
    SubmissionForm,
    MultiUploadForm,
    SubmissionEventForm,
    SubmissionDynamicFieldsForm,
)
from .models import Submission, Upload, SubmissionEvent, SubmissionField


def _is_lender_like(user: User) -> bool:
    """
    대주 권한으로 인정할 기준:
    - role == LENDER 이거나
    - is_staff / is_superuser 인 관리자
    """
    return getattr(user, "is_lender", False) or user.is_staff or user.is_superuser


# -------------------------------
# 파일 파싱 → SubmissionField 생성 관련 헬퍼
# -------------------------------

def _auto_name_from_label(label: str) -> str:
    """
    라벨에서 자동으로 name을 만들어내는 간단한 함수.
    - 한글/영문/숫자 외 문자는 제거 또는 언더스코어 대체
    - 공백은 언더스코어로
    """
    s = str(label).strip()
    # 공백을 언더스코어로
    s = re.sub(r"\s+", "_", s)
    # 너무 지저분하면 그냥 field_... 형태로 가도 됨
    return s


def extract_fields_from_upload(upload: Upload):
    """
    업로드된 엑셀 파일을 읽어서
    SubmissionField로 쓸 원시 데이터 리스트를 반환한다.

    현재 가정하는 엑셀 구조 (예시):

        A열: 라벨 (예: "당기순이익", "자산총계")
        B열: 값   (예: 999, 88888)

    이 함수는 엑셀에 몇 행이 있든,
    라벨/값이 차있는 만큼 모두 자동으로 필드를 생성한다.

    반환 형식:

        [
            {
                "name": "당기순이익",   # 라벨 기반 자동 생성
                "label": "당기순이익",
                "value": "999",
                "data_type": SubmissionField.DataType.NUMBER,
                "order": 1,
            },
            ...
        ]
    """
    file_path = upload.file.path  # 실제 서버 상의 파일 경로

    wb = openpyxl.load_workbook(file_path, data_only=True)
    print(wb.sheetnames[0])
    ws = wb[wb.sheetnames[0]]

    fields = []
    order = 1

    for row in ws.iter_rows(
        min_row=1,
        max_row=ws.max_row,
        min_col=1,
        max_col=2,
        values_only=True,
    ):
        label_cell, value_cell = row

        if label_cell is None or value_cell is None:
            continue

        label_str = str(label_cell).strip()
        value_str = str(value_cell).strip()

        # name 자동 생성 (label 기반)
        name = _auto_name_from_label(label_str)

        # 숫자인지 간단 판별
        data_type = SubmissionField.DataType.TEXT
        try:
            Decimal(value_str.replace(",", ""))
            data_type = SubmissionField.DataType.NUMBER
        except InvalidOperation:
            pass

        fields.append(
            {
                "name": name,
                "label": label_str,
                "value": value_str,
                "data_type": data_type,
                "order": order,
            }
        )
        order += 1

    return fields


def create_fields_from_upload(submission: Submission, upload: Upload):
    """
    특정 업로드 파일을 기준으로 SubmissionField들을 생성/갱신
    - 기존 필드는 싹 지우고 새로 만든다
    """
    SubmissionField.objects.filter(submission=submission).delete()

    raw_fields = extract_fields_from_upload(upload)
    for idx, f in enumerate(raw_fields, start=1):
        SubmissionField.objects.create(
            submission=submission,
            name=f.get("name") or f"field_{idx}",
            label=f.get("label") or f"Field {idx}",
            value=f.get("value") or "",
            data_type=f.get("data_type") or SubmissionField.DataType.TEXT,
            order=f.get("order") or idx,
        )


# -------------------------------
# 뷰들
# -------------------------------

@login_required
def new_submission(request):
    """
    새 심의 신청 작성 (1단계)
    - 제목/설명 + 파일 업로드
    - 여기서는 무조건 DRAFT로 생성
    - 파일을 기반으로 SubmissionField 생성
    - 이후 edit_submission으로 리다이렉트하여 가변 필드/제출 처리
    """
    user = request.user
    if not getattr(user, "is_borrower", False):
        return HttpResponseForbidden("차주만 새로운 심의 신청을 만들 수 있습니다.")

    if request.method == "POST":
        sub_form = SubmissionForm(request.POST)
        upload_form = MultiUploadForm(request.POST, request.FILES)
        if sub_form.is_valid() and upload_form.is_valid():
            submission = sub_form.save(commit=False)
            submission.borrower = user
            submission.status = Submission.Status.DRAFT
            submission.save()

            # 상태변경 이벤트 기록
            SubmissionEvent.objects.create(
                submission=submission,
                actor=user,
                event_type=SubmissionEvent.EventType.STATUS_CHANGE,
                from_status=None,
                to_status=submission.status,
                field_name="general",
                message="초기 생성 및 저장",
            )

            # 파일 업로드
            uploads = []
            for i in range(1, 3):
                f = upload_form.cleaned_data.get(f"file_{i}")
                if f:
                    uploads.append(
                        Upload.objects.create(
                            submission=submission,
                            file=f,
                            original_name=f.name,
                        )
                    )

            # 파싱 기준이 될 파일 선택: 우선 file_1, 없으면 첫 업로드
            target_upload = uploads[0] if uploads else None

            if target_upload:
                create_fields_from_upload(submission, target_upload)

            return redirect("edit_submission", submission_id=submission.id)
    else:
        sub_form = SubmissionForm()
        upload_form = MultiUploadForm()

    return render(
        request,
        "submissions/new_submission.html",
        {
            "sub_form": sub_form,
            "upload_form": upload_form,
            "mode": "create",
        },
    )


@login_required
def edit_submission(request, submission_id: int):
    """
    차주가 기존 심의 신청을 수정하는 화면
    - 제목/설명 + 가변 필드들 + 파일목록/교체 + 타임라인
    - 임시저장: DRAFT
    - 검토 요청(제출): IN_REVIEW
    - 최종확정된 신청서는 수정 불가
    """
    user = request.user
    submission = get_object_or_404(Submission, id=submission_id)

    if submission.borrower != user:
        return HttpResponseForbidden("자신의 신청서만 수정할 수 있습니다.")

    fields_qs = submission.fields.all()

    if submission.status == Submission.Status.FINALIZED:
        if request.method == "POST":
            return HttpResponseForbidden("최종확정된 신청서는 더 이상 수정할 수 없습니다.")

    if request.method == "POST":
        sub_form = SubmissionForm(request.POST, instance=submission)
        upload_form = MultiUploadForm(request.POST, request.FILES)
        dynamic_form = SubmissionDynamicFieldsForm(request.POST, fields_qs=fields_qs)

        if sub_form.is_valid() and upload_form.is_valid() and dynamic_form.is_valid():
            old_status = submission.status
            submission = sub_form.save(commit=False)

            action = request.POST.get("action")
            if action == "submit":
                submission.status = Submission.Status.IN_REVIEW
            elif action == "draft":
                submission.status = Submission.Status.DRAFT

            submission.save()

            # 상태 변경 로그 남기기
            if old_status != submission.status:
                SubmissionEvent.objects.create(
                    submission=submission,
                    actor=user,
                    event_type=SubmissionEvent.EventType.STATUS_CHANGE,
                    from_status=old_status,
                    to_status=submission.status,
                    field_name="general",
                    message="차주가 신청서를 수정/제출했습니다.",
                )

            # 가변 필드 값 저장
            for field in fields_qs:
                form_field_name = SubmissionDynamicFieldsForm._field_name(field)
                value = dynamic_form.cleaned_data.get(form_field_name)
                field.value = "" if value is None else str(value)
                field.save()

            # 새로 업로드된 파일 추가
            for i in range(1, 3):
                f = upload_form.cleaned_data.get(f"file_{i}")
                if f:
                    Upload.objects.create(
                        submission=submission,
                        file=f,
                        original_name=f.name,
                    )

            return redirect("borrower_dashboard")
    else:
        sub_form = SubmissionForm(instance=submission)
        upload_form = MultiUploadForm()
        dynamic_form = SubmissionDynamicFieldsForm(fields_qs=fields_qs)

    events = submission.events.select_related("actor").all()

    return render(
        request,
        "submissions/edit_submission.html",
        {
            "submission": submission,
            "sub_form": sub_form,
            "upload_form": upload_form,
            "dynamic_form": dynamic_form,
            "mode": "edit",
            "events": events,
        },
    )


@login_required
def replace_upload_inline(request, upload_id: int):
    """
    차주가 기존 파일을 교체
    """
    upload = get_object_or_404(Upload, id=upload_id)
    user = request.user

    if upload.submission.borrower != user:
        return HttpResponseForbidden("자신의 파일만 교체할 수 있습니다.")

    if upload.submission.status == Submission.Status.FINALIZED:
        return HttpResponseForbidden("최종확정된 신청서의 파일은 교체할 수 없습니다.")

    if request.method == "POST" and request.FILES.get("file"):
        new_file = request.FILES["file"]
        upload.file = new_file
        upload.original_name = new_file.name
        upload.save()

        SubmissionEvent.objects.create(
            submission=upload.submission,
            actor=user,
            event_type=SubmissionEvent.EventType.COMMENT,
            field_name="general",
            message=f"파일 '{upload.original_name}' 을 교체했습니다.",
        )

    return HttpResponseRedirect(reverse("borrower_dashboard"))


@login_required
def submission_review(request, submission_id: int):
    """
    대주가 신청서 상세를 보고
    - 코멘트/수정요청 남기기 (드롭다운 없이 코멘트만 입력)
    - 상태를 최종확정(FINALIZED)으로 변경
    - '수정요청' 버튼을 누르면 상태를 REVISION_REQUIRED로 변경
    """
    user = request.user
    if not _is_lender_like(user):
        return HttpResponseForbidden("대주만 접근할 수 있습니다.")

    submission = get_object_or_404(Submission, id=submission_id)

    if request.method == "POST":
        action = request.POST.get("action")

        # 1) 코멘트/수정요청 추가
        if action in ("comment", "request_revision"):
            form = SubmissionEventForm(request.POST)
            if form.is_valid():
                ev = form.save(commit=False)
                ev.submission = submission
                ev.actor = user
                ev.field_name = "general"

                if action == "request_revision":
                    # 수정요청이면 상태도 같이 변경
                    old_status = submission.status
                    submission.status = Submission.Status.REVISION_REQUIRED
                    submission.save()

                    ev.event_type = SubmissionEvent.EventType.REQUEST
                    ev.from_status = old_status
                    ev.to_status = submission.status
                else:
                    ev.event_type = SubmissionEvent.EventType.COMMENT

                ev.save()
                return redirect("submission_review", submission_id=submission.id)

        # 2) 최종확정
        elif action == "finalize":
            old_status = submission.status
            submission.status = Submission.Status.FINALIZED
            submission.save()

            SubmissionEvent.objects.create(
                submission=submission,
                actor=user,
                event_type=SubmissionEvent.EventType.STATUS_CHANGE,
                from_status=old_status,
                to_status=submission.status,
                field_name="general",
                message="대주가 최종확정했습니다.",
            )
            return redirect("submission_review", submission_id=submission.id)

    events = submission.events.select_related("actor").all()
    fields_qs = submission.fields.all()

    return render(
        request,
        "submissions/submission_review.html",
        {
            "submission": submission,
            "events": events,
            "event_form": SubmissionEventForm(),
            "fields": fields_qs,
        },
    )
