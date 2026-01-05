# NyayaSetu 🇮🇳⚖️

**Bridging the Gap Between Citizens and Justice.**

NyayaSetu is an AI-powered legal assistant designed to simplify the Indian bureaucratic process and make the Constitution and laws (BNS, BNSS) accessible to every citizen in plain language.

## Features
- **Lexical Simplification**: Translates complex legal jargon into everyday language.
- **Voice Support**: Speak your queries in Indian English.
- **RAG Engine**: powered by Gemini API and ChromaDB for accurate, context-aware answers.
- **Modern UI**: A beautiful, responsive interface built with Tailwind CSS.

## Tech Stack
- **Backend**: Python (FastAPI)
- **Frontend**: HTML5, Jinja2, Tailwind CSS, Vanilla JS
- **AI/LLM**: Google Gemini API
- **Vector DB**: ChromaDB

## Setup & Installation

1.  **Clone the repository** (or unzip).
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up Environment Variables**:
    - Create a `.env` file in the root.
    - Add your Gemini API Key: `GEMINI_API_KEY=your_key_here`
4.  **Add Data**:
    - Place `BNS_2023.pdf`, `BNSS_2023.pdf`, and `constitution.pdf` in the `data/` directory.
5.  **Run Ingestion** (First time only):
    ```bash
    python backend/ingest.py
    ```
6.  **Start the Server**:
    ```bash
    uvicorn backend.main:app --reload
    ```
7.  **Access**: Open `http://localhost:8000` in your browser.

## Project Structure
Adheres to the proposed structure including `backend/`, `templates/`, `static/`, and `data/` directories.
