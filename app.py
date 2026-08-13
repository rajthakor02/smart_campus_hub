import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables if available
load_dotenv()

# Initialize Database
from database import init_db, get_projects, get_interview_stats, get_resume_stats
init_db()

# Navigation menu import with fallback
try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False

# Import Modules
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

# Modern Custom Design System (CSS)
def inject_custom_css():
    st.markdown("""
        <style>
            /* Hide Streamlit Default Top Header, Fork & GitHub Icons, and Footer */
            header[data-testid="stHeader"] {
                display: none !important;
            }
            div[data-testid="stToolbar"] {
                display: none !important;
            }
            #MainMenu {
                visibility: hidden !important;
            }
            footer {
                visibility: hidden !important;
            }

            /* Base Theme Tweaks */
            .main {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
            }
            
            /* Glassmorphism Card Boxes */
            .card-box {
                background: rgba(30, 41, 59, 0.7);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                padding: 20px;
                margin-bottom: 18px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
                transition: transform 0.2s ease, border-color 0.2s ease;
            }
            
            .card-box:hover {
                border-color: rgba(59, 130, 246, 0.4);
            }

            /* Module Banner Header */
            .module-header {
                background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
                border-left: 5px solid #3B82F6;
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 25px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            }

            .module-header h2 {
                margin: 0 0 6px 0;
                font-size: 1.8rem;
                font-weight: 700;
                background: linear-gradient(90deg, #60A5FA, #93C5FD);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .module-header p {
                margin: 0;
                color: #94A3B8;
                font-size: 0.98rem;
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
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
                display: inline-block;
            }

            .skill-matched {
                background-color: rgba(16, 185, 129, 0.2);
                color: #34D399;
                border: 1px solid rgba(52, 211, 153, 0.4);
            }

            .skill-missing {
                background-color: rgba(239, 68, 68, 0.2);
                color: #F87171;
                border: 1px solid rgba(248, 113, 113, 0.4);
            }

            /* Top Overview Metric Badges */
            [data-testid="stMetricValue"] {
                font-size: 1.8rem !important;
                font-weight: 800 !important;
                color: #60A5FA !important;
            }

            /* Primary Button Styling */
            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
                border: none;
                border-radius: 10px;
                font-weight: 600;
                padding: 10px 20px;
                transition: all 0.2s ease;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
            }

            .stButton > button[kind="primary"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5);
            }
            
            /* Sidebar Styling */
            section[data-testid="stSidebar"] {
                background-color: #0B1120;
                border-right: 1px solid rgba(255, 255, 255, 0.08);
            }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# Sidebar Setup & API Configuration
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 10px 0 20px 0;">
            <h1 style="margin:0; font-size: 1.6rem; color: #60A5FA;">🎓 Smart Campus</h1>
            <span style="font-size: 0.85rem; color: #94A3B8; font-weight: 600;">AI Career & Project Hub</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### ⚙️ AI Engine Setup")
    
    provider = st.radio(
        "Select LLM Provider",
        ["Google Gemini", "OpenAI"],
        help="Select your AI API provider for resume parsing and mock interviewing."
    )
    
    provider_key = "gemini" if "Gemini" in provider else "openai"
    
    # Check default env key
    default_key = os.getenv("GEMINI_API_KEY" if provider_key == "gemini" else "OPENAI_API_KEY", "")
    
    api_key_input = st.text_input(
        f"{provider} API Key",
        value=default_key,
        type="password",
        help=f"Enter your {provider} API key. If left blank, the app uses intelligent fallback AI engines."
    )
    
    if provider_key == "gemini":
        model_name = st.selectbox("Gemini Model", ["gemini-1.5-flash", "gemini-1.5-pro"])
    else:
        model_name = st.selectbox("OpenAI Model", ["gpt-4o-mini", "gpt-4o"])
        
    if api_key_input:
        st.success(f"🔑 {provider} Key Configured")
    else:
        st.info("💡 Running in Live Demo Mode (Built-in Rule AI active)")

    st.markdown("---")
    
    # Navigation Menu
    st.markdown("### 🧭 Navigation")
    
    menu_options = [
        "Dashboard Overview",
        "Resume Parser & JD Matcher",
        "AI Mock Interviewer",
        "Project Directory Showcase"
    ]
    menu_icons = ["house", "file-earmark-text", "mic", "grid"]

    if HAS_OPTION_MENU:
        selected_menu = option_menu(
            menu_title=None,
            options=menu_options,
            icons=menu_icons,
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#60A5FA", "font-size": "1rem"},
                "nav-link": {
                    "font-size": "0.92rem",
                    "text-align": "left",
                    "margin": "4px 0",
                    "border-radius": "8px",
                    "color": "#94A3B8"
                },
                "nav-link-selected": {"background-color": "#1E293B", "color": "#F8FAFC", "font-weight": "600"}
            }
        )
    else:
        selected_menu = st.radio("Choose Module", menu_options)

    st.markdown("---")
    st.caption("⚡ Built 100% in Pure Python using Streamlit, SQLite & LLM APIs.")

# Main Header Global Statistics Bar
def render_header_stats():
    proj_count = len(get_projects())
    int_stats = get_interview_stats()
    res_stats = get_resume_stats()

    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
    
    with col1:
        st.markdown("""
            <h1 style="margin:0; font-size: 2rem; background: linear-gradient(90deg, #3B82F6, #60A5FA); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Smart Campus & Career Hub
            </h1>
            <p style="margin:0; color: #94A3B8; font-size: 0.95rem;">Empowering campus talent with AI resume scoring, mock technical interviews, and open project showcases.</p>
        """, unsafe_allow_html=True)
        
    with col2:
        st.metric("Featured Projects", proj_count, delta="Live Directory")
        
    with col3:
        st.metric("Mock Interviews", int_stats["total_interviews"], delta=f"Avg Score: {int_stats['avg_score']}%" if int_stats['avg_score'] else "Active")
        
    with col4:
        st.metric("Resume ATS Scans", res_stats["total_scans"], delta=f"Avg Match: {res_stats['avg_score']}%" if res_stats['avg_score'] else "Active")

    st.markdown("---")

render_header_stats()

# Page Routing Logic
if selected_menu == "Dashboard Overview":
    st.markdown("""
        <div class="card-box" style="background: linear-gradient(135deg, rgba(30,41,59,0.9), rgba(15,23,42,0.9)); border: 1px solid rgba(59,130,246,0.3);">
            <h2 style="color: #60A5FA; margin-top:0;">🚀 Welcome to the AI-Powered Campus & Career Hub</h2>
            <p style="font-size: 1.05rem; color: #CBD5E1; line-height: 1.6;">
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
                <p style="color: #94A3B8;">Upload your PDF resume and paste target job descriptions. Extract key skills, detect missing gaps, and get instant ATS compatibility scores.</p>
                <ul style="color: #CBD5E1; padding-left: 20px;">
                    <li>PDF text extraction via pdfplumber</li>
                    <li>Structured JSON skill gap output</li>
                    <li>Actionable improvement steps</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    with d_col2:
        st.markdown("""
            <div class="card-box" style="height: 100%;">
                <h3>🎙️ Module B: AI Mock Interview</h3>
                <p style="color: #94A3B8;">Practice real-time technical interviews tailored by role and difficulty level with live response streaming and answer evaluation.</p>
                <ul style="color: #CBD5E1; padding-left: 20px;">
                    <li>Interactive chat stream (st.write_stream)</li>
                    <li>Instant score & feedback card</li>
                    <li>Q&A session history tracking</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    with d_col3:
        st.markdown("""
            <div class="card-box" style="height: 100%;">
                <h3>🚀 Module C: Project Showcase</h3>
                <p style="color: #94A3B8;">Browse student engineering projects, upvote community submissions, filter by tech stack, and publish your own portfolio projects.</p>
                <ul style="color: #CBD5E1; padding-left: 20px;">
                    <li>2-Column grid showcase cards</li>
                    <li>Domain & Tech Stack filtering</li>
                    <li>SQLite persistent database</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

elif selected_menu == "Resume Parser & JD Matcher":
    render_resume_parser_page(api_key=api_key_input, provider=provider_key, model_name=model_name)

elif selected_menu == "AI Mock Interviewer":
    render_mock_interview_page(api_key=api_key_input, provider=provider_key, model_name=model_name)

elif selected_menu == "Project Directory Showcase":
    render_project_directory_page()
