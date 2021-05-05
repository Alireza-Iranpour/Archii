import pandas as pd
import json
import streamlit as st
import json
import os
import plotly.express as px
from collections import OrderedDict
from utils import *
import pydeck as pdk

path_to_store_data = 'Often//separated data'

store_names = [name.split('.csv')[0] for name in os.listdir(path_to_store_data)]
store_data_size = [os.stat(f'{path_to_store_data}{os.sep}{name}').st_size for name in os.listdir(path_to_store_data)]
sorted_store_names = [x for _,x in sorted(zip(store_data_size, store_names), reverse=True)]

st.header('Archii Dashboard')

sidebar_option = st.sidebar.selectbox(
    'Options',
     ['Data', 'Menu', 'Food Combinations', 'Stats', 'Customer Data', 'Sales'])

# -------------------------------------------------------------------------

store_name = st.selectbox('Please select your store', sorted_store_names)

@st.cache
def load_store_data(path_to_store_data, store_name):
    data = pd.read_csv(f'{path_to_store_data}{os.sep}{store_name}.csv', index_col=False, parse_dates=['ordered_at', 'ready_time'])
    return data

data = load_store_data(path_to_store_data, store_name)

# -------------------------------------------------------------------------

if sidebar_option == 'Data':
    st.subheader('Data')

    st.write('Number of records: ', data.shape[0])
    st.dataframe(data.head(100))

    column = st.selectbox('Please select your column', data.columns)
    try:
        json_dict = json.loads(data.loc[0, column])
        st.write(json_dict)

    except:
        st.write(data.loc[0, column])

    st.write(get_map(data))


# -------------------------------------------------------------------------

if sidebar_option == 'Stats':
    st.subheader('Stats')
    Stats_expander_1 = st.beta_expander("Order type", expanded=False)
    with Stats_expander_1:
        # st.subheader('Order type')
        fig = px.pie(data, names='order_type', hole=.3)
        st.plotly_chart(fig)

    Stats_expander_2 = st.beta_expander("Status", expanded=False)
    with Stats_expander_2:
        # st.subheader('Status')
        fig = px.pie(data, names='status', hole=.3)
        st.plotly_chart(fig)

    Stats_expander_3 = st.beta_expander("Preparation_time", expanded=False)
    with Stats_expander_3:
        preparation_time_stats = get_preparation_time_stats(data)
        st.write(preparation_time_stats)

    Stats_expander_4 = st.beta_expander("Payment_type", expanded=False)
    with Stats_expander_4:
        df = get_payment_type(data)
        fig = px.pie(df, names='payment_type', hole=.3)
        st.plotly_chart(fig)

# -------------------------------------------------------------------------

if sidebar_option == 'Food Combinations':
    st.subheader('Food Combinations')

    expander_1 = st.beta_expander("Regular Combinations", expanded=False)
    with expander_1:
        combination_length = st.slider('Select combination length', 1, 5)
        top = 10
        all_combinations = get_all_combinations(data, combination_length=combination_length, frequency_threshold=2)
        fig = plot_bar(all_combinations, top=top, title=f'top {top} food combinations')
        st.plotly_chart(fig)

        #####################################################
        # information
        if combination_length == 1:
            st.write(f'({list(all_combinations.keys())[0]}) is the best selling food item which has been ordered ({list(all_combinations.values())[0]}) times')
        else:
            st.write(f'({list(all_combinations.keys())[0]}) is the most common {combination_length} item combination which has appeared in {list(all_combinations.values())[0]} orders')
        #####################################################

    expander_2 = st.beta_expander("Targeted Combinations", expanded=False)
    with expander_2:
        targeted_combination_length = st.slider('Select target combination length', 1, 5)
        menu_items = list(get_menu(data).keys())
        menu_item = st.selectbox('Please select your food item', menu_items)
        targeted_combinations = get_targeted_combinations(food=menu_item, data=data, combination_length=targeted_combination_length+1, frequency_threshold=2)
        fig = plot_bar(targeted_combinations, top=top, title=f'top {top} food combinations with ({menu_item})')

        
        st.plotly_chart(fig)

        #####################################################
        st.write(f'If the customer has already ordered ({menu_item}), we can also recommend:') 
        st.write(f'({list(targeted_combinations.keys())[0]})')
        #####################################################
# -------------------------------------------------------------------------

if sidebar_option == 'Customer Data':
    st.subheader('All Customer Data')
    customer_df = get_customers(data)
    st.write(customer_df)

    #####################################################
    st.write(f"({customer_df.index[0]}) has been the most loyal customer with a total of {customer_df['number of orders'][0]} orders so far")
    #####################################################

    customer = st.selectbox('Please select a customer', customer_df.index)
    customer_orders = data[data['customer_info'].map(lambda x: json.loads(x)['name'] if 'name' in json.loads(x).keys() else None) == customer]
    st.subheader('Customer order history')
    st.dataframe(customer_orders)

    customer_menu = get_menu(customer_orders)
    customer_menu_df = pd.DataFrame(customer_menu).T.sort_values(by=['popularity'], ascending=False)
    st.subheader('Customer preferences')
    st.dataframe(customer_menu_df)

# -------------------------------------------------------------------------

if sidebar_option == 'Menu':
    st.subheader('Inferred Menu')
    menu = get_menu(data)
    menu_df = pd.DataFrame(menu).T.sort_values(by=['popularity'], ascending=False)
    st.dataframe(menu_df)

    menu_item = st.selectbox('Please select your menu item', menu_df.index)
    menu_item_options = menu_df.loc[menu_item].loc['options']
    menu_item_options = pd.DataFrame(menu_item_options, index=['frequency']).T.sort_values(by=['frequency'], ascending=False)
    st.write(f'Options for ({menu_item}) in order of popularity:')
    st.dataframe(menu_item_options)

# -------------------------------------------------------------------------
if sidebar_option == 'Sales':
    st.subheader('Sales')
    timeframe = st.radio('Timeframe', ['daily', 'weekly', 'monthly', 'yearly'])
    sales_info = get_sales_info(data, timeframe)
    Sales_expander_1 = st.beta_expander("Sales data", expanded=False)
    with Sales_expander_1:
        st.dataframe(sales_info)

    Sales_expander_2 = st.beta_expander("Sales plot", expanded=False)
    with Sales_expander_2:
        fig = px.line(sales_info, x=sales_info.index, y=sales_info.columns, title='Sales over time')
        st.plotly_chart(fig)

# -------------------------------------------------------------------------
