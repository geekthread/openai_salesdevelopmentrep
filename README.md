# OpenAI SDR Agent

An agentic Sales Development Representative (SDR) system that automatically generates, evaluates, and sends cold sales outreach emails using the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) and SendGrid.

## Overview

The system demonstrates three core agentic design patterns:

| Pattern | Where it's used |
|---|---|
| **Parallel agent execution** | Three writer agents draft emails concurrently |
| **Agent-as-tool** | Writer agents are wrapped as tools for the Sales Manager |
| **Handoff** | Sales Manager delegates sending to the Email Manager |

### Agent architecture

```
Sales Manager (orchestrator)
├── sales_agent1 (tool) — Professional tone
├── sales_agent2 (tool) — Witty/engaging tone
├── sales_agent3 (tool) — Concise tone
└── emailer_agent (handoff)
    ├── subject_writer (tool) — Writes email subject
    ├── html_converter (tool) — Converts body to HTML
    └── send_html_email (function tool) — Sends via SendGrid
```

## Requirements

- Python 3.14+
- A SendGrid account with a verified sender address
- An OpenAI API key

## Setup

1. **Install dependencies**

   ```bash
   uv sync
   ```

2. **Configure environment variables**

   Create a `.env` file in the project root:

   ```env
   OPENAI_API_KEY=sk-...
   SENDGRID_API_KEY=SG....
   ```

3. **Configure email addresses**

   In [openai_sdr_agent.py](openai_sdr_agent.py), update the two constants near the top:

   ```python
   FROM_EMAIL = "you@yourdomain.com"   # Must be a verified SendGrid sender
   TO_EMAIL   = "prospect@example.com"
   ```

   > The `FROM_EMAIL` address must be verified in SendGrid under
   > **Settings → Sender Authentication → Verify a Single Sender**.

## Usage

```bash
uv run openai_sdr_agent.py
```

The script runs four demo flows in sequence:

1. **Stream single draft** — streams a draft from the professional agent token-by-token
2. **Parallel drafts** — generates three drafts concurrently and prints them
3. **Pick best** — generates drafts, then uses a picker agent to select the best one
4. **Full SDR pipeline** — orchestrates the entire flow end-to-end and sends an HTML email

Traces for all runs are available at <https://platform.openai.com/traces>.

## Project structure

```
openai_sdr_agent/
├── openai_sdr_agent.py   # All agents, tools, and demo flows
├── pyproject.toml
├── uv.lock
└── .env                  # Not committed — add your keys here
```

## Dependencies

| Package | Purpose |
|---|---|
| `openai-agents` | Agent orchestration and tool/handoff primitives |
| `sendgrid` | Email delivery |
| `python-dotenv` | Loading `.env` variables |
