import pandas as pd
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

# Paths to the CSV files
csv_path_1 = r"Isokorb_T_Updated.csv"
csv_path_2 = r"Isokorb_XT_Updated.csv"
csv_path_Leviat_1 = r"HIT-HP_Updated.csv"
csv_path_Leviat_2 = r"HIT-SP_Updated.csv"

# Load the CSV files
df1 = pd.read_csv(csv_path_1)
df2 = pd.read_csv(csv_path_2)
df_Leviat_1 = pd.read_csv(csv_path_Leviat_1)
df_Leviat_2 = pd.read_csv(csv_path_Leviat_2)

# Exclude the first row from the second DataFrame and combine them
df2 = df2.iloc[1:].reset_index(drop=True)
df_Schoeck = pd.concat([df1, df2], ignore_index=True)

# Create Proper DataFrame for Leviat Products
df_Leviat_2 = df_Leviat_2.iloc[1:].reset_index(drop=True)
df_Leviat = pd.concat([df_Leviat_1, df_Leviat_2], ignore_index=True)

# Corrected preprocessing function for additional file
def preprocess_additional_file(df_Leviat):
    filtered_df = df_Leviat[df_Leviat['c'] == "25/30"].copy()
    filtered_df['mrd'] = filtered_df['mrd'].astype(str).str.replace(',', '.').str.replace('-', '')
    filtered_df['vrd'] = filtered_df['vrd'].astype(str).str.replace(',', '.').str.replace('-', '')
    filtered_df['mrd'] = filtered_df['mrd'].astype(float)
    filtered_df['vrd'] = filtered_df['vrd'].astype(float)
    filtered_df = filtered_df[['mrd', 'vrd', 'mrd_type', 'vrd_type', 'new_product_type', 'hh']]
    result_df = filtered_df.groupby('new_product_type').agg(
        MRD_Range=pd.NamedAgg(column='mrd', aggfunc=lambda x: f"{x.min()}-{x.max()}"),
        VRD_Range=pd.NamedAgg(column='vrd', aggfunc=lambda x: f"{x.min()}-{x.max()}"),
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
    specific_product = preprocessed_df[preprocessed_df['new_product_type'] == encoded_value]
    if specific_product.empty:
        return None, None, None
    mrd_value = specific_product['MRD_Range'].values[0].split('-')
    vrd_value = specific_product['VRD_Range'].values[0].split('-')
    height_value = specific_product['Height'].values[0]
    return float(mrd_value[0]), float(vrd_value[0]), height_value

# Function to fetch alternative products by specifications from combined CSVs (Schoeck and Leviat)
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
    ][['new_product_type', 'MRD_Range', 'VRD_Range', 'Height']]  # Selecting specific columns

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
                    if row['new_product_type'] == product_name:
                        return ['background-color: yellow'] * len(row)
                    else:
                        return [''] * len(row)
                    
                st.write("Your Alternative Products from Leviat's Database:")
                st.write(alternative_products_leviat.style.apply(highlight_product_leviat, axis=1))
        
        if mrd_value_leviat is not None and vrd_value_leviat is not None and height_value_leviat is not None:
            # Search for alternatives in both databases using Leviat specs
            specific_product_leviat = preprocess_additional_file(df_Leviat)[preprocess_additional_file(df_Leviat)['new_product_type'] == product_name]
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
                    if row['new_product_type'] == product_name:
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
        alternative_products_schoeck, additional_products_leviat = fetch_alternative_products_by_specs(
            df_Schoeck, df_Leviat, mrd_value, vrd_value, height_value,
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
