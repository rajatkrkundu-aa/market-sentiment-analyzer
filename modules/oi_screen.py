from __future__ import annotations

import json
from http.cookiejar import CookieJar
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, build_opener

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
        st.caption("Open interest view mapped from NSE option chain API")

        st.sidebar.subheader("OI source settings")
        expiry = st.sidebar.text_input("Expiry", value="28-Jul-2026")
        strike_step = st.sidebar.selectbox("Strike interval", options=[50, 100], index=1)
        strikes_each_side = st.sidebar.slider("Strikes around ATM", 5, 20, 10)

        oi_df, source_note = self._load_oi_table(expiry, strike_step, strikes_each_side)
        st.info(source_note)

        if oi_df.empty:
            st.warning("No OI rows are available for the selected expiry.")
            return

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

    def _load_oi_table(self, expiry: str, strike_step: int, strikes_each_side: int) -> tuple[pd.DataFrame, str]:
        payload, error = self._fetch_option_chain_payload(expiry)
        if payload is None:
            fallback = self._build_simulated_table(24500.0, strike_step, strikes_each_side)
            return fallback, f"NSE API unavailable ({error}). Showing simulated fallback data."

        api_df = self._parse_nse_payload(payload)
        if api_df.empty:
            fallback = self._build_simulated_table(24500.0, strike_step, strikes_each_side)
            return fallback, "NSE API returned no usable OI rows. Showing simulated fallback data."

        # Focus around ATM for readability.
        underlying = payload.get("records", {}).get("underlyingValue")
        if underlying is not None:
            atm = int(round(float(underlying) / strike_step) * strike_step)
            low = atm - (strikes_each_side * strike_step)
            high = atm + (strikes_each_side * strike_step)
            api_df = api_df[(api_df["Strike"] >= low) & (api_df["Strike"] <= high)].copy()

        if api_df.empty:
            return self._parse_nse_payload(payload), "Using full NSE chain (ATM slice returned empty)."

        return api_df, "Using live NSE option chain API data."

    def _fetch_option_chain_payload(self, expiry: str) -> tuple[dict | None, str | None]:
        params = {
            "type": "Indices",
            "symbol": "NIFTY",
            "expiry": expiry,
        }
        api_url = f"https://www.nseindia.com/api/option-chain-v3?{urlencode(params)}"

        cookie_jar = CookieJar()
        opener = build_opener(HTTPCookieProcessor(cookie_jar))
        opener.addheaders = [
            (
                "User-Agent",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            ),
            ("Accept", "application/json,text/plain,*/*"),
            ("Accept-Language", "en-US,en;q=0.9"),
            ("Referer", "https://www.nseindia.com/option-chain"),
            ("Origin", "https://www.nseindia.com"),
            ("Connection", "keep-alive"),
        ]

        try:
            # Prime cookies before API call.
            opener.open("https://www.nseindia.com", timeout=10).read(256)
            with opener.open(api_url, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload, None
        except Exception as exc:
            return None, str(exc)

    def _parse_nse_payload(self, payload: dict) -> pd.DataFrame:
        records = payload.get("records", {})
        rows = records.get("data") or payload.get("filtered", {}).get("data") or payload.get("data") or []

        parsed_rows: list[dict] = []
        for row in rows:
            strike = row.get("strikePrice") or row.get("strike")
            if strike is None:
                continue

            ce = row.get("CE") or row.get("ce") or {}
            pe = row.get("PE") or row.get("pe") or {}

            parsed_rows.append(
                {
                    "Strike": int(strike),
                    "Call_OI": int(ce.get("openInterest") or 0),
                    "Put_OI": int(pe.get("openInterest") or 0),
                    "Call_OI_Change": int(ce.get("changeinOpenInterest") or 0),
                    "Put_OI_Change": int(pe.get("changeinOpenInterest") or 0),
                }
            )

        if not parsed_rows:
            return pd.DataFrame(columns=["Strike", "Call_OI", "Put_OI", "Call_OI_Change", "Put_OI_Change"])

        df = pd.DataFrame(parsed_rows)
        df.sort_values("Strike", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def _build_simulated_table(self, spot: float, strike_step: int, strikes_each_side: int) -> pd.DataFrame:
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
