SUPER_ADMIN_GROUP = "super_admin"
ADMIN_GROUP = "admin"
USER_GROUP = "user"
TEACHER_GROUP = "teacher"

USER_GROUP_META = {
    SUPER_ADMIN_GROUP: {
        "title": "超级管理员",
        "color": "#F56C6C",
        "tag_type": "danger",
        "is_admin": True,
        "can_grant_admin": True,
    },
    ADMIN_GROUP: {
        "title": "管理员",
        "color": "#409EFF",
        "tag_type": "primary",
        "is_admin": True,
        "can_grant_admin": False,
    },
    USER_GROUP: {
        "title": "用户",
        "color": "#67C23A",
        "tag_type": "success",
        "is_admin": False,
        "can_grant_admin": False,
    },
    TEACHER_GROUP: {
        "title": "老师",
        "color": "#9B59B6",
        "tag_type": "info",
        "is_admin": False,
        "can_grant_admin": False,
    },
}


def normalize_user_group(value: str | None) -> str:
    if not value:
        return USER_GROUP
    group = str(value).strip().lower()
    return group if group in USER_GROUP_META else USER_GROUP


def resolve_user_group(user_group: str | None, is_admin: int | bool) -> str:
    normalized = normalize_user_group(user_group)
    if user_group:
        return normalized
    return ADMIN_GROUP if bool(is_admin) else USER_GROUP


def is_admin_group(user_group: str | None) -> bool:
    group = normalize_user_group(user_group)
    return bool(USER_GROUP_META[group]["is_admin"])


def can_grant_admin(user_group: str | None) -> bool:
    group = normalize_user_group(user_group)
    return bool(USER_GROUP_META[group]["can_grant_admin"])


def get_user_group_meta(user_group: str | None) -> dict:
    group = normalize_user_group(user_group)
    meta = USER_GROUP_META[group]
    return {
        "key": group,
        "title": meta["title"],
        "color": meta["color"],
        "tag_type": meta["tag_type"],
        "is_admin": bool(meta["is_admin"]),
        "can_grant_admin": bool(meta["can_grant_admin"]),
    }
