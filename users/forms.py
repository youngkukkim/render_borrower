from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class SignUpForm(UserCreationForm):
    """
    회원가입 폼
    - username, email, role(차주/대주), password1, password2
    - ADMIN 역할은 여기서 선택 불가 (관리자 페이지에서만 세팅)
    """

    email = forms.EmailField(required=True, label="이메일")

    role = forms.ChoiceField(
        label="역할",
        widget=forms.RadioSelect,
        choices=(
            (User.Role.BORROWER, "차주"),
            (User.Role.LENDER, "대주"),
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "role")

    def clean_role(self):
        """
        혹시라도 폼 조작으로 ADMIN을 보내도 막아둠.
        """
        role = self.cleaned_data["role"]
        if role not in [User.Role.BORROWER, User.Role.LENDER]:
            raise forms.ValidationError("허용되지 않은 역할입니다.")
        return role
