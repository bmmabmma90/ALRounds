import streamlit as st
import pandas as pd
from datetime import datetime

debug_harness = False

def format_currency(value):
    """Formats a number as currency with $ and thousands separator."""
    if pd.isna(value):
      return ""
    try:
        return "${:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return str(value) # just pass it through if can't do any formatting

def format_date(date):
    """Formats a date to DD MM YY format for the screen but if the value is zero then just return an empty string"""
    if pd.isna(date):
        return ""
    else:
        return date.strftime("%b %Y")

def format_percentage(value):
    """Formats a number as a percentage with 0 decimal places."""
    if pd.isna(value):
      return ""
    try:
      return "{:.2%}".format(float(value))
    except (ValueError, TypeError):
        return str(value) # just pass it through if can't do any formatting

def format_multiple(value):
    """Formats a number as a multiple with 1 decimal place and 'x'."""
    if pd.isna(value):
      return ""
    try:
      return "{:.2f}x".format(float(value))
    except (ValueError, TypeError):
        return str(value) # just pass it through if can't do any formatting

def format_large_number(value):
    """Formats a number with K or M suffix."""
    if pd.isna(value):
        return ""
    try:
        value = float(value)
        if value >= 1e6:
            return f"{value / 1e6:.2f}M"
        elif value >= 1e3:
            return f"{value / 1e3:.2f}K"
        else:
            return f"{value:.2f}"
    except (ValueError, TypeError):
        return str(value)

# --- Highlight Changes ---
def highlight_diff(row):
    """Highlights cells that have been updated."""
    styles = []
    if debug_harness : print("Entered highlight_diff with row",row)
    for col in row.index:
        if col.endswith('_updated'):
            if debug_harness : print(col," column ends with _updated")
            original_col = col.replace('_updated', '')
            if not pd.isna(row[original_col]) and not pd.isna(row[col]) and row[original_col] != row[col]:
                styles.append('background-color: green') #new value
            elif not pd.isna(row[original_col]) and not pd.isna(row[col]) and row[original_col] == row[col]:
                styles.append('') # no change
            elif pd.isna(row[original_col]) and not pd.isna(row[col]):
                styles.append('background-color: green') #new value
            else:
                styles.append('')

        elif not col.endswith('_updated') and f'{col}_updated' in row.index:
            if not pd.isna(row[col]) and not pd.isna(row[f'{col}_updated']) and row[col] != row[f'{col}_updated']:
                styles.append('background-color: orange')  # original value (changed)
            else:
                styles.append('')  # no change
        else:
            styles.append('')
    if debug_harness : print("Exiting highlight diff")
    return styles

def add_new_row(edited_df):
    """Adds a new row to the edited_df DataFrame with default values and next Round #."""
    if not edited_df.empty:
        try:
            next_round_number = edited_df["Round #"].max() + 1
        except:
            next_round_number = 1
    else:
        next_round_number = 1

    # Create a new row with default values (empty strings or 0)
    new_row = pd.DataFrame({col: [""] for col in edited_df.columns}, index=[0])
    for col in edited_df.select_dtypes(include=['number']):
      new_row[col]=0

    #Set some values correctly to start
    new_row["Round #"] = next_round_number # same as previous
    new_row["Date"] = datetime.now() # as now for editing
    if not edited_df.empty: new_row["Name"] = edited_df["Name"].iloc[-1]      #Set the company name to be the same as the previous one (if there is one)

    return new_row

