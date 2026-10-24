"""Pricing table and cost calculator for Groq-hosted LLMs in PhoenixCI."""

from typing import Dict, Optional, Tuple


class CostCalculator:
    """
    Computes exact inference cost based on model and token counts.
    Pricing source: Official Groq Pricing Documentation (Verified Oct 2026).
    Rates in USD per 1,000,000 tokens.
    """

    PRICING_TABLE: Dict[str, Dict[str, float]] = {
        "openai/gpt-oss-120b": {
            "input_per_million": 0.59,
            "output_per_million": 0.79,
        },
        "openai/gpt-oss-20b": {
            "input_per_million": 0.15,
            "output_per_million": 0.20,
        },
        "qwen/qwen3.8-27b": {
            "input_per_million": 0.20,
            "output_per_million": 0.30,
        },
        "llama-3.3-70b-versatile": {
            "input_per_million": 0.59,
            "output_per_million": 0.79,
        },
        "llama-3.1-8b-instant": {
            "input_per_million": 0.05,
            "output_per_million": 0.08,
        },
    }

    LAST_VERIFIED_DATE = "2026-10-24"
    PRICING_SOURCE = "https://groq.com/pricing"

    @classmethod
    def calculate_cost(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Tuple[Optional[float], str]:
        """
        Calculates estimated cost in USD.
        
        Returns:
            (cost_usd, status_message)
            If model pricing is unavailable, cost_usd is None.
        """
        if not model or model not in cls.PRICING_TABLE:
            return None, f"Model '{model}' not in verified pricing table. Tokens tracked without cost estimate."

        rates = cls.PRICING_TABLE[model]
        cost_in = (input_tokens / 1_000_000.0) * rates["input_per_million"]
        cost_out = (output_tokens / 1_000_000.0) * rates["output_per_million"]
        total_cost = cost_in + cost_out

        return round(total_cost, 6), f"Estimated using Groq pricing verified on {cls.LAST_VERIFIED_DATE}"
