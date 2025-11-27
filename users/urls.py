# from django.urls import path
# from django.contrib.auth import views as auth_views

# from . import views

# urlpatterns = [
#     path("", views.home, name="home"),

#     path("signup/", views.signup, name="signup"),

#     path(
#         "login/",
#         auth_views.LoginView.as_view(
#             template_name="users/login.html"
#         ),
#         name="login",
#     ),

#     path(
#         "logout/",
#         auth_views.LogoutView.as_view(
#             next_page="home",
#         ),
#         name="logout",
#     ),

#     path("post-login/", views.post_login_redirect, name="post_login_redirect"),

#     path(
#         "borrower/dashboard/",
#         views.borrower_dashboard,
#         name="borrower_dashboard",
#     ),

#     path(
#         "lender/dashboard/",
#         views.lender_dashboard,
#         name="lender_dashboard",
#     ),
# ]


from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="users/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),

    path("post-login/", views.post_login_redirect, name="post_login_redirect"),

    # 차주 대시보드
    path("borrower/dashboard/", views.borrower_dashboard, name="borrower_dashboard"),

    # 대주 대시보드 + 차주 선택/상세
    path("lender/dashboard/", views.lender_dashboard, name="lender_dashboard"),
    path("lender/borrowers/<int:borrower_id>/", views.lender_borrower_detail, name="lender_borrower_detail"),
]
