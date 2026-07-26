import streamlit as st
import yfinance as yf
import pandas as pd
from textblob import TextBlob
import plotly.express as px

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Market Sentiment MVP", layout="wide")

st.title("📈 Stock Market Sentiment & News Analyzer")
st.markdown("Analyze real-time news headlines alongside price history for any stock ticker.")

# --- Sidebar Controls ---
st.sidebar.header("User Inputs")
ticker_symbol = st.sidebar.text_input("Enter Ticker Symbol", value="AAPL").upper()
period = st.sidebar.selectbox("Price History Period", ("1mo", "3mo", "6mo", "1y"), index=1)

if ticker_symbol:
    ticker = yf.Ticker(ticker_symbol)

    # --- Fetch Historical Data & Plot Price ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"{ticker_symbol} Price Chart ({period})")
        hist = ticker.history(period=period)
        if not hist.empty:
            fig = px.line(
                hist,
                x=hist.index,
                y="Close",
                title=f"{ticker_symbol} Daily Closing Price",
                labels={"Close": "Price ($)", "index": "Date"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No price data found for this ticker.")

    # --- Fetch News & Analyze Sentiment ---
    st.subheader(f"Latest News & Sentiment for {ticker_symbol}")
    news = ticker.news

    if news:
        processed_news = []

        for item in news:
            # Extract title and publisher safely
            content = item.get("content", {})
            title = content.get("title", item.get("title", "No Title"))
            publisher = content.get("provider", {}).get("displayName", "Unknown Provider")
            link = content.get("canonicalUrl", {}).get("url", "#")

            # Perform Sentiment Analysis using TextBlob
            analysis = TextBlob(title)
            polarity = analysis.sentiment.polarity # Ranges from -1.0 (Negative) to 1.0 (Positive)

            # Assign Label based on polarity score
            if polarity > 0.05:
                sentiment = "Bullish 🟢"
            elif polarity < -0.05:
                sentiment = "Bearish 🔴"
            else:
                sentiment = "Neutral ⚪"

            processed_news.append({
                "Title": title,
                "Publisher": publisher,
                "Polarity Score": round(polarity, 2),
                "Sentiment": sentiment,
                "Link": link
            })

        df_news = pd.DataFrame(processed_news)

        # Calculate Aggregate Metrics
        avg_polarity = df_news["Polarity Score"].mean()

        with col2:
            st.subheader("Sentiment Summary")
            st.metric(
                label="Average News Sentiment Polarity",
                value=f"{avg_polarity:.2f}",
                delta="Bullish" if avg_polarity > 0.05 else ("Bearish" if avg_polarity < -0.05 else "Neutral")
            )

            # Sentiment Breakdown Pie Chart
            sentiment_counts = df_news["Sentiment"].value_counts().reset_index()
            sentiment_counts.columns = ["Sentiment", "Count"]

            fig_pie = px.pie(
                sentiment_counts,
                names="Sentiment",
                values="Count",
                title="Sentiment Distribution",
                color="Sentiment",
                color_discrete_map={
                    "Bullish 🟢": "#2ECC71",
                    "Bearish 🔴": "#E74C3C",
                    "Neutral ⚪": "#95A5A6"
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # Render News Table with Links
        st.markdown("### News Headlines Analysis")
        st.dataframe(
            df_news[["Title", "Publisher", "Polarity Score", "Sentiment", "Link"]],
            column_config={
                "Link": st.column_config.LinkColumn("Article Link")
            },
            use_container_width=True
        )

    else:
        st.info("No recent news found for this ticker.")
