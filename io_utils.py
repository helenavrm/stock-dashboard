# io_utils.py

import os
from typing import Union, IO
import pandas as pd
import logging

# Set up logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)
logger = logging.getLogger("io_utils")

def load_stock_data(
    filepath_or_buffer: Union[str, IO[bytes]],
    sheet_name: str = "Sheet1"
) -> pd.DataFrame:
    """
    Load stock data from Excel (xlsx/xls), CSV, or Parquet, picking only the needed columns.
    GR Date is parsed as DD.MM.YYYY (e.g., 24.06.2025).
    """
    usecols = [
        "EWM WH",
        "Storage BIN",
        "Product",
        "Material Description",
        "Available Qty",
        "Stock Type",
        "GR Date",
        "Handling Unit"
    ]

    # Detect file extension
    ext = ""
    if hasattr(filepath_or_buffer, "name"):
        ext = os.path.splitext(filepath_or_buffer.name)[1].lower()
    logger.info(f"Detected file extension: {ext}")

    # Load data based on file type
    try:
        if ext == ".csv":
            logger.info("Loading CSV file")
            df = pd.read_csv(filepath_or_buffer, usecols=usecols)
            df["GR Date"] = pd.to_datetime(df["GR Date"], format="%d.%m.%Y", errors="coerce")
        elif ext in (".parquet", ".pq"):
            logger.info("Loading Parquet file")
            df = pd.read_parquet(filepath_or_buffer, columns=usecols)
            df["GR Date"] = pd.to_datetime(df["GR Date"], errors="coerce")
        elif ext in (".xlsx", ".xls"):
            logger.info(f"Loading Excel file with extension {ext}")
            # Try openpyxl first for .xlsx
            try:
                df = pd.read_excel(
                    filepath_or_buffer,
                    sheet_name=sheet_name,
                    usecols=usecols,
                    engine="openpyxl"
                )
                df["GR Date"] = pd.to_datetime(df["GR Date"], format="%d.%m.%Y", errors="coerce")
                logger.info("Successfully loaded with openpyxl")
            except Exception as e1:
                logger.warning(f"openpyxl failed: {str(e1)}. Trying xlrd for .xls...")
                # Fallback to xlrd for .xls
                df = pd.read_excel(
                    filepath_or_buffer,
                    sheet_name=sheet_name,
                    usecols=usecols,
                    engine="xlrd"
                )
                df["GR Date"] = pd.to_datetime(df["GR Date"], format="%d.%m.%Y", errors="coerce")
                logger.info("Successfully loaded with xlrd")
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
    except Exception as e:
        logger.error(f"File loading failed: {str(e)}")
        raise ValueError(f"Failed to load file: {str(e)}")

    # Validate required columns
    required = set(usecols)
    missing = required - set(df.columns)
    if missing:
        logger.error(f"Missing columns: {missing}")
        raise ValueError(f"Stock data is missing columns: {missing}")

    # Basic data cleaning
    logger.info("Performing data cleaning")
    df["Available Qty"] = pd.to_numeric(df["Available Qty"], errors="coerce").fillna(0)
    df["EWM WH"] = df["EWM WH"].astype(str).str.strip()
    df["Storage BIN"] = df["Storage BIN"].astype(str).str.strip()
    df["Product"] = df["Product"].astype(str).str.strip()
    df["Stock Type"] = df["Stock Type"].astype(str).str.strip()
    df["Handling Unit"] = df["Handling Unit"].astype(str).str.strip()

    # Log rows with invalid GR Date
    invalid_dates = df["GR Date"].isna()
    if invalid_dates.any():
        logger.warning(f"Found {invalid_dates.sum()} rows with invalid GR Date values: {df[invalid_dates]['GR Date'].tolist()[:10]}")
        # Keep rows with invalid dates, mark them for review
        df["GR Date Invalid"] = invalid_dates
    else:
        df["GR Date Invalid"] = False

    logger.info(f"Loaded {len(df)} rows")
    return df