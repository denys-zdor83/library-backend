from rest_framework.permissions import BasePermission
from .models import Role


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == Role.ADMIN)


class IsAdminOrLibrarian(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and request.user.role in (Role.ADMIN, Role.LIBRARIAN)
        )


class IsLibrarian(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == Role.LIBRARIAN)
