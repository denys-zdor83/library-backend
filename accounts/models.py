from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    USER = 'user', 'User'
    LIBRARIAN = 'librarian', 'Librarian'
    ADMIN = 'admin', 'Administrator'


class LibrarianPermission(models.TextChoices):
    ADD_BOOKS = 'add_books', 'Add Books'
    EDIT_BOOKS = 'edit_books', 'Edit Books'
    DELETE_BOOKS = 'delete_books', 'Delete Books'
    VIEW_BOOKINGS = 'view_bookings', 'View Bookings'


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def is_admin(self):
        return self.role == Role.ADMIN

    def is_librarian(self):
        return self.role == Role.LIBRARIAN

    def is_regular_user(self):
        return self.role == Role.USER


class LibrarianProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='librarian_profile',
    )
    permissions = models.JSONField(default=list)

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions

    def __str__(self):
        return f'LibrarianProfile({self.user.email})'


class FavoriteGenre(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='favorite_genres')
    genre = models.CharField(max_length=100)

    class Meta:
        unique_together = ('user', 'genre')

    def __str__(self):
        return f'{self.user.email} - {self.genre}'
