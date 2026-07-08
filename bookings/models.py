from django.db import models
from accounts.models import CustomUser
from books.models import Book


class Booking(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
        RETURNED = 'returned', 'Returned'

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.user.email} - {self.book.title} ({self.status})'
