# AI Agent Dashboard

A full-stack platform for deploying AI-powered business agents, built with the Claude Agent SDK, FastAPI, and React.

![Dashboard](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.12-blue) ![React](https://img.shields.io/badge/React-18-61dafb)

## What This Is

A production-ready framework for building and deploying AI agents that solve real business problems. Each agent has its own tools, knowledge base, and specialised behaviour — accessible through a modern web dashboard.

## Live Agents

### 🏪 Customer Support Agent
- Searches a company knowledge base to answer customer questions
- Looks up order status in real time
- Escalates complex issues by creating support tickets
- Logs conversations for quality assurance

### 📋 Meeting Prep Assistant
- Researches companies via web search
- Generates structured briefing documents
- Saves briefings for future reference
- Covers: company overview, leadership, news, competitors, talking points

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Engine | Claude Agent SDK (Anthropic) |
| Backend | FastAPI + WebSockets |
| Frontend | React + Vite |
| Custom Tools | MCP (Model Context Protocol) |
| Communication | Real-time via WebSocket |

## Architecture
```
┌─────────────┐     WebSocket     ┌──────────────┐     Claude Agent SDK     ┌─────────┐
│   React UI  │ ◄──────────────► │  FastAPI API  │ ◄────────────────────►  │  Claude  │
│  (Vite)     │                  │  (Python)     │                         │  (AI)    │
└─────────────┘                  └──────┬───────┘                         └─────────┘
                                        │
                                 ┌──────┴───────┐
                                 │  MCP Tools   │
                                 │ • KB Search  │
                                 │ • Tickets    │
                                 │ • Orders     │
                                 │ • Briefings  │
                                 └──────────────┘
```

## Project Structure
```
├── web/
│   ├── backend/
│   │   └── server.py              # FastAPI + WebSocket server
│   └── frontend/
│       └── src/
│           ├── App.jsx            # Main dashboard
│           └── components/
│               ├── AgentList.jsx  # Sidebar agent selector
│               └── ChatWindow.jsx # Real-time chat interface
├── use_cases/
│   ├── customer_support/
│   │   ├── agent.py               # Standalone CLI agent
│   │   └── knowledge_base/        # Company FAQ documents
│   └── meeting_prep/
│       ├── agent.py               # Standalone CLI agent
│       └── briefings/             # Generated briefing docs
├── step1_basic.py                 # Tutorial: basic agent
├── step2_conversation.py          # Tutorial: conversation loop
├── step3_tools.py                 # Tutorial: custom tools
└── step4_subagents.py             # Tutorial: multi-agent system
```

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 20+
- Claude Code CLI (`claude` authenticated)

### Setup
```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/ai-agent-dashboard.git
cd ai-agent-dashboard

# Backend
python3.12 -m venv venv
source venv/bin/activate
pip install claude-agent-sdk fastapi uvicorn websockets

# Frontend
cd web/frontend
npm install
```

### Run

**Terminal 1 — Backend:**
```bash
source venv/bin/activate
python3 web/backend/server.py
```

**Terminal 2 — Frontend:**
```bash
cd web/frontend
npm run dev
```

Open **http://localhost:5173**

## Customisation for Clients

This platform is designed to be customised per client:

- **Knowledge Base**: Replace `knowledge_base/*.md` files with client's own FAQs, policies, and documentation
- **Tools**: Add custom MCP tools for client's specific systems (CRM, database, email, etc.)
- **Agents**: Create new agents for any business workflow
- **Branding**: Update the React frontend with client's branding and colours
- **Integrations**: Connect to Slack, email, Google Drive via MCP servers

## Adding a New Agent

1. Create a folder: `use_cases/your_agent/`
2. Define custom tools with `@tool` decorator
3. Add agent config to `web/backend/server.py`
4. Add agent to `AgentList.jsx` and suggestions to `ChatWindow.jsx`

## License

MIT
