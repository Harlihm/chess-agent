import base64
import html
import json
import os
import re
from pathlib import Path

import chess
import chess.svg
import streamlit as st
from autogen import ConversableAgent, register_function
from autogen.io import IOStream
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_API_KEY = os.getenv("MINIMAX_API_KEY", "")
DEFAULT_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
DEFAULT_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M3")

WHITE_SYSTEM = (
    "You are a friendly chess grandmaster playing as White against Black. "
    "On every turn: 1) call available_moves() to get legal UCI moves, "
    "2) call execute_move(move) exactly once with a move from that list (e.g. e2e4). "
    "Alongside your tool calls, add ONE short conversational sentence to your opponent "
    "about your move or the position (banter is welcome). "
    "Never print ASCII boards or long analysis, and never skip the tool calls."
)
BLACK_SYSTEM = (
    "You are a witty chess grandmaster playing as Black against White. "
    "On every turn: 1) call available_moves() to get legal UCI moves, "
    "2) call execute_move(move) exactly once with a move from that list (e.g. e7e5). "
    "Alongside your tool calls, add ONE short conversational sentence to your opponent "
    "about your move or the position (banter is welcome). "
    "Never print ASCII boards or long analysis, and never skip the tool calls."
)

ROLE_META = {
    "Agent_White": {"label": "White", "tone": "white"},
    "Agent_Black": {"label": "Black", "tone": "black"},
    "Game_Master": {"label": "Arbiter", "tone": "arbiter"},
}

THINK_RE = re.compile(r"<think>.*?(?:</think>|$)", re.DOTALL)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Figtree:wght@400;500;600;700&display=swap');

:root {
  --ink: #14201a;
  --ink-soft: #3d4f45;
  --mist: #dfe8e1;
  --paper: #f3f6f2;
  --leaf: #1f6b45;
  --leaf-deep: #154f33;
  --brass: #b8892d;
  --board-frame: #2a3a31;
  --chat-bg: rgba(255, 255, 255, 0.55);
  --radius: 18px;
}

html, body, [data-testid="stApp"] {
  background:
    radial-gradient(1200px 600px at 12% -10%, rgba(31, 107, 69, 0.16), transparent 55%),
    radial-gradient(900px 500px at 100% 0%, rgba(184, 137, 45, 0.12), transparent 50%),
    linear-gradient(165deg, #e8efe9 0%, #f5f7f3 42%, #e4ebe5 100%) !important;
  color: var(--ink);
  font-family: 'Figtree', sans-serif;
}

[data-testid="stHeader"],
[data-testid="stToolbar"],
#MainMenu,
footer,
[data-testid="stDecoration"],
[data-testid="stSidebar"],
[data-testid="collapsedControl"] {
  display: none !important;
  visibility: hidden !important;
}

.block-container {
  padding-top: 1.4rem !important;
  padding-bottom: 2.5rem !important;
  max-width: 1180px !important;
}

.hero {
  animation: rise 0.7s ease both;
  margin-bottom: 1.35rem;
}

.brand {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: clamp(2.4rem, 5vw, 3.6rem);
  letter-spacing: -0.045em;
  line-height: 0.95;
  color: var(--ink);
  margin: 0;
}

.brand span {
  color: var(--leaf);
}

.tagline {
  margin: 0.7rem 0 0;
  max-width: 34rem;
  color: var(--ink-soft);
  font-size: 1.05rem;
  line-height: 1.45;
  animation: rise 0.85s ease both;
}

.status-strip {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  align-items: center;
  animation: rise 1s ease both;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: rgba(20, 32, 26, 0.06);
  color: var(--ink-soft);
  font-size: 0.82rem;
  font-weight: 600;
}

.chip.live {
  background: rgba(31, 107, 69, 0.12);
  color: var(--leaf-deep);
}

.chip.live::before {
  content: "";
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--leaf);
  box-shadow: 0 0 0 0 rgba(31, 107, 69, 0.5);
  animation: pulse 1.6s ease infinite;
}

.stage {
  display: grid;
  grid-template-columns: minmax(280px, 1.05fr) minmax(280px, 1fr);
  gap: 1.25rem;
  align-items: start;
}

@media (max-width: 900px) {
  .stage { grid-template-columns: 1fr; }
}

