# Only BUY signals for CE/PE based on order book imbalance

def generate_buy_signals(depth_data):
    """
    depth_data: dict {symbol: {"tbq": int, "tsq": int, "bids": list, "asks": list, "timestamp": str}}
    Returns list of signal dicts: {"symbol": str, "type": "CE" or "PE", "reason": str}
    Max 3 signals per call.
    """
    signals = []
    for symbol, data in depth_data.items():
        if not data:
            continue
        # Determine if CE or PE
        if symbol.endswith("CE"):
            opt_type = "CE"
        elif symbol.endswith("PE"):
            opt_type = "PE"
        else:
            continue  # skip futures or other symbols
        
        tbq = data.get("tbq", 0)
        tsq = data.get("tsq", 0)
        total = tbq + tsq
        if total == 0:
            continue
        
        # Imbalance = (buy - sell) / total
        imbalance = (tbq - tsq) / total
        
        # Strong buying pressure (imbalance > 0.3) -> BUY signal
        # For CE, buying pressure means bullish; for PE, buying pressure means bearish.
        # But we only generate BUY signals (buy the option), so:
        #   - If CE and imbalance > 0.3 → buy CE (expect price up)
        #   - If PE and imbalance < -0.3 → buy PE (expect price down)
        # However, for simplicity, we treat any strong imbalance as a signal to buy the option that aligns.
        # Better: For CE, we want bullish imbalance (tbq > tsq). For PE, we want bearish imbalance (tsq > tbq).
        
        if opt_type == "CE" and imbalance > 0.3:
            signals.append({
                "symbol": symbol,
                "type": "CE",
                "reason": f"Strong buy imbalance: tbq={tbq}, tsq={tsq}"
            })
        elif opt_type == "PE" and imbalance < -0.3:
            signals.append({
                "symbol": symbol,
                "type": "PE",
                "reason": f"Strong sell imbalance (buy PE): tbq={tbq}, tsq={tsq}"
            })
        
        if len(signals) >= 3:
            break
    return signals
