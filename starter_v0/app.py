from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from env_loader import load_lab_env
from providers import make_provider
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version
from chat import run_model_tool_loop, write_transcript, now_iso, safe_slug, trim_history

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
load_lab_env(ROOT)

# Page configuration
st.set_page_config(
    page_title="Research Studio AI",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Advanced Modern Pastel Perplexity-Inspired CSS
PASTEL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* World-Class AI Research Palette (Perplexity AI Pro Style) */

/* Soft Crisp Slate Background */
.stApp {
    background-color: #F8FAFC;
    color: #0F172A;
}

/* Deep Sapphire Slate Header Banner */
.main-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
    padding: 1.6rem 2.2rem;
    border-radius: 20px;
    margin-bottom: 1.75rem;
    border: 1px solid #334155;
    box-shadow: 0 12px 35px -10px rgba(15, 23, 42, 0.4);
    transition: all 0.3s ease;
}

.main-title {
    font-size: 1.85rem;
    font-weight: 800;
    color: #F8FAFC;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.65rem;
    letter-spacing: -0.025em;
}

.main-title-span {
    background: linear-gradient(135deg, #38BDF8 0%, #818CF8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.main-subtitle {
    font-size: 0.95rem;
    color: #94A3B8;
    margin-top: 0.35rem;
    font-weight: 500;
}

/* Badges & Pills */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.32rem 0.8rem;
    font-size: 0.78rem;
    font-weight: 600;
    border-radius: 30px;
    margin-right: 0.45rem;
}

.badge-provider { background-color: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(52, 211, 153, 0.3); }
.badge-model { background-color: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.3); }
.badge-status { background-color: rgba(129, 140, 248, 0.15); color: #A5B4FC; border: 1px solid rgba(165, 180, 252, 0.3); }

/* Welcome Alert Box (Soft Crisp Ice Blue) */
.welcome-box {
    background: #F0F9FF;
    border: 1px solid #BAE6FD;
    color: #0369A1;
    padding: 1.15rem 1.6rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    font-size: 0.95rem;
    font-weight: 500;
    box-shadow: 0 4px 15px rgba(186, 230, 253, 0.3);
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

/* Source Pill Card for Perplexity Style Results */
.source-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #0EA5E9;
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    margin-bottom: 0.65rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    transition: all 0.2s ease;
}

.source-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(14, 165, 233, 0.12);
}

/* Sidebar Customization (Modern Slate Dark/Light) */
section[data-testid="stSidebar"] {
    background-color: #0F172A;
    border-right: 1px solid #1E293B;
}

section[data-testid="stSidebar"] * {
    color: #F8FAFC !important;
}

section[data-testid="stSidebar"] .stButton > button {
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
    color: #F8FAFC !important;
}

section[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #334155 !important;
    border-color: #38BDF8 !important;
    color: #38BDF8 !important;
}

/* Buttons Hover & Styling */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    color: #0F172A !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.02) !important;
    transition: all 0.2s ease-in-out !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    border-color: #38BDF8 !important;
    color: #0284C7 !important;
    box-shadow: 0 8px 20px rgba(14, 165, 233, 0.15) !important;
}

/* Hide Streamlit Top-Right Deploy Button & Header Elements */
.stAppDeployButton {display: none !important;}
[data-testid="stAppDeployButton"] {display: none !important;}
header[data-testid="stHeader"] {
    background-color: transparent !important;
    z-index: 100 !important;
}
#MainMenu {visibility: hidden !important;}
footer {visibility: hidden !important;}

