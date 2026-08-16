"""
Dave Command Center - Cloud Version (Secure)
All personal financial data stored in Streamlit Secrets + Supabase.
Code is generic and safe to be public on GitHub.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from transaction_parser import parse_csv_upload, get_spending_summary, get_spending_by_month, get_income_summary
from database import (
    save_transactions, load_transactions, get_transaction_count,
    get_bill_payments, mark_bill_paid, mark_bill_unpaid, update_paid_date,
    delete_transaction, recategorize_all_transactions,
    get_debts, adjust_debt_balance,
    get_bills, add_bill, update_bill, archive_bill
)

st.set_page_config(page_title="Dave Command Center", page_icon="$", layout="wide", initial_sidebar_state="collapsed")

# === PASSWORD GATE ===
def check_password():
    def password_entered():
        if st.session_state.get("password") == st.secrets["passwords"]["app_password"]:
            st.session_state["password_correct"] = True
            st.session_state["login_time"] = time.time()
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct") == True:
        return True
    st.title("Dave Command Center")
    st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
    st.caption("Household financial dashboard")
    if st.session_state.get("password_correct") == False:
        st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

# === SESSION STATE ===
if 'transactions' not in st.session_state:
    st.session_state.transactions = pd.DataFrame()
if 'db_loaded' not in st.session_state:
    st.session_state.db_loaded = False

# === LOAD FROM DB ON FIRST OPEN ===
st.title("Dave Command Center")
if not st.session_state.db_loaded:
    try:
        db_data = load_transactions()
        if not db_data.empty:
            st.session_state.transactions = db_data
        st.session_state.db_loaded = True
    except:
        st.session_state.db_loaded = True

# === PROFILE + MONTH SELECTOR ===
col_profile, col_month, col_year = st.columns([2, 1, 1])
with col_profile:
    profile = st.radio("Who's viewing?", ["Cody", "Deidra", "Household"], horizontal=True)
with col_month:
    selected_month = st.selectbox("Month", options=list(range(1, 13)), format_func=lambda m: datetime(2026, m, 1).strftime('%B'), index=datetime.now().month - 1)
with col_year:
    current_year = datetime.now().year
    selected_year = st.selectbox("Year", options=list(range(2025, current_year + 2)), index=current_year - 2025)

st.caption(f"Viewing: **{datetime(selected_year, selected_month, 1).strftime('%B %Y')}** | Profile: **{profile}**")

# Load data from DB
bills = get_bills(profile)
debts = get_debts(profile.lower()) if profile != "Household" else get_debts("cody")
income_data = dict(st.secrets.get("cody_income", {}))

# Filter transactions
df_all = st.session_state.transactions
if not df_all.empty:
    df = df_all[(df_all['Date'].dt.month == selected_month) & (df_all['Date'].dt.year == selected_year)].copy()
else:
    df = pd.DataFrame()

# === BILL-TO-DEBT MAPPING ===
BILL_DEBT_LINKS = {
    "Chase Sapphire": "Chase Sapphire",
    "Robinhood CC": "Robinhood CC",
    "Best Buy": "Best Buy",
    "Southern FCU": "Southern FCU",
    "HELOC (Figure)": "Figure HELOC",
}

# === TABS ===
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Bills Board", "Spending", "Debt Tracker", "Cash Flow", "Upload"])

# --- TAB 1: BILLS BOARD ---
with tab1:
    st.header(f"Bills Board - {profile}")
    st.caption(f"{datetime(selected_year, selected_month, 1).strftime('%B %Y')}")

    try:
        payment_status = get_bill_payments(profile, selected_month, selected_year)
    except:
        payment_status = {}

    today = datetime.now()
    if selected_month == today.month and selected_year == today.year:
        current_day = today.day
    elif (selected_year < today.year) or (selected_year == today.year and selected_month < today.month):
        current_day = 32
    else:
        current_day = 0

    paid_bills = []
    unpaid_bills = []
    for bill in bills:
        bill_status = payment_status.get(bill['name'], {})
        if isinstance(bill_status, dict) and bill_status.get('paid', False):
            bill['paid_date'] = bill_status.get('paid_date')
            paid_bills.append(bill)
        else:
            unpaid_bills.append(bill)

    due_soon, upcoming, overdue = [], [], []
    for bill in unpaid_bills:
        due_day = bill['day']
        if current_day == 32:
            overdue.append(bill)
        elif current_day == 0:
            upcoming.append(bill)
        elif due_day < current_day - 2:
            overdue.append(bill)
        elif due_day <= current_day + 7:
            due_soon.append(bill)
        else:
            upcoming.append(bill)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.subheader(f"Paid ({len(paid_bills)})")
        for bill in paid_bills:
            paid_date = bill.get('paid_date', '')
            apr_text = f" | {bill['apr']}%" if bill.get('apr') else ""
            st.success(f"**{bill['name']}**\n${float(bill['amount']):,.2f}{apr_text}\nPaid: {paid_date or 'unknown'}")
            c1, c2 = st.columns(2)
            with c1:
                new_date = st.date_input("Date", value=datetime.strptime(paid_date, '%Y-%m-%d').date() if paid_date else datetime.now().date(), key=f"dt_{bill['name']}_{selected_month}", label_visibility="collapsed")
                if paid_date and str(new_date) != paid_date:
                    try:
                        update_paid_date(bill['name'], profile, selected_month, selected_year, str(new_date))
                    except:
                        pass
            with c2:
                if st.button("Undo", key=f"undo_{bill['name']}_{selected_month}"):
                    try:
                        mark_bill_unpaid(bill['name'], profile, selected_month, selected_year)
                        debt_name = BILL_DEBT_LINKS.get(bill['name'])
                        if debt_name:
                            adjust_debt_balance(debt_name, profile.lower(), float(bill['amount']))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    with col2:
        st.subheader(f"Due Soon ({len(due_soon)})")
        for bill in due_soon:
            apr_text = f" | {bill['apr']}%" if bill.get('apr') else ""
            st.warning(f"**{bill['name']}**\n${float(bill['amount']):,.2f} - due {bill['day']}th{apr_text}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Mark Paid", key=f"pay_{bill['name']}_{selected_month}"):
                    try:
                        mark_bill_paid(bill['name'], profile, selected_month, selected_year)
                        debt_name = BILL_DEBT_LINKS.get(bill['name'])
                        if debt_name:
                            adjust_debt_balance(debt_name, profile.lower(), -float(bill['amount']))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with c2:
                if st.button("Edit", key=f"edit_{bill['name']}_{selected_month}"):
                    st.session_state[f"editing_{bill['name']}"] = True

            if st.session_state.get(f"editing_{bill['name']}"):
                new_amt = st.number_input("Amount", value=float(bill['amount']), key=f"amt_{bill['name']}")
                new_day = st.number_input("Due day", value=int(bill['day']), min_value=1, max_value=31, key=f"day_{bill['name']}")
                if st.button("Save", key=f"save_{bill['name']}"):
                    update_bill(bill['name'], profile.lower(), amount=new_amt, day=new_day)
                    del st.session_state[f"editing_{bill['name']}"]
                    st.rerun()

    with col3:
        st.subheader(f"Upcoming ({len(upcoming)})")
        for bill in upcoming:
            apr_text = f" | {bill['apr']}%" if bill.get('apr') else ""
            st.info(f"**{bill['name']}**\n${float(bill['amount']):,.2f} - due {bill['day']}th{apr_text}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Mark Paid", key=f"pay_{bill['name']}_{selected_month}_u"):
                    try:
                        mark_bill_paid(bill['name'], profile, selected_month, selected_year)
                        debt_name = BILL_DEBT_LINKS.get(bill['name'])
                        if debt_name:
                            adjust_debt_balance(debt_name, profile.lower(), -float(bill['amount']))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with c2:
                if st.button("Edit", key=f"edit_{bill['name']}_{selected_month}_u"):
                    st.session_state[f"editing_{bill['name']}"] = True

            if st.session_state.get(f"editing_{bill['name']}"):
                new_amt = st.number_input("Amount", value=float(bill['amount']), key=f"amt_{bill['name']}_u")
                new_day = st.number_input("Due day", value=int(bill['day']), min_value=1, max_value=31, key=f"day_{bill['name']}_u")
                if st.button("Save", key=f"save_{bill['name']}_u"):
                    update_bill(bill['name'], profile.lower(), amount=new_amt, day=new_day)
                    del st.session_state[f"editing_{bill['name']}"]
                    st.rerun()

    with col4:
        st.subheader(f"Overdue ({len(overdue)})")
        for bill in overdue:
            st.error(f"**{bill['name']}**\n${float(bill['amount']):,.2f} - WAS DUE {bill['day']}th!")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Mark Paid", key=f"pay_{bill['name']}_{selected_month}_o"):
                    try:
                        mark_bill_paid(bill['name'], profile, selected_month, selected_year)
                        debt_name = BILL_DEBT_LINKS.get(bill['name'])
                        if debt_name:
                            adjust_debt_balance(debt_name, profile.lower(), -float(bill['amount']))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with c2:
                if st.button("Edit", key=f"edit_{bill['name']}_{selected_month}_o"):
                    st.session_state[f"editing_{bill['name']}"] = True

    st.divider()
    total_bills = sum(float(b['amount']) for b in bills)
    total_paid = sum(float(b['amount']) for b in paid_bills)
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Total Monthly Bills", f"${total_bills:,.2f}")
    col_m2.metric("Paid So Far", f"${total_paid:,.2f}")
    col_m3.metric("Still Owed", f"${total_bills - total_paid:,.2f}")

    # Add new bill manually
    st.divider()
    with st.expander("Add a new bill"):
        new_name = st.text_input("Bill name", key="new_bill_name")
        new_amount = st.number_input("Monthly amount (your share)", min_value=0.0, key="new_bill_amt")
        new_day = st.number_input("Due day of month", min_value=1, max_value=31, value=1, key="new_bill_day")
        new_autopay = st.checkbox("AutoPay?", key="new_bill_auto")
        if st.button("Add Bill", key="add_bill_btn"):
            if new_name and new_amount > 0:
                add_bill(new_name, profile.lower(), new_amount, new_day, new_autopay)
                st.success(f"Added: {new_name} - ${new_amount:,.2f}/mo")
                st.rerun()


# --- TAB 2: SPENDING ---
with tab2:
    st.header("Spending Breakdown")
    st.caption(f"{datetime(selected_year, selected_month, 1).strftime('%B %Y')}")
    if df.empty:
        st.info("No transactions for this month. Upload bank CSVs in the **Upload** tab.")
    else:
        st.caption(f"{len(df)} transactions")
        summary = get_spending_summary(df, exclude_wife=(profile != "Deidra"))
        if not summary.empty:
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.pie(summary, values='Total_Spent', names='Category', title='Where the Money Goes', hole=0.4)
                fig.update_traces(textposition='inside', textinfo='label+percent')
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                for _, row in summary.iterrows():
                    st.write(f"**{row['Category']}:** ${row['Total_Spent']:,.2f}")
                st.divider()
                st.metric("Total Spent", f"${summary['Total_Spent'].sum():,.2f}")
                st.metric("Total Income", f"${get_income_summary(df):,.2f}")

            fig_bar = px.bar(summary, x='Category', y='Total_Spent', color='Category', title='By Category')
            fig_bar.update_layout(showlegend=False, xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

        if not df_all.empty:
            monthly = get_spending_by_month(df_all)
            if not monthly.empty and len(monthly['Month'].unique()) > 1:
                st.subheader("Monthly Trend")
                fig_t = px.bar(monthly, x='Month', y='Amount', color='Category', barmode='stack')
                fig_t.update_layout(height=400)
                st.plotly_chart(fig_t, use_container_width=True)

        uncategorized = df[df['Category'] == 'Uncategorized']
        if not uncategorized.empty:
            st.subheader(f"Uncategorized ({len(uncategorized)})")
            for idx, row in uncategorized.head(20).iterrows():
                c1, c2, c3 = st.columns([4, 1, 1])
                with c1:
                    st.write(f"{row['Date'].date()} | {row['Description'][:50]}")
                with c2:
                    st.write(f"${row['Amount']:,.2f}")
                with c3:
                    if st.button("X", key=f"del_{idx}"):
                        try:
                            delete_transaction(row['Date'].strftime('%Y-%m-%d'), float(row['Amount']), row['Description'], profile.lower())
                            st.session_state.transactions = st.session_state.transactions.drop(idx)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))


# --- TAB 3: DEBT TRACKER ---
with tab3:
    st.header("Debt Snowball Tracker")
    if profile in ("Cody", "Household"):
        active = [d for d in debts if float(d.get('balance', 0)) > 0 and d.get('status') != 'Baby Step 6']
        total_debt = sum(float(d.get('balance', 0)) for d in active)
        total_daily = sum(float(d.get('daily_interest', 0)) for d in active)
        killed = sum(1 for d in debts if d.get('status') == 'PAID OFF')

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Non-Mortgage Debt", f"${total_debt:,.2f}")
        c2.metric("Daily Interest", f"${total_daily:.2f}/day")
        c3.metric("Monthly Interest", f"${total_daily * 30:.0f}/mo")
        c4.metric("Debts Killed", str(killed))

        st.divider()
        for debt in debts:
            status = debt.get('status', 'Active')
            bal = float(debt.get('balance', 0))
            apr = float(debt.get('apr', 0))
            daily = float(debt.get('daily_interest', 0))
            if status == 'PAID OFF':
                st.success(f"~~{debt['name']}~~ - DEAD ({debt.get('killed_date', '')})")
            elif status == 'CURRENT TARGET':
                st.warning(f"**{debt['name']}** - ${bal:,.2f} at {apr}% | CURRENT TARGET")
                if debt.get('promo_deadline'):
                    st.caption(f"Promo: {debt['promo_deadline']}")
            elif status == '0% Promo':
                st.info(f"**{debt['name']}** - ${bal:,.2f} at 0% | Min ${float(debt.get('minimum', 0))}/mo | Ends {debt.get('promo_deadline', '?')}")
            elif status == 'Baby Step 6':
                st.info(f"{debt['name']} - ${bal:,.2f} at {apr}% | After cards die")
            else:
                st.write(f"**{debt['name']}** - ${bal:,.2f} at {apr}% | Min ${float(debt.get('minimum', 0))}/mo | ${daily:.2f}/day")

        st.divider()
        int_data = [{"Debt": d['name'], "Monthly": float(d.get('daily_interest', 0)) * 30} for d in debts if float(d.get('daily_interest', 0)) > 0]
        if int_data:
            fig = px.bar(pd.DataFrame(int_data), x='Debt', y='Monthly', color='Debt', title='Monthly Interest Burn')
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Deidra's debt tracking coming soon.")


# --- TAB 4: CASH FLOW ---
with tab4:
    st.header("Cash Flow")
    if profile in ("Cody", "Household") and income_data:
        chk_b = income_data.get('check_with_bonus', 0)
        chk_n = income_data.get('check_without_bonus', 0)
        cpm = income_data.get('checks_per_month', 2.17)
        bonus_end = income_data.get('bonus_end_date', '2026-10-12')
        inc_b = chk_b * cpm
        inc_n = chk_n * cpm
        bills_total = sum(float(b['amount']) for b in get_bills("Cody"))
        var = 560 + 800
        outflow = bills_total + var

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("With Bonus")
            st.metric("Income", f"${inc_b:,.0f}")
            st.metric("Outflow", f"${outflow:,.0f}")
            st.metric("Surplus", f"${inc_b - outflow:,.0f}")
        with c2:
            st.subheader("After Bonus")
            st.metric("Income", f"${inc_n:,.0f}")
            st.metric("Outflow", f"${outflow:,.0f}")
            st.metric("Surplus", f"${inc_n - outflow:,.0f}", delta=f"-${inc_b - inc_n:,.0f}")

        st.divider()
        st.subheader("12-Month Forecast")
        bonus_dt = datetime.strptime(bonus_end, '%Y-%m-%d')
        months = []
        for i in range(12):
            md = datetime.now() + timedelta(days=30*i)
            inc = inc_b if md < bonus_dt else inc_n
            months.append({"Month": md.strftime('%b %Y'), "Income": inc, "Expenses": outflow, "Surplus": inc - outflow})
        fdf = pd.DataFrame(months)
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Income', x=fdf['Month'], y=fdf['Income'], marker_color='#2ecc71'))
        fig.add_trace(go.Bar(name='Expenses', x=fdf['Month'], y=fdf['Expenses'], marker_color='#e74c3c'))
        fig.add_trace(go.Scatter(name='Surplus', x=fdf['Month'], y=fdf['Surplus'], mode='lines+markers', marker_color='#3498db'))
        fig.update_layout(barmode='group', height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Add income data to populate.")


# --- TAB 5: UPLOAD ---
with tab5:
    st.header("Upload Financial Data")
    st.caption("Drop bank CSVs and bill PDFs. Nothing runs until you click Analyze.")

    uploaded_files = st.file_uploader("Drop files here", type=['csv', 'pdf'], accept_multiple_files=True, key="uploader")

    if uploaded_files:
        st.session_state['staged_files'] = []
        for f in uploaded_files:
            data = f.read()
            st.session_state['staged_files'].append({'name': f.name, 'data': data, 'size': len(data)})
            f.seek(0)

    staged = st.session_state.get('staged_files', [])
    if staged:
        st.write(f"**{len(staged)} file(s) staged:**")
        for sf in staged:
            st.write(f"{'CSV' if sf['name'].endswith('.csv') else 'PDF'}: {sf['name']} ({sf['size']/1024:.1f} KB)")
        st.divider()

        if st.button("Analyze", type="primary", use_container_width=True):
            from io import BytesIO
            import re as re_mod

            csvs = [s for s in staged if s['name'].lower().endswith('.csv')]
            pdfs = [s for s in staged if s['name'].lower().endswith('.pdf')]

            if csvs:
                st.subheader(f"Transactions ({len(csvs)} files)")
                all_dfs = []
                for sf in csvs:
                    try:
                        parsed = parse_csv_upload(BytesIO(sf['data']))
                        all_dfs.append(parsed)
                        st.success(f"{sf['name']}: {len(parsed)} transactions")
                    except Exception as e:
                        st.error(f"{sf['name']}: {e}")
                if all_dfs:
                    new_data = pd.concat(all_dfs, ignore_index=True)
                    try:
                        ins, skip = save_transactions(new_data, profile=profile.lower())
                        st.success(f"Saved: {ins} new, {skip} duplicates skipped")
                    except Exception as e:
                        st.warning(f"DB: {e}")
                    if not st.session_state.transactions.empty:
                        combined = pd.concat([st.session_state.transactions, new_data], ignore_index=True)
                    else:
                        combined = new_data
                    combined = combined.drop_duplicates(subset=['Date', 'Amount', 'Description'], keep='first')
                    st.session_state.transactions = combined.sort_values('Date', ascending=False).reset_index(drop=True)

            if pdfs:
                st.subheader(f"Statements ({len(pdfs)} files)")
                import pdfplumber
                for sf in pdfs:
                    try:
                        pdf = pdfplumber.open(BytesIO(sf['data']))
                        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
                        pdf.close()
                        if not text.strip():
                            st.warning(f"{sf['name']}: Image-based PDF")
                            continue
                        if "chase" in text.lower() and "cardhelp" in text.lower():
                            amts = [float(a.replace(',','')) for a in re_mod.findall(r'([\d,]+\.\d{2})', text) if 5000 < float(a.replace(',','')) < 50000]
                            bal = max(set(amts), key=amts.count) if amts else 0
                            int_m = re_mod.search(r'PURCHASE INTEREST CHARGE\s*([\d,]+\.\d{2})', text)
                            interest = float(int_m.group(1).replace(',','')) if int_m else 0
                            st.success(f"**Chase** - Balance: ${bal:,.2f} | Interest: ${interest:,.2f}")
                        elif "toyota" in text.lower() and "financial" in text.lower():
                            bm = re_mod.search(r'OutstandingBalance\*?\s*\$?([\d,]+\.?\d*)', text)
                            bal = float(bm.group(1).replace(',','')) if bm else 0
                            dm = re_mod.search(r'PaymentDueDate\s*(\d+/\d+/\d+)', text)
                            due = dm.group(1) if dm else "?"
                            st.success(f"**Toyota** - Balance: ${bal:,.2f} | Due: {due}")
                        elif "wells fargo" in text.lower():
                            amts = [float(a.replace(',','')) for a in re_mod.findall(r'[\d,]+\.\d{2}', text) if 5000 < float(a.replace(',','')) < 50000]
                            bal = amts[0] if amts else 0
                            st.success(f"**Wells Fargo** - Payoff: ${bal:,.2f}")
                        elif "southern" in text.lower() or "sfcu" in text.lower():
                            st.success(f"**Southern FCU** - Statement processed")
                        else:
                            st.info(f"**{sf['name']}** - Unknown type. Add as new bill?")
                            if st.button(f"Add as bill", key=f"addbill_{sf['name']}"):
                                st.session_state['new_bill_from_pdf'] = sf['name']
                    except Exception as e:
                        st.error(f"{sf['name']}: {e}")

            st.session_state['staged_files'] = []
            st.success("Analysis complete. Check other tabs.")
    else:
        st.write("No files staged.")

    st.divider()
    st.subheader("Maintenance")
    if st.button("Re-categorize All", help="Re-apply category rules to all DB transactions"):
        try:
            from transaction_parser import CATEGORY_RULES
            u, t = recategorize_all_transactions(CATEGORY_RULES)
            st.success(f"{u} of {t} re-categorized.")
            st.session_state.db_loaded = False
            st.rerun()
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.subheader("Data Status")
    try:
        st.write(f"**Database:** {get_transaction_count()} transactions")
    except:
        st.write("**Database:** Not connected")
    if not st.session_state.transactions.empty:
        d = st.session_state.transactions
        st.write(f"**Session:** {len(d)} | {d['Date'].min().date()} to {d['Date'].max().date()}")


# --- SIDEBAR ---
with st.sidebar:
    st.header("Quick Stats")
    st.write(f"**Profile:** {profile}")
    st.write(f"**Today:** {datetime.now().strftime('%b %d, %Y')}")
    if income_data:
        bonus_end = income_data.get('bonus_end_date', '2026-10-12')
        days_left = max(0, (datetime.strptime(bonus_end, '%Y-%m-%d') - datetime.now()).days)
        st.metric("Days Until Bonus Ends", days_left)
        st.divider()
        st.write("**Baby Step:** 2")
        st.write("**Target:** Best Buy")
        killed = sum(1 for d in debts if d.get('status') == 'PAID OFF')
        st.write(f"**Debts Killed:** {killed}")
