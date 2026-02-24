# AI Agent Dashboard — Architecture

## Overview
Full-stack platform for deploying AI-powered business agents. FastAPI backend with WebSocket communication, React frontend, Claude Agent SDK for AI.

## Tech Stack
- **Backend:** Python 3.12, FastAPI, WebSockets, Claude Agent SDK
- **Frontend:** React 18, Vite
- **AI:** Claude Agent SDK with MCP (Model Context Protocol) custom tools
- **Communication:** WebSocket (real-time streaming)

## Project Structure
```
ai-agent-dashboard/
├── web/
│   ├── backend/
│   │   └── server.py                 # FastAPI + WebSocket server, all agent configs
│   └── frontend/
│       ├── package.json
│       └── src/
│           ├── App.jsx                # Main layout: header, sidebar, content area
│           ├── App.css                # All styles (dark theme, responsive)
│           └── components/
│               ├── AgentList.jsx      # Sidebar with agent cards
│               └── ChatWindow.jsx     # Chat UI with WebSocket connection
├── use_cases/
│   ├── customer_support/
│   │   ├── agent.py                   # Standalone CLI version
│   │   └── knowledge_base/
│   │       ├── returns_policy.md
│   │       ├── shipping_info.md
│   │       ├── account_help.md
│   │       └── products_faq.md
│   ├── meeting_prep/
│   │   ├── agent.py                   # Standalone CLI version
│   │   └── briefings/                 # Generated briefings saved here
│   └── retail_analyzer/
│       ├── agent.py                   # Standalone CLI version
│       └── sample_data/
│           ├── sales_2026.csv         # ~25 rows: date, product, category, quantity, unit_price, total, customer_type, payment_method
│           ├── inventory.csv          # ~10 rows: product, category, in_stock, reorder_level, cost_price, retail_price, supplier
│           └── customers.csv          # ~10 rows: customer_id, name, type, total_spent, orders_count, loyalty_points, city
├── .gitignore
└── README.md
```

## Agent Specifications

### 1. Customer Support Agent (model: haiku)
**Purpose:** Answer customer questions using a knowledge base, check orders, escalate issues.

**MCP Tools:**
- `search_knowledge_base(query)` — Searches all .md files in knowledge_base/ folder. Splits query into individual words, matches ANY word against file content. Returns surrounding context (5 lines before, 10 after match).
- `create_ticket(customer_name, issue_summary, priority, category)` — Creates JSON ticket file in support_data/tickets/ with timestamp-based ID (TKT-YYYYMMDDHHMMSS).
- `check_order(order_number)` — Looks up order in hardcoded sample dict. Returns status, items, tracking. Sample orders: ORD-001 (Delivered), ORD-002 (In Transit), ORD-003 (Processing).

**System prompt key rules:**
- ALWAYS search knowledge base with SHORT keywords before answering
- NEVER say "I don't have that information" without searching first
- Escalate: billing disputes >£50, security concerns, complaints requesting manager

**Allowed tools:** Read, Glob, Grep + all 3 MCP tools

### 2. Meeting Prep Agent (model: haiku)
**Purpose:** Research companies via web search and generate structured briefing documents.

**MCP Tools:**
- `save_briefing(company_name, content, meeting_date)` — Saves markdown file to briefings/ folder with format: YYYY-MM-DD_company_briefing.md

**System prompt key rules:**
- Do only 1 web search with short keywords (2-4 words)
- Combine search results with existing knowledge
- Generate briefing with: Company Overview, Key People, Recent News, Products, Competitors, Talking Points
- Save briefing after generating

**Allowed tools:** Read, Glob, Grep, Write, WebSearch, WebFetch + save_briefing MCP tool

### 3. Retail Data Analyzer (model: haiku)
**Purpose:** Analyze sales, inventory, and customer CSV data for business insights.

**No MCP tools** — uses Bash + Python pandas directly.

**System prompt key rules:**
- ALWAYS use Bash with Python pandas to read and analyze data in a single python3 -c command
- Never just read the file — always calculate with pandas
- Give specific numbers, percentages, and rankings
- Flag problems (low stock where in_stock < reorder_level)
- Include exact file paths in the system prompt

**Allowed tools:** Read, Bash, Glob, Grep, Write

## Backend Architecture (server.py)

### FastAPI App
- CORS middleware allowing all origins (dev mode)
- Health endpoint: GET /api/health
- WebSocket endpoint: /ws/{agent_id}

### WebSocket Flow
1. Client connects to /ws/{agent_id}
2. Server validates agent_id exists in AGENTS dict
3. Creates ClaudeSDKClient with agent-specific options
4. Sends {"type": "status", "text": "Connected"}
5. Receives user messages as {"text": "..."}
6. Sends {"type": "status", "text": "Thinking..."}
7. Streams responses:
   - {"type": "assistant", "text": "..."} for text content
   - {"type": "tool", "text": "Using: tool_name"} for tool calls
   - {"type": "error", "text": "..."} for errors
