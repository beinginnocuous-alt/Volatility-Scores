import streamlit as st
import yfinance as yf
import pandas as pd
import json
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Stock Spike Scanner", layout="centered")

st.title("📈 4-Hour Stock Spike Scanner")
st.write("Calculates 30% rally spikes over the past 365 days (including extended hours trading).")

default_tickers = (
    "VIVK, NIVF, ELPW, ZNB, GCTK, CYCU, CHSN, ONCO, LRHC, IVF, ALP, SHPH, TRUG, "
    "IPW, CISS, CDT, RTB, CLIK, SOAR, UZX, ARTL, NUWE, WHLR, EZGO, NTCL, ALBT, "
    "VSME, CUPR, DRMA, UGRO, ZCMD, CTNT, GDC, TAOP, MASK, CIIT, PMAX, GCTS, "
    "LZMH, ADVB, KIDZ, PRFX, FGL, JYD, SLXN, LHSW, JTAI, GMEX, LNKS, RUBI, "
    "KITT, TRNR, PFSA, AMOD, HAO, PPCB, RBNE, AEHL, INEO, RVYL, CCTG, ITP, "
    "HTOO, LGHL, IMTE, DSS, MITQ, CMCT, ICON, PAVS, HCWC, MRM, NCRA, INHD, "
    "ILAG, SKK, JCSE, UPC, BAOS, RPGL, WBUY, HKIT, RDGT, BJDX, KALA, IVDA, "
    "CPOP, SNYR, EDHL, DLXY, CYAB, COSM, AIXC, FCHL, FCUV, OBAI, OTLK, JUNS, "
    "CENN, NEXR, TOP, YFOR, INLF, RAYA, WETO, LESL, CRIS, SDOT, LGCL, VBIO, "
    "ONFO, GRML, OMH, JZXN, RITRF, LHAI, YMT, FFAI, OFAL, HLSQ, UCAR, YYAI, "
    "APUS, SGRX, OLOX, TNMG, GIPR"
)

user_input = st.text_area("Stock Watchlist (comma-separated):", default_tickers, height=150)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

def push_scores_to_gist(scores_dict):
    token   = st.secrets["GITHUB_TOKEN"]
    gist_id = st.secrets["GIST_ID"]
    payload = {
        "files": {
            "scores.json": {
                "content": json.dumps(scores_dict, indent=2)
            }
        }
    }
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    r = requests.patch(
        f"https://api.github.com/gists/{gist_id}",
        headers=headers,
        json=payload
    )
    return r.status_code == 200

def calculate_stock_score(ticker_symbol):
    try:
        end_date   = datetime.now()
        start_date = end_date - timedelta(days=365)
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(start=start_date, end=end_date, interval="1h", prepost=True)
        if df.empty:
            return 0, 0
        df_4h = df.resample('4h').agg({
            'Open':   'first',
            'High':   'max',
            'Low':    'min',
            'Close':  'last',
            'Volume': 'sum'
        }).dropna()
        score    = 0
        in_spike = False
        current_low = df_4h['Low'].iloc[0]
        for i in range(len(df_4h)):
            candle_high = df_4h['High'].iloc[i]
            candle_low  = df_4h['Low'].iloc[i]
            if candle_low < current_low and not in_spike:
                current_low = candle_low
            gain = (candle_high - current_low) / current_low if current_low > 0 else 0
            if gain >= 0.30 and not in_spike:
                score   += 1
                in_spike = True
            elif gain < 0.30 and in_spike:
                in_spike    = False
                current_low = candle_low
        return score, len(df_4h)
    except Exception:
        return 0, 0

if st.button("Run Scanner", type="primary"):
    results       = []
    progress_bar  = st.progress(0)
    status_text   = st.empty()
    total_tickers = len(ticker_list)

    for idx, symbol in enumerate(ticker_list):
        status_text.text(f"Scanning ({idx+1}/{total_tickers}): {symbol}")
        score, candles_count = calculate_stock_score(symbol)
        status = "Active" if candles_count > 0 else "Data Unavailable"
        results.append({
            "Ticker":          symbol,
            "30% Spike Score": score,
            "Status":          status
        })
        progress_bar.progress((idx + 1) / total_tickers)

    status_text.text("Scan complete! Pushing scores to website...")

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by="30% Spike Score", ascending=False)

    scores_dict = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        "scores": {
            row["Ticker"]: row["30% Spike Score"]
            for _, row in df_results.iterrows()
            if row["Status"] == "Active"
        }
    }

    success = push_scores_to_gist(scores_dict)
    if success:
        st.success("✅ Scores pushed to website successfully!")
    else:
        st.error("❌ Failed to push scores to Gist — check your token and Gist ID in secrets.")

    st.subheader("Results (Sorted by Highest Spikes)")
    st.dataframe(df_results, use_container_width=True)

    st.subheader("Top Performers")
    top_3 = df_results[df_results["Status"] == "Active"].head(3)
    cols  = st.columns(3)
    for idx, (_, row) in enumerate(top_3.iterrows()):
        with cols[idx]:
            st.metric(label=row["Ticker"], value=f"{row['30% Spike Score']} Spikes")
