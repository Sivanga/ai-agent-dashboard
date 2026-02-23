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
from claude_agent_sdk.types import AgentDefinition

# ─── Directory for persistent notes ───
NOTES_DIR = Path("./assistant_data/notes")
NOTES_DIR.mkdir(parents=True, exist_ok=True)
TODOS_FILE = Path("./assistant_data/todos.json")
TODOS_FILE.parent.mkdir(parents=True, exist_ok=True)


# ─── Custom Tools ───
@tool("save_note", "Save a note with a title and content", {"title": str, "content": str, "tags": str})
async def save_note(args):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = args["title"].replace(" ", "_").lower()[:50]
    filepath = NOTES_DIR / f"{timestamp}_{safe_title}.md"
    filepath.write_text(
        f"# {args['title']}\n**Date:** {datetime.now():%Y-%m-%d %H:%M}\n"
        f"**Tags:** {args.get('tags','')}\n\n---\n\n{args['content']}\n"
    )
    return {"content": [{"type": "text", "text": f"Note saved: {filepath}"}]}


@tool("search_notes", "Search saved notes", {"query": str})
async def search_notes(args):
    results = []
    for f in NOTES_DIR.glob("*.md"):
        if args["query"].lower() in f.read_text().lower():
            results.append(f"📄 {f.name}")
    text = "\n".join(results) if results else "No matching notes found."
    return {"content": [{"type": "text", "text": text}]}


@tool("manage_todos", "Manage to-do list", {"action": str, "item": str})
async def manage_todos(args):
    todos = json.loads(TODOS_FILE.read_text()) if TODOS_FILE.exists() else []
    action = args["action"].lower()
    if action == "add":
        todos.append({"task": args["item"], "done": False, "created": datetime.now().isoformat()})
        TODOS_FILE.write_text(json.dumps(todos, indent=2))
        return {"content": [{"type": "text", "text": f"Added: {args['item']}"}]}
    elif action == "complete":
        try:
            idx = int(args["item"]) - 1
            if 0 <= idx < len(todos):
                todos[idx]["done"] = True
                TODOS_FILE.write_text(json.dumps(todos, indent=2))
                return {"content": [{"type": "text", "text": f"Completed: {todos[idx]['task']}"}]}
        except ValueError:
            pass
        return {"content": [{"type": "text", "text": "Invalid item."}]}
    elif action == "list":
        if not todos:
            return {"content": [{"type": "text", "text": "No to-do items."}]}
        lines = [f"{'✅' if t['done'] else '⬜'} {i}. {t['task']}" for i, t in enumerate(todos, 1)]
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}
    return {"content": [{"type": "text", "text": f"Unknown action: {action}"}]}


assistant_tools = create_sdk_mcp_server("assistant", "1.0.0", [save_note, search_notes, manage_todos])


# ─── Subagents ───
SUBAGENTS = {
    "researcher": AgentDefinition(
        description=(
            "Deep research specialist. Use when the user wants in-depth research "
            "on a topic, comparison of multiple sources, or comprehensive summaries."
        ),
        prompt=(
            "You are a research specialist. When given a topic:\n"
            "1. Search the web for multiple authoritative sources\n"
            "2. Read and analyze the most relevant pages\n"
            "3. Synthesize findings into a clear, structured summary\n"
            "4. Include key facts, dates, and data points\n"
            "5. Note any conflicting information between sources\n"
            "Be thorough but concise. Cite your sources."
        ),
        tools=["WebSearch", "WebFetch", "Read", "Glob"],
        model="haiku",
    ),
    "writer": AgentDefinition(
        description=(
            "Writing specialist. Use for drafting emails, documents, blog posts, "
            "reports, or any creative/professional writing task."
        ),
        prompt=(
            "You are a skilled writer. When given a writing task:\n"
            "1. Understand the audience and purpose\n"
            "2. Create well-structured, polished content\n"
            "3. Use appropriate tone (formal, casual, technical, etc.)\n"
            "4. Save the output as a file when appropriate\n"
            "Be creative yet professional."
        ),
        tools=["Read", "Write", "Edit", "Glob"],
        model="haiku",
    ),
    "analyst": AgentDefinition(
        description=(
            "Data and code analyst. Use for analyzing files, processing data, "
            "running calculations, debugging code, or technical tasks."
        ),
        prompt=(
            "You are a data and code analyst. You can:\n"
            "1. Read and analyze any file type\n"
            "2. Run shell commands for data processing\n"
            "3. Write and execute scripts\n"
            "4. Debug and fix code\n"
            "Be precise and show your work."
        ),
        tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        model="haiku",
    ),
}


# ─── System Prompt ───
SYSTEM_PROMPT = """You are a personal assistant with three specialist subagents:

1. **researcher** — for deep web research and summaries
2. **writer** — for drafting documents, emails, and content
3. **analyst** — for data analysis, code, and technical tasks

You also have direct access to:
- Note management (save_note, search_notes)
- To-do list (manage_todos)
- File operations, web search, and shell commands

GUIDELINES:
- For complex research, delegate to the researcher subagent
- For polished writing tasks, delegate to the writer subagent
- For technical/data tasks, delegate to the analyst subagent
- Handle simple requests (notes, todos, quick lookups) yourself
- After a subagent returns results, offer to save them as a note
"""


async def print_response(client):
    try:
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text.strip():
                        print(f"\n🤖 {block.text}")
                    elif hasattr(block, "name"):
                        if block.name == "Task":
                            agent_type = getattr(block, "input", {}).get("subagent_type", "unknown")
                            print(f"\n  🧠 Delegating to: {agent_type}")
                        else:
                            print(f"  🔧 {block.name}")
            elif isinstance(message, ResultMessage):
                if message.subtype == "error":
                    print(f"\n❌ Error: {message.error}")
    except Exception as e:
        if "rate_limit_event" in str(e):
            pass
        else:
            raise
            
# ─── Safety Hook ───
async def safety_hook(tool_name, tool_input, hook_event_name, **kwargs):
    if hook_event_name != "PreToolUse" or tool_name != "Bash":
        return {"decision": "approve"}

    command = tool_input.get("command", "")
    dangerous_patterns = [
        "rm -rf /", "rm -rf ~", "mkfs", "dd if=",
        ":(){:|:&};:", "chmod -R 777 /", "shutdown",
        "reboot", "> /dev/sda",
    ]

    for pattern in dangerous_patterns:
        if pattern in command:
            return {
                "decision": "block",
                "reason": f"Blocked dangerous command: {pattern}",
            }

    return {"decision": "approve"}

async def main():
    print("=" * 50)
    print("  🤖 Personal Assistant (with subagents)")
    print("  Specialists: researcher, writer, analyst")
    print("  Type 'quit' to exit")
    print("=" * 50)

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model="haiku",
        agents=SUBAGENTS,
        mcp_servers={"assistant": assistant_tools},
        allowed_tools=[
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "WebSearch", "WebFetch",
            "Task",
            "mcp__assistant__save_note",
            "mcp__assistant__search_notes",
            "mcp__assistant__manage_todos",
        ],
        permission_mode="acceptEdits",
         hooks={
            "PreToolUse": [safety_hook],
        },
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
