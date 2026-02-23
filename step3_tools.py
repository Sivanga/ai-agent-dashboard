import asyncio
import json
import os
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

# ─── Directory for persistent notes ───
NOTES_DIR = Path("./assistant_data/notes")
NOTES_DIR.mkdir(parents=True, exist_ok=True)

TODOS_FILE = Path("./assistant_data/todos.json")
TODOS_FILE.parent.mkdir(parents=True, exist_ok=True)


# ─── Custom Tool: Save a Note ───
@tool("save_note", "Save a note with a title and content to local storage", {
    "title": str,
    "content": str,
    "tags": str,
})
async def save_note(args: dict) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = args["title"].replace(" ", "_").lower()[:50]
    filename = f"{timestamp}_{safe_title}.md"
    filepath = NOTES_DIR / filename

    note_content = f"""# {args['title']}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Tags:** {args.get('tags', 'none')}

---

{args['content']}
"""
    filepath.write_text(note_content)
    return {"content": [{"type": "text", "text": f"Note saved: {filepath}"}]}


# ─── Custom Tool: Search Notes ───
@tool("search_notes", "Search saved notes by keyword or tag", {
    "query": str,
})
async def search_notes(args: dict) -> dict:
    query = args["query"].lower()
    results = []

    for note_file in NOTES_DIR.glob("*.md"):
        content = note_file.read_text()
        if query in content.lower():
            preview = content[:200].replace("\n", " ")
            results.append(f"📄 {note_file.name}\n   {preview}...")

    if not results:
        return {"content": [{"type": "text", "text": "No notes found matching your query."}]}

    return {"content": [{"type": "text", "text": "\n\n".join(results)}]}


# ─── Custom Tool: To-Do List ───
@tool("manage_todos", "Add, complete, or list to-do items", {
    "action": str,
    "item": str,
})
async def manage_todos(args: dict) -> dict:
    if TODOS_FILE.exists():
        todos = json.loads(TODOS_FILE.read_text())
    else:
        todos = []

    action = args["action"].lower()

    if action == "add":
        todos.append({
            "task": args["item"],
            "done": False,
            "created": datetime.now().isoformat(),
        })
        TODOS_FILE.write_text(json.dumps(todos, indent=2))
        return {"content": [{"type": "text", "text": f"Added: {args['item']}"}]}

    elif action == "complete":
        try:
            idx = int(args["item"]) - 1
            if 0 <= idx < len(todos):
                todos[idx]["done"] = True
                TODOS_FILE.write_text(json.dumps(todos, indent=2))
                return {"content": [{"type": "text", "text": f"Completed: {todos[idx]['task']}"}]}
            return {"content": [{"type": "text", "text": "Invalid item number."}]}
        except ValueError:
            return {"content": [{"type": "text", "text": "Please provide a number."}]}

    elif action == "list":
        if not todos:
            return {"content": [{"type": "text", "text": "No to-do items yet!"}]}
        lines = []
        for i, t in enumerate(todos, 1):
            status = "✅" if t["done"] else "⬜"
            lines.append(f"  {status} {i}. {t['task']}")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    return {"content": [{"type": "text", "text": f"Unknown action: {action}"}]}


# ─── Bundle tools into an MCP server ───
assistant_tools = create_sdk_mcp_server(
    name="assistant",
    version="1.0.0",
    tools=[save_note, search_notes, manage_todos],
)


# ─── System prompt ───
SYSTEM_PROMPT = """You are a personal assistant with access to custom tools:

CUSTOM TOOLS (use these when relevant):
- save_note: Save notes with titles, content, and tags
- search_notes: Search through saved notes by keyword
- manage_todos: Manage a to-do list (add / complete / list)

BUILT-IN TOOLS:
- WebSearch / WebFetch: Search the web and fetch pages
- Read / Write / Edit: File operations
- Bash: Run shell commands
- Glob / Grep: Find and search files

GUIDELINES:
- Be concise and action-oriented
- Use custom tools for note and to-do management
- Use built-in tools for file ops, web research, and commands
- Format output for terminal readability
"""


async def print_response(client):
    try:
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text.strip():
                        print(f"\n🤖 {block.text}")
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
    print("=" * 50)
    print("  🤖 Personal Assistant (with custom tools)")
    print("  Commands: type naturally, 'quit' to exit")
    print("=" * 50)

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model="haiku",
        mcp_servers={"assistant": assistant_tools},
        allowed_tools=[
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "WebSearch", "WebFetch",
            "mcp__assistant__save_note",
            "mcp__assistant__search_notes",
            "mcp__assistant__manage_todos",
        ],
        permission_mode="acceptEdits",
    )

    async with ClaudeSDKClient(options=options) as client:
        while True:
            user_input = input("\n📝 You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Goodbye!")
                break
            if not user_input:
                continue

            await client.query(user_input)
            await print_response(client)


asyncio.run(main())
