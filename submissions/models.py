import uuid
import os

from django.conf import settings
from django.db import models


def submission_upload_path(instance, filename: str) -> str:
    """
    업로드 파일 실제 저장 경로
    예: submissions/<user_id>/<submission_uuid>/<원래파일이름>
    """
    submission = instance.submission
    return f"submissions/{submission.borrower_id}/{submission.uuid}/{filename}"


class Submission(models.Model):
    """
    차주의 '심의 신청' 단위
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "임시저장"
        IN_REVIEW = "IN_REVIEW", "검토 중"
        REVISION_REQUIRED = "REVISION_REQUIRED", "수정요청"
        FINALIZED = "FINALIZED", "최종확정"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
        help_text="신청을 올린 차주",
    )

    title = models.CharField(
        max_length=255,
        help_text="신청 제목 (예: 2024년 3분기 심의신청)",
    )

    description = models.TextField(
        blank=True,
        help_text="간단한 메모/설명",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.borrower.username})"


class Upload(models.Model):
    """
    Submission에 속한 업로드 파일 한 개
    """

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="uploads",
    )

    file = models.FileField(
        upload_to=submission_upload_path,
    )

    original_name = models.CharField(
        max_length=255,
        help_text="업로드 당시 파일 이름",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.original_name and self.file:
            self.original_name = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.original_name


class SubmissionField(models.Model):
    """
    파일에서 추출된 '필드'들
    - 예: 당기순이익, 매출액, 자산총계 등
    - 화면에 가변 텍스트박스로 렌더링되는 대상
    """

    class DataType(models.TextChoices):
        TEXT = "TEXT", "텍스트"
        NUMBER = "NUMBER", "숫자"

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="fields",
    )

    # 내부 키 (자동 생성해도 됨)
    name = models.CharField(
        max_length=100,
        help_text="내부용 필드 이름 (예: net_income)",
    )

    # 화면에 보여줄 라벨 (엑셀 A열 그대로)
    label = models.CharField(
        max_length=200,
        help_text="화면에 표시할 라벨 (예: 당기순이익(원))",
    )

    # 문자열 형태 값
    value = models.TextField(
        blank=True,
        help_text="파일에서 읽어온 값(문자열 형태)",
    )

    data_type = models.CharField(
        max_length=20,
        choices=DataType.choices,
        default=DataType.TEXT,
    )

    order = models.IntegerField(
        default=0,
        help_text="화면에 표시될 순서",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.label} = {self.value}"


class SubmissionEvent(models.Model):
    """
    하나의 제출물에 대한 모든 기록(타임라인)
    - 대주의 수정요청(=피드백)
    - 일반 코멘트
    - 상태 변경 로그 등
    """

    class EventType(models.TextChoices):
        COMMENT = "COMMENT", "일반코멘트"
        REQUEST = "REQUEST", "수정요청"
        STATUS_CHANGE = "STATUS_CHANGE", "상태변경"

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="events",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submission_events",
    )

    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
    )

    # 이제 UI에서 선택 안 쓰지만, 구조상 남겨둠 (항상 'general' 등으로만 사용 가능)
    field_name = models.CharField(
        max_length=50,
        default="general",
        help_text="예: net_income, general 등 (지금은 일반용으로만 사용)",
    )

    message = models.TextField(
        blank=True,
        help_text="수정요청/코멘트/상태변경에 대한 설명",
    )

    from_status = models.CharField(
        max_length=30,
        choices=Submission.Status.choices,
        null=True,
        blank=True,
    )
    to_status = models.CharField(
        max_length=30,
        choices=Submission.Status.choices,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.submission.title} - {self.get_event_type_display()} ({self.created_at})"
