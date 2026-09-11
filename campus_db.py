import os
import json
import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime

# Optional MongoDB driver imports
try:
    from pymongo import MongoClient
    import certifi
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False

# Auto-load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Configuration & Paths ---
DB_PATH = os.path.join(os.path.dirname(__file__), "campus_hub.db")

# Global MongoDB references
_mongo_client = None
_mongo_db = None
_IS_USING_MONGO = False

def get_mongo_uri() -> str:
    """Retrieves the MongoDB URI from environment variables or Streamlit secrets."""
    uri = os.getenv("MONGODB_URI", "").strip()
    if uri:
        return uri
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "MONGODB_URI" in st.secrets:
            return str(st.secrets["MONGODB_URI"]).strip()
    except Exception:
        pass
    return ""

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

# --- Database Connection Initializer ---

def get_mongo_db():
    """Attempts to connect to MongoDB Atlas if MONGODB_URI is provided."""
    global _mongo_client, _mongo_db, _IS_USING_MONGO
    if not HAS_PYMONGO:
        return None

    if _mongo_db is not None:
        return _mongo_db

    uri = get_mongo_uri()
    if not uri:
        return None

    try:
        ca_file = certifi.where() if 'certifi' in globals() else None
        _mongo_client = MongoClient(
            uri,
            tlsCAFile=ca_file,
            serverSelectionTimeoutMS=5000
        )
        # Verify connection
        _mongo_client.admin.command('ping')
        _mongo_db = _mongo_client["campus_hub"]
        _IS_USING_MONGO = True
        return _mongo_db
    except Exception as e:
        print(f"[MongoDB Warning] Connection to MongoDB Atlas failed: {e}. Falling back to SQLite.")
        _IS_USING_MONGO = False
        return None

def is_using_mongodb():
    """Returns True if the backend is currently connected to MongoDB Atlas."""
    if _mongo_db is None:
        get_mongo_db()
    return _IS_USING_MONGO

