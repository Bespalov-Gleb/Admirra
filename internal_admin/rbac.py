"""RBAC внутренней админки (ТЗ v1.0)."""
from core import models

STAFF_ROLES = {
    models.UserRole.ADMIN,
    models.UserRole.SUPERADMIN,
    models.UserRole.STAFF_MANAGER,
    models.UserRole.SUPPORT,
    models.UserRole.SEO,
    models.UserRole.DEVELOPER,
}

SUPERADMIN_ROLES = {models.UserRole.ADMIN, models.UserRole.SUPERADMIN}

# Менеджер (внутренний): все клиенты, без закрепления
MANAGER_ROLES = SUPERADMIN_ROLES | {models.UserRole.STAFF_MANAGER, models.UserRole.SUPPORT}

SEO_ROLES = SUPERADMIN_ROLES | {models.UserRole.SEO}


def is_staff(user: models.User) -> bool:
    return user.role in STAFF_ROLES


def is_superadmin(user: models.User) -> bool:
    return user.role in SUPERADMIN_ROLES


def is_internal_manager(user: models.User) -> bool:
    return user.role in {models.UserRole.STAFF_MANAGER, models.UserRole.SUPPORT}


def can_access_manager(user: models.User) -> bool:
    return user.role in MANAGER_ROLES


def can_access_seo(user: models.User) -> bool:
    return user.role in SEO_ROLES


def can_impersonate(user: models.User) -> bool:
    return user.role in MANAGER_ROLES


def staff_role_label(role: models.UserRole) -> str:
    mapping = {
        models.UserRole.ADMIN: "Super Admin",
        models.UserRole.SUPERADMIN: "Super Admin",
        models.UserRole.STAFF_MANAGER: "Менеджер",
        models.UserRole.SUPPORT: "Менеджер",
        models.UserRole.SEO: "SEO",
        models.UserRole.DEVELOPER: "Разработчик",
    }
    return mapping.get(role, role.value)
