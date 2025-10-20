#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whale Scalping Bot - Version interactive
IA + 60% threshold + SMC + FVG + Fundamentals + Auto-trade + Email alerts
Compatible Python 3.10+
"""

import os, time, math, json, requests, pandas as pd
import ccxt
import pandas_ta as ta
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime

# ===============================================================
# 🔧 Configuration initiale
# ===============================================================

load_dotenv()

KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY")
KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET")
KUCOIN_PASSPHRASE = os.getenv("KUCOIN_PASSPHRASE")

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TO_EMAIL = os.getenv("TO_EMAIL", SMTP_USER)

TOTAL_CAPITAL = float(os.getenv("TOTAL_CAPITAL_USDT", 18))
LEVERAGE = int(os.getenv("LEVERAGE", 3))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30))
AI_THRESHOLD = 60.0
AUTO_TRADE = True

# ===============================================================
# ⚙️ Initialisation des exchanges
# ===============================================================
try:
    exchange = ccxt.kucoinfutures({
        'apiKey': KUCOIN_API_KEY,
        'secret': KUCOIN_API_SECRET,
        'password': KUCOIN_PASSPHRASE,
        'enableRateLimit': True,
    })
    balance = exchange.fetch_balance()
    usdt_balance = balance.get('USDT', {}).get('free', 0)
    print(f"✅ KuCoin Futures connecté — Solde: {usdt_balance:.2f} USDT")
except Exception as e:
    print(f"❌ Échec de connexion KuCoin : {e}")

# ===============================================================
# ✉️ Vérification SMTP Gmail
# ===============================================================
def test_smtp():
    if not SMTP_USER or not SMTP_PASS:
        print("⚠️  SMTP Gmail non configuré (.env incomplet)")
        return False
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        msg = MIMEText("✅ Bot prêt (test SMTP)", "plain", "utf-8")
        msg["Subject"] = "Whale Bot : test de connexion"
        msg["From"] = SMTP_USER
        msg["To"] = TO_EMAIL
        server.sendmail(SMTP_USER, [TO_EMAIL], msg.as_string())
        server.quit()
        print("✅ Gmail SMTP prêt pour alertes")
        return True
    except Exception as e:
        print(f"❌ Erreur SMTP Gmail : {e}")
        return False

test_smtp()

print(f"🎯 Seuil IA : {AI_THRESHOLD:.0f}% — Auto-trade : {AUTO_TRADE} — Intervalle : {CHECK_INTERVAL}s\n")

# ===============================================================
# 📊 Fonctions d’analyse technique
# ===============================================================

def fetch_ohlcv(symbol="BTC/USDT", timeframe="5m", limit=200):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
        return df.astype(float)
    except Exception as e:
        print(f"⚠️ Erreur OHLCV {symbol} : {e}")
        return None

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df["ema20"] = ta.ema(df["close"], 20)
    df["ema50"] = ta.ema(df["close"], 50)
    df["rsi"] = ta.rsi(df["close"], 14)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], 14)
    macd = ta.macd(df["close"])
    df["macd"] = macd["MACD_12_26_9"]
    df["macds"] = macd["MACDs_12_26_9"]
    df["supertrend"] = ta.supertrend(df["high"], df["low"], df["close"], 10, 3.0)["SUPERT_10_3.0"]
    return df

# ===============================================================
# 🧠 Analyse IA + Smart Money Concept + FVG
# ===============================================================

def fair_value_gap(df):
    try:
        gaps = []
        for i in range(2, len(df)):
            prev_low = df["low"].iloc[i-2]
            prev_high = df["high"].iloc[i-2]
            current_low = df["low"].iloc[i]
            current_high = df["high"].iloc[i]
            if current_low > prev_high:  # gap haussier
                gaps.append(("bullish", df.index[i]))
            elif current_high < prev_low:  # gap baissier
                gaps.append(("bearish", df.index[i]))
        return gaps
    except Exception:
        return []

def smc_score(df):
    try:
        recent = df.tail(10)
        ema_up = recent["ema20"].iloc[-1] > recent["ema50"].iloc[-1]
        st_up = recent["supertrend"].iloc[-1] < recent["close"].iloc[-1]
        rsi = recent["rsi"].iloc[-1]
        base = 50
        if ema_up and st_up: base += 10
        if rsi > 60: base += 5
        if rsi < 40: base -= 5
        return max(0, min(base, 100))
    except Exception:
        return 50
      # ===============================================================
# 🧩 Analyse fondamentale via CoinGecko
# ===============================================================

def fundamental_analysis(coin_id="bitcoin"):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        data = requests.get(url, params={"localization": "false"}, timeout=15).json()
        mcap = data["market_data"]["market_cap"]["usd"]
        vol = data["market_data"]["total_volume"]["usd"]
        change_24h = data["market_data"]["price_change_percentage_24h"]
        community = data.get("community_data", {})
        twitter = community.get("twitter_followers", 0)
        reddit = community.get("reddit_subscribers", 0)

        score = 50
        if vol / mcap > 0.2: score += 10
        if change_24h > 5: score += 5
        if twitter > 100000: score += 5
        if reddit > 50000: score += 5
        if mcap < 20000000: score += 5
        return min(score, 100)
    except Exception:
        return 50

# ===============================================================
# 🤖 IA Scoring global (technique + fondamentale + SMC + FVG)
# ===============================================================

def ai_score(df, coin_id):
    df = compute_indicators(df)
    fvg_list = fair_value_gap(df)
    smc_val = smc_score(df)
    fund_val = fundamental_analysis(coin_id)
    last = df.iloc[-1]

    score = 0
    if last["ema20"] > last["ema50"]: score += 15
    if last["macd"] > last["macds"]: score += 10
    if last["supertrend"] < last["close"]: score += 10
    if 45 < last["rsi"] < 60: score += 10
    score += smc_val * 0.2
    score += fund_val * 0.3
    score += (len(fvg_list) % 3) * 5  # présence de gaps

    return min(100, round(score, 2))

# ===============================================================
# 💰 Gestion des positions & Risk/Reward
# ===============================================================

def trade_decision(symbol, df, coin_id):
    score = ai_score(df, coin_id)
    if score < AI_THRESHOLD:
        print(f"⏳ {symbol}: score IA {score:.1f}% < {AI_THRESHOLD:.0f}% (aucune action)")
        return None

    last = df.iloc[-1]
    price = last["close"]
    atr = last["atr"]
    direction = "LONG" if last["ema20"] > last["ema50"] else "SHORT"
    stop_loss = price - atr if direction == "LONG" else price + atr
    take_profit = price + (2 * atr) if direction == "LONG" else price - (2 * atr)

    risk = 0.02
    risk_amount = TOTAL_CAPITAL * risk
    qty = risk_amount / abs(price - stop_loss)
    qty = max(qty, 0.0001)

    print(f"🟢 Signal {symbol} {direction} | IA {score:.1f}% | Entrée {price:.4f} | SL {stop_loss:.4f} | TP {take_profit:.4f} | Qty {qty:.5f}")
    return {
        "symbol": symbol,
        "direction": direction,
        "score": score,
        "entry": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "qty": qty
    }

# ===============================================================
# 🧭 Exécution de trades KuCoin + Email alertes
# ===============================================================

def send_email(subject, body):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = TO_EMAIL
        server.sendmail(SMTP_USER, [TO_EMAIL], msg.as_string())
        server.quit()
        print("📩 Alerte envoyée par email")
    except Exception as e:
        print(f"❌ Envoi email échoué : {e}")

def execute_trade(signal):
    if not AUTO_TRADE:
        print("⚠️ Auto-trade désactivé")
        return
    try:
        side = "buy" if signal["direction"] == "LONG" else "sell"
        exchange.set_leverage(LEVERAGE, signal["symbol"])
        order = exchange.create_market_order(signal["symbol"], side, signal["qty"], params={"leverage": LEVERAGE})
        print(f"✅ Trade exécuté sur KuCoin : {signal['symbol']} {side.upper()} @ {signal['entry']:.4f}")
        send_email(
            f"Whale Bot - {signal['symbol']} {side.upper()}",
            f"""
