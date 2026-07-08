from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        RESERVED = 'reserved', 'Reserved'
        BORROWED = 'borrowed', 'Borrowed'

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    year = models.IntegerField()
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, related_name='books')
    cover = models.ImageField(upload_to='book_covers/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    total_copies = models.IntegerField(default=1)
    available_copies = models.IntegerField(default=1)
    borrow_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} by {self.author}'

    @property
    def average_rating(self):
        ratings = self.ratings.all()
        if not ratings.exists():
            return 0
        return round(sum(r.value for r in ratings) / ratings.count(), 1)


class BookRating(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='book_ratings')
    value = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('book', 'user')

    def __str__(self):
        return f'{self.user.email} rated {self.book.title}: {self.value}'
