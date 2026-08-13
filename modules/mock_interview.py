import streamlit as st
import time
import json
import re

# Import LLM clients safely
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

from database import save_interview_log, get_interview_stats

def init_interview_state():
    """Initializes session state variables for mock interview module."""
    if "interview_messages" not in st.session_state:
        st.session_state.interview_messages = []
    if "interview_started" not in st.session_state:
        st.session_state.interview_started = False
    if "current_question_num" not in st.session_state:
        st.session_state.current_question_num = 0
    if "last_eval" not in st.session_state:
        st.session_state.last_eval = None

def generate_llm_stream(prompt, system_instruction, provider="gemini", api_key=None, model_name=None):
    """Generator function yielding text chunks for st.write_stream."""
    
    if provider == "gemini" and api_key:
        if HAS_NEW_GENAI:
            try:
                client = genai.Client(api_key=api_key)
                selected_model = model_name or "gemini-2.5-flash"
                response = client.models.generate_content_stream(
                    model=selected_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction
                    )
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                pass
                
        if HAS_LEGACY_GENAI:
            try:
                legacy_genai.configure(api_key=api_key)
                selected_model = model_name or "gemini-1.5-flash"
                model = legacy_genai.GenerativeModel(selected_model, system_instruction=system_instruction)
                response = model.generate_content(prompt, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                yield f"\n*(Gemini API connection error: {e}. Switching to simulated interviewer)*\n"
            
    elif provider == "openai" and api_key and HAS_OPENAI:
        try:
            client = openai.OpenAI(api_key=api_key)
            selected_model = model_name or "gpt-4o-mini"
            stream = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            yield f"\n*(OpenAI API connection error: {e}. Switching to simulated interviewer)*\n"

    # Fallback simulated response stream
    simulated_responses = [
        "Welcome to the technical interview! Let's start with a core concept: Can you explain how you design a scalable REST API in Python, and how you handle authentication and database connection pooling?",
        "That's a solid explanation. Following up on that: How would you optimize SQL query performance when dealing with tables containing millions of records?",
        "Great insights! Moving to system architecture: If your service experiences a sudden 10x traffic spike, what caching and load balancing strategies would you deploy first?",
        "Excellent response. Let's do a practical scenario: Describe a challenging bug you encountered in a recent campus or personal project, and walk me through your step-by-step debugging process."
    ]
    
    idx = min(st.session_state.current_question_num, len(simulated_responses) - 1)
    text_to_stream = simulated_responses[idx]
    for word in text_to_stream.split(" "):
        yield word + " "
        time.sleep(0.04)

def evaluate_user_answer(role, difficulty, question, user_answer, provider="gemini", api_key=None, model_name=None):
    """Evaluates user's answer and returns structured evaluation dict."""
    eval_prompt = f"""
You are an expert Senior Technical Interviewer evaluating a candidate answer.

Target Role: {role}
Difficulty Level: {difficulty}
Interviewer Question: {question}
Candidate Answer: {user_answer}

Provide a strict JSON response (no markdown fences) evaluating the candidate:
{{
    "score": <integer score from 0 to 100>,
    "strengths": "<Key positive aspects of candidate response>",
    "gaps": "<Missing technical points or room for improvement>",
    "ideal_snippet": "<1-2 sentence recommendation or concise ideal answer hint>"
}}
"""

    if provider == "gemini" and api_key:
        if HAS_NEW_GENAI:
            try:
                client = genai.Client(api_key=api_key)
                selected_model = model_name or "gemini-2.5-flash"
                res = client.models.generate_content(
                    model=selected_model,
                    contents=eval_prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                return parse_eval_json(res.text)
            except Exception:
                pass

        if HAS_LEGACY_GENAI:
            try:
                legacy_genai.configure(api_key=api_key)
                selected_model = model_name or "gemini-1.5-flash"
                model = legacy_genai.GenerativeModel(selected_model, generation_config={"response_mime_type": "application/json"})
                res = model.generate_content(eval_prompt)
                return parse_eval_json(res.text)
            except Exception:
                pass
            
    elif provider == "openai" and api_key and HAS_OPENAI:
        try:
            client = openai.OpenAI(api_key=api_key)
            selected_model = model_name or "gpt-4o-mini"
            res = client.chat.completions.create(
                model=selected_model,
                messages=[{"role": "user", "content": eval_prompt}],
                response_format={"type": "json_object"}
            )
            return parse_eval_json(res.choices[0].message.content)
        except Exception:
            pass

    # Heuristic evaluation fallback
    ans_length = len(user_answer.split())
    if ans_length > 40:
        score = 88
        strengths = "Detailed response showing good technical context and articulation."
        gaps = "Could include specific metrics or architectural trade-offs."
        ideal_snippet = "Structure answers using STAR format (Situation, Task, Action, Result) with precise metrics."
    elif ans_length > 15:
        score = 75
        strengths = "Direct answer addressing the core concept."
        gaps = "Lacks deep technical elaboration or edge-case handling."
        ideal_snippet = "Elaborate further on concurrency, scaling, or framework internals."
    else:
        score = 55
        strengths = "Attempted answer."
        gaps = "Response is very brief; missing key architectural details and examples."
        ideal_snippet = "Provide detailed examples and step-by-step logic."

    return {
        "score": score,
        "strengths": strengths,
        "gaps": gaps,
        "ideal_snippet": ideal_snippet
    }

def parse_eval_json(text):
    """Clean markdown formatting and parse evaluation JSON."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        return {
            "score": 80,
            "strengths": "Clear communication and relevant concepts.",
            "gaps": "Could dive deeper into system trade-offs.",
            "ideal_snippet": "Mention specific tools, benchmarks, and performance considerations."
        }

def render_mock_interview_page(api_key, provider, model_name):
    """Renders the AI Mock Interviewer module UI."""
    init_interview_state()

    st.markdown("""
        <div class="module-header">
            <h2>🎙️ Interactive AI Mock Technical Interviewer</h2>
            <p>Practice real-time technical interviews tailored to your target role and experience level. Receive instant streaming questions and live feedback cards after every response.</p>
        </div>
    """, unsafe_allow_html=True)

    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([2, 2, 2, 1])

    with ctrl_col1:
        role = st.selectbox(
            "Target Role",
            ["Python Software Engineer", "AI / Machine Learning Engineer", "Data Scientist", "Full Stack Developer", "DevOps & Cloud Engineer", "Product Manager"],
            key="interview_role"
        )

    with ctrl_col2:
        difficulty = st.selectbox(
            "Difficulty Level",
            ["Junior / Internship", "Mid-Level Engineer", "Senior / Tech Lead"],
            key="interview_diff"
        )

    with ctrl_col3:
        stats = get_interview_stats()
        st.metric("Total Practice Qs", stats["total_interviews"], delta=f"Avg Score: {stats['avg_score']}%" if stats['avg_score'] else "New Session")

    with ctrl_col4:
        st.write("")
        st.write("")
        if st.button("🔄 Reset Chat", type="secondary", use_container_width=True):
            st.session_state.interview_messages = []
            st.session_state.interview_started = False
            st.session_state.current_question_num = 0
            st.session_state.last_eval = None
            st.rerun()

    st.markdown("---")

    if not st.session_state.interview_started:
        st.info("👋 Click below to initialize your AI interviewer and receive your first technical question.")
        if st.button("🚀 Start Interview", type="primary", use_container_width=True):
            st.session_state.interview_started = True
            
            system_instruction = f"You are a Senior Technical Interviewer conducting an interview for a {role} at difficulty {difficulty}. Ask one precise, challenging question at a time. Keep tone professional yet encouraging."
            initial_prompt = f"Greet the candidate for the {role} ({difficulty}) position and ask the very first interview question."
            
            with st.chat_message("assistant", avatar="🤖"):
                full_res = st.write_stream(
                    generate_llm_stream(
                        prompt=initial_prompt,
                        system_instruction=system_instruction,
                        provider=provider,
                        api_key=api_key,
                        model_name=model_name
                    )
                )
            
            st.session_state.interview_messages.append({"role": "assistant", "content": full_res})
            st.rerun()
        return

    for msg in st.session_state.interview_messages:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    if st.session_state.last_eval:
        ev = st.session_state.last_eval
        score = ev.get("score", 75)
        badge_color = "#10B981" if score >= 80 else ("#F59E0B" if score >= 60 else "#EF4444")
        
        st.markdown(f"""
            <div class="card-box" style="border: 1px solid {badge_color}; background-color: rgba(30, 41, 59, 0.7); margin-top: 15px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h4 style="margin: 0; color: #F8FAFC;">💡 Instant Answer Evaluation</h4>
                    <span style="background-color: {badge_color}; color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-weight: bold;">
                        Score: {score}/100
                    </span>
                </div>
                <p><strong>✅ Key Strengths:</strong> {ev.get('strengths')}</p>
                <p><strong>⚠️ Improvement Opportunities:</strong> {ev.get('gaps')}</p>
                <p><strong>✨ Ideal Answer Tip:</strong> <em>{ev.get('ideal_snippet')}</em></p>
            </div>
        """, unsafe_allow_html=True)

    user_input = st.chat_input("Type your response to the interviewer...")

    if user_input:
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        st.session_state.interview_messages.append({"role": "user", "content": user_input})

        last_question = "Technical Interview Question"
        for m in reversed(st.session_state.interview_messages):
            if m["role"] == "assistant":
                last_question = m["content"]
                break

        with st.spinner("⚡ AI Recruiter evaluating response..."):
            eval_res = evaluate_user_answer(
                role=role,
                difficulty=difficulty,
                question=last_question,
                user_answer=user_input,
                provider=provider,
                api_key=api_key,
                model_name=model_name
            )
            st.session_state.last_eval = eval_res
            
            save_interview_log(
                role=role,
                difficulty=difficulty,
                question=last_question,
                user_answer=user_input,
                score=eval_res.get("score", 75),
                strengths=eval_res.get("strengths", ""),
                gaps=eval_res.get("gaps", "")
            )

        st.session_state.current_question_num += 1

        next_prompt = f"Candidate answered: '{user_input}'. Briefly acknowledge response and ask question #{st.session_state.current_question_num + 1} for {role} role."
        system_instruction = f"You are a Senior Technical Interviewer. Keep follow-up questions realistic and progressive."

        with st.chat_message("assistant", avatar="🤖"):
            full_next_res = st.write_stream(
                generate_llm_stream(
                    prompt=next_prompt,
                    system_instruction=system_instruction,
                    provider=provider,
                    api_key=api_key,
                    model_name=model_name
                )
            )

        st.session_state.interview_messages.append({"role": "assistant", "content": full_next_res})
        st.rerun()
