from django.urls import path
from .views import (
    GenreListView, BookListView, BookDetailView,
    BookRatingView, NewestBooksView, PopularBooksView,
)

urlpatterns = [
    path('genres/', GenreListView.as_view(), name='genre-list'),
    path('', BookListView.as_view(), name='book-list'),
    path('<int:pk>/', BookDetailView.as_view(), name='book-detail'),
    path('<int:pk>/rate/', BookRatingView.as_view(), name='book-rate'),
    path('newest/', NewestBooksView.as_view(), name='books-newest'),
    path('popular/', PopularBooksView.as_view(), name='books-popular'),
]
