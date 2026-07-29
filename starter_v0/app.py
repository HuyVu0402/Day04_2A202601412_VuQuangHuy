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

# Pastel ChatGPT Theme CSS
PASTEL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
    background-color: #FAFAFC;
    color: #2D3748;
}

/* Custom Header Banner */
.main-header {
    background: linear-gradient(135deg, #E6FFFA 0%, #EBF8FF 50%, #F3E8FF 100%);
    padding: 1.25rem 1.75rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    border: 1px solid #E2E8F0;
    box-shadow: 0 4px 20px rgba(160, 174, 192, 0.08);
}

.main-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #2C3E50;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.main-subtitle {
    font-size: 0.9rem;
    color: #718096;
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

.badge-version { background-color: #E9D8FD; color: #553C9A; }
.badge-provider { background-color: #C6F6D5; color: #22543D; }
.badge-model { background-color: #BEE3F8; color: #2B6CB0; }
.badge-hash { background-color: #EDF2F7; color: #4A5568; font-family: monospace; }

/* Sidebar Customization */
section[data-testid="stSidebar"] {
    background-color: #F7FAFC;
    border-right: 1px solid #EDF2F7;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
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


def load_artifacts():
    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    
    system_prompt = system_prompt_path.read_text(encoding="utf-8") if system_prompt_path.exists() else ""
    tool_declarations = load_tool_declarations(tools_path) if tools_path.exists() else []
    return system_prompt_path, tools_path, system_prompt, tool_declarations


def render_sidebar(system_prompt_path: Path, tools_path: Path, system_prompt: str, tool_declarations: list[dict]):
    # Top Action: New Chat Button
    if st.sidebar.button("➕ Cuộc trò chuyện mới", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.transcript = None
        st.session_state.transcript_path = None
        st.session_state.turn_index = 0
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Lịch sử trò chuyện")
    
    # Load and render saved transcript list in ChatGPT sidebar style
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

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Cấu hình Artifact")
    
    # Version selector
    version_input = st.sidebar.selectbox(
        "Phiên bản Version",
        ["v0", "v1", "v2", "v3"],
        index=0,
    )
    
    artifact_ver = build_artifact_version(version_input, system_prompt_path, tools_path)
    st.sidebar.caption(f"**Artifact Hash**: `{artifact_ver.artifact_version}`")
    
    with st.sidebar.expander("📝 Xem System Prompt", expanded=False):
        st.code(system_prompt, language="markdown")
        
    with st.sidebar.expander(f"🛠️ Danh sách Tool ({len(tool_declarations)})", expanded=False):
        for tool in tool_declarations:
            st.markdown(f"**`{tool.get('name')}`**: {tool.get('description', '')[:80]}...")

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
                <span class="badge badge-version">Version: {version_tag}</span>
                <span class="badge badge-provider">Provider: {provider_name}</span>
                <span class="badge badge-model">Model: {default_model}</span>
                <span class="badge badge-hash">Hash: {artifact_ver.artifact_version}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Render Chat Stream
    if not st.session_state.messages:
        st.info("💡 **Chào mừng!** Hãy nhập câu hỏi hoặc yêu cầu nghiên cứu bên dưới. Agent sẽ tự động chạy các tool và in kết quả câu trả lời chi tiết.")

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
                    # Formatted result from tool events if main content is empty
                    formatted_tool_res = format_tool_results_to_markdown(tool_events)
                    if formatted_tool_res:
                        st.markdown(formatted_tool_res)
                    else:
                        st.caption("*(Agent đã thực thi xong)*")

    # Chat Input Box
    user_input = st.chat_input("Nhập câu hỏi hoặc yêu cầu nghiên cứu...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.turn_index += 1
        
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
                {"role": "user", "content": user_input},
            ]

            turn_record = {
                "turn_index": st.session_state.turn_index,
                "started_at": now_iso(),
                "user": user_input,
                "status": "started",
                "assistant_text": None,
                "rounds": [],
                "tool_events": [],
            }

            with st.spinner("🤖 Đang suy luận & thực thi tool..."):
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

            # Update Session History
            st.session_state.history.append({"role": "user", "content": user_input})
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
