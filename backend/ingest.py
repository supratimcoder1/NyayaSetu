import os
# Fix for "Could not find a suitable TLS CA certificate bundle" error
os.environ.pop('CURL_CA_BUNDLE', None)

import sys
import time
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Ensure backend package is in path if run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings

import google.generativeai as genai
import chromadb
from pypdf import PdfReader
from chromadb.utils import embedding_functions

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

# Initialize Chroma
chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
collection = chroma_client.get_or_create_collection(name="legal_docs")

def get_gemini_embedding(text):
    """Fetch embeddings using Gemini API with retry logic"""
    retries = 3
    for attempt in range(retries):
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait_time = 2 * (2 ** attempt)
                logger.warning(f"Rate limit hit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            elif attempt == retries - 1:
                print(f"Error generating embedding: {e}")
                return []
    return []

def ingest_data():
    if not os.path.exists(settings.DATA_DIR):
        print(f"Data directory {settings.DATA_DIR} not found.")
        return

    print(f"Scanning {settings.DATA_DIR} for PDFs...")
    
    files = [f for f in os.listdir(settings.DATA_DIR) if f.lower().endswith(('.pdf', '.txt'))]
    if not files:
        print("No PDF or TXT files found.")
        return

    for filename in files:
        filepath = os.path.join(settings.DATA_DIR, filename)
        print(f"Processing {filename}...")
        
        try:
            text_buffer = ""
            
            if filename.lower().endswith('.pdf'):
                reader = PdfReader(filepath)
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        text_buffer += content + "\n\n"
            else: # .txt
                with open(filepath, 'r', encoding='utf-8') as f:
                    text_buffer = f.read()

            if not text_buffer:
                continue
                
            # Chunking: logic to split large pages
            # We'll just take page-sized chunks for simplicity in V1
            # or split by paragraphs if possible.
            
            # Let's do a simple recursive-like split by newlines for better context
            paragraphs = text_buffer.split('\n\n')
            current_chunk = ""
            
            for para in paragraphs:
                if len(current_chunk) + len(para) < 1000:
                    current_chunk += para + "\n\n"
                else:
                    # Flush chunk
                    if current_chunk.strip():
                        # Use hash of chunk as pseudo-page number for TXT
                        embed_and_store(filename, "1", current_chunk)
                    current_chunk = para + "\n\n"
            
            if current_chunk.strip():
                    embed_and_store(filename, "1", current_chunk)
                     
        except Exception as e:
            print(f"Failed to process {filename}: {e}")
                     


def embed_and_store(filename, page_num, text):
    # Sanitize text
    clean_text = text.strip()
    if len(clean_text) < 50: # Skip tiny chunks
        return

    # Generate ID
    doc_id = f"{filename}_pg{page_num}_{hash(clean_text)}"
    
    # Store in Chroma (Let's stick to default embeddings if Gemini fails, 
    # OR strictly use Gemini. For a hackathon, let's use Gemini explicitly)
    
    # Note: Standard Chroma add() computes embeddings automatically if none provided.
    # But we want 'Gemini Implementation'. 
    # To keep it fast/robust, we will pass embeddings explicitly.
    
    embedding = get_gemini_embedding(clean_text)
    if not embedding:
        return

    collection.add(
        documents=[clean_text],
        metadatas=[{"source": filename, "page": page_num}],
        ids=[doc_id],
        embeddings=[embedding]
    )
    print(f"  Stored chunk from {filename} page {page_num}")

if __name__ == "__main__":
    ingest_data()
