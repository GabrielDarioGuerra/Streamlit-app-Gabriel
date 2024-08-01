import pandas as pd
import streamlit as st
import sqlite3

# Title of the Streamlit app
st.title("Product Finder App")

# Example displayed on the website to explain model number input
st.write("## Examples of Model Number Format:")

col1, col2 = st.columns(2)

with col1:
    st.write("### Schöck Example:")
    st.write("T-K-M9-VV1-REI120-CV35-X80-H200-6.2")

with col2:
    st.write("### Halfen/Leviat Example:")
    st.write("HIT_SP-MVX-1407-16-100-35")

# Path to the SQLite database
db_path = "masterfile.db"

# Function to load data from the SQLite database
def load_data(query):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Load the data from the database tables
df_Schoeck = load_data("SELECT * FROM updated_Isokorb_T_full_columns")
df_XT = load_data("SELECT * FROM updated_Isokorb_XT_full_columns")
df_Schoeck = pd.concat([df_Schoeck, df_XT], ignore_index=True)

df_Leviat_HP = load_data("SELECT * FROM final_file_extended_columns_HIT_HP")
df_Leviat_SP = load_data("SELECT * FROM final_file_extended_columns_HIT_SP")
df_Leviat = pd.concat([df_Leviat_HP, df_Leviat_SP], ignore_index=True)

# Load the product mapping table
product_mapping = load_data("SELECT * FROM product_mapping")

# Corrected preprocessing function for additional file
def preprocess_additional_file(df_Leviat):
    filtered_df = df_Leviat[df_Leviat['c'] == "25/30"].copy()
    filtered_df['mRd_minus'] = filtered_df['mRd_minus'].astype(str).str.replace(',', '.').str.replace('-', '')
    filtered_df['vRd_plus'] = filtered_df['vRd_plus'].astype(str).str.replace(',', '.').str.replace('-', '')
    filtered_df['mRd_minus'] = filtered_df['mRd_minus'].astype(float)
    filtered_df['vRd_plus'] = filtered_df['vRd_plus'].astype(float)
    filtered_df = filtered_df[['mRd_minus', 'vRd_plus', 'mrd_type', 'vrd_type', 'product_name', 'hh']]
    result_df = filtered_df.groupby('product_name').agg(
        MRD_Range=pd.NamedAgg(column='mRd_minus', aggfunc=lambda x: f"{x.min()}-{x.max()}"),
        VRD_Range=pd.NamedAgg(column='vRd_plus', aggfunc=lambda x: f"{x.min()}-{x.max()}"),
        Height=pd.NamedAgg(column='hh', aggfunc='first')
    ).reset_index()
    return result_df

# Preprocessing function for Schoeck data
def preprocess_schoeck_file(df_Schoeck):
    df_Schoeck['mRd'] = df_Schoeck['mRd'].astype(str).str.replace(',', '.').str.replace('±', '').str.replace('-', '0').astype(float)
    df_Schoeck['vRd'] = df_Schoeck['vRd'].astype(str).str.replace(',', '.').str.replace('±', '').str.replace('-', '0').astype(float)
    return df_Schoeck

# Apply preprocessing to the Schoeck dataframe
df_Schoeck = preprocess_schoeck_file(df_Schoeck)

# Function to fetch specifications by model number from Schoeck
def fetch_specs_by_model_schoeck(df_Schoeck, product_name):
    specific_product = df_Schoeck[df_Schoeck['product_name'] == product_name]
    if specific_product.empty:
        st.write("No such product found in the Schoeck's Database.")
        return None, None, None
    mrd_value = specific_product['mRd'].values[0]
    vrd_value = specific_product['vRd'].values[0]
    height_value = int(product_name.split('-')[7][1:])  # Extract height from model number
    return mrd_value, vrd_value, height_value

# Function to fetch specifications by model number from Leviat
def fetch_specs_by_model_leviat(df_Leviat, encoded_value):
    preprocessed_df = preprocess_additional_file(df_Leviat)
    specific_product = preprocessed_df[preprocessed_df['product_name'] == encoded_value]
    if specific_product.empty:
        return None, None, None
    mrd_value = specific_product['MRD_Range'].values[0].split('-')
    vrd_value = specific_product['VRD_Range'].values[0].split('-')
    height_value = specific_product['Height'].values[0]
    return float(mrd_value[0]), float(vrd_value[0]), height_value

