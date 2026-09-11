import streamlit as st
import json
import re
import os
import sys
from datetime import datetime

# Guarantee parent repository root is in sys.path
_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

import campus_db

# Safely resolve database functions with graceful fallback
get_projects = getattr(campus_db, "get_projects", lambda: [])
get_user_resume_scans = getattr(campus_db, "get_user_resume_scans", lambda u, limit=10: [])
get_user_interview_history = getattr(campus_db, "get_user_interview_history", lambda u, limit=10: [])
save_agent_message = getattr(campus_db, "save_agent_message", lambda *args, **kwargs: None)
get_agent_history = getattr(campus_db, "get_agent_history", lambda *args, **kwargs: [])
clear_agent_history = getattr(campus_db, "clear_agent_history", lambda *args, **kwargs: True)
is_using_mongodb = getattr(campus_db, "is_using_mongodb", lambda: False)

# Optional LLM driver imports
try:
    from google import genai
    from google.genai import types
    HAS_NEW_GENAI = True
except ImportError:
    genai = None
    HAS_NEW_GENAI = False

try:
    import google.generativeai as legacy_genai
    HAS_LEGACY_GENAI = True
except ImportError:
    legacy_genai = None
    HAS_LEGACY_GENAI = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    openai = None
    HAS_OPENAI = False

# ==============================================================================
# 🛠️ AGENT TOOL REGISTRY (Autonomous Domain Tools)
# ==============================================================================

def tool_inspect_user_skills(username: str) -> dict:
    """Tool 1: Inspects the student's uploaded resume scans, matched skills, and ATS score."""
    if not username:
        return {"status": "error", "message": "User not authenticated. Running in guest mode."}
    
    scans = get_user_resume_scans(username, limit=5)
    if not scans:
        return {
            "status": "no_data",
            "message": f"No past resume scans found for student @{username}.",
            "suggestion": "Recommend the student upload a resume in the Resume Parser module first."
        }
    
    latest = scans[0]
    all_matched = set()
    all_missing = set()
    for s in scans:
        for m in s.get("matched_skills", []):
            all_matched.add(m)
        for mis in s.get("missing_skills", []):
            all_missing.add(mis)
            
    return {
        "status": "success",
        "username": username,
        "scans_analyzed": len(scans),
        "latest_target_role": latest.get("target_role", "General Software"),
        "latest_ats_score": latest.get("match_score", 0),
        "verified_skills": sorted(list(all_matched)),
        "identified_skill_gaps": sorted(list(all_missing))[:8],
        "latest_recommendations": latest.get("recommendations", [])[:3]
    }

