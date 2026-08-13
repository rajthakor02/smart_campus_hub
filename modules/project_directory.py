import streamlit as st
from database import get_projects, add_project, upvote_project

def render_project_directory_page():
    """Renders the Student Project Showcase Directory module UI."""
    st.markdown("""
        <div class="module-header">
            <h2>🚀 Student Project Showcase Directory</h2>
            <p>Discover innovative campus engineering projects, star student repositories, filter by domain/tech stack, or submit your own project to gain visibility with top recruiters.</p>
        </div>
    """, unsafe_allow_html=True)

    # Filter and Search Row
    filter_col1, filter_col2, filter_col3 = st.columns([2, 3, 2])

    with filter_col1:
        domain_filter = st.selectbox(
            "Filter by Domain",
            ["All", "AI / Machine Learning", "Web Development", "IoT / Data Science", "NLP / AI", "Other Domain"]
        )

    with filter_col2:
        search_query = st.text_input("🔍 Search by Project Title, Tech Stack, or Author...", placeholder="e.g. PyTorch, Streamlit, Alex...")

    with filter_col3:
        st.write("")
        st.write("")
        show_add_form = st.checkbox("➕ Submit New Project", value=False)

    # Submission Form Expander / Modal
    if show_add_form:
        with st.form("new_project_form", clear_on_submit=True):
            st.subheader("📌 Register Your Student Project")
            
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                title = st.text_input("Project Title *", placeholder="e.g. NeuralVision Campus Navigation")
                student_name = st.text_input("Student Name & Department *", placeholder="e.g. Jane Doe (CS '25)")
                domain = st.selectbox("Primary Domain *", ["AI / Machine Learning", "Web Development", "IoT / Data Science", "NLP / AI", "Mobile App", "Cybersecurity", "Other Domain"])
            
            with p_col2:
                tech_stack = st.text_input("Tech Stack Tags (Comma separated) *", placeholder="e.g. Python, PyTorch, React, SQLite")
                github_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/username/project")
                demo_url = st.text_input("Live Demo URL", placeholder="https://myproject.streamlit.app")

            description = st.text_area("Detailed Description *", placeholder="Explain the problem solved, architecture, key features, and impact...")

            submitted = st.form_submit_button("🚀 Publish Project to Campus Hub", type="primary", use_container_width=True)

            if submitted:
                if not title or not student_name or not tech_stack or not description:
                    st.error("⚠️ Please fill in all required fields marked with *")
                else:
                    add_project(
                        title=title,
                        student_name=student_name,
                        domain=domain,
                        tech_stack=tech_stack,
                        description=description,
                        github_url=github_url,
                        demo_url=demo_url
                    )
                    st.success("🎉 Project published successfully to the directory!")
                    st.rerun()

    st.markdown("---")

    # Fetch projects from SQLite
    projects = get_projects(domain_filter=domain_filter, search_query=search_query)

    if not projects:
        st.info("ℹ️ No projects found matching your search or domain criteria. Try clearing filters or submit a new project!")
        return

    st.markdown(f"### 💡 Displaying {len(projects)} Campus Projects")

    # Render Project Cards in 2-column Grid
    for i in range(0, len(projects), 2):
        cols = st.columns(2, gap="large")
        
        for idx, col in enumerate(cols):
            if i + idx < len(projects):
                proj = projects[i + idx]
                with col:
                    # Format Tech Stack Badges
                    tech_list = [t.strip() for t in proj["tech_stack"].split(",") if t.strip()]
                    tech_html = "".join([f'<span class="skill-tag skill-matched" style="font-size: 0.78rem;">{t}</span>' for t in tech_list])

                    github_btn = f'<a href="{proj["github_url"]}" target="_blank" style="color: #3B82F6; text-decoration: none; font-size: 0.9rem; margin-right: 15px;">💻 GitHub Code</a>' if proj["github_url"] else ""
                    demo_btn = f'<a href="{proj["demo_url"]}" target="_blank" style="color: #10B981; text-decoration: none; font-size: 0.9rem;">🌐 Live Demo</a>' if proj["demo_url"] else ""

                    st.markdown(f"""
                        <div class="card-box" style="height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
                            <div>
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                    <h3 style="margin: 0; font-size: 1.15rem; color: #F8FAFC;">{proj["title"]}</h3>
                                    <span style="background-color: #334155; color: #94A3B8; font-size: 0.75rem; padding: 2px 8px; border-radius: 12px; white-space: nowrap;">
                                        {proj["domain"]}
                                    </span>
                                </div>
                                <p style="font-size: 0.85rem; color: #CBD5E1; margin-bottom: 12px;"><strong>By:</strong> {proj["student_name"]}</p>
                                <p style="font-size: 0.9rem; color: #94A3B8; line-height: 1.4; margin-bottom: 15px;">
                                    {proj["description"]}
                                </p>
                                <div style="margin-bottom: 15px;">
                                    {tech_html}
                                </div>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #334155; padding-top: 12px; margin-top: 10px;">
                                <div>
                                    {github_btn}
                                    {demo_btn}
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Upvote Button (handled via Streamlit state)
                    up_col1, up_col2 = st.columns([3, 1])
                    with up_col2:
                        if st.button(f"👍 {proj['upvotes']}", key=f"upvote_{proj['id']}", use_container_width=True):
                            upvote_project(proj['id'])
                            st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)
