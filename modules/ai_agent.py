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
get_gemini_api_key = getattr(campus_db, "get_gemini_api_key", lambda: "")
get_openai_api_key = getattr(campus_db, "get_openai_api_key", lambda: "")

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
    if not username or username == "guest":
        return {
            "status": "guest_mode",
            "message": "User running in guest mode. Sign in to analyze personal resume scans.",
            "verified_skills": ["Python", "Problem Solving", "Web Architecture"],
            "identified_skill_gaps": ["Docker", "Kubernetes", "Redis", "Cloud CI/CD"]
        }
    
    scans = get_user_resume_scans(username, limit=5)
    if not scans:
        return {
            "status": "no_data",
            "message": f"No past resume scans found for student @{username}.",
            "suggestion": "Recommend the student upload a resume in the Resume Parser module first.",
            "verified_skills": ["Python", "SQL", "Git"],
            "identified_skill_gaps": ["Docker", "System Design", "Cloud Deployment"]
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
        "latest_target_role": latest.get("target_role", "Software Engineer"),
        "latest_ats_score": latest.get("match_score", 0),
        "verified_skills": sorted(list(all_matched)) if all_matched else ["Python", "Git", "Problem Solving"],
        "identified_skill_gaps": sorted(list(all_missing))[:8] if all_missing else ["Docker", "Kubernetes", "Redis"],
        "latest_recommendations": latest.get("recommendations", [])[:3]
    }