/* Mobile Responsive Styles (Smartphones & Small Screens) */
@media (max-width: 768px) {
    .main-header {
        padding: 1.1rem 1.25rem !important;
        margin-bottom: 1.1rem !important;
        border-radius: 16px !important;
    }
    .main-title {
        font-size: 1.45rem !important;
    }
    .main-subtitle {
        font-size: 0.85rem !important;
    }
    .badge {
        font-size: 0.72rem !important;
        padding: 0.25rem 0.6rem !important;
        margin-bottom: 0.3rem !important;
    }
    .welcome-box {
        padding: 0.9rem 1.1rem !important;
        font-size: 0.88rem !important;
        border-radius: 12px !important;
    }
    .stChatMessage {
        padding: 0.5rem 0.65rem !important;
    }
    .stButton > button {
        font-size: 0.85rem !important;
        padding: 0.55rem 0.85rem !important;
        margin-bottom: 0.4rem !important;
    }
}
</style>
"""

st.markdown(PASTEL_CSS, unsafe_allow_html=True)


def get_auto_provider() -> tuple[str, str]:
    if os.getenv("OPENAI_API_KEY"):
        model = os.getenv("OPENAI_MODEL") or os.getenv("MODEL") or "gpt-4o-mini"
        return "openai", model
    if os.getenv("OPENROUTER_API_KEY"):
        model = os.getenv("OPENROUTER_MODEL") or os.getenv("MODEL") or "google/gemini-3.5-flash"
        return "openrouter", model
    if os.getenv("ANTHROPIC_API_KEY"):
        model = os.getenv("ANTHROPIC_MODEL") or os.getenv("MODEL") or "claude-3-5-haiku-20241022"
        return "anthropic", model
    if os.getenv("GEMINI_API_KEY"):
        model = os.getenv("GEMINI_MODEL") or os.getenv("MODEL") or "gemini-3.5-flash"
        return "gemini", model
    return "gemini", "gemini-3.5-flash"


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history" not in st.session_state:
        st.session_state.history = []
    if "transcript" not in st.session_state:
        st.session_state.transcript = None
    if "transcript_path" not in st.session_state:
        st.session_state.transcript_path = None
    if "turn_index" not in st.session_state:
        st.session_state.turn_index = 0
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None
    if "show_url_selector" not in st.session_state:
        st.session_state.show_url_selector = False


def load_artifacts():
    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    
    system_prompt = system_prompt_path.read_text(encoding="utf-8") if system_prompt_path.exists() else ""
    tool_declarations = load_tool_declarations(tools_path) if tools_path.exists() else []
    return system_prompt_path, tools_path, system_prompt, tool_declarations


def generate_markdown_report() -> str:
    """Generate downloadable markdown research report from chat session."""
    lines = [
        "# BÁO CÁO NGHIÊN CỨU AI (RESEARCH REPORT)",
        f"**Thời gian xuất báo cáo**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "---",
        ""
    ]
    for idx, msg in enumerate(st.session_state.messages, 1):
        role_title = "👤 CÂU HỎI / YÊU CẦU NGHIÊN CỨU" if msg["role"] == "user" else "🤖 KẾT QUẢ TỔNG HỢP (RESEARCH AGENT)"
        lines.append(f"## {idx}. {role_title}")
        lines.append(msg.get("content", ""))
        lines.append("\n" + "-"*40 + "\n")
    return "\n".join(lines)


def render_sidebar(system_prompt_path: Path, tools_path: Path, system_prompt: str, tool_declarations: list[dict]):
    # Top Action: New Chat Button
    if st.sidebar.button("➕ Cuộc trò chuyện mới", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.transcript = None
        st.session_state.transcript_path = None
        st.session_state.turn_index = 0
        st.session_state.pending_query = None
        st.session_state.show_url_selector = False
        st.rerun()

    # Research Report Download Feature
    if st.session_state.messages:
        report_md = generate_markdown_report()
        st.sidebar.download_button(
            label="📥 Xuất Báo cáo Research (.md)",
            data=report_md,
            file_name=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Lịch sử trò chuyện")
    
    if TRANSCRIPTS_DIR.exists():
        transcripts = sorted(TRANSCRIPTS_DIR.glob("*.transcript.json"), reverse=True)
        if transcripts:
            for ts_file in transcripts[:12]:
                try:
                    ts_data = json.loads(ts_file.read_text(encoding="utf-8"))
                    first_turn = ""
                    if ts_data.get("turns"):
                        first_turn = ts_data["turns"][0].get("user", "")
                    
                    title_text = (first_turn[:22] + "...") if first_turn else ts_file.stem[:18]
                    created_time = ts_data.get("created_at", "")[11:16] if ts_data.get("created_at") else ""
                    
                    btn_label = f"💬 {title_text} ({created_time})"
                    if st.sidebar.button(btn_label, key=f"ts_btn_{ts_file.name}", use_container_width=True):
                        st.session_state.messages = []
                        st.session_state.history = []
                        st.session_state.transcript = ts_data
                        st.session_state.transcript_path = ts_file
                        st.session_state.turn_index = len(ts_data.get("turns", []))
                        
                        for turn in ts_data.get("turns", []):
                            u_text = turn.get("user", "")
                            a_text = turn.get("assistant_text", "")
                            if u_text:
                                st.session_state.messages.append({"role": "user", "content": u_text})
                                st.session_state.history.append({"role": "user", "content": u_text})
                            if a_text:
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": a_text,
                                    "rounds": turn.get("rounds", []),
                                    "tool_events": turn.get("tool_events", []),
                                    "status": turn.get("status"),
                                })
                                st.session_state.history.append({"role": "assistant", "content": a_text})
                        st.rerun()
                except Exception:
                    pass
        else:
            st.sidebar.caption("Chưa có lịch sử trò chuyện.")

    version_input = "v0"
    artifact_ver = build_artifact_version(version_input, system_prompt_path, tools_path)
    return version_input, artifact_ver


def format_tool_results_to_markdown(tool_events: list[dict]) -> str:
    """Format tool results into clean Perplexity-style card sections."""
    sections = []
    for ev in tool_events:
        t_name = ev.get("tool")
        res = ev.get("result", {})
        if not isinstance(res, dict):
            continue

        if "error" in res or "message" in res:
            err_msg = res.get("message") or res.get("error")
            sections.append(f"> ⚠️ **Tool `{t_name}` thông báo**: {err_msg}")
        
        elif "items" in res and res["items"]:
            items = res["items"]
            sec = [f"#### 📚 Nguồn dữ liệu từ `{t_name}` ({len(items)} mục):"]
            for idx, item in enumerate(items[:5], 1):
                title = item.get("title") or item.get("text") or "Chi tiết"
                url = item.get("url") or ""
                summary = item.get("summary") or item.get("content") or item.get("text") or ""
                link_md = f"[{title}]({url})" if url else f"**{title}**"
                sec.append(f"**[{idx}] {link_md}**\n\n_{summary[:220]}..._\n")
            sections.append("\n".join(sec))
            
        elif "content" in res:
            content = str(res["content"])
            sections.append(f"#### 📄 Trích xuất nội dung từ `{t_name}`:\n```text\n{content[:500]}...\n```")
            
        elif "answer" in res or "question" in res:
            q = res.get("question") or res.get("answer")
            sections.append(f"❓ **Xác nhận/Hỏi lại**: {q}")
            
    return "\n\n".join(sections)


def main():
    init_session_state()
    system_prompt_path, tools_path, system_prompt, tool_declarations = load_artifacts()
    provider_name, default_model = get_auto_provider()
    
    version_tag, artifact_ver = render_sidebar(
        system_prompt_path, tools_path, system_prompt, tool_declarations
    )
    
    # Hero Header Banner
    st.markdown(
        f"""
        <div class="main-header">
            <div class="main-title">🌸 <span class="main-title-span">Research Studio AI</span></div>
            <div class="main-subtitle">Deep Research Assistant • Real-Time Evidence Tracing • Academic Citations</div>
            <div style="margin-top: 0.75rem;">
                <span class="badge badge-provider">⚡ {provider_name.upper()}</span>
                <span class="badge badge-model">🧠 {default_model}</span>
                <span class="badge badge-status">✨ Deep Research Active</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Render Chat Stream
    if not st.session_state.messages:
        st.markdown(
            '<div class="welcome-box">💡 <strong>Chào mừng bạn đến với Research Studio!</strong> Chọn một chủ đề nghiên cứu nhanh bên dưới hoặc nhập yêu cầu để bắt đầu.</div>',
            unsafe_allow_html=True
        )
        
        # Perplexity-Style Research Mode Action Cards
        st.markdown("#### 🔬 Chức năng Research Nhanh:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📚  Nghiên cứu bài báo arXiv mới nhất", use_container_width=True):
                st.session_state.pending_query = "Tìm các bài báo nghiên cứu mới nhất về AI Agent trên arXiv"
                st.rerun()
            if st.button("🏢  Tra cứu Quy định Trích dẫn & Workflow Research AI", use_container_width=True):
                st.session_state.pending_query = "Quy định trích dẫn nguồn khi viết báo cáo nghiên cứu AI như thế nào?"
                st.rerun()
        with col2:
            if st.button("📰  Điểm tin Thời sự Công nghệ AI", use_container_width=True):
                st.session_state.pending_query = "Tin tức AI hôm nay có gì nổi bật?"
                st.rerun()
            if st.button("🔗  Phân tích & Tóm tắt bài viết từ URL", use_container_width=True):
                st.session_state.show_url_selector = True
                st.rerun()

        # Database Article Picker Card (Hiển thị danh sách bài báo khi người dùng muốn chọn tóm tắt)
        if st.session_state.get("show_url_selector", False):
            with st.container():
                st.markdown("---")
                st.markdown("### 📑 Danh sách Bài báo & Tài liệu có sẵn trong Database")
                
                featured_articles = {
                    "📑 Attention Is All You Need (Transformer Paper - arXiv:1706.03762)": "https://arxiv.org/abs/1706.03762",
                    "📑 DeepSeek-R1: Incentivizing Reasoning Capability via RL (arXiv:2501.12948)": "https://arxiv.org/abs/2501.12948",
                    "📑 Language Models are Few-Shot Learners (GPT-3 - arXiv:2005.14165)": "https://arxiv.org/abs/2005.14165",
                    "📑 Chain-of-Thought Prompting Elicits Reasoning in LLMs (arXiv:2201.11903)": "https://arxiv.org/abs/2201.11903",
                    "🏢 AI Research Policy (Chính sách Nghiên cứu AI Nội bộ)": "https://company-policy.internal/ai-research",
                    "🏢 Data Privacy Policy (Chính sách Bảo mật Dữ liệu Nội bộ)": "https://company-policy.internal/data-privacy",
                }

                selected_paper_name = st.selectbox(
                    "Chọn một bài báo từ Database để Agent tóm tắt:",
                    list(featured_articles.keys())
                )
                selected_url = featured_articles[selected_paper_name]
                
                custom_url = st.text_input("Hoặc dán đường link URL bài báo khác tùy chỉnh tại đây:", value=selected_url)
                
                c_btn1, c_btn2 = st.columns([2, 1])
                with c_btn1:
                    if st.button("🚀 Bắt đầu Phân tích & Tóm tắt Bài báo đã chọn", use_container_width=True, type="primary"):
                        st.session_state.show_url_selector = False
                        st.session_state.pending_query = f"Đọc và tóm tắt chi tiết nội dung bài viết từ URL: {custom_url}"
                        st.rerun()
                with c_btn2:
                    if st.button("❌ Hủy chọn", use_container_width=True):
                        st.session_state.show_url_selector = False
                        st.rerun()

    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg.get("content", "")
        tool_events = msg.get("tool_events", [])
        status = msg.get("status")

        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(content)
        elif role == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                # 1. Compact Tool Execution Trace (separate accordion)
                if tool_events:
                    with st.expander(f"🛠️ **Chi tiết gọi Tool ({len(tool_events)} tool calls)**", expanded=False):
                        for idx, event in enumerate(tool_events, 1):
                            st.markdown(f"**Call #{idx}: `{event.get('tool')}`**")
                            st.caption("Arguments")
                            st.json(event.get("args", {}))
                            st.caption("Raw Result")
                            st.json(event.get("result", {}))
                            st.divider()

                if status == "waiting_for_user":
                    st.warning("❓ **Cần thông tin bổ sung / xác nhận từ người dùng**")
                elif status == "provider_error":
                    st.error(f"❌ **Lỗi Provider**: {msg.get('error')}")

                # 2. Main Response / Result Output
                if content and content.strip():
                    st.markdown(content)
                else:
                    formatted_tool_res = format_tool_results_to_markdown(tool_events)
                    if formatted_tool_res:
                        st.markdown(formatted_tool_res)
                    else:
                        st.caption("*(Agent đã thực thi xong)*")

    # Chat Input Box
    user_input = st.chat_input("Nhập câu hỏi hoặc chủ đề nghiên cứu...")

    # Process input from text box OR pending quick action card
    active_query = user_input or st.session_state.get("pending_query", None)

    if active_query:
        st.session_state.pending_query = None
        st.session_state.messages.append({"role": "user", "content": active_query})
        st.session_state.turn_index += 1
        
        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(active_query)

        # Create assistant response container with inline spinner next to robot icon
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Đang suy luận & thực thi tool..."):
                try:
                    provider = make_provider(provider_name)
                    openai_tools = to_openai_tools(tool_declarations)
                    
                    if st.session_state.transcript is None:
                        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
                        transcript_id = "_".join([safe_slug(version_tag), safe_slug(provider_name), timestamp])
                        st.session_state.transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
                        st.session_state.transcript = {
                            "transcript_id": transcript_id,
                            **artifact_version_dict(artifact_ver),
                            "provider": provider_name,
                            "model": default_model,
                            "system_prompt": str(system_prompt_path),
                            "tools": str(tools_path),
                            "history_window": 5,
                            "max_tool_rounds": 4,
                            "created_at": now_iso(),
                            "updated_at": now_iso(),
                            "turns": [],
                        }

                    working_messages = [
                        {"role": "system", "content": system_prompt},
                        *trim_history(st.session_state.history, 5),
                        {"role": "user", "content": active_query},
                    ]

                    turn_record = {
                        "turn_index": st.session_state.turn_index,
                        "started_at": now_iso(),
                        "user": active_query,
                        "status": "started",
                        "assistant_text": None,
                        "rounds": [],
                        "tool_events": [],
                    }

                    loop_result = run_model_tool_loop(
                        provider=provider,
                        messages=working_messages,
                        tools=openai_tools,
                        model=default_model,
                        max_tool_rounds=4,
                    )

                    turn_record.update(loop_result)
                    assistant_text = loop_result.get("assistant_text") or ""
                    
                    # Extract text from rounds if empty
                    if not assistant_text.strip():
                        round_texts = [r.get("assistant_text") for r in loop_result.get("rounds", []) if r.get("assistant_text") and r.get("assistant_text").strip()]
                        if round_texts:
                            assistant_text = "\n\n".join(round_texts)

                    # If still empty, format results from tool events directly as main output
                    if not assistant_text.strip():
                        tool_events = loop_result.get("tool_events", [])
                        assistant_text = format_tool_results_to_markdown(tool_events)

                    if not assistant_text.strip():
                        assistant_text = "*(Agent đã thực thi tool nhưng không sinh ra văn bản bổ sung.)*"

                    # Stream text output word-by-word into active assistant container
                    def text_stream_generator(text: str):
                        import time
                        words = text.split(" ")
                        for i, word in enumerate(words):
                            yield word + (" " if i < len(words) - 1 else "")
                            time.sleep(0.012)

                    st.write_stream(text_stream_generator(assistant_text))

                    # Update Session History
                    st.session_state.history.append({"role": "user", "content": active_query})
                    st.session_state.history.append({"role": "assistant", "content": assistant_text})

                    # Append Assistant Message to UI
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_text,
                        "rounds": loop_result.get("rounds", []),
                        "tool_events": loop_result.get("tool_events", []),
                        "status": loop_result.get("status"),
                    })

                    # Save Transcript
                    turn_record["ended_at"] = now_iso()
                    st.session_state.transcript["turns"].append(turn_record)
                    write_transcript(st.session_state.transcript_path, st.session_state.transcript)

                except Exception as exc:
                    error_msg = f"{type(exc).__name__}: {str(exc)}"
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"⚠️ **Lỗi thực thi**: {error_msg}",
                        "status": "provider_error",
                        "error": error_msg,
                    })

        st.rerun()


if __name__ == "__main__":
    main()
