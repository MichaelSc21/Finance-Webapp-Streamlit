import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from src.pages.main_page import load_transactions


def create_waterfall_chart(credits_df, debits_df):
    """Generate a Plotly waterfall chart from transaction data."""

    df = pd.merge(credits_df, debits_df)

    # Ensure 'Amount' is numeric and handle debits/credits
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["Amount"] = df.apply(
        lambda row: -row["Amount"] if row["Credit/Debit"] == "Debit" else row["Amount"],
        axis=1
    )
    
    # Sort by date
    df = df.sort_values("Completed Date")
    
    # Calculate running balance
    df["Balance"] = df["Amount"].cumsum()
    
    # Create waterfall steps
    waterfall_df = pd.DataFrame({
        "Date": df["Completed Date"],
        "Transaction": df["Description"],
        "Amount": df["Amount"],
        "Balance": df["Balance"]
    })
    
    # Plotly waterfall
    fig = go.Figure(go.Waterfall(
        name="Balance",
        orientation="v",
        measure=["relative"] * (len(df) - 1) + ["total"],
        x=waterfall_df["Date"].astype(str) + "<br>" + waterfall_df["Transaction"],
        y=waterfall_df["Amount"],
        textposition="outside",
        text=waterfall_df["Amount"].apply(lambda x: f"+{x:.2f}" if x > 0 else f"{x:.2f}"),
        connector={"line": {"color": "gray"}},
    ))
    
    fig.update_layout(
        title="Cash Flow Waterfall",
        xaxis_title="Date & Transaction",
        yaxis_title="Amount",
        showlegend=False,
        template="plotly_dark"  # Match your existing theme
    )
    
    return fig



def waterfall_chart_main():
    


      

    if not st.session_state.uploaded_file_bool: 
        st.error("Please upload your personal finances file in the Main Dashboard")
    elif st.session_state.uploaded_file_bool:
        
        credits_df = st.session_state.credits_df
        debits_df = st.session_state.debits_df

        tab1, _ = st.tabs(["Expenses over time", "Nothing here yet"])

        with tab1:  # Or tab2, depending on where you want it
            st.subheader("Cash Flow Waterfall")
            waterfall_fig = create_waterfall_chart(credits_df, debits_df)  # Pass your filtered DataFrame
            st.plotly_chart(waterfall_fig, use_container_width=True, theme="streamlit")


if __name__ == '__main__':
    waterfall_chart_main()

