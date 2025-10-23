from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from datetime import datetime
from typing import Optional
import os

# ------------------------------------------------------------
# Setup
# ------------------------------------------------------------
load_dotenv()

app = FastAPI(title="Hälsa Product Chatbot API")

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

# ------------------------------------------------------------
# Prompt Templates
# ------------------------------------------------------------
qa_prompt = """
You are a helpful customer support assistant for Hälsa products.
Use ONLY the provided context from official manuals to answer questions.
If relevant, include which manual and page number the information came from.

If the manuals do not mention the topic, reply:
"The manuals do not mention that specifically. Please contact Hälsa support."

If the user's tone seems negative or frustrated, begin your response with an empathetic sentence.
Always write in clear, professional English.

----------------
{context}
----------------
User's new question: {question}
Helpful answer:
"""

prompt = PromptTemplate(input_variables=["context", "question"], template=qa_prompt)

# Fast model for QA and summarization
qa_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
summarizer_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

qa_chain = ConversationalRetrievalChain.from_llm(
    qa_model,
    retriever=vectorstore.as_retriever(search_kwargs={"k": 10}),
    return_source_documents=True,
    combine_docs_chain_kwargs={"prompt": prompt},
)


# ------------------------------------------------------------
# Schemas
# ------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    summary: Optional[str] = None  # optional summary from frontend


# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@app.post("/chat")
async def chat(req: ChatRequest):
    """Stateless chat endpoint — uses summary from frontend and updates it."""
    
    # Step 1: Use summary from frontend if provided
    local_summary = req.summary or ""

    # Step 2: Combine summary with current question
    context_text = f"""
Previous Conversation Summary:
{local_summary or "None yet."}

New User Message:
{req.question}

Respond based on the summary above, but prioritize the new question.
"""

    # Step 3: Get QA response from manual context
    result = qa_chain({"question": context_text, "chat_history": []})
    answer = result["answer"]

    # Step 4: Update chat summary using a small LLM call
    summary_prompt = f"""
Update the ongoing chat summary below by briefly including what the user just asked and how you responded.
Keep it under 3 sentences.
---
Previous Summary:
{local_summary}

User: {req.question}
Assistant: {answer}
---
New concise summary:
"""
    new_summary = summarizer_model.invoke(summary_prompt).content.strip()

    print(f"🧾 Updated Summary (preview): {new_summary[:120]}...")

    # Step 5: Extract sources
    sources = [
        f"{os.path.basename(doc.metadata.get('source', 'unknown'))} (page {doc.metadata.get('page_label', '?')})"
        for doc in result.get("source_documents", [])
    ]

    return {
        "answer": answer,
        "sources": sources,
        "summary": new_summary,  # send summary back to frontend
    }


@app.get("/")
async def root():
    return {"message": "✅ Hälsa Chatbot API running with stateless summary-based memory!"}
