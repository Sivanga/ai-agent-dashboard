import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    tool,
    create_sdk_mcp_server,
)

# ─── Paths ───
BASE_DIR = Path(__file__).parent.parent.parent
KB_DIR = BASE_DIR / "use_cases" / "customer_support" / "knowledge_base"
TICKETS_DIR = BASE_DIR / "use_cases" / "customer_support" / "support_data" / "tickets"
TICKETS_DIR.mkdir(parents=True, exist_ok=True)
BRIEFINGS_DIR = BASE_DIR / "use_cases" / "meeting_prep" / "briefings"
BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = BASE_DIR / "use_cases" / "retail_analyzer" / "sample_data"


# ════════════════════════════════════════
#  CUSTOMER SUPPORT TOOLS
# ════════════════════════════════════════

@tool("search_knowledge_base", "Search the company knowledge base", {"query": str})
async def search_knowledge_base(args: dict) -> dict:
    query_words = args["query"].lower().split()
    results = []
    for doc in KB_DIR.glob("*.md"):
        content = doc.read_text()
        if any(word in content.lower() for word in query_words):
            lines = content.split("\n")
            relevant = []
            for i, line in enumerate(lines):
                if any(word in line.lower() for word in query_words):
                    start = max(0, i - 5)
                    end = min(len(lines), i + 10)
                    relevant = lines[start:end]
                    break
            if not relevant:
                relevant = lines[:20]
            results.append(f"**{doc.stem}**\n" + "\n".join(relevant))
    if not results:
        return {"content": [{"type": "text", "text": "No relevant information found. May need escalation."}]}
    return {"content": [{"type": "text", "text": "\n\n---\n\n".join(results)}]}


@tool("create_ticket", "Create a support ticket", {
    "customer_name": str, "issue_summary": str, "priority": str, "category": str,
})
async def create_ticket(args: dict) -> dict:
    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    ticket = {
        "ticket_id": ticket_id,
        "customer_name": args["customer_name"],
        "issue_summary": args["issue_summary"],
        "priority": args.get("priority", "medium"),
        "category": args.get("category", "general"),
        "status": "open",
        "created_at": datetime.now().isoformat(),
    }
    (TICKETS_DIR / f"{ticket_id}.json").write_text(json.dumps(ticket, indent=2))
    return {"content": [{"type": "text", "text": f"Ticket {ticket_id} created. A human agent will follow up within 24 hours."}]}


@tool("check_order", "Look up an order by order number", {"order_number": str})
async def check_order(args: dict) -> dict:
    orders = {
        "ORD-001": {"status": "Delivered", "date": "2026-02-20", "items": "Blue Jacket (M)", "tracking": "RM12345678GB"},
        "ORD-002": {"status": "In Transit", "date": "2026-02-22", "items": "Running Shoes (42)", "tracking": "RM87654321GB"},
        "ORD-003": {"status": "Processing", "date": "2026-02-23", "items": "Wool Scarf, Gloves Set", "tracking": "Not yet assigned"},
    }
    order = orders.get(args["order_number"].upper())
    if not order:
        return {"content": [{"type": "text", "text": f"Order {args['order_number']} not found."}]}
    return {"content": [{"type": "text", "text": f"Order: {args['order_number'].upper()}\nStatus: {order['status']}\nItems: {order['items']}\nTracking: {order['tracking']}"}]}


support_tools = create_sdk_mcp_server("support", "1.0.0", [search_knowledge_base, create_ticket, check_order])


# ════════════════════════════════════════
#  MEETING PREP TOOLS
# ════════════════════════════════════════

@tool("save_briefing", "Save a meeting briefing document", {"company_name": str, "content": str, "meeting_date": str})
async def save_briefing(args: dict) -> dict:
    safe_name = args["company_name"].replace(" ", "_").lower()[:50]
    date_str = args.get("meeting_date", datetime.now().strftime("%Y-%m-%d"))
    filepath = BRIEFINGS_DIR / f"{date_str}_{safe_name}_briefing.md"
    filepath.write_text(args["content"])
    return {"content": [{"type": "text", "text": f"Briefing saved: {filepath.name}"}]}


prep_tools = create_sdk_mcp_server("prep", "1.0.0", [save_briefing])


