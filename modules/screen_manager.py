from __future__ import annotations

import time
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.config import AppConfig
from modules.external_source import ExternalSourceConnector


class NiftyDashboardScreen:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def render(self) -> None:
        st.title("Nifty 50 real-time 5-second interval analyzer")
        controls = self._render_sidebar_controls()

        connector = ExternalSourceConnector(
            source=controls["source"],
            symbol=controls["symbol"],
        )
        is_connected, status_message = connector.connection_status()
        self._render_connection_status(is_connected, status_message)

        self._initialize_data()

        if controls["run_stream"]:
            self._append_tick(connector)

        df = self._build_indicators(controls["window_size"])
        self._render_metrics(df)
        self._render_chart(df, controls["window_size"])

        if controls["run_stream"]:
            time.sleep(self.config.refresh_seconds)
            st.rerun()

    def _render_sidebar_controls(self) -> dict[str, object]:
        st.sidebar.header("Stream controls")
        source = st.sidebar.selectbox(
            "External source",
            options=["Simulated", "Yahoo Finance"],
            index=0,
        )
        symbol = st.sidebar.text_input("Ticker symbol", value=self.config.symbol)
        run_stream = st.sidebar.toggle("Start live 5s feed", value=True)
        window_size = st.sidebar.slider("Moving average window", 5, 30, self.config.default_ma_window)

        return {
            "source": source,
            "symbol": symbol.strip() or self.config.symbol,
            "run_stream": run_stream,
            "window_size": window_size,
        }

    def _render_connection_status(self, is_connected: bool, status_message: str) -> None:
        if is_connected:
            st.success(status_message)
        else:
            st.warning(status_message)

    def _initialize_data(self) -> None:
        if "nifty_data" in st.session_state:
            return

        now = datetime.now()
        dates = pd.date_range(end=now, periods=self.config.seed_points, freq="5s")
        prices = self.config.seed_price + np.cumsum(np.random.normal(0, 2, size=self.config.seed_points))

        st.session_state.nifty_data = pd.DataFrame(
            {
                "Timestamp": dates,
                "Price": prices,
            }
        )

    def _append_tick(self, connector: ExternalSourceConnector) -> None:
        last_price = float(st.session_state.nifty_data["Price"].iloc[-1])
        new_time, new_price = connector.fetch_latest_tick(last_price)
        new_row = pd.DataFrame([{"Timestamp": new_time, "Price": new_price}])
        st.session_state.nifty_data = pd.concat(
            [st.session_state.nifty_data, new_row],
            ignore_index=True,
        ).tail(self.config.history_size)

    def _build_indicators(self, window_size: int) -> pd.DataFrame:
        df = st.session_state.nifty_data.copy()
        df["SMA"] = df["Price"].rolling(window=window_size).mean()
        df["STD"] = df["Price"].rolling(window=window_size).std()
        df["Upper_Band"] = df["SMA"] + (df["STD"] * 2)
        df["Lower_Band"] = df["SMA"] - (df["STD"] * 2)
        return df

    def _render_metrics(self, df: pd.DataFrame) -> None:
        current_price = float(df["Price"].iloc[-1])
        prev_price = float(df["Price"].iloc[-2]) if len(df) > 1 else current_price
        price_diff = round(current_price - prev_price, 2)

        col1, col2, col3 = st.columns(3)
        col1.metric("Live Nifty 50", f"Rs {current_price:,.2f}", f"{price_diff} pts")
        col2.metric(
            "Upper Bollinger band",
            f"Rs {df['Upper_Band'].iloc[-1]:,.2f}"
            if not pd.isna(df["Upper_Band"].iloc[-1])
            else "Calculating...",
        )
        col3.metric(
            "Lower Bollinger band",
            f"Rs {df['Lower_Band'].iloc[-1]:,.2f}"
            if not pd.isna(df["Lower_Band"].iloc[-1])
            else "Calculating...",
        )

    def _render_chart(self, df: pd.DataFrame, window_size: int) -> None:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["Timestamp"],
                y=df["Price"],
                mode="lines+markers",
                name="Nifty 50 price",
                line=dict(color="#00CC96", width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["Timestamp"],
                y=df["SMA"],
                mode="lines",
                name=f"{window_size}-tick SMA",
                line=dict(color="#FFA15A", dash="dash"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["Timestamp"],
                y=df["Upper_Band"],
                mode="lines",
                name="Upper band",
                line=dict(color="rgba(255,0,0,0.3)"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["Timestamp"],
                y=df["Lower_Band"],
                mode="lines",
                name="Lower band",
                line=dict(color="rgba(0,255,0,0.3)"),
            )
        )

        fig.update_layout(
            title="5-second tick stream",
            xaxis_title="Time",
            yaxis_title="Nifty 50 index",
            height=500,
        )
        st.plotly_chart(fig, width="stretch")
