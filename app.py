"""
Dave Command Center — Cloud Version
=====================================
Hosted on Streamlit Community Cloud. Accessible from any device.
Password-protected. Supports two profiles (Cody & Deidra).
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from transaction_parser import parse_csv_upload, get_spending_summary, get_spending_by_month, get_income_summary


# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Dave Command Center",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =============================================================================
# PASSWORD GATE
# =============================================================================
def check_password():
    """Returns True if the user entered the correct password."""
    
    def password_entered():
        """Check whether password is correct."""
        if st.session_state["password"] == st.secrets["passwords"]["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    # First run or password not yet correct
    if "password_correct" not in st.session_state:
        st.title("Dave Command Center")
        st.text_input(
            "Enter password to continue:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.caption("Household financial dashboard — Emerson family")
        return False
    
    # Password incorrect
    elif not st.session_state["password_correct"]:
        st.title("Dave Command Center")
        st.text_input(
            "Enter password to continue:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("Incorrect password. Try again.")
        return False
    
    # Password correct
    else:
        return True


if not check_password():
    st.stop()


# =============================================================================
# BILL SCHEDULES (per profile)
# =============================================================================
CODY_BILLS = [
    {"name": "Mortgage (Onity)", "amount": 829.45, "day": 1, "autopay": True},
    {"name": "HELOC (Figure)", "amount": 313.66, "day": 1, "autopay": True},
    {"name": "Toyota Camry", "amount": 692.59, "day": 1, "autopay": True},
    {"name": "Camper (US Bank)", "amount": 405.00, "day": 1, "autopay": True},
    {"name": "C-Spire Fiber", "amount": 52.27, "day": 1, "autopay": True},
    {"name": "Spartan Gym", "amount": 75.00, "day": 1, "autopay": True},
    {"name": "Brookhaven Academy", "amount": 281.33, "day": 1, "autopay": False},
    {"name": "GMC Canyon", "amount": 335.98, "day": 3, "autopay": True},
    {"name": "Chase Sapphire", "amount": 500.00, "day": 5, "autopay": True},
    {"name": "Robinhood CC", "amount": 259.00, "day": 10, "autopay": False},
    {"name": "Best Buy", "amount": 67.00, "day": 12, "autopay": False},
    {"name": "Alfa Insurance", "amount": 319.34, "day": 13, "autopay": True},
    {"name": "IRS Installment", "amount": 124.50, "day": 15, "autopay": True},
    {"name": "Southern FCU", "amount": 205.00, "day": 16, "autopay": True},
    {"name": "AT&T Wireless", "amount": 323.52, "day": 22, "autopay": True},
    {"name": "Nissan Sentra", "amount": 232.00, "day": 24, "autopay": True},
    {"name": "Entergy Electric", "amount": 162.00, "day": 28, "autopay": True},
    {"name": "Cable", "amount": 45.00, "day": 28, "autopay": False},
    {"name": "Voice Lessons", "amount": 60.00, "day": 15, "autopay": False},
]

DEIDRA_BILLS = [
    {"name": "Mortgage (her 40%)", "amount": 552.97, "day": 1, "autopay": True},
    {"name": "HELOC (her 40%)", "amount": 209.10, "day": 1, "autopay": True},
    {"name": "Entergy (her 40%)", "amount": 108.00, "day": 28, "autopay": True},
    {"name": "C-Spire (her 40%)", "amount": 34.84, "day": 1, "autopay": True},
    {"name": "Cable (her 50%)", "amount": 45.00, "day": 28, "autopay": False},
    {"name": "AT&T (her lines)", "amount": 307.94, "day": 22, "autopay": True},
    {"name": "Alfa Insurance (her vehicles)", "amount": 285.12, "day": 13, "autopay": True},
    {"name": "GMC Canyon (her 40%)", "amount": 224.00, "day": 3, "autopay": True},
    {"name": "350Z", "amount": 129.82, "day": 9, "autopay": True},
    {"name": "IRS (her 50%)", "amount": 124.50, "day": 15, "autopay": True},
    {"name": "Americor Debt Mgmt", "amount": 235.53, "day": 6, "autopay": True},
    {"name": "Voice Lessons (her 50%)", "amount": 60.00, "day": 15, "autopay": False},
]

CODY_DEBTS = [
    {"name": "Home Depot", "balance": 0, "apr": 29.99, "minimum": 0, "status": "PAID OFF", "killed_date": "07/23/2026"},
    {"name": "Best Buy", "balance": 444.21, "apr": 29.74, "minimum": 67, "status": "CURRENT TARGET", "promo_deadline": "05/16/2027"},
    {"name": "Chase Sapphire", "balance": 16335.33, "apr": 25.49, "minimum": 500, "status": "Active", "daily_interest": 11.41},
    {"name": "Robinhood CC", "balance": 12013.14, "apr": 24.24, "minimum": 259, "status": "Active", "daily_interest": 7.98},
    {"name": "Southern FCU", "balance": 4249.70, "apr": 10.25, "minimum": 205, "status": "Active", "daily_interest": 1.19},
    {"name": "Wells Fargo (0% transfer)", "balance": 3000.00, "apr": 0, "minimum": 143, "status": "0% Promo", "promo_deadline": "05/2028"},
    {"name": "Figure HELOC", "balance": 58137.37, "apr": 10.30, "minimum": 522.76, "status": "Baby Step 6", "daily_interest": 16.41},
]


# =============================================================================
# MAIN APP (after password)
# =============================================================================
st.title("Dave Command Center")
st.caption(f"Opened: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")

# Profile selector
profile = st.radio("Who's viewing?", ["Cody", "Deidra", "Household"], horizontal=True)

# Select the right bill schedule
if profile == "Cody":
    bills = CODY_BILLS
elif profile == "Deidra":
    bills = DEIDRA_BILLS
else:
    bills = CODY_BILLS + DEIDRA_BILLS


# =============================================================================
# TABS
# =============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Bills Board", "Spending", "Debt Tracker", "Cash Flow", "Upload"])


# --- TAB 1: BILLS BOARD ---
with tab1:
    st.header(f"Bills Board — {profile}")
    
    today = datetime.now()
    current_day = today.day
    
    upcoming = []
    due_soon = []
    paid = []
    overdue = []
    
    for bill in bills:
        due_day = bill['day']
        if due_day < current_day - 5:
            if bill['autopay']:
                paid.append(bill)
            else:
                paid.append(bill)  # Assume paid if past due date by 5+ days
        elif due_day < current_day:
            if bill['autopay']:
                paid.append(bill)
            else:
                overdue.append(bill)
        elif due_day <= current_day + 7:
            due_soon.append(bill)
        else:
            upcoming.append(bill)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.subheader(f"Paid ({len(paid)})")
        for bill in paid:
            st.success(f"**{bill['name']}**\n${bill['amount']:,.2f}")
    
    with col2:
        st.subheader(f"Due Soon ({len(due_soon)})")
        for bill in due_soon:
            st.warning(f"**{bill['name']}**\n${bill['amount']:,.2f} — due {bill['day']}th")
    
    with col3:
        st.subheader(f"Upcoming ({len(upcoming)})")
        for bill in upcoming:
            st.info(f"**{bill['name']}**\n${bill['amount']:,.2f} — due {bill['day']}th")
    
    with col4:
        st.subheader(f"Overdue ({len(overdue)})")
        for bill in overdue:
            st.error(f"**{bill['name']}**\n${bill['amount']:,.2f} — WAS DUE {bill['day']}th!")
    
    st.divider()
    total_bills = sum(b['amount'] for b in bills)
    st.metric(f"Total Monthly Bills ({profile})", f"${total_bills:,.2f}")


# --- TAB 2: SPENDING ---
with tab2:
    st.header("Spending Breakdown")
    
    # Check if transactions are in session state
    if 'transactions' not in st.session_state:
        st.session_state.transactions = pd.DataFrame()
    
    df = st.session_state.transactions
    
    if df.empty:
        st.info("No transactions loaded yet. Go to the **Upload** tab to drop your bank CSV exports.")
    else:
        st.caption(f"Data: {df['Date'].min().date()} to {df['Date'].max().date()} ({len(df)} transactions)")
        
        # Spending summary
        if profile == "Deidra":
            summary = get_spending_summary(df, exclude_wife=False, exclude_transfers=True)
        else:
            summary = get_spending_summary(df, exclude_wife=True, exclude_transfers=True)
        
        if not summary.empty:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.pie(summary, values='Total_Spent', names='Category', title='Where the Money Goes', hole=0.4)
                fig.update_traces(textposition='inside', textinfo='label+percent')
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("By Category")
                for _, row in summary.iterrows():
                    st.write(f"**{row['Category']}:** ${row['Total_Spent']:,.2f}")
                st.divider()
                st.metric("Total Spent", f"${summary['Total_Spent'].sum():,.2f}")
                income = get_income_summary(df)
                st.metric("Total Income", f"${income:,.2f}")
            
            # Bar chart
            fig_bar = px.bar(summary, x='Category', y='Total_Spent', color='Category', title='Spending by Category')
            fig_bar.update_layout(showlegend=False, xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Monthly trend
            monthly = get_spending_by_month(df)
            if not monthly.empty:
                st.subheader("Monthly Trend")
                fig_trend = px.bar(monthly, x='Month', y='Amount', color='Category', barmode='stack', title='Monthly Spending')
                fig_trend.update_layout(height=400)
                st.plotly_chart(fig_trend, use_container_width=True)
        
        # Uncategorized
        uncategorized = df[df['Category'] == 'Uncategorized']
        if not uncategorized.empty:
            st.subheader(f"Uncategorized ({len(uncategorized)})")
            st.dataframe(uncategorized[['Date', 'Amount', 'Description']].head(20), use_container_width=True)


# --- TAB 3: DEBT TRACKER ---
with tab3:
    st.header("Debt Snowball Tracker")
    
    if profile in ("Cody", "Household"):
        debts = CODY_DEBTS
        active_debts = [d for d in debts if d['balance'] > 0 and d['status'] != 'Baby Step 6']
        total_non_mortgage = sum(d['balance'] for d in active_debts)
        total_daily_interest = sum(d.get('daily_interest', 0) for d in active_debts)
        killed_count = sum(1 for d in debts if d['status'] == 'PAID OFF')
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Non-Mortgage Debt", f"${total_non_mortgage:,.2f}")
        col2.metric("Daily Interest Burn", f"${total_daily_interest:.2f}/day")
        col3.metric("Monthly Interest Burn", f"${total_daily_interest * 30:.0f}/mo")
        col4.metric("Debts Killed", f"{killed_count}")
        
        st.divider()
        st.subheader("Snowball Order")
        
        for debt in debts:
            if debt['status'] == 'PAID OFF':
                st.success(f"~~{debt['name']}~~ — **DEAD** ({debt.get('killed_date', '')})")
            elif debt['status'] == 'CURRENT TARGET':
                st.warning(f"**{debt['name']}** — ${debt['balance']:,.2f} at {debt['apr']}% | CURRENT TARGET")
                if 'promo_deadline' in debt:
                    st.caption(f"Promo deadline: {debt['promo_deadline']}")
            elif debt['status'] == '0% Promo':
                st.info(f"**{debt['name']}** — ${debt['balance']:,.2f} at 0% | Min ${debt['minimum']}/mo | Promo ends {debt.get('promo_deadline', '?')}")
            elif debt['status'] == 'Baby Step 6':
                st.info(f"{debt['name']} — ${debt['balance']:,.2f} at {debt['apr']}% | After cards die")
            else:
                daily = debt.get('daily_interest', 0)
                st.write(f"**{debt['name']}** — ${debt['balance']:,.2f} at {debt['apr']}% | Min ${debt['minimum']}/mo | ${daily:.2f}/day interest")
        
        # Interest chart
        st.divider()
        interest_data = [{"Debt": d['name'], "Monthly Interest": d.get('daily_interest', 0) * 30} for d in debts if d.get('daily_interest', 0) > 0]
        if interest_data:
            fig_int = px.bar(pd.DataFrame(interest_data), x='Debt', y='Monthly Interest', color='Debt', title='Monthly Interest Burn')
            fig_int.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig_int, use_container_width=True)
    else:
        st.info("Deidra's debt tracking coming soon — add her debt info to get started.")


# --- TAB 4: CASH FLOW ---
with tab4:
    st.header("Cash Flow")
    
    if profile in ("Cody", "Household"):
        income_with_bonus = 4422.30 * 2.17
        income_without_bonus = 3559.75 * 2.17
        cody_bills_total = sum(b['amount'] for b in CODY_BILLS)
        gas_groceries = 560 + 800
        total_outflow = cody_bills_total + gas_groceries
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("With Bonus (thru Oct 12)")
            st.metric("Monthly Income", f"${income_with_bonus:,.0f}")
            st.metric("Monthly Outflow", f"${total_outflow:,.0f}")
            surplus = income_with_bonus - total_outflow
            st.metric("Surplus", f"${surplus:,.0f}")
        
        with col2:
            st.subheader("After Oct 12 (No Bonus)")
            st.metric("Monthly Income", f"${income_without_bonus:,.0f}")
            st.metric("Monthly Outflow", f"${total_outflow:,.0f}")
            surplus_no = income_without_bonus - total_outflow
            st.metric("Surplus", f"${surplus_no:,.0f}", delta=f"-${income_with_bonus - income_without_bonus:,.0f}")
        
        # Forecast chart
        st.divider()
        st.subheader("12-Month Forecast")
        months = []
        for i in range(12):
            month_date = datetime.now() + timedelta(days=30*i)
            income = income_with_bonus if month_date < datetime(2026, 10, 12) else income_without_bonus
            months.append({"Month": month_date.strftime('%b %Y'), "Income": income, "Expenses": total_outflow, "Surplus": income - total_outflow})
        
        forecast_df = pd.DataFrame(months)
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Income', x=forecast_df['Month'], y=forecast_df['Income'], marker_color='#2ecc71'))
        fig.add_trace(go.Bar(name='Expenses', x=forecast_df['Month'], y=forecast_df['Expenses'], marker_color='#e74c3c'))
        fig.add_trace(go.Scatter(name='Surplus', x=forecast_df['Month'], y=forecast_df['Surplus'], mode='lines+markers', marker_color='#3498db'))
        fig.update_layout(title='Income vs Expenses (12-Month Forecast)', barmode='group', height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Deidra's cash flow — add her income info to populate this view.")


# --- TAB 5: UPLOAD ---
with tab5:
    st.header("Upload Financial Data")
    st.caption("Drop your bank CSV exports here. Data stays in your session only — nothing is stored permanently on the server.")
    
    uploaded_files = st.file_uploader(
        "Upload Ally Bank CSV exports",
        type=['csv'],
        accept_multiple_files=True,
        key="csv_uploader"
    )
    
    if uploaded_files:
        all_dfs = []
        for f in uploaded_files:
            try:
                parsed = parse_csv_upload(f)
                all_dfs.append(parsed)
                st.success(f"Parsed: {f.name} ({len(parsed)} transactions)")
            except Exception as e:
                st.error(f"Error with {f.name}: {e}")
        
        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            combined = combined.drop_duplicates(subset=['Date', 'Amount', 'Description'], keep='first')
            combined = combined.sort_values('Date', ascending=False).reset_index(drop=True)
            st.session_state.transactions = combined
            st.success(f"Loaded {len(combined)} unique transactions. Go to **Spending** tab to see charts.")
    
    # Show current data status
    st.divider()
    if not st.session_state.get('transactions', pd.DataFrame()).empty:
        df = st.session_state.transactions
        st.write(f"**Transactions loaded:** {len(df)}")
        st.write(f"**Date range:** {df['Date'].min().date()} to {df['Date'].max().date()}")
        st.write(f"**Accounts detected:** Based on transaction patterns")
    else:
        st.write("No data loaded this session.")


# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.header("Quick Stats")
    st.write(f"**Profile:** {profile}")
    st.write(f"**Today:** {datetime.now().strftime('%b %d, %Y')}")
    
    if profile in ("Cody", "Household"):
        days_to_cliff = max(0, (datetime(2026, 10, 12) - datetime.now()).days)
        st.metric("Days Until Bonus Ends", days_to_cliff)
        st.divider()
        st.write("**Baby Step:** 2")
        st.write("**Target:** Best Buy")
        st.write("**Debts Killed:** 1 (Home Depot)")
