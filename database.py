import sqlite3
import os
import json
import hashlib
import hmac
import secrets
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "campus_hub.db")

def get_connection():
    """Returns a SQLite database connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# --- Password Security (PBKDF2-HMAC-SHA256) ---

def hash_password(password: str) -> str:
    """Hashes a password with a secure random salt using PBKDF2-HMAC-SHA256."""
    salt = secrets.token_bytes(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{pwd_hash.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plain-text password against a stored salt:hash string."""
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(expected_hash.hex(), hash_hex)
    except Exception:
        return False

# --- Database Initialization & Migrations ---

def init_db():
    """Initializes SQLite database tables and applies automatic column migrations."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Users Table (Capstone Authentication)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Projects Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            student_name TEXT NOT NULL,
            domain TEXT NOT NULL,
            tech_stack TEXT NOT NULL,
            description TEXT NOT NULL,
            github_url TEXT,
            demo_url TEXT,
            upvotes INTEGER DEFAULT 0,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # 3. Interview History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interview_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            role TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            question TEXT NOT NULL,
            user_answer TEXT NOT NULL,
            score INTEGER,
            strengths TEXT,
            gaps TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # 4. Resume Scans Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resume_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            filename TEXT NOT NULL,
            target_role TEXT,
            match_score INTEGER,
            matched_skills TEXT,
            missing_skills TEXT,
            recommendations TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # 5. Project Upvotes Table (Prevents multiple upvotes per user)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_upvotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, project_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()

    # --- Schema Migrations for Existing Tables ---
    def add_col_if_missing(table, column, col_type):
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [row["name"] for row in cursor.fetchall()]
        if column not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    add_col_if_missing("projects", "user_id", "INTEGER")
    add_col_if_missing("resume_scans", "user_id", "INTEGER")
    add_col_if_missing("resume_scans", "username", "TEXT")
    add_col_if_missing("interview_history", "user_id", "INTEGER")
    add_col_if_missing("interview_history", "username", "TEXT")
    conn.commit()

    # --- Seed Demo Users if empty ---
    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()["count"]
    if user_count == 0:
        demo_pwd_hash = hash_password("Campus@2026")
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        ''', ("student_demo", "student@campus.edu", demo_pwd_hash, "Alex Rivera (Demo Student)", "student"))
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        ''', ("recruiter_demo", "recruiter@techcorp.com", demo_pwd_hash, "Sarah Chen (Tech Recruiter)", "recruiter"))
        conn.commit()

    # --- Seed Initial Projects if empty ---
    cursor.execute("SELECT COUNT(*) as count FROM projects")
    row = cursor.fetchone()
    if row and row['count'] == 0:
        seed_projects = [
            (
                1,
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
                2,
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
                1,
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
                1,
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
                1,
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
            INSERT INTO projects (user_id, title, student_name, domain, tech_stack, description, github_url, demo_url, upvotes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', seed_projects)
        conn.commit()
    
    conn.close()

# --- User Authentication Operations ---

def create_user(username, email, password, full_name, role="student"):
    """Registers a new user account with hashed password."""
    clean_username = username.strip().lower()
    clean_email = email.strip().lower()
    clean_name = full_name.strip()

    if not clean_username or len(clean_username) < 3:
        return False, "Username must be at least 3 characters long.", None
    if not clean_email or "@" not in clean_email:
        return False, "Please enter a valid email address.", None
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long.", None
    if not clean_name:
        return False, "Full Name is required.", None

    conn = get_connection()
    cursor = conn.cursor()

    try:
        pwd_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        ''', (clean_username, clean_email, pwd_hash, clean_name, role))
        conn.commit()
        user_id = cursor.lastrowid
        cursor.execute("SELECT id, username, email, full_name, role, created_at FROM users WHERE id = ?", (user_id,))
        user = dict(cursor.fetchone())
        conn.close()
        return True, "Account registered successfully!", user
    except sqlite3.IntegrityError as e:
        conn.close()
        if "username" in str(e).lower():
            return False, f"Username '{clean_username}' is already taken.", None
        elif "email" in str(e).lower():
            return False, f"Email '{clean_email}' is already registered.", None
        return False, "An account with this username or email already exists.", None
    except Exception as e:
        conn.close()
        return False, f"Registration error: {e}", None

def authenticate_user(username_or_email, password):
    """Authenticates a user via username or email and verifies password."""
    clean_ident = username_or_email.strip().lower()
    if not clean_ident or not password:
        return False, "Please enter both username/email and password.", None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM users WHERE username = ? OR email = ?
    ''', (clean_ident, clean_ident))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False, "No account found with that username or email.", None

    if verify_password(password, row["password_hash"]):
        user_dict = {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "created_at": row["created_at"]
        }
        return True, "Login successful!", user_dict
    else:
        return False, "Incorrect password. Please try again.", None

def get_user_by_username(username):
    """Fetches user profile dict by username."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, created_at FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# --- CRUD Operations for Projects ---

