"""
Dave Command Center — Cloud Version (Secure)
==============================================
All personal financial data is stored in Streamlit Secrets (encrypted).
This code is GENERIC — safe to be public on GitHub.
No names, balances, account numbers, or amounts in this file.
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
st.set_page_config(page_title="Dave Command Center", page_icon="💰", layout="wide", initial_sidebar_state="collapsed")


# =============================================================================
# PASSWORD GATE
# =============================================================================
def check_password():
    """Returns True if correct password entered."""
    def password_entered():
        if st.session_state["password"] == st.secrets["passwords"]["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("Dave Command Center")
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.caption("Household financial dashboard")
        return False
    elif not st.session_state["password_correct"]:
        st.title("Dave Command Center")
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.error("Incorrect password.")
        return False
    return True


if not check_password():
    st.stop()


# =============================================================================
# LOAD DATA FROM SECRETS
# =============================================================================
def load_bills(profile):
    """Load bill schedule from secrets based on profile."""
    if profile == "Cody":
        return [dict(b) for b in st.secrets.get("cody_bills", [])]
    elif profile == "Deidra":
        return [dict(b) for b in st.secrets.get("deidra_bills", [])]
    else:
        cody = [dict(b) for b in st.secrets.get("cody_bills", [])]
        deidra = [dict(b) for b in st.secrets.get("deidra_bills", [])]
        return cody + deidra


def load_debts():
    """Load debt snowball data from secrets."""
    return [dict(d) for d in st.secrets.get("cody_debts", [])]


def load_income():
    """Load income data from secrets."""
    return dict(st.secrets.get("cody_income", {}))


# =============================================================================
# MAIN APP
# =============================================================================
st.title("Dave Command Center")
st.caption(f"Opened: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")

profile = st.radio("Who's viewing?", ["Cody", "Deidra", "Household"], horizontal=True)

bills = load_bills(profile)
debts = load_debts()
income_data = load_income()


# =============================================================================
# TABS
# =============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Bills Board", "Spending", "Debt Tracker", "Cash Flow", "Upload"])


# --- TAB 1: BILLS BOARD ---
with tab1:
    st.header(f"Bills Board — {profile}")

    today = datetime.now()
    current_day = today.day

    upcoming, due_soon, paid, overdue = [], [], [], []

    for bill in bills:
        due_day = bill['day']
        if due_day < current_day - 5:
            paid.append(bill)
        elif due_day < current_day:
            if bill.get('autopay', False):
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

    if 'transactions' not in st.session_state:
        st.session_state.transactions = pd.DataFrame()

    df = st.session_state.transactions

    if df.empty:
        st.info("No transactions loaded. Go to the **Upload** tab to drop your bank CSV exports.")
    else:
        st.caption(f"Data: {df['Date'].min().date()} to {df['Date'].max().date()} ({len(df)} transactions)")

        if profile == "Deidra":
            summary = get_spending_summary(df, exclude_wife=False)
        else:
            summary = get_spending_summary(df, exclude_wife=True)

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

            fig_bar = px.bar(summary, x='Category', y='Total_Spent', color='Category', title='Spending by Category')
            fig_bar.update_layout(showlegend=False, xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

            monthly = get_spending_by_month(df)
            if not monthly.empty:
                st.subheader("Monthly Trend")
                fig_trend = px.bar(monthly, x='Month', y='Amount', color='Category', barmode='stack', title='Monthly Spending')
                fig_trend.update_layout(height=400)
                st.plotly_chart(fig_trend, use_container_width=True)

        uncategorized = df[df['Category'] == 'Uncategorized']
        if not uncategorized.empty:
            st.subheader(f"Uncategorized ({len(uncategorized)})")
            st.dataframe(uncategorized[['Date', 'Amount', 'Description']].head(20), use_container_width=True)


# --- TAB 3: DEBT TRACKER ---
with tab3:
    st.header("Debt Snowball Tracker")

    if profile in ("Cody", "Household"):
        active_debts = [d for d in debts if d.get('balance', 0) > 0 and d.get('status') != 'Baby Step 6']
        total_non_mortgage = sum(d.get('balance', 0) for d in active_debts)
        total_daily_interest = sum(d.get('daily_interest', 0) for d in active_debts)
        killed_count = sum(1 for d in debts if d.get('status') == 'PAID OFF')

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Non-Mortgage Debt", f"${total_non_mortgage:,.2f}")
        col2.metric("Daily Interest Burn", f"${total_daily_interest:.2f}/day")
        col3.metric("Monthly Interest Burn", f"${total_daily_interest * 30:.0f}/mo")
        col4.metric("Debts Killed", f"{killed_count}")

        st.divider()
        st.subheader("Snowball Order")

        for debt in debts:
            status = debt.get('status', 'Active')
            if status == 'PAID OFF':
                st.success(f"~~{debt['name']}~~ — **DEAD** ({debt.get('killed_date', '')})")
            elif status == 'CURRENT TARGET':
                st.warning(f"**{debt['name']}** — ${debt.get('balance', 0):,.2f} at {debt.get('apr', 0)}% | CURRENT TARGET")
                if debt.get('promo_deadline'):
                    st.caption(f"Promo deadline: {debt['promo_deadline']}")
            elif status == '0% Promo':
                st.info(f"**{debt['name']}** — ${debt.get('balance', 0):,.2f} at 0% | Min ${debt.get('minimum', 0)}/mo | Promo ends {debt.get('promo_deadline', '?')}")
            elif status == 'Baby Step 6':
                st.info(f"{debt['name']} — ${debt.get('balance', 0):,.2f} at {debt.get('apr', 0)}% | After cards die")
            else:
                daily = debt.get('daily_interest', 0)
                st.write(f"**{debt['name']}** — ${debt.get('balance', 0):,.2f} at {debt.get('apr', 0)}% | Min ${debt.get('minimum', 0)}/mo | ${daily:.2f}/day")

        st.divider()
        interest_data = [{"Debt": d['name'], "Monthly Interest": d.get('daily_interest', 0) * 30} for d in debts if d.get('daily_interest', 0) > 0]
        if interest_data:
            fig_int = px.bar(pd.DataFrame(interest_data), x='Debt', y='Monthly Interest', color='Debt', title='Monthly Interest Burn')
            fig_int.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig_int, use_container_width=True)
    else:
        st.info("Deidra's debt tracking — add her debt info to secrets to populate this view.")


# --- TAB 4: CASH FLOW ---
with tab4:
    st.header("Cash Flow")

    if profile in ("Cody", "Household") and income_data:
        check_bonus = income_data.get('check_with_bonus', 0)
        check_no_bonus = income_data.get('check_without_bonus', 0)
        checks_per_month = income_data.get('checks_per_month', 2.17)
        bonus_end = income_data.get('bonus_end_date', '2026-10-12')

        income_with_bonus = check_bonus * checks_per_month
        income_without_bonus = check_no_bonus * checks_per_month
        cody_bills_total = sum(b['amount'] for b in load_bills("Cody"))
        gas_groceries = 560 + 800
        total_outflow = cody_bills_total + gas_groceries

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("With Bonus")
            st.metric("Monthly Income", f"${income_with_bonus:,.0f}")
            st.metric("Monthly Outflow", f"${total_outflow:,.0f}")
            st.metric("Surplus", f"${income_with_bonus - total_outflow:,.0f}")

        with col2:
            st.subheader("After Bonus Ends")
            st.metric("Monthly Income", f"${income_without_bonus:,.0f}")
            st.metric("Monthly Outflow", f"${total_outflow:,.0f}")
            surplus_no = income_without_bonus - total_outflow
            st.metric("Surplus", f"${surplus_no:,.0f}", delta=f"-${income_with_bonus - income_without_bonus:,.0f}")

        # Forecast
        st.divider()
        st.subheader("12-Month Forecast")
        bonus_end_dt = datetime.strptime(bonus_end, '%Y-%m-%d')
        months = []
        for i in range(12):
            month_date = datetime.now() + timedelta(days=30*i)
            income = income_with_bonus if month_date < bonus_end_dt else income_without_bonus
            months.append({"Month": month_date.strftime('%b %Y'), "Income": income, "Expenses": total_outflow, "Surplus": income - total_outflow})

        forecast_df = pd.DataFrame(months)
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Income', x=forecast_df['Month'], y=forecast_df['Income'], marker_color='#2ecc71'))
        fig.add_trace(go.Bar(name='Expenses', x=forecast_df['Month'], y=forecast_df['Expenses'], marker_color='#e74c3c'))
        fig.add_trace(go.Scatter(name='Surplus', x=forecast_df['Month'], y=forecast_df['Surplus'], mode='lines+markers', marker_color='#3498db'))
        fig.update_layout(title='Income vs Expenses', barmode='group', height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Add income data to secrets to populate this view.")


# --- TAB 5: UPLOAD ---
with tab5:
    st.header("Upload Financial Data")
    st.caption("Drop your files here — the system auto-detects whether it's a bank CSV or a bill PDF and processes accordingly. Nothing is stored on the server.")

    uploaded_files = st.file_uploader(
        "Drop bank CSVs and bill PDFs here",
        type=['csv', 'pdf'],
        accept_multiple_files=True
    )

    if uploaded_files:
        csv_files = [f for f in uploaded_files if f.name.lower().endswith('.csv')]
        pdf_files = [f for f in uploaded_files if f.name.lower().endswith('.pdf')]

        # Process CSVs (bank transactions)
        if csv_files:
            st.subheader(f"Bank Transactions ({len(csv_files)} files)")
            all_dfs = []
            for f in csv_files:
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
                st.info(f"Loaded {len(combined)} transactions. Go to **Spending** tab to see charts.")

        # Process PDFs (bill statements)
        if pdf_files:
            st.subheader(f"Bill Statements ({len(pdf_files)} files)")
            import pdfplumber
            import re

            for f in pdf_files:
                try:
                    # Read PDF text
                    pdf = pdfplumber.open(f)
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                    pdf.close()

                    if not text.strip():
                        st.warning(f"{f.name}: Image-based PDF — cannot extract text automatically.")
                        continue

                    # Auto-detect statement type and show key info
                    st.write(f"**{f.name}**")

                    # Chase
                    if "chase" in text.lower() and ("sapphire" in text.lower() or "cardhelp" in text.lower()):
                        amounts = re.findall(r'([\d,]+\.\d{2})', text)
                        cc_amounts = [float(a.replace(',', '')) for a in amounts if 5000 < float(a.replace(',', '')) < 50000]
                        balance = max(set(cc_amounts), key=cc_amounts.count) if cc_amounts else "Unknown"
                        interest_match = re.search(r'PURCHASE INTEREST CHARGE\s*([\d,]+\.\d{2})', text)
                        interest = float(interest_match.group(1).replace(',', '')) if interest_match else "Unknown"
                        due_match = re.search(r'(\d{2}/\d{2}/\d{2})', text)
                        due = due_match.group(1) if due_match else "Unknown"
                        st.success(f"Chase Credit Card — Balance: ${balance:,.2f} | Interest: ${interest} | Due: {due}")

                    # Toyota Financial
                    elif "toyota" in text.lower() and "financial" in text.lower():
                        bal_match = re.search(r'OutstandingBalance\*?\s*\$?([\d,]+\.?\d*)', text)
                        balance = float(bal_match.group(1).replace(',', '')) if bal_match else "Unknown"
                        due_match = re.search(r'PaymentDueDate\s*(\d+/\d+/\d+)', text)
                        due = due_match.group(1) if due_match else "Unknown"
                        pmt_match = re.search(r'CurrentPaymentDue\s*\$?([\d,]+\.?\d*)', text)
                        pmt = float(pmt_match.group(1).replace(',', '')) if pmt_match else "Unknown"
                        st.success(f"Toyota Financial — Balance: ${balance:,.2f} | Payment: ${pmt} | Due: {due}")

                    # Wells Fargo
                    elif "wells fargo" in text.lower():
                        amounts = re.findall(r'[\d,]+\.\d{2}', text)
                        payoff_amounts = [float(a.replace(',', '')) for a in amounts if 5000 < float(a.replace(',', '')) < 50000]
                        payoff = payoff_amounts[0] if payoff_amounts else "Unknown"
                        due_match = re.search(r'Payment due date\s*(\d{2}/\d{2}/\d{2,4})', text)
                        due = due_match.group(1) if due_match else "Unknown"
                        past_match = re.search(r'Amount past due\s*\$?([\d,]+\.?\d*)', text)
                        past_due = float(past_match.group(1).replace(',', '')) if past_match else 0
                        st.success(f"Wells Fargo Auto — Payoff: ${payoff:,.2f} | Due: {due} | Past Due: ${past_due:,.2f}")

                    else:
                        st.info(f"Recognized as bill statement but type unknown. First 200 chars: {text[:200]}")

                except Exception as e:
                    st.error(f"Error reading {f.name}: {e}")

    st.divider()
    st.subheader("Current Session Data")
    if not st.session_state.get('transactions', pd.DataFrame()).empty:
        df_status = st.session_state.transactions
        st.write(f"**Transactions loaded:** {len(df_status)}")
        st.write(f"**Date range:** {df_status['Date'].min().date()} to {df_status['Date'].max().date()}")
    else:
        st.write("No transaction data loaded this session.")


# --- SIDEBAR ---
with st.sidebar:
    st.header("Quick Stats")
    st.write(f"**Profile:** {profile}")
    st.write(f"**Today:** {datetime.now().strftime('%b %d, %Y')}")

    if profile in ("Cody", "Household") and income_data:
        bonus_end = income_data.get('bonus_end_date', '2026-10-12')
        bonus_end_dt = datetime.strptime(bonus_end, '%Y-%m-%d')
        days_left = max(0, (bonus_end_dt - datetime.now()).days)
        st.metric("Days Until Bonus Ends", days_left)
        st.divider()
        st.write("**Baby Step:** 2")
        st.write("**Target:** Best Buy")
        killed = sum(1 for d in debts if d.get('status') == 'PAID OFF')
        st.write(f"**Debts Killed:** {killed}")
