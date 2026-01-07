# NyayaSetu 🇮🇳⚖️

**Bridging the Gap Between Citizens and Justice.**

NyayaSetu is an AI-powered legal assistant designed to simplify the Indian bureaucratic process and make the Constitution and laws (BNS, BNSS) accessible to every citizen in plain language. Built for the **IMPECTUS Hackathon**.

![NyayaSetu Banner](static/nyayasetu_banner.png)

---

## 🚀 Key Features

### 1. 🤖 AI Legal Chatbot ("Nyaya Sahayak")
*   **Context-Aware**: Powered by **Gemini Pro** and **RAG (Retrieval Augmented Generation)** using ChromaDB.
*   **Knowledge Base**: Trained on the **Bharatiya Nyaya Sanhita (BNS)**, **Bharatiya Nagarik Suraksha Sanhita (BNSS)**, and the **Constitution of India**.
*   **Multilingual**: Supports **Hindi, Bengali, Telugu, Kannada, Tamil, Malayalam, Marathi**, and English.
*   **Voice-First**: Integrated Speech-to-Text for accessibility.

### 2. 📄 Document Simplifier ("Samvidhan Setu")
*   **"Explain Like I'm 5"**: Upload complex legal documents (PDF/Images) and get a summary so simple a 5-year-old could understand it.
*   **Vision Capabilities**: Uses **Gemini Vision** to read scanned images and photos of documents.
*   **Key Insights**: Extracts "Document Type", "What it Says", "Why it Matters", and "Action Required".

### 3. 📝 Forms & Bureaucracy Helper
*   **Interactive Guidance**: Step-by-step help for navigating common government forms.
*   **Smart Filling**: AI suggestions for completing complex bureaucratic fields.

### 4. 🔐 Robust & Secure
*   **Secure Authentication**: Cookie-based authentication with `HttpOnly` cookies.
*   **Sliding Sessions**: Smart session management that keeps you logged in while active (30-minute sliding window).
*   **Admin Dashboard**: comprehensive view of user activity and system stats.

---

## 🛠️ Tech Stack

*   **Backend**: Python 3.10.11, FastAPI
*   **Frontend**: HTML5, Jinja2, Tailwind CSS (via CDN), Vanilla JS
*   **AI Engine**: Google Gemini API (GenerativeLanguage)
*   **Vector Database**: ChromaDB (Local persistence)
*   **Database**: SQLite + SQLAlchemy (User data)

---

## ⚙️ Setup & Installation

Follow these steps to set up the project locally:

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/NyayaSetu.git
cd NyayaSetu
```

### 2. Install Dependencies
It is recommended to use a virtual environment.
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
SECRET_KEY=generate_a_secure_random_string_here
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4. Initialize Data
Place your source PDF documents in the `data/` folder:
*   `data/BNS_2023.pdf`
*   `data/BNSS_2023.pdf`
*   `data/constitution.pdf`

Run the ingestion script to build the vector database (this may take a few minutes):
```bash
python backend/ingest.py
```
*(Note: You only need to run this once or whenever you add new documents.)*

### 5. Run the Server
```bash
uvicorn backend.main:app --reload
```
The application will be available at: **http://localhost:8000**

---

## 🧪 Testing/Debugging
*   **API Docs**: Visit `http://localhost:8000/docs` for the automatic Swagger UI.
*   **Reset Chat Limit**: A debug button is available on the landing page (bottom-right) to reset the free chat limit cookie.
*   **Admin Panel**: Access via `/admin-dashboard` (requires login).

---

## 🤝 Contribution
1.  Fork the repo.
2.  Create a feature branch (`git checkout -b feature-name`).
3.  Commit your changes (`git commit -m "Added cool feature"`).
4.  Push to the branch (`git push origin feature-name`).
5.  Open a Pull Request.

---

Made with ❤️ for India by Team **DarthCoders**.
