from datetime import datetime, timedelta

def get_nearest_expiry():
    """Returns next Thursday (weekly expiry) as YYMMDD string."""
    today = datetime.today()
    # Thursday is 3 (Monday=0)
    days_ahead = (3 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    expiry_date = today + timedelta(days=days_ahead)
    return expiry_date.strftime("%y%m%d")

def get_atm_strike(price, index_type):
    """Returns ATM strike based on index type."""
    if index_type == "NIFTY":
        step = 50
    else:  # BANKNIFTY
        step = 100
    return int(round(price / step) * step)

def generate_option_symbols(index_type, expiry, atm_strike):
    """
    Returns list of option symbols for ATM, ATM-2, ATM+2 strikes, both CE and PE.
    Format: NSE:INDEXYYMMDDSTRIKEPRICECE/PE
    """
    step = 50 if index_type == "NIFTY" else 100
    strikes = [atm_strike - 2*step, atm_strike - step, atm_strike, atm_strike + step, atm_strike + 2*step]
    symbols = []
    for strike in strikes:
        strike_str = f"{int(strike):05d}"  # pad to 5 digits
        for opt_type in ["CE", "PE"]:
            sym = f"NSE:{index_type}{expiry}{strike_str}{opt_type}"
            symbols.append(sym)
    return symbols

def generate_futures_symbol(index_type, expiry):
    """Returns futures symbol for underlying price feed."""
    return f"NSE:{index_type}{expiry}FUT"
