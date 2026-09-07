"""Google sign-in gate.

Nobody sees any data until they sign in with Google, and only the allow-listed
addresses get through. Everyone else is signed in but shown a refusal.

The allow-list ships in code so it is version-controlled and cannot be changed
from inside the running app. It can be overridden per-deployment with an
`ALLOWED_EMAILS` secret (comma-separated, or a TOML list).
"""
from __future__ import annotations

import streamlit as st

ALLOWED_EMAILS: frozenset[str] = frozenset(
    {
        "auditorneodrift@gmail.com",
        "neodriftoffice@gmail.com",
        "admin@neodrift.in",
    }
)


def allowed_emails() -> frozenset[str]:
    """The allow-list, with an optional secrets override."""
    try:
        raw = st.secrets.get("ALLOWED_EMAILS")
    except Exception:
        raw = None
    if not raw:
        return ALLOWED_EMAILS
    values = raw if isinstance(raw, (list, tuple)) else str(raw).split(",")
    cleaned = {str(v).strip().lower() for v in values if str(v).strip()}
    return frozenset(cleaned) or ALLOWED_EMAILS


def _auth_configured() -> bool:
    try:
        auth = st.secrets.get("auth")
    except Exception:
        return False
    return bool(auth) and bool(auth.get("google") or auth.get("client_id"))


def _provider() -> str | None:
    """`st.login("google")` for a named provider, `st.login()` for a bare one."""
    try:
        auth = st.secrets.get("auth") or {}
    except Exception:
        return None
    return "google" if auth.get("google") else None


def _setup_help() -> None:
    st.title("Sign-in is not configured yet")
    st.error(
        "This app requires Google sign-in, but no OAuth credentials are set.",
        icon=":material/lock:",
    )
    st.markdown(
        """
Add the following to **`.streamlit/secrets.toml`** locally, or to
**app settings → Secrets** on Streamlit Cloud:

```toml
[auth]
redirect_uri = "https://YOUR-APP.streamlit.app/oauth2callback"
cookie_secret = "a-long-random-string"

[auth.google]
client_id = "...apps.googleusercontent.com"
client_secret = "..."
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Create the credentials in the [Google Cloud console](https://console.cloud.google.com/apis/credentials)
as an **OAuth client ID → Web application**, and register the same
`redirect_uri` there as an authorised redirect URI.

See `.streamlit/secrets.toml.example` in the repository for the full walkthrough.
"""
    )
    st.stop()


def _sign_in_screen(provider: str | None) -> None:
    st.title("NEODRIFT Interns Audit")
    st.markdown(
        "This dashboard contains internal order, payment and intern data. "
        "Sign in with an authorised Google account to continue."
    )
    left, _ = st.columns([1, 2])
    with left:
        if st.button("Sign in with Google", type="primary",
                     width="stretch", icon=":material/login:"):
            st.login(provider) if provider else st.login()
    st.caption("Access is limited to three approved NEODRIFT accounts.")
    st.stop()


def _denied_screen(email: str) -> None:
    st.title("You do not have access")
    st.error(
        f"**{email}** is not on the access list for this dashboard.",
        icon=":material/block:",
    )
    st.markdown(
        "If you should have access, ask the NEODRIFT admin to add your address, "
        "then sign in again."
    )
    left, _ = st.columns([1, 2])
    with left:
        if st.button("Sign out", width="stretch", icon=":material/logout:"):
            st.logout()
    st.stop()


def require_login() -> str:
    """Block the app until an allow-listed Google account is signed in.

    Returns the signed-in email. Calls st.stop() in every other case, so
    nothing after it runs for an unauthorised visitor.
    """
    if not hasattr(st, "user") or not hasattr(st, "login"):
        st.error(
            "Google sign-in needs Streamlit 1.42 or newer. Run "
            "`pip install -r requirements.txt` to update.",
            icon=":material/error:",
        )
        st.stop()

    if not _auth_configured():
        _setup_help()

    provider = _provider()
    try:
        logged_in = bool(st.user.is_logged_in)
    except Exception:
        logged_in = False

    if not logged_in:
        _sign_in_screen(provider)

    email = str(getattr(st.user, "email", "") or "").strip().lower()
    if email not in allowed_emails():
        _denied_screen(email or "This account")
    return email


def sidebar_account() -> None:
    """Who is signed in, plus a sign-out button."""
    try:
        email = str(getattr(st.user, "email", "") or "")
        name = str(getattr(st.user, "name", "") or "")
    except Exception:
        return
    if not email:
        return
    st.caption(f"Signed in as **{name or email}**")
    if st.button("Sign out", width="stretch", icon=":material/logout:"):
        st.logout()
