from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import pandas as pd

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('smartphones.db')
    conn.row_factory = sqlite3.Row
    return conn

def load_data():
    conn = get_db_connection()
    df = pd.read_sql_query('SELECT * FROM smartphones', conn)
    conn.close()
    return df

smartphones_df = load_data()

top_brands = ['Apple', 'Samsung', 'Oppo', 'Vivo', 'Xiaomi', 'OnePlus', 'Realme', 'Google', 'Motorola', 'POCO']

def extract_brand(model):
    for brand in top_brands:
        if model.startswith(brand):
            return brand
    return 'Unknown'

smartphones_df['brand'] = smartphones_df['model'].apply(extract_brand)

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
        conn = get_db_connection()
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
            unique_values[col] = ['No preference'] + sorted(set(smartphones_df[col].dropna().astype(str)))

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

    conn = get_db_connection()
    
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
