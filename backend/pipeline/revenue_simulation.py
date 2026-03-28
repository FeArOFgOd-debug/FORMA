from __future__ import annotations

import json
import math
from typing import Any

from openai import OpenAI

from backend.config import OPENAI_API_KEY

_DEFAULTS_PROMPT = """\
You are a financial modelling expert. Given a business idea and its analysis, \
produce realistic default parameters for a revenue simulation.

Return ONLY valid JSON (no markdown fences) with this exact structure:
{
  "price_per_user_monthly": <float — realistic monthly price per paying user in USD>,
  "initial_users": <int — realistic month-1 paying users>,
  "monthly_growth_rate": <float 0-1 — e.g. 0.12 for 12% MoM growth>,
  "churn_rate": <float 0-1 — monthly churn, e.g. 0.05 for 5%>,
  "fixed_monthly_cost": <float — rent, salaries, infra in USD>,
  "variable_cost_per_user": <float — marginal cost per user in USD>,
  "projection_months": 24,
  "pricing_tiers": [
    {"name": "Free / Basic", "price": 0, "description": "..."},
    {"name": "Pro", "price": <float>, "description": "..."},
    {"name": "Enterprise", "price": <float>, "description": "..."}
  ],
  "rationale": "2-3 sentences explaining why these numbers are reasonable"
}

Be grounded in reality — use the analysis data (market size, competitors, \
revenue model) to justify your numbers. For B2B SaaS use higher prices and \
lower user counts; for consumer apps use lower prices and higher user counts.
"""


def generate_revenue_defaults(
    idea: str,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    """Use GPT-4o to produce smart default simulation parameters."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing.")

    analysis_summary = json.dumps(
        {
            k: analysis.get(k)
            for k in (
                "executive_summary",
                "market_size",
                "target_audience",
                "competitors",
                "revenue_model",
            )
            if analysis.get(k) is not None
        },
        indent=2,
    )

    user_msg = (
        f"Business idea: {idea}\n\n"
        f"--- ANALYSIS ---\n{analysis_summary}"
    )

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _DEFAULTS_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    return json.loads(response.choices[0].message.content)


def run_simulation(params: dict[str, Any]) -> dict[str, Any]:
    """Pure-math revenue simulation. No API calls — instant and re-runnable.

    Accepts the same shape as generate_revenue_defaults output, with optional
    user overrides merged on top.

    Returns month-by-month projections for base / optimistic / pessimistic
    scenarios plus summary KPIs.
    """
    price = float(params.get("price_per_user_monthly", 10))
    initial = int(params.get("initial_users", 100))
    growth = float(params.get("monthly_growth_rate", 0.10))
    churn = float(params.get("churn_rate", 0.05))
    fixed_cost = float(params.get("fixed_monthly_cost", 5000))
    var_cost = float(params.get("variable_cost_per_user", 1.0))
    months = int(params.get("projection_months", 24))
    months = max(1, min(months, 120))

    scenarios = {
        "base": {"growth_mult": 1.0, "churn_mult": 1.0},
        "optimistic": {"growth_mult": 1.5, "churn_mult": 0.6},
        "pessimistic": {"growth_mult": 0.5, "churn_mult": 1.5},
    }

    results: dict[str, Any] = {}

    for name, mults in scenarios.items():
        g = growth * mults["growth_mult"]
        c = min(churn * mults["churn_mult"], 0.99)
        timeline: list[dict[str, Any]] = []
        users = float(initial)
        cumulative_revenue = 0.0
        cumulative_cost = 0.0
        break_even_month: int | None = None

        for m in range(1, months + 1):
            new_users = users * g
            churned = users * c
            users = max(0, users + new_users - churned)
            active = math.ceil(users)

            revenue = active * price
            cost = fixed_cost + active * var_cost
            profit = revenue - cost
            cumulative_revenue += revenue
            cumulative_cost += cost

            if break_even_month is None and cumulative_revenue >= cumulative_cost:
                break_even_month = m

            timeline.append({
                "month": m,
                "active_users": active,
                "new_users": math.ceil(new_users),
                "churned_users": math.ceil(churned),
                "revenue": round(revenue, 2),
                "cost": round(cost, 2),
                "profit": round(profit, 2),
                "cumulative_revenue": round(cumulative_revenue, 2),
                "cumulative_cost": round(cumulative_cost, 2),
            })

        last = timeline[-1] if timeline else {}
        results[name] = {
            "timeline": timeline,
            "summary": {
                "final_users": last.get("active_users", 0),
                "total_revenue": round(cumulative_revenue, 2),
                "total_cost": round(cumulative_cost, 2),
                "total_profit": round(cumulative_revenue - cumulative_cost, 2),
                "break_even_month": break_even_month,
                "final_mrr": last.get("revenue", 0),
                "final_arr": round(last.get("revenue", 0) * 12, 2),
            },
        }

    return {
        "parameters": {
            "price_per_user_monthly": price,
            "initial_users": initial,
            "monthly_growth_rate": growth,
            "churn_rate": churn,
            "fixed_monthly_cost": fixed_cost,
            "variable_cost_per_user": var_cost,
            "projection_months": months,
        },
        "scenarios": results,
    }
