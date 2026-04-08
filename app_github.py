import streamlit as st 
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image
import os
import base64
import urllib.parse

journal_file = "trade_journal.csv"

if os.path.exists(journal_file):
    journal_df = pd.read_csv(journal_file)
else:
    journal_df = pd.DataFrame(columns=[
        "position_id",
        "Merits",
        "Demerits",
        "Reason"
    ])

expense_file = "expenses.csv"

if os.path.exists(expense_file):
    expense_df = pd.read_csv(expense_file)
    expense_df["date"] = pd.to_datetime(expense_df["date"], errors="coerce")  # ✅ FIX
else:
    expense_df = pd.DataFrame(columns=[
        "date", "category", "amount", "note"
    ])

APP_PASSWORD = "0581@R"   # 👉 change this to your own password

task_file = "tasks.csv"

if os.path.exists(task_file):
    task_df = pd.read_csv(task_file)

    # ✅ REMOVE unwanted column
    if "date" in task_df.columns:
        task_df = task_df.drop(columns=["date"])
        task_df.to_csv(task_file, index=False)  # overwrite cleaned file
else:
    task_df = pd.DataFrame(columns=[
        "task", "priority", "status", "created_date", "due_date"
    ])

# ------------------------------
# DAILY RECURRING TASKS
# ------------------------------
DAILY_TASKS = [
    {"task": "Review trades", "priority": "High"},
    {"task": "Trade Journal entries update", "priority": "High"},
    {"task": "Analyze strategy performance", "priority": "High"},
    {"task": "Task 5", "priority": "High"},
    {"task": "Task 6", "priority": "High"},
    {"task": "Task 7", "priority": "High"},
    {"task": "Task 8", "priority": "High"},
    {"task": "Task 9", "priority": "High"},
    {"task": "Task 10", "priority": "High"},
    {"task": "Task 11", "priority": "High"},
]

# ------------------------------
# AUTO CREATE DAILY TASKS
# ------------------------------
today = pd.to_datetime(datetime.now().date())

# Convert created_date properly
task_df["created_date"] = pd.to_datetime(task_df["created_date"], errors="coerce")
task_df["due_date"] = pd.to_datetime(task_df["due_date"], errors="coerce")


# Get today's existing tasks
# Get today's existing tasks
today_tasks = task_df[task_df["created_date"] == today]["task"].tolist()

new_tasks = []

for t in DAILY_TASKS:

    # 👉 CASE 1: Task already exists → UPDATE due_date
    mask = (task_df["task"] == t["task"]) & (task_df["status"] != "Completed")

    if mask.any():
        task_df.loc[mask, "due_date"] = today

    # 👉 CASE 2: Task not exists → CREATE
    if t["task"] not in today_tasks:
        new_tasks.append({
            "task": t["task"],
            "priority": t["priority"],
            "status": "Pending",
            "created_date": today,
            "due_date": today
        })

# Add only if missing
if new_tasks:
    task_df = pd.concat([task_df, pd.DataFrame(new_tasks)], ignore_index=True)
    task_df.to_csv(task_file, index=False)

if "edit_expense_row" not in st.session_state:
    st.session_state.edit_expense_row = None

# ------------------------------
# Page Config
# ------------------------------
st.set_page_config(page_title="Algo Station", layout="wide")

st.html("""
<style>

div.stButton > button {
    background-color:#1f2937;
    color:white;
    border-radius:6px;
    border:1px solid #374151;
    padding:4px 6px;
    font-size:14px;
}

div.stButton > button:hover {
    background-color:#2563eb;
    color:white;
}

</style>
""")

# ------------------------------
# Connect to MT5
# ------------------------------
if not mt5.initialize():
    st.error("MT5 Initialization Failed")
    st.stop()

from_date = datetime(2024, 1, 1)
to_date = datetime.now()
deals = mt5.history_deals_get(from_date, to_date)

if deals is None or len(deals) == 0:
    st.warning("No trade history found.")
    st.stop()

df = pd.DataFrame(deals, columns=deals[0]._asdict().keys())
df['entry_datetime'] = pd.to_datetime(df['time'], unit='s')
df = df[df['entry'] == 1]  # only closing trades

# Combine partial closes
df = df.groupby('position_id').agg({
    'profit':'sum',
    'commission':'sum',
    'swap':'sum',
    'entry_datetime':'max',
    'magic':'first'
}).reset_index()

df['net_profit'] = df['profit'] + df['commission'] + df['swap']
df = df.sort_values('entry_datetime')

df = df.merge(journal_df, on="position_id", how="left")

