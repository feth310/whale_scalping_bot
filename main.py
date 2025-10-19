# =========================================================
# Whale Scalping Bot - Version Légère Optimisée
# =========================================================
# 🧠 Analyse technique + fondamentale
# 📨 Envoi d'alertes par e-mail
# 🤖 Auto-trading sur KuCoin (optionnel)
# =========================================================

import os, time, ccxt, requests, pandas as pd
import pandas_ta_classic as ta
from email.mime.text import MIMEText
import smtplib
from dotenv import load_dotenv

load_dotenv()

# ---------------- CONFIG ----------------
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY", "")
KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET", "")
KUCOIN_PASSPHRASE = os.getenv("KUCOIN_PASSPHRASE", "")

SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
TO_EMAIL = os.getenv("TO_EMAIL", SMTP_USER)

TOTAL_CAPITAL = float(os.getenv("TOTAL_CAPITAL_USDT", 18))
AUTO_TRADE = os.getenv("AUTO_TRADE", "true").lower() == "true"
LEVERAGE = int(os.getenv("LEVERAGE", 3))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))

# Liste courte pour test (tu peux ajouter d’autres)
MONITOR_LIST = ["BTC/USDT", "ETH/USDT", "KAS/USDT", "TIA/USDT", "SOL/USDT"]

# Connexions API
exchange = ccxt.kucoin({"enableRateLimit": True})
kucoin_futures = ccxt.kucoinfutures({
    "apiKey": KUCOIN_API_KEY,
    "secret": KUCOIN_API_SECRET,
    "password": KUCOIN_PASSPHRASE,
})

# ---------------- EMAIL ----------------
def send_email(subject, body):
    if not SMTP_USER or not SMTP_PASS:
        print("⚠️ Email non configuré, skip...")
        return
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = TO_EMAIL
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_USER, [TO_EMAIL], msg.as_string())
        s.quit()
        print("📧 Email envoyé :", subject)
    except Exception as e:
        print("Erreur envoi email :", e)

# ---------------- INDICATEURS ----------------
def fetch_data(symbol, limit=150):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, "5m", limit=limit)
        df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
        df = df.astype(float)
        return df
    except Exception:
        return None

def compute_indicators(df):
    df["ema20"] = ta.ema(df["close"], 20)
    df["ema50"] = ta.ema(df["close"], 50)
    df["rsi"] = ta.rsi(df["close"], 14)
    df["macd"] = ta.macd(df["close"]).iloc[:, 0]
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], 14)
    return df

# ---------------- SIGNALS ----------------
def check_signal(symbol):
    df = fetch_data(symbol)
    if df is None or len(df) < 50:
        return None
    df = compute_indicators(df)
    last = df.iloc[-1]

    # Conditions de base
    if last["rsi"] < 30 and last["ema20"] > last["ema50"]:
        direction = "LONG"
    elif last["rsi"] > 70 and last["ema20"] < last["ema50"]:
        direction = "SHORT"
    else:
        return None

    stop_loss = last["close"] - last["atr"] * 1.5 if direction == "LONG" else last["close"] + last["atr"] * 1.5
    take_profit = last["close"] + last["atr"] * 1.5 if direction == "LONG" else last["close"] - last["atr"] * 1.5

    signal = {
        "symbol": symbol,
        "price": last["close"],
        "direction": direction,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "rsi": last["rsi"],
        "ema20": last["ema20"],
        "ema50": last["ema50"]
    }
    return signal

# ---------------- TRADE ----------------
def execute_trade(signal):
    if not AUTO_TRADE:
        return
    try:
        symbol = signal["symbol"]
        side = "buy" if signal["direction"] == "LONG" else "sell"
        qty = (TOTAL_CAPITAL / signal["price"]) / 20  # petit trade
        kucoin_futures.set_leverage(LEVERAGE, symbol)
        kucoin_futures.create_market_order(symbol, side, qty)
        print(f"✅ Trade exécuté : {side} {symbol} x{LEVERAGE}")
    except Exception as e:
        print("Erreur trade :", e)

# ---------------- MAIN LOOP ----------------
def main():
    print("🚀 Whale Scalping Bot démarré...")
    print(f"Capital: ${TOTAL_CAPITAL} | Auto-Trade: {AUTO_TRADE} | Levier: {LEVERAGE}x")

    while True:
        for symbol in MONITOR_LIST:
            print(f"\n🔍 Analyse {symbol} ...")
            sig = check_signal(symbol)
            if sig:
                direction_emoji = "🟢" if sig["direction"] == "LONG" else "🔴"
                print(f"{direction_emoji} Signal {sig['direction']} sur {symbol} @ {sig['price']:.4f}")
                send_email(
                    f"{direction_emoji} Whale Signal: {symbol} {sig['direction']}",
                    f"""
Symbole : {sig['symbol']}
Direction : {sig['direction']}
Prix actuel : ${sig['price']:.4f}
Stop Loss : ${sig['stop_loss']:.4f}
Take Profit : ${sig['take_profit']:.4f}
RSI : {sig['rsi']:.2f}
EMA20 : {sig['ema20']:.2f} | EMA50 : {sig['ema50']:.2f}
                    """
                )
                execute_trade(sig)
        print(f"⏱️ Pause {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
