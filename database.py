import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "campus_hub.db")

def get_connection():
    """Returns a SQLite database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite database tables and seeds initial project showcase data."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Projects Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            student_name TEXT NOT NULL,
            domain TEXT NOT NULL,
            tech_stack TEXT NOT NULL,
            description TEXT NOT NULL,
            github_url TEXT,
            demo_url TEXT,
            upvotes INTEGER DEFAULT 0,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Interview History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interview_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            question TEXT NOT NULL,
            user_answer TEXT NOT NULL,
            score INTEGER,
            strengths TEXT,
            gaps TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Resume Scans Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resume_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            target_role TEXT,
            match_score INTEGER,
            matched_skills TEXT,
            missing_skills TEXT,
            recommendations TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    # Seed initial projects if empty
    cursor.execute("SELECT COUNT(*) as count FROM projects")
    row = cursor.fetchone()
    if row and row['count'] == 0:
        seed_projects = [
            (
                "Nexus AI: Intelligent Campus Event Matcher",
                "Alex Rivera (CS '25)",
                "AI / Machine Learning",
                "Python, PyTorch, Streamlit, Scikit-Learn, SQLite",
                "A personalized event recommendation system utilizing collaborative filtering and LLM semantic embedding to connect students with campus hackathons, research talks, and career workshops.",
                "https://github.com/alex-rivera/nexus-ai-campus",
                "https://nexus-campus-demo.streamlit.app",
                42
            ),
            (
                "EcoCampus: IoT Energy & Carbon Tracker",
                "Sarah Chen (ECE '24)",
                "IoT / Data Science",
                "Python, Flask, MQTT, Pandas, Plotly, Raspberry Pi",
                "Real-time campus dorm energy consumption dashboard powered by edge sensors. Monitors HVAC and lighting efficiency, gamifying energy conservation for campus residence halls.",
                "https://github.com/sarahchen/eco-campus-iot",
                "https://ecocampus-live.org",
                35
            ),
            (
                "AlgoMate: Peer-to-Peer Interview Simulator",
                "David Kumar (SE '25)",
                "Web Development",
                "Python, FastAPI, Streamlit, WebSockets, Docker",
                "An open platform pairing students for mock coding interviews, featuring collaborative code editors, automated test case execution, and instant feedback reports.",
                "https://github.com/dkumar/algomate-app",
                "https://algomate.dev",
                29
            ),
            (
                "ResumePulse: Automated ATS Optimizer",
                "Maya Patel (DS '26)",
                "NLP / AI",
                "Python, pdfplumber, Gemini API, spaCy, Streamlit",
                "Deep learning keyword extractor and ATS resume scorer designed specifically for campus recruitment, helping students format resumes for top tech firms.",
                "https://github.com/mayapatel/resumepulse-ai",
                "https://resumepulse.streamlit.app",
                58
            ),
            (
                "QuantumQuery: Academic Paper Summarizer",
                "Liam Vance (Physics & CS '24)",
                "AI / NLP",
                "Python, LangChain, OpenAI API, ChromaDB, Streamlit",
                "RAG-based research assistant enabling students and professors to chat directly with multi-page ArXiv PDF papers, extracting equations, findings, and citations.",
                "https://github.com/liamvance/quantum-query-rag",
                "https://quantumquery.demo.app",
                50
            )
        ]
        cursor.executemany('''
            INSERT INTO projects (title, student_name, domain, tech_stack, description, github_url, demo_url, upvotes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', seed_projects)
        conn.commit()
    
    conn.close()

# --- CRUD Operations for Projects ---

def add_project(title, student_name, domain, tech_stack, description, github_url="", demo_url=""):
    """Adds a new project to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO projects (title, student_name, domain, tech_stack, description, github_url, demo_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title, student_name, domain, tech_stack, description, github_url, demo_url))
    conn.commit()
    project_id = cursor.lastrowid
    conn.close()
    return project_id

def get_projects(domain_filter="All", search_query=""):
    """Retrieves projects based on domain filter and search query, ordered by upvotes."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM projects WHERE 1=1"
    params = []
    
    if domain_filter and domain_filter != "All":
        query += " AND domain = ?"
        params.append(domain_filter)
        
    if search_query:
        query += " AND (title LIKE ? OR tech_stack LIKE ? OR description LIKE ? OR student_name LIKE ?)"
        search_pattern = f"%{search_query}%"
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
        
    query += " ORDER BY upvotes DESC, date_added DESC"
    
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def upvote_project(project_id):
    """Increments the upvote count for a given project."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET upvotes = upvotes + 1 WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

# --- CRUD Operations for Interview Logs ---

def save_interview_log(role, difficulty, question, user_answer, score, strengths, gaps):
    """Saves an interview Q&A evaluation entry."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO interview_history (role, difficulty, question, user_answer, score, strengths, gaps)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (role, difficulty, question, user_answer, score, strengths, gaps))
    conn.commit()
    conn.close()

def get_interview_stats():
    """Gets aggregate stats for interview module."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total_interviews, AVG(score) as avg_score FROM interview_history")
    row = cursor.fetchone()
    conn.close()
    return {
        "total_interviews": row["total_interviews"] if row else 0,
        "avg_score": round(row["avg_score"], 1) if row and row["avg_score"] else 0
    }

# --- CRUD Operations for Resume Scans ---

def save_resume_scan(filename, target_role, match_score, matched_skills, missing_skills, recommendations):
    """Saves a resume scan result."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO resume_scans (filename, target_role, match_score, matched_skills, missing_skills, recommendations)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        filename,
        target_role,
        match_score,
        json.dumps(matched_skills) if isinstance(matched_skills, list) else matched_skills,
        json.dumps(missing_skills) if isinstance(missing_skills, list) else missing_skills,
        json.dumps(recommendations) if isinstance(recommendations, list) else recommendations
    ))
    conn.commit()
    conn.close()

def get_resume_stats():
    """Gets aggregate stats for resume scans."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total_scans, AVG(match_score) as avg_score FROM resume_scans")
    row = cursor.fetchone()
    conn.close()
    return {
        "total_scans": row["total_scans"] if row else 0,
        "avg_score": round(row["avg_score"], 1) if row and row["avg_score"] else 0
    }

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