def tool_inspect_interview_gaps(username: str) -> dict:
    """Tool 2: Analyzes student's mock technical interview answers, weak topics, and scores."""
    if not username:
        return {"status": "error", "message": "User not authenticated. Running in guest mode."}
        
    history = get_user_interview_history(username, limit=10)
    if not history:
        return {
            "status": "no_data",
            "message": f"No past mock interview attempts found for @{username}.",
            "suggestion": "Recommend taking a mock interview session to evaluate technical readiness."
        }
        
    scores = [h.get("score", 0) for h in history if h.get("score") is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    
    gaps_collected = []
    strengths_collected = []
    for h in history:
        if h.get("gaps"):
            gaps_collected.append(h["gaps"])
        if h.get("strengths"):
            strengths_collected.append(h["strengths"])
            
    return {
        "status": "success",
        "username": username,
        "interviews_taken": len(history),
        "average_score": avg_score,
        "identified_weaknesses": gaps_collected[:3],
        "demonstrated_strengths": strengths_collected[:3]
    }

def tool_search_campus_projects(query: str = "", domain: str = "") -> dict:
    """Tool 3: Queries the campus project showcase directory for peer benchmarks and collaborator ideas."""
    all_projects = get_projects()
    matches = []
    
    q = query.lower().strip() if query else ""
    d = domain.lower().strip() if domain else ""
    
    for p in all_projects:
        title = p.get("title", "").lower()
        tech = p.get("tech_stack", "").lower()
        dom = p.get("domain", "").lower()
        desc = p.get("description", "").lower()
        
        match_query = (q in title or q in tech or q in desc) if q else True
        match_domain = (d in dom) if d else True
        
        if match_query and match_domain:
            matches.append({
                "title": p.get("title"),
                "author": p.get("student_name"),
                "domain": p.get("domain"),
                "tech_stack": p.get("tech_stack"),
                "upvotes": p.get("upvotes", 0),
                "github_url": p.get("github_url", "")
            })
            
    return {
        "status": "success",
        "search_query": query,
        "search_domain": domain,
        "total_matches": len(matches),
        "top_projects": matches[:5]
    }

def tool_generate_milestone_roadmap(target_role: str, weeks: int = 4, focus_skills: list = None) -> dict:
    """Tool 4: Generates a milestone-driven week-by-week career preparation roadmap."""
    role = target_role.title()
    
    curriculum = [
        {
            "week": 1,
            "phase": "Diagnostic & Foundational Mastery",
            "goal": f"Strengthen baseline concepts for {role}",
            "tasks": [
                f"Review core data structures, system patterns, and architecture for {role}",
                "Audit GitHub repository and configure automated unit tests",
                "Complete 1 diagnostic mock technical interview on Smart Campus Hub"
            ]
        },
        {
            "week": 2,
            "phase": "Technical Deep Dive & Gap Remediation",
            "goal": "Bridge identified missing technical competencies",
            "tasks": [
                "Build a containerized REST/gRPC service with Docker & Python",
                "Implement caching or indexing optimizations (Redis, MongoDB, PostgreSQL)",
                "Refactor Capstone project code for clean modular architecture"
            ]
        },
        {
            "week": 3,
            "phase": "Capstone Project Architecture & Cloud Deployment",
            "goal": "Deploy a production-grade portfolio project to showcase on campus",
            "tasks": [
                "Deploy full-stack web application to Streamlit Cloud or container hosting",
                "Add interactive README with architecture diagrams and API specs",
                "Publish project to the Campus Showcase Directory for peer & recruiter review"
            ]
        },
        {
            "week": 4,
            "phase": "Interview Readiness & ATS Fine-Tuning",
            "goal": "Polish resume and master technical/system design questions",
            "tasks": [
                "Run ATS scanner on resume for target job descriptions until 85%+ score",
                "Simulate 3 high-difficulty technical mock interviews",
                "Connect with campus peers or recruiters reviewing showcased projects"
            ]
        }
    ]
    
    return {
        "status": "success",
        "target_role": role,
        "duration_weeks": weeks,
        "curriculum": curriculum
    }

def tool_generate_project_blueprint(idea: str, domain: str = "AI / Machine Learning") -> dict:
    """Tool 5: Creates an architectural blueprint and tech stack design for student projects."""
    clean_idea = idea.strip() or "Smart AI Campus Assistant"
    return {
        "status": "success",
        "project_title": f"{clean_idea}: Next-Gen Architecture",
        "domain": domain,
        "suggested_tech_stack": {
            "frontend": "Streamlit (Python-first, responsive, zero frontend overhead)",
            "backend": "Python 3.12+ (Async FastAPI / Modular Architecture)",
            "database": "MongoDB Atlas Cloud (Flexible NoSQL collections) + SQLite local fallback",
            "ai_engine": "Google Gemini 1.5 Flash / LangChain / OpenAI API",
            "devops": "Docker, GitHub Actions, Streamlit Community Cloud"
        },
        "architecture_modules": [
            "Authentication & Role-Based Access (PBKDF2-HMAC-SHA256)",
            "Data Ingestion & Vector / Relational Storage Engine",
            "Autonomous Agent Reasoning Loop with Tool Registry",
            "Interactive Analytical Dashboard with Exportable Metrics"
        ],
        "milestones": [
            "Sprint 1: Schema design, data seeding, and secure authentication flow",
            "Sprint 2: Core functional logic & LLM prompt chain integration",
            "Sprint 3: UI polishing, error boundaries, and offline fallbacks",
            "Sprint 4: Deployment to Cloud & Campus Directory Showcase"
        ]
    }

# ==============================================================================
# 🧠 AUTONOMOUS AGENT REASONING ENGINE (ReAct Loop)
# ==============================================================================

def execute_heuristic_agent(user_prompt: str, current_user: dict = None) -> tuple:
    """
    Autonomous ReAct execution loop that handles planning, tool dispatching,
    and synthesis when no LLM API key is configured or offline.
    """
    prompt_lower = user_prompt.lower()
    username = current_user.get("username") if current_user else None
    
    tool_trace = []
    
    # Intent Detection & Tool Selection
    wants_profile_audit = any(w in prompt_lower for w in ["audit", "profile", "skill", "resume", "weakness", "gap", "my stats"])
    wants_roadmap = any(w in prompt_lower for w in ["roadmap", "plan", "prepare", "how to learn", "guide", "weeks", "study"])
    wants_project_search = any(w in prompt_lower for w in ["project", "directory", "showcase", "campus", "peers", "docker", "pytorch", "python", "find"])
    wants_blueprint = any(w in prompt_lower for w in ["architect", "blueprint", "idea", "capstone", "build", "create project"])
    
    # 1. Profile & Skills Audit Tool
    skills_data = None
    interview_data = None
    if wants_profile_audit or wants_roadmap:
        tool_trace.append({
            "thought": f"Student is asking for guidance. Querying user's historical resume ATS scans and verified skills for @{username or 'guest'}...",
            "tool": "tool_inspect_user_skills",
            "args": {"username": username}
        })
        skills_data = tool_inspect_user_skills(username)
        
        tool_trace.append({
            "thought": "Inspecting candidate's mock interview track record and technical gaps...",
            "tool": "tool_inspect_interview_gaps",
            "args": {"username": username}
        })
        interview_data = tool_inspect_interview_gaps(username)

    # 2. Campus Projects Tool
    project_data = None
    if wants_project_search or wants_profile_audit or wants_blueprint:
        search_term = ""
        for term in ["python", "pytorch", "docker", "ai", "iot", "fastapi", "machine learning"]:
            if term in prompt_lower:
                search_term = term
                break
        tool_trace.append({
            "thought": f"Searching Campus Project Showcase for relevant reference projects (query='{search_term}')...",
            "tool": "tool_search_campus_projects",
            "args": {"query": search_term, "domain": ""}
        })
        project_data = tool_search_campus_projects(query=search_term)

    # 3. Roadmap Tool
    roadmap_data = None
    if wants_roadmap:
        role_guess = "Software Engineer"
        for r in ["backend engineer", "data scientist", "ml engineer", "frontend engineer", "cloud engineer", "full stack"]:
            if r in prompt_lower:
                role_guess = r
                break
        tool_trace.append({
            "thought": f"Synthesizing structured milestone roadmap for target role: '{role_guess}'.",
            "tool": "tool_generate_milestone_roadmap",
            "args": {"target_role": role_guess, "weeks": 4}
        })
        roadmap_data = tool_generate_milestone_roadmap(target_role=role_guess, weeks=4)

    # 4. Blueprint Tool
    blueprint_data = None
    if wants_blueprint:
        tool_trace.append({
            "thought": "Synthesizing full Capstone technical architecture and schema blueprint...",
            "tool": "tool_generate_project_blueprint",
            "args": {"idea": user_prompt, "domain": "AI / Full-Stack"}
        })
        blueprint_data = tool_generate_project_blueprint(idea=user_prompt)

    # Synthesize Final Advisory Response
    response_parts = []
    
    if current_user:
        response_parts.append(f"### 🎓 Personalized Advisory for **{current_user.get('full_name', username)}** (`@{username}`)\n")
    else:
        response_parts.append("### 🎓 CampusAI Career & Project Advisory\n*(Guest Mode: Sign in to enable personal ATS & interview score analysis)*\n")

    if skills_data and skills_data.get("status") == "success":
        response_parts.append("#### 🔍 1. Profile & ATS Competency Audit")
        response_parts.append(f"- **Latest ATS Match Score**: `{skills_data['latest_ats_score']}%` for **{skills_data['latest_target_role']}**")
        if skills_data.get("verified_skills"):
            v_skills = ", ".join(f"`{s}`" for s in skills_data["verified_skills"])
            response_parts.append(f"- **Verified Strengths**: {v_skills}")
        if skills_data.get("identified_skill_gaps"):
            g_skills = ", ".join(f"`{s}`" for s in skills_data["identified_skill_gaps"])
            response_parts.append(f"- **Identified Missing Skills**: {g_skills}")
        response_parts.append("")

    if interview_data and interview_data.get("status") == "success":
        response_parts.append(f"- **Technical Mock Interview Average**: `{interview_data['average_score']}/100` ({interview_data['interviews_taken']} attempts)")
        if interview_data.get("identified_weaknesses"):
            response_parts.append(f"- **Key Interview Areas for Growth**: {interview_data['identified_weaknesses'][0]}")
        response_parts.append("")
    elif skills_data and skills_data.get("status") == "no_data":
        response_parts.append("> 💡 **Tip**: You haven't uploaded a resume yet! Navigate to **Resume Parser** to get instant ATS scoring and unlock tailored skill audits.\n")

    if roadmap_data and roadmap_data.get("status") == "success":
        response_parts.append(f"#### 🗺️ 2. Recommended {roadmap_data['target_role']} Action Roadmap")
        for item in roadmap_data["curriculum"]:
            response_parts.append(f"**Week {item['week']}: {item['phase']}** (_{item['goal']}_)")
            for t in item["tasks"]:
                response_parts.append(f"  - [ ] {t}")
        response_parts.append("")

    if blueprint_data and blueprint_data.get("status") == "success":
        response_parts.append(f"#### 🏗️ Capstone Project Architecture Blueprint: **{blueprint_data['project_title']}**")
        response_parts.append("**Recommended Technology Stack:**")
        for comp, val in blueprint_data["suggested_tech_stack"].items():
            response_parts.append(f"- **{comp.title()}**: {val}")
        response_parts.append("\n**Core Architecture Modules:**")
        for mod in blueprint_data["architecture_modules"]:
            response_parts.append(f"- {mod}")
        response_parts.append("")

    if project_data and project_data.get("status") == "success" and project_data["top_projects"]:
        response_parts.append("#### 📂 3. Campus Peer Project Benchmarks")
        response_parts.append("Here are exemplary projects from your campus peers to reference for architecture and tech stack:")
        for p in project_data["top_projects"]:
            gh = f" ([GitHub]({p['github_url']}))" if p.get('github_url') else ""
            response_parts.append(f"- **{p['title']}** by _{p['author']}_ ({p['domain']}) — `{p['tech_stack']}` ★ {p['upvotes']}{gh}")
        response_parts.append("")

    if not wants_profile_audit and not wants_roadmap and not wants_project_search and not wants_blueprint:
        response_parts.append("I'm your **CampusAI Career & Project Advisor Agent**. Here is how I can autonomously assist your campus journey:")
        response_parts.append("1. **Audit Profile & Skill Gaps**: I query your past ATS resume scans and mock interview transcripts to highlight exactly what skills you are missing.")
        response_parts.append("2. **Build Week-by-Week Roadmaps**: Ask me to prepare a customized preparation sprint for roles like _Backend Engineer_, _ML Engineer_, or _Data Analyst_.")
        response_parts.append("3. **Architect Capstone Projects**: Give me a project idea and I'll design the database schema, frontend/backend architecture, and milestones.")
        response_parts.append("4. **Campus Collaboration**: Search peer repositories and connect with student engineering projects across campus.")
        response_parts.append("\n*Try clicking one of the quick prompts above to get started!*")

    return "\n".join(response_parts), tool_trace

def run_ai_agent(user_prompt: str, current_user: dict = None, api_key: str = "", provider: str = "gemini", model_name: str = "gemini-1.5-flash") -> tuple:
    """
    Main entry point for running the agent. Dispatches to LLM if configured,
    with seamless fallback to the heuristic agent.
    """
    username = current_user.get("username") if current_user else "guest"
    
    # First, run domain tools to gather live campus context
    skills_context = tool_inspect_user_skills(username if current_user else None)
    interview_context = tool_inspect_interview_gaps(username if current_user else None)
    projects_context = tool_search_campus_projects()
    
    # If API key is available, call the LLM with full context
    if api_key:
        try:
            system_context = f"""You are CampusAI, an elite Autonomous Career & Project Advisor Agent for engineering students.
You have access to real-time tools and database records for the student.
Student Context:
- Username: {username}
- Authenticated: {bool(current_user)}
- Latest ATS Skills: {json.dumps(skills_context)}
- Mock Interview Transcripts: {json.dumps(interview_context)}
- Campus Projects Sample: {json.dumps(projects_context.get('top_projects', []))}

Format your answer with clear markdown headings, bullet points, actionable checklists, and reference specific projects from campus.
"""
            if provider == "gemini" and (HAS_NEW_GENAI or HAS_LEGACY_GENAI):
                if HAS_NEW_GENAI:
                    client = genai.Client(api_key=api_key)
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=[system_context, user_prompt]
                    )
                    content = resp.text
                else:
                    legacy_genai.configure(api_key=api_key)
                    model = legacy_genai.GenerativeModel(model_name)
                    resp = model.generate_content(f"{system_context}\n\nStudent Prompt: {user_prompt}")
                    content = resp.text
                
                tool_trace = [
                    {"thought": "Retrieved user ATS profile and interview records from MongoDB Atlas.", "tool": "tool_inspect_user_skills", "args": {"username": username}},
                    {"thought": "Queried campus project showcase directory for domain peer benchmarks.", "tool": "tool_search_campus_projects", "args": {"query": ""}},
                    {"thought": f"Synthesized tailored guidance with {model_name}.", "tool": "llm_reasoning_pipeline", "args": {"provider": provider}}
                ]
                return content, tool_trace
                
            elif provider == "openai" and HAS_OPENAI:
                client = openai.OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_context},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7
                )
                content = resp.choices[0].message.content
                tool_trace = [
                    {"thought": "Retrieved user ATS profile and interview records from MongoDB Atlas.", "tool": "tool_inspect_user_skills", "args": {"username": username}},
                    {"thought": "Queried campus project showcase directory for domain peer benchmarks.", "tool": "tool_search_campus_projects", "args": {"query": ""}},
                    {"thought": "Synthesized tailored guidance with OpenAI GPT-4o-mini.", "tool": "llm_reasoning_pipeline", "args": {"provider": provider}}
                ]
                return content, tool_trace
        except Exception as e:
            st.warning(f"[AI Notice] API call encountered an issue: {e}. Switching to offline Expert Heuristic Agent.")
    
    # Robust Heuristic Agent Fallback
    return execute_heuristic_agent(user_prompt, current_user)

