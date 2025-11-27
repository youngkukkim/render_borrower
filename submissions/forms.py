from django import forms
from .models import Submission, SubmissionEvent, SubmissionField


class SubmissionForm(forms.ModelForm):
    """
    Submission 입력/수정용 폼
    - 제목/설명만 관리
    """

    class Meta:
        model = Submission
        fields = ("title", "description")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "title": "신청 제목",
            "description": "설명/메모",
        }


class MultiUploadForm(forms.Form):
    """
    파일 업로드 슬롯 (2개)
    """

    file_1 = forms.FileField(
        label="파일 1",
        required=False,
        help_text="PDF / Excel(xlsx) / Word(docx) 등",
    )
    file_2 = forms.FileField(
        label="파일 2",
        required=False,
        help_text="PDF / Excel(xlsx) / Word(docx) 등",
    )


class SubmissionEventForm(forms.ModelForm):
    """
    대주가 남기는 피드백 폼
    - 드롭다운 없이, 순수 코멘트만 입력
    - event_type, field_name 은 뷰에서 결정
    """

    class Meta:
        model = SubmissionEvent
        fields = ("message",)
        labels = {
            "message": "피드백 내용",
        }
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3}),
        }


class SubmissionDynamicFieldsForm(forms.Form):
    """
    SubmissionField 들로부터 동적으로 생성되는 폼
    - 화면에 가변 텍스트박스들을 만들어줌
    """

    def __init__(self, *args, fields_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._field_objs = []

        if fields_qs is not None:
            for field in fields_qs.order_by("order", "id"):
                self._field_objs.append(field)
                field_name = self._field_name(field)

                if field.data_type == SubmissionField.DataType.NUMBER:
                    form_field = forms.DecimalField(
                        label=field.label,
                        required=False,
                    )
                else:
                    form_field = forms.CharField(
                        label=field.label,
                        required=False,
                    )

                self.fields[field_name] = form_field
                self.initial[field_name] = field.value

    @staticmethod
    def _field_name(field_obj: SubmissionField) -> str:
        return f"field_{field_obj.id}"
