"""
Transaction Parser for Dave Command Center (Cloud Version)
===========================================================
Same logic as the local version but works with uploaded file objects
instead of file paths.
"""

import pandas as pd
import re
from io import StringIO


CATEGORY_RULES = [
    # === WIFE'S EXPENSES (exclude from Cody's budget) ===
    ("AMERICOR", "Wife-Expense"),
    ("GLOBAL GHLLC", "Wife-Expense"),
    ("OCHSNER CLINIC", "Wife-Income"),
    ("THERALOGIX", "Wife-Expense"),
    ("BREADPAY", "Wife-Expense"),
    ("Pirate Ship", "Wife-Expense"),
    ("SP AFF.*IRESTORE", "Wife-Expense"),
    ("Check Paid #1120", "Wife-Expense"),

    # === INCOME ===
    ("AMAZON DATA SERV PAYROLL", "Income"),
    ("PAYROLL", "Income"),
    ("Interest Paid", "Income"),
    ("ATM Fee Reimbursement", "Income"),
    ("VENMO.*EMERSON", "Income"),
    ("Return Check", "Income"),

    # === TRANSFERS ===
    ("Internet transfer from Spending", "Transfer-In"),
    ("Internet transfer from", "Transfer-In"),
    ("Internet transfer to Spending", "Transfer-Out"),
    ("Internet transfer to", "Transfer-Out"),
    ("Requested transfer from", "Transfer-In"),
    ("eCheck Deposit", "Transfer-In"),
    ("Round ups Booster Transfer", "Investing"),
    ("Acorns Round-Ups", "Investing"),
    ("Acorns Invest Transfer", "Investing"),

    # === BILLS: HOUSING ===
    ("MORTGAGE SERV", "Bills-Housing"),
    ("FIGURE LENDING", "Bills-Housing"),
    ("FIGUREPAYM", "Bills-Housing"),
    ("ENTERGY", "Bills-Housing"),
    ("CSPIRE", "Bills-Housing"),
    ("C-SPIRE", "Bills-Housing"),

    # === BILLS: AUTO PAYMENTS ===
    ("WELLS FARGO AUTO", "Bills-Auto"),
    ("TOYOTA ACH", "Bills-Auto"),
    ("ALFA MUTUAL INS", "Bills-Auto"),

    # === BILLS: AUTO MAINTENANCE ===
    ("TOYOTA OF BROOKHAVEN", "Auto-Maintenance"),
    ("AUTOZONE", "Auto-Maintenance"),
    ("TOUCH.*GO CAR WASH", "Auto-Maintenance"),

    # === BILLS: DEBT PAYMENTS ===
    ("CHASE CREDIT CRD", "Bills-Debt"),
    ("Robinhood CCB Payment", "Bills-Debt"),
    ("Robinhood Card Payment", "Bills-Debt"),
    ("HOME DEPOT ONLINE PMT", "Bills-Debt"),
    ("BEST BUY PAYMENT", "Bills-Debt"),
    ("Southern FCU Payment", "Bills-Debt"),

    # === BILLS: SUBSCRIPTIONS ===
    ("Netflix", "Bills-Subscriptions"),
    ("APPLE\\.COM/BILL", "Bills-Subscriptions"),
    ("APPLE COM BILL", "Bills-Subscriptions"),
    ("SCRIBD", "Bills-Subscriptions"),
    ("ANTHROPIC.*CLAUDE", "Bills-Subscriptions"),
    ("OPENAI.*CHATGPT", "Bills-Subscriptions"),
    ("AMAZON PRIME", "Bills-Subscriptions"),
    ("Prime Video", "Bills-Subscriptions"),
    ("PLAYSTATION STORE", "Bills-Subscriptions"),
    ("FID BKG SVC LLC MONEYLINE", "Bills-Subscriptions"),
    ("OUR FAMILY WIZARD", "Bills-Subscriptions"),
    ("Subscription Acorns", "Bills-Subscriptions"),
    ("GLOBAL WORK AI", "Bills-Subscriptions"),
    ("ROBOFORM", "Bills-Subscriptions"),
    ("Plarium", "Bills-Subscriptions"),
    ("Sams Club Renewal", "Bills-Subscriptions"),

    # === BILLS: PHONE ===
    ("ATT PAYMENT", "Bills-Phone"),
    ("AT&T", "Bills-Phone"),

    # === BILLS: FITNESS ===
    ("SPARTAN", "Bills-Fitness"),
    ("The Clubs at Ole", "Bills-Fitness"),

    # === KIDS ===
    ("CASH APP.*EASTON", "Kids"),
    ("Brookhaven Academy", "Kids"),
    ("NBS.*Brookhaven Academy", "Kids"),
    ("BROOKHAVEN SCHOOL", "Kids"),
    ("BANKPLUS", "Kids"),
    ("BROOKHAVEN LITTLE THEA", "Kids"),

    # === MEDICAL ===
    ("DABBS CANNA", "Medical"),
    ("DABBS.*BYRAM", "Medical"),
    ("DABBS", "Medical"),
    ("MAGNOLIA SUP", "Medical"),
    ("KING'S DAUGHTERS MED", "Medical"),
    ("DELTA DISPENSARY", "Medical"),
    ("ROOTDOWN", "Medical"),
    ("PAI ATM", "Medical"),
    ("BROOKHAVEN INTERNAL ME", "Medical"),

    # === GAS ===
    ("CHEVRON", "Gas"),
    ("SHELL", "Gas"),
    ("HOODS FUEL", "Gas"),
    ("WALL EXPRESS", "Gas"),
    ("CITY MART", "Gas"),
    ("MURPHY", "Gas"),
    ("TEXACO", "Gas"),
    ("TERRY TEXACO", "Gas"),
    ("CIRCLE K", "Gas"),
    ("B - KWIK", "Gas"),
    ("PICAYUNE PETROL", "Gas"),
    ("CROSSROADS CONV", "Gas"),

    # === FOOD: GROCERIES ===
    ("WAL.*MART", "Food-Groceries"),
    ("WM SUPERCENTER", "Food-Groceries"),
    ("DOLLAR GENERAL", "Food-Groceries"),
    ("DOLLAR-GENERAL", "Food-Groceries"),
    ("SAMSCLUB", "Food-Groceries"),
    ("SULLIVAN", "Food-Groceries"),
    ("TRACTOR SUPPLY", "Food-Groceries"),
    ("ALDI", "Food-Groceries"),
    ("DOLLAR TREE", "Food-Groceries"),
    ("WHOLE.?F", "Food-Groceries"),
    ("WALGREENS", "Food-Groceries"),

    # === FOOD: DINING OUT ===
    ("WENDY", "Food-Dining"),
    ("SONIC DRIVE", "Food-Dining"),
    ("RAISING CANE", "Food-Dining"),
    ("TACO BELL", "Food-Dining"),
    ("WAFFLE HOUSE", "Food-Dining"),
    ("DONUT PALACE", "Food-Dining"),
    ("TORTILLA SOUP", "Food-Dining"),
    ("LOS.*PARRILLERO", "Food-Dining"),
    ("CAZADORES", "Food-Dining"),
    ("JASON.S DELI", "Food-Dining"),
    ("ARBY", "Food-Dining"),
    ("The Fish Fry", "Food-Dining"),
    ("OLD COKE PLAN", "Food-Dining"),
    ("BURGER KING", "Food-Dining"),
    ("SHRIMP BASKET", "Food-Dining"),
    ("BETTY.*EAT SHOP", "Food-Dining"),
    ("WALK-ON", "Food-Dining"),
    ("DOMINO", "Food-Dining"),
    ("KFC", "Food-Dining"),
    ("HUEY MAGOO", "Food-Dining"),
    ("BROMA.*DELI", "Food-Dining"),
    ("MAGNOLIA BLUES BBQ", "Food-Dining"),
    ("YOYO SAKI", "Food-Dining"),
    ("CAFFE LATTE", "Food-Dining"),
    ("EAT WITH US", "Food-Dining"),
    ("APLOS", "Food-Dining"),

    # === SHOPPING ===
    ("AMAZON MKTPL", "Shopping"),
    ("AMAZON", "Shopping"),
    ("T\\.?J\\.? MAXX", "Shopping"),
    ("MARSHALLS", "Shopping"),
    ("ROSS STORE", "Shopping"),
    ("FIVE BELOW", "Shopping"),
    ("TARGET", "Shopping"),
    ("HOME HARDWARE", "Shopping"),
    ("BEALLS", "Shopping"),
    ("HOBBYLOBBY", "Shopping"),
    ("HOBBY LOBBY", "Shopping"),
    ("COLUMBUS RETAIL", "Shopping"),
    ("WIGS BEAUTY", "Shopping"),
    ("SQ.*WARD", "Shopping"),

    # === SHOPPING: HOME/HARDWARE ===
    ("NST THE HOME DEPOT", "Shopping-Home"),
    ("THE HOME DEPOT", "Shopping-Home"),
    ("Harbor Freight", "Shopping-Home"),

    # === INVESTING ===
    ("Acorns", "Investing"),

    # === KIDS ACTIVITIES ===
    ("PAYPAL INST XFER", "Kids-Activities"),
    ("PAYPAL PURCHASE", "Kids-Activities"),
    ("PAYPAL TRANSFER", "Transfer-In"),

    # === ONE-TIME ===
    ("STATE PARKS", "One-Time"),
    ("Check Paid #1450", "One-Time"),
    ("Check Paid #1119", "One-Time"),

    # === MISC ===
    ("TRUSTMARK BANK", "Misc-Bills"),
    ("Check Paid", "Misc-Bills"),
    ("USPS", "Misc-Bills"),
]


