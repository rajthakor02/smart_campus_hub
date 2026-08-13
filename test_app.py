import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_projects, add_project, upvote_project, save_interview_log, save_resume_scan
from modules.resume_parser import fallback_resume_analyzer
from modules.mock_interview import evaluate_user_answer

def run_tests():
    print("--- Running Smart Campus Hub Verification Tests ---")
    
    # 1. Test Database Initialization & CRUD
    init_db()
    projects = get_projects()
    print(f"[OK] Initial Seeded Projects Count: {len(projects)}")
    assert len(projects) >= 5, "Database seeding failed"
    
    first_proj_id = projects[0]['id']
    initial_upvotes = projects[0]['upvotes']
    upvote_project(first_proj_id)
    updated_projects = get_projects()
    print(f"[OK] Upvote Test Passed: ID {first_proj_id} upvotes went from {initial_upvotes} to {updated_projects[0]['upvotes']}")
    assert updated_projects[0]['upvotes'] == initial_upvotes + 1
    
    # Test Adding Project
    new_id = add_project(
        title="Automated Quantum Simulator",
        student_name="Tester Bot",
        domain="AI / Machine Learning",
        tech_stack="Python, Qiskit, Streamlit",
        description="A testing simulator for quantum circuits.",
        github_url="https://github.com/test/quantum",
        demo_url="https://quantum.demo"
    )
    print(f"[OK] New Project Added with ID: {new_id}")
    
    # 2. Test Resume Fallback Analyzer
    sample_resume = "Experienced Python developer with skills in Streamlit, SQL, PyTorch, and Data Structures."
    sample_jd = "Looking for a Python Developer with knowledge of Streamlit, SQL, Docker, and AWS."
    analysis = fallback_resume_analyzer(sample_resume, sample_jd)
    print(f"[OK] Resume Analysis Score: {analysis['match_score']}%")
    print(f"  Matched Skills: {analysis['matched_skills']}")
    print(f"  Missing Skills: {analysis['missing_skills']}")
    assert analysis['match_score'] > 0
    assert "Python" in [s.capitalize() for s in analysis['matched_skills']]
    
    # 3. Test Mock Interview Evaluator
    eval_res = evaluate_user_answer(
        role="Python Engineer",
        difficulty="Mid-Level Engineer",
        question="How do you handle database connections in Streamlit?",
        user_answer="I use st.cache_resource to cache the sqlite connection object so it isn't recreated on every rerun."
    )
    print(f"[OK] Interview Eval Score: {eval_res['score']}/100")
    print(f"  Strengths: {eval_res['strengths']}")
    assert eval_res['score'] >= 50

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
