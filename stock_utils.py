# stock_utils.py

import pandas as pd
from datetime import datetime, timedelta

def summarize_stock(df: pd.DataFrame) -> dict:
    """
    Summarize total stock quantities for CHKO and CHKI in CROD, split by current, yesterday's, and previous stock.
    Current stock is for the current system date; yesterday's stock is for the previous day; previous stock is before that.
    """
    # Ensure data is filtered for CROD
    df_crod = df[df["Storage BIN"] == "CROD"].copy()
    
    # Define current and yesterday's dates (dynamic system date)
    current_date = pd.to_datetime(datetime.now().date())
    yesterday_date = current_date - timedelta(days=1)
    
    # Split into current, yesterday's, and previous stock
    df_current = df_crod[df_crod["GR Date"].dt.date == current_date.date()].copy()
    df_yesterday = df_crod[df_crod["GR Date"].dt.date == yesterday_date.date()].copy()
    df_previous = df_crod[df_crod["GR Date"].dt.date < yesterday_date.date()].copy()
    
    # Group by warehouse and sum quantities
    current_summary = df_current.groupby("EWM WH")["Available Qty"].sum().to_dict()
    yesterday_summary = df_yesterday.groupby("EWM WH")["Available Qty"].sum().to_dict()
    previous_summary = df_previous.groupby("EWM WH")["Available Qty"].sum().to_dict()
    
    # Ensure both CHKO and CHKI are present, default to 0 if missing
    return {
        "CHKO": {
            "current": current_summary.get("CHKO", 0.0),
            "yesterday": yesterday_summary.get("CHKO", 0.0),
            "previous": previous_summary.get("CHKO", 0.0)
        },
        "CHKI": {
            "current": current_summary.get("CHKI", 0.0),
            "yesterday": yesterday_summary.get("CHKI", 0.0),
            "previous": previous_summary.get("CHKI", 0.0)
        }
    }

def categorize_fg_codes(df: pd.DataFrame, warehouse: str, stock_type: str) -> dict:
    """
    Categorize FG codes for a given warehouse and stock type into Ready to Dispatch, Quality, and Blocked.
    stock_type: 'current' (current system date), 'yesterday' (previous day), or 'previous' (before previous day).
    Returns full_df for stock details table.
    """
    # Define current and yesterday's dates
    current_date = pd.to_datetime(datetime.now().date())
    yesterday_date = current_date - timedelta(days=1)
    
    # Filter for the warehouse and CROD
    df_wh = df[(df["EWM WH"] == warehouse) & (df["Storage BIN"] == "CROD")].copy()
    
    # Filter by stock type
    if stock_type == "current":
        df_wh = df_wh[df_wh["GR Date"].dt.date == current_date.date()].copy()
    elif stock_type == "yesterday":
        df_wh = df_wh[df_wh["GR Date"].dt.date == yesterday_date.date()].copy()
    elif stock_type == "previous":
        df_wh = df_wh[df_wh["GR Date"].dt.date < yesterday_date.date()].copy()
    
    # Categorize based on Stock Type
    def get_category(stock_type):
        if stock_type in ["DU", "EU"]:
            return "Ready to Dispatch"
        elif stock_type in ["DQ", "EQ"]:
            return "Quality"
        elif stock_type == "DB":
            return "Blocked"
        return "Unknown"

    df_wh["Category"] = df_wh["Stock Type"].apply(get_category)
    
    # Filter out Unknown categories
    df_wh = df_wh[df_wh["Category"] != "Unknown"].copy()
    
    # Prepare summary DataFrame for visualization
    summary_df = df_wh.groupby(["Product", "Category"])["Available Qty"].sum().reset_index()
    
    # Split into separate DataFrames
    ready_df = df_wh[df_wh["Category"] == "Ready to Dispatch"].copy()
    quality_df = df_wh[df_wh["Category"] == "Quality"].copy()
    blocked_df = df_wh[df_wh["Category"] == "Blocked"].copy()
    
    # Compute counts and total quantities
    return {
        "full_df": df_wh,  # Full DataFrame for stock details table
        "summary_df": summary_df,
        "ready_df": ready_df,
        "ready_count": len(ready_df["Product"].unique()),
        "ready_qty": ready_df["Available Qty"].sum(),
        "quality_df": quality_df,
        "quality_count": len(quality_df["Product"].unique()),
        "quality_qty": quality_df["Available Qty"].sum(),
        "blocked_df": blocked_df,
        "blocked_count": len(blocked_df["Product"].unique()),
        "blocked_qty": blocked_df["Available Qty"].sum()
    }
