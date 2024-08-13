
import pandas as pd
import streamlit as st
import sqlite3

# Display logo and author names
st.image("Logos.png", use_column_width=True)
st.write("### Gabriel D. Guerra and Nikita G. Meshin")
st.title("Product Finder App")

# Example model numbers
st.write("## Examples of Model Number Format:")

col1, col2 = st.columns(2)

with col1:
    st.write("### Schöck Example:")
    st.write("T-K-M9-VV1-REI120-CV35-X80-H200-6.2")

with col2:
    st.write("### Halfen/Leviat Example:")
    st.write("HIT_SP-MVX-1407-16-100-35")

# Load data from SQLite database
db_path = "masterfile.db"

def load_data(query):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

df_Schoeck = load_data("SELECT * FROM updated_Isokorb_T_full_columns")
df_XT = load_data("SELECT * FROM updated_Isokorb_XT_full_columns")
df_Schoeck = pd.concat([df_Schoeck, df_XT], ignore_index=True)

df_Leviat_HP = load_data("SELECT * FROM final_file_extended_columns_HIT_HP")
df_Leviat_SP = load_data("SELECT * FROM final_file_extended_columns_HIT_SP")
df_Leviat = pd.concat([df_Leviat_HP, df_Leviat_SP], ignore_index=True)

# Preprocessing functions
def preprocess_additional_file(df_Leviat):
    filtered_df = df_Leviat[df_Leviat['c'] == "25/30"].copy()
    filtered_df['mRd_minus'] = filtered_df['mRd_minus'].astype(str).str.replace(',', '.').str.replace('-', '').astype(float)
    filtered_df['vRd_plus'] = filtered_df['vRd_plus'].astype(str).str.replace(',', '.').str.replace('-', '').astype(float)
    return filtered_df

def preprocess_schoeck_file(df_Schoeck):
    df_Schoeck['mRd'] = df_Schoeck['mRd'].astype(str).str.replace(',', '.').str.replace('±', '').str.replace('-', '0').astype(float)
    df_Schoeck['vRd'] = df_Schoeck['vRd'].astype(str).str.replace(',', '.').str.replace('±', '').str.replace('-', '0').astype(float)
    return df_Schoeck

df_Schoeck = preprocess_schoeck_file(df_Schoeck)

# Functions to fetch specifications by model number
def fetch_specs_by_model_schoeck(df_Schoeck, product_name):
    specific_product = df_Schoeck[df_Schoeck['product_name'] == product_name]
    if specific_product.empty:
        return None, None, None
    mrd_value = specific_product['mRd'].values[0]
    vrd_value = specific_product['vRd'].values[0]
    height_value = int(product_name.split('-')[7][1:])  # Extract height from model number
    return mrd_value, vrd_value, height_value

def fetch_specs_by_model_leviat(df_Leviat, encoded_value):
    preprocessed_df = preprocess_additional_file(df_Leviat)
    specific_products = preprocessed_df[preprocessed_df['product_name'] == encoded_value]
    if specific_products.empty:
        return None, None, None, None, None
    mrd_values = specific_products['mRd_minus'].values
    vrd_values = specific_products['vRd_plus'].values
    height_value = specific_products['hh'].values[0]
    mrd_types = specific_products['mrd_type'].values
    vrd_types = specific_products['vrd_type'].values
    return mrd_values, vrd_values, height_value, mrd_types, vrd_types

