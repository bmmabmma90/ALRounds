import streamlit as st
import pandas as pd
import sys
from datetime import datetime
from functions import (
    format_currency,
    format_percentage,
    format_date,
    format_multiple,
    format_large_number,
    add_new_row,
    update_calculated_columns,
    calculate_increase_value,
)

# This program should allow you to import data in a specified format (see Round.csv) which is then validated
# for data in the right format, then totals are calculated

# Set the page configuration to "wide" layout
st.set_page_config(layout="wide")

debug_harness = False
auto_load = True

# --- Column Configuration ---
column_config = {
    "Round #": st.column_config.NumberColumn("#", help="Round Number", format="%d"),
    "Round Name": st.column_config.TextColumn("Round", help="Round Name"),
    "Total Invested": st.column_config.NumberColumn("Round Size", help="Total Invested", format="%d" ),
    "Estimated": st.column_config.TextColumn("Est", help="Estimated"),"Round Ownership": st.column_config.NumberColumn("Round %", help="Round Ownership", format="%.3f%%"),
    "My Ownership": st.column_config.NumberColumn("Our %", help="My Ownership", format="%.4f%%"),
    "Increase (Value)": st.column_config.NumberColumn("Val Increase", help="Increase (Value)", format="%d"),
    "Increase (round/round)": st.column_config.NumberColumn("Rnd/Rnd Inc", help="Increase (round/round)", format="%.2fx"),
    "Name": st.column_config.TextColumn("Name", help="Name"),
    "Premoney": st.column_config.NumberColumn("Premoney", help="Premoney", format="%d"),
    "Post Money": st.column_config.NumberColumn("Post Money", help="Post Money", format="%d"),
    "Invested": st.column_config.NumberColumn("Invested", help="Invested", format="$%.2f"),
    "Dilution (est)": st.column_config.NumberColumn("Dilution (est)", help="Dilution (est)", format="%.1fx"),
    "Date": st.column_config.DateColumn("Date", help="Date"),
}

summary_format_style = {
    "Total_Invested": format_currency,
    "Total_Value": format_currency,
    "First_Val": format_large_number,
    "Last_Val": format_large_number,
    "First_Date": format_date,
    "Last_Date": format_date,
    "Round Increase": format_multiple,
    "Dilution Increase": format_multiple,
}

# --- Styling Functions for DataFrames ---
def highlight_estimated(val):
    """Highlights cells with 'Y' in the 'Estimated' column in yellow."""
    return "background-color: yellow" if val == "Y" else ""


def highlight_values_by_estimated(row):
    """Highlights 'Total Invested' and 'Post Money' with light yellow background if 'Estimated' is 'Y' in the same row."""
    styles = []
    for col in row.index:
        if row["Estimated"] == "Y" and col in ["Total Invested", "Post Money"]:
            styles.append("background-color: lightyellow; color: black")
        else:
            styles.append("")
    return styles


def style_filtered_data(filtered_edited_df):
    """Styles the filtered DataFrame for display, applying various formatting and highlighting."""
    styled_df = filtered_edited_df.style.map(highlight_estimated, subset=["Estimated"])
    styled_df = styled_df.apply(highlight_values_by_estimated, axis=1)
    # styled_df = styled_df.format(summary_format_style)
    styled_df = styled_df.format(format_large_number, subset=["Total Invested", "Premoney", "Post Money"])
    styled_df = styled_df.format(format_percentage, subset=["Round Ownership", "My Ownership"])
    styled_df = styled_df.format(format_multiple, subset=["Increase (round/round)", "Dilution (est)"])
    styled_df = styled_df.format(format_currency, subset=["Invested", "Increase (Value)"])
    styled_df = styled_df.format(format_date, subset=["Date"])
    return styled_df


# --- Session State Initialization ---
if "has_data_file" not in st.session_state:
    st.session_state.has_data_file = False
if "edited_df" not in st.session_state:
    st.session_state.edited_df = pd.DataFrame()
if "summary_df" not in st.session_state:
    st.session_state.summary_df = pd.DataFrame()
if "menu_choice" not in st.session_state:
    st.session_state.menu_choice = "About"


# --- Functions ---
def load_data(uploaded_file):
    """Loads data from a CSV file, handling data type conversions and potential errors."""
    try:
        df = pd.read_csv(uploaded_file, skiprows=1)
        cols_to_convert = [
            "Total Invested",
            "Premoney",
            "Post Money",
            "Invested",
            "Increase (Value)",
            "Round Ownership",
            "My Ownership",
            "Increase (round/round)",
            "Dilution (est)",
        ]
        for col in cols_to_convert:
            df[col] = df[col].fillna(0)  # Set values to 0 if they are not a number
            df[col] = (
                df[col].replace(r"[^\d.]", "", regex=True).astype(float)
            )  # Force all values to a float

        # divide percentage column values by 100
        percentage_columns = ["Round Ownership", "My Ownership"]
        for col in percentage_columns:
            df[col] = df[col]/100
        
        # convert dates
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        st.write(
            f"Exception type {exc_type} with value {exc_value} and traceback {exc_traceback}"
        )
        return pd.DataFrame()


def process_data(df, show_changes):
    """Processes the data by updating calculated columns and increase values."""
    df = update_calculated_columns(df, show_changes)
    df = calculate_increase_value(df)
    return df