8. Sends {"type": "done"} when response complete
9. Rate limit errors (rate_limit_event) are silently caught

### AGENTS Config Dict
Each agent has: model, system_prompt, mcp_servers, allowed_tools.
All use permission_mode="acceptEdits".

## Frontend Architecture

### App.jsx
- State: selectedAgent (null or agent object)
- Layout: header (fixed) + main (sidebar + content)
- Shows welcome screen with feature cards when no agent selected
- Shows ChatWindow when agent selected

### AgentList.jsx
- Hardcoded AGENTS array: [{id, name, description, icon}]
- Highlights active agent with purple border
- onClick passes agent object to parent

### ChatWindow.jsx
- Creates WebSocket connection on mount and when agent changes
- Manages: messages[], input, status, isLoading
- SUGGESTIONS object maps agent_id to array of example prompts
- Suggestions render as clickable pill buttons in empty state
- Messages render as bubbles: user (purple, right-aligned), assistant (dark, left-aligned), tool (subtle border, italic), error (red tint)
- Typing indicator: 3 bouncing dots animation
- Auto-scrolls to bottom on new messages

### App.css — Dark Theme
- Background: #0f1117
- Sidebar: #1a1b23, 300px wide
- Accent: #6366f1 (indigo/purple)
- Message bubbles: user #6366f1, assistant #1e1f2a
- Tool messages: transparent with border
- Error: #2d1215 background
- Animations: fadeIn on messages, bounce on typing dots
- Scrollbar: thin, dark
- Mobile responsive: sidebar collapses below 768px

## Knowledge Base Content (customer support)

### returns_policy.md
- 30 day returns, original packaging, 5-7 day refunds
- £5.99 return shipping (free for defective)
- Exceptions: sale items, personalized, electronics 14 days, gift cards
- Process: myaccount.example.com → Order History → Return Item → Royal Mail
- Free exchanges for size/color

### shipping_info.md
- Standard 5-7 days (free >£50, else £4.99), Express £9.99, Next Day £14.99, International from £19.99
- Tracking included, emails within 24hrs, track at tracking.example.com
- Issues: missing (wait 48hrs), damaged (photos within 48hrs), wrong item (free replacement)

### account_help.md
- Password reset: myaccount.example.com/reset, 8+ chars, locks after 5 attempts for 30min
- Account management: settings pages for email, payment, address, delete (30 days)
- Loyalty: 1 point/£1, 100 points = £5, Silver 500+/yr, Gold 1000+/yr
- Payments: Visa, MC, Amex, PayPal, Apple/Google Pay, Klarna >£30

### products_faq.md
- Sizing: guide on product page, size up if between
- Care: wash cold, hang dry, wool hand wash, no tumble dry waterproof
- Stock: Notify Me button, restock 2-4 weeks, limited edition not restocked
- Warranty: 1 year (2 for electronics), not wear and tear

## Sample Data (retail analyzer)

### sales_2026.csv (~25 rows)
Products: Winter Jacket (£89.99), Wool Scarf (£24.99), Running Shoes (£119.99), Cotton T-Shirt (£19.99), Leather Belt (£34.99), Denim Jeans (£59.99)
Categories: Outerwear, Accessories, Footwear, Tops, Bottoms
Customer types: new, returning
Payment methods: card, paypal, cash
Date range: Jan-Feb 2026

### inventory.csv (~10 rows)
Same products + Rain Coat, Hiking Boots, Silk Tie, Chino Trousers
Key fields: in_stock, reorder_level (for low stock alerts), cost_price vs retail_price (for margin analysis)
Suppliers: Nordic Textiles, SportStep Ltd, BasicWear Co, CraftLeather, DenimWorks

### customers.csv (~10 rows)
Mix of new and returning customers
Fields: total_spent (£124-£3210), orders_count (1-20), loyalty_points, city
Cities: London, Manchester, Birmingham, Leeds, Bristol, Edinburgh, Cardiff

## Dependencies
```
# Python (in venv)
claude-agent-sdk
fastapi
uvicorn
websockets
pandas

# Node (frontend)
react (via vite template)
```

## Known Issues & Workarounds
1. **Rate limit bug:** SDK v0.1.39 throws "rate_limit_event" parsing error. Wrap all message loops in try/except, catch "rate_limit_event" string, silently pass.
2. **Haiku web search:** Haiku struggles with multi-step search→synthesize tasks. Meeting prep works better with sonnet but costs more.
3. **Retail analyzer:** Telling Claude to "use python3 -c with pandas" in the system prompt produces more reliable results than having it read files and calculate in its head.