.panel {
  border-radius: var(--radius);
  background: linear-gradient(180deg, rgba(255,255,255,0.72), rgba(255,255,255,0.42));
  border: 1px solid rgba(20, 32, 26, 0.08);
  backdrop-filter: blur(10px);
  padding: 1rem 1rem 1.15rem;
  animation: rise 0.9s ease both;
}

.panel-label {
  font-family: 'Syne', sans-serif;
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin: 0 0 0.75rem;
}

.board-shell {
  background: linear-gradient(145deg, #354840, #1d2b24);
  border-radius: 16px;
  padding: 0.85rem;
  animation: settle 0.9s ease both;
}

.board-shell .board-img,
.board-shell img {
  width: 100% !important;
  height: auto !important;
  display: block;
  border-radius: 8px;
}

.move-line {
  margin-top: 0.85rem;
  min-height: 1.4rem;
  font-weight: 600;
  color: var(--ink);
  font-size: 0.98rem;
}

.chat-scroll {
  height: 540px;
  overflow-y: auto;
  padding-right: 0.35rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  scroll-behavior: smooth;
}

.chat-empty {
  margin: auto;
  text-align: center;
  color: var(--ink-soft);
  padding: 2rem 1rem;
}

.bubble {
  border-radius: 14px;
  padding: 0.75rem 0.9rem;
  background: var(--chat-bg);
  border: 1px solid rgba(20, 32, 26, 0.07);
  animation: slide 0.35s ease both;
}

.bubble.white {
  border-left: 3px solid #f0f3ee;
  background: rgba(255,255,255,0.78);
}

.bubble.black {
  border-left: 3px solid #1a2420;
  background: rgba(26, 36, 32, 0.08);
}

.bubble.arbiter {
  border-left: 3px solid var(--brass);
  background: rgba(184, 137, 45, 0.1);
}

.bubble-meta {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: 0.3rem;
}

.bubble-body {
  color: var(--ink);
  font-size: 0.95rem;
  line-height: 1.45;
}

.bubble-body em {
  color: var(--leaf-deep);
  font-style: italic;
}

.actions {
  margin-top: 1.1rem;
  animation: rise 1.05s ease both;
}

div[data-testid="stButton"] > button {
  border-radius: 999px !important;
  font-family: 'Figtree', sans-serif !important;
  font-weight: 700 !important;
  padding: 0.55rem 1.25rem !important;
  border: none !important;
  transition: transform 0.18s ease, background 0.18s ease !important;
}

div[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, var(--leaf), var(--leaf-deep)) !important;
  color: #f7faf7 !important;
}

div[data-testid="stButton"] > button[kind="secondary"],
div[data-testid="stButton"] > button:not([kind="primary"]) {
  background: rgba(20, 32, 26, 0.08) !important;
  color: var(--ink) !important;
}

div[data-testid="stButton"] > button:hover {
  transform: translateY(-1px);
}

