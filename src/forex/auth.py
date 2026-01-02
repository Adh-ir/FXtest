import datetime

import extra_streamlit_components as stx
import streamlit as st

try:
    from forex.config import CACHE_CONFIG

    EXPIRY_DAYS = CACHE_CONFIG.COOKIE_EXPIRY_DAYS
except ImportError:
    EXPIRY_DAYS = 7  # Fallback

# Cookie Manager Key
COOKIE_NAME = "twelve_data_api_key"


def get_cookie_manager() -> stx.CookieManager:
    """
    Returns a CookieManager instance with a unique key to avoid widget conflicts.
    """
    return stx.CookieManager(key="fx_cookie_manager")


def get_api_key(cookie_manager: stx.CookieManager) -> str | None:
    """
    Retrieve API key from Session State or Cookie.
    Returns None if user has logged out or no valid key exists.
    """
    # Check if user has explicitly logged out (force show modal)
    if st.session_state.get("force_logout", False):
        return None

    # 1. Check Session State first (fastest)
    if "api_key" in st.session_state and st.session_state["api_key"]:
        return st.session_state["api_key"]

    # 2. Check Cookie (may be async-loaded)
    try:
        cookie_val = cookie_manager.get(COOKIE_NAME)
        # Ensure we have a valid, non-empty string
        if cookie_val and isinstance(cookie_val, str) and cookie_val.strip():
            st.session_state["api_key"] = cookie_val.strip()
            return cookie_val.strip()
    except Exception:
        pass  # Cookie manager may not be ready yet

    return None


def set_api_key(cookie_manager: stx.CookieManager, key: str) -> None:
    """
    Save API key to Session State and Cookie.
    Also clears any force_logout flag.
    """
    # Clear logout flag if it was set
    if "force_logout" in st.session_state:
        del st.session_state["force_logout"]

    # Save to session
    st.session_state["api_key"] = key.strip()

    # Save to cookie
    expires = datetime.datetime.now() + datetime.timedelta(days=EXPIRY_DAYS)
    try:
        cookie_manager.set(COOKIE_NAME, key.strip(), expires_at=expires)
    except Exception:
        pass  # Cookie save may fail but session state is primary


def clear_api_key(cookie_manager: stx.CookieManager) -> None:
    """
    Remove API key from everything and set force_logout flag.
    The force_logout flag ensures the modal shows even if cookies are stale.
    """
    # Set force logout flag FIRST (most important)
    st.session_state["force_logout"] = True

    # Clear session state
    if "api_key" in st.session_state:
        del st.session_state["api_key"]

    # Try to delete cookie (may or may not work)
    try:
        cookie_manager.delete(COOKIE_NAME)
    except Exception:
        pass  # Cookie doesn't exist or manager not ready
