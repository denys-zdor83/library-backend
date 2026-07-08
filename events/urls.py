from django.urls import path
from .views import EventListView, EventDetailView, UpcomingEventsView

urlpatterns = [
    path('', EventListView.as_view(), name='event-list'),
    path('<int:pk>/', EventDetailView.as_view(), name='event-detail'),
    path('upcoming/', UpcomingEventsView.as_view(), name='events-upcoming'),
]