# Function to fetch alternative products by specifications from combined dataframes (Schoeck and Leviat)
def fetch_alternative_products_by_specs(df_Schoeck, df_Leviat, mrd_value, vrd_value, height_value, mrd_min, mrd_max, vrd_min, vrd_max, height_min, height_max):
    # Ensure 'Height' column is numeric
    df_Schoeck['Height'] = pd.to_numeric(df_Schoeck['product_name'].str.extract(r'H(\d+)')[0], errors='coerce')
    df_Schoeck_filtered = df_Schoeck[
        (df_Schoeck['mRd'] >= mrd_min) & (df_Schoeck['mRd'] <= mrd_max) &
        (df_Schoeck['vRd'] >= vrd_min) & (df_Schoeck['vRd'] <= vrd_max) &
        (df_Schoeck['Height'].between(height_min, height_max))
    ][['product_name', 'mRd', 'vRd', 'Height']]  # Rearrange columns

    preprocessed_df_leviat = preprocess_additional_file(df_Leviat)
    preprocessed_df_leviat[['MRD_min', 'MRD_max']] = preprocessed_df_leviat['MRD_Range'].str.split('-', expand=True).astype(float)
    preprocessed_df_leviat[['VRD_min', 'VRD_max']] = preprocessed_df_leviat['VRD_Range'].str.split('-', expand=True).astype(float)
    df_Leviat_filtered = preprocessed_df_leviat[
        (preprocessed_df_leviat['MRD_min'] <= mrd_max) & (preprocessed_df_leviat['MRD_max'] >= mrd_min) &
        (preprocessed_df_leviat['VRD_min'] <= vrd_max) & (preprocessed_df_leviat['VRD_max'] >= vrd_min) &
        (preprocessed_df_leviat['Height'].between(height_min, height_max))
    ][['product_name', 'MRD_Range', 'VRD_Range', 'Height']]  # Selecting specific columns

    # Map product types using the product_mapping table
    df_Schoeck_filtered['Mapped_Product_Type'] = df_Schoeck_filtered['product_name'].apply(lambda x: product_mapping[product_mapping['Schöck'] == x.split('-')[0]]['Leviat'].values[0] if x.split('-')[0] in product_mapping['Schöck'].values else x.split('-')[0])
    df_Leviat_filtered['Mapped_Product_Type'] = df_Leviat_filtered['product_name'].apply(lambda x: product_mapping[product_mapping['Leviat'] == x.split('-')[0]]['Schöck'].values[0] if x.split('-')[0] in product_mapping['Leviat'].values else x.split('-')[0])

    return df_Schoeck_filtered, df_Leviat_filtered

# Function to format DataFrame columns
def format_dataframe(df):
    if not df.empty:
        df.loc[:, df.select_dtypes(include=['float']).columns] = df.select_dtypes(include=['float']).apply(lambda x: x.astype(float).map('{:.2f}'.format))
    return df

# Drop-down menu to choose input type
input_type = st.selectbox("Choose input type:", ["Model Number", "Specifications"])

# Input fields for search ranges
st.write("### Set Search Ranges:")
col_mrd, col_vrd, col_height = st.columns(3)

with col_mrd:
    mrd_lower_bound = st.number_input("MRD Lower Bound", min_value=0.0, value=0.99, step=0.01, format="%.2f")
    mrd_upper_bound = st.number_input("MRD Upper Bound", min_value=0.0, value=1.03, step=0.01, format="%.2f")

with col_vrd:
    vrd_lower_bound = st.number_input("VRD Lower Bound", min_value=0.0, value=0.99, step=0.01, format="%.2f")
    vrd_upper_bound = st.number_input("VRD Upper Bound", min_value=0.0, value=1.03, step=0.01, format="%.2f")

with col_height:
    height_offset = st.number_input("Height Offset", min_value=0, value=20, step=1)

