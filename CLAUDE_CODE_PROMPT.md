# Claude Code Prompt: AI Agent Dashboard

## Instructions

Build a full-stack AI agent dashboard from scratch. Read the ARCHITECTURE.md file first for complete specifications.

The project is an AI-powered business tool platform with 3 agents:
1. **Customer Support** — answers questions from a knowledge base, checks orders, creates tickets
2. **Meeting Prep** — researches companies via web search, generates briefing docs
3. **Retail Data Analyzer** — analyzes sales/inventory/customer CSVs with Python pandas

## Build Order

Follow this exact sequence:

### Phase 1: Project Setup
1. Create project structure as defined in ARCHITECTURE.md
2. Set up Python venv with: claude-agent-sdk, fastapi, uvicorn, websockets, pandas
3. Set up React frontend with Vite: `npm create vite@latest . -- --template react`
4. Create .gitignore (exclude: venv/, node_modules/, __pycache__, .env, support_data/, briefings/, assistant_data/, .DS_Store)

### Phase 2: Knowledge Base & Sample Data
Create all content files exactly as specified in ARCHITECTURE.md:
- 4 markdown files in use_cases/customer_support/knowledge_base/
- 3 CSV files in use_cases/retail_analyzer/sample_data/
- Create empty directories: support_data/tickets/, briefings/

### Phase 3: Backend (web/backend/server.py)
Build a single server.py containing:
1. All MCP tool definitions (search_knowledge_base, create_ticket, check_order, save_briefing)
2. AGENTS config dict with 3 agents (see ARCHITECTURE.md for exact configs)
3. FastAPI app with CORS, health endpoint, WebSocket endpoint
4. WebSocket handler that creates per-connection ClaudeSDKClient
5. Rate limit error handling: catch "rate_limit_event" in str(e), silently pass

Key implementation details:
- search_knowledge_base: split query into words, match ANY word, return surrounding context
- Retail analyzer: embed exact DATA_DIR paths in system prompt, instruct to use python3 -c with pandas
- All agents use permission_mode="acceptEdits"

### Phase 4: Frontend
Build 4 files:
1. **src/App.css** — Complete dark theme (see ARCHITECTURE.md for exact colors and responsive breakpoints)
2. **src/App.jsx** — Layout with sidebar + content, welcome screen with 3 feature cards
3. **src/components/AgentList.jsx** — 3 agent cards with icons, highlight active
4. **src/components/ChatWindow.jsx** — WebSocket chat with:
   - Connection management (connect on mount, reconnect on agent switch)
   - Message types: user, assistant, tool, error
   - SUGGESTIONS object with example prompts per agent as clickable pill buttons
   - Typing indicator (3 bouncing dots)
   - Auto-scroll to bottom
   - Disabled input when not connected

### Phase 5: Standalone CLI Agents
Create agent.py in each use_case folder — standalone terminal versions of each agent for testing without the web UI. These should have the same tools and system prompts as the backend but run independently with input() loops.

### Phase 6: README.md
Create a professional README with: project description, architecture diagram (ASCII), features list, tech stack table, project structure, setup instructions (prerequisites, backend setup, frontend setup), how to run, customization guide for clients, how to add new agents.

## Critical Implementation Notes

1. **Rate limit handling is essential.** Every message receive loop MUST be wrapped in try/except catching "rate_limit_event". Without this, the app crashes after every response.

2. **Knowledge base search must split by words.** Searching for "free shipping" as an exact string won't find "Free Shipping" section. Split into ["free", "shipping"] and match ANY word.

3. **Retail analyzer must use Bash + pandas.** Don't tell it to read files and calculate — tell it to run python3 -c one-liners. Include exact file paths in the system prompt.

4. **System prompts matter hugely.** Customer support must be told to search with SHORT keywords (not full sentences). Meeting prep must be limited to 1 search to avoid rate limits.

5. **All paths should use Path(__file__).parent** for portability. Never hardcode absolute paths.

6. **Frontend WebSocket messages** follow this protocol:
   - Client sends: {"text": "user message"}
   - Server sends: {"type": "status|assistant|tool|error|done", "text": "..."}

7. **Empty src/index.css** — all styles go in App.css to keep things simple.

8. **MCP tool return format:** All tools must return {"content": [{"type": "text", "text": "..."}]}
