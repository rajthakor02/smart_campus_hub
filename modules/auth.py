import os
import sys
_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

import streamlit as st
from campus_db import authenticate_user, create_user

def init_auth_state():
    """Initializes authentication session state variables."""
    if "current_user" not in st.session_state:
        st.session_state.current_user = None

def get_current_user():
    """Returns the logged-in user dictionary or None."""
    init_auth_state()
    return st.session_state.get("current_user")

def logout_user():
    """Logs out the current user and clears session state."""
    st.session_state.current_user = None
    st.rerun()

def render_sidebar_user_profile():
    """Renders the user profile card and logout button in the sidebar."""
    user = get_current_user()
    if not user:
        return

    role_badge_color = "#34D399" if user.get("role") == "student" else "#60A5FA"
    st.sidebar.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; padding: 12px 14px; margin-bottom: 15px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #3B82F6, #1D4ED8); display: flex; align-items: center; justify-content: center; font-weight: bold; color: #FFFFFF; font-size: 1rem;">
                    {user.get('full_name', 'U')[0].upper()}
                </div>
                <div style="overflow: hidden;">
                    <div style="font-size: 0.92rem; font-weight: 700; color: #F8FAFC; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">
                        {user.get('full_name')}
                    </div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">
                        @{user.get('username')} &bull; <span style="color: {role_badge_color}; font-weight: 600;">{user.get('role', 'student').capitalize()}</span>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Sign Out", use_container_width=True, key="sidebar_logout_btn"):
        logout_user()

def render_auth_page():
    """Renders the Login and Registration interface."""
    init_auth_state()

    st.markdown("""
        <div class="hero-banner" style="margin-bottom: 24px;">
            <span class="hero-icon">🔐</span>
            <h2>Smart Campus Authentication Hub</h2>
            <p>Sign in to unlock personalized AI resume scoring, private mock interview analytics, and showcase your campus engineering projects.</p>
        </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔑 Sign In", "✨ Create Account"])

    # --- TAB 1: SIGN IN ---
    with tab_login:
        col1, col2 = st.columns([1.2, 1], gap="large")

        with col1:
            st.markdown("### Welcome Back")
            st.caption("Enter your registered campus username or email to access your account.")

            with st.form("login_form"):
                ident = st.text_input("Username or Email", placeholder="e.g. alex_rivera or alex@campus.edu")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign In to Campus Hub", type="primary", use_container_width=True)

                if submitted:
                    success, msg, user = authenticate_user(ident, password)
                    if success:
                        st.session_state.current_user = user
                        st.success(f"Welcome back, {user['full_name']}! 👋")
                        st.rerun()
                    else:
                        st.error(f"⚠️ {msg}")

        with col2:
            st.markdown("### 🎓 Quick Demo Access")
            st.info("""
                **Capstone Evaluation Demo Accounts:**
                
                - **Student Account:**
                  - Username: `student_demo`
                  - Password: `Campus@2026`
                
                - **Recruiter Account:**
                  - Username: `recruiter_demo`
                  - Password: `Campus@2026`
            """)
            if st.button("⚡ Quick Sign In as Demo Student", use_container_width=True):
                success, msg, user = authenticate_user("student_demo", "Campus@2026")
                if success:
                    st.session_state.current_user = user
                    st.rerun()

    # --- TAB 2: SIGN UP ---
    with tab_signup:
        st.markdown("### Register New Campus Account")
        st.caption("Create your profile to start tracking your resume ATS scores and mock interview performance.")

        with st.form("signup_form", clear_on_submit=True):
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                full_name = st.text_input("Full Name *", placeholder="e.g. Alex Rivera")
                username = st.text_input("Choose Username *", placeholder="e.g. alex_rivera (letters, numbers, underscores)")
            with r_col2:
                email = st.text_input("Campus Email Address *", placeholder="e.g. alex@campus.edu")
                role = st.selectbox("Role *", ["Student", "Recruiter", "Faculty / Mentor"])

            new_password = st.text_input("Password (min 6 characters) *", type="password", placeholder="Create a secure password")
            confirm_password = st.text_input("Confirm Password *", type="password", placeholder="Repeat password")

            signup_submitted = st.form_submit_button("Create My Account", type="primary", use_container_width=True)

            if signup_submitted:
                if new_password != confirm_password:
                    st.error("⚠️ Passwords do not match. Please re-enter.")
                else:
                    success, msg, user = create_user(
                        username=username,
                        email=email,
                        password=new_password,
                        full_name=full_name,
                        role=role.lower()
                    )
                    if success:
                        st.session_state.current_user = user
                        st.success("🎉 Account created successfully! Logging you in...")
                        st.rerun()
                    else:
                        st.error(f"⚠️ {msg}")