# Functions to fetch alternative products by specifications
def fetch_alternative_products_by_specs(df_Schoeck, df_Leviat, mrd_value, vrd_value, height_value, mrd_min, mrd_max, vrd_min, vrd_max):
    df_Schoeck['Height'] = pd.to_numeric(df_Schoeck['product_name'].str.extract(r'H(\d+)')[0], errors='coerce')
    df_Schoeck_filtered = df_Schoeck[
        (df_Schoeck['mRd'] >= mrd_min) & (df_Schoeck['mRd'] <= mrd_max) &
        (df_Schoeck['vRd'] >= vrd_min) & (df_Schoeck['vRd'] <= vrd_max) &
        (df_Schoeck['Height'] == height_value)
    ][['product_name', 'mRd', 'vRd', 'Height']]

    preprocessed_df_leviat = preprocess_additional_file(df_Leviat)
    df_Leviat_filtered = preprocessed_df_leviat[
        (preprocessed_df_leviat['mRd_minus'] >= mrd_min) & (preprocessed_df_leviat['mRd_minus'] <= mrd_max) &
        (preprocessed_df_leviat['vRd_plus'] >= vrd_min) & (preprocessed_df_leviat['vRd_plus'] <= vrd_max) &
        (preprocessed_df_leviat['hh'] == height_value)
    ][['product_name', 'mRd_minus', 'vRd_plus', 'hh', 'mrd_type', 'vrd_type']]

    return df_Schoeck_filtered, df_Leviat_filtered

def format_dataframe(df):
    if not df.empty:
        df.loc[:, df.select_dtypes(include=['float']).columns] = df.select_dtypes(include=['float']).apply(lambda x: x.astype(float).map('{:.2f}'.format))
    return df

# User input and search ranges
input_type = st.selectbox("Choose input type:", ["Model Number", "Specifications"])

st.write("### Set Search Ranges:")
col_mrd, col_vrd = st.columns(2)

with col_mrd:
    mrd_lower_bound = st.number_input("MRD Lower Bound", min_value=0.0, value=0.99, step=0.01, format="%.2f")
    mrd_upper_bound = st.number_input("MRD Upper Bound", min_value=0.0, value=1.03, step=0.01, format="%.2f")

with col_vrd:
    vrd_lower_bound = st.number_input("VRD Lower Bound", min_value=0.0, value=0.99, step=0.01, format="%.2f")
    vrd_upper_bound = st.number_input("VRD Upper Bound", min_value=0.0, value=1.03, step=0.01, format="%.2f")