💹 Trade exécuté :
Symbole : {signal['symbol']}
Direction : {signal['direction']}
Entrée : {signal['entry']:.4f}
Stop Loss : {signal['stop_loss']:.4f}
Take Profit : {signal['take_profit']:.4f}
IA Score : {signal['score']}%
Qty : {signal['qty']:.4f}
"""
        )
    except Exception as e:
        print(f"❌ Échec trade {signal['symbol']} : {e}")
      # ===============================================================
# 🔎 Sélection des paires Futures USDT les plus prometteuses
# (par volume et variation 24h)
# ===============================================================

def get_top_futures_symbols(n=30, min_quote_vol_usd=10_000_000, min_abs_change_pct=5):
    try:
        markets = exchange.load_markets()
    except Exception:
        markets = {m['symbol']: m for m in exchange.fetch_markets()}
    # Filtrer les swaps en USDT
    candidates = [s for s, m in markets.items()
                  if m.get('type') in ('swap', 'future', 'futures', None)
                  and 'USDT' in s
                  and m.get('active', True)]
    scored = []
    for sym in candidates:
        try:
            t = exchange.fetch_ticker(sym)
            qv = t.get('quoteVolume') or t.get('baseVolume') or 0
            pct = abs(t.get('percentage') or 0)
            if qv >= min_quote_vol_usd and pct >= min_abs_change_pct:
                scored.append((sym, float(qv)))
        except Exception:
            continue
        time.sleep(0.05)
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in scored[:n]]

# ===============================================================
# 🗺️ CoinGecko ID mapping minimal (fallback = base symbol minuscule)
# ===============================================================

COINGECKO_MAP = {
    'btc':'bitcoin','eth':'ethereum','bnb':'binancecoin','sol':'solana','xrp':'ripple',
    'ada':'cardano','doge':'dogecoin','matic':'matic-network','dot':'polkadot','ltc':'litecoin',
    'avax':'avalanche-2','atom':'cosmos','link':'chainlink','near':'near','apt':'aptos',
    'arb':'arbitrum','op':'optimism','inj':'injective-protocol','kas':'kaspa','tia':'celestia',
    'sei':'sei-network','sui':'sui','stx':'blockstack','fil':'filecoin','xmr':'monero',
    'etc':'ethereum-classic','bch':'bitcoin-cash','ftm':'fantom','egld':'elrond-erd-2',
    'mina':'mina-protocol','imx':'immutable-x','rndr':'render-token'
}

def base_to_cgid(symbol: str) -> str:
    base = symbol.split('/')[0].split(':')[0].split('-')[0].lower()
    return COINGECKO_MAP.get(base, base)

# ===============================================================
# 🏁 Main loop interactive
# ===============================================================

def main():
    print("\n==============================================")
    print("🚀 Whale Scalping Bot — Mode INTERACTIF")
    print("----------------------------------------------")
    print(f"🎯 Seuil IA actif : {AI_THRESHOLD:.0f}%")
    print(f"⚡ Auto-trade : {AUTO_TRADE} | Levier : {LEVERAGE}x | Intervalle : {CHECK_INTERVAL}s")
    print("==============================================\n")

    # Bannière de démarrage déjà affichée par les tests KuCoin/SMTP au début du script

    last_universe_ts = 0
    universe = []

    while True:
        try:
            # Rafraîchir l'univers toutes les 10 minutes
            now = time.time()
            if now - last_universe_ts > 600 or not universe:
                print("🔍 Sélection des 30 paires Futures USDT les plus actives...")
                universe = get_top_futures_symbols(n=30)
                last_universe_ts = now
                if not universe:
                    print("⚠️ Aucun candidat trouvé (volume/variation insuffisants).")
                    time.sleep(CHECK_INTERVAL)
                    continue
                print("✅ Univers mis à jour:", ", ".join(universe[:10]), "…")

            for sym in universe:
                print(f"🔎 Analyse {sym} ...")
                df = fetch_ohlcv(sym, timeframe="5m", limit=200)
                if df is None or len(df) < 60:
                    print(f"⚠️ Données insuffisantes pour {sym}")
                    continue

                # Calcul des indicateurs + décision
                try:
                    coin_id = base_to_cgid(sym)
                    sig = trade_decision(sym, compute_indicators(df.copy()), coin_id)
                    if sig:
                        execute_trade(sig)
                except Exception as e:
                    print(f"⚠️ Erreur décision trade {sym} : {e}")

                # rythme
                time.sleep(0.5)

            print(f"⏱️ Pause {CHECK_INTERVAL}s...\n")
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n🛑 Arrêt manuel demandé. Au revoir.")
            break
        except Exception as e:
            print(f"💥 Erreur boucle principale : {e}")
            time.sleep(5)

# Lancement si exécuté directement
if __name__ == "__main__":
    # Les tests KuCoin/SMTP et le print du seuil IA sont effectués plus haut, à l'import
    try:
        main()
    except Exception as e:
        print("❌ Échec lancement main():", e)
