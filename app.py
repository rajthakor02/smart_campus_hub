import os
import sys

# Guarantee repository root is in sys.path on Streamlit Cloud and Render
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import importlib.util
import streamlit as st
from dotenv import load_dotenv

# Load environment variables if available
load_dotenv()

# Guaranteed database module loader across platforms
try:
    import database
except (ImportError, ModuleNotFoundError):
    db_path = os.path.join(REPO_ROOT, "database.py")
    db_spec = importlib.util.spec_from_file_location("database", db_path)
    database = importlib.util.module_from_spec(db_spec)
    sys.modules["database"] = database
    db_spec.loader.exec_module(database)

init_db = database.init_db
get_projects = database.get_projects
get_interview_stats = database.get_interview_stats
get_resume_stats = database.get_resume_stats
get_user_resume_scans = database.get_user_resume_scans
get_user_interview_history = database.get_user_interview_history

# Initialize Database
init_db()

# Navigation menu import with fallback
try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False

# Import Modules
from modules.auth import render_auth_page, render_sidebar_user_profile, get_current_user, logout_user
from modules.resume_parser import render_resume_parser_page
from modules.mock_interview import render_mock_interview_page
from modules.project_directory import render_project_directory_page

# Page Configuration
st.set_page_config(
    page_title="AI Smart Campus & Career Hub",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Design tokens and shared Streamlit styling.
def inject_custom_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            :root {
                --cream: #DBD2C1;
                --cream-soft: #EDE6D8;
                --slate: #4C5962;
                --slate-soft: #5C6A74;
                --charcoal: #2A333C;
                --charcoal-soft: #333E48;
                --canvas: #1B2026;
                --sidebar: #21262E;
                --ink: #EDEAE3;
                --muted: #9BA3AC;
                --border: #3A4650;
            }

            header[data-testid="stHeader"] {
                background: transparent !important;
                z-index: 99999 !important;
            }

            [data-testid="stSidebarCollapseButton"],
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="stSidebarExpandButton"],
            [data-testid="collapsedControl"],
            [data-testid="stExpandSidebarButton"] {
                pointer-events: auto !important;
                display: flex !important;
                visibility: visible !important;
                z-index: 999999 !important;
            }

            [data-testid="stExpandSidebarButton"] {
                position: fixed !important;
                top: 16px !important;
                left: 8px !important;
                width: 32px !important;
                height: 32px !important;
            }

            [data-testid="stSidebarCollapseButton"] button,
            [data-testid="stSidebarCollapsedControl"] button,
            [data-testid="stSidebarExpandButton"] button,
            [data-testid="collapsedControl"] button,
            [data-testid="stExpandSidebarButton"] {
                pointer-events: auto !important;
                display: flex !important;
                visibility: visible !important;
                opacity: 1 !important;
                background-color: var(--charcoal) !important;
                border: 1px solid var(--border) !important;
                border-radius: 8px !important;
                padding: 4px 8px !important;
                color: var(--cream) !important;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4) !important;
                cursor: pointer !important;
            }

            [data-testid="stSidebarCollapseButton"]:hover,
            [data-testid="stSidebarCollapseButton"] button:hover,
            [data-testid="stSidebarCollapsedControl"]:hover,
            [data-testid="stSidebarExpandButton"]:hover,
            [data-testid="collapsedControl"]:hover,
            [data-testid="stSidebarCollapsedControl"] button:hover,
            [data-testid="stSidebarExpandButton"] button:hover,
            [data-testid="collapsedControl"] button:hover {
                background-color: var(--slate) !important;
                color: #FFFFFF !important;
            }

            /* Hide ONLY the top-right toolbar (Fork icon, GitHub link, 3 dots menu) and footer */
            [data-testid="stDecoration"],
            [data-testid="stStatusWidget"],
            #MainMenu,
            footer {
                display: none !important;
                visibility: hidden !important;
            }

            .main {
                background: radial-gradient(circle at 85% 0%, #262c34 0, transparent 34%), var(--canvas);
                color: var(--ink);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            .main .block-container {
                max-width: 1140px;
                padding-top: 4.5rem;
                padding-bottom: 3rem;
            }

            h1, h2, h3, h4, p, label, .stMarkdown {
                color: var(--ink);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            .hub-title {
                margin: 0;
                font-size: 2.15rem;
                font-weight: 800;
                letter-spacing: -0.02em;
                line-height: 1.15;
            }

            .hub-subtitle {
                margin: 6px 0 0 0;
                color: var(--muted);
                font-size: 0.95rem;
                max-width: 34ch;
            }

            .card-box {
                background: linear-gradient(145deg, var(--slate-soft), var(--slate));
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 18px;
                box-shadow: 0 12px 28px rgba(0, 0, 0, 0.22);
                transition: border-color 0.15s ease;
            }

            .card-box:hover {
                border-color: var(--cream);
            }

            .card-box h3 {
                font-size: 1.15rem;
                font-weight: 700;
                margin: 0 0 10px 0;
            }

            .card-box p, .card-box ul {
                color: #C9D0D6;
            }

            .card-box p {
                font-size: 0.92rem;
                line-height: 1.55;
            }

            .card-box ul {
                padding-left: 20px;
                margin-bottom: 4px;
                font-size: 0.88rem;
                line-height: 1.7;
            }

            .hero-banner {
                background: linear-gradient(120deg, var(--cream-soft) 0%, var(--cream) 55%, #cfc4ae 100%);
                border-radius: 14px;
                padding: 40px 32px;
                margin-bottom: 26px;
                text-align: center;
                box-shadow: 0 14px 32px rgba(0, 0, 0, 0.28);
            }

            .hero-banner .hero-icon {
                font-size: 2.2rem;
                display: block;
                margin-bottom: 10px;
            }

            .hero-banner h2 {
                margin: 0 0 4px 0;
                font-size: 1.55rem;
                font-weight: 800;
                color: #1B2026;
            }

            .hero-banner p {
                margin: 0 auto;
                max-width: 60ch;
                color: #3A3327;
                font-size: 0.98rem;
                line-height: 1.6;
            }

            .module-header {
                background: linear-gradient(145deg, var(--charcoal-soft), var(--charcoal));
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 24px 26px;
                margin-bottom: 25px;
            }

            .module-header h2 {
                margin: 0 0 6px 0;
                font-size: 1.6rem;
                font-weight: 700;
                color: var(--ink);
            }

            .module-header p {
                margin: 0;
                color: var(--muted);
                font-size: 0.95rem;
            }

            /* Skill Tags */
            .skill-container {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 10px;
            }

            .skill-tag {
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 0.85rem;
                font-weight: 600;
                display: inline-block;
            }

            .skill-matched {
                background-color: rgba(219, 210, 193, 0.16);
                color: var(--cream-soft);
                border: 1px solid rgba(219, 210, 193, 0.4);
            }

            .skill-missing {
                background-color: rgba(196, 120, 105, 0.16);
                color: #e3ada1;
                border: 1px solid rgba(227, 173, 161, 0.4);
            }

            /* Compact metric row matching the reference dashboard. */
            [data-testid="stMetricValue"] {
                font-size: 1.75rem !important;
                font-weight: 800 !important;
                color: var(--ink) !important;
            }

            [data-testid="stMetricLabel"] { color: var(--muted) !important; }
            [data-testid="stMetricDelta"] {
                background: var(--charcoal);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 3px 10px;
                color: var(--cream-soft) !important;
            }

            /* Cream buttons are the strong visual action in each module. */
            .stButton > button,
            .stFormSubmitButton > button {
                border: 1px solid var(--cream) !important;
                border-radius: 8px !important;
                background: var(--cream) !important;
                color: #2A333C !important;
                font-family: 'Inter', sans-serif !important;
                font-weight: 600 !important;
                min-height: 2.55rem;
            }

            .stButton > button *,
            .stFormSubmitButton > button * {
                color: #2A333C !important;
            }

            .stButton > button[kind="primary"] {
                background: var(--cream) !important;
                box-shadow: 0 5px 12px rgba(0, 0, 0, 0.18);
            }

            .stButton > button:hover,
            .stFormSubmitButton > button:hover {
                border-color: var(--cream-soft) !important;
                background: var(--cream-soft) !important;
            }

            .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
                background: var(--charcoal) !important;
                color: var(--ink) !important;
                border-color: var(--border) !important;
                border-radius: 8px !important;
            }

            hr { border-color: var(--border) !important; }

            section[data-testid="stSidebar"] {
                background: var(--sidebar);
                border-right: 1px solid var(--border);
            }

            section[data-testid="stSidebar"] {
                min-width: 266px !important;
                max-width: 266px !important;
            }

            section[data-testid="stSidebar"] .block-container {
                padding: 2.25rem 1.6rem;
            }

            section[data-testid="stSidebar"] hr { border-color: var(--border); }

            .sidebar-brand {
                text-align: left;
                padding: 10px 0 24px 0;
            }

            .sidebar-brand h1 {
                margin: 0;
                color: var(--ink);
                font-size: 1.18rem;
                font-weight: 500;
                letter-spacing: 0.38em;
            }

            .sidebar-brand span {
                display: block;
                margin-top: 8px;
                font-size: 0.75rem;
                color: var(--muted);
                font-weight: 500;
                letter-spacing: 0.08em;
                word-spacing: 0.45em;
            }

            .sidebar-nav-label {
                display: none;
            }

            section[data-testid="stSidebar"] hr {
                margin: 0 0 22px 0;
            }

            section[data-testid="stSidebar"] .nav-link {
                min-height: 46px;
                padding: 0.7rem 0.75rem !important;
                margin: 3px 0 !important;
                border-radius: 12px !important;
                font-size: 0.9rem !important;
            }

            section[data-testid="stSidebar"] .nav-link-selected {
                background-color: var(--cream-soft) !important;
                color: #1B2026 !important;
                font-weight: 500 !important;
            }

            section[data-testid="stSidebar"] .nav-link-selected .icon {
                color: #1B2026 !important;
            }

            section[data-testid="stSidebar"] .nav-link:hover {
                background-color: var(--charcoal) !important;
            }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# Current User State
current_user = get_current_user()

# Sidebar Setup
with st.sidebar:
    st.markdown("""
        <div class="sidebar-brand">
            <h1>MOKOTO</h1>
            <span>Learn&nbsp;&nbsp; Build&nbsp;&nbsp; Grow</span>
        </div>
    """, unsafe_allow_html=True)

    # Render User Profile Card or Guest Badge
    if current_user:
        render_sidebar_user_profile()
    else:
        st.markdown("""
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; font-size: 0.82rem; color: #9BA3AC;">
                👋 <strong>Guest Mode</strong><br>Sign in to save your personal resume scans & interview scores.
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    if current_user:
        menu_options = [
            "Dashboard",
            "Resume Parser",
            "AI Mock Interview",
            "Project Showcase",
            "My Profile"
        ]
        menu_icons = ["house", "file-earmark-text", "mic", "grid", "person-badge"]
    else:
        menu_options = [
            "Dashboard",
            "Sign In / Register",
            "Resume Parser",
            "AI Mock Interview",
            "Project Showcase"
        ]
        menu_icons = ["house", "box-arrow-in-right", "file-earmark-text", "mic", "grid"]

    _override = st.session_state.pop("_nav_override", None)
    _default_index = menu_options.index(_override) if _override in menu_options else 0

    if HAS_OPTION_MENU:
        selected_menu = option_menu(
            menu_title=None,
            options=menu_options,
            icons=menu_icons,
            default_index=_default_index,
            manual_select=_default_index if _override else None,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#DBD2C1", "font-size": "1rem"},
                "nav-link": {
                    "font-size": "0.92rem",
                    "text-align": "left",
                    "margin": "4px 0",
                    "border-radius": "8px",
                    "color": "#9BA3AC",
                    "--hover-color": "#2A333C",
                },
                "nav-link-selected": {"background-color": "#EDE6D8", "color": "#1B2026", "font-weight": "500"}
            }
        )
    else:
        selected_menu = st.radio("Choose Module", menu_options, index=_default_index, label_visibility="collapsed")

    st.markdown("---")

# Main Header Global / Personal Statistics Bar
def render_header_stats(user=None):
    proj_count = len(get_projects())
    if user:
        username = user.get("username")
        int_stats = get_interview_stats(username=username)
        res_stats = get_resume_stats(username=username)
        int_label = "My Interviews"
        res_label = "My Resume Scans"
        int_delta = f"Avg Score: {int_stats['avg_score']}%" if int_stats['avg_score'] else "Start First"
        res_delta = f"Avg Match: {res_stats['avg_score']}%" if res_stats['avg_score'] else "Upload Resume"
    else:
        int_stats = get_interview_stats()
        res_stats = get_resume_stats()
        int_label = "Mock Interviews"
        res_label = "Resume ATS Scans"
        int_delta = f"Avg Score: {int_stats['avg_score']}%" if int_stats['avg_score'] else "Active"
        res_delta = f"Avg Match: {res_stats['avg_score']}%" if res_stats['avg_score'] else "Active"

    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
    
    with col1:
        st.markdown("""
            <h1 class="hub-title">Smart Campus &amp; Career Hub</h1>
            <p class="hub-subtitle">Empowering campus talent with AI resume scoring, mock technical interviews, and open project showcases.</p>
        """, unsafe_allow_html=True)
        
    with col2:
        st.metric("Featured Projects", proj_count, delta="Live Directory")
        
    with col3:
        st.metric(int_label, int_stats["total_interviews"], delta=int_delta)
        
    with col4:
        st.metric(res_label, res_stats["total_scans"], delta=res_delta)

    st.markdown("---")

render_header_stats(current_user)

def render_my_profile_page(user):
    """Renders the personalized user profile and activity dashboard."""
    username = user.get("username")
    res_stats = get_resume_stats(username)
    int_stats = get_interview_stats(username)
    scans = get_user_resume_scans(username, limit=10)
    interviews = get_user_interview_history(username, limit=10)

    st.markdown(f"""
        <div class="module-header">
            <h2>👤 Student Profile: {user.get('full_name')}</h2>
            <p>Email: {user.get('email')} &bull; Role: <strong>{user.get('role', 'student').capitalize()}</strong> &bull; Member since: {user.get('created_at', '')[:10]}</p>
        </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Resume Scans", res_stats["total_scans"])
    with m2:
        st.metric("Avg ATS Score", f"{res_stats['avg_score']}%" if res_stats['avg_score'] else "N/A")
    with m3:
        st.metric("Mock Interviews", int_stats["total_interviews"])
    with m4:
        st.metric("Avg Interview Score", f"{int_stats['avg_score']}%" if int_stats['avg_score'] else "N/A")

    st.markdown("---")

    p_tab1, p_tab2 = st.tabs(["📄 My Saved Resume Scans", "🎙️ My Mock Interview Evaluations"])

    with p_tab1:
        if not scans:
            st.info("ℹ️ You haven't scanned any resumes yet. Navigate to 'Resume Parser' to run an ATS compatibility scan!")
        else:
            for s in scans:
                with st.container():
                    st.markdown(f"""
                        <div class="card-box" style="margin-bottom: 12px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <h4 style="margin:0; color:#F8FAFC;">{s['filename']}</h4>
                                <span style="background-color:rgba(16, 185, 129, 0.2); color:#34D399; border:1px solid rgba(52,211,153,0.4); padding:4px 12px; border-radius:14px; font-weight:bold;">
                                    ATS Score: {s['match_score']}%
                                </span>
                            </div>
                            <p style="margin:6px 0; color:#9BA3AC; font-size:0.85rem;">Target Role: <strong>{s['target_role']}</strong> &bull; Scanned on: {s['timestamp'][:16]}</p>
                            <div style="margin-top:8px;">
                                <small style="color:#60A5FA;">Matched Skills: {', '.join(s['matched_skills'][:5]) if s['matched_skills'] else 'None detected'}</small>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    with p_tab2:
        if not interviews:
            st.info("ℹ️ No mock interview sessions recorded yet. Navigate to 'AI Mock Interview' to practice technical Q&A!")
        else:
            for iv in interviews:
                with st.container():
                    st.markdown(f"""
                        <div class="card-box" style="margin-bottom: 12px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <h4 style="margin:0; color:#F8FAFC;">{iv['role']} ({iv['difficulty']})</h4>
                                <span style="background-color:rgba(59, 130, 246, 0.2); color:#60A5FA; border:1px solid rgba(59,130,246,0.4); padding:4px 12px; border-radius:14px; font-weight:bold;">
                                    Score: {iv['score']}/100
                                </span>
                            </div>
                            <p style="margin:6px 0; color:#CBD5E1; font-size:0.9rem;"><strong>Q:</strong> {iv['question'][:140]}...</p>
                            <p style="margin:4px 0; color:#9BA3AC; font-size:0.85rem;"><strong>Your Answer:</strong> {iv['user_answer'][:120]}...</p>
                            <div style="margin-top:6px; font-size:0.82rem; color:#34D399;">
                                <strong>Feedback:</strong> {iv['strengths']}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

# Page Routing Logic
if selected_menu == "Dashboard":
    st.markdown("""
        <div class="hero-banner">
            <span class="hero-icon">🚀</span>
            <h2>Welcome to the AI-Powered Campus &amp; Career Hub</h2>
            <p>
                This platform integrates cutting-edge AI features into a single, unified campus portal. 
                Whether you're preparing for upcoming campus recruitment, benchmarking your resume against top tech job descriptions, 
                or showcasing your engineering projects to recruiters and peers, Smart Campus Hub provides instant AI assistance.
            </p>
        </div>
    """, unsafe_allow_html=True)

    d_col1, d_col2, d_col3 = st.columns(3, gap="large")

    with d_col1:
        st.markdown("""
            <div class="card-box" style="height: 100%;">
                <h3>📄 Module A: Resume Parser</h3>
                <p>Upload your PDF resume and paste target job descriptions. Extract key skills, detect missing gaps, and get instant ATS compatibility scores.</p>
                <ul>
                    <li>PDF text extraction via pdfplumber</li>
                    <li>Structured JSON skill gap output</li>
                    <li>Actionable improvement steps</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Analyze", key="dash_go_resume"):
            st.session_state["_nav_override"] = "Resume Parser"
            st.rerun()

    with d_col2:
        st.markdown("""
            <div class="card-box" style="height: 100%;">
                <h3>🎙️ Module B: AI Mock Interview</h3>
                <p>Practice real-time technical interviews tailored by role and difficulty level with live response streaming and answer evaluation.</p>
                <ul>
                    <li>Interactive chat stream (st.write_stream)</li>
                    <li>Instant score & feedback card</li>
                    <li>Q&A session history tracking</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Start Session", key="dash_go_interview"):
            st.session_state["_nav_override"] = "AI Mock Interview"
            st.rerun()

    with d_col3:
        st.markdown("""
            <div class="card-box" style="height: 100%;">
                <h3>🚀 Module C: Project Showcase</h3>
                <p>Browse student engineering projects, upvote community submissions, filter by tech stack, and publish your own portfolio projects.</p>
                <ul>
                    <li>2-Column grid showcase cards</li>
                    <li>Domain & Tech Stack filtering</li>
                    <li>SQLite persistent database</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Browse Projects", key="dash_go_projects"):
            st.session_state["_nav_override"] = "Project Showcase"
            st.rerun()

elif selected_menu == "Sign In / Register":
    render_auth_page()

elif selected_menu == "My Profile":
    if current_user:
        render_my_profile_page(current_user)
    else:
        render_auth_page()

elif selected_menu == "Resume Parser":
    render_resume_parser_page(
        api_key=os.getenv("GEMINI_API_KEY", ""),
        provider="gemini",
        model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        current_user=current_user
    )

elif selected_menu == "AI Mock Interview":
    render_mock_interview_page(
        api_key=os.getenv("GEMINI_API_KEY", ""),
        provider="gemini",
        model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        current_user=current_user
    )

elif selected_menu == "Project Showcase":
    render_project_directory_page(current_user=current_user)
