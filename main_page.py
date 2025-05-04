import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os



category_file = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorised": [],
    }
    
if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)
        
def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

def categorise_transactions(df):
    df["Category"] = "Uncategorised"
    
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorised" or not keywords:
            continue
        
        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        
        for idx, row in df.iterrows():
            description = row["Description"].lower().strip()
            if description in lowered_keywords:
                df.at[idx, "Category"] = category
                
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
        df = df.astype({col: str for col in df.select_dtypes(include='object').columns})
        print("read the file")
        df.columns = [col.strip() for col in df.columns]
        #df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        df["Credit/Debit"] = df["Type"].map(type_to_debit_credit)
        #df["Completed Date"] = pd.to_datetime(df["Completed Date"], format="%d %b %Y") 
        
        return categorise_transactions(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    
    return False

def main():
    st.title("Simple Finance Dashboard")
    
    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["xlsx"])
    
    if uploaded_file is not None:
        df = load_transactions(uploaded_file)
        
        if df is not None:
            debits_df = df[df["Credit/Debit"] == "Debit"].copy()
            credits_df = df[df["Credit/Debit"] == "Credit"].copy()
            
            st.session_state.debits_df = debits_df.copy()
            
            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])
            with tab1:
                new_category = st.text_input("New Category Name")
                add_button = st.button("Add Category")
                
                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()
                
                st.subheader("Your Expenses")


                col1, col2, col3 = st.columns(3)

                # Adding feature to filter by date range
                with col1:
                    min_data = pd.to_datetime(debits_df["Completed Date"]).min()
                    max_data = pd.to_datetime(debits_df["Completed Date"]).max()
                    
                    date_range = st.date_input(
                        "Date Range",
                        value=(min_data, max_data),
                        min_value=min_data,
                        max_value=max_data
                    )


                with col2:

                    all_categories = ["All"] + sorted(debits_df["Category"].unique().tolist())
                    selected_categories = st.multiselect(
                        "Select Categories",
                        options=all_categories,
                        default="All"
                    )

                    if "All" in selected_categories or not selected_categories:
                        selected_categories = all_categories[1:] # exclude "All" as it is added to the all_categories list

                search_term = st.text_input("Search Description")

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

            with tab2:
                st.subheader("Payments Summary")
                total_payments = credits_df["Amount"].sum()
                st.metric("Total Payments", f"{total_payments:,.2f} GBP")
                st.write(credits_df)
        
main()