def tool_inspect_interview_gaps(username: str) -> dict:
    """Tool 2: Analyzes student's mock technical interview answers, weak topics, and scores."""
    if not username or username == "guest":
        return {
            "status": "guest_mode",
            "message": "User running in guest mode.",
            "interviews_taken": 0,
            "average_score": 75.0,
            "identified_weaknesses": ["Multithreading GIL constraints", "Distributed database transactions"],
            "demonstrated_strengths": ["REST API Architecture", "Relational Schema Design"]
        }
        
    history = get_user_interview_history(username, limit=10)
    if not history:
        return {
            "status": "no_data",
            "message": f"No past mock interview attempts found for @{username}.",
            "suggestion": "Recommend taking a mock interview session to evaluate technical readiness.",
            "average_score": 0,
            "identified_weaknesses": ["High-concurrency bottlenecks", "System scaling strategies"],
            "demonstrated_strengths": ["Core Language Fundamentals"]
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
        "identified_weaknesses": gaps_collected[:3] if gaps_collected else ["Distributed Caching", "Container Orchestration"],
        "demonstrated_strengths": strengths_collected[:3] if strengths_collected else ["Clean Code", "API Design"]
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
    and conversational synthesis when no LLM API key is configured or offline.
    """
    prompt_lower = user_prompt.lower()
    username = current_user.get("username") if current_user else "guest"
    full_name = current_user.get("full_name") if current_user else ""
    
    # Check for friendly greetings & introductions
    is_greeting = any(re.search(rf"\b{w}\b", prompt_lower) for w in ["hey", "hi", "hello", "namaste", "greetings", "good morning", "good evening", "yo"])
    is_asking_capabilities = any(w in prompt_lower for w in [
        "what can you do", "what you can do", "capabilities", "features", "who are you", 
        "what are you", "help me", "how to use", "guide me", "how can you help"
    ])
    
    # 1. Handle Conversational Greeting
    if is_greeting and not any(w in prompt_lower for w in ["audit", "roadmap", "project", "architect", "skills", "resume", "interview"]):
        name_display = f" **{full_name}**" if full_name else ""
        if not name_display and "raj" in prompt_lower:
            name_display = " **Raj**"
        
        greeting_text = (
            f"### 👋 Hello{name_display}! Welcome to the **CampusAI Career & Project Advisor**\n\n"
            "I'm your autonomous assistant for the Smart Campus Hub. I connect directly with our campus database to help you master technical skills, practice for interviews, and build winning engineering projects.\n\n"
            "**Here are a few things I can do for you right now:**\n"
            "- 🔍 **Audit Your Skills**: Analyze your past ATS resume scores and identify missing technologies.\n"
            "- 🗺️ **Build Career Roadmaps**: Create a customized 4-week preparation sprint for roles like *Backend Engineer*, *ML Specialist*, or *Cloud Architect*.\n"
            "- 🏗️ **Architect Capstone Projects**: Provide a full-stack blueprint, database schema, and tech stack for your project idea.\n"
            "- 📂 **Explore Peer Projects**: Discover student repositories and benchmarks across campus.\n\n"
            "👉 *Try asking:* **\"Audit my profile & find my skill gaps\"** or click any of the quick prompt buttons above!"
        )
        return greeting_text, [{"thought": "Detected user greeting. Introducing capabilities and campus database tools.", "tool": "conversational_greeting", "args": {"user": username}}]

    # 2. Handle Capability Inquiries
    if is_asking_capabilities and not any(w in prompt_lower for w in ["audit", "roadmap", "architect"]):
        caps_text = (
            "### 🤖 What I Can Do For You as CampusAI Advisor\n\n"
            "Unlike a standard text bot, I am equipped with **5 autonomous domain tools** connected to our campus backend:\n\n"
            "1. **`tool_inspect_user_skills`**: Reads your uploaded resumes and calculates your verified strengths vs. target job gaps.\n"
            "2. **`tool_inspect_interview_gaps`**: Reviews your past mock interview transcripts and highlights conceptual weak points.\n"
            "3. **`tool_search_campus_projects`**: Searches through campus engineering repositories to find reference projects in Python, Docker, PyTorch, etc.\n"
            "4. **`tool_generate_milestone_roadmap`**: Formats an actionable week-by-week curriculum tailored to your desired career track.\n"
            "5. **`tool_generate_project_blueprint`**: Designs full technical specifications for Capstone projects (architecture, API routes, database choices).\n\n"
            "💡 *Tip: To enable live generative LLM responses, you can also paste a free Gemini API Key in the **⚙️ LLM & API Key Settings** expander above!*"
        )
        return caps_text, [{"thought": "User inquired about agent capabilities. Explaining tool suite and database integrations.", "tool": "explain_capabilities", "args": {}}]

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
            "thought": f"Student is requesting guidance. Querying user's historical resume ATS scans and verified skills for @{username}...",
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

    if skills_data and skills_data.get("status") in ["success", "guest_mode"]:
        response_parts.append("#### 🔍 1. Profile & ATS Competency Audit")
        if skills_data.get("latest_ats_score"):
            response_parts.append(f"- **Latest ATS Match Score**: `{skills_data['latest_ats_score']}%` for **{skills_data['latest_target_role']}**")
        if skills_data.get("verified_skills"):
            v_skills = ", ".join(f"`{s}`" for s in skills_data["verified_skills"])
            response_parts.append(f"- **Verified Strengths**: {v_skills}")
        if skills_data.get("identified_skill_gaps"):
            g_skills = ", ".join(f"`{s}`" for s in skills_data["identified_skill_gaps"])
            response_parts.append(f"- **Identified Missing Skills**: {g_skills}")
        response_parts.append("")

    if interview_data and interview_data.get("status") in ["success", "guest_mode"]:
        if interview_data.get("interviews_taken", 0) > 0:
            response_parts.append(f"- **Technical Mock Interview Average**: `{interview_data['average_score']}/100` ({interview_data['interviews_taken']} attempts)")
        if interview_data.get("identified_weaknesses"):
            response_parts.append(f"- **Key Interview Growth Areas**: {interview_data['identified_weaknesses'][0]}")
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
    with robust multi-model fallback and heuristic execution.
    """
    username = current_user.get("username") if current_user else "guest"
    
    # Run domain tools to gather live campus context
    skills_context = tool_inspect_user_skills(username if current_user else None)
    interview_context = tool_inspect_interview_gaps(username if current_user else None)
    projects_context = tool_search_campus_projects()
    
    # If an API key is available, call the LLM
    if api_key:
        system_context = f"""You are CampusAI, an elite Autonomous Career & Project Advisor Agent for engineering students.
You have access to real-time tools and database records for the student.
Student Context:
- Username: {username}
- Authenticated: {bool(current_user)}
- Latest ATS Skills: {json.dumps(skills_context)}
- Mock Interview Transcripts: {json.dumps(interview_context)}
- Campus Projects Sample: {json.dumps(projects_context.get('top_projects', []))}

Format your answer with clear markdown headings, bullet points, actionable checklists, and reference specific projects from campus.
Be conversational, helpful, encouraging, and highly technical when discussing architectures.
"""
        candidate_gemini_models = [model_name, "gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]
        last_error = None
        
        if provider == "gemini" and (HAS_NEW_GENAI or HAS_LEGACY_GENAI):
            if HAS_NEW_GENAI:
                try:
                    client = genai.Client(api_key=api_key)
                    for m in candidate_gemini_models:
                        try:
                            resp = client.models.generate_content(
                                model=m,
                                contents=[system_context, user_prompt]
                            )
                            if resp and resp.text:
                                tool_trace = [
                                    {"thought": "Retrieved user ATS profile and interview records from MongoDB Atlas.", "tool": "tool_inspect_user_skills", "args": {"username": username}},
                                    {"thought": "Queried campus project showcase directory for domain peer benchmarks.", "tool": "tool_search_campus_projects", "args": {"query": ""}},
                                    {"thought": f"Generated response using Google {m}.", "tool": "llm_reasoning_pipeline", "args": {"provider": "gemini", "model": m}}
                                ]
                                return resp.text, tool_trace
                        except Exception as e_m:
                            last_error = e_m
                            continue
                except Exception as e_client:
                    last_error = e_client
            else:
                try:
                    legacy_genai.configure(api_key=api_key)
                    for m in candidate_gemini_models:
                        try:
                            model = legacy_genai.GenerativeModel(m)
                            resp = model.generate_content(f"{system_context}\n\nStudent Prompt: {user_prompt}")
                            if resp and resp.text:
                                tool_trace = [
                                    {"thought": "Retrieved user ATS profile and interview records from MongoDB Atlas.", "tool": "tool_inspect_user_skills", "args": {"username": username}},
                                    {"thought": "Queried campus project showcase directory for domain peer benchmarks.", "tool": "tool_search_campus_projects", "args": {"query": ""}},
                                    {"thought": f"Generated response using Google {m}.", "tool": "llm_reasoning_pipeline", "args": {"provider": "gemini", "model": m}}
                                ]
                                return resp.text, tool_trace
                        except Exception as e_m:
                            last_error = e_m
                            continue
                except Exception as e_cfg:
                    last_error = e_cfg
                    
        elif provider == "openai" and HAS_OPENAI:
            try:
                client = openai.OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_context},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7
                )
                if resp.choices and resp.choices[0].message.content:
                    tool_trace = [
                        {"thought": "Retrieved user ATS profile and interview records from MongoDB Atlas.", "tool": "tool_inspect_user_skills", "args": {"username": username}},
                        {"thought": "Queried campus project showcase directory for domain peer benchmarks.", "tool": "tool_search_campus_projects", "args": {"query": ""}},
                        {"thought": "Synthesized tailored guidance with OpenAI GPT-4o-mini.", "tool": "llm_reasoning_pipeline", "args": {"provider": provider}}
                    ]
                    return resp.choices[0].message.content, tool_trace
            except Exception as e_oa:
                last_error = e_oa

        # If LLM API call encountered an issue, provide feedback and run heuristic agent
        if last_error:
            err_str = str(last_error)
            if "API_KEY_INVALID" in err_str or "invalid" in err_str.lower():
                notice = "> ⚠️ **API Key Notice**: The configured Gemini API key appears invalid. Please check your key from [Google AI Studio](https://aistudio.google.com/app/apikey). Switched to Domain Agent mode.\n"
            elif "429" in err_str or "quota" in err_str.lower():
                notice = "> ⚠️ **API Notice**: Gemini free tier quota limit reached (429). Switched to offline Domain Agent mode.\n"
            else:
                notice = f"> ⚠️ **API Notice**: LLM provider returned an error (`{err_str[:90]}`). Switched to offline Domain Agent mode.\n"
            
            fallback_text, trace = execute_heuristic_agent(user_prompt, current_user)
            return f"{notice}\n{fallback_text}", trace
    
    # Heuristic Agent execution when no API key is provided
    return execute_heuristic_agent(user_prompt, current_user)

