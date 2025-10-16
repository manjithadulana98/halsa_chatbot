"""
build_index.py
--------------------------------------
This script builds a FAISS vector index
from all PDF manuals and CSV files in the 'Halsa_Usermanuals' folder.
"""

from pathlib import Path
import os
import pandas as pd
from langchain_community.document_loaders import PyPDFLoader
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
DATA_DIR = Path("Halsa_Usermanuals")   # Folder containing your PDFs and CSVs
INDEX_DIR = Path("index/faiss")
INDEX_DIR.mkdir(parents=True, exist_ok=True)


def load_pdfs(folder: Path):
    """Loads and reads all PDFs from the given folder."""
    docs = []
    for pdf_path in folder.glob("*.pdf"):
        print(f"📄 Loading {pdf_path.name} ...")
        loader = PyPDFLoader(str(pdf_path))
        pdf_docs = loader.load()
        docs.extend(pdf_docs)
    print(f"✅ Loaded {len(docs)} pages from {len(list(folder.glob('*.pdf')))} PDF(s).")
    return docs


def load_csvs(folder: Path):
    """Loads all CSV files and converts rows into text documents."""
    docs = []
    for csv_path in folder.glob("*.csv"):
        print(f"📊 Loading {csv_path.name} ...")
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            print(f"⚠️  Could not read {csv_path.name} as standard CSV, trying ISO encoding...")
            df = pd.read_csv(csv_path, encoding="ISO-8859-1")

        # Combine columns into readable text
        for i, row in df.iterrows():
            text = " | ".join([f"{col}: {row[col]}" for col in df.columns if not pd.isna(row[col])])
            if text.strip():
                docs.append(Document(page_content=text, metadata={"source": str(csv_path)}))
        print(f"✅ Loaded {len(df)} rows from {csv_path.name}")
    return docs


def build_index():
    """Builds FAISS index from PDF and CSV content."""
    all_docs = []

    # Load PDFs
    if any(DATA_DIR.glob("*.pdf")):
        all_docs.extend(load_pdfs(DATA_DIR))

    # Load CSVs
    if any(DATA_DIR.glob("*.csv")):
        all_docs.extend(load_csvs(DATA_DIR))

    if not all_docs:
        print("❌ No PDF or CSV files found in the data folder.")
        return

    # Split into manageable chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(all_docs)
    print(f"✂️ Split into {len(chunks)} text chunks from {len(all_docs)} documents.")

    # Create embeddings and build FAISS index
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    print("⚙️  Generating embeddings and building FAISS index ...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # Save locally
    vectorstore.save_local(str(INDEX_DIR))
    print(f"✅ FAISS index saved to: {INDEX_DIR.resolve()}")


if __name__ == "__main__":
    if not DATA_DIR.exists():
        print(f"❌ ERROR: Folder '{DATA_DIR}' not found. Please check the path.")
        exit(1)
    build_index()