def update_calculated_columns(original_df, show_changes):
    """ Updates the calculated columns based on other data, such as round on round increases and dilution
    """
    if debug_harness: print("Entered update_calculated_columns")

    df = original_df.copy() # Make a copy of the original df to modify and replace into

    # # Remove total from the data frame so it doesn't get in the way - this probably doesn't exist any more
    if 'Total' in df['Name'].values:
        df = df[df['Name'] != 'Total']
    if debug_harness: print("with values in Round Ownership",df['Round Ownership'])

    # Get the unique names
    unique_names = df['Name'].unique()
    # Initialize an empty DataFrame to store all filtered_dfs
    all_filtered_dfs = pd.DataFrame(columns=df.columns)
    
    debug_harness_2 = False
    # Loop through unique names 
    for name in unique_names:

        if debug_harness_2: print("Looking at Name:", name)
        # Filter the DataFrame for the current name
        filtered_df = df[df['Name'] == name].copy()  # Create a copy to avoid warnings
        # Process each row for the current name
        for index, row in filtered_df.iterrows():
            if row['Name'] == 'Sanas' : 
                debug_harness_2 = False
            else :
                debug_harness_2 = False
            round_number = int(row["Round #"])
            if debug_harness_2 : print("Row",row)
            if debug_harness_2 : print("-Round:",round_number)
            # Fix in here - deal with special cases
            if row['Round Name'] == 'Adjustment': # Note when totalling will also need to overwrite at this point
                if pd.notna(row["Dilution (est)"]) and row["Dilution (est)"] != 0.0:
                    if debug_harness_2: print("-- Value to overwrite found with Dilution(est):", row["Dilution (est)"])
                    continue  # Skip the rest of the calculations for this row
            # check if row['Estimated'] = 'Y' and Round Ownership > 0, if so it will fill in based on the values it has specifically:
            # if Post money is empty but Total Invested, calculate Post money = Total Invested / Round Ownership
            # if Total Invested is empty but Post Money, calculate Total Invested = Post Money * Round Ownership 
            if row['Estimated'] == 'Y' and row['Round Ownership'] > 0:

                if debug_harness_2 : print("Estimated is 'Y' and Round ownership > 0")
                if row["Total Invested"] > 0:
                    post_money_overwrite = row["Total Invested"] / row["Round Ownership"]
                    filtered_df.loc[index, 'Post Money'] = post_money_overwrite # Update in filtered df
                    row['Post Money'] = post_money_overwrite # update in the row for subsequent calcs
                    if debug_harness_2 : print("-- Post Money in estimated is 'Y':",post_money_overwrite)
                elif row["Post Money"] > 0:
                    total_invested_overwrite = row["Post Money"] * row["Round Ownership"]
                    filtered_df.loc[index, 'Total Invested'] = total_invested_overwrite # Update in filtered df
                    row['Total Invested'] = total_invested_overwrite # update in the row for subsequent calcs
                    if debug_harness_2 : print("-- Total Invested in estimated is 'Y':",total_invested_overwrite)

            # Check + Fix: Premoney + Total Invested == Post Money - Advanced version of this should interpolate what is missing - at the moment you put in the pre-money
            if ( pd.notna(row["Premoney"]) and pd.notna(row["Total Invested"]) and row["Post Money"] == 0) :
                postmoney_overwrite = row["Premoney"] + row["Total Invested"]
                filtered_df.loc[index, 'Post Money'] = postmoney_overwrite # Update in filtered df
                row['Post Money'] = postmoney_overwrite # update in the row for subsequent calcs
                if debug_harness_2 : print("-- Post Money:",postmoney_overwrite)
            elif ( row["Premoney"] == 0) and pd.notna(row["Total Invested"]) and pd.notna(row["Post Money"]):
                premoney_overwrite = row["Post Money"] - row["Total Invested"]
                filtered_df.loc[index, 'Premoney'] = premoney_overwrite # Update in filtered df
                row['Premoney'] = premoney_overwrite # update in the row for subsequent calcs
                if debug_harness_2 : print("-- Premoney:",premoney_overwrite)

            # Check: Round Ownership == Total Invested / Post Money
            if ( pd.notna(row["Total Invested"]) and pd.notna(row["Post Money"]) and row["Post Money"] > 0) :
                ownership_overwrite = row["Total Invested"] / row["Post Money"]
                if debug_harness_2: print("-- Round ownership before update:",ownership_overwrite)
                filtered_df.loc[index, 'Round Ownership'] = ownership_overwrite # Update in filtered df
                row['Round Ownership'] = ownership_overwrite # update in the row for subsequent calcs
                if debug_harness_2 : print("-- Round ownership after update:",filtered_df.loc[index, 'Round Ownership'])
  
            # Check: My Ownership == Invested / Post Money
            if (pd.notna(row["Invested"]) and pd.notna(row["Post Money"]) and row["Post Money"] > 0):
                ownership_overwrite = row["Invested"] / row["Post Money"]
                filtered_df.loc[index, 'My Ownership'] = ownership_overwrite # Update in filtered df
                if debug_harness_2 : print("-- My ownership:",ownership_overwrite)
            # else: # Default set to zero (should already be)
            #     filtered_df.loc[index, 'My Ownership'] = 0.0

        # Update all the Increase(round/round) now so that the other calculations have the correct data.
        if debug_harness_2: print("Calculating Increase (round/round) and round/round increase")
        
        # If it has adjustment as the last value in the data set then ignore this (and use that value)
        for index, row in filtered_df.iterrows():
            round_number = int(row["Round #"])

            if debug_harness_2 : print("-Round:",round_number)
            # Check: Increase (round/round) accuracy = Post Money (this) / Post Money (previous)
            if round_number > 1: # only run on the ones that have a previous round
                # Get the previous row based on Round # for this name from the original df
                previous_row = df.loc[(df["Round #"] == round_number - 1) & (df["Name"] == name)].squeeze()
                if pd.notna(previous_row["Post Money"]) and pd.notna(row["Post Money"]) and previous_row["Post Money"] > 0:  # Check if the previous row has Post Money
                    calculated_increase = row["Post Money"] / previous_row["Post Money"]
                    filtered_df.loc[index, 'Increase (round/round)'] = calculated_increase # Update in filtered df
                    row['Increase (round/round)'] = calculated_increase # update in the row for subsequent calcs']
                    if debug_harness_2: print("-- Increase round/round:",calculated_increase)
                # Also calculate round/round increase 
                # The special case is where Adjustment = Y in which case we accept the current Dilution Est as the overall total but we then set the value for this row such that the effects of this and the previous row match
                if pd.notna(row["Increase (round/round)"]) and pd.notna(row["Round Ownership"]) :
                    round_dilution = 1 - row['Round Ownership'] 
                    increase_round = row["Increase (round/round)"]
                    if row['Round Name'] != 'Adjustment':
                        final_dilution = increase_round * round_dilution
                        filtered_df.loc[index, 'Dilution (est)'] = final_dilution # Update in filtered df
                        row['Dilution (est)'] = final_dilution # update in the row for subsequent calcs']
                    else :
                        # Get all previous rows for this company but exclude Round = 1
                        previous_rows = filtered_df.loc[(filtered_df["Round #"] < round_number) & (filtered_df["Name"] == name) & (filtered_df["Round #"] != 1)]
                        # Calculate the product of previous dilutions (excluding NaN values)
                        previous_dilution_product = 1.0
                        for prev_index, prev_row in previous_rows.iterrows():
                            if pd.notna(prev_row["Dilution (est)"]):
                                previous_dilution_product *= prev_row["Dilution (est)"]
                                if debug_harness_2 : print("---previous dilution product", previous_dilution_product)
                        # Update the current row with the calculated product
                        final_dilution = row['Dilution (est)']/previous_dilution_product
                        filtered_df.loc[index, "Dilution (est)"] = final_dilution
                        row['Dilution (est)'] = final_dilution

                    if debug_harness_2: print("-- Dilution (final):",final_dilution," with round dilution:",round_dilution, " and increase round:",increase_round)                
 
        if debug_harness: print("All filtered DFs",all_filtered_dfs)
        # Use pd.concat to add this filtered_df to the dataframe
        all_filtered_dfs = pd.concat([all_filtered_dfs, filtered_df], ignore_index=True)

    if debug_harness : print("All filtered DF at the end was:", all_filtered_dfs)
    # Concatenate all the filtered_df's together into one.
    # Now don't check if empty as they might all be empty
    if all_filtered_dfs.empty == False :
        updated_df = all_filtered_dfs
        # Overwrite the old df values with the new ones.
        # Do an inner join to ensure that the index are all set correctly
        if debug_harness : print("Updated DF",updated_df)
        merged_df = pd.merge(original_df, updated_df, on=['Name', 'Round #'], how='left', suffixes=('', '_updated'))
        
        if show_changes == "Highlight Changes":
        # --- Show the dataframe with colour coded changes
            merged_df_display = merged_df.copy()
            # Drop the specified columns BEFORE displaying
            cols_to_drop = ["Date", "Notes", "Round Name_updated", "Estimated_updated", "Invested_updated", "Date_updated", "Notes_updated"]
            cols_to_drop_in_df = [col for col in cols_to_drop if col in merged_df_display.columns]
            merged_df_display.drop(columns=cols_to_drop_in_df, inplace=True)
            # Apply the highlighting
            merged_df_styled = merged_df_display.style.apply(highlight_diff, axis=1)
            # Display the styled DataFrame
            st.write("Changes highlighted below: green is new, orange is old/overwritten")
            st.dataframe(merged_df_styled, hide_index=True)

        elif show_changes == "Show Changes Summary" :
            # --- Capture and display the changes by company ---
            changes_by_company = {}
            for index, row in merged_df.iterrows():
                company_name = row["Name"]
                round_number = row["Round #"]
                if company_name not in changes_by_company:
                    changes_by_company[company_name] = {}
                row_changes = []

                for col in ['Premoney', 'Post Money', 'Round Ownership', 'My Ownership', 'Increase (round/round)', 'Dilution (est)']:
                    old_val = row[col]
                    new_val = row.get(f"{col}_updated", pd.NA)

                    if not pd.isna(new_val) and old_val != new_val:
                        if pd.notna(old_val) and old_val != 0 and pd.notna(new_val):
                            diff_percent = ((new_val - old_val) / old_val) * 100
                            if abs(diff_percent) < 0.2 :
                                row_changes.append(f"{col}: {old_val:.4f} --> {new_val:.4f} ({diff_percent:.2f}%)")
                            else :
                                row_changes.append(f"{col}: {old_val} --> {new_val} ({diff_percent:.2f}%)")
                        else:
                            row_changes.append(f"{col}: {old_val} --> {new_val}")

                if row_changes:
                    changes_by_company[company_name][round_number] = "; ".join(row_changes)

            if changes_by_company:
                st.write("Summary of changes by Company:")
                for company, round_data in changes_by_company.items():
                    st.write(f"**{company}**")
                    for round_num, changes in round_data.items():
                        st.write(f"  Round #{round_num}: {changes}")


        # Update the relevant columns from _updated columns but also make a list of the changes that can be simply displayed on the screen but of only those values that have been changed
        for col in ['Premoney', 'Post Money', 'Round Ownership', 'My Ownership', 'Increase (round/round)', 'Dilution (est)']:
            if f'{col}_updated' in merged_df.columns:
                merged_df[col] = merged_df[f'{col}_updated'].combine_first(merged_df[col])

        # Drop the extra columns - now everything is updated
        merged_df.drop(columns=[col for col in merged_df.columns if col.endswith('_updated')], inplace=True)
        # Assign the result back to df
        result = merged_df 
        if debug_harness : print("All filtered DF was not empty result was:", result)

    else :
        result = df.copy()
        if debug_harness : print("All filtered DF was empty result was:", result)
    
    if debug_harness : print("Exiting update_calculated_columns")
    return result

