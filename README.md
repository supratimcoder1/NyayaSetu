# NyayaSetu 🇮🇳⚖️

**Bridging the Gap Between Citizens and Justice.**

NyayaSetu is a comprehensive Legal Tech platform built to democratize access to the Indian judicial system. It tackles two critical problems: **Legal Literacy** (helping citizens understand laws and complex documents through multilingual AI) and **Procedural Friction** (providing an accessible, secure interface for tracking active court cases and receiving context-aware AI procedural guidance).

![NyayaSetu Banner](static/nyayasetu_banner.png)

---

## 🚀 Key Features

### 1. ⚖️ Judicial Modules (Case Management & Trial Tracking)
A secure, feature-rich platform for managing civil and criminal litigation lifecycles.
*   **VaadDakhil (Case Intake)**: Register specific legal disputes (Civil, Criminal, Family, Corporate) and assign roles (Plaintiff/Defendant).
*   **CNR Hard-Gating**: Cases begin in a "Pre-Filing" stage. To prevent platform abuse, evidence and hearing features are strictly locked until a valid 16-character **Court Case Number Record (CNR)** is registered and verified via strict regex and DB unique constraints.
*   **VaadSuchak (Judicial Tracker)**: A dynamic, kanban-style timeline dashboard displaying the progress of active cases (Filing → Hearings → Evidence → Final Arguments).
*   **NyayaMargdarshak (Case-Aware Procedural Guide)**: *The Crown Jewel*. An AI chat interface contextually bound to your active cases. By selecting a case, the backend fetches the *entire case history* (roles, evidence, hearing notes) and injects it into the Gemini LLM. The AI provides highly specific, actionable, and role-tailored legal advice (e.g., "As the defendant, since the plaintiff submitted a deed...").

### 2. 🏛️ Law Modules (Pre-Litigation & Legal Literacy)
*   **NagrikSahayak (Citizen Helper / RAG Chatbot)**: A voice-enabled chatbot supporting 8 regional Indian languages (Hindi, Bengali, Telugu, Tamil, Marathi, Kannada, Malayalam, English). Powered by a highly-available RAG pipeline embedded with the Bharatiya Nyaya Sanhita (BNS) and the Indian Constitution.
*   **SamvidhanSetu (Document Simplifier)**: Upload complex legal notices or court orders (PDF/Images). Uses text extraction and Gemini multi-modal parsing to break down legalese into plain-language summaries, bulleted rights, and "Explain Like I'm 5" actionable steps.

### 3. 🔐 Enterprise-Grade Security & Administration
*   **Robust Authentication**: JWT (JSON Web Tokens) in `HttpOnly`, `SameSite=Lax` secure cookies to prevent XSS/CSRF.
*   **Data Isolation**: Row-level security checks ensure every user’s cases and chats are strictly private.
*   **Admin Dashboard**: Dedicated portal for system administrators to monitor active sessions, view total user metrics, and securely delete users (with automatic cascading database cleanup).

---

## 🛠️ Tech Stack & Architecture

*   **Backend Framework**: Python 3.11+, FastAPI (Modular Router Architecture), Uvicorn Server.
*   **AI Engine**: Google Gemini (1.5 Pro, 2.5 Flash, 3-Preview fallback loop) via `google-generativeai`.
*   **Vector Database**: ChromaDB (Local Persistence for Legal Embeddings).
*   **Relational Database**: PostgreSQL / SQLite via SQLAlchemy ORM (Strict schema migrations).
*   **Frontend**: HTML5, Jinja2 Server-Side Rendering (SSR), TailwindCSS (CDN), Vanilla JavaScript (Voice API integration).
*   **Security**: `passlib` (bcrypt password hashing), `python-jose` (JWT).

---

## 📂 Project Structure

```text
NyayaSetu/
├── backend/
│   ├── routers/           # Modular API Routes (Auth, Chat, Judicial, Pages, Tools)
│   ├── models.py          # Database Schemas (User, Case, Documents, Hearings, Chats)
│   ├── schemas.py         # Pydantic Request/Response Validation (e.g., CNR Check)
│   ├── judicial_engine.py # Core Logic State Machine for Civil/Criminal Workflow
│   ├── rag_engine.py      # LLM Prompt Construction, Semantic Vector Search 
│   ├── auth.py            # JWT Cookie Handlers & Password Hashing
│   └── main.py            # FastAPI Entry Point & Middleware Config
├── templates/             # Jinja2 HTML Pages (Admin, Dashboards, Chat UI)
├── static/                # Assets, Icons, and CSS Styles
├── data/                  # Legal Knowledge Base (PDFs)
└── chroma_db_store/       # Persistent Embeddings Directory
```

---

## ⚙️ Setup & Installation

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/yourusername/NyayaSetu.git
cd NyayaSetu
python -m venv venv
# Activate Venv (Windows: venv\Scripts\activate, Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_secure_random_string (optional, will auto-generate if blank)
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Initialize Knowledge Base & Admin
(Only needed once for the first setup)
```bash
# Ingest local legal PDFs into ChromaDB
python backend/ingest.py

# Create the master admin account (admin@nyaya.com / admin123)
python create_admin.py
```

### 4. Run the Platform
```bash
uvicorn backend.main:app --reload
```
Visit **http://localhost:8000** in your browser.

---

## 🧪 Testing the Workflow Flows

*   **Admin Access**: Log in with `admin@nyaya.com` / `admin123` to view the System Administration dashboard.
*   **Judicial Case Flow**:
    1.  Create a new case (Intake). It starts in "Pre-Filing".
    2.  Notice that Evidence and Hearing tabs are locked.
    3.  Enter a demo CNR (e.g., `DLND010012342024`). The stage auto-advances, unlocking the trial features.
    4.  Upload Evidence and record Hearings.
    5.  Navigate to NyayaMargdarshak (Guidance), select your case from the dropdown, and ask the AI "What is my next step?" to see deep context injection in action.
*   **Law Modules**: Head to NagrikSahayak and use the microphone icon to ask a legal query in Hindi.

---

## 🤝 Contribution

We welcome contributions! Please follow the `backend/routers` pattern when adding new API endpoints.

```bash
git checkout -b feature/amazing-feature
git commit -m "Add Amazing Feature"
git push origin feature/amazing-feature
```

---
*Built with ❤️ for Justice.*
