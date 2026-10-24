import pytest
from phoenix_agent.cost_calculator import CostCalculator


def test_cost_calculation_known_model():
    cost, msg = CostCalculator.calculate_cost(
        model="openai/gpt-oss-120b",
        input_tokens=1_000_000,
        output_tokens=1_000_000
    )
    # Rate: 0.59 input + 0.79 output = 1.38 USD
    assert cost == 1.38
    assert "Estimated using Groq pricing" in msg


def test_cost_calculation_small_token_count():
    cost, msg = CostCalculator.calculate_cost(
        model="llama-3.1-8b-instant",
        input_tokens=1000,
        output_tokens=500
    )
    # (1000/1M * 0.05) + (500/1M * 0.08) = 0.00005 + 0.00004 = 0.00009
    assert cost == 0.00009


def test_cost_calculation_unknown_model():
    cost, msg = CostCalculator.calculate_cost(
        model="unverified-custom-model",
        input_tokens=500,
        output_tokens=200
    )
    assert cost is None
    assert "not in verified pricing table" in msg