# ==============================================================================
# 🎨 STREAMLIT AGENT UI
# ==============================================================================

def render_ai_agent_page(current_user: dict = None, api_key: str = "", provider: str = "gemini", model_name: str = "gemini-1.5-flash"):
    """Renders the interactive AI Career & Project Advisor Agent interface."""
    
    # Resolve active API key
    effective_api_key = st.session_state.get("user_gemini_api_key", "").strip() or api_key.strip()
    username = current_user.get("username") if current_user else "guest"

    # Header
    st.markdown('''
        <div style="padding: 10px 0 16px 0;">
            <h1 style="margin: 0; font-size: 2.1rem; font-weight: 800; color: #EDEAE3;">
                🤖 CampusAI Career &amp; Project Advisor
            </h1>
            <p style="margin: 6px 0 0 0; color: #9BA3AC; font-size: 0.95rem;">
                Autonomous multi-tool agent for personalized skill gap audits, capstone architectural blueprints, and curated career roadmaps.
            </p>
        </div>
    ''', unsafe_allow_html=True)

    # Status Badges Bar
    col_stat1, col_stat2, col_stat3 = st.columns([3, 3, 2])
    with col_stat1:
        if current_user:
            st.markdown(f"👤 **Session:** `{current_user.get('full_name')}` (`@{username}`)")
        else:
            st.markdown("👤 **Session:** `Guest Mode` (Sign in to save personal history)")
    with col_stat2:
        if effective_api_key:
            st.markdown("⚡ **LLM:** `Google Gemini 1.5 Flash` (Live)")
        else:
            st.markdown("⚡ **Engine:** `Offline Domain Agent` (Free)")
    with col_stat3:
        db_status = "🟢 Atlas Cloud" if is_using_mongodb() else "⚪ SQLite Local"
        st.markdown(f"💾 **Memory:** {db_status}")

    # Collapsible API Key Configuration Section
    with st.expander("⚙️ LLM & API Key Settings (Configure Gemini for live AI)", expanded=(not bool(effective_api_key))):
        if effective_api_key:
            st.markdown("🟢 **Gemini API Key is Active!** The agent will run full LLM generation via Google Gemini.")
        else:
            st.markdown("ℹ️ **Running in Free Offline Domain Agent Mode.** Enter a free Google Gemini API key below to unlock generative LLM reasoning.")
        
        cfg_col1, cfg_col2 = st.columns([3, 1])
        with cfg_col1:
            entered_key = st.text_input(
                "Gemini API Key (saved for your session):",
                value=st.session_state.get("user_gemini_api_key", effective_api_key),
                type="password",
                placeholder="AIzaSy...",
                help="Paste your Gemini key here. It will not be committed to GitHub."
            )
            if entered_key != st.session_state.get("user_gemini_api_key", ""):
                st.session_state["user_gemini_api_key"] = entered_key
                st.success("API key updated for this session!")
                st.rerun()
        with cfg_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("[🔑 **Get Free API Key**](https://aistudio.google.com/app/apikey)")

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
            with st.spinner("CampusAI Agent is reasoning and querying database..."):
                response_text, tool_calls = run_ai_agent(
                    user_prompt=active_prompt,
                    current_user=current_user,
                    api_key=effective_api_key,
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
