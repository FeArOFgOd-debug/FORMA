from __future__ import annotations

import re
from typing import Any

from openai import OpenAI

from backend.config import OPENAI_API_KEY

_SYSTEM_PROMPT = """\
You are a Mermaid.js diagram expert. Given a structured business analysis, \
create a clear, detailed Mermaid flowchart that visualizes the business model.

Rules:
- Use `flowchart TD` (top-down) syntax.
- Include nodes for: idea, target audience, value proposition, revenue streams, \
  key activities, channels, cost structure, and competitive advantages.
- Use subgraphs to group related nodes (e.g., "Revenue", "Operations", "Market").
- Use descriptive edge labels.
- Do NOT use spaces in node IDs — use camelCase or underscores.
- Do NOT use the reserved word "end" as a node ID.
- Wrap labels with special characters in double quotes.
- Return ONLY the raw Mermaid code, no markdown fences, no explanation.
"""


def generate_flowchart(
    idea: str,
    analysis: dict[str, Any],
) -> str:
    """Generate a Mermaid flowchart string from the business analysis."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing. Add it to your .env file.")

    import json

    user_msg = (
        f"Business idea: {idea}\n\n"
        f"Business analysis:\n{json.dumps(analysis, indent=2)}"
    )

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )

    mermaid_code = response.choices[0].message.content.strip()
    mermaid_code = re.sub(r"^```(?:mermaid)?\s*", "", mermaid_code)
    mermaid_code = re.sub(r"\s*```$", "", mermaid_code)
    return mermaid_code