def calculate_and_display_total_position(df):
    """Calculates and displays the total position for each company."""
    summary_df = df.groupby("Name").agg(
        Rounds=("Round #", "count"),
        Total_Invested=("Invested", "sum"),
        Total_Value=("Increase (Value)", "sum"),
        First_Val=("Post Money", "first"),
        Last_Val=("Post Money", "last"),
        First_Date=("Date", "first"),
        Last_Date=("Date", "last"),
    ).reset_index()
    summary_df["Round Increase"] = summary_df["Last_Val"] / summary_df["First_Val"]
    summary_df["Dilution Increase"] = summary_df["Total_Value"] / summary_df["Total_Invested"]
    summary_df.sort_values(by="Dilution Increase", ascending=False, inplace=True)
    summary_df_styled = summary_df.style.format(summary_format_style)
    return summary_df, summary_df_styled


# --- Sidebar Menu ---
with st.sidebar:
    st.title("Round Calculator")
    menu_choice = st.radio(
        "Menu", ["About", "Check & Calculate", "Browse Companies", "Totals"], key="menu_choice_sidebar"
    )
    if st.session_state.menu_choice != menu_choice:
        st.session_state.menu_choice = menu_choice


# --- Main App ---
if st.session_state.menu_choice == "About":
    st.title("Round Level Data Editor")
    st.header("About", divider=True)
    st.markdown(
        """
This app helps you manage and analyze round-level investment data. You can load data from a CSV file, check its consistency, perform calculations,
and browse company-specific information.

The usual controls exist to sort by columns :red[:material/arrow_upward:] :red[:material/arrow_downward:], export the data to a CSV :red[:material/download:], search :red[:material/search:] for particular values or use full screen :red[:material/fullscreen:].

Version: 0.1.4
    """
    )

    if auto_load:
        uploaded_file = "/Users/deepseek/Downloads/Round.csv"
        st.session_state.edited_df = load_data(uploaded_file)
        if not st.session_state.edited_df.empty:
            st.session_state.has_data_file = True
            st.write("Loaded Data:")
            st.dataframe(st.session_state.edited_df)
        else:
            st.write("Failed to load")
    else:
        uploaded_file = st.file_uploader("Load Round.csv", type="csv")

        if uploaded_file is not None:
            st.session_state.edited_df = load_data(uploaded_file)
            if not st.session_state.edited_df.empty:
                st.session_state.has_data_file = True
                st.write("Loaded Data:")
                st.dataframe(st.session_state.edited_df)
            else:
                st.write("Failed to load")

elif st.session_state.menu_choice == "Check & Calculate":
    st.header("Check & Calculate", divider=True)
    if not st.session_state.has_data_file:
        st.warning("Please load data in the 'About' section first.")
        st.stop()

    # --- Changes View Options ---
    changes_view_options = ["No Changes", "Highlight Changes", "Show Changes Summary"]
    st.session_state.changes_view_option = st.radio(
        "View Changes:", changes_view_options, key="changes_view_radio", horizontal=True
    )

    show_changes = st.session_state.changes_view_option

    if st.button("Recalculate Data and Total Position"):
        st.session_state.edited_df = process_data(st.session_state.edited_df, show_changes)
        st.session_state.summary_df, summary_df_styled = calculate_and_display_total_position(
            st.session_state.edited_df
        )

    if "edited_df" in st.session_state:

        if debug_harness: 
            print("Current Data", st.session_state.edited_df)

        st.subheader("Edit Data")
        st.session_state.edited_df = st.data_editor(
            st.session_state.edited_df,
            column_config=column_config,
            hide_index=True,
            num_rows="dynamic",
        )

elif st.session_state.menu_choice == "Browse Companies":
    st.header("Browse Companies", divider=True)
    if not st.session_state.has_data_file:
        st.warning("Please load data in the 'About' section first.")
        st.stop()

    edited_df = st.session_state.edited_df
    summary_df = st.session_state.summary_df

    # --- Display Name-Specific Data ---
    st.subheader("View Data by Name")

    # Get unique names
    unique_names = edited_df["Name"].unique()

    if "name_state" not in st.session_state:
        st.session_state.name_state = {name: False for name in unique_names}

    # Use st.radio for pill selection
    selected_name = st.radio(
        "Select a Name to view:", unique_names, key="name_select_radio", horizontal=True
    )
    if selected_name:
        # Filter edited_df for the current name
        filtered_edited_df = edited_df[edited_df["Name"] == selected_name]

        # Apply the styling
        styled_df = style_filtered_data(filtered_edited_df)

        st.write(f"Data for: {selected_name}")
        st.dataframe(styled_df)

        # Filter summary_df for the current name
        if not summary_df.empty:
            filtered_summary_df = summary_df[summary_df["Name"] == selected_name]
            if not filtered_summary_df.empty:
                st.write(f"Summary Data for: {selected_name}")
                filtered_summary_df = filtered_summary_df.style.format(summary_format_style)
                st.dataframe(filtered_summary_df)
            else:
                st.write(f"No summary data found for: {selected_name}")
        else:
            st.write(
                f"Please press Calculate total position in Check and Calculate to display summary data."
            )

        # --- New row functionality with Round # sequence ---
        if st.button("Add New Row"):
            new_row = add_new_row(st.session_state.edited_df)
            st.session_state.edited_df = pd.concat(
                [st.session_state.edited_df, new_row], ignore_index=True
            )
            st.session_state.edited_df = process_data(st.session_state.edited_df)
            st.rerun()

elif st.session_state.menu_choice == "Totals":
    st.header("Totals", divider=True)
    st.write("These total values can be shared with others or the values used to put into 'Overwrite' data to enhance other data.")
    if not st.session_state.has_data_file:
        st.warning("Please load data in the 'About' section first.")
        st.stop()

    if st.session_state.summary_df.empty :
            st.write(
                f"Please press Calculate total position in Check and Calculate to display summary data."
            )
    else :
        summary_df = st.session_state.summary_df
        summary_df_styled = summary_df.style.format(summary_format_style)
        st.dataframe(summary_df_styled, hide_index=True)