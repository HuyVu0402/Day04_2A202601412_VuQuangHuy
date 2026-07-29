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
    page_title="Research Agent Studio",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Soft Light Blue Pastel Theme CSS
PASTEL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Soft Light Blue Background */
.stApp {
    background-color: #F0F7FB;
    color: #1E293B;
}

/* Custom Header Banner (Soft Light Pink Pastel) */
.main-header {
    background: linear-gradient(135deg, #FFF0F5 0%, #FCE7F3 50%, #FBCFE8 100%);
    padding: 1.25rem 1.75rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    border: 1px solid #FBCFE8;
    box-shadow: 0 4px 20px rgba(251, 207, 232, 0.35);
}

.main-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #9D174D;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.main-subtitle {
    font-size: 0.9rem;
    color: #BE185D;
    margin-top: 0.25rem;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    font-size: 0.75rem;
    font-weight: 600;
    border-radius: 20px;
    margin-right: 0.4rem;
}

.badge-version { background-color: #E0E7FF; color: #3730A3; }
.badge-provider { background-color: #D1FAE5; color: #065F46; }
.badge-model { background-color: #E0F2FE; color: #0369A1; }
.badge-hash { background-color: #F1F5F9; color: #475569; font-family: monospace; }

/* Welcome Box (Soft Light Pink Pastel) */
.welcome-box {
    background-color: #FFF0F5;
    border: 1px solid #FBCFE8;
    color: #9D174D;
    padding: 1rem 1.25rem;
    border-radius: 14px;
    margin-bottom: 1.25rem;
    font-size: 0.95rem;
    box-shadow: 0 2px 10px rgba(251, 207, 232, 0.2);
}

/* Sidebar Customization */
section[data-testid="stSidebar"] {
    background-color: #E8F4FA;
    border-right: 1px solid #D0E8F2;
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
        padding: 0.85rem 1rem !important;
        margin-bottom: 1rem !important;
        border-radius: 12px !important;
    }
    .main-title {
        font-size: 1.25rem !important;
    }
    .main-subtitle {
        font-size: 0.8rem !important;
    }
    .badge {
        font-size: 0.68rem !important;
        padding: 0.2rem 0.5rem !important;
        margin-bottom: 0.25rem !important;
    }
    .welcome-box {
        padding: 0.75rem 0.9rem !important;
        font-size: 0.85rem !important;
        border-radius: 10px !important;
    }
    .stChatMessage {
        padding: 0.5rem 0.65rem !important;
    }
    .stButton > button {
        font-size: 0.85rem !important;
        padding: 0.5rem 0.75rem !important;
        margin-bottom: 0.35rem !important;
    }
}
</style>
"""

st.markdown(PASTEL_CSS, unsafe_allow_html=True)


def get_auto_provider() -> tuple[str, str]:
    if os.getenv("GEMINI_API_KEY"):
        return "gemini", "gemini-3.5-flash"
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter", "google/gemini-3.5-flash"
    if os.getenv("OPENAI_API_KEY"):
        return "openai", "gpt-4o-mini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic", "claude-3-5-haiku-20241022"
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
    """Format tool results into clean markdown sections for main result view."""
    sections = []
    for ev in tool_events:
        t_name = ev.get("tool")
        res = ev.get("result", {})
        if not isinstance(res, dict):
            continue

        if "error" in res or "message" in res:
            err_msg = res.get("message") or res.get("error")
            sections.append(f"> ⚠️ **Tool `{t_name}` lỗi**: {err_msg}")
        
        elif "items" in res and res["items"]:
            items = res["items"]
            sec = [f"#### 📰 Kết quả tìm kiếm từ `{t_name}` ({len(items)} mục):"]
            for idx, item in enumerate(items[:5], 1):
                title = item.get("title") or item.get("text") or "Chi tiết"
                url = item.get("url") or ""
                summary = item.get("summary") or item.get("content") or item.get("text") or ""
                link_md = f"[{title}]({url})" if url else f"**{title}**"
                sec.append(f"{idx}. {link_md}\n   *{summary[:200]}...*" if summary else f"{idx}. {link_md}")
            sections.append("\n".join(sec))
            
        elif "content" in res:
            content = str(res["content"])
            sections.append(f"#### 📄 Nội dung trích xuất từ `{t_name}`:\n```text\n{content[:500]}...\n```")
            
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
    
    # Header Banner
    st.markdown(
        f"""
        <div class="main-header">
            <div class="main-title">🌸 Research Agent Studio</div>
            <div class="main-subtitle">Evidence-Driven Research Agent UI</div>
            <div style="margin-top: 0.6rem;">
                <span class="badge badge-provider">Provider: {provider_name}</span>
                <span class="badge badge-model">Model: {default_model}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Render Chat Stream
    if not st.session_state.messages:
        st.markdown(
            '<div class="welcome-box">💡 <strong>Chào mừng!</strong> Chọn một mẫu yêu cầu nghiên cứu nhanh bên dưới hoặc nhập câu hỏi của bạn.</div>',
            unsafe_allow_html=True
        )
        
        # Quick Research Mode Action Chips
        st.markdown("#### 🔬 Lựa chọn Chức năng Research Nhanh:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📚 Tìm bài báo arXiv mới nhất về AI", use_container_width=True):
                st.session_state.pending_query = "Tìm các bài báo nghiên cứu mới nhất về AI Agent trên arXiv"
                st.rerun()
            if st.button("🏢 Tra cứu Quy định / Chính sách nội bộ", use_container_width=True):
                st.session_state.pending_query = "Chính sách làm việc từ xa của công ty quy định như thế nào?"
                st.rerun()
        with col2:
            if st.button("📰 Tổng hợp Tin tức Công nghệ AI", use_container_width=True):
                st.session_state.pending_query = "Tin tức AI hôm nay có gì nổi bật?"
                st.rerun()
            if st.button("🔗 Tóm tắt nội dung bài viết từ URL", use_container_width=True):
                st.session_state.pending_query = "Đọc và tóm tắt bài báo https://arxiv.org/abs/1706.03762"
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
    user_input = st.chat_input("Nhập câu hỏi hoặc yêu cầu nghiên cứu...")

    # Process input from text box OR pending quick action chip
    active_query = user_input or st.session_state.pop("pending_query", None)

    if active_query:
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
