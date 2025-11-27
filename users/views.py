from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.db.models import Count

from .forms import SignUpForm
from .models import User
from submissions.models import Submission


def home(request):
    """
    메인 홈 화면.
    """
    return render(request, "users/home.html")


def signup(request):
    """
    회원가입 뷰.
    """
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("post_login_redirect")
    else:
        form = SignUpForm()

    return render(request, "users/signup.html", {"form": form})


def _is_lender_like(user: User) -> bool:
    """
    대주 권한으로 인정할 기준:
    - role == LENDER 이거나
    - is_staff / is_superuser 인 관리자
    """
    return getattr(user, "is_lender", False) or user.is_staff or user.is_superuser


def _is_borrower_like(user: User) -> bool:
    """
    차주 권한으로 인정할 기준:
    - role == BORROWER
    (관리자는 여기 안 들어감)
    """
    return getattr(user, "is_borrower", False)


@login_required
def post_login_redirect(request):
    """
    로그인 이후 역할에 따라 분기
    - superuser/staff: 관리자 페이지
    - 차주: 차주 대시보드
    - 대주: 대주 대시보드
    """
    user = request.user

    if user.is_superuser or user.is_staff:
        # 관리자 계정은 그냥 admin 으로
        return redirect("/admin/")

    if _is_borrower_like(user):
        return redirect("borrower_dashboard")

    if _is_lender_like(user):
        return redirect("lender_dashboard")

    return redirect("home")


@login_required
def borrower_dashboard(request):
    """
    차주 대시보드
    - 위: 새 신청 작성 카드
    - 아래: 본인이 작성한 Submission 카드 목록
    """
    user = request.user

    if not _is_borrower_like(user):
        return HttpResponseForbidden("차주만 접근할 수 있습니다.")

    submissions = (
        Submission.objects.filter(borrower=user)
        .prefetch_related("uploads")
        .order_by("-created_at")
    )

    return render(
        request,
        "users/borrower_dashboard.html",
        {
            "submissions": submissions,
        },
    )


@login_required
def lender_dashboard(request):
    """
    대주 대시보드
    - 차주 목록 + 각 차주의 신청서 개수 표시
    """
    user = request.user

    if not _is_lender_like(user):
        return HttpResponseForbidden("대주만 접근할 수 있습니다.")

    # 진짜 차주만 목록에 노출 (관리자 제외)
    borrowers = (
        User.objects.filter(
            role=User.Role.BORROWER,
            is_staff=False,
            is_superuser=False,
        )
        .annotate(submission_count=Count("submissions"))
        .order_by("username")
    )

    return render(
        request,
        "users/lender_dashboard.html",
        {
            "borrowers": borrowers,
        },
    )


@login_required
def lender_borrower_detail(request, borrower_id: int):
    """
    대주가 특정 차주를 선택했을 때,
    해당 차주의 Submission 목록을 보는 화면
    """
    user = request.user

    if not _is_lender_like(user):
        return HttpResponseForbidden("대주만 접근할 수 있습니다.")

    borrower = get_object_or_404(
        User,
        id=borrower_id,
        role=User.Role.BORROWER,
        is_staff=False,
        is_superuser=False,
    )

    submissions = (
        Submission.objects.filter(borrower=borrower)
        .order_by("-created_at")
    )

    return render(
        request,
        "users/lender_borrower_detail.html",
        {
            "borrower": borrower,
            "submissions": submissions,
        },
    )
