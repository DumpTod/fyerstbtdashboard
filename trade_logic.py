def generate_buy_signals(depth_data):
    signals = []
    for symbol, data in depth_data.items():
        if not data:
            continue
        if symbol.endswith("CE"):
            opt_type = "CE"
        elif symbol.endswith("PE"):
            opt_type = "PE"
        else:
            continue
        tbq = data.get("tbq", 0)
        tsq = data.get("tsq", 0)
        total = tbq + tsq
        if total == 0:
            continue
        imbalance = (tbq - tsq) / total
        if opt_type == "CE" and imbalance > 0.3:
            signals.append({"symbol": symbol, "type": "CE", "reason": f"Buy pressure (imbalance {imbalance:.2f})"})
        elif opt_type == "PE" and imbalance < -0.3:
            signals.append({"symbol": symbol, "type": "PE", "reason": f"Sell pressure (imbalance {imbalance:.2f})"})
        if len(signals) >= 3:
            break
    return signals
