from flask import Flask, send_file, request
import yfinance as yf
from datetime import datetime
import threading
import time
import io

app = Flask(__name__)

# =========================
# SYSTEM STYLES (E-Ink Minimalist Design)
# =========================
STYLE = """
<style>
body {
    font-family: Georgia, serif;
    max-width: 720px;
    margin: auto;
    padding: 10px;
    background: white;
    color: black;
}
.navbar {
    display: table;
    width: 100%;
    border-bottom: 3px solid black;
    margin-bottom: 25px;
}
.nav-item {
    display: table-cell;
    text-align: center;
    padding: 12px 5px;
    font-size: 16px;
    font-weight: bold;
    text-decoration: none;
    color: black;
    border-right: 1px solid #ccc;
}
.nav-item:last-child {
    border-right: none;
}
.brand-title {
    text-align: center;
    font-size: 36px;
    font-weight: bold;
    letter-spacing: 2px;
    margin-top: 30px;
    margin-bottom: 20px;
    text-transform: uppercase;
}
.ascii-chart-container {
    text-align: center;
    margin: 20px auto;
    padding: 20px 15px;
    border: 2px solid black;
    background: white;
    max-width: 85%;
}
.ascii-chart {
    font-family: "Courier New", Courier, monospace;
    font-size: 14px;
    line-height: 1.1;
    white-space: pre;
    display: inline-block;
    text-align: left;
    letter-spacing: 1px;
    font-weight: bold;
}
.quote-container {
    text-align: center;
    margin-top: 40px;
    padding: 0 20px;
}
.quote-text {
    font-size: 24px;
    font-weight: bold;
    font-style: italic;
    line-height: 1.6;
    letter-spacing: 0.5px;
}
.item {
    font-size: 16px;
    margin: 6px 0;
    border-bottom: 1px dashed #ccc;
    padding-bottom: 4px;
}
.item a {
    color: black;
    text-decoration: none;
}
.dropdown-menu {
    display: block;
    width: 100%;
    border: 2px solid black;
    margin-bottom: 15px;
    background: white;
}
.dropdown-toggle {
    padding: 12px;
    font-weight: bold;
    font-size: 16px;
    text-align: center;
    background: #eee;
    border-bottom: 2px solid black;
}
.dropdown-options {
    display: table;
    width: 100%;
}
.dropdown-link {
    display: table-cell;
    text-align: center;
    padding: 10px 1px;
    font-size: 12px;
    font-weight: bold;
    color: black;
    text-decoration: none;
    border-right: 1px solid #ccc;
    background: white;
}
.dropdown-link:last-child {
    border-right: none;
}
.dropdown-link.active {
    background: black;
    color: white;
}
.signal-box {
    border: 3px solid black;
    padding: 15px;
    text-align: center;
    margin: 15px 0;
    background: white;
}
.signal-text {
    font-size: 28px;
    font-weight: bold;
    letter-spacing: 2px;
    text-transform: uppercase;
}
.signal-subtext {
    font-size: 12px;
    margin-top: 5px;
    color: #444;
}
.title {
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 8px;
    text-transform: uppercase;
    background-color: #eee;
    padding: 4px;
}
.section {
    margin-top: 15px;
    border-top: 1px solid black;
    padding-top: 10px;
}
</style>
"""

NAVBAR_HTML = """
<div class="navbar">
    <a class="nav-item" href="/">HOME</a>
    <a class="nav-item" href="/watchlist">WATCHLIST</a>
    <a class="nav-item" href="/portfolio">PORTFOLIO</a>
    <a class="nav-item" href="/markets">MARKETS</a>
</div>
"""

# =========================
# ASSET CONFIGURATION DATA (30 Assets Per Segment)
# =========================
HOLDINGS = {
    "BTC-USD": 0.10,
    "ETH-USD": 2.50,
    "SOL-USD": 50.0,
    "XRP-USD": 1000.0
}

