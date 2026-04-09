import streamlit as st
import threading
import time
import json
from collections import defaultdict
from fyers_apiv3.FyersWebsocket.tbt_ws import FyersTbtSocket, SubscriptionModes
from utils import get_nearest_expiry, get_atm_strike, generate_option_symbols, generate_futures_symbol
from trade_logic import generate_buy_signals

# ---------------------------
# Global state
# ---------------------------
depth_store = {}          # {symbol: depth_data}
underlying_prices = {}    # {futures_symbol: last_price}
current_atm = {           # store current ATM strikes to detect changes
    "NIFTY": None,
    "BANKNIFTY": None
}
subscribed_symbols = set()   # set of symbols currently subscribed
fyers = None
expiry = get_nearest_expiry()

# ---------------------------
# Helper to re-subscribe when ATM changes
# ---------------------------
def update_subscriptions():
    global subscribed_symbols, fyers
    new_symbols = set()
    # Add futures symbols for underlying price
    for idx in ["NIFTY", "BANKNIFTY"]:
        fut_sym = generate_futures_symbol(idx, expiry)
        new_symbols.add(fut_sym)
    
    # Add options for each index based on latest underlying price
    for idx in ["NIFTY", "BANKNIFTY"]:
        fut_sym = generate_futures_symbol(idx, expiry)
        price = underlying_prices.get(fut_sym)
        if price is None or price == 0:
            continue
        atm_strike = get_atm_strike(price, idx)
        # Check if ATM changed
        if current_atm[idx] != atm_strike:
            current_atm[idx] = atm_strike
            # Unsubscribe old options (will be replaced)
            # We'll just re-subscribe all needed symbols
        opt_syms = generate_option_symbols(idx, expiry, atm_strike)
        new_symbols.update(opt_syms)
    
    # If no change in subscriptions, do nothing
    if new_symbols == subscribed_symbols:
        return
    
    # Unsubscribe old symbols (if any) – Fyers SDK doesn't have direct unsubscribe,
    # but we can just subscribe new set; the SDK will replace.
    if fyers and subscribed_symbols:
        # To unsubscribe, we can subscribe an empty list? Not supported.
        # Workaround: reconnect? But simpler: just subscribe new symbols.
        # The SDK will maintain only the latest subscription.
        pass
    
    # Subscribe to new symbols
    to_subscribe = list(new_symbols)
    if to_subscribe:
        try:
            fyers.subscribe(symbol_tickers=to_subscribe, channelNo='1', mode=SubscriptionModes.DEPTH)
            subscribed_symbols.clear()
            subscribed_symbols.update(new_symbols)
            st.toast(f"Subscribed to {len(to_subscribe)} symbols", icon="✅")
        except Exception as e:
            st.error(f"Subscription error: {e}")

# ---------------------------
# WebSocket callbacks
# ---------------------------
def onopen():
    print("WebSocket connected")
    # Initial subscription will be triggered from main loop

def on_depth_update(ticker, message):
    # Store depth data
    depth_store[ticker] = {
        "tbq": message.tbq,
        "tsq": message.tsq,
        "bids": list(zip(message.bidprice[:5], message.bidqty[:5])),
        "asks": list(zip(message.askprice[:5], message.askqty[:5])),
        "timestamp": message.timestamp
    }
    # If it's a futures contract, update underlying price (mid of best bid/ask)
    if "FUT" in ticker:
        if message.bidprice and message.askprice:
            mid = (message.bidprice[0] + message.askprice[0]) / 2
            underlying_prices[ticker] = mid
            # Trigger subscription update when price changes
            update_subscriptions()

def onerror(message):
    print("WebSocket error:", message)

def onclose(message):
    print("WebSocket closed:", message)

def onerror_message(message):
    print("Server error:", message)

# ---------------------------
# Background WebSocket thread
# ---------------------------
def start_websocket():
    global fyers
    access_token = st.secrets["access_token"]
    fyers = FyersTbtSocket(
        access_token=access_token,
        write_to_file=False,
        log_path="",
        on_open=onopen,
        on_close=onclose,
        on_error=onerror,
        on_depth_update=on_depth_update,
        on_error_message=onerror_message
    )
    fyers.connect()

# ---------------------------
# Streamlit Dashboard
# ---------------------------
st.set_page_config(page_title="Fyers TBT Depth Trader", layout="wide")
st.title("📈 50-Level Market Depth Dashboard")
st.markdown("**Nifty & Bank Nifty** | ATM, ATM±2 strikes (CE & PE) | **Only BUY signals**")

# Start WebSocket thread
if "ws_started" not in st.session_state:
    st.session_state.ws_started = True
    thread = threading.Thread(target=start_websocket, daemon=True)
    thread.start()
    time.sleep(2)  # allow connection

# Auto-refresh placeholder
placeholder = st.empty()

# Main loop
while True:
    with placeholder.container():
        # Show underlying prices
        col1, col2 = st.columns(2)
        nifty_fut = generate_futures_symbol("NIFTY", expiry)
        banknifty_fut = generate_futures_symbol("BANKNIFTY", expiry)
        
        with col1:
            st.subheader("🇮🇳 NIFTY 50")
            nifty_price = underlying_prices.get(nifty_fut, 0)
            st.metric("Underlying Futures Price", f"{nifty_price:.2f}")
            if nifty_price > 0:
                atm = get_atm_strike(nifty_price, "NIFTY")
                st.write(f"**ATM Strike:** {atm}")
                st.write(f"**Strikes tracked:** {atm-100}, {atm-50}, {atm}, {atm+50}, {atm+100}")
        
        with col2:
            st.subheader("🏦 BANK NIFTY")
            bn_price = underlying_prices.get(banknifty_fut, 0)
            st.metric("Underlying Futures Price", f"{bn_price:.2f}")
            if bn_price > 0:
                atm_bn = get_atm_strike(bn_price, "BANKNIFTY")
                st.write(f"**ATM Strike:** {atm_bn}")
                st.write(f"**Strikes tracked:** {atm_bn-200}, {atm_bn-100}, {atm_bn}, {atm_bn+100}, {atm_bn+200}")
        
        # Trade signals section
        st.subheader("🎯 BUY SIGNALS (max 3 intraday)")
        signals = generate_buy_signals(depth_store)
        if signals:
            for sig in signals:
                st.success(f"**BUY {sig['type']}** – {sig['symbol']}\n\nReason: {sig['reason']}")
        else:
            st.info("No buy signal at this moment. Waiting for strong order book imbalance.")
        
        # Display depth for first few option symbols (optional)
        with st.expander("🔍 Live Depth Data (first 10 options)"):
            opt_symbols = [s for s in depth_store.keys() if s.endswith(("CE","PE"))][:10]
            if not opt_symbols:
                st.write("Waiting for option depth data...")
            else:
                for sym in opt_symbols:
                    d = depth_store.get(sym, {})
                    tbq = d.get("tbq", 0)
                    tsq = d.get("tsq", 0)
                    st.write(f"**{sym}** | TBQ:{tbq} TSQ:{tsq} | Imbalance: {(tbq-tsq)/(tbq+tsq+1e-9):.2f}")
                    st.write(f"  Best 3 bids: {d.get('bids', [])[:3]}")
                    st.write(f"  Best 3 asks: {d.get('asks', [])[:3]}")
                    st.divider()
    
    time.sleep(1)  # refresh every second
