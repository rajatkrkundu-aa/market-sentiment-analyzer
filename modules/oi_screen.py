from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.config import AppConfig


class NiftyOiScreen:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def render(self) -> None:
        st.title("Nifty OI analysis")
        st.caption("Open interest view for Nifty option chain (simulated structure)")

        spot = st.sidebar.number_input("Spot price", min_value=10000.0, max_value=30000.0, value=24500.0, step=50.0)
        strike_step = st.sidebar.selectbox("Strike interval", options=[50, 100], index=1)
        strikes_each_side = st.sidebar.slider("Strikes each side", 5, 20, 10)

        oi_df = self._build_oi_table(spot, strike_step, strikes_each_side)

        call_oi_total = int(oi_df["Call_OI"].sum())
        put_oi_total = int(oi_df["Put_OI"].sum())
        pcr = round((put_oi_total / call_oi_total), 2) if call_oi_total else 0.0
        max_pain = int(oi_df.loc[(oi_df["Call_OI"] + oi_df["Put_OI"]).idxmax(), "Strike"])

        m1, m2, m3 = st.columns(3)
        m1.metric("Put-call ratio (PCR)", f"{pcr}")
        m2.metric("Max pain strike", f"{max_pain}")
        m3.metric("Total OI", f"{call_oi_total + put_oi_total:,}")

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=oi_df["Strike"],
                y=oi_df["Call_OI"],
                name="Call OI",
                marker_color="#f45b69",
            )
        )
        fig.add_trace(
            go.Bar(
                x=oi_df["Strike"],
                y=oi_df["Put_OI"],
                name="Put OI",
                marker_color="#2ec4b6",
            )
        )
        fig.update_layout(
            barmode="group",
            title="Nifty OI by strike",
            xaxis_title="Strike",
            yaxis_title="Open interest",
            height=500,
        )
        st.plotly_chart(fig, width="stretch")

        st.dataframe(
            oi_df,
            width="stretch",
            hide_index=True,
        )

    def _build_oi_table(self, spot: float, strike_step: int, strikes_each_side: int) -> pd.DataFrame:
        atm = int(round(spot / strike_step) * strike_step)
        start = atm - (strikes_each_side * strike_step)
        end = atm + (strikes_each_side * strike_step)
        strikes = np.arange(start, end + strike_step, strike_step)

        # Build smooth OI curves centered around ATM with random market noise.
        distance = np.abs(strikes - atm) / strike_step
        base_curve = np.exp(-distance / 4)

        call_oi = (120000 * base_curve + np.random.randint(5000, 30000, size=len(strikes))).astype(int)
        put_oi = (115000 * base_curve + np.random.randint(5000, 30000, size=len(strikes))).astype(int)

        return pd.DataFrame(
            {
                "Strike": strikes,
                "Call_OI": call_oi,
                "Put_OI": put_oi,
                "Call_OI_Change": np.random.randint(-5000, 5000, size=len(strikes)),
                "Put_OI_Change": np.random.randint(-5000, 5000, size=len(strikes)),
            }
        )