def calculate_increase_value(original_df):
    """Calculates the 'Increase (Value)' column based on dilution and invested amounts."""
    if debug_harness : print("Entered calculate_increase_value")
    df = original_df.copy()  # Create a copy to avoid modifying the original DataFrame
    df["Increase (Value)"] = 0.0  # Initialize the column with 0.0
    # st.subheader("Debugging: calculate_increase_value")
    # Group data by 'Name'
    for name, group in df.groupby('Name'):
        # Process each group (company) separately
        for i in range(len(group)):
            invested = group.iloc[i]["Invested"]  # Access 'Invested' from group
            if invested > 0:
                dilution_multiplier = 1.0
                for j in range(i + 1, len(group)): # j in the range of the size of the group
                    if pd.notna(group.iloc[j]["Dilution (est)"]) : # Check if a non zero number, if so ignore
                        dilution_multiplier *= group.iloc[j]["Dilution (est)"]  # Access 'Dilution (est)' from group
                final_increase_value = invested * dilution_multiplier
                # Update the 'Increase (Value)' column in the original DataFrame
                # Get the index of the row in the original dataframe
                original_index = group.iloc[i].name
                df.loc[original_index, "Increase (Value)"] = final_increase_value
    if debug_harness : print("Exiting calculate_increase_value")
    return df
