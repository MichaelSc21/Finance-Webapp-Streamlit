import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from src.login import auth_manager, db_manager
from src.logger import logger


category_file = "app/src/pages/categories.json"


if 'user' in st.session_state:
    # Load user's categories from the DB
    st.session_state.categories = db_manager.get_user_categories(st.session_state.user['google_id'])
    logger.info("Saved the categories field to st.session_state")
else:
    st.session_state.categories = {"Uncategorised": []}


        
def save_categories():
    if "user" in st.session_state:
        db_manager.save_user_categories(st.session_state.user['google_id'], st.session_state.categories)
        logger.info("Saved user categories to DB")


def categorise_transactions(df):
    """Categorise transactions using the current category mapping"""
    # Iterating through the categories and keywords, and mapping categories found in the mapping to the associated keywords, on the df

    df["Category"] = "Uncategorised"
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorised" or not keywords:
            continue
        
        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        
        for idx, row in df.iterrows():
            description = row["Description"].lower().strip()
            if description in lowered_keywords:
                df.at[idx, "Category"] = category

    logger.info("Categorised transactions on the st.session_state.df")
    return df  

type_to_debit_credit = {
    "CARD_PAYMENT": "Debit",
    "ATM": "Debit",
    "EXCHANGE": "Debit",  # depends, might need special handling
    "TRANSFER": "Credit",
    "TOPUP": "Credit",
    "CARD_REFUND": "Credit",
    "REWARD": "Credit"
}


def load_transactions(file):
    try:
        df = pd.read_excel(file)
        # Changing columns from object type to string
        df = df.astype({col: str for col in df.select_dtypes(include='object').columns})
        print("read the excel file")
        df.columns = [col.strip() for col in df.columns]
        df["Credit/Debit"] = df["Type"].map(type_to_debit_credit)
        #df["Completed Date"] = pd.to_datetime(df["Completed Date"], format="%d %b %Y") 
        
        # Mapping the categories on the df, with the associated keywords
        # (Check the categorise_transactions function for more detail)
        return categorise_transactions(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def add_keyword_to_category(category, keyword):
    """Add a keyword to category and save to database"""

    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories.get(category, []):

        # Making a list for the category and appending the new keyword, otherwise append the keyword to the existing list for that category
        if keyword and keyword not in st.session_state.categories:
            st.session_state.categories[category] = []
        st.session_state.categories[category].append(keyword)

        if 'user' in st.session_state:
            db_manager.add_category_keyword(
                st.session_state.user['google_id'],
                category,
                keyword
            )
        return True
    
    return False

def main():
    st.title("Simple Finance Dashboard")
    

    if 'user' in st.session_state:
        st.sidebar.success(f"Logged in as: {st.session_state.user['name']}")
    else:
        st.sidebar.warning("Not logged in - categories won't be saved 🙃")

    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["xlsx"])
    st.session_state.uploaded_file_bool = True


    if uploaded_file is not None:
        df = load_transactions(uploaded_file)
        
        if df is not None:
            debits_df = df[df["Credit/Debit"] == "Debit"].copy()
            credits_df = df[df["Credit/Debit"] == "Credit"].copy()
            
            st.session_state.debits_df = debits_df.copy()
            
            tab1, tab2, tab3 = st.tabs(["Expenses (Debits)", "Payments (Credits)", "Expenses over time"])

            with tab1:
                # Category management section
                col1, col2 = st.columns(2)
                with col1:
                    new_category = st.text_input("New Category Name")
                with col2:
                    st.write("") # For alignment 
                    add_button = st.button("Add Category")
                
                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()
                

                st.subheader("Your Expenses")
                # Filters
                col1, col2, col3 = st.columns(3)


                # Filtering date ranges
                with col1:
                    min_data = pd.to_datetime(debits_df["Completed Date"]).min()
                    max_data = pd.to_datetime(debits_df["Completed Date"]).max()
                    
                    date_range = st.date_input(
                        "Date Range",
                        value=(min_data, max_data),
                        min_value=min_data,
                        max_value=max_data
                    )


                # Filtering categories
                with col2:
                    all_categories = ["All"] + sorted(debits_df["Category"].unique().tolist())
                    selected_categories = st.multiselect(
                        "Select Categories",
                        options=all_categories,
                        default="All"
                    )

                    if "All" in selected_categories or not selected_categories:
                        selected_categories = all_categories[1:] # exclude "All" as it is added to the all_categories list
                with col3:
                    search_term = st.text_input("Search Description")


                # Filtering df based on the criteria
                filtered_df = debits_df.copy()

                # Filering df based on the selected date range
                if len(date_range) == 2:
                    start_date, end_date = date_range
                    filtered_df = filtered_df[
                        (pd.to_datetime(filtered_df["Completed Date"]) >= pd.to_datetime(start_date)) &
                        (pd.to_datetime(filtered_df["Completed Date"]) <= pd.to_datetime(end_date))
                    ]

                # Filtering df based on the selected cateogires
                filtered_df = filtered_df[filtered_df["Category"].isin(selected_categories)]

                # Filtering df descriptions based on the search term
                if search_term:
                    filtered_df = filtered_df[
                        filtered_df["Description"].str.contains(search_term, case=False)
                    ]

                st.write(f"Showing {len(filtered_df)} of {len(debits_df)} transactions")


                edited_df = st.data_editor(
                    st.session_state.debits_df[["Completed Date", "Description", "Amount", "Category"]],
                    column_config={
                        "Completed Date": st.column_config.DateColumn("Completed Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f GBP"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )


                # Save button to apply changes                  
                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        if new_category == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                        
                        description = row["Description"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, description)
                    st.success("Categories Updated 😀")



            
                        
                st.subheader('Expense Summary')
                # Update summary to use filtered data
                category_totals = filtered_df.groupby("Category")["Amount"].sum().abs().reset_index()
                category_totals = category_totals.sort_values("Amount", ascending=False)
                
                st.dataframe(
                    category_totals, 
                    column_config={
                     "Amount": st.column_config.NumberColumn("Amount", format="%.2f GBP")   
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                st.metric("Total Filtered Expenses", f"{category_totals['Amount'].sum():,.2f} GBP")
                
                category_totals["Amount"] = pd.to_numeric(category_totals["Amount"], errors='coerce')
                fig = px.pie(
                    category_totals,
                    values="Amount",
                    names="Category",
                    title="Expenses by Category"
                )
                fig.update_layout(template="plotly_dark")
                fig.update_traces(
                    textfont=dict(color='black'),  # Dark text for labels
                    marker=dict(line=dict(color='#000000', width=1))  # Dark borders
                )

                st.plotly_chart(fig, use_container_width=True, theme="streamlit")

                st.session_state.credits_df = credits_df 

            with tab2:
                st.subheader("Payments Summary")
                total_payments = credits_df["Amount"].sum()
                st.metric("Total Payments", f"{total_payments:,.2f} GBP")
                st.write(credits_df)


main()
