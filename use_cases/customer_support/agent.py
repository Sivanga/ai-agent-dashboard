import asyncio
import json
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    tool,
    create_sdk_mcp_server,
)

# ─── Directories ───
KB_DIR = Path(__file__).parent / "knowledge_base"
TICKETS_DIR = Path(__file__).parent / "support_data" / "tickets"
TICKETS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = Path(__file__).parent / "support_data" / "conversation_log.json"


# ─── Custom Tool: Search Knowledge Base ───
@tool("search_knowledge_base", "Search the company knowledge base for answers to customer questions", {
    "query": str,
})
async def search_knowledge_base(args: dict) -> dict:
    query = args["query"].lower()
    query_words = query.split()
    results = []

    for doc in KB_DIR.glob("*.md"):
        content = doc.read_text()
        content_lower = content.lower()

        # Match if ANY query word appears in the document
        if any(word in content_lower for word in query_words):
            lines = content.split("\n")
            relevant = []

            # Find the most relevant section
            for i, line in enumerate(lines):
                if any(word in line.lower() for word in query_words):
                    start = max(0, i - 5)
                    end = min(len(lines), i + 10)
                    relevant = lines[start:end]
                    break

            if not relevant:
                relevant = lines[:20]

            results.append(f"📄 **{doc.stem}**\n" + "\n".join(relevant))

    if not results:
        return {"content": [{"type": "text", "text": "No relevant information found in knowledge base. This may need to be escalated to a human agent."}]}

    return {"content": [{"type": "text", "text": "\n\n---\n\n".join(results)}]}


# ─── Custom Tool: Create Support Ticket ───
@tool("create_ticket", "Create a support ticket when issue cannot be resolved automatically", {
    "customer_name": str,
    "issue_summary": str,
    "priority": str,
    "category": str,
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

    ticket_file = TICKETS_DIR / f"{ticket_id}.json"
    ticket_file.write_text(json.dumps(ticket, indent=2))

    return {"content": [{"type": "text", "text": (
        f"Ticket created successfully!\n"
        f"  Ticket ID: {ticket_id}\n"
        f"  Priority: {args.get('priority', 'medium')}\n"
        f"  Category: {args.get('category', 'general')}\n"
        f"A human agent will follow up within 24 hours."
    )}]}


# ─── Custom Tool: Check Order Status ───
@tool("check_order", "Look up an order by order number", {
    "order_number": str,
})
async def check_order(args: dict) -> dict:
    sample_orders = {
        "ORD-001": {"status": "Delivered", "date": "2026-02-20", "items": "Blue Jacket (M)", "tracking": "RM12345678GB"},
        "ORD-002": {"status": "In Transit", "date": "2026-02-22", "items": "Running Shoes (42)", "tracking": "RM87654321GB"},
        "ORD-003": {"status": "Processing", "date": "2026-02-23", "items": "Wool Scarf, Gloves Set", "tracking": "Not yet assigned"},
    }

    order = sample_orders.get(args["order_number"].upper())
    if not order:
        return {"content": [{"type": "text", "text": f"Order {args['order_number']} not found. Please check the order number and try again."}]}

    return {"content": [{"type": "text", "text": (
        f"Order: {args['order_number'].upper()}\n"
        f"  Status: {order['status']}\n"
        f"  Items: {order['items']}\n"
        f"  Order Date: {order['date']}\n"
        f"  Tracking: {order['tracking']}"
    )}]}


# ─── Custom Tool: Log Conversation ───
@tool("log_conversation", "Log the conversation summary for quality and training purposes", {
    "summary": str,
    "resolved": str,
    "category": str,
})
async def log_conversation(args: dict) -> dict:
    logs = json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
    logs.append({
        "timestamp": datetime.now().isoformat(),
        "summary": args["summary"],
        "resolved": args.get("resolved", "yes"),
        "category": args.get("category", "general"),
    })
    LOG_FILE.write_text(json.dumps(logs, indent=2))
    return {"content": [{"type": "text", "text": "Conversation logged."}]}


# ─── Bundle tools ───
support_tools = create_sdk_mcp_server(
    name="support",
    version="1.0.0",
    tools=[search_knowledge_base, create_ticket, check_order, log_conversation],
)


# ─── System Prompt ───
SYSTEM_PROMPT = """You are a friendly, professional customer support agent for an online retail store.

YOUR TOOLS:
- search_knowledge_base: ALWAYS search this first before answering ANY question about policies, products, shipping, returns, or accounts. Search with simple keywords like "shipping", "return", "password", "warranty", etc.
- check_order: Look up order status when a customer asks about their order
- create_ticket: Escalate to a human agent when you cannot resolve the issue
- log_conversation: Log a summary when the conversation ends

CRITICAL RULES:
1. NEVER say "I don't have that information" without searching the knowledge base first
2. Always search with SHORT keywords, not long sentences. Example: search "shipping" not "do you offer free shipping options"
3. If one search doesn't find results, try different keywords
4. Give specific, accurate answers based ONLY on the knowledge base — never guess or make up policies
5. Be empathetic with frustrated customers
6. Offer additional help before ending the conversation
7. When a customer says goodbye, log the conversation summary

ESCALATION RULES (create a ticket):
- Billing disputes or refund issues over £50
- Account security concerns
- Technical issues you cannot troubleshoot
- Complaints requesting a manager
- Any issue not covered in the knowledge base after multiple searches

SAMPLE ORDER NUMBERS FOR TESTING: ORD-001, ORD-002, ORD-003
"""


# ─── Safety Hook ───
async def safety_hook(tool_name, tool_input, hook_event_name, **kwargs):
    if hook_event_name != "PreToolUse" or tool_name != "Bash":
        return {"decision": "approve"}
    return {"decision": "block", "reason": "Shell commands are disabled for the support agent."}


async def print_response(client):
    try:
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text.strip():
                        print(f"\n💬 {block.text}")
                    elif hasattr(block, "name"):
                        print(f"  🔧 {block.name}")
            elif isinstance(message, ResultMessage):
                if message.subtype == "error":
                    print(f"\n❌ Error: {message.error}")
    except Exception as e:
        if "rate_limit_event" in str(e):
            pass
        else:
            raise


async def main():
    print("=" * 55)
    print("  🏪 Customer Support Agent")
    print("  Powered by Claude AI")
    print("  Type 'quit' to exit")
    print("=" * 55)
    print("\n  Test orders: ORD-001, ORD-002, ORD-003")
    print("  Ask about: returns, shipping, account help, products\n")

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model="haiku",
        mcp_servers={"support": support_tools},
        hooks={
            "PreToolUse": [safety_hook],
        },
        allowed_tools=[
            "Read", "Glob", "Grep",
            "mcp__support__search_knowledge_base",
            "mcp__support__create_ticket",
            "mcp__support__check_order",
            "mcp__support__log_conversation",
        ],
        permission_mode="acceptEdits",
    )

    async with ClaudeSDKClient(options=options) as client:
        while True:
            user_input = input("\n🧑 Customer: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Thank you for contacting us!")
                break
            if not user_input:
                continue

            await client.query(user_input)
            await print_response(client)


asyncio.run(main())
