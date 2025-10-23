const API_URL  = "https://halsachatbot-production.up.railway.app/chat";
const SAVE_URL = "https://halsachatbot-production.up.railway.app/save_unanswered";
const chatContainer = document.getElementById("chat-container");
const userInput     = document.getElementById("user-input");

// 🧠 Local summary memory (stored only in this browser tab)
let summary = sessionStorage.getItem("summary") || "";

// 🗨️ Display welcome message
window.addEventListener("DOMContentLoaded", () => {
  if (!sessionStorage.getItem("summary")) {
    showIntro();
  } else {
    appendMessage("bot", "💬 Chat resumed (summary loaded from this session).");
  }
});

// 🪄 Intro message
function showIntro() {
  const intro = `
👋 Hello! I'm your Hälsa Support Assistant.
I can help you with:
• Device setup
• Troubleshooting
• Cleaning & maintenance
• Warranty and support info

Type your question below to get started:
`;
  appendMessage("bot", intro);
}

// 🚀 Send user message
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  appendMessage("user", text);
  userInput.value = "";

  const botDiv = appendMessage("bot", "");
  const typingIndicator = document.createElement("span");
  typingIndicator.classList.add("typing-indicator");
  typingIndicator.textContent = "▮";
  botDiv.appendChild(typingIndicator);

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: text,
        summary: summary || null, // send previous summary if available
      }),
    });

    if (!res.ok) throw new Error("Request failed");
    const data = await res.json();
    typingIndicator.remove();

    await typeText(botDiv, data.answer);

    // 🧠 Update and store summary
    summary = data.summary || "";
    sessionStorage.setItem("summary", summary);
    console.log("🧾 Updated summary:", summary);

    // 📚 Add sources (if any)
    if (data.sources?.length) {
      const srcDiv = document.createElement("div");
      srcDiv.classList.add("sources");
      srcDiv.textContent = "📚 Sources:\n" + data.sources.join("\n");
      botDiv.appendChild(srcDiv);
    }

    // 💾 Save unanswered button if needed
    if (data.answer.includes("The manuals do not mention that specifically")) {
      const saveBtn = document.createElement("button");
      saveBtn.textContent = "💾 Save question for review";
      saveBtn.style.marginTop = "8px";
      saveBtn.onclick = async () => await saveUnanswered(text, botDiv, saveBtn);
      botDiv.appendChild(saveBtn);
    }

  } catch (err) {
    typingIndicator.remove();
    botDiv.textContent = "⚠️ Error contacting the server.";
    console.error(err);
  }

  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// 💾 Log unanswered questions
async function saveUnanswered(question, botDiv, btn) {
  btn.disabled = true;
  btn.textContent = "Saving...";
  try {
    const res = await fetch(SAVE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    await res.json();
    btn.textContent = "✅ Saved";
  } catch (err) {
    console.error(err);
    btn.textContent = "❌ Error saving";
  }
}

// 🧹 Reset chat + memory
function resetChat() {
  chatContainer.innerHTML = "";
  summary = "";
  sessionStorage.removeItem("summary");
  appendMessage("bot", "🧹 Chat and memory cleared.");
  showIntro();
}

// 📝 Typewriter effect
async function typeText(element, text) {
  const words = text.split(" ");
  for (const w of words) {
    element.textContent += w + " ";
    chatContainer.scrollTop = chatContainer.scrollHeight;
    await new Promise(r => setTimeout(r, 25));
  }
}

// 💬 Append message
function appendMessage(sender, text) {
  const div = document.createElement("div");
  div.classList.add("message", sender);
  div.textContent = text;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return div;
}

// ⌨️ Enter key sends message
userInput.addEventListener("keydown", e => {
  if (e.key === "Enter") sendMessage();
});

// 🧼 Optional reset button logic
const resetBtn = document.getElementById("reset-btn");
if (resetBtn) resetBtn.addEventListener("click", resetChat);