# ════════════════════════════════════════
#  AGENT CONFIGS
# ════════════════════════════════════════

AGENTS = {
    "customer_support": {
        "model": "haiku",
        "system_prompt": """You are a friendly customer support agent for an online retail store.
ALWAYS search the knowledge base with short keywords before answering questions.
Never say "I don't have that information" without searching first.
Give specific answers based on the knowledge base. Never guess policies.
Be empathetic. Offer additional help before ending conversations.
SAMPLE ORDERS: ORD-001, ORD-002, ORD-003""",
        "mcp_servers": {"support": support_tools},
        "allowed_tools": [
            "Read", "Glob", "Grep",
            "mcp__support__search_knowledge_base",
            "mcp__support__create_ticket",
            "mcp__support__check_order",
        ],
    },
    "meeting_prep": {
        "model": "haiku",
        "system_prompt": """You are a meeting preparation assistant.
When asked to prepare a briefing:
1. Do only 1 web search with short keywords
2. Combine search results with your existing knowledge
3. Generate a briefing with: Company Overview, Key People, Recent News, Products, Competitors, Talking Points
4. Save the briefing using save_briefing
Be concise — briefings should be a 2-minute read.""",
        "mcp_servers": {"prep": prep_tools},
        "allowed_tools": [
            "Read", "Glob", "Grep", "Write",
            "WebSearch", "WebFetch",
            "mcp__prep__save_briefing",
        ],
    },
    "retail_analyzer": {
        "model": "haiku",
        "system_prompt": f"""You are a retail business data analyst.

DATA FILES (use these exact paths with Bash + Python):
- {DATA_DIR}/sales_2026.csv — Sales transactions (date, product, category, quantity, unit_price, total, customer_type, payment_method)
- {DATA_DIR}/inventory.csv — Stock levels (product, category, in_stock, reorder_level, cost_price, retail_price, supplier)
- {DATA_DIR}/customers.csv — Customer data (name, type, total_spent, orders_count, loyalty_points, city)

HOW TO ANALYZE:
- ALWAYS use Bash to run Python pandas commands to read and analyze data
- Do everything in a single python3 -c command, for example:
  python3 -c "import pandas as pd; df = pd.read_csv('{DATA_DIR}/sales_2026.csv'); print('Total Revenue: £' + str(round(df['total'].sum(), 2)))"
- NEVER just read the file — always calculate with pandas
- Give specific numbers, percentages, and rankings
- Flag problems (low stock items where in_stock < reorder_level)
- Compare metrics when possible
- Suggest actionable business decisions
- Keep responses concise and focused on insights""",
        "mcp_servers": {},
        "allowed_tools": [
            "Read", "Bash", "Glob", "Grep", "Write",
        ],
    },
}


# ════════════════════════════════════════
#  FASTAPI APP
# ════════════════════════════════════════

app = FastAPI(title="AI Agent Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await websocket.accept()

    if agent_id not in AGENTS:
        await websocket.send_json({"type": "error", "text": f"Unknown agent: {agent_id}"})
        await websocket.close()
        return

    config = AGENTS[agent_id]

    options = ClaudeAgentOptions(
        system_prompt=config["system_prompt"],
        model=config.get("model", "haiku"),
        mcp_servers=config.get("mcp_servers", {}),
        allowed_tools=config["allowed_tools"],
        permission_mode="acceptEdits",
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            await websocket.send_json({"type": "status", "text": "Connected"})

            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                user_text = message.get("text", "")
                if not user_text:
                    continue

                await websocket.send_json({"type": "status", "text": "Thinking..."})
                await client.query(user_text)

                try:
                    async for msg in client.receive_response():
                        if isinstance(msg, AssistantMessage):
                            for block in msg.content:
                                if hasattr(block, "text") and block.text.strip():
                                    await websocket.send_json({"type": "assistant", "text": block.text})
                                elif hasattr(block, "name"):
                                    await websocket.send_json({"type": "tool", "text": f"Using: {block.name}"})
                        elif isinstance(msg, ResultMessage):
                            if msg.subtype == "error":
                                await websocket.send_json({"type": "error", "text": str(msg.error)})
                except Exception as e:
                    if "rate_limit_event" not in str(e):
                        await websocket.send_json({"type": "error", "text": str(e)})

                await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
