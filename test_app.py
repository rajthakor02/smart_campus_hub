import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from campus_db import (
    init_db,
    create_user,
    authenticate_user,
    get_projects,
    add_project,
    toggle_project_upvote,
    has_user_upvoted,
    save_interview_log,
    get_interview_stats,
    save_resume_scan,
    get_user_resume_scans,
    get_user_interview_history,
    save_agent_message,
    get_agent_history,
    clear_agent_history
)
from modules.resume_parser import fallback_resume_analyzer
from modules.mock_interview import evaluate_user_answer
from modules.ai_agent import (
    tool_inspect_user_skills,
    tool_inspect_interview_gaps,
    tool_search_campus_projects,
    tool_generate_milestone_roadmap,
    tool_generate_project_blueprint,
    run_ai_agent
)

def run_tests():
    print("--- Running Capstone Smart Campus Hub Verification Tests ---")
    
    # 1. Test Database Initialization & Relational Schemas
    init_db()
    projects = get_projects()
    print(f"[OK] Initial Seeded Projects Count: {len(projects)}")
    assert len(projects) >= 5, "Database seeding failed"

    # 2. Test User Authentication & Password Hashing
    test_uname = "capstone_tester"
    test_email = "tester@campus.edu"
    test_pwd = "SecurePass123!"

    # Create User
    ok, msg, user = create_user(
        username=test_uname,
        email=test_email,
        password=test_pwd,
        full_name="Capstone Tester",
        role="student"
    )
    if not ok and "already" in msg.lower():
        print(f"[OK] User '{test_uname}' already exists, proceeding to auth verification.")
    else:
        assert ok, f"User creation failed: {msg}"
        print(f"[OK] User created successfully: {user['username']}")

    # Authenticate User with Valid Password
    auth_ok, auth_msg, auth_user = authenticate_user(test_uname, test_pwd)
    assert auth_ok, f"Authentication failed: {auth_msg}"
    print(f"[OK] Authentication passed for '{auth_user['username']}'")

    # Authenticate User with Invalid Password
    bad_ok, bad_msg, _ = authenticate_user(test_uname, "WrongPassword!")
    assert not bad_ok, "Authentication should fail with wrong password"
    print(f"[OK] Invalid password rejection test passed")

    # 3. Test User-Specific Project Upvoting
    first_proj_id = projects[0]['id']
    user_id = auth_user['id']
    
    # Toggle upvote on
    upvoted, count_after_vote = toggle_project_upvote(user_id, first_proj_id)
    assert has_user_upvoted(user_id, first_proj_id) == upvoted
    print(f"[OK] Project upvote toggle test passed (Current state: {upvoted}, count: {count_after_vote})")

    # Toggle upvote off
    upvoted_off, count_after_unvote = toggle_project_upvote(user_id, first_proj_id)
    assert not upvoted_off
    print(f"[OK] Project un-vote toggle test passed (Count: {count_after_unvote})")

    # 4. Test User-Scoped Resume Scans
    save_resume_scan(
        filename="tester_resume.pdf",
        target_role="Full Stack Developer",
        match_score=85,
        matched_skills=["Python", "Streamlit", "SQLite"],
        missing_skills=["Docker", "Kubernetes"],
        recommendations=["Deploy on cloud container"],
        user_id=user_id,
        username=test_uname
    )
    user_scans = get_user_resume_scans(test_uname)
    assert len(user_scans) >= 1, "User resume scans not saved/retrieved"
    print(f"[OK] User-scoped resume scan verified: {user_scans[0]['filename']} ({user_scans[0]['match_score']}%)")

    # 5. Test User-Scoped Mock Interview History
    save_interview_log(
        role="Python Engineer",
        difficulty="Mid-Level",
        question="How does Python's GIL impact multithreading?",
        user_answer="The GIL prevents multiple native threads from executing Python bytecodes at once.",
        score=88,
        strengths="Clear explanation of GIL constraint.",
        gaps="Mention multiprocessing alternative.",
        user_id=user_id,
        username=test_uname
    )
    user_ivs = get_user_interview_history(test_uname)
    assert len(user_ivs) >= 1, "User interview history not retrieved"
    print(f"[OK] User-scoped interview log verified: {user_ivs[0]['role']} ({user_ivs[0]['score']}/100)")

    # 6. Test Resume Fallback Analyzer
    sample_resume = "Experienced Python developer with skills in Streamlit, SQL, PyTorch, and Data Structures."
    sample_jd = "Looking for a Python Developer with knowledge of Streamlit, SQL, Docker, and AWS."
    analysis = fallback_resume_analyzer(sample_resume, sample_jd)
    assert analysis['match_score'] > 0
    print(f"[OK] Resume heuristic scoring passed: {analysis['match_score']}%")

    # 7. Test AI Agent Tool Registry
    skills_data = tool_inspect_user_skills(test_uname)
    assert skills_data['status'] == 'success'
    assert 'Python' in skills_data['verified_skills']
    print(f"[OK] Agent Tool 1 (inspect_user_skills) passed: {len(skills_data['verified_skills'])} verified skills")

    iv_data = tool_inspect_interview_gaps(test_uname)
    assert iv_data['status'] == 'success'
    print(f"[OK] Agent Tool 2 (inspect_interview_gaps) passed: Avg Score {iv_data['average_score']}/100")

    proj_search = tool_search_campus_projects(query="Python")
    assert proj_search['status'] == 'success'
    print(f"[OK] Agent Tool 3 (search_campus_projects) passed: {proj_search['total_matches']} projects matched")

    roadmap = tool_generate_milestone_roadmap("Backend Engineer", weeks=4)
    assert roadmap['status'] == 'success' and len(roadmap['curriculum']) == 4
    print(f"[OK] Agent Tool 4 (generate_milestone_roadmap) passed: 4-week curriculum generated")

    blueprint = tool_generate_project_blueprint("Smart Campus Hub")
    assert blueprint['status'] == 'success' and 'suggested_tech_stack' in blueprint
    print(f"[OK] Agent Tool 5 (generate_project_blueprint) passed: {blueprint['project_title']}")

    # 8. Test Agent Conversation Persistence (MongoDB Atlas / SQLite)
    msg_id = save_agent_message(
        username=test_uname,
        role="assistant",
        content="Here is your tailored 4-week roadmap.",
        tool_calls=[{"tool": "tool_generate_milestone_roadmap", "args": {"role": "Backend Engineer"}}],
        session_id="test_session"
    )
    assert msg_id is not None
    history = get_agent_history(test_uname, session_id="test_session")
    assert len(history) >= 1
    assert history[0]['content'] == "Here is your tailored 4-week roadmap."
    print(f"[OK] Agent Conversation Persistence verified in database (ID: {msg_id})")
    clear_agent_history(test_uname, session_id="test_session")
    assert len(get_agent_history(test_uname, session_id="test_session")) == 0
    print("[OK] Agent Conversation Cleanup passed")

    # 9. Test ReAct Agent Execution Loop
    agent_resp, agent_trace = run_ai_agent(
        user_prompt="Audit my profile and find missing skills for a Backend role",
        current_user=auth_user
    )
    assert len(agent_resp) > 50
    assert len(agent_trace) >= 1
    print(f"[OK] Autonomous ReAct Agent Loop passed ({len(agent_trace)} tool actions executed)")

    print("\n[SUCCESS] ALL CAPSTONE DATABASE, AUTH & AI AGENT VERIFICATION TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
