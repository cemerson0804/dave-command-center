"""
Database Layer — Supabase Connection
======================================
Handles saving and loading transaction data to/from Supabase.
This gives the app permanent memory — data persists between sessions.

HOW IT WORKS:
- When you click "Analyze", transactions get saved to Supabase
- When you open the app, it loads all historical transactions from Supabase
- Duplicates are prevented (same date + amount + description = skip)
"""

import streamlit as st
import pandas as pd
from supabase import create_client


def get_supabase_client():
    """Create a Supabase client using credentials from Streamlit secrets."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def save_transactions(df, profile="cody"):
    """
    Save a DataFrame of transactions to Supabase.
    Skips duplicates (same date + amount + description).
    Returns the count of new records inserted.
    """
    client = get_supabase_client()
    
    inserted = 0
    skipped = 0
    
    for _, row in df.iterrows():
        record = {
            "date": row['Date'].strftime('%Y-%m-%d'),
            "amount": float(row['Amount']),
            "description": str(row.get('Description', '')),
            "category": str(row.get('Category', 'Uncategorized')),
            "type": "expense" if row['Amount'] < 0 else "income",
            "source_file": str(row.get('Source_File', '')),
            "profile": profile
        }
        
        # Check for duplicate before inserting
        existing = client.table('transactions').select('id').eq(
            'date', record['date']
        ).eq(
            'amount', record['amount']
        ).eq(
            'description', record['description']
        ).eq(
            'profile', record['profile']
        ).execute()
        
        if existing.data:
            skipped += 1
        else:
            client.table('transactions').insert(record).execute()
            inserted += 1
    
    return inserted, skipped


def load_transactions(profile=None):
    """
    Load all transactions from Supabase.
    If profile is specified, only loads that profile's data.
    Returns a pandas DataFrame.
    """
    client = get_supabase_client()
    
    query = client.table('transactions').select('*').order('date', desc=True)
    
    if profile and profile != "Household":
        query = query.eq('profile', profile.lower())
    
    # Supabase returns max 1000 rows by default — paginate if needed
    all_data = []
    page_size = 1000
    offset = 0
    
    while True:
        result = query.range(offset, offset + page_size - 1).execute()
        if result.data:
            all_data.extend(result.data)
            if len(result.data) < page_size:
                break
            offset += page_size
        else:
            break
    
    if not all_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_data)
    df['Date'] = pd.to_datetime(df['date'])
    df['Amount'] = df['amount'].astype(float)
    df['Description'] = df['description']
    df['Category'] = df['category']
    df['Is_Expense'] = df['Amount'] < 0
    df['Abs_Amount'] = df['Amount'].abs()
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    
    return df


def get_transaction_count(profile=None):
    """Quick count of transactions in the database."""
    client = get_supabase_client()
    query = client.table('transactions').select('id', count='exact')
    if profile and profile != "Household":
        query = query.eq('profile', profile.lower())
    result = query.execute()
    return result.count if result.count else 0


def delete_transactions_by_month(year, month, profile="cody"):
    """Delete all transactions for a specific month (useful for re-uploading corrected data)."""
    client = get_supabase_client()
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    result = client.table('transactions').delete().eq(
        'profile', profile.lower()
    ).gte('date', start_date).lt('date', end_date).execute()
    
    return len(result.data) if result.data else 0
