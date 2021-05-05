import json
from itertools import combinations
from collections import OrderedDict
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import streamlit as st
import datetime
import requests
import pydeck as pdk
from bs4 import BeautifulSoup

@st.cache
def get_menu(data):
    menu = {}
    for order_id, order in enumerate(data['order_items']):
        order_list = json.loads(order)
        order_items = []
        for item in order_list:
            
            if item['name'] not in menu.keys():
                menu[item['name']] = {}
                menu[item['name']]['price'] = item['price']
                # menu[item['name']]['options'] = item['options']
                menu[item['name']]['popularity'] = 1
                order_items.append(item['name'])

                menu[item['name']]['options'] = {option: 1 for option in item['options']}
                
            else:
                if item['options']:
                    # menu[item['name']]['options'] = list(set(menu[item['name']]['options']) | set(item['options']))
                    
                    for option in item['options']:
                        if option in menu[item['name']]['options'].keys():
                            menu[item['name']]['options'][option] = menu[item['name']]['options'][option] + 1
                        else:
                            menu[item['name']]['options'][option] = 1


                if item['name'] not in order_items:
                    # if not already observed in this order
                    menu[item['name']]['popularity'] = menu[item['name']]['popularity'] + 1
                    order_items.append(item['name'])

    #for item in menu.keys():
        #menu[item]['options'] = OrderedDict(menu[item]['options'].items(), reverse=True, key=lambda x: x[1])

    return menu

# ---------------------------------------------------------------------------
@st.cache
def get_all_combinations(data, combination_length=2, frequency_threshold=2):
    item_combinations = {}
    clean_item_combinations = {}

    for order in data['order_items']:
        order_list = json.loads(order)
        items = list(set([item['name'] for item in order_list]))
        _combinations = [" , ".join(map(str, comb)) for comb in combinations(sorted(items), combination_length)]
        for combination in _combinations:
            if combination not in item_combinations.keys():
                item_combinations[combination] = 1
            else:
                item_combinations[combination] += 1
                if item_combinations[combination] > frequency_threshold:
                    clean_item_combinations[combination] = item_combinations[combination]

    clean_item_combinations = OrderedDict(sorted(clean_item_combinations.items(), reverse=True, key=lambda x: x[1]))
    return clean_item_combinations

# ---------------------------------------------------------------------------
@st.cache
def get_targeted_combinations(food, data, combination_length=2, frequency_threshold=2):
    item_combinations = {}
    for order in data['order_items']:
        order_list = json.loads(order)
        items = list(set([item['name'] for item in order_list]))
        if food in items:
            _combinations = [" , ".join(map(str, comb)) for comb in combinations(sorted(items), combination_length)]
            for combination in _combinations:
                if food in combination:
                    combination.split(' , ')
                    if combination not in item_combinations.keys():
                        item_combinations[combination] = 1
                    else:
                        item_combinations[combination] += 1

    clean_item_combinations = {}               
    for combination in item_combinations.keys():
        clean_combination = combination.split(' , ')
        clean_combination.remove(food)
        clean_combination = ' , '.join(clean_combination)
        if item_combinations[combination] >= frequency_threshold:
            clean_item_combinations[clean_combination] = item_combinations[combination]

    clean_item_combinations = OrderedDict(sorted(clean_item_combinations.items(), reverse=True, key=lambda x: x[1]))
    return clean_item_combinations


# ---------------------------------------------------------------------------
@st.cache
def plot_bar(data, top=10, title=None):
    fig = go.Figure(go.Bar(x=list(data.values())[:top], y=list(data.keys())[:top], orientation='h'))
    fig['layout']['yaxis']['autorange'] = 'reversed'
    fig.update_layout(title_text=title)
    return fig

# ---------------------------------------------------------------------------
@st.cache
def get_customers(data):
    customer_df = data.groupby(['customer_info']).apply(lambda x: pd.Series({
        'Name': json.loads(x['customer_info'].iloc[0])['name'],
        'Email': [json.loads(x['customer_info'].iloc[0])['email'] if ('email' in json.loads(x['customer_info'].iloc[0]).keys()) else np.NaN][0],
        'Phone': [json.loads(x['customer_info'].iloc[0])['phone'] if ('phone' in json.loads(x['customer_info'].iloc[0]).keys()) else np.NaN][0],
        'number of orders': x['invoice_id'].count()
    })).set_index(['Name']).sort_values(by=['number of orders'], ascending=False)
    return customer_df