def add_project(title, student_name, domain, tech_stack, description, github_url="", demo_url="", user_id=None):
    """Adds a new project to the database, optionally linked to a user_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO projects (user_id, title, student_name, domain, tech_stack, description, github_url, demo_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, title, student_name, domain, tech_stack, description, github_url, demo_url))
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

def toggle_project_upvote(user_id, project_id):
    """Toggles upvote for a user on a project (prevents duplicate voting). Returns (upvoted: bool, new_count: int)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if user already upvoted this project
    cursor.execute("SELECT id FROM project_upvotes WHERE user_id = ? AND project_id = ?", (user_id, project_id))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("DELETE FROM project_upvotes WHERE id = ?", (existing["id"],))
        cursor.execute("UPDATE projects SET upvotes = MAX(0, upvotes - 1) WHERE id = ?", (project_id,))
        upvoted = False
    else:
        cursor.execute("INSERT INTO project_upvotes (user_id, project_id) VALUES (?, ?)", (user_id, project_id))
        cursor.execute("UPDATE projects SET upvotes = upvotes + 1 WHERE id = ?", (project_id,))
        upvoted = True
        
    conn.commit()
    cursor.execute("SELECT upvotes FROM projects WHERE id = ?", (project_id,))
    res = cursor.fetchone()
    new_count = res["upvotes"] if res else 0
    conn.close()
    return upvoted, new_count

def has_user_upvoted(user_id, project_id):
    """Checks if a given user has upvoted a project."""
    if not user_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM project_upvotes WHERE user_id = ? AND project_id = ?", (user_id, project_id))
    row = cursor.fetchone()
    conn.close()
    return bool(row)

def upvote_project(project_id):
    """Legacy helper: increments upvote count for a given project."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET upvotes = upvotes + 1 WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

# --- User-Scoped Operations for Interview Logs ---

def save_interview_log(role, difficulty, question, user_answer, score, strengths, gaps, user_id=None, username=None):
    """Saves an interview Q&A evaluation entry linked to an optional user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO interview_history (user_id, username, role, difficulty, question, user_answer, score, strengths, gaps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, role, difficulty, question, user_answer, score, strengths, gaps))
    conn.commit()
    conn.close()

def get_interview_stats(username=None):
    """Gets aggregate stats for interview module (optionally scoped to a user)."""
    conn = get_connection()
    cursor = conn.cursor()
    if username:
        cursor.execute("SELECT COUNT(*) as total_interviews, AVG(score) as avg_score FROM interview_history WHERE username = ?", (username,))
    else:
        cursor.execute("SELECT COUNT(*) as total_interviews, AVG(score) as avg_score FROM interview_history")
    row = cursor.fetchone()
    conn.close()
    return {
        "total_interviews": row["total_interviews"] if row else 0,
        "avg_score": round(row["avg_score"], 1) if row and row["avg_score"] else 0
    }

def get_user_interview_history(username, limit=10):
    """Fetches recent interview question evaluations for a specific user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT role, difficulty, question, user_answer, score, strengths, gaps, timestamp
        FROM interview_history
        WHERE username = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (username, limit))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# --- User-Scoped Operations for Resume Scans ---

def save_resume_scan(filename, target_role, match_score, matched_skills, missing_skills, recommendations, user_id=None, username=None):
    """Saves a resume scan result linked to an optional user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO resume_scans (user_id, username, filename, target_role, match_score, matched_skills, missing_skills, recommendations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        username,
        filename,
        target_role,
        match_score,
        json.dumps(matched_skills) if isinstance(matched_skills, list) else matched_skills,
        json.dumps(missing_skills) if isinstance(missing_skills, list) else missing_skills,
        json.dumps(recommendations) if isinstance(recommendations, list) else recommendations
    ))
    conn.commit()
    conn.close()

def get_resume_stats(username=None):
    """Gets aggregate stats for resume scans (optionally scoped to a user)."""
    conn = get_connection()
    cursor = conn.cursor()
    if username:
        cursor.execute("SELECT COUNT(*) as total_scans, AVG(match_score) as avg_score FROM resume_scans WHERE username = ?", (username,))
    else:
        cursor.execute("SELECT COUNT(*) as total_scans, AVG(match_score) as avg_score FROM resume_scans")
    row = cursor.fetchone()
    conn.close()
    return {
        "total_scans": row["total_scans"] if row else 0,
        "avg_score": round(row["avg_score"], 1) if row and row["avg_score"] else 0
    }

def get_user_resume_scans(username, limit=10):
    """Fetches past resume scans for a specific user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT filename, target_role, match_score, matched_skills, missing_skills, recommendations, timestamp
        FROM resume_scans
        WHERE username = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (username, limit))
    rows = []
    for r in cursor.fetchall():
        d = dict(r)
        try:
            d["matched_skills"] = json.loads(d["matched_skills"]) if d["matched_skills"] else []
        except Exception:
            d["matched_skills"] = []
        try:
            d["missing_skills"] = json.loads(d["missing_skills"]) if d["missing_skills"] else []
        except Exception:
            d["missing_skills"] = []
        try:
            d["recommendations"] = json.loads(d["recommendations"]) if d["recommendations"] else []
        except Exception:
            d["recommendations"] = []
        rows.append(d)
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with Capstone Schema and Demo Users.")