.history-rail {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.history-pill {
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.3rem 0.65rem;
  border-radius: 999px;
  background: rgba(20, 32, 26, 0.07);
  color: var(--ink-soft);
}

@keyframes rise {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes settle {
  from { opacity: 0; transform: scale(0.97) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

@keyframes slide {
  from { opacity: 0; transform: translateX(10px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(31, 107, 69, 0.45); }
  70% { box-shadow: 0 0 0 8px rgba(31, 107, 69, 0); }
  100% { box-shadow: 0 0 0 0 rgba(31, 107, 69, 0); }
}
</style>
"""


def init_state() -> None:
    defaults = {
        "minimax_api_key": DEFAULT_API_KEY or None,
        "minimax_base_url": DEFAULT_BASE_URL,
        "minimax_model": DEFAULT_MODEL,
        "board": chess.Board(),
        "made_move": False,
        "move_history": [],
        "move_labels": [],
        "game_summary": None,
        "chat_log": [],
        "game_running": False,
        "last_status": "Ready for a full match.",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    st.session_state.max_turns = 250


st.set_page_config(
    page_title="AI CHESS BATTLE",
    layout="wide",
    initial_sidebar_state="collapsed",
)
init_state()
st.markdown(APP_CSS, unsafe_allow_html=True)


def clean_text(text: str) -> str:
    text = THINK_RE.sub("", str(text))
    text = text.replace("</think>", "").replace("<think>", "")
    return ANSI_RE.sub("", text).strip()


def format_chat_body(text: str) -> str:
    """Escape user/agent text, then apply safe **bold** markers only."""
    escaped = html.escape(clean_text(text))
    escaped = escaped.replace("\n", "<br>")
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def svg_to_img_tag(svg: str) -> str:
    """Embed SVG as an <img> so Streamlit's HTML sanitizer does not strip it."""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (
        f'<img class="board-img" alt="Chess board" '
        f'src="data:image/svg+xml;base64,{encoded}" />'
    )


def board_to_svg(board: chess.Board, last_move: chess.Move | None = None, size: int = 440) -> str:
    kwargs = {
        "size": size,
        "coordinates": True,
        "colors": {
            "square light": "#e8efe4",
            "square dark": "#4f7a5c",
            "margin": "#24352c",
            "coord": "#d7e2d9",
            "inner border": "#24352c",
            "outer border": "#24352c",
        },
    }
    if last_move is not None:
        kwargs["arrows"] = [(last_move.from_square, last_move.to_square)]
        kwargs["fill"] = {last_move.from_square: "#b8892d55", last_move.to_square: "#b8892d88"}
    return chess.svg.board(board, **kwargs)


def chat_html(entries: list[dict]) -> str:
    if not entries:
        return """
        <div class="chat-scroll" id="agent-chat-scroll">
          <div class="chat-empty">
            Press <strong>Start Game</strong> and the agents will talk while they play.
          </div>
        </div>
        """

    bubbles = []
    for entry in entries:
        role = entry.get("role", "System")
        meta = ROLE_META.get(role, {"label": role.replace("_", " "), "tone": "arbiter"})
        body = format_chat_body(entry.get("content", ""))
        bubbles.append(
            f"""
            <div class="bubble {meta['tone']}">
              <div class="bubble-meta">{html.escape(meta['label'])}</div>
              <div class="bubble-body">{body}</div>
            </div>
            """
        )
    return f"""
    <div class="chat-scroll" id="agent-chat-scroll">
      {"".join(bubbles)}
      <div id="agent-chat-end"></div>
    </div>
    <script>
      (function () {{
        const el = document.getElementById("agent-chat-scroll");
        if (!el) return;
        requestAnimationFrame(function () {{
          el.scrollTop = el.scrollHeight;
        }});
      }})();
    </script>
    """


def render_chat(container, entries: list[dict]) -> None:
    container.html(
        f"""
        <div class="panel">
          <p class="panel-label">Table talk</p>
          {chat_html(entries)}
        </div>
        """,
        unsafe_allow_javascript=True,
    )


def render_board_panel(container, status: str, svg: str, labels: list[str]) -> None:
    container.html(
        f"""
        <div class="panel">
          <p class="panel-label">The board</p>
          <div class="move-line">{html.escape(status)}</div>
          <div class="board-shell">{svg_to_img_tag(svg)}</div>
          {history_html(labels[-12:]) if labels else ""}
        </div>
        """
    )


def history_html(labels: list[str]) -> str:
    if not labels:
        return ""
    pills = "".join(
        f'<span class="history-pill">{html.escape(f"{i}. {label}")}</span>'
        for i, label in enumerate(labels, 1)
    )
    return f'<div class="history-rail">{pills}</div>'


def minimax_llm_config():
    return {
        "config_list": [
            {
                "model": st.session_state.minimax_model,
                "api_key": st.session_state.minimax_api_key,
                "base_url": st.session_state.minimax_base_url,
                "api_type": "openai",
            }
        ],
        "cache_seed": None,
    }


class StreamlitIOStream:
    def __init__(self, chat_placeholder, log_list: list[dict]):
        self.chat_placeholder = chat_placeholder
        self.log_list = log_list
        self._seen_texts: set[tuple] = set()

    def print(self, *objects, sep: str = " ", end: str = "\n", flush: bool = False) -> None:
        return

    def input(self, prompt: str = "", *, password: bool = False) -> str:
        return ""

    def send(self, message) -> None:
        try:
            data = message.model_dump() if hasattr(message, "model_dump") else {}
        except Exception:
            return

        event_type = data.get("type", "")
        inner = data.get("content")
        if not isinstance(inner, dict):
            inner = data

        entry = self._event_to_entry(event_type, inner)
        if entry:
            self._append(**entry)

    def _append(self, role: str, content: str) -> None:
        content = content.strip()
        if not content:
            return
        key = (role, content)
        if key in self._seen_texts:
            return
        self._seen_texts.add(key)
        self.log_list.append({"role": role, "content": content})
        render_chat(self.chat_placeholder, self.log_list)

    def _event_to_entry(self, event_type: str, d: dict) -> dict | None:
        sender = d.get("sender") or d.get("sender_name") or "System"

        if event_type == "text":
            # Arbiter only announces real move results (executed_function), not relays.
            if sender == "Game_Master":
                return None
            text = clean_text(d.get("content") or "")
            if not text:
                return None
            low = text.lower()
            if "via tools only" in low or "call available_moves" in low:
                return None
            return {"role": sender, "content": text}

        if event_type == "tool_call":
            parts = []
            speech = clean_text(d.get("content") or "")
            if speech:
                parts.append(speech)
            for call in d.get("tool_calls") or []:
                fn = call.get("function") or {}
                name = fn.get("name")
                if name == "available_moves":
                    parts.append("checking legal moves…")
                elif name == "execute_move":
                    move = ""
                    try:
                        move = (json.loads(fn.get("arguments") or "{}")).get("move", "")
                    except Exception:
                        pass
                    parts.append(f"plays **{move}**" if move else "makes a move…")
                elif name:
                    parts.append(f"calls {name}…")
            if not parts:
                return None
            return {"role": sender, "content": "\n\n".join(parts)}

        if event_type == "executed_function":
            result = str(d.get("content") or "")
            if d.get("func_name") == "execute_move":
                return {"role": "Game_Master", "content": result}
            return None

        return None


# --- Hero ---
live_chip = (
    '<span class="chip live">Match in progress</span>'
    if st.session_state.game_running
    else '<span class="chip">Spectator mode</span>'
)
st.markdown(
    f"""
    <div class="hero">
      <h1 class="brand">AI <span>CHESS</span> BATTLE</h1>
      <p class="tagline">Two grandmasters agents play a full game. You watch the board and their conversation in real time.</p>
      <div class="status-strip">
        {live_chip}
        <span class="chip">Powered by MiniMax-M3</span>
        <span class="chip">{len(st.session_state.move_labels)} moves</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.minimax_api_key:
    st.warning("Set MINIMAX_API_KEY in your `.env` file to start.")
    st.stop()

# --- Controls ---
col1, col2, _ = st.columns([1, 1, 3])
start = col1.button("Start Game", type="primary", use_container_width=True)
reset = col2.button("Reset", use_container_width=True)

# --- Stage ---
board_col, chat_col = st.columns([1.05, 1], gap="large")

with board_col:
    board_panel = st.empty()
    last_move = st.session_state.board.peek() if st.session_state.board.move_stack else None
    render_board_panel(
        board_panel,
        st.session_state.last_status,
        board_to_svg(st.session_state.board, last_move=last_move),
        st.session_state.move_labels,
    )

with chat_col:
    chat_placeholder = st.empty()
    render_chat(chat_placeholder, st.session_state.chat_log)


def available_moves() -> str:
    moves = [str(move) for move in st.session_state.board.legal_moves]
    return "Available moves are: " + ",".join(moves)


def execute_move(move: str) -> str:
    try:
        chess_move = chess.Move.from_uci(move)
        if chess_move not in st.session_state.board.legal_moves:
            return f"Invalid move: {move}. Call available_moves() and pick a legal UCI move."

        st.session_state.board.push(chess_move)
        st.session_state.made_move = True

        board_svg = board_to_svg(st.session_state.board, last_move=chess_move)
        st.session_state.move_history.append(board_svg)

        moved_piece = st.session_state.board.piece_at(chess_move.to_square)
        piece_unicode = moved_piece.unicode_symbol()
        piece_type_name = chess.piece_name(moved_piece.piece_type)
        piece_name = piece_type_name.capitalize() if piece_unicode.isupper() else piece_type_name

        from_square = chess.SQUARE_NAMES[chess_move.from_square]
        to_square = chess.SQUARE_NAMES[chess_move.to_square]
        player = "White" if st.session_state.board.turn == chess.BLACK else "Black"
        move_desc = f"{player}: {piece_name} ({piece_unicode}) {from_square}→{to_square}"
        st.session_state.move_labels.append(move_desc)

        if st.session_state.board.is_checkmate():
            winner = "White" if st.session_state.board.turn == chess.BLACK else "Black"
            move_desc += f" — Checkmate! {winner} wins!"
        elif st.session_state.board.is_stalemate():
            move_desc += " — Stalemate!"
        elif st.session_state.board.is_insufficient_material():
            move_desc += " — Draw (insufficient material)."
        elif st.session_state.board.is_check():
            move_desc += " — Check!"

        st.session_state.last_status = move_desc
        render_board_panel(
            board_panel,
            move_desc,
            board_svg,
            st.session_state.move_labels,
        )
        return move_desc
    except ValueError:
        return f"Invalid move format: {move}. Use UCI (e.g. e2e4)."


def check_made_move(msg):
    if st.session_state.made_move:
        st.session_state.made_move = False
        return True
    return False


if reset:
    st.session_state.board.reset()
    st.session_state.made_move = False
    st.session_state.move_history = []
    st.session_state.move_labels = []
    st.session_state.game_summary = None
    st.session_state.chat_log = []
    st.session_state.game_running = False
    st.session_state.last_status = "Ready for a full match."
    st.rerun()

if start:
    st.session_state.board.reset()
    st.session_state.made_move = False
    st.session_state.move_history = []
    st.session_state.move_labels = []
    st.session_state.game_summary = None
    st.session_state.chat_log = []
    st.session_state.game_running = True
    st.session_state.last_status = "Match underway — White to move."

    render_board_panel(
        board_panel,
        st.session_state.last_status,
        board_to_svg(st.session_state.board),
        [],
    )
    render_chat(chat_placeholder, st.session_state.chat_log)

    try:
        llm_config = minimax_llm_config()

        agent_white = ConversableAgent(
            name="Agent_White",
            system_message=WHITE_SYSTEM,
            llm_config=llm_config,
        )
        agent_black = ConversableAgent(
            name="Agent_Black",
            system_message=BLACK_SYSTEM,
            llm_config=llm_config,
        )
        game_master = ConversableAgent(
            name="Game_Master",
            llm_config=False,
            is_termination_msg=check_made_move,
            default_auto_reply="Call available_moves() then execute_move(uci).",
            human_input_mode="NEVER",
        )

        for agent in (agent_white, agent_black):
            register_function(
                execute_move,
                caller=agent,
                executor=game_master,
                name="execute_move",
                description="Make a chess move. Argument move must be UCI, e.g. e2e4.",
            )
            register_function(
                available_moves,
                caller=agent,
                executor=game_master,
                name="available_moves",
                description="Return the list of legal UCI moves for the current position.",
            )

        agent_white.register_nested_chats(
            trigger=agent_black,
            chat_queue=[
                {
                    "sender": game_master,
                    "recipient": agent_white,
                    "summary_method": "last_msg",
                }
            ],
        )
        agent_black.register_nested_chats(
            trigger=agent_white,
            chat_queue=[
                {
                    "sender": game_master,
                    "recipient": agent_black,
                    "summary_method": "last_msg",
                }
            ],
        )

        ui_stream = StreamlitIOStream(chat_placeholder, st.session_state.chat_log)
        with IOStream.set_default(ui_stream):
            chat_result = agent_black.initiate_chat(
                recipient=agent_white,
                message="Let's play a full game of chess. White moves first.",
                max_turns=st.session_state.max_turns,
                summary_method="last_msg",
            )

        st.session_state.game_summary = getattr(chat_result, "summary", None) or ""
        st.session_state.game_running = False
        if not st.session_state.move_history:
            st.session_state.last_status = "No moves recorded — agents may have skipped tools."
        else:
            st.session_state.last_status = (
                f"Match finished — {len(st.session_state.move_labels)} moves played."
            )
        st.rerun()

    except Exception as e:
        st.session_state.game_running = False
        st.error(f"An error occurred: {e}. Check your MiniMax API key / credits and try again.")
