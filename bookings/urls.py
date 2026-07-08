from django.urls import path
from .views import (
    UserBookingListView, UserBookingCancelView,
    AllBookingsView, BookingUsersView,
    BookingApproveView, BookingRejectView,
)

urlpatterns = [
    path('', UserBookingListView.as_view(), name='booking-list'),
    path('<int:pk>/cancel/', UserBookingCancelView.as_view(), name='booking-cancel'),
    path('all/', AllBookingsView.as_view(), name='booking-all'),
    path('users/', BookingUsersView.as_view(), name='booking-users'),
    path('<int:pk>/approve/', BookingApproveView.as_view(), name='booking-approve'),
    path('<int:pk>/reject/', BookingRejectView.as_view(), name='booking-reject'),
]
