import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    try:
        async for message in query(
            prompt="Say hello",
            options=ClaudeAgentOptions(
                model="haiku",
                allowed_tools=["Bash"],
                permission_mode="acceptEdits",
                hooks={
                    "PreToolUse": [safety_hook],
                },
            ),
        ):
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        print(block.text)
    except Exception as e:
        if "rate_limit_event" in str(e):
            pass  # Ignore this - response already completed
        else:
            raise

asyncio.run(main())
