# policy_engine.py

POLICIES = {

    "student": [
        "/student_login",
        "/student_dashboard",
        "/student_profile",
        "/request_change",
        "/mfa",
        "/logout"
    ],

    "parent": [
        "/parent_login",
        "/parent_dashboard",
        "/parent_profile",
        "/mfa",
        "/logout"
    ],

    "faculty": [
        "/faculty_login",
        "/faculty_dashboard",
        "/marks_entry",
        "/attendance_entry",
        "/announcements",
        "/mfa",
        "/logout"
    ],

    "admin": [
        "/admin_login",
        "/admin_dashboard",
        "/manage_students",
        "/manage_faculty",
        "/reports",
        "/logs",
        "/mfa",
        "/logout"
    ]
}

def allowed(role, path):
    """
    Enforce RBAC strictly based on URL prefix
    """
    if not role or not path:
        return False

    allowed_prefixes = ROLE_POLICIES.get(role, [])

    for prefix in allowed_prefixes:
        if path.startswith(prefix):
            return True

    return False
