from datetime import datetime, timedelta
import calendar

def get_last_thursday(year, month):
    """Returns the date of the last Thursday of a given month."""
    last_day = calendar.monthrange(year, month)[1]
    for day in range(last_day, last_day - 7, -1):
        if datetime(year, month, day).weekday() == 3:  # Thursday = 3
            return datetime(year, month, day)
    return None

def get_nearest_expiry():
    """Returns the last Thursday of the current month, or next month if passed."""
    today = datetime.today()
    # Check current month's last Thursday
    last_thu = get_last_thursday(today.year, today.month)
    if last_thu and last_thu >= today:
        expiry_date = last_thu
    else:
        # Next month
        if today.month == 12:
            next_month = 1
            next_year = today.year + 1
        else:
            next_month = today.month + 1
            next_year = today.year
        expiry_date = get_last_thursday(next_year, next_month)
    # Format as ddMMM (e.g., 30APR)
    return expiry_date.strftime("%d%b").upper()

def get_atm_strike(price, index_type):
    step = 50 if index_type == "NIFTY" else 100
    return int(round(price / step) * step)

def generate_option_symbols(index_type, expiry, atm_strike):
    step = 50 if index_type == "NIFTY" else 100
    strikes = [atm_strike - 2*step, atm_strike - step, atm_strike, atm_strike + step, atm_strike + 2*step]
    symbols = []
    for strike in strikes:
        strike_str = f"{int(strike):05d}"
        for opt_type in ["CE", "PE"]:
            symbols.append(f"NSE:{index_type}{expiry}{strike_str}{opt_type}")
    return symbols

def generate_futures_symbol(index_type, expiry):
    """Example: NSE:NIFTY30APRFUT"""
    return f"NSE:{index_type}{expiry}FUT"
