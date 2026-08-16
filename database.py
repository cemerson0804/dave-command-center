"""
Database Layer --- Supabase Connection
======================================
Handles saving and loading transaction data to/from Supabase.
This gives the app permanent memory --- data persists between sessions.

HOW IT WORKS:
- When you click "Analyze", transactions get saved to Supabase
- When you open the app, it loads all historical transactions from Supabase
- Duplicates are prevented (same date + amount + description = skip)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
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
    
    # Supabase returns max 1000 rows by default --- paginate if needed
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


# =============================================================================
# BILL PAYMENT TRACKING
# =============================================================================

def get_bill_payments(profile, month, year):
    """
    Load bill payment statuses for a specific month.
    Returns a dict: {bill_name: {"paid": True/False, "paid_date": "2026-08-03"}}
    """
    client = get_supabase_client()
    result = client.table('bill_payments').select('bill_name, paid, paid_date').eq(
        'profile', profile.lower()
    ).eq('month', month).eq('year', year).execute()
    
    payments = {}
    if result.data:
        for row in result.data:
            payments[row['bill_name']] = {
                "paid": row['paid'],
                "paid_date": row.get('paid_date')
            }
    return payments


def mark_bill_paid(bill_name, profile, month, year, paid=True):
    """
    Mark a bill as paid (or unpaid) for a specific month.
    Uses upsert --- creates the record if it doesn't exist, updates if it does.
    """
    client = get_supabase_client()
    
    record = {
        "bill_name": bill_name,
        "profile": profile.lower(),
        "month": month,
        "year": year,
        "paid": paid,
        "paid_date": datetime.now().strftime('%Y-%m-%d') if paid else None
    }
    
    client.table('bill_payments').upsert(
        record,
        on_conflict='bill_name,profile,month,year'
    ).execute()


def mark_bill_unpaid(bill_name, profile, month, year):
    """Move a bill back to unpaid (undo a paid mark)."""
    mark_bill_paid(bill_name, profile, month, year, paid=False)


def update_paid_date(bill_name, profile, month, year, new_date):
    """Update the paid date for a bill (for correcting timestamps)."""
    client = get_supabase_client()
    client.table('bill_payments').update(
        {"paid_date": new_date}
    ).eq('bill_name', bill_name).eq(
        'profile', profile.lower()
    ).eq('month', month).eq('year', year).execute()


def delete_transaction(date, amount, description, profile="cody"):
    """Delete a specific transaction from the database."""
    client = get_supabase_client()
    result = client.table('transactions').delete().eq(
        'date', date
    ).eq(
        'amount', amount
    ).eq(
        'description', description
    ).eq(
        'profile', profile.lower()
    ).execute()
    return len(result.data) if result.data else 0

def recategorize_all_transactions(category_rules):
    """Re-apply category rules to all transactions in the database."""
    import re as re_mod
    client = get_supabase_client()
    
    all_rows = []
    offset = 0
    while True:
        result = client.table('transactions').select('id, description, category').order('id').range(offset, offset + 999).execute()
        if result.data:
            all_rows.extend(result.data)
            if len(result.data) < 1000:
                break
            offset += 1000
        else:
            break
    
    def categorize(desc):
        if not desc:
            return 'Uncategorized'
        for pattern, cat in category_rules:
            if re_mod.search(pattern, desc, re_mod.IGNORECASE):
                return cat
        return 'Uncategorized'
    
    updated = 0
    for row in all_rows:
        new_cat = categorize(row['description'])
        if new_cat != row['category']:
            client.table('transactions').update({'category': new_cat}).eq('id', row['id']).execute()
            updated += 1
    
    return updated, len(all_rows)


# =============================================================================
# LIVE DEBT BALANCE TRACKING
# =============================================================================

def get_debts(profile="cody"):
    """Load all debts for a profile, ordered by balance ascending (snowball order)."""
    client = get_supabase_client()
    result = client.table('debts').select('*').eq('profile', profile.lower()).order('balance').execute()
    return result.data if result.data else []


def seed_debt(name, profile, balance, apr, minimum, status, promo_deadline=None, killed_date=None, daily_interest=0):
    """Insert or update a debt record (used for initial setup/migration)."""
    client = get_supabase_client()
    record = {
        "name": name,
        "profile": profile.lower(),
        "balance": balance,
        "apr": apr,
        "minimum": minimum,
        "status": status,
        "promo_deadline": promo_deadline,
        "killed_date": killed_date,
        "daily_interest": daily_interest,
    }
    client.table('debts').upsert(record, on_conflict='name,profile').execute()


def adjust_debt_balance(name, profile, delta):
    """
    Adjust a debt's balance by delta.
    Negative delta = payment reduces balance.
    Positive delta = undo increases balance back.
    Balance never goes below zero.
    Returns the new balance, or None if the debt wasn't found.
    """
    client = get_supabase_client()
    result = client.table('debts').select('balance').eq('name', name).eq('profile', profile.lower()).execute()
    if not result.data:
        return None
    current = float(result.data[0]['balance'])
    new_balance = max(0, current + delta)
    client.table('debts').update({
        "balance": new_balance,
        "updated_at": datetime.now().isoformat()
    }).eq('name', name).eq('profile', profile.lower()).execute()
    return new_balance


# =============================================================================
# DYNAMIC BILLS MANAGEMENT
# =============================================================================

def get_bills(profile):
    """Load all active bills for a profile from the database."""
    client = get_supabase_client()
    if profile.lower() == "household":
        result = client.table('bills').select('*').eq('active', True).order('day').execute()
    else:
        result = client.table('bills').select('*').eq('profile', profile.lower()).eq('active', True).order('day').execute()
    return result.data if result.data else []


def add_bill(name, profile, amount, day, autopay=False, apr=None, category=None):
    """Add a new bill to the database."""
    client = get_supabase_client()
    record = {
        "name": name,
        "profile": profile.lower(),
        "amount": amount,
        "day": day,
        "autopay": autopay,
        "apr": apr,
        "category": category,
        "active": True
    }
    client.table('bills').upsert(record, on_conflict='name,profile').execute()


def update_bill(name, profile, **kwargs):
    """Update a bill's fields (amount, day, autopay, apr, category, active)."""
    client = get_supabase_client()
    client.table('bills').update(kwargs).eq('name', name).eq('profile', profile.lower()).execute()


def archive_bill(name, profile):
    """Mark a bill as inactive (paid off / no longer owed). Removes from Bills Board."""
    update_bill(name, profile, active=False)


def reactivate_bill(name, profile):
    """Bring a bill back to active status."""
    update_bill(name, profile, active=True)
