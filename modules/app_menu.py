from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class MenuItem:
    key: str
    label: str


class AppMenu:
    def __init__(self) -> None:
        self.items = [
            MenuItem(key="live", label="Live analyzer"),
            MenuItem(key="oi", label="Nifty OI analysis"),
        ]
        self._label_to_key = {item.label: item.key for item in self.items}

    def render(self) -> str:
        if "top_menu" not in st.session_state:
            st.session_state.top_menu = self.items[0].label

        selected_label = st.segmented_control(
            "Top menu",
            options=[item.label for item in self.items],
            default=st.session_state.top_menu,
            selection_mode="single",
            key="top_menu",
        )

        if selected_label is None:
            selected_label = self.items[0].label

        return self._label_to_key.get(selected_label, self.items[0].key)
