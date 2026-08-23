# FinWise DOIT changes

## AI Assistant
- Reworked the chat UI for the FinWise dark theme.
- AI messages now use a dark slate bubble with high-contrast text instead of a white bubble with unreadable light text.
- User messages remain blue and visually distinct.
- Added clearer local-AI status text and a dark input/send area.
- Integrated free local Ollama support using `qwen2.5:7b`.
- Ollama is preferred when enabled; OpenAI remains optional and disabled by default.
- Financial facts still come from FinWise's deterministic database logic.
- The local LLM is used to explain/rephrase verified results rather than invent financial numbers.
- Explicit account/budget/goal creation remains handled by backend logic.

## Dark UI
- Updated shared buttons, cards, inputs and scrollbars for the dark workspace.
- Converted dashboard forecast, budget, alerts, recent-transaction and budget-progress surfaces from white to dark cards.
- Improved dashboard stat-card icon/badge contrast.
- Updated forecast chart axes, grid and tooltip styling for dark mode.
- Updated confirmation dialog styling.

## Settings
- Preserved the existing editable profile implementation and dark preference cards from this project version.

## Configuration
- Added `OLLAMA_ENABLED`, `OLLAMA_BASE_URL`, and `OLLAMA_MODEL` settings.
- Added Ollama instructions to README and `.env.example`.
