import pandas as pd
import sqlite3
import streamlit as st

# Title of the Streamlit app
st.title("Product Finder App")

# Example displayed on the website to explain model number input
st.write("## Examples of Model Number Format:")

col1, col2 = st.columns(2)

with col1:
    st.write("### Schoek Example:")
    st.write("T-K-M9-VV1-REI120-CV35-X80-H200-L1000-6.2")

with col2:
    st.write("### Halfen/Leviat Example:")
    st.write("HIT_SP-MVX-1407-16-100-35")

# Path to the SQLite database
db_path = r"masterfile.db"

# Function to load data from the SQLite database
def load_data_from_db(table_name):
    conn = sqlite3.connect(db_path)
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Load the tables into DataFrames
df_Schoeck_T = load_data_from_db("updated_Isokorb_T_full_columns")
df_Schoeck_XT = load_data_from_db("updated_Isokorb_XT_full_columns")
df_Leviat_HP = load_data_from_db("final_file_extended_columns_HIT_HP")
df_Leviat_SP = load_data_from_db("final_file_extended_columns_HIT_SP")

# Load the product mapping table
product_mapping = load_data_from_db("product_mapping")

# Function to preprocess Leviat data
def preprocess_leviat_data(df):
    df['mRd'] = df['mRd_minus'].astype(str).str.replace(',', '.').str.replace('-', '0').astype(float)
    df['vRd'] = df['vRd_plus'].astype(str).str.replace(',', '.').str.replace('-', '0').astype(float)
    df = df[['mRd', 'vRd', 'mrd_type', 'vrd_type', 'product_name', 'hh', 'Thickness']]
    return df

# Preprocess Leviat data
df_Leviat_HP = preprocess_leviat_data(df_Leviat_HP)
df_Leviat_SP = preprocess_leviat_data(df_Leviat_SP)
df_Leviat = pd.concat([df_Leviat_HP, df_Leviat_SP], ignore_index=True)

# Function to preprocess Schoeck data
def preprocess_schoeck_data(df):
    df['mRd'] = df['mRd'].astype(str).str.replace(',', '.').str.replace('±', '').str.replace('-', '0').astype(float)
    df['vRd'] = df['vRd'].astype(str).str.replace(',', '.').str.replace('±', '').str.replace('-', '0').astype(float)
    df = df[['mRd', 'vRd', 'product_name', 'Height', 'Thickness']]
    return df

# Preprocess Schoeck data
df_Schoeck_T = preprocess_schoeck_data(df_Schoeck_T)
df_Schoeck_XT = preprocess_schoeck_data(df_Schoeck_XT)
df_Schoeck = pd.concat([df_Schoeck_T, df_Schoeck_XT], ignore_index=True)

# Function to fetch specifications by model number
def fetch_specs_by_model(df, product_name):
    specific_product = df[df['product_name'] == product_name]
    if specific_product.empty:
        st.write(f"No such product found in the Database for {product_name}.")
        return None, None, None
    mrd_value = specific_product['mRd'].values[0]
    vrd_value = specific_product['vRd'].values[0]
    height_value = specific_product['Height'].values[0] if 'Height' in specific_product.columns else specific_product['hh'].values[0]
    thickness_value = specific_product['Thickness'].values[0]
    return mrd_value, vrd_value, height_value, thickness_value

