import streamlit as st
import threading
import time
import os
from datetime import datetime
from fyers_apiv3.FyersWebsocket.tbt_ws import FyersTbtSocket, SubscriptionModes
from utils import get_nearest_expiry, get_atm_strike, generate_option_symbols, generate_futures_symbol
from trade_logic import generate_buy_signals

# ---------------------------
# Page config & styling
# ---------------------------
st.set_page_config(page_title="Fyers TBT Depth Trader", layout="wide")
st.markdown("""
    <style>
        .stApp { background-color: #f5f5f0; }
        .stMetric, .stDataFrame, .stMarkdown { color: #2c3e50; }
        .stButton button { background-color: #4682b4; color: white; }
        .stSuccess { background-color: #d4edda; color: #155724; }
        .stInfo { background-color: #d1ecf1; color: #0c5460; }
        .stError { background-color: #f8d7da; color: #721c24; }
        h1, h2, h3 { color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Helper to load/save last price
# ---------------------------
def load_last_price(index):
    try:
        with open(f"last_{index}.txt", "r") as f:
            return float(f.read().strip())
    except:
        return 0.0

def save_last_price(index, price):
    with open(f"last_{index}.txt", "w") as f:
        f.write(str(price))

# ---------------------------
# Global state
# ---------------------------
depth_store = {}
underlying_prices = {
    generate_futures_symbol("NIFTY", get_nearest_expiry()): load_last_price("NIFTY"),
    generate_futures_symbol("BANKNIFTY", get_nearest_expiry()): load_last_price("BANKNIFTY")
}
current_atm = {"NIFTY": None, "BANKNIFTY": None}
subscribed_symbols = set()
fyers = None
expiry = get_nearest_expiry()  # e.g., "16APR"
trade_history = []

def save_trade_signal(signal):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trade_history.append({
        "Time": timestamp,
        "Symbol": signal["symbol"],
        "Type": signal["type"],
        "Reason": signal["reason"]
    })
    with open("history.html", "w") as f:
        f.write("<html><head><title>Trade History</title>")
        f.write("<style>body{background:#f5f5f0; font-family:sans-serif;} table{border-collapse:collapse;} th,td{padding:8px 12px; border:1px solid #ccc;} th{background:#4682b4; color:white;}</style>")
        f.write("</head><body><h1>Trade History</h1></table><table><tr><th>Time</th><th>Symbol</th><th>Type</th><th>Reason</th></tr>")
        for t in trade_history:
            f.write(f"<tr><td>{t['Time']}</td><td>{t['Symbol']}</td><td>{t['Type']}</td><td>{t['Reason']}</td></tr>")
        f.write("</table></body></html>")

def onopen():
    print("WebSocket connected successfully")
    symbols = [generate_futures_symbol("NIFTY", expiry), generate_futures_symbol("BANKNIFTY", expiry)]
    try:
        fyers.subscribe(symbol_tickers=symbols, channelNo='1', mode=SubscriptionModes.DEPTH)
        print(f"Subscribed to futures: {symbols}")
    except Exception as e:
        print(f"Subscription error: {e}")

def on_depth_update(ticker, message):
    depth_store[ticker] = {
        "tbq": message.tbq,
        "tsq": message.tsq,
        "bids": list(zip(message.bidprice[:5], message.bidqty[:5])),
        "asks": list(zip(message.askprice[:5], message.askqty[:5])),
        "timestamp": message.timestamp
    }
    if "FUT" in ticker and message.bidprice and message.askprice:
        mid = (message.bidprice[0] + message.askprice[0]) / 2
        underlying_prices[ticker] = mid
        # Save to file
        if "NIFTY" in ticker:
            save_last_price("NIFTY", mid)
        elif "BANKNIFTY" in ticker:
            save_last_price("BANKNIFTY", mid)
        print(f"Price update for {ticker}: {mid}")
        update_subscriptions()

def update_subscriptions():
    global subscribed_symbols, fyers
    new_symbols = set()
    for idx in ["NIFTY", "BANKNIFTY"]:
        new_symbols.add(generate_futures_symbol(idx, expiry))
    for idx in ["NIFTY", "BANKNIFTY"]:
        fut_sym = generate_futures_symbol(idx, expiry)
        price = underlying_prices.get(fut_sym, 0)
        if price and price > 0:
            atm_strike = get_atm_strike(price, idx)
            if current_atm[idx] != atm_strike:
                print(f"{idx} ATM changed to {atm_strike}")
                current_atm[idx] = atm_strike
            opt_syms = generate_option_symbols(idx, expiry, atm_strike)
            new_symbols.update(opt_syms)
    if new_symbols != subscribed_symbols:
        to_subscribe = list(new_symbols)
        try:
            print(f"Subscribing to: {to_subscribe[:5]}...")  # print first 5 symbols
            fyers.subscribe(symbol_tickers=to_subscribe, channelNo='1', mode=SubscriptionModes.DEPTH)
            subscribed_symbols.clear()
            subscribed_symbols.update(new_symbols)
            print(f"Subscribed to {len(to_subscribe)} symbols")
        except Exception as e:
            print(f"Subscription error: {e}")

def onerror(message):
    print("WebSocket error:", message)

def onclose(message):
    print("WebSocket closed:", message)

def onerror_message(message):
    print("Server error:", message)

def start_websocket():
    global fyers
    app_id = os.environ.get("APP_ID")
    token = os.environ.get("ACCESS_TOKEN")
    if not app_id or not token:
        st.error("Missing APP_ID or ACCESS_TOKEN environment variables.")
        return
    full_token = f"{app_id}:{token}"
    print(f"Connecting with token: {full_token[:20]}...")
    fyers = FyersTbtSocket(
        access_token=full_token,
        write_to_file=False,
        log_path="",
        on_open=onopen,
        on_close=onclose,
        on_error=onerror,
        on_depth_update=on_depth_update,
        on_error_message=onerror_message
    )
    fyers.connect()

st.title("📈 50‑Level Market Depth Dashboard")
st.markdown("**Nifty & Bank Nifty** | ATM, ATM±2 strikes (CE & PE) | **Only BUY signals**")

if "ws_started" not in st.session_state:
    st.session_state.ws_started = True
    thread = threading.Thread(target=start_websocket, daemon=True)
    thread.start()
    time.sleep(3)

placeholder = st.empty()
while True:
    with placeholder.container():
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
        
        st.subheader("🎯 BUY SIGNALS (max 3 intraday)")
        signals = generate_buy_signals(depth_store)
        if signals:
            for sig in signals:
                st.success(f"**BUY {sig['type']}** – {sig['symbol']}\n\nReason: {sig['reason']}")
                save_trade_signal(sig)
        else:
            st.info("No buy signal at this moment. Waiting for strong order book imbalance.")
        
        if os.path.exists("history.html"):
            st.markdown("📜 [View Trade History](./history.html)", unsafe_allow_html=True)
        
        with st.expander("🔍 Live Depth Data (first 10 options)"):
            opt_symbols = [s for s in depth_store.keys() if s.endswith(("CE","PE"))][:10]
            if not opt_symbols:
                st.write("Waiting for option depth data...")
            else:
                for sym in opt_symbols:
                    d = depth_store.get(sym, {})
                    tbq = d.get("tbq", 0)
                    tsq = d.get("tsq", 0)
                    imb = (tbq-tsq)/(tbq+tsq+1e-9)
                    st.write(f"**{sym}** | TBQ:{tbq} TSQ:{tsq} | Imbalance: {imb:.2f}")
                    st.write(f"  Best 3 bids: {d.get('bids', [])[:3]}")
                    st.write(f"  Best 3 asks: {d.get('asks', [])[:3]}")
                    st.divider()
    time.sleep(1)
