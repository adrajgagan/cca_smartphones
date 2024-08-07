import sqlite3
import pandas as pd

# Connect to SQLite database
conn = sqlite3.connect('smartphones.db')

# Load dataset
df = pd.read_csv('dataset/combined.csv')

# Convert all columns to string type
df = df.astype(str)

# Fill missing values with an empty string
df.fillna('', inplace=True)

# Write the data to SQLite database
df.to_sql('smartphones', conn, if_exists='replace', index=False)

conn.close()