# Function to fetch alternative products based on the specifications and thickness mapping
def fetch_alternative_products(df_schoeck, df_leviat, mrd_value, vrd_value, height_value, thickness_value, mrd_min, mrd_max, vrd_min, vrd_max, height_min, height_max):
    # Map the thickness to the product type
    if thickness_value in product_mapping['Schöck'].values:
        mapped_thickness = product_mapping[product_mapping['Schöck'] == thickness_value]['Leviat'].values[0]
        df_schoeck_filtered = df_schoeck[(df_schoeck['Thickness'] == thickness_value)]
        df_leviat_filtered = df_leviat[(df_leviat['Thickness'] == mapped_thickness)]
    elif thickness_value in product_mapping['Leviat'].values:
        mapped_thickness = product_mapping[product_mapping['Leviat'] == thickness_value]['Schöck'].values[0]
        df_schoeck_filtered = df_schoeck[(df_schoeck['Thickness'] == mapped_thickness)]
        df_leviat_filtered = df_leviat[(df_leviat['Thickness'] == thickness_value)]
    else:
        st.write("No mapping found for the product's thickness.")
        return pd.DataFrame(), pd.DataFrame()
    
    df_schoeck_filtered = df_schoeck_filtered[
        (df_schoeck_filtered['mRd'] >= mrd_min) & (df_schoeck_filtered['mRd'] <= mrd_max) &
        (df_schoeck_filtered['vRd'] >= vrd_min) & (df_schoeck_filtered['vRd'] <= vrd_max) &
        (df_schoeck_filtered['Height'].between(height_min, height_max))
    ]

    df_leviat_filtered = df_leviat_filtered[
        (df_leviat_filtered['mRd'] >= mrd_min) & (df_leviat_filtered['mRd'] <= mrd_max) &
        (df_leviat_filtered['vRd'] >= vrd_min) & (df_leviat_filtered['vRd'] <= vrd_max) &
        (df_leviat_filtered['hh'].between(height_min, height_max))
    ]

    return df_schoeck_filtered, df_leviat_filtered

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
        mrd_value_schoeck, vrd_value_schoeck, height_value_schoeck, thickness_value_schoeck = fetch_specs_by_model(df_Schoeck, product_name)
        mrd_value_leviat, vrd_value_leviat, height_value_leviat, thickness_value_leviat = fetch_specs_by_model(df_Leviat, product_name)
        
        if mrd_value_schoeck is not None and vrd_value_schoeck is not None and height_value_schoeck is not None:
            # Search for alternatives in both databases using Schoeck specs
            alternative_products_schoeck, alternative_products_leviat = fetch_alternative_products(
                df_Schoeck, df_Leviat, mrd_value_schoeck, vrd_value_schoeck, height_value_schoeck, thickness_value_schoeck,
                mrd_value_schoeck * mrd_lower_bound, mrd_value_schoeck * mrd_upper_bound,
                vrd_value_schoeck * vrd_lower_bound, vrd_value_schoeck * vrd_upper_bound,
                height_value_schoeck - height_offset, height_value_schoeck + height_offset)
            
            if not alternative_products_schoeck.empty:
                alternative_products_schoeck = format_dataframe(alternative_products_schoeck)
                specific_product_schoeck = df_Schoeck[df_Schoeck['product_name'] == product_name]

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
            alternative_products_schoeck, alternative_products_leviat = fetch_alternative_products(
                df_Schoeck, df_Leviat, mrd_value_leviat, vrd_value_leviat, height_value_leviat, thickness_value_leviat,
                mrd_value_leviat * mrd_lower_bound, mrd_value_leviat * mrd_upper_bound,
                vrd_value_leviat * vrd_lower_bound, vrd_value_leviat * vrd_upper_bound,
                height_value_leviat - height_offset, height_value_leviat + height_offset)
            
            if not alternative_products_schoeck.empty:
                alternative_products_schoeck = format_dataframe(alternative_products_schoeck)

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
    mrd_value = st.number_input("Input mRd value:", format="%.2f")
    vrd_value = st.number_input("Input vRd value:", format="%.2f")
    height_value = st.number_input("Input Height value (in intervals of 10):", step=10, format="%d")
    
    if mrd_value != 0.00 and vrd_value != 0.00:
        alternative_products_schoeck, additional_products_leviat = fetch_alternative_products(
            df_Schoeck, df_Leviat, mrd_value, vrd_value, height_value, None,
            mrd_value * mrd_lower_bound, mrd_value * mrd_upper_bound,
            vrd_value * vrd_lower_bound, vrd_value * vrd_upper_bound,
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
