from datetime import datetime, timedelta

def get_nearest_expiry():
    """Returns next Thursday as ddMMM (e.g., 16APR)."""
    today = datetime.today()
    days_to_thu = (3 - today.weekday()) % 7
    if days_to_thu == 0:
        days_to_thu = 7
    expiry_date = today + timedelta(days=days_to_thu)
    return expiry_date.strftime("%d%b").upper()

def get_atm_strike(price, index_type):
    """Returns ATM strike price."""
    step = 50 if index_type == "NIFTY" else 100
    return int(round(price / step) * step)

def generate_option_symbols(index_type, expiry, atm_strike):
    """Returns list of option symbols for ATM, ATM-2, ATM+2 strikes, both CE and PE."""
    step = 50 if index_type == "NIFTY" else 100
    strikes = [atm_strike - 2*step, atm_strike - step, atm_strike, atm_strike + step, atm_strike + 2*step]
    symbols = []
    for strike in strikes:
        strike_str = f"{int(strike):05d}"
        for opt_type in ["CE", "PE"]:
            symbols.append(f"NSE:{index_type}{expiry}{strike_str}{opt_type}")
    return symbols

def generate_futures_symbol(index_type, expiry):
    """Returns futures symbol for underlying price feed."""
    return f"NSE:{index_type}{expiry}FUT"