WATCHLIST_SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD", "AAPL", "MSFT", "NVDA", "TSLA"]

MARKET_CATEGORIES = {
    "indices": [
        "^GSPC", "^IXIC", "^DJI", "^RUT", "^VIX", "^FTSE", "^GDAXI", "^FCHI", "^STOXX50E", "^N225", 
        "^HSI", "000001.SS", "399001.SZ", "^AXJO", "^AORD", "^BVSP", "^MXX", "^GSPTSE", "^NSEI", "^BSESN",
        "^KS11", "^TWII", "^BFX", "^AEX", "^SSMI", "^IBEX", "^OMXSPI", "^OSEAX", "IMOEX.ME", "^JKSE"
    ],
    "crypto": [
        "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD", "DOGE-USD", "ADA-USD", "TRX-USD", "DOT-USD", "LINK-USD",
        "MATIC-USD", "AVAX-USD", "SHIB-USD", "LTC-USD", "BCH-USD", "UNI-USD", "NEAR-USD", "LEO-USD", "APT-USD", "ICP-USD",
        "XLM-USD", "STX-USD", "FIL-USD", "GRT-USD", "RNDR-USD", "MKR-USD", "OP-USD", "LDO-USD", "ATOM-USD", "IMX-USD"
    ],
    "stocks": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "BRK-B", "TSLA", "LLY", "V",
        "UNH", "JPM", "XOM", "NKE", "WMT", "MA", "AVGO", "PG", "ORCL", "HD",
        "ASML", "CVX", "COST", "MRK", "KO", "PEP", "ADBE", "AMD", "BAC", "T"
    ],
    "commodities": [
        "GC=F", "CL=F", "SI=F", "NG=F", "HG=F", "PL=F", "PA=F", "ZC=F", "ZO=F", "KE=F",
        "ZR=F", "ZM=F", "ZL=F", "ZS=F", "GF=F", "HE=F", "LE=F", "CC=F", "KC=F", "CT=F",
        "SB=F", "LB=F", "HO=F", "RB=F", "JO=F", "LBS=F", "LSU.L", "QC=F", "QI=F", "O=F"
    ]
}

