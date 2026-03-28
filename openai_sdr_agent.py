"""
Sales Development Representative (SDR) Agent

Three demo flows showing progressively complex agent patterns:
  1. demo_stream_single — stream a single draft token-by-token (Runner.run_streamed)
  2. demo_pick_best     — parallel generation + explicit Python-orchestrated selection
  3. demo_full_sdr      — full pipeline: sales_manager self-selects + hands off to emailer_agent

Patterns demonstrated: streaming, asyncio.gather, agent-as-tool, handoff, function_tool.
"""

import asyncio

from agents import Agent, Runner, function_tool, trace
from dotenv import load_dotenv
from openai.types.responses import ResponseTextDeltaEvent

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Sales writer agents  (called first: demo_stream_single, demo_parallel_drafts, demo_pick_best)
# ---------------------------------------------------------------------------

COMPANY_CONTEXT = (
    "a company that provides a SaaS tool for ensuring SOC2 compliance and "
    "preparing for audits, powered by AI"
)

sales_agent1 = Agent(
    name="Professional Sales Agent",
    instructions=(
        f"You are a sales agent working for ComplAI, {COMPANY_CONTEXT}. "
        "You write professional, serious cold emails."
    ),
    model="gpt-4o-mini",
)

sales_agent2 = Agent(
    name="Engaging Sales Agent",
    instructions=(
        f"You are a humorous, engaging sales agent working for ComplAI, {COMPANY_CONTEXT}. "
        "You write witty, engaging cold emails that are likely to get a response."
    ),
    model="gpt-4o-mini",
)

sales_agent3 = Agent(
    name="Busy Sales Agent",
    instructions=(
        f"You are a busy sales agent working for ComplAI, {COMPANY_CONTEXT}. "
        "You write concise, to-the-point cold emails."
    ),
    model="gpt-4o-mini",
)

# ---------------------------------------------------------------------------
# Formatter agents  (called by emailer_agent)
# ---------------------------------------------------------------------------

subject_writer = Agent(
    name="Email subject writer",
    instructions=(
        "You write subjects for cold sales emails. "
        "Given an email body, write a subject line likely to get a response."
    ),
    model="gpt-4o-mini",
)

html_converter = Agent(
    name="HTML email body converter",
    instructions=(
        "You convert plain-text email bodies (which may contain markdown) "
        "to HTML with a simple, clear, and compelling layout."
    ),
    model="gpt-4o-mini",
)

# ---------------------------------------------------------------------------
# Email tools  (called by emailer_agent)
# ---------------------------------------------------------------------------


FROM_EMAIL = "alice@complai.com"
TO_EMAIL = "ceo@prospect.com"


@function_tool
def send_html_email(subject: str, html_body: str) -> dict:
    """Terminal action in the SDR pipeline — stub that prints the final email instead of sending via SMTP."""
    print(
        f"\n{'='*60}\n"
        f"[EMAIL]\n"
        f"  From   : {FROM_EMAIL}\n"
        f"  To     : {TO_EMAIL}\n"
        f"  Subject: {subject}\n"
        f"  Body   :\n{html_body}\n"
        f"{'='*60}\n"
    )
    return {"status": "success"}

# ---------------------------------------------------------------------------
# Emailer agent  (called as handoff by sales_manager)
# Receives the winning draft and runs a sequential pipeline:
#   subject_writer → html_converter → send_html_email
# ---------------------------------------------------------------------------

emailer_agent = Agent(
    name="Email Manager",
    instructions=(
        "You receive the body of an email to send. "
        "First use subject_writer to write a subject, then use html_converter to convert "
        "the body to HTML, then use send_html_email to send the email."
    ),
    tools=[
        subject_writer.as_tool(tool_name="subject_writer", tool_description="Write a subject for a cold sales email"),
        html_converter.as_tool(tool_name="html_converter", tool_description="Convert a text email body to HTML"),
        send_html_email,
    ],
    model="gpt-4o-mini",
    handoff_description="Convert an email to HTML and send it",
)

# ---------------------------------------------------------------------------
# Sales manager (orchestrator)  (called last: demo_full_sdr)
# ---------------------------------------------------------------------------

SALES_MANAGER_INSTRUCTIONS = """
You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email.

Follow these steps:
1. Generate Drafts: Use all three sales_agent tools to generate three different drafts.
   Do not proceed until all three are ready.
2. Evaluate and Select: Choose the single best email. You may re-generate if unsatisfied.
3. Hand off: Pass ONLY the winning draft to the Email Manager for formatting and sending.

Rules:
- Use the sales agent tools to generate drafts — never write them yourself.
- Hand off exactly ONE email to the Email Manager.
"""

sales_manager = Agent(
    name="Sales Manager",
    instructions=SALES_MANAGER_INSTRUCTIONS,
    tools=[
        sales_agent1.as_tool(tool_name="sales_agent1", tool_description="Write a cold sales email"),
        sales_agent2.as_tool(tool_name="sales_agent2", tool_description="Write a cold sales email"),
        sales_agent3.as_tool(tool_name="sales_agent3", tool_description="Write a cold sales email"),
    ],
    handoffs=[emailer_agent],
    model="gpt-4o-mini",
)

# ---------------------------------------------------------------------------
# Demo flows
# ---------------------------------------------------------------------------

async def demo_stream_single() -> None:
    """Stream a single cold email draft token-by-token using Runner.run_streamed."""
    print("=== Streaming single draft ===")
    with trace("Streaming single draft"):
        result = Runner.run_streamed(sales_agent1, input="Write a cold sales email")
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="", flush=True)
    print("\n")

async def demo_pick_best() -> None:
    """Generate three drafts in parallel, concatenate them, then pass to sales_picker to select the best.

    Unlike sales_manager (which self-selects inside its own reasoning loop), here
    selection is explicit: Python collects all drafts and hands them to a separate picker agent.
    """
    print("=== Picking best cold email ===")
    sales_picker = Agent(
        name="sales_picker",
        instructions=(
            "You pick the best cold sales email from given options. "
            "Imagine you are a customer and pick the one you are most likely to respond to. "
            "Do not explain; reply with the selected email only."
        ),
        model="gpt-4o-mini",
    )
    message = "Write a cold sales email"
    with trace("Selection from sales people"):
        results = await asyncio.gather(
            Runner.run(sales_agent1, message),
            Runner.run(sales_agent2, message),
            Runner.run(sales_agent3, message),
        )
        emails = "Cold sales emails:\n\n" + "\n\nEmail:\n\n".join(r.final_output for r in results)
        best = await Runner.run(sales_picker, emails)
    print(f"Best email:\n{best.final_output}\n")


async def demo_full_sdr() -> None:
    """Full pipeline via sales_manager: calls all three agents as tools, self-selects the best
    draft inside its own reasoning loop, then hands off to emailer_agent to format and send.
    """
    print("=== Full SDR pipeline ===")
    with trace("Automated SDR"):
        await Runner.run(sales_manager, "Send a cold sales email addressed to Dear CEO from Alice")
    print("Done — check traces at https://platform.openai.com/traces")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    await demo_stream_single()
    await demo_pick_best()
    await demo_full_sdr()


if __name__ == "__main__":
    asyncio.run(main())
