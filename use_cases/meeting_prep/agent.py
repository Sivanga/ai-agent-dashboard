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
BRIEFINGS_DIR = Path(__file__).parent / "briefings"
BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)


@tool("save_briefing", "Save a meeting briefing document as a markdown file", {
    "company_name": str, "content": str, "meeting_date": str,
})
async def save_briefing(args: dict) -> dict:
    safe_name = args["company_name"].replace(" ", "_").lower()[:50]
    date_str = args.get("meeting_date", datetime.now().strftime("%Y-%m-%d"))
    filepath = BRIEFINGS_DIR / f"{date_str}_{safe_name}_briefing.md"
    filepath.write_text(args["content"])
    return {"content": [{"type": "text", "text": f"Briefing saved: {filepath.name}"}]}


@tool("list_briefings", "List saved meeting briefings", {"search": str})
async def list_briefings(args: dict) -> dict:
    search = args.get("search", "").lower()
    results = []
    for f in sorted(BRIEFINGS_DIR.glob("*.md"), reverse=True):
        if search and search not in f.name.lower():
            continue
        results.append(f.name)
    if not results:
        return {"content": [{"type": "text", "text": "No briefings found."}]}
    return {"content": [{"type": "text", "text": "\n".join(results)}]}


prep_tools = create_sdk_mcp_server("prep", "1.0.0", [save_briefing, list_briefings])


SYSTEM_PROMPT = """You are a meeting preparation assistant. Research companies and generate briefing documents.

When asked to prepare a briefing:
1. Search the web for the company (use SHORT search queries like "Spotify company overview 2026")
2. Search for recent news ("Spotify news 2026")
3. Search for leadership ("Spotify CEO leadership team")
4. Generate a structured briefing with: Company Overview, Key People, Recent News, Products, Financials, Competitors, Talking Points, Questions to Ask
5. Save the briefing using save_briefing

IMPORTANT:
- Use SHORT search queries (2-4 words), not long sentences
- Do only 1 search maximum, then write the briefing combining search results with your existing knowledge
- Be thorough but concise — briefings should be a 2-minute read
- If web search is slow, use your existing knowledge and note what may need verification
"""


async def print_response(client):
    collected_text = []
    try:
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text.strip():
                        print(f"\n📋 {block.text}")
                        collected_text.append(block.text)
                    elif hasattr(block, "name"):
                        print(f"  🔧 {block.name}")
            elif isinstance(message, ResultMessage):
                if message.subtype == "error":
                    print(f"\n❌ Error: {message.error}")
    except Exception as e:
        if "rate_limit_event" in str(e):
            if collected_text:
                print("\n⚠️  Rate limit reached, but response was captured above.")
            else:
                print("\n⚠️  Rate limit reached. Wait 60 seconds and try again.")
                print("    Tip: try a simpler query like 'Tell me about Spotify'")
        else:
            raise


async def main():
    print("=" * 55)
    print("  📋 Meeting Prep Assistant")
    print("  Powered by Claude AI")
    print("  Type 'quit' to exit")
    print("=" * 55)
    print()
    print("  Examples:")
    print("  • Prepare a briefing for a meeting with Stripe")
    print("  • Research Anthropic, I'm meeting their sales team")
    print("  • Show my past briefings")
    print()

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model="haiku",
        mcp_servers={"prep": prep_tools},
        allowed_tools=[
            "Read", "Glob", "Grep", "Write",
            "WebSearch", "WebFetch",
            "mcp__prep__save_briefing",
            "mcp__prep__list_briefings",
        ],
        permission_mode="acceptEdits",
    )

    async with ClaudeSDKClient(options=options) as client:
        while True:
            user_input = input("\n👤 You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Good luck in your meeting!")
                break
            if not user_input:
                continue

            await client.query(user_input)
            await print_response(client)


asyncio.run(main())
