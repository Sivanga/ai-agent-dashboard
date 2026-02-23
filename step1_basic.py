import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage
from claude_agent_sdk.types import TextBlock, ToolUseBlock, ToolResultBlock


async def main():
    print("🤖 Personal Assistant (basic)\n")

    async for message in query(
        prompt="What's today's date? Then list the files in the current directory.",
        options=ClaudeAgentOptions(
            allowed_tools=["Bash", "Glob"],
            permission_mode="acceptEdits",
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"  🔧 Using tool: {block.name}")
        elif isinstance(message, ResultMessage):
            print("\n✅ Done!")


asyncio.run(main())