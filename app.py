from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import sqlite3
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go

# Initialize Flask app
app = Flask(__name__)

# Initialize Dash app
dash_app = Dash(__name__, server=app, url_base_pathname='/dashboard/')

# Load CSV data into Pandas DataFrame
df = pd.read_csv('combined.csv')

# Extract brand from model names
top_brands = ['Apple', 'Samsung', 'Oppo', 'Vivo', 'Xiaomi', 'OnePlus', 'Realme', 'Google', 'Motorola', 'POCO']

def extract_brand(model):
    model_lower = model.lower()
    for brand in top_brands:
        if brand.lower() in model_lower:
            return brand
    return 'Unknown'

df['brand'] = df['model'].apply(extract_brand)

# Save data to SQLite database
def save_to_db(df):
    conn = sqlite3.connect('smartphones.db')
    df.to_sql('smartphones', conn, if_exists='replace', index=False)
    conn.close()

save_to_db(df)

# Define Flask routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/explore')
def explore():
    return render_template('explore.html')

@app.route('/index')
def index():
    return render_template('index.html', models=top_brands)

@app.route('/price_ranges', methods=['POST'])
def price_ranges():
    model = request.form.get('model', '')

    if model:
        conn = sqlite3.connect('smartphones.db')
        query = f'SELECT DISTINCT "price" FROM smartphones WHERE "model" LIKE "{model}%"'
        unique_prices = [row[0] for row in conn.execute(query).fetchall()]
        conn.close()

        # Handle price ranges
        if unique_prices:
            unique_prices = sorted(map(float, unique_prices))
            min_price, max_price = unique_prices[0], unique_prices[-1]
            range_step = (max_price - min_price) / 3
            price_ranges = [
                f"{min_price:.0f}-{min_price + range_step:.0f}",
                f"{min_price + range_step:.0f}-{min_price + 2 * range_step:.0f}",
                f"{min_price + 2 * range_step:.0f}-{max_price:.0f}"
            ]
        else:
            price_ranges = []

        # Get unique values for other attributes
        unique_values = {}
        for col in ['5G_or_not', 'ram_capacity', 'internal_memory', 'extended_memory_available']:
            unique_values[col] = ['No preference'] + sorted(set(df[col].dropna().astype(str)))

        return render_template('price_ranges.html', price_ranges=price_ranges, model=model, unique_values=unique_values)
    
    return redirect(url_for('index'))

@app.route('/recommend', methods=['POST'])
def recommend():
    model = request.form.get('model', '')
    price_range = request.form.get('price_range', 'No preference')
    _5G_or_not = request.form.get('5G_or_not', 'No preference')
    ram_capacity = request.form.get('ram_capacity', 'No preference')
    internal_memory = request.form.get('internal_memory', 'No preference')
    extended_memory_available = request.form.get('extended_memory_available', 'No preference')

    conn = sqlite3.connect('smartphones.db')
    
    # Construct the query with filters
    filters = []
    if model and model != 'No preference':
        filters.append(f'"model" LIKE "{model}%"')
    if price_range and price_range != 'No preference':
        min_price, max_price = map(float, price_range.split('-'))
        filters.append(f'"price" BETWEEN {min_price} AND {max_price}')
    if _5G_or_not and _5G_or_not != 'No preference':
        filters.append(f'"5G_or_not" = "{_5G_or_not}"')
    if ram_capacity and ram_capacity != 'No preference':
        filters.append(f'"ram_capacity" = "{ram_capacity}"')
    if internal_memory and internal_memory != 'No preference':
        filters.append(f'"internal_memory" = "{internal_memory}"')
    if extended_memory_available and extended_memory_available != 'No preference':
        filters.append(f'"extended_memory_available" = "{extended_memory_available}"')

    query = "SELECT * FROM smartphones"
    if filters:
        query += " WHERE " + " AND ".join(filters)

    # Debug: Print the query for troubleshooting
    print(f"Generated Query: {query}")

    smartphones_df_filtered = pd.read_sql_query(query, conn)
    conn.close()

    # Debug: Print the filtered DataFrame for troubleshooting
    print(smartphones_df_filtered)

    if not smartphones_df_filtered.empty:
        return render_template('results.html', tables=[smartphones_df_filtered.to_html(classes='data')], titles=smartphones_df_filtered.columns.values)
    else:
        return render_template('results.html', message="No smartphones match your criteria.")

# Dash layout and callbacks
dash_app.layout = html.Div([
    html.H1('Smartphone Trend Analysis Dashboard'),
    dcc.Dropdown(
        id='brand-dropdown',
        options=[{'label': brand, 'value': brand} for brand in df['brand'].unique()],
        value='Apple'
    ),
    dcc.Dropdown(
        id='comparison-brand-dropdown',
        options=[{'label': brand, 'value': brand} for brand in df['brand'].unique()],
        value='Samsung'
    ),
    html.Div([
        dcc.Graph(id='price-distribution'),
        dcc.Graph(id='comparison-price-distribution')
    ], style={'display': 'flex', 'justify-content': 'space-around'}),
    dcc.Graph(id='price-trend'),
    html.Div(
        html.Button('Home', id='return-home', n_clicks=0, style={'margin-top': '20px'}),
        style={'display': 'flex', 'justify-content': 'center'}
    ),
    dcc.Location(id='home-url', refresh=True)
])

@dash_app.callback(
    [Output('price-distribution', 'figure'),
     Output('comparison-price-distribution', 'figure'),
     Output('price-trend', 'figure'),
     Output('home-url', 'href')],
    [Input('brand-dropdown', 'value'),
     Input('comparison-brand-dropdown', 'value'),
     Input('return-home', 'n_clicks')]
)
def update_graphs(selected_brand, comparison_brand, n_clicks):
    # Check if the button is clicked
    if n_clicks > 0:
        return None, None, None, '/'

    filtered_df = df[df['brand'] == selected_brand]
    comparison_df = df[df['brand'] == comparison_brand]

    # First Pie Chart
    price_ranges = {
        'Low': sum(filtered_df['price'] < 20000),
        'Mid': sum((filtered_df['price'] >= 20000) & (filtered_df['price'] < 40000)),
        'High': sum(filtered_df['price'] >= 40000)
    }
    pie_fig = px.pie(
        names=list(price_ranges.keys()),
        values=list(price_ranges.values()),
        title=f'Price Range Distribution for {selected_brand}'
    )

    # Second Pie Chart
    comparison_price_ranges = {
        'Low': sum(comparison_df['price'] < 20000),
        'Mid': sum((comparison_df['price'] >= 20000) & (comparison_df['price'] < 40000)),
        'High': sum(comparison_df['price'] >= 40000)
    }
    comparison_pie_fig = px.pie(
        names=list(comparison_price_ranges.keys()),
        values=list(comparison_price_ranges.values()),
        title=f'Price Range Distribution for {comparison_brand}'
    )

    # Line Graph
    line_fig = go.Figure()
    line_fig.add_trace(go.Scatter(x=filtered_df['model'], y=filtered_df['price'], mode='lines+markers', name=selected_brand))
    line_fig.add_trace(go.Scatter(x=comparison_df['model'], y=comparison_df['price'], mode='lines+markers', name=comparison_brand))
    line_fig.update_layout(title=f'Price Trend Comparison: {selected_brand} vs {comparison_brand}', xaxis_title='Model', yaxis_title='Price')

    return pie_fig, comparison_pie_fig, line_fig, None

if __name__ == '__main__':
    app.run(debug=True, port=5000)