# ==============================================================================
# 🎨 STREAMLIT AGENT UI
# ==============================================================================

def render_ai_agent_page(current_user: dict = None, api_key: str = "", provider: str = "gemini", model_name: str = "gemini-1.5-flash"):
    """Renders the interactive AI Career & Project Advisor Agent interface."""
    
    # Header
    st.markdown('''
        <div style="padding: 10px 0 20px 0;">
            <h1 style="margin: 0; font-size: 2.1rem; font-weight: 800; color: #EDEAE3;">
                🤖 CampusAI Career &amp; Project Advisor
            </h1>
            <p style="margin: 6px 0 0 0; color: #9BA3AC; font-size: 0.95rem;">
                Autonomous multi-tool agent for personalized skill gap audits, capstone architectural blueprints, and curated career roadmaps.
            </p>
        </div>
    ''', unsafe_allow_html=True)

    # Status Badges Bar
    username = current_user.get("username") if current_user else "guest"
    col_stat1, col_stat2, col_stat3 = st.columns([3, 3, 2])
    with col_stat1:
        if current_user:
            st.markdown(f"👤 **Session:** `{current_user.get('full_name')}` (`@{username}`)")
        else:
            st.markdown("👤 **Session:** `Guest Mode` (Login to load personal history)")
    with col_stat2:
        engine_label = f"⚡ LLM: {model_name}" if api_key else "⚡ Engine: Autonomous Domain Agent (Offline/Free)"
        st.markdown(engine_label)
    with col_stat3:
        db_status = "🟢 Atlas Cloud" if is_using_mongodb() else "⚪ SQLite Local"
        st.markdown(f"💾 **Memory:** {db_status}")

    st.markdown("---")

    # Quick Starter Prompt Action Chips
    st.markdown("<span style='font-size: 0.85rem; color: #9BA3AC; font-weight: 600;'>QUICK ADVISORY PROMPTS:</span>", unsafe_allow_html=True)
    chip_col1, chip_col2, chip_col3, chip_col4 = st.columns(4)
    
    prompt_to_trigger = None
    with chip_col1:
        if st.button("🔍 Audit Skill Gaps", key="chip_audit", use_container_width=True):
            prompt_to_trigger = "Audit my profile and tell me my top missing skills based on past resumes and interviews."
    with chip_col2:
        if st.button("🗺️ Backend Roadmap", key="chip_roadmap", use_container_width=True):
            prompt_to_trigger = "Generate a 4-week preparation roadmap for a Backend Software Engineer role."
    with chip_col3:
        if st.button("🏗️ Capstone Blueprint", key="chip_blueprint", use_container_width=True):
            prompt_to_trigger = "Architect my Capstone project idea: an AI Smart Campus Hub with MongoDB, Streamlit, and LLMs."
    with chip_col4:
        if st.button("📂 Explore Projects", key="chip_projects", use_container_width=True):
            prompt_to_trigger = "Search campus projects using Python and Docker to find reference architectures."

    # Load Past History from Database
    if "_agent_initialized" not in st.session_state or st.session_state.get("_agent_user") != username:
        raw_history = get_agent_history(username=username, session_id="default", limit=30)
        st.session_state["agent_messages"] = []
        for h in raw_history:
            st.session_state["agent_messages"].append({
                "role": h.get("role"),
                "content": h.get("content"),
                "tool_calls": h.get("tool_calls", [])
            })
        st.session_state["_agent_initialized"] = True
        st.session_state["_agent_user"] = username

    # Render Conversation Turns
    for msg in st.session_state.get("agent_messages", []):
        role = msg.get("role")
        avatar = "🎓" if role == "user" else "🤖"
        with st.chat_message(role, avatar=avatar):
            # Render Tool Call Trace if available
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                with st.expander(f"🛠️ Agent Reasoning Trace ({len(tool_calls)} autonomous actions)", expanded=False):
                    for idx, tc in enumerate(tool_calls, 1):
                        st.markdown(f"**Step {idx}:** _{tc.get('thought', 'Reasoning...')}_\n- **Tool:** `{tc.get('tool')}`\n- **Arguments:** `{json.dumps(tc.get('args', {}))}`")
            st.markdown(msg.get("content", ""))

    # Handle Prompt Submission (from chat input or quick prompt chip)
    user_input = st.chat_input("Ask CampusAI Advisor about skills, roadmaps, peer projects, or capstone architecture...")
    active_prompt = prompt_to_trigger or user_input

    if active_prompt:
        # Display and record user message
        st.session_state["agent_messages"].append({"role": "user", "content": active_prompt, "tool_calls": []})
        save_agent_message(
            username=username,
            role="user",
            content=active_prompt,
            tool_calls=[],
            session_id="default",
            user_id=current_user.get("id") if current_user else None
        )
        
        with st.chat_message("user", avatar="🎓"):
            st.markdown(active_prompt)

        # Run Agent ReAct Loop
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("CampusAI Agent is analyzing database records & reasoning..."):
                response_text, tool_calls = run_ai_agent(
                    user_prompt=active_prompt,
                    current_user=current_user,
                    api_key=api_key,
                    provider=provider,
                    model_name=model_name
                )
                
                if tool_calls:
                    with st.expander(f"🛠️ Agent Reasoning Trace ({len(tool_calls)} autonomous actions)", expanded=True):
                        for idx, tc in enumerate(tool_calls, 1):
                            st.markdown(f"**Step {idx}:** _{tc.get('thought', 'Reasoning...')}_\n- **Tool Executed:** `{tc.get('tool')}`\n- **Parameters:** `{json.dumps(tc.get('args', {}))}`")
                
                st.markdown(response_text)

        # Record assistant response
        st.session_state["agent_messages"].append({
            "role": "assistant",
            "content": response_text,
            "tool_calls": tool_calls
        })
        save_agent_message(
            username=username,
            role="assistant",
            content=response_text,
            tool_calls=tool_calls,
            session_id="default",
            user_id=current_user.get("id") if current_user else None
        )
        st.rerun()

    # Footer Controls
    st.markdown("<br>", unsafe_allow_html=True)
    f_col1, f_col2 = st.columns([6, 2])
    with f_col2:
        if st.button("🗑️ Clear Chat Memory", use_container_width=True):
            clear_agent_history(username=username, session_id="default")
            st.session_state["agent_messages"] = []
            st.success("Conversation history reset.")
            st.rerun()
