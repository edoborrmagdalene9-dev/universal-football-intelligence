"""Transparent tactical event-rate adjustments using supplied multipliers."""

def adjusted_event_rates(base_rates, state_multipliers=None, tactical_multipliers=None):
    state_multipliers = state_multipliers or {}
    tactical_multipliers = tactical_multipliers or {}
    result = {}
    for event, rate in base_rates.items():
        rate, sf, tf = float(rate), float(state_multipliers.get(event, 1)), float(tactical_multipliers.get(event, 1))
        if min(rate, sf, tf) < 0:
            raise ValueError('rates and multipliers must be non-negative')
        result[event] = rate * sf * tf
    return result

def state_conditioned_event_rates(rates_by_state, state_probabilities):
    if not rates_by_state or not state_probabilities:
        raise ValueError('state rates and probabilities are required')
    if any(p < 0 for p in state_probabilities.values()) or abs(sum(state_probabilities.values()) - 1) > 1e-6:
        raise ValueError('state probabilities must sum to 1')
    events = set().union(*(rates_by_state.get(s, {}).keys() for s in state_probabilities))
    return {e: sum(float(p) * float(rates_by_state.get(s, {}).get(e, 0)) for s, p in state_probabilities.items()) for e in events}