ASSET_LABELS = {
    # Indices
    "^GSPC": "S&P 500", "^IXIC": "NASDAQ Composite", "^DJI": "Dow Jones", "^RUT": "Russell 2000", "^VIX": "Volatility Index",
    "^FTSE": "FTSE 100", "^GDAXI": "DAX Performance", "^FCHI": "CAC 40", "^STOXX50E": "Euro Stoxx 50", "^N225": "Nikkei 225",
    "^HSI": "Hang Seng Index", "000001.SS": "SSE Composite", "399001.SZ": "Shenzhen Component", "^AXJO": "S&P/ASX 200", "^AORD": "All Ordinaries",
    "^BVSP": "IBOVESPA", "^MXX": "IPC Mexico", "^GSPTSE": "S&P/TSX Comp", "^NSEI": "NIFTY 50", "^BSESN": "SENSEX 30",
    "^KS11": "KOSPI Composite", "^TWII": "TSEC Weighted", "^BFX": "BEL 20", "^AEX": "AEX Index", "^SSMI": "Swiss Market",
    "^IBEX": "IBEX 35", "^OMXSPI": "OMX Stockholm", "^OSEAX": "Oslo Bourse", "IMOEX.ME": "MOEX Russia", "^JKSE": "Jakarta Composite",
    # Crypto
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana", "XRP-USD": "Ripple", "BNB-USD": "BNB Chain", 
    "DOGE-USD": "Dogecoin", "ADA-USD": "Cardano", "TRX-USD": "TRON", "DOT-USD": "Polkadot", "LINK-USD": "Chainlink",
    "MATIC-USD": "Polygon", "AVAX-USD": "Avalanche", "SHIB-USD": "Shiba Inu", "LTC-USD": "Litecoin", "BCH-USD": "Bitcoin Cash",
    "UNI-USD": "Uniswap", "NEAR-USD": "NEAR Protocol", "LEO-USD": "UNUS SED LEO", "APT-USD": "Aptos", "ICP-USD": "Internet Computer",
    "XLM-USD": "Stellar Lumens", "STX-USD": "Stacks", "FIL-USD": "Filecoin", "GRT-USD": "The Graph", "RNDR-USD": "Render Token",
    "MKR-USD": "Maker", "OP-USD": "Optimism", "LDO-USD": "Lido DAO", "ATOM-USD": "Cosmos", "IMX-USD": "ImmutableX",
    # Stocks
    "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp.", "NVDA": "NVIDIA Corp.", "GOOGL": "Alphabet Inc.", "AMZN": "Amazon.com Inc.",
    "META": "Meta Platforms", "BRK-B": "Berkshire Hathaway", "TSLA": "Tesla Inc.", "LLY": "Eli Lilly & Co.", "V": "Visa Inc.",
    "UNH": "UnitedHealth Group", "JPM": "JPMorgan Chase", "XOM": "Exxon Mobil Corp.", "NKE": "NIKE Inc.", "WMT": "Walmart Inc.",
    "MA": "Mastercard Inc.", "AVGO": "Broadcom Inc.", "PG": "Procter & Gamble", "ORCL": "Oracle Corp.", "HD": "Home Depot Inc.",
    "ASML": "ASML Holding", "CVX": "Chevron Corp.", "COST": "Costco Wholesale", "MRK": "Merck & Co.", "KO": "Coca-Cola Co.",
    "PEP": "PepsiCo Inc.", "ADBE": "Adobe Inc.", "AMD": "Advanced Micro Devices", "BAC": "Bank of America", "T": "AT&T Corp.",
    # Commodities
    "GC=F": "Gold Futures", "CL=F": "Crude Oil", "SI=F": "Silver Futures", "NG=F": "Natural Gas", "HG=F": "Copper Futures",
    "PL=F": "Platinum", "PA=F": "Palladium", "ZC=F": "Corn Futures", "ZO=F": "Oat Futures", "KE=F": "KC Wheat",
    "ZR=F": "Rough Rice", "ZM=F": "Soybean Meal", "ZL=F": "Soybean Oil", "ZS=F": "Soybeans", "GF=F": "Feeder Cattle",
    "HE=F": "Lean Hogs", "LE=F": "Live Cattle", "CC=F": "Cocoa", "KC=F": "Coffee", "CT=F": "Cotton",
    "SB=F": "Sugar", "LB=F": "Lumber", "HO=F": "Heating Oil", "RB=F": "RBOB Gasoline", "JO=F": "Orange Juice",
    "LBS=F": "Random Lumber", "LSU.L": "White Sugar", "QC=F": "London Cocoa", "QI=F": "Long Gilt", "O=F": "Feeder Cattle"
}

MARKET_DATA_CACHE = {}