df["Merits"] = df["Merits"].fillna("")
df["Demerits"] = df["Demerits"].fillna("")
df["Reason"] = df["Reason"].fillna("")

df['mode'] = df['magic'].apply(lambda x: "Manual" if x == 0 else "Algo")

# ------------------------------
# Strategy Name Mapping
# ------------------------------
strategy_map = {
    0: "Manual Trades",
    60002: "EMA Pullback",
    60004: "EMA 50 Pullback",
    70004: "EMA Plus Fib 90",
    20250727: "EM                                                                                                                                                                                             A Pullback",
    500100: "Scalping Pro",
    70003: "Swing Master",
    500200: "EMA Pullback",
    10815: "Pivot Plus Stoch RSI",
    20250806: "Unknown",
    10816: "FakeBO",
    108108: "Pivot Double Tap",
    107108: "Liquidity Pulse Scalper",
}

df['strategy_name'] = df['magic'].map(strategy_map)

# If any magic not in map → show as Magic_xxxx
df['strategy_name'] = df.apply(
    lambda row: row['strategy_name'] 
    if pd.notna(row['strategy_name']) 
    else f"Magic_{int(row['magic'])}",
    axis=1
)

# ------------------------------
# Top Ribbon: Logo + Heading + Overall PnL
# ------------------------------
logo_path = r"D:\PL\Algostation\Algo_station_Dashboard\logo.png"
if not os.path.exists(logo_path):
    st.error(f"Logo file not found at: {logo_path}")
    st.stop()

# Encode logo to base64
with open(logo_path, "rb") as f:
    logo_data = f.read()
logo_b64 = base64.b64encode(logo_data).decode()

overall_pnl = float(df['net_profit'].sum() if not df['net_profit'].empty else 0)

# Determine PnL color
pnl_color = "#16a34a" if overall_pnl >= 0 else "#dc2626"

st.html(f"""
<div style="
    width:100%;
    background-color:#111827;
    padding:18px 35px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    border-radius:12px;
">

    <div style="display:flex; align-items:center; gap:15px;">
        <img src="data:image/png;base64,{logo_b64}" width="55">
        <div style="
            font-size:30px;
            font-weight:800;
            letter-spacing:1px;
            color:white;
        ">
            ALGO STATION 
        </div>
    </div>

    <div style="
        background:white;
        padding:5px 5px;
        border-radius:12px;
        font-size:20px;
        font-weight:800;
        font-family:monospace;
        color:{pnl_color};
        box-shadow:0 6px 20px rgba(0,0,0,0.25);
    ">
        {overall_pnl:,.2f} $
    </div>

</div>
""")

# ------------------------------
# Daily PnL for Calendar Heatmap
# ------------------------------

df['date'] = df['entry_datetime'].dt.date

daily_pnl = df.groupby('date')['net_profit'].sum().reset_index()
daily_pnl['date'] = pd.to_datetime(daily_pnl['date'])

daily_pnl['year'] = daily_pnl['date'].dt.year
daily_pnl['week'] = daily_pnl['date'].dt.isocalendar().week
daily_pnl['weekday'] = daily_pnl['date'].dt.weekday