# Conditional display of input boxes and fetch results
if input_type == "Model Number":
    product_name = st.text_input("Input Model Number:")
    
    if product_name:
        mrd_value_schoeck, vrd_value_schoeck, height_value_schoeck = fetch_specs_by_model_schoeck(df_Schoeck, product_name)
        mrd_values_leviat, vrd_values_leviat, height_value_leviat, mrd_types_leviat, vrd_types_leviat = fetch_specs_by_model_leviat(df_Leviat, product_name)
        
        st.write("## Your Alternative Products:")
        
        if mrd_value_schoeck is not None and vrd_value_schoeck is not None and height_value_schoeck is not None:
            specific_product_schoeck = df_Schoeck[df_Schoeck['product_name'] == product_name]
            alternative_products_schoeck, alternative_products_leviat = fetch_alternative_products_by_specs(
                df_Schoeck, df_Leviat, mrd_value_schoeck, vrd_value_schoeck, height_value_schoeck,
                mrd_value_schoeck * mrd_lower_bound, mrd_value_schoeck * mrd_upper_bound,
                vrd_value_schoeck * vrd_lower_bound, vrd_value_schoeck * vrd_upper_bound)
            
            if not alternative_products_schoeck.empty:
                alternative_products_schoeck = format_dataframe(alternative_products_schoeck)
                specific_product_schoeck = format_dataframe(specific_product_schoeck[['product_name', 'mRd', 'vRd', 'Height']])

                def highlight_product_schoeck(row):
                    if row['product_name'] == product_name:
                        return ['background-color: yellow'] * len(row)
                    else:
                        return [''] * len(row)
                
                st.write("From Schöck's Database:")
                st.write(alternative_products_schoeck.style.apply(highlight_product_schoeck, axis=1))
            else:
                st.write("No alternative products found in Schöck's files.")
            
            if not alternative_products_leviat.empty:
                alternative_products_leviat = format_dataframe(alternative_products_leviat)

                def highlight_product_leviat(row):
                    if row['product_name'] == product_name:
                        return ['background-color: yellow'] * len(row)
                    else:
                        return [''] * len(row)
                
                st.write("From Leviat's Database:")
                st.write(alternative_products_leviat.style.apply(highlight_product_leviat, axis=1))
            else:
                st.write("No alternative products found in Leviat's files.")
        
        if mrd_values_leviat is not None and vrd_values_leviat is not None and height_value_leviat is not None:
            for mrd_value, vrd_value, mrd_type, vrd_type in zip(mrd_values_leviat, vrd_values_leviat, mrd_types_leviat, vrd_types_leviat):
                alternative_products_schoeck, alternative_products_leviat = fetch_alternative_products_by_specs(
                    df_Schoeck, df_Leviat, mrd_value, vrd_value, height_value_leviat,
                    mrd_value * mrd_lower_bound, mrd_value * mrd_upper_bound,
                    vrd_value * vrd_lower_bound, vrd_value * vrd_upper_bound)
                
                if not alternative_products_schoeck.empty:
                    alternative_products_schoeck = format_dataframe(alternative_products_schoeck[['product_name', 'mRd', 'vRd', 'Height']])

                    def highlight_product_schoeck(row):
                        if row['product_name'] == product_name:
                            return ['background-color: yellow'] * len(row)
                        else:
                            return [''] * len(row)
                    
                    st.write("From Schöck's Database:")
                    st.write(alternative_products_schoeck.style.apply(highlight_product_schoeck, axis=1))
                else:
                    st.write("No alternative products found in Schöck's files.")
                
                if not alternative_products_leviat.empty:
                    alternative_products_leviat = format_dataframe(alternative_products_leviat[['product_name', 'mRd_minus', 'vRd_plus', 'hh', 'mrd_type', 'vrd_type']])

                    def highlight_product_leviat(row):
                        if row['product_name'] == product_name:
                            return ['background-color: yellow'] * len(row)
                        else:
                            return [''] * len(row)
                    
                    st.write("From Leviat's Database:")
                    st.write(alternative_products_leviat.style.apply(highlight_product_leviat, axis=1))
                else:
                    st.write("No alternative products found in Leviat's files.")
else:
    mRd_value = st.number_input("Input mRd value:", format="%.2f")
    vRd_value = st.number_input("Input vRd value:", format="%.2f")
    height_value = st.number_input("Input Height value (in intervals of 10):", step=10, format="%d")
    
    if mRd_value != 0.00 and vRd_value != 0.00:
        alternative_products_schoeck, additional_products_leviat = fetch_alternative_products_by_specs(
            df_Schoeck, df_Leviat, mRd_value, vRd_value, height_value,
            mRd_value * mrd_lower_bound, mRd_value * mrd_upper_bound,
            vRd_value * vrd_lower_bound, vRd_value * vrd_upper_bound)
        
        st.write("## Your Alternative Products:")
        
        if not alternative_products_schoeck.empty:
            alternative_products_schoeck = format_dataframe(alternative_products_schoeck[['product_name', 'mRd', 'vRd', 'Height']])
            st.write("From Schöck's Database:")
            st.write(alternative_products_schoeck)
        else:
            st.write("No alternative products found in Schöck's files.")
        
        if not additional_products_leviat.empty:
            additional_products_leviat = format_dataframe(additional_products_leviat[['product_name', 'mRd_minus', 'vRd_plus', 'hh', 'mrd_type', 'vrd_type']])
            st.write("From Leviat's Database:")
            st.write(additional_products_leviat)
        else:
            st.write("No alternative products found in Leviat's files.")

# Explanation of methods
st.write("## There are two ways to use this app:")

col1, col2 = st.columns(2)

with col1:
    st.write("### Method 1:")
    st.write("You input the exact model number of a model off of the company's website and the app will give you the existing alternative models to compare to the one you input.")

with col2:
    st.write("### Method 2:")
    st.write("You can input the required moment and shear load resistances along with the total height needed for your project and get the exact model configuration you require. The output product heights are +-20mm of your input, in case the exact specifications you would prefer are not available.")



