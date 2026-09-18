import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Stock Spike Scanner", layout="centered")

st.title("📈 4-Hour Stock Spike Scanner")
st.write("Calculates 30% rally spikes over the past 365 days (including extended hours trading).")

# Input field for stock tickers
default_tickers = "VIVK, NIVF, ELPW, ZNB, GCTK"
user_input = st.text_input("Enter stock tickers (separated by commas):", default_tickers)

# Convert input string into a list of cleaned ticker symbols
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

def calculate_stock_score(ticker_symbol):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(start=start_date, end=end_date, interval="1h", prepost=True)
    
    if df.empty:
        return 0, 0

    df_4h = df.resample('4h').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()

    score = 0
    in_spike = False
    current_low = df_4h['Low'].iloc[0]

    for i in range(len(df_4h)):
        candle_high = df_4h['High'].iloc[i]
        candle_low = df_4h['Low'].iloc[i]

        if candle_low < current_low and not in_spike:
            current_low = candle_low

        gain = (candle_high - current_low) / current_low if current_low > 0 else 0

        if gain >= 0.30 and not in_spike:
            score += 1
            in_spike = True
        elif gain < 0.30 and in_spike:
            in_spike = False
            current_low = candle_low

    return score, len(df_4h)

if st.button("Run Scanner", type="primary"):
    results = []
    
    with st.spinner("Scanning 4-hour candles and calculating scores..."):
        for symbol in ticker_list:
            score, candles_count = calculate_stock_score(symbol)
            status = "Active" if candles_count > 0 else "Data Unavailable"
            results.append({
                "Ticker": symbol,
                "30% Spike Score": score,
                "Status": status
            })
            
    df_results = pd.DataFrame(results)
    
    st.subheader("Results")
    st.dataframe(df_results, use_container_width=True)
    
    # Display highlight metric cards for high scores
    st.subheader("Top Performers")
    cols = st.columns(min(len(ticker_list), 3))
    sorted_results = sorted(results, key=lambda x: x["30% Spike Score"], reverse=True)
    
    for idx, item in enumerate(sorted_results[:3]):
        with cols[idx % len(cols)]:
            st.metric(label=item["Ticker"], value=f"{item['30% Spike Score']} Spikes")
