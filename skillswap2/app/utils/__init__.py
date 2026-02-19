__all__ = [
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "authenticate_user",
    "get_current_user",
    "oauth2_scheme",
    "is_email_enabled",
    "send_email",
]


def __getattr__(name):
    if name in {
        "verify_password",
        "get_password_hash",
        "create_access_token",
        "authenticate_user",
        "get_current_user",
        "oauth2_scheme",
    }:
        from . import security as _security
        return getattr(_security, name)
    if name in {"is_email_enabled", "send_email"}:
        from . import email as _email
        return getattr(_email, name)
    raise AttributeError(f"module 'app.utils' has no attribute '{name}'")
