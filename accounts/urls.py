from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, RefreshTokenView,
    MeView, ChangePasswordView, LibrarianListView, LibrarianDetailView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', RefreshTokenView.as_view(), name='token-refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('librarians/', LibrarianListView.as_view(), name='librarian-list'),
    path('librarians/<int:pk>/', LibrarianDetailView.as_view(), name='librarian-detail'),
]