def get_sqlite_connection():
    """Returns a SQLite database connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# --- Default Seed Data ---

SEED_PROJECTS = [
    {
        "title": "Nexus AI: Intelligent Campus Event Matcher",
        "student_name": "Alex Rivera (CS '25)",
        "domain": "AI / Machine Learning",
        "tech_stack": "Python, PyTorch, Streamlit, Scikit-Learn, SQLite",
        "description": "A personalized event recommendation system utilizing collaborative filtering and LLM semantic embedding to connect students with campus hackathons, research talks, and career workshops.",
        "github_url": "https://github.com/alex-rivera/nexus-ai-campus",
        "demo_url": "https://nexus-campus-demo.streamlit.app",
        "upvotes": 42,
        "upvoted_by": []
    },
    {
        "title": "EcoCampus: IoT Energy & Carbon Tracker",
        "student_name": "Sarah Chen (ECE '24)",
        "domain": "IoT / Data Science",
        "tech_stack": "Python, Flask, MQTT, Pandas, Plotly, Raspberry Pi",
        "description": "Real-time campus dorm energy consumption dashboard powered by edge sensors. Monitors HVAC and lighting efficiency, gamifying energy conservation for campus residence halls.",
        "github_url": "https://github.com/sarahchen/eco-campus-iot",
        "demo_url": "https://ecocampus-live.org",
        "upvotes": 35,
        "upvoted_by": []
    },
    {
        "title": "AlgoMate: Peer-to-Peer Interview Simulator",
        "student_name": "David Kumar (SE '25)",
        "domain": "Web Development",
        "tech_stack": "Python, FastAPI, Streamlit, WebSockets, Docker",
        "description": "An open platform pairing students for mock coding interviews, featuring collaborative code editors, automated test case execution, and instant feedback reports.",
        "github_url": "https://github.com/dkumar/algomate-app",
        "demo_url": "https://algomate.dev",
        "upvotes": 29,
        "upvoted_by": []
    },
    {
        "title": "ResumePulse: Automated ATS Optimizer",
        "student_name": "Maya Patel (DS '26)",
        "domain": "NLP / AI",
        "tech_stack": "Python, pdfplumber, Gemini API, spaCy, Streamlit",
        "description": "Deep learning keyword extractor and ATS resume scorer designed specifically for campus recruitment, helping students format resumes for top tech firms.",
        "github_url": "https://github.com/mayapatel/resumepulse-ai",
        "demo_url": "https://resumepulse.streamlit.app",
        "upvotes": 58,
        "upvoted_by": []
    },
    {
        "title": "QuantumQuery: Academic Paper Summarizer",
        "student_name": "Liam Vance (Physics & CS '24)",
        "domain": "AI / NLP",
        "tech_stack": "Python, LangChain, OpenAI API, ChromaDB, Streamlit",
        "description": "RAG-based research assistant enabling students and professors to chat directly with multi-page ArXiv PDF papers, extracting equations, findings, and citations.",
        "github_url": "https://github.com/liamvance/quantum-query-rag",
        "demo_url": "https://quantumquery.demo.app",
        "upvotes": 50,
        "upvoted_by": []
    }
]

# --- Database Initialization & Seeding ---

def init_db():
    """Initializes backend database (MongoDB Atlas if configured, or SQLite)."""
    mongo_db = get_mongo_db()
    
    if mongo_db is not None:
        # Initialize MongoDB Collections & Indexes
        users_col = mongo_db["users"]
        projects_col = mongo_db["projects"]
        
        # Create unique indexes
        users_col.create_index("username", unique=True)
        users_col.create_index("email", unique=True)
        
        # Seed demo users in MongoDB if empty
        if users_col.count_documents({}) == 0:
            demo_pwd = hash_password("Campus@2026")
            users_col.insert_many([
                {
                    "username": "student_demo",
                    "email": "student@campus.edu",
                    "password_hash": demo_pwd,
                    "full_name": "Alex Rivera (Demo Student)",
                    "role": "student",
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "username": "recruiter_demo",
                    "email": "recruiter@techcorp.com",
                    "password_hash": demo_pwd,
                    "full_name": "Sarah Chen (Tech Recruiter)",
                    "role": "recruiter",
                    "created_at": datetime.utcnow().isoformat()
                }
            ])
            
        # Seed demo projects in MongoDB if empty
        if projects_col.count_documents({}) == 0:
            for p in SEED_PROJECTS:
                item = p.copy()
                item["date_added"] = datetime.utcnow().isoformat()
                projects_col.insert_one(item)
                
        print("[DB Engine] Successfully initialized with MongoDB Atlas Cloud backend!")
        return

    # Fallback to SQLite
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    
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

    # Apply SQLite column migrations
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

    # Seed SQLite demo users if empty
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] == 0:
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

    # Seed SQLite demo projects if empty
    cursor.execute("SELECT COUNT(*) as count FROM projects")
    if cursor.fetchone()["count"] == 0:
        seed_tuples = [
            (
                1,
                p["title"],
                p["student_name"],
                p["domain"],
                p["tech_stack"],
                p["description"],
                p["github_url"],
                p["demo_url"],
                p["upvotes"]
            )
            for p in SEED_PROJECTS
        ]
        cursor.executemany('''
            INSERT INTO projects (user_id, title, student_name, domain, tech_stack, description, github_url, demo_url, upvotes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', seed_tuples)
        conn.commit()
    
    conn.close()
    print("[DB Engine] Running on SQLite (Local Fallback). Set MONGODB_URI to connect to MongoDB Atlas Cloud.")

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

    pwd_hash = hash_password(password)
    mongo_db = get_mongo_db()

    # MongoDB Implementation
    if mongo_db is not None:
        users_col = mongo_db["users"]
        if users_col.find_one({"username": clean_username}):
            return False, f"Username '{clean_username}' is already taken.", None
        if users_col.find_one({"email": clean_email}):
            return False, f"Email '{clean_email}' is already registered.", None
            
        doc = {
            "username": clean_username,
            "email": clean_email,
            "password_hash": pwd_hash,
            "full_name": clean_name,
            "role": role,
            "created_at": datetime.utcnow().isoformat()
        }
        res = users_col.insert_one(doc)
        doc["id"] = str(res.inserted_id)
        return True, "Account registered successfully!", doc

    # SQLite Fallback Implementation
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    try:
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

    mongo_db = get_mongo_db()
    if mongo_db is not None:
        users_col = mongo_db["users"]
        user_doc = users_col.find_one({
            "$or": [{"username": clean_ident}, {"email": clean_ident}]
        })
        if not user_doc:
            return False, "No account found with that username or email.", None
        if verify_password(password, user_doc["password_hash"]):
            user_dict = {
                "id": str(user_doc["_id"]),
                "username": user_doc["username"],
                "email": user_doc["email"],
                "full_name": user_doc["full_name"],
                "role": user_doc.get("role", "student"),
                "created_at": user_doc.get("created_at", "")
            }
            return True, "Login successful!", user_dict
        else:
            return False, "Incorrect password. Please try again.", None

    # SQLite Implementation
    conn = get_sqlite_connection()
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
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        u = mongo_db["users"].find_one({"username": username})
        if u:
            u["id"] = str(u["_id"])
            return u
        return None

    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, created_at FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# --- CRUD Operations for Projects ---

def add_project(title, student_name, domain, tech_stack, description, github_url="", demo_url="", user_id=None):
    """Adds a new project to the database, optionally linked to a user_id."""
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        doc = {
            "user_id": str(user_id) if user_id else None,
            "title": title,
            "student_name": student_name,
            "domain": domain,
            "tech_stack": tech_stack,
            "description": description,
            "github_url": github_url,
            "demo_url": demo_url,
            "upvotes": 0,
            "upvoted_by": [],
            "date_added": datetime.utcnow().isoformat()
        }
        res = mongo_db["projects"].insert_one(doc)
        return str(res.inserted_id)

    conn = get_sqlite_connection()
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
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        query = {}
        if domain_filter and domain_filter != "All":
            query["domain"] = domain_filter
        if search_query:
            regex_pat = {"$regex": search_query, "$options": "i"}
            query["$or"] = [
                {"title": regex_pat},
                {"tech_stack": regex_pat},
                {"description": regex_pat},
                {"student_name": regex_pat}
            ]
        cursor = mongo_db["projects"].find(query).sort([("upvotes", -1), ("date_added", -1)])
        results = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            results.append(doc)
        return results

    conn = get_sqlite_connection()
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
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        from bson.objectid import ObjectId
        projects_col = mongo_db["projects"]
        uid_str = str(user_id)
        try:
            proj = projects_col.find_one({"_id": ObjectId(project_id)})
        except Exception:
            proj = projects_col.find_one({"id": project_id})
            
        if not proj:
            return False, 0
            
        upvoted_by = proj.get("upvoted_by", [])
        if uid_str in upvoted_by:
            projects_col.update_one(
                {"_id": proj["_id"]},
                {"$pull": {"upvoted_by": uid_str}, "$inc": {"upvotes": -1}}
            )
            upvoted = False
            new_count = max(0, proj.get("upvotes", 1) - 1)
        else:
            projects_col.update_one(
                {"_id": proj["_id"]},
                {"$addToSet": {"upvoted_by": uid_str}, "$inc": {"upvotes": 1}}
            )
            upvoted = True
            new_count = proj.get("upvotes", 0) + 1
        return upvoted, new_count

    conn = get_sqlite_connection()
    cursor = conn.cursor()
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
        
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        from bson.objectid import ObjectId
        projects_col = mongo_db["projects"]
        try:
            proj = projects_col.find_one({"_id": ObjectId(project_id)})
        except Exception:
            proj = projects_col.find_one({"id": project_id})
        if proj:
            return str(user_id) in proj.get("upvoted_by", [])
        return False

    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM project_upvotes WHERE user_id = ? AND project_id = ?", (user_id, project_id))
    row = cursor.fetchone()
    conn.close()
    return bool(row)

def upvote_project(project_id):
    """Legacy helper: increments upvote count for a given project."""
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        from bson.objectid import ObjectId
        try:
            mongo_db["projects"].update_one({"_id": ObjectId(project_id)}, {"$inc": {"upvotes": 1}})
        except Exception:
            mongo_db["projects"].update_one({"id": project_id}, {"$inc": {"upvotes": 1}})
        return

    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET upvotes = upvotes + 1 WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

# --- User-Scoped Operations for Interview Logs ---

def save_interview_log(role, difficulty, question, user_answer, score, strengths, gaps, user_id=None, username=None):
    """Saves an interview Q&A evaluation entry linked to an optional user."""
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        doc = {
            "user_id": str(user_id) if user_id else None,
            "username": username,
            "role": role,
            "difficulty": difficulty,
            "question": question,
            "user_answer": user_answer,
            "score": score,
            "strengths": strengths,
            "gaps": gaps,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        mongo_db["interview_history"].insert_one(doc)
        return

    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO interview_history (user_id, username, role, difficulty, question, user_answer, score, strengths, gaps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, role, difficulty, question, user_answer, score, strengths, gaps))
    conn.commit()
    conn.close()

def get_interview_stats(username=None):
    """Gets aggregate stats for interview module (optionally scoped to a user)."""
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        query = {"username": username} if username else {}
        iv_col = mongo_db["interview_history"]
        total = iv_col.count_documents(query)
        if total == 0:
            return {"total_interviews": 0, "avg_score": 0}
        
        pipeline = [{"$match": query}, {"$group": {"_id": None, "avg_score": {"$avg": "$score"}}}]
        agg = list(iv_col.aggregate(pipeline))
        avg_score = round(agg[0]["avg_score"], 1) if agg else 0
        return {"total_interviews": total, "avg_score": avg_score}

    conn = get_sqlite_connection()
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
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        cursor = mongo_db["interview_history"].find({"username": username}).sort("timestamp", -1).limit(limit)
        return list(cursor)

    conn = get_sqlite_connection()
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
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        doc = {
            "user_id": str(user_id) if user_id else None,
            "username": username,
            "filename": filename,
            "target_role": target_role,
            "match_score": match_score,
            "matched_skills": matched_skills if isinstance(matched_skills, list) else [],
            "missing_skills": missing_skills if isinstance(missing_skills, list) else [],
            "recommendations": recommendations if isinstance(recommendations, list) else [],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        mongo_db["resume_scans"].insert_one(doc)
        return

    conn = get_sqlite_connection()
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
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        query = {"username": username} if username else {}
        res_col = mongo_db["resume_scans"]
        total = res_col.count_documents(query)
        if total == 0:
            return {"total_scans": 0, "avg_score": 0}
        
        pipeline = [{"$match": query}, {"$group": {"_id": None, "avg_score": {"$avg": "$match_score"}}}]
        agg = list(res_col.aggregate(pipeline))
        avg_score = round(agg[0]["avg_score"], 1) if agg else 0
        return {"total_scans": total, "avg_score": avg_score}

    conn = get_sqlite_connection()
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
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        cursor = mongo_db["resume_scans"].find({"username": username}).sort("timestamp", -1).limit(limit)
        return list(cursor)

    conn = get_sqlite_connection()
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
    print(f"Backend initialized. MongoDB Active: {is_using_mongodb()}")
