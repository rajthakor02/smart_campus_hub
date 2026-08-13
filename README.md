# 🎓 AI-Powered Smart Campus & Career Hub

A 100% pure Python web application built using **Streamlit**, **SQLite**, **pdfplumber**, and **Google Gemini / OpenAI APIs**.

---

## 🌟 Key Features

1. **📄 AI Resume Parser & Job Matcher**: Upload PDF resumes, extract skills with `pdfplumber`, compare against target Job Descriptions, and view ATS compatibility scores and missing skill gaps.
2. **🎙️ Interactive AI Mock Interviewer**: Practice real-time technical interviews with streaming AI responses (`st.write_stream`) and instant answer evaluation cards.
3. **🚀 Student Project Showcase Directory**: Grid showcase of student projects with domain filtering, upvotes, and project submission forms.

---

## 🚀 Live Deployment Guide (Streamlit Community Cloud - FREE)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Smart Campus Hub"
   git remote add origin https://github.com/YOUR_USERNAME/smart-campus-hub.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Community Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
   - Click **"New app"**.
   - Select your repository (`YOUR_USERNAME/smart-campus-hub`), branch (`main`), and set Main file path to `app.py`.
   - Click **Deploy!** Your app will be live at `https://<your-app-name>.streamlit.app`.

3. **Configure Environment Secrets (Optional)**:
   - In Streamlit Cloud settings -> **Secrets**, add your API keys:
     ```toml
     GEMINI_API_KEY = "your_gemini_api_key_here"
     OPENAI_API_KEY = "your_openai_api_key_here"
     ```

---

## 🛠️ Local Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/smart-campus-hub.git
cd smart-campus-hub

# Install dependencies
pip install -r requirements.txt

# Run the app locally
streamlit run app.py
```
