# Ai chess Battle

Two AG2 agents play a full chess game against each other, powered by **MiniMax-M3 API**. A Streamlit UI shows the live board and agent chat. A Game Master agent validates moves and manages turns.

## Setup

1. Use Python 3.10+ (this project was tested with Python 3.14).
2. Install dependencies:

```bash
pip3 install -r requirements.txt
```

3. Create a `.env` file in the project root (already gitignored):

```env
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_BASE_URL=https://api.minimax.io/v1
MINIMAX_MODEL=MiniMax-M3
```

Get a key from [MiniMax Platform](https://platform.minimax.io/). Make sure your Token Plan or Credits have remaining usage.

## Run

```bash
python3 -m streamlit run ai_chess_agent.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

Click **Start Game** to let White and Black play a full game. The board updates live on the left; agent conversation streams on the right.

## How it works

| Role | Job |
|------|-----|
| **Agent White** | MiniMax-M3 player for white |
| **Agent Black** | MiniMax-M3 player for black |
| **Game Master** | Lists legal moves, executes UCI moves, updates the board |

Agents call tools `available_moves()` and `execute_move(move)` through the Game Master.

## Project layout

```
ai_chess_agent.py   # Streamlit app + agents
requirements.txt    # Python dependencies
.env                # Secrets (do not commit)
.gitignore
```

## Notes

- Never commit `.env` — it is listed in `.gitignore`.
- Config (API key, model, base URL) comes only from `.env`.
- A full game can use many API credits.
- If you see a MiniMax `429` / usage limit error, upgrade your plan or buy credits.
- On macOS, use `pip3` / `python3` if `pip` is not found.