def categorize_transaction(description):
    """Categorize a single transaction by its description."""
    if not description or pd.isna(description):
        return "Uncategorized"
    for pattern, category in CATEGORY_RULES:
        if re.search(pattern, description, re.IGNORECASE):
            return category
    return "Uncategorized"


def parse_csv_upload(uploaded_file):
    """Parse an uploaded CSV file (Streamlit UploadedFile object)."""
    df = pd.read_csv(uploaded_file)
    df.columns = [col.strip() for col in df.columns]
    df['Date'] = pd.to_datetime(df['Date'])
    if df['Amount'].dtype == object:
        df['Amount'] = df['Amount'].replace(r'[\$,]', '', regex=True).astype(float)
    df['Category'] = df['Description'].apply(categorize_transaction)
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    df['Is_Expense'] = df['Amount'] < 0
    df['Abs_Amount'] = df['Amount'].abs()
    df = df.sort_values('Date', ascending=False).reset_index(drop=True)
    return df


def get_spending_summary(df, exclude_wife=True, exclude_transfers=True):
    """Get spending grouped by category."""
    filters = df['Is_Expense'] == True
    if exclude_wife:
        filters = filters & (~df['Category'].str.startswith('Wife'))
    if exclude_transfers:
        filters = filters & (~df['Category'].str.startswith('Transfer'))
    filters = filters & (df['Category'] != 'Income')
    filters = filters & (df['Category'] != 'Wife-Income')
    
    your_expenses = df[filters].copy()
    summary = your_expenses.groupby('Category')['Abs_Amount'].agg(['sum', 'count']).reset_index()
    summary.columns = ['Category', 'Total_Spent', 'Transaction_Count']
    summary = summary.sort_values('Total_Spent', ascending=False)
    return summary


def get_spending_by_month(df, exclude_wife=True, exclude_transfers=True):
    """Get spending by month and category for trend charts."""
    filters = df['Is_Expense'] == True
    if exclude_wife:
        filters = filters & (~df['Category'].str.startswith('Wife'))
    if exclude_transfers:
        filters = filters & (~df['Category'].str.startswith('Transfer'))
    filters = filters & (df['Category'] != 'Income')
    filters = filters & (df['Category'] != 'Wife-Income')
    
    your_expenses = df[filters].copy()
    monthly = your_expenses.groupby(['Month', 'Category'])['Abs_Amount'].sum().reset_index()
    monthly.columns = ['Month', 'Category', 'Amount']
    return monthly


def get_income_summary(df):
    """Get total income."""
    income = df[df['Category'] == 'Income']
    return income['Amount'].sum()
