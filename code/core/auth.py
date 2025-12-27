import streamlit as st
import extra_streamlit_components as stx
import datetime

# Cookie Manager Key
COOKIE_NAME = "twelve_data_api_key"
EXPIRY_DAYS = 7

def get_cookie_manager():
    return stx.CookieManager()

def get_api_key(cookie_manager):
    """
    Retrieve API key from Session State or Cookie.
    """
    # 1. Check Session State
    if "api_key" in st.session_state and st.session_state["api_key"]:
        return st.session_state["api_key"]
    
    # 2. Check Cookie
    cookie_val = cookie_manager.get(COOKIE_NAME)
    if cookie_val:
        st.session_state["api_key"] = cookie_val
        return cookie_val
    
    return None

def set_api_key(cookie_manager, key):
    """
    Save API key to Session State and Cookie (7 days).
    """
    # Save to session
    st.session_state["api_key"] = key
    
    # Save to cookie
    expires = datetime.datetime.now() + datetime.timedelta(days=EXPIRY_DAYS)
    cookie_manager.set(COOKIE_NAME, key, expires_at=expires)
    
def clear_api_key(cookie_manager):
    """
    Remove API key from everything.
    """
    if "api_key" in st.session_state:
        del st.session_state["api_key"]
    cookie_manager.delete(COOKIE_NAME)
