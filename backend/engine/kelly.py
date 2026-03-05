from backend.config import KlarmanThresholds

config = KlarmanThresholds()


def calculate_position_size(
    prob_undervalued: float,
    mos_downside: float,
    portfolio_value: float,
    current_price: float,
) -> dict:
    """
    Fractional Kelly criterion position sizing.

    Kelly fraction = edge / odds
      edge = probability-weighted gain − probability-weighted loss
      odds = expected gain if the thesis is correct

    Klarman overlay:
    - Expected gain  = realised margin of safety (downside-anchored)
    - Expected loss  = 30% (conservative downside assumption)
    - Apply quarter-Kelly and cap at max_position_size
    """
    prob_win = max(0.0, min(1.0, prob_undervalued))
    prob_loss = 1.0 - prob_win

    expected_gain = max(0.0, mos_downside)
    expected_loss = 0.30   # Conservative 30% downside if thesis is wrong

    # Degenerate cases: no edge or no risk
    if expected_gain == 0.0 or prob_win == 0.0:
        return {
            "kelly_full_pct": 0.0,
            "kelly_fractional_pct": 0.0,
            "dollar_amount": 0.0,
            "shares": 0,
        }

    # Full Kelly
    kelly_full = (prob_win * expected_gain - prob_loss * expected_loss) / expected_gain
    kelly_full = max(0.0, kelly_full)

    # Quarter-Kelly, capped at max position size
    kelly_fractional = kelly_full * config.kelly_fraction
    kelly_capped = min(kelly_fractional, config.max_position_size)

    dollar_amount = portfolio_value * kelly_capped
    shares = int(dollar_amount / current_price) if current_price > 0 else 0

    return {
        "kelly_full_pct": round(kelly_full * 100.0, 1),
        "kelly_fractional_pct": round(kelly_capped * 100.0, 1),
        "dollar_amount": round(dollar_amount, 2),
        "shares": shares,
    }
