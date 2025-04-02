from django.urls import path, include
from .views import (
    register_user,
    login_user,
    logout_user,
    google_login,
    password_register,
    UserUpdateView,
    ProductViewSet,
    CategoryViewSet,
    BrandViewSet,
    OrderViewSet,
    CommentViewSet,
    UserProfileImageView,
    ProductImageViewSet
)
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r"products", ProductViewSet)
router.register(r"categories", CategoryViewSet)
router.register(r"brands", BrandViewSet)
router.register(r"orders", OrderViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'products/images', ProductImageViewSet, basename='product-image')

urlpatterns = [
    path("register/", register_user, name="register_user"),
    path("google-login/", google_login, name="get_user_inf_google_auth" ), 
    path("login/", login_user, name="login_user"),
    path("logout/", logout_user, name="logout_user"),
    path("password-register/", password_register, name="password_register"),
    path("user-update/", UserUpdateView.as_view(), name="user_update"),
    path('upload-profile-image/', UserProfileImageView.as_view(), name='upload-profile-image'),
    path("", include(router.urls)),
]