# Conditional display of input boxes based on selection
if input_type == "Model Number":
    # Input box for model number
    product_name = st.text_input("Input Model Number:")
    
    if product_name:
        # Fetch specs from Schoeck and Leviat
        mrd_value_schoeck, vrd_value_schoeck, height_value_schoeck = fetch_specs_by_model_schoeck(df_Schoeck, product_name)
        mrd_value_leviat, vrd_value_leviat, height_value_leviat = fetch_specs_by_model_leviat(df_Leviat, product_name)
        
        if mrd_value_schoeck is not None and vrd_value_schoeck is not None and height_value_schoeck is not None:
            # Search for alternatives in both databases using Schoeck specs
            specific_product_schoeck = df_Schoeck[df_Schoeck['product_name'] == product_name]
            alternative_products_schoeck, alternative_products_leviat = fetch_alternative_products_by_specs(
                df_Schoeck, df_Leviat, mrd_value_schoeck, vrd_value_schoeck, height_value_schoeck,
                mrd_value_schoeck * mrd_lower_bound, mrd_value_schoeck * mrd_upper_bound,
                vrd_value_schoeck * vrd_lower_bound, vrd_value_schoeck * vrd_upper_bound,
                height_value_schoeck - height_offset, height_value_schoeck + height_offset)
            
            if not alternative_products_schoeck.empty:
                alternative_products_schoeck = format_dataframe(alternative_products_schoeck)
                specific_product_schoeck = format_dataframe(specific_product_schoeck[['product_name', 'mRd', 'vRd', 'Height']])

                def highlight_product_schoeck(row):
                    if row['product_name'] == product_name:
                        return ['background-color: yellow'] * len(row)
                    else:
                        return [''] * len(row)
                
                st.write("Your Alternative Products from Schoeck's Database:")
                st.write(alternative_products_schoeck.style.apply(highlight_product_schoeck, axis=1))
            else:
                st.write("No alternative products found in Schoeck's files.")
            
            if not alternative_products_leviat.empty:
                alternative_products_leviat = format_dataframe(alternative_products_leviat)

                def highlight_product_leviat(row):
                    if row['product_name'] == product_name:
                        return ['background-color: yellow'] * len(row)
                    else:
                        return [''] * len(row)
                    
                st.write("Your Alternative Products from Leviat's Database:")
                st.write(alternative_products_leviat.style.apply(highlight_product_leviat, axis=1))
        
        if mrd_value_leviat is not None and vrd_value_leviat is not None and height_value_leviat is not None:
            # Search for alternatives in both databases using Leviat specs
            specific_product_leviat = preprocess_additional_file(df_Leviat)[preprocess_additional_file(df_Leviat)['product_name'] == product_name]
            alternative_products_schoeck, alternative_products_leviat = fetch_alternative_products_by_specs(
                df_Schoeck, df_Leviat, mrd_value_leviat, vrd_value_leviat, height_value_leviat,
                mrd_value_leviat * mrd_lower_bound, mrd_value_leviat * mrd_upper_bound,
                vrd_value_leviat * vrd_lower_bound, vrd_value_leviat * vrd_upper_bound,
                height_value_leviat - height_offset, height_value_leviat + height_offset)
            
            if not alternative_products_schoeck.empty:
                alternative_products_schoeck = format_dataframe(alternative_products_schoeck[['product_name', 'mRd', 'vRd', 'Height']])

                def highlight_product_schoeck(row):
                    if row['product_name'] == product_name:
                        return ['background-color: yellow'] * len(row)
                    else:
                        return [''] * len(row)
                
                st.write("Your Alternative Products from Schoeck's Database:")
                st.write(alternative_products_schoeck.style.apply(highlight_product_schoeck, axis=1))
            else:
                st.write("No alternative products found in Schoeck's files.")
            
            if not alternative_products_leviat.empty:
                alternative_products_leviat = format_dataframe(alternative_products_leviat)

                def highlight_product_leviat(row):
                    if row['product_name'] == product_name:
                        return ['background-color: yellow'] * len(row)
                    else:
                        return [''] * len(row)
                    
                st.write("Your Alternative Products from Leviat's Database:")
                st.write(alternative_products_leviat.style.apply(highlight_product_leviat, axis=1))

else:
    # Input boxes for specifications
    mRd_value = st.number_input("Input mRd value:", format="%.2f")
    vRd_value = st.number_input("Input vRd value:", format="%.2f")
    height_value = st.number_input("Input Height value (in intervals of 10):", step=10, format="%d")
    
    if mRd_value != 0.00 and vRd_value != 0.00:
        alternative_products_schoeck, additional_products_leviat = fetch_alternative_products_by_specs(
            df_Schoeck, df_Leviat, mRd_value, vRd_value, height_value,
            mRd_value * mrd_lower_bound, mRd_value * mrd_upper_bound,
            vRd_value * vrd_lower_bound, vRd_value * vrd_upper_bound,
            height_value - height_offset, height_value + height_offset)
        
        if not alternative_products_schoeck.empty:
            alternative_products_schoeck = format_dataframe(alternative_products_schoeck[['product_name', 'mRd', 'vRd', 'Height']])
            st.write("Your Alternative Products from Schoeck's Database:")
            st.write(alternative_products_schoeck)
        else:
            st.write("No alternative products found in Schoeck's files.")
        
        if not additional_products_leviat.empty:
            additional_products_leviat = format_dataframe(additional_products_leviat)
            st.write("Additional Products from Leviat's Database:")
            st.write(additional_products_leviat)
        else:
            st.write("No additional products found in the Leviat's files.")

# Explanation of methods
st.write("## There are two ways to use this app:")

col1, col2 = st.columns(2)

with col1:
    st.write("### Method 1:")
    st.write("You input the exact model number of a model off of the company's website and the app will give you the existing alternative models to compare to the one you input.")

with col2:
    st.write("### Method 2:")
    st.write("You can input the required moment and shear load resistances along with the total height needed for your project and get the exact model configuration you require. The output product heights are +-20mm of your input, in case the exact specifications you would prefer are not available.")
