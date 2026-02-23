import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, ResultMessage


SYSTEM_PROMPT = """You are a helpful personal assistant. You can:
- Search the web for information
- Read and write files on the user's computer
- Run shell commands
- Take notes and manage to-do lists
- Summarize documents and web pages

Be concise, friendly, and proactive. When the user asks you to do something,
just do it. Format your responses for terminal readability.
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
    print("  🤖 Personal Assistant")
    print("  Type 'quit' to exit")
    print("=" * 50)

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model="haiku",
        allowed_tools=[
            "Read", "Write", "Edit",
            "Bash",
            "Glob", "Grep",
            "WebSearch", "WebFetch",
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