# ---------------------------------------------------------------------------

@st.cache
def get_preparation_time_stats(data):
    delays_in_minutes = (data['ready_time'] - data['ordered_at']).map(lambda x: x.seconds/60)
    stats = {
        'mean_delay (minutes)': delays_in_minutes.mean(),
        'median_delay (minutes)': delays_in_minutes.median(),
        'min_delay (minutes)': delays_in_minutes.min(),
        'max_delay (minutes)': delays_in_minutes.max(),
    }
    return stats

# ---------------------------------------------------------------------------
@st.cache
def get_payment_type(data):
    invoice_data = data['invoice_data'].map(lambda x: json.loads(x))
    invoice_data = invoice_data.map(lambda x: x['card'] if 'card' in x.keys() else {})
    invoice_data = invoice_data.map(lambda x: x['brand'] if 'brand' in x.keys() else None)
    df = pd.DataFrame({'payment_type': invoice_data})
    return df

# ---------------------------------------------------------------------------
@st.cache
def get_sales_info(data, timeframe):
    invoice_data = data['invoice_data'].map(lambda x: json.loads(x))
    total = invoice_data.map(lambda x: float(x['total'].replace('$', '')) if 'total' in x.keys() else np.NaN)
    tips = invoice_data.map(lambda x: float(x['tips'].replace('$', '')) if 'tips' in x.keys() else np.NaN)
    sub_total = invoice_data.map(lambda x: float(x['sub_total'].replace('$', '')) if 'sub_total' in x.keys() else np.NaN)
    total_paid = invoice_data.map(lambda x: (x['total_paid'].replace('$', '')) if 'total_paid' in x.keys() else np.NaN)
    df = pd.DataFrame({
        'date': data['ordered_at'],
        'total': total,
        'tips': tips,
        'sub_total': sub_total,
        'total_paid': total_paid})

    special_cases = (df['total_paid'] == 'Failed') | (df['total_paid'] == 'Refunded') | (df['total_paid'] == 'Adjusted')
    df = df[~special_cases]
    df['total_paid'] = df['total_paid'].astype(float)

    tf = {'daily': '1D', 'weekly':'1W', 'monthly':'1M', 'yearly': '1Y'}
    
    try:
        return df.groupby(pd.Grouper(key='date',freq=tf[timeframe])).sum()
    except:
        return df

# ---------------------------------------------------------------------------

def get_lon_lat(address):
    address = address.replace(' ', '+')
    response  = requests.get(f'https://www.google.ca/maps/place/{address}')
    html_content = response.text
    soup = BeautifulSoup(html_content)
    soup.find_all('meta')
    content = soup.find("meta",  property="og:image")['content']
    ll = [item for item in content.split('&') if 'll' in item][0].split('=')[-1].split(',')
    latitude, longitude = (float(ll[0]), float(ll[1]))
    return latitude, longitude

# ---------------------------------------------------------------------------
@st.cache
def get_map(data):
    address = json.loads(data['store_info'][0])['address']
    (latitude, longitude) = get_lon_lat(address)
    view_state = pdk.ViewState(latitude=latitude, longitude=longitude, zoom=12, bearing=0, pitch=50)

    geo_data = pd.DataFrame({
        'name': json.loads(data['store_info'][0])['name'],
        'address': json.loads(data['store_info'][0])['address'],
        'sales': get_sales_info(data, 'daily')['total'].max(),
        'coordinates': [[longitude, latitude]]
        })


    layer = pdk.Layer(
        "ColumnLayer",
        data=geo_data,
        get_position='coordinates',
        get_elevation="sales",
        elevation_scale=0.1,
        radius=50,
        get_fill_color=[255, 140, 0],
        pickable=True,
        auto_highlight=True,
        radius_min_pixels=1,
        radius_max_pixels=200,
        )

    r = pdk.Deck(layers=[layer], initial_view_state=view_state, map_style='light', tooltip={"text": "{name}\n{address}\n${sales}/month"})
    return r

# ---------------------------------------------------------------------------