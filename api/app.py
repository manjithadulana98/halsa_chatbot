from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from datetime import datetime
from textblob import TextBlob

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_community.chains import ConversationalRetrievalChain
from langchain_core.prompts import PromptTemplate

# ------------------------------------------------------------
# Setup
# ------------------------------------------------------------
load_dotenv()

app = FastAPI(title="Halsa Product Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("📦 Loading FAISS index ...")
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = FAISS.load_local("index/faiss", embeddings, allow_dangerous_deserialization=True)
print("✅ Index loaded successfully!")

qa_template = """
You are a helpful customer support assistant for Halsa products.
Use ONLY the provided context from official manuals to answer questions.
If relevant, include which manual and page number the information came from.
If the manuals do not mention the topic, reply:
"The manuals do not mention that specifically. Please contact Halsa support."
----------------
{context}
----------------
Question: {question}
Helpful answer:
"""
prompt = PromptTemplate(input_variables=["context", "question"], template=qa_template)

qa_chain = ConversationalRetrievalChain.from_llm(
    ChatOpenAI(model="gpt-4o-mini", temperature=0),
    retriever=vectorstore.as_retriever(search_kwargs={"k": 8}),
    return_source_documents=True,
    combine_docs_chain_kwargs={"prompt": prompt},
)

chat_history = []


# ------------------------------------------------------------
# Local sentiment + intent detection
# ------------------------------------------------------------
def analyze_local(text: str):
    """Lightweight sentiment & intent detection using TextBlob."""
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity

    if any(w in text.lower() for w in ["hi", "hello", "hey"]):
        intent = "greeting"
    elif any(w in text.lower() for w in ["bye", "goodbye", "see you"]):
        intent = "farewell"
    elif any(w in text.lower() for w in ["thank", "thanks"]):
        intent = "gratitude"
    elif any(w in text.lower() for w in ["sorry", "apologize"]):
        intent = "apology"
    elif any(w in text.lower() for w in ["help", "issue", "problem", "error"]):
        intent = "product_question"
    else:
        intent = "other"

    if polarity > 0.3:
        emotion = "positive"
    elif polarity < -0.3:
        emotion = "negative"
    else:
        emotion = "neutral"

    return {"emotion": emotion, "intent": intent}


# ------------------------------------------------------------
# API Schemas
# ------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str


# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "✅ Halsa Chatbot API is running (fast mode)!"}


@app.post("/chat")
async def chat(req: ChatRequest):
    analysis = analyze_local(req.question)
    emotion = analysis["emotion"]
    intent = analysis["intent"]
    print(f"🧠 Detected Emotion: {emotion} | Intent: {intent}")

    # --- Emotionally aware quick responses ---
    if intent == "greeting":
        return {"answer": "👋 Hello! I’m your Hälsa Support Assistant. How can I help today?", "sources": []}
    if intent == "farewell":
        return {"answer": "Goodbye 👋 and thank you for being part of the Hälsa family!", "sources": []}
    if intent == "gratitude":
        return {"answer": "You're very welcome! 💙 I'm glad I could help.", "sources": []}
    if intent == "apology":
        return {"answer": "No worries at all 😊 I'm here to help you with anything Hälsa-related!", "sources": []}

    # --- Add empathy tone for negative emotion ---
    empathy_prefix = ""
    if emotion == "negative":
        empathy_prefix = "I understand this might be frustrating 😔. Let's sort this out together.\n\n"

    # --- Manual-based response ---
    result = qa_chain({"question": req.question, "chat_history": chat_history})
    chat_history.append((req.question, result["answer"]))

    sources = [
        f"{os.path.basename(doc.metadata.get('source', 'unknown'))} (page {doc.metadata.get('page_label', '?')})"
        for doc in result.get("source_documents", [])
    ]
    return {"answer": empathy_prefix + result["answer"], "sources": sources}


@app.post("/save_unanswered")
async def save_unanswered(req: ChatRequest):
    log_path = "unanswered_questions.txt"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {req.question}\n")
    return {"status": "saved", "message": "Question logged for review."}
