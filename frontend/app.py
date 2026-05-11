"""
frontend/app.py — TailorTalk Drive Agent chat interface.
Premium dark UI inspired by Phantom / Linear design language.
"""

import httpx
import streamlit as st

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TailorTalk — Drive Agent",
    page_icon="🗂️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

BACKEND_URL = "http://localhost:8000"

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background: #0a0a0f !important;
    font-family: 'Inter', sans-serif !important;
    color: #e2e8f0 !important;
}

[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse at 20% 50%, #1a0533 0%, #0a0a0f 60%) !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {
    display: none !important;
}

/* ── Main container ── */
.main .block-container {
    max-width: 780px !important;
    padding: 0 1.5rem 6rem !important;
    margin: 0 auto !important;
}

/* ── Hero header ── */
.hero {
    text-align: center;
    padding: 3.5rem 0 2rem;
}

.hero-logo {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    background: linear-gradient(135deg, #7c3aed, #a855f7);
    border-radius: 16px;
    font-size: 1.6rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 0 32px rgba(124, 58, 237, 0.4);
}

.hero h1 {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #e2e8f0 0%, #a78bfa 100%);
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    letter-spacing: -0.03em !important;
    margin-bottom: 0.5rem !important;
}

.hero p {
    color: #64748b;
    font-size: 0.9rem;
    font-weight: 400;
}

/* ── Chat messages ── */
.message-wrap {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.message {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
    animation: fadeSlideIn 0.25s ease;
}

@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

.message.user { flex-direction: row-reverse; }

.avatar {
    width: 32px;
    height: 32px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    flex-shrink: 0;
    font-weight: 600;
}

.avatar.bot {
    background: linear-gradient(135deg, #7c3aed, #a855f7);
    box-shadow: 0 0 12px rgba(124,58,237,0.35);
}

.avatar.user-av {
    background: linear-gradient(135deg, #1e293b, #334155);
    border: 1px solid #334155;
}

.bubble {
    max-width: 75%;
    padding: 0.85rem 1.1rem;
    border-radius: 16px;
    font-size: 0.9rem;
    line-height: 1.65;
    word-break: break-word;
}

.bubble.bot {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-top-left-radius: 4px;
    color: #e2e8f0;
    backdrop-filter: blur(12px);
}

.bubble.user {
    background: linear-gradient(135deg, #7c3aed, #6d28d9);
    border-top-right-radius: 4px;
    color: #fff;
    box-shadow: 0 4px 20px rgba(124,58,237,0.25);
}

/* Links inside bot bubbles */
.bubble.bot a {
    color: #a78bfa;
    text-decoration: none;
    border-bottom: 1px solid rgba(167,139,250,0.3);
}
.bubble.bot a:hover { border-bottom-color: #a78bfa; }

/* ── Typing indicator ── */
.typing {
    display: flex;
    gap: 5px;
    align-items: center;
    padding: 0.6rem 0.4rem;
}
.typing span {
    width: 7px;
    height: 7px;
    background: #7c3aed;
    border-radius: 50%;
    animation: bounce 1.2s infinite;
}
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
    0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
    40%            { transform: translateY(-6px); opacity: 1; }
}

/* ── Divider ── */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
    margin: 1.5rem 0;
}

/* ── Suggestion chips ── */
.chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 1.2rem 0;
}

.chip {
    background: rgba(124,58,237,0.1);
    border: 1px solid rgba(124,58,237,0.25);
    color: #a78bfa;
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.15s ease;
}
.chip:hover {
    background: rgba(124,58,237,0.2);
    border-color: rgba(124,58,237,0.5);
}

/* ── Input area ── */
[data-testid="stBottom"] {
    background: transparent !important;
    border: none !important;
    padding: 1rem 1.5rem !important;
}

[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 16px !important;
    color: #e2e8f0 !important;
    backdrop-filter: blur(20px) !important;
    box-shadow: 0 0 0 0 rgba(124,58,237,0) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: rgba(124,58,237,0.5) !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.1) !important;
}

[data-testid="stChatInput"] textarea {
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #475569 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(124,58,237,0.3);
    border-radius: 99px;
}
</style>
""", unsafe_allow_html=True)


# ── Session State ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def render_message(role: str, content: str):
    avatar = "🗂️" if role == "assistant" else "U"
    av_class = "bot" if role == "assistant" else "user-av"
    bubble_class = "bot" if role == "assistant" else "user"
    msg_class = "" if role == "assistant" else "user"

    st.markdown(f"""
    <div class="message {msg_class}">
        <div class="avatar {av_class}">{avatar}</div>
        <div class="bubble {bubble_class}">{content}</div>
    </div>
    """, unsafe_allow_html=True)


def stream_response(user_message: str) -> str:
    """Call backend SSE endpoint and accumulate the full response."""
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]

    full_response = ""
    placeholder = st.empty()

    try:
        with httpx.Client(timeout=60.0) as client:
            with client.stream(
                "POST",
                f"{BACKEND_URL}/chat",
                json={"message": user_message, "history": history},
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        token = line[6:]
                        if token == "[DONE]":
                            break
                        full_response += token
                        # Live render while streaming
                        placeholder.markdown(f"""
                        <div class="message">
                            <div class="avatar bot">🗂️</div>
                            <div class="bubble bot">{full_response}▌</div>
                        </div>
                        """, unsafe_allow_html=True)

        placeholder.empty()
        return full_response

    except httpx.ConnectError:
        placeholder.empty()
        return "❌ Cannot connect to backend. Make sure the FastAPI server is running on port 8000."
    except Exception as e:
        placeholder.empty()
        return f"❌ Unexpected error: {str(e)}"


SUGGESTIONS = [
    "📄 Show me all PDFs",
    "📊 Find spreadsheets",
    "🖼️ List all images",
    "📝 Recent Google Docs",
    "🔍 Files modified this week",
]


# ── UI ────────────────────────────────────────────────────────────────────────

# Hero
st.markdown("""
<div class="hero">
    <div class="hero-logo">🗂️</div>
    <h1>TailorTalk Drive Agent</h1>
    <p>Search your Google Drive with natural language</p>
</div>
""", unsafe_allow_html=True)

# Suggestion chips — only show when no conversation yet
if not st.session_state.messages:
    st.markdown('<div class="chips">' + "".join(
        f'<span class="chip">{s}</span>' for s in SUGGESTIONS
    ) + '</div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# Render message history
if st.session_state.messages:
    st.markdown('<div class="message-wrap">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        render_message(msg["role"], msg["content"])
    st.markdown('</div>', unsafe_allow_html=True)

# Handle pending message (runs on rerun after input)
if st.session_state.pending:
    user_msg = st.session_state.pending
    st.session_state.pending = None

    st.markdown('<div class="message-wrap">', unsafe_allow_html=True)
    render_message("user", user_msg)

    # Typing indicator
    typing_placeholder = st.empty()
    typing_placeholder.markdown("""
    <div class="message">
        <div class="avatar bot">🗂️</div>
        <div class="bubble bot">
            <div class="typing">
                <span></span><span></span><span></span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    reply = stream_response(user_msg)
    typing_placeholder.empty()

    render_message("assistant", reply)
    st.markdown('</div>', unsafe_allow_html=True)

    st.session_state.messages.append({"role": "user", "content": user_msg})
    st.session_state.messages.append({"role": "assistant", "content": reply})


# ── Chat Input ────────────────────────────────────────────────────────────────

if prompt := st.chat_input("Ask anything about your Drive files..."):
    st.session_state.pending = prompt
    st.rerun()