import asyncio
from pathlib import Path

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
)

DATA_DIR = Path(__file__).parent / "sample_data"

SYSTEM_PROMPT = f"""You are a retail business data analyst.

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
- Keep responses concise and focused on insights
"""


async def print_response(client):
    try:
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text.strip():
                        print(f"\n📊 {block.text}")
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
    print("  📊 Retail Data Analyzer")
    print("  Powered by Claude AI")
    print("  Type 'quit' to exit")
    print("=" * 55)
    print()
    print("  Try asking:")
    print("  • What's my total revenue this year?")
    print("  • Which products are low on stock?")
    print("  • Who are my top 3 customers?")
    print("  • Show me sales breakdown by category")
    print("  • What are my profit margins per product?")
    print()

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model="haiku",
        allowed_tools=[
            "Read", "Bash", "Glob", "Grep", "Write",
        ],
        permission_mode="acceptEdits",
    )

    async with ClaudeSDKClient(options=options) as client:
        while True:
            user_input = input("\n👤 You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Goodbye!")
                break
            if not user_input:
                continue

            await client.query(user_input)
            await print_response(client)


asyncio.run(main())