def monthly_trading_calendar(df, selected_strategy):

    if selected_strategy != "All":
        df = df[df["strategy_name"] == selected_strategy]

    df['date'] = df['entry_datetime'].dt.date

    daily = df.groupby('date')['net_profit'].sum().reset_index()
    daily['date'] = pd.to_datetime(daily['date'])

    daily['day'] = daily['date'].dt.day
    daily['month'] = daily['date'].dt.month
    daily['year'] = daily['date'].dt.year

    # Month selector
    months = daily['date'].dt.to_period("M").astype(str).unique()
    selected_month = st.selectbox("Select Month", months[::-1])

    month_df = daily[daily['date'].dt.to_period("M").astype(str) == selected_month]

    month_df['week'] = month_df['date'].dt.isocalendar().week
    month_df['weekday'] = month_df['date'].dt.weekday

    fig = go.Figure()

    fig.add_trace(
        go.Heatmap(
            x=month_df['weekday'],
            y=month_df['week'],
            z=month_df['net_profit'],
            text=month_df['date'],
            hovertemplate=
            "<b>Date:</b> %{text}<br>" +
            "<b>PnL:</b> %{z:.2f}$<extra></extra>",
            colorscale=[
                [0,"#7f1d1d"],
                [0.25,"#dc2626"],
                [0.5,"#f3f4f6"],
                [0.75,"#16a34a"],
                [1,"#14532d"]
            ],
            colorbar=dict(title="Daily PnL")
        )
    )

    fig.update_layout(
        title="Monthly Trading Calendar",
        xaxis=dict(
            tickmode='array',
            tickvals=[0,1,2,3,4,5,6],
            ticktext=['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        ),
        height=450
    )

    st.plotly_chart(fig, use_container_width=True)

    # Click day simulation
    selected_day = st.date_input("View trades for date")

    day_trades = df[df['entry_datetime'].dt.date == selected_day]

    if not day_trades.empty:
        st.subheader(f"Trades on {selected_day}")
        st.dataframe(day_trades.sort_values('entry_datetime'))

def calendar_heatmap(df, start_date, end_date):

    df = df.copy()
    df['date'] = pd.to_datetime(df['entry_datetime']).dt.floor('D')

    daily = df.groupby('date')['net_profit'].sum().reset_index()
    daily['date'] = pd.to_datetime(daily['date'])

    all_days = pd.date_range(start=start_date, end=end_date)

    cal = pd.DataFrame({'date': all_days})
    cal = cal.merge(daily, on='date', how='left')
    cal['net_profit'] = cal['net_profit'].fillna(0)

    cal['date'] = pd.to_datetime(cal['date'])
    cal['month'] = cal['date'].dt.month
    cal['month_name'] = cal['date'].dt.strftime("%b")
    cal['weekday'] = cal['date'].dt.weekday
    cal['week'] = cal['date'].dt.isocalendar().week

    # Normalize colors properly
    max_profit = cal['net_profit'].max()
    max_loss = cal['net_profit'].min()

    cal['color_val'] = cal['net_profit']

    months = pd.date_range(start=start_date, periods=12, freq="MS")
    titles = [m.strftime("%b-%y") for m in months]

    fig = make_subplots(
        rows=2,
        cols=6,
        subplot_titles=titles
    )

    colorscale = [
        [0.0, "#7f1d1d"],
        [0.25, "#dc2626"],
        [0.5, "#ffffff"],
        [0.75, "#86efac"],
        [1.0, "#166534"]
    ]

    for m in range(1,13):

        month_df = cal[cal['month']==m]

        if month_df.empty:
            continue

        row = (m-1)//6 + 1
        col = (m-1)%6 + 1

        fig.add_trace(
            go.Heatmap(
                x=month_df['week'],
                y=month_df['weekday'],
                z=month_df['color_val'],
                text=month_df['date'],
                zmid=0,
                colorscale=colorscale,
                showscale=False,
                hovertemplate=
                "<b>Date:</b> %{text}<br>" +
                "<b>PnL:</b> %{z:.2f}$<extra></extra>"
            ),
            row=row,
            col=col
        )

    fig.update_layout(
        height=650,
        title="Trading Calendar",
        margin=dict(t=50)
    )

    fig.update_yaxes(
        tickmode='array',
        tickvals=[0,1,2,3,4],
        ticktext=["Mon","Tue","Wed","Thu","Fri"]
    )

    return fig   

def editable_trade_table(trades):

    # Track which row is being edited
    if "edit_row" not in st.session_state:
        st.session_state.edit_row = None

    # ---------- TABLE HEADER ----------
    header = st.columns([1.6,2,1.2,2.2,2.2,2.5,0.7,0.7])

    header[0].markdown("**Position**")
    header[1].markdown("**Strategy**")
    header[2].markdown("**PnL**")
    header[3].markdown("**Merits**")
    header[4].markdown("**Demerits**")
    header[5].markdown("**Reason**")
    header[6].markdown("**Edit**")
    header[7].markdown("**Save**")

    #st.markdown("---")
    st.markdown("<hr style='margin:6px 0'>", unsafe_allow_html=True)

    for i, row in trades.iterrows():

        pos_id = row["position_id"]

        cols = st.columns([1.6,2,1.2,2.2,2.2,2.5,0.7,0.7])

        # -------- POSITION --------
        cols[0].write(pos_id)

        # -------- STRATEGY --------
        cols[1].write(row["strategy_name"])

        # -------- PNL COLOR --------
        pnl = round(row["net_profit"],2)

        pnl_color = "green" if pnl >= 0 else "red"

        cols[2].markdown(
            f"<span style='color:{pnl_color}; font-weight:600'>{pnl}</span>",
            unsafe_allow_html=True
        )

        # -------- EDIT MODE --------
        editing = st.session_state.edit_row == pos_id

        merits = cols[3].text_input(
            "",
            value=row["Merits"],
            key=f"merits_{pos_id}",
            disabled=not editing,
            label_visibility="collapsed"
        )

        demerits = cols[4].text_input(
            "",
            value=row["Demerits"],
            key=f"demerits_{pos_id}",
            disabled=not editing,
            label_visibility="collapsed"
        )

        reason = cols[5].text_input(
            "",
            value=row["Reason"],
            key=f"reason_{pos_id}",
            disabled=not editing,
            label_visibility="collapsed"
        )

        # -------- EDIT BUTTON --------
        if cols[6].button("✏", key=f"edit_{pos_id}"):

            st.session_state.edit_row = pos_id

        # -------- SAVE BUTTON --------
        if cols[7].button("✔", key=f"save_{pos_id}"):

            global journal_df

            new_row = pd.DataFrame([{
                "position_id": pos_id,
                "Merits": merits,
                "Demerits": demerits,
                "Reason": reason
            }])

            journal_df = journal_df[
                journal_df["position_id"] != pos_id
            ]

            journal_df = pd.concat([journal_df,new_row])

            journal_df.to_csv("trade_journal.csv", index=False)

            st.session_state.edit_row = None

            st.success("Saved")

        st.markdown("---")

# ------------------------------
# Professional Navigation Ribbon
# ------------------------------

# ------------------------------
# Simple Navigation Ribbon (TEXT ONLY)
# ------------------------------
# ------------------------------
# Professional Clickable Navigation Ribbon (Active Highlight)
# ------------------------------

pages = [
    "Dashboard Overview",
    "Today's Performance",
    "Strategy Analytics",
    "Weekly & Monthly",
    "Trade Journal",
    "Expense Manager",     # NEW
    "Task Manager"
]

query_params = st.query_params

if "page" in query_params:
    selected_page = query_params["page"]
    if isinstance(selected_page, list):
        selected_page = selected_page[0]
else:
    selected_page = "Dashboard Overview"

nav_html = """
<style>
.navbar {
    width:100%;
    background-color:rgba(17, 24, 39, 0.85);
    backdrop-filter: blur(6px);
    padding:10px 20px;
    border-radius:6px;
    margin-bottom:25px;
    text-align:center;
}

.navbar a {
    color:white;
    text-decoration:none;
    font-weight:600;
    font-size:15px;
    margin:0 18px;
    padding:6px 14px;
    border-radius:5px;
    transition:0.2s;
}

.navbar a:hover {
    background-color:#374151;
    color:white;
}

.navbar .active {
    background-color:#2563eb;
    color:white;
}
</style>

<div class="navbar">
"""

for page in pages:
    encoded_page = urllib.parse.quote(page)
    if page == selected_page:
        nav_html += f'<a href="?page={encoded_page}" target="_self" class="active">{page}</a>'
    else:
        nav_html += f'<a href="?page={encoded_page}" target="_self">{page}</a>'

nav_html += "</div>"

st.markdown(nav_html, unsafe_allow_html=True)

# ------------------------------
# DASHBOARD OVERVIEW
# ------------------------------
if selected_page == "Dashboard Overview":
    df['equity'] = df['net_profit'].cumsum()
    df['peak'] = df['equity'].cummax()
    df['drawdown'] = df['equity'] - df['peak']

    col1, col2 = st.columns([1,3])

    # Pie Chart (Manual vs Algo)
    mode_summary = df.groupby('mode')['net_profit'].sum().reset_index()
    if not mode_summary.empty:
        pie = px.pie(
            mode_summary,
            names='mode',
            values=mode_summary['net_profit'].abs(),
            title="Manual vs Algo Performance",
            color_discrete_sequence=px.colors.qualitative.Set2,
            custom_data=['net_profit']
        )
        pie.update_traces(
            hovertemplate='%{label}: %{customdata[0]:.2f}<br>%{percent}',
            textinfo='label+percent'
        )
        col1.plotly_chart(pie, use_container_width=True)
    else:
        col1.warning("No data available for pie chart.")

    # Equity Curve
    col2.markdown(
        "<h3 style='text-align: center;'>Equity Curve</h3>",
        unsafe_allow_html=True
    )
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=df['entry_datetime'], y=df['equity'], name='Equity', line=dict(color='green')))
    col2.plotly_chart(fig_eq, use_container_width=True)

    # Drawdown below
    st.subheader("Drawdown")
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=df['entry_datetime'], y=df['drawdown'], name='Drawdown', line=dict(color='red')))
    st.plotly_chart(fig_dd, use_container_width=True)

    # ------------------------------
    # Monthly Performance Badge
    # ------------------------------

    monthly_perf = df.copy()
    monthly_perf['month'] = monthly_perf['entry_datetime'].dt.to_period("M")

    monthly_summary = monthly_perf.groupby('month').agg(
        pnl=('net_profit','sum'),
        trades=('position_id','count')
    ).reset_index()

    last_month = monthly_summary.iloc[-1]

    badge_color = "green" if last_month['pnl'] >= 0 else "red"

    st.markdown(f"""
    <div style="
    padding:15px;
    border-radius:10px; 
    background-color:#111827;
    color:white;
    font-size:18px;
    font-weight:600;
    display:inline-block;
    margin-bottom:20px;
    ">
    📅 Last Month Performance<br>
    PnL: <span style="color:{badge_color}">{last_month['pnl']:.2f}$</span> |
    Trades: {last_month['trades']}
    </div>
    """, unsafe_allow_html=True)

    # ------------------------------
    # Strategy Calendar
    # ------------------------------

    # ------------------------------
    # Date Range Selector
    # ------------------------------

    default_start = datetime.now().date() - pd.DateOffset(months=12)
    default_end = datetime.now().date()

    date_range = st.date_input(
        "Select Date Range",
        [default_start, default_end]
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = default_start
        end_date = default_end

    calendar_df = df[
        (df['entry_datetime'].dt.date >= start_date) &
        (df['entry_datetime'].dt.date <= end_date)
    ]

    # ------------------------------
    # Performance Metrics
    # ------------------------------

    total_pnl = calendar_df['net_profit'].sum()
    total_trades = len(calendar_df)

    accuracy = (
        (calendar_df['net_profit'] > 0).mean() * 100
        if total_trades > 0 else 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("PnL", f"{total_pnl:.2f} $")
    col2.metric("Trades", total_trades)
    col3.metric("Accuracy", f"{accuracy:.2f}%")

    # ------------------------------
    # Daily Heatmap Data
    # ------------------------------

    #calendar_df['date'] = calendar_df['entry_datetime'].dt.date
    calendar_df['date'] = pd.to_datetime(calendar_df['entry_datetime']).dt.floor('D')

    daily_calendar = calendar_df.groupby('date')['net_profit'].sum().reset_index()

    daily_calendar['date'] = pd.to_datetime(daily_calendar['date'])
    daily_calendar['week'] = daily_calendar['date'].dt.isocalendar().week
    daily_calendar['weekday'] = daily_calendar['date'].dt.weekday

    # ------------------------------
    # Calendar Heatmap
    # ------------------------------



    fig = calendar_heatmap(calendar_df, start_date, end_date)
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# TODAY'S PERFORMANCE
# ------------------------------
elif selected_page == "Today's Performance":
    today = datetime.now().date()
    df['date'] = df['entry_datetime'].dt.date
    today_trades = df[df['date'] == today]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total PnL", round(today_trades['net_profit'].sum(),2))
    col2.metric("Total Trades", len(today_trades))
    col3.metric("Win Rate",
        round((today_trades['net_profit'] > 0).mean()*100,2)
        if len(today_trades)>0 else 0
    )

    editable_trade_table(
        today_trades.sort_values('entry_datetime', ascending=False)
    )

# ------------------------------
# STRATEGY ANALYTICS
# ------------------------------
elif selected_page == "Strategy Analytics":

    df_strategy = df.copy()

    # =========================
    # TABLE SUMMARY
    # =========================
    summary = df_strategy.groupby('strategy_name').agg(
        Total_Trades=('position_id','count'),
        Total_Net_Profit=('net_profit','sum'),
        Avg_Profit=('net_profit','mean')
    ).reset_index()

    win_rate = df_strategy.groupby('strategy_name')['net_profit'].apply(
        lambda x: (x > 0).sum() / len(x) * 100
    ).reset_index(name='Win_Rate_%')

    summary = summary.merge(win_rate, on='strategy_name')

    def calculate_max_dd(x):
        equity = x['net_profit'].cumsum()
        peak = equity.cummax()
        dd = equity - peak
        return dd.min()

    max_dd = df_strategy.groupby('strategy_name').apply(
        calculate_max_dd
    ).reset_index(name='Max_Drawdown')

    summary = summary.merge(max_dd, on='strategy_name')

    summary = summary.sort_values('Total_Net_Profit', ascending=False)

    st.dataframe(summary)

    # =========================
    # STRATEGY EQUITY CURVE
    # =========================
    st.subheader("Strategy Equity Curve")

    df_strategy = df_strategy.sort_values('entry_datetime')
    df_strategy['strategy_equity'] = df_strategy.groupby(
        'strategy_name'
    )['net_profit'].cumsum()

    fig = px.line(
        df_strategy,
        x='entry_datetime',
        y='strategy_equity',
        color='strategy_name'
    )

    st.plotly_chart(fig, use_container_width=True)
# Weekly and monthly 

elif selected_page == "Weekly & Monthly":

    if df.empty:
        st.warning("No data available.")
    else:
        df['entry_datetime'] = pd.to_datetime(df['entry_datetime'])

        # Create Year-Month and Year-Week properly
        df['year_month'] = df['entry_datetime'].dt.to_period('M').astype(str)
        df['year_week'] = df['entry_datetime'].dt.to_period('W').astype(str)

        # =========================
        # STRATEGY MONTHLY MATRIX
        # =========================

        df['month'] = df['entry_datetime'].dt.to_period('M')

        strategy_month = df.groupby(['strategy_name', 'month'])['net_profit'].sum().reset_index()

        # Pivot → rows = strategy, columns = months
        strategy_pivot = strategy_month.pivot(
            index='strategy_name',
            columns='month',
            values='net_profit'
        )

        # Sort latest month first
        strategy_pivot = strategy_pivot.sort_index(axis=1, ascending=False)

        # Keep only last 12 months
        strategy_pivot = strategy_pivot.iloc[:, :12]

        # Format columns as readable names
        strategy_pivot.columns = [str(col) for col in strategy_pivot.columns]

        # Fill NaN
        strategy_pivot = strategy_pivot.fillna(0)
        

        # Create layout: LEFT = Monthly Table | RIGHT = Weekly Chart
        col_left, col_right = st.columns([1, 1.5])

        # =========================
        # MONTHLY TABLE (LEFT SIDE)
        # =========================
        with col_left:
            st.subheader("Monthly Performance")

            monthly = df.groupby('year_month').agg(
                Total_Trades=('position_id', 'count'),
                Net_Profit=('net_profit', 'sum')
            ).reset_index()

            # Sort by most recent month on top
            monthly = monthly.sort_values('year_month', ascending=False)

            st.dataframe(monthly, use_container_width=True)

        # =========================
        # WEEKLY GRAPH (RIGHT SIDE)
        # =========================
        with col_right:

            st.subheader("Strategy-wise Monthly Performance")

            st.dataframe(strategy_pivot, use_container_width=True)

        st.subheader("Last 52 Weeks Performance")

        weekly = df.groupby('year_week')['net_profit'].sum().reset_index()

        # Sort properly by week
        weekly = weekly.sort_values('year_week')

        # Take only last 52 weeks
        weekly = weekly.tail(52)

        if not weekly.empty:
            fig_week = px.bar(
                weekly,
                x='year_week',
                y='net_profit',
                title="Net Profit - Last 52 Weeks"
            )
            fig_week.update_layout(
                xaxis_title="Week",
                yaxis_title="Net Profit",
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig_week, use_container_width=True)
        else:
            st.info("No weekly data available.")        

# ------------------------------
# TRADE JOURNAL
# ------------------------------
elif selected_page == "Trade Journal":
    st.subheader("Full Trade Journal")
    mode_filter = st.selectbox("Filter by Mode", ["All","Manual","Algo"])
    if mode_filter != "All":
        filtered_df = df[df['mode'] == mode_filter]
    else:
        filtered_df = df

    editable_trade_table(
        filtered_df.sort_values('entry_datetime', ascending=False)
    )

elif selected_page == "Expense Manager":

    st.subheader("💸 Expense Manager")


    # ---- INIT SESSION STATE ----
    if "exp_date" not in st.session_state:
        st.session_state.exp_date = datetime.now()

    if "exp_category" not in st.session_state:
        st.session_state.exp_category = "Order Food"

    if "exp_amount" not in st.session_state:
        st.session_state.exp_amount = 0.0

    if "exp_note" not in st.session_state:
        st.session_state.exp_note = ""

    # ---- ADD EXPENSE ----
    with st.expander("Add Expense"):

        col1, col2, col3, col4 = st.columns(4)

        date = col1.date_input("Date", key="exp_date")

        category = col2.selectbox(
            "Category",
            [
                "Order Food",
                "Grocery Fruits and Veg",
                "Grocery Bareilly",
                "Grocery Shop",
                "Travel",
                "Shanu",
                "Rushika",
                "Bill",
                "Trading Cost",
                "Other"
            ],
            key="exp_category"
        )

        amount = col3.number_input(
            "Amount",
            min_value=0.0,
            step=10.0,
            key="exp_amount"
        )

        note = col4.text_input("Note", key="exp_note")

        if st.button("Add Expense"):

            new_row = pd.DataFrame([{
                "date": pd.to_datetime(st.session_state.exp_date),
                "category": st.session_state.exp_category,
                "amount": st.session_state.exp_amount,
                "note": st.session_state.exp_note
            }])

            expense_df = pd.concat([expense_df, new_row])
            expense_df.to_csv(expense_file, index=False)

            st.success("Expense Added ✅")

            st.rerun()   # 🔥 IMPORTANT

    


    # ---- SUMMARY ----
    st.subheader("📊 Expense Summary")

    total_expense = expense_df["amount"].sum()
    st.metric("Total Expense", f"{total_expense:.2f}")

    # Category Breakdown
    cat_summary = expense_df.groupby("category")["amount"].sum().reset_index()

    fig = px.pie(cat_summary, names="category", values="amount", title="Category Breakdown")
    st.plotly_chart(fig, use_container_width=True)

    # Table
    st.subheader("📋 Expense Details")

    # Ensure index reset
    expense_df = expense_df.reset_index(drop=True)

    if "auth_expense" not in st.session_state:
        st.session_state.auth_expense = False

    st.subheader("🔐 Secure Access")

    col_pass, col_btn = st.columns([2,1])

    password_input = col_pass.text_input("Enter Password", type="password")

    if col_btn.button("Unlock"):
        if password_input == APP_PASSWORD:
            st.session_state.auth_expense = True
            st.success("Access Granted ✅")
        else:
            st.error("Wrong Password ❌")

    if st.session_state.auth_expense:
        st.info("🔓 Editing Enabled")
    else:
        st.warning("🔒 Editing Locked")

    # ---- HEADER ROW ----
    header = st.columns([1.2, 1.5, 1, 2, 0.5, 0.5, 0.5])

    header[0].markdown("**Date**")
    header[1].markdown("**Category**")
    header[2].markdown("**Amount**")
    header[3].markdown("**Note**")
    header[4].markdown("**Edit**")
    header[5].markdown("**Save**")
    header[6].markdown("**Delete**")

    st.markdown("<hr>", unsafe_allow_html=True)

    for i, row in expense_df.iterrows():

        cols = st.columns([1.2, 1.5, 1, 2, 0.5, 0.5, 0.5])

        editing = st.session_state.edit_expense_row == i

        # ---- DATE ----
        date_val = cols[0].date_input(
            "",
            value=pd.to_datetime(row["date"]),
            key=f"date_{i}",
            disabled=not editing
        )

        # ---- CATEGORY ----
        category_val = cols[1].selectbox(
            "",
            [
                "Order Food",
                "Grocery Fruits and Veg",
                "Grocery Bareilly",
                "Grocery Shop",
                "Travel",
                "Shanu",
                "Rushika",
                "Bill",
                "Trading Cost",
                "Other"
            ],
            index=[
                "Order Food",
                "Grocery Fruits and Veg",
                "Grocery Bareilly",
                "Grocery Shop",
                "Travel",
                "Shanu",
                "Rushika",
                "Bill",
                "Trading Cost",
                "Other"
            ].index(row["category"]) if row["category"] in [
                "Order Food",
                "Grocery Fruits and Veg",
                "Grocery Bareilly",
                "Grocery Shop",
                "Travel",
                "Shanu",
                "Rushika",
                "Bill",
                "Trading Cost",
                "Other"
            ] else 0,
            key=f"cat_{i}",
            disabled=not editing
        )

        # ---- AMOUNT ----
        amount_val = cols[2].number_input(
            "",
            value=float(row["amount"]),
            key=f"amt_{i}",
            disabled=not editing
        )

        # ---- NOTE ----
        note_val = cols[3].text_input(
            "",
            value=row["note"],
            key=f"note_{i}",
            disabled=not editing
        )

        # ---- EDIT BUTTON ----
        if cols[4].button("✏", key=f"edit_exp_{i}"):
            if st.session_state.auth_expense:
                st.session_state.edit_expense_row = i
            else:
                st.error("Enter Password First 🔒")

        # ---- SAVE BUTTON ----
        if cols[5].button("✔", key=f"save_exp_{i}"):
            if not st.session_state.auth_expense:
                st.error("Unauthorized 🔒")
                st.stop()

            expense_df.loc[i] = [
                pd.to_datetime(date_val),
                category_val,
                amount_val,
                note_val
            ]

            expense_df.to_csv(expense_file, index=False)

            st.session_state.edit_expense_row = None

            st.success("Updated ✅")
            st.session_state.auth_expense = False
            st.rerun()

        # ---- DELETE BUTTON ----
        if cols[6].button("❌", key=f"del_exp_{i}"):
            if not st.session_state.auth_expense:
                st.error("Unauthorized 🔒")
                st.stop()

            expense_df = expense_df.drop(i).reset_index(drop=True)

            expense_df.to_csv(expense_file, index=False)

            st.success("Deleted ✅")
            st.session_state.auth_expense = False
            st.rerun()

        st.markdown("---")

elif selected_page == "Task Manager":

    st.subheader("📋 Task Manager")

    # ---- ADD TASK ----
    with st.expander("Add Task"):

        col1, col2, col3 = st.columns(3)

        task = col1.text_input("Task")
        priority = col2.selectbox("Priority", ["High", "Medium", "Low"])
        due_date = col3.date_input("Due Date", datetime.now())

        if st.button("Add Task"):

            new_task = pd.DataFrame([{
                "task": task,
                "priority": priority,
                "status": "Pending",
                "created_date": datetime.now().date(),
                "due_date": due_date
            }])

            task_df = pd.concat([task_df, new_task])
            task_df.to_csv(task_file, index=False)

            st.success("Task Added ✅")
            st.rerun()

    # ---- FILTER ----
    filter_status = st.selectbox("Filter", ["All", "Pending", "Completed"])

    # ---- SORTING LOGIC ----
    today = pd.to_datetime(datetime.now().date())

    # Convert due_date properly
    task_df["due_date"] = pd.to_datetime(task_df["due_date"], errors="coerce")
    # 👉 Replace missing due_date with None (important)
    task_df["due_date"] = task_df["due_date"].where(task_df["due_date"].notna(), None)

    def get_task_order(row):
        if row["status"] == "Completed":
            return 5  # Completed last
        if row["due_date"] < today:
            return 1  # Overdue
        elif row["due_date"] == today:
            return 2  # Today
        elif row["due_date"] == today + pd.Timedelta(days=1):
            return 3  # Tomorrow
        else:
            return 4  # Future

    # Apply sorting number
    task_df["sort_order"] = task_df.apply(get_task_order, axis=1)

    # Sort dataframe
    task_df = task_df.sort_values(
        by=["sort_order", "due_date"],
        ascending=[True, True]
    )

    if filter_status != "All":
        display_df = task_df[task_df["status"] == filter_status]
    else:
        display_df = task_df.copy()

    if "edit_task_row" not in st.session_state:
        st.session_state.edit_task_row = None

    # ---- TASK TABLE ----
    for i, row in display_df.iterrows():

        cols = st.columns([3,1,1,1.5,1,1,1,1])

        editing = st.session_state.edit_task_row == i

        # ---- TASK NAME ----
        task_val = cols[0].text_input(
            "",
            value=row["task"],
            key=f"task_{i}",
            disabled=not editing
        )

        # ---- PRIORITY ----
        priority_val = cols[1].selectbox(
            "",
            ["High", "Medium", "Low"],
            index=["High","Medium","Low"].index(row["priority"]),
            key=f"priority_{i}",
            disabled=not editing
        )

        # ---- STATUS (IMPORTANT CHANGE) ----
        status_val = cols[2].selectbox(
            "",
            ["Pending", "Completed"],
            index=["Pending","Completed"].index(row["status"]),
            key=f"status_{i}",
            disabled=not editing
        )

        # ---- DUE DATE ----
        due_date_val = cols[3].date_input(
            "",
            value = row["due_date"] if pd.notna(row["due_date"]) else None,
            key=f"due_{i}",
            disabled=not editing
        )

        # ---- EDIT BUTTON ----
        if cols[4].button("✏", key=f"edit_task_{i}"):
            st.session_state.edit_task_row = i

        # ---- SAVE BUTTON ----
        if cols[5].button("✔", key=f"save_task_{i}"):

            task_df.at[i, "task"] = task_val
            task_df.at[i, "priority"] = priority_val
            task_df.at[i, "status"] = status_val
            task_df.at[i, "created_date"] = row["created_date"]
            task_df.at[i, "due_date"] = pd.to_datetime(due_date_val) if due_date_val else None

            task_df.to_csv(task_file, index=False)

            st.session_state.edit_task_row = None
            st.success("Updated ✅")
            st.rerun()

        # ---- DELETE BUTTON ----
        if cols[6].button("❌", key=f"delete_task_{i}"):

            task_df = task_df.drop(i).reset_index(drop=True)
            task_df.to_csv(task_file, index=False)

            st.success("Deleted ✅")
            st.rerun()

    st.markdown("---")

    st.dataframe(task_df.sort_values("created_date", ascending=False))