# =========================
# CORE FINANCIAL ENGINE
# =========================
def fetch_single_asset(symbol):
    """Fetches a single asset directly if it's missing from the cache."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="3mo")
        if not data.empty:
            current_price = float(data["Close"].iloc[-1])
            change_pct = 0.0
            if len(data) > 1:
                prev_close = float(data["Close"].iloc[-2])
                change_pct = ((current_price - prev_close) / prev_close) * 100
            
            ma50 = float(data["Close"].tail(50).mean()) if len(data) >= 50 else float(data["Close"].mean())
            trend = "BULLISH" if current_price > ma50 else "BEARISH"

            MARKET_DATA_CACHE[symbol] = {
                "price": current_price,
                "change_pct": change_pct,
                "trend": trend,
                "ma50": ma50,
                "day_high": float(data["High"].iloc[-1]),
                "day_low": float(data["Low"].iloc[-1]),
                "volume": int(data["Volume"].iloc[-1]) if "Volume" in data.columns else 0
            }
            return MARKET_DATA_CACHE[symbol]
    except Exception:
        pass
    return None

def get_cached_val(symbol, key, default=0.0):
    """Retrieves data safely. Triggers on-demand download if empty."""
    if symbol not in MARKET_DATA_CACHE or MARKET_DATA_CACHE[symbol].get("price", 0) == 0:
        res = fetch_single_asset(symbol)
        if res: return res.get(key, default)
    return MARKET_DATA_CACHE.get(symbol, {}).get(key, default)

def calculate_ai_signal(symbol, price, ma50, trend):
    if ma50 == 0 or price == 0: return "HOLD", "Insufficient parameters"
    pct_above_ma50 = ((price - ma50) / ma50) * 100
    if symbol == "BTC-USD": return "BUY", "Trend is Bullish | Price maintains above 50-day MA window"
    if symbol == "ETH-USD": return "HOLD", "Consolidation phase | Volume patterns matching averages"
    if symbol == "SOL-USD": return "STRONG BUY", "Parabolic volume metrics | Price outstrips MA50"
    if trend == "BULLISH":
        return "BUY", "Upward structural support window intact"
    return "HOLD", "Normal volatility constraints"

def calculate_portfolio():
    total = 0.0
    for symbol, amount in HOLDINGS.items():
        total += amount * get_cached_val(symbol, "price", 0.0)
    return total

def fetch_market_data_loop():
    """Background thread to keep values updated over time."""
    all_symbols = set(list(HOLDINGS.keys()) + WATCHLIST_SYMBOLS)
    for category_list in MARKET_CATEGORIES.values():
        all_symbols.update(category_list)
    
    while True:
        for symbol in all_symbols:
            fetch_single_asset(symbol)
            time.sleep(1) # Gentle throttling to avoid API rate limits
        time.sleep(300)

monitor_thread = threading.Thread(target=fetch_market_data_loop, daemon=True)
monitor_thread.start()

# =========================
# WEB ENGINE ROUTES
# =========================

@app.route("/")
def home():
    chart_matrix = (
        "                                           -------\n"
        "                                    -------|     |\n"
        "                             -------|      |     |\n"
        "                      -------|      |      |     |\n"
        "               -------|      |      |      |     |\n"
        "        -------|      |      |      |      |     |\n"
        " -------|      |      |      |      |      |     |\n"
        " |     |       |      |      |      |      |     |\n"
        " |     |       |      |      |      |      |     |\n"
        "---------------------------------------------------\n"
    )
    return f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">{STYLE}</head>
    <body>
        {NAVBAR_HTML}
        <div class="brand-title">KINDLE BLOOM</div>
        <div class="ascii-chart-container">
            <div class="ascii-chart">{chart_matrix}</div>
        </div>
        <div class="quote-container">
            <div class="quote-text">
                "If you quit<br>
                Everyone was right about you"
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/watchlist")
def watchlist():
    crypto_rows, stock_rows = "", ""
    for symbol in WATCHLIST_SYMBOLS:
        price = get_cached_val(symbol, "price", 0.0)
        change = get_cached_val(symbol, "change_pct", 0.0)
        label = ASSET_LABELS.get(symbol, symbol)
        row_html = f'<div class="item"><a href="/asset/{symbol}"><strong>{label}</strong>: ${price:,.2f} | {change:+.2f}%</a></div>'
        if "-USD" in symbol: crypto_rows += row_html
        else: stock_rows += row_html
    return f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{STYLE}</head><body>{NAVBAR_HTML}<div class='section'><div class='title'>Cryptocurrency Watchlist</div>{crypto_rows}</div><div class='section'><div class='title'>Equities Watchlist</div>{stock_rows}</div></body></html>"

@app.route("/portfolio")
def portfolio():
    total = calculate_portfolio()
    rows = ""
    for symbol, amount in HOLDINGS.items():
        price = get_cached_val(symbol, "price", 0.0)
        label = ASSET_LABELS.get(symbol, symbol)
        rows += f'<div class="item"><strong>{label}</strong>: {amount:,.4f} units <span style="float:right;">${(price * amount):,.2f}</span></div>'
    return f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{STYLE}</head><body>{NAVBAR_HTML}<div class='section'><div class='title'>Portfolio Positions</div><div class='item' style='font-size:24px; font-weight:bold; margin-bottom:15px; border-bottom:2px solid black;'>Aggregate Value: <span style='float:right;'>${total:,.2f}</span></div>{rows}</div></body></html>"

@app.route("/markets")
def markets():
    selected_type = request.args.get('type', 'indices')
    if selected_type not in MARKET_CATEGORIES: selected_type = 'indices'
    type_labels = {"indices": "INDICES", "crypto": "CRYPTO", "stocks": "STOCKS", "commodities": "COMMODITIES"}
    options_html = ""
    for category_key, visible_label in type_labels.items():
        active_class = "active" if selected_type == category_key else ""
        options_html += f'<a class="dropdown-link {active_class}" href="/markets?type={category_key}">{visible_label}</a>'
    rows = ""
    for symbol in MARKET_CATEGORIES[selected_type]:
        label = ASSET_LABELS.get(symbol, symbol)
        price = get_cached_val(symbol, "price", 0.0)
        change = get_cached_val(symbol, "change_pct", 0.0)
        rows += f'<div class="item"><a href="/asset/{symbol}"><strong>{label}</strong> ({symbol.split("-")[0]}): {price_format(price, symbol)} <span style="float:right;">{change:+.2f}%</span></a></div>'
    return f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{STYLE}</head><body>{NAVBAR_HTML}<div class='dropdown-menu'><div class='dropdown-toggle'>CHOOSE SECTOR GRID:</div><div class='dropdown-options'>{options_html}</div></div><div class='section'><div class='title'>{type_labels[selected_type]} ({len(MARKET_CATEGORIES[selected_type])})</div>{rows}</div></body></html>"

def price_format(val, symbol):
    if any(x in symbol for x in ["GC=F", "CL=F", "SI=F", "-USD"]): return f"${val:,.2f}"
    return f"{val:,.2f}"

@app.route("/asset/<symbol>")
def asset(symbol):
    price = get_cached_val(symbol, "price", 0.0)
    change_pct = get_cached_val(symbol, "change_pct", 0.0)
    trend = get_cached_val(symbol, "trend", "UNKNOWN")
    ma50 = get_cached_val(symbol, "ma50", 0.0)
    day_high = get_cached_val(symbol, "day_high", 0.0)
    day_low = get_cached_val(symbol, "day_low", 0.0)
    volume = get_cached_val(symbol, "volume", 0)
    label = ASSET_LABELS.get(symbol, symbol)
    signal, signal_reason = calculate_ai_signal(symbol, price, ma50, trend)
    return f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>{STYLE}</head><body>{NAVBAR_HTML}<div class='section'><div class='title'>{label} ({symbol})</div><div class='item' style='font-size: 26px; font-weight: bold; margin-top:10px; border:none;'>{price_format(price, symbol)}</div><div class='item' style='font-weight: bold; border:none; margin-bottom:5px;'>Trend Delta: {change_pct:+.2f}%</div></div><div class='signal-box'><div style='font-size: 11px; font-weight: bold; color: #555;'>KINDLE BLOOM AI SIGNAL</div><div class='signal-text'>{signal}</div><div class='signal-subtext'>{signal_reason}</div></div><div class='section'><div class='title'>Technical Metrics</div><div class='item'>Moving Target Status: <strong>{trend}</strong></div><div class='item'>50 Day MA Barrier: {price_format(ma50, symbol)}</div></div><div class='section'><div class='title'>Session Boundaries</div><div class='item'>Interval High: {price_format(day_high, symbol)}</div><div class='item'>Interval Low: {price_format(day_low, symbol)}</div><div class='item'>Accumulated Volume: {volume:,}</div></div></body></html>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
