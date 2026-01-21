import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, date
from fpdf import FPDF

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Plants & Pots Business App",
    layout="wide"
)

# ================= DATABASE =================
conn = sqlite3.connect("business.db", check_same_thread=False)
c = conn.cursor()

# ================= TABLES =================
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT,
    role TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT UNIQUE,
    category TEXT,
    type TEXT,
    quantity INTEGER DEFAULT 0,
    cost_price REAL DEFAULT 0,
    sell_price REAL DEFAULT 0,
    low_stock_limit INTEGER DEFAULT 10
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT,
    quantity INTEGER,
    total REAL,
    cost REAL,
    user TEXT,
    action TEXT,
    date TEXT
)
""")

conn.commit()

# ================= AUTH =================
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ================= DEFAULT ADMIN =================
if not c.execute(
    "SELECT * FROM users WHERE username='admin'"
).fetchone():
    c.execute(
        "INSERT INTO users VALUES (?,?,?)",
        ("admin", hash_password("admin123"), "admin")
    )
    conn.commit()

# ================= LOGIN =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        user = c.execute(
            """
            SELECT username, role
            FROM users
            WHERE username=? AND password_hash=?
            """,
            (u, hash_password(p))
        ).fetchone()

        if user:
            st.session_state.logged_in = True
            st.session_state.user = user[0]
            st.session_state.role = user[1]

            st.session_state.is_admin = user[1] == "admin"
            st.session_state.is_staff = user[1] == "staff"

            st.success(f"Welcome {user[0]} 👋")
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

    st.stop()

# ================= TOP BAR =================
t1, t2 = st.columns([6, 1])
t1.title("🌱 Plants & Pots Business App")

if t2.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

st.caption(
    f"Logged in as **{st.session_state.user.upper()} "
    f"({st.session_state.role.upper()})**"
)

# ================= ADD USER / STAFF =================
if st.session_state.is_admin:
    with st.expander("➕ Add New User / Staff"):
        nu = st.text_input("Username", key="add_user_name")
        npw = st.text_input(
            "Password",
            type="password",
            key="add_user_pass"
        )
        nr = st.selectbox(
            "Role",
            ["staff", "admin"],
            key="add_user_role"
        )

        if st.button("Create User", key="create_user_btn"):
            if not nu or not npw:
                st.error("❌ Username & password required")

            elif c.execute(
                "SELECT 1 FROM users WHERE username=?",
                (nu,)
            ).fetchone():
                st.error("❌ User already exists")

            else:
                c.execute(
                    """
                    INSERT INTO users
                    (username, password_hash, role)
                    VALUES (?,?,?)
                    """,
                    (nu, hash_password(npw), nr)
                )
                conn.commit()
                st.success(
                    f"✅ User '{nu}' created successfully as {nr}"
                )

# ================= TYPE MAP =================
TYPE_MAP = {
    "Plants": [
        "Flower", "Succulent", "Indoor",
        "Outdoor", "Bonsai", "Cactus"
    ],
    "Pots": [
        "Ceramic", "Plastic", "Terracotta",
        "Hanging", "Large", "Small"
    ],
    "Tools": [
        "Cutter", "Pruner", "Shovel", "Sprayer"
    ],
    "Other": ["Other"]
}

# ================= ADD / UPDATE ITEM =================
if st.session_state.role == "admin":
    st.header("➕ Add / Update Item")

    c1, c2 = st.columns(2)

    with c1:
        item = st.text_input("Item Name").strip()
        category = st.selectbox(
            "Category",
            list(TYPE_MAP.keys())
        )
        item_type = st.selectbox(
            "Type",
            TYPE_MAP[category]
        )

    with c2:
        qty = st.number_input(
            "Set Stock Quantity",
            min_value=0,
            step=1
        )
        cost = st.number_input(
            "Cost Price",
            min_value=0.0
        )
        sell = st.number_input(
            "Selling Price",
            min_value=0.0
        )
        low = st.number_input(
            "Low Stock Alert At",
            min_value=1,
            value=10
        )

    if st.button("Save Item") and item:
        c.execute("""
        INSERT INTO inventory
        (item, category, type, quantity,
         cost_price, sell_price, low_stock_limit)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(item) DO UPDATE SET
            quantity=excluded.quantity,
            cost_price=excluded.cost_price,
            sell_price=excluded.sell_price,
            category=excluded.category,
            type=excluded.type,
            low_stock_limit=excluded.low_stock_limit
        """, (
            item,
            category,
            item_type,
            int(qty),
            float(cost),
            float(sell),
            int(low)
        ))

        conn.commit()
        st.success("Item saved successfully")
        st.rerun()
# ================= INVENTORY =================
st.header("📦 Inventory")

inv = pd.read_sql(
    "SELECT * FROM inventory",
    conn
)

if not inv.empty:
    inv["quantity"] = (
        pd.to_numeric(inv["quantity"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    inv["low_stock_limit"] = (
        pd.to_numeric(inv["low_stock_limit"], errors="coerce")
        .fillna(10)
        .astype(int)
    )

st.dataframe(inv, use_container_width=True)

# ================= DELETE ITEM (ADMIN) =================
if st.session_state.role == "admin" and not inv.empty:
    st.subheader("❌ Delete Item")

    di = st.selectbox(
        "Select Item",
        inv["item"]
    )

    if st.button("Delete Item"):
        c.execute(
            "DELETE FROM inventory WHERE item=?",
            (di,)
        )
        conn.commit()
        st.success("Item deleted")
        st.rerun()

# ================= LOW STOCK =================
if not inv.empty:
    low_df = inv[
        (inv["quantity"] > 0) &
        (inv["quantity"] <= inv["low_stock_limit"])
    ]

    if not low_df.empty:
        st.warning("⚠️ Low Stock Alert")
        st.dataframe(
            low_df[["item", "quantity", "low_stock_limit"]],
            use_container_width=True
        )

# ================= SALE / RETURN =================
st.header("🧾 Sale / Return")

if inv.empty:
    st.info("📦 Inventory empty. Pehle item add karein.")

else:
    # ---- Display safe item selector ----
    inv["display"] = (
        inv["item"] +
        " (Stock " +
        inv["quantity"].astype(str) +
        ")"
    )

    it_display = st.selectbox(
        "Item",
        inv["display"]
    )

    row = inv[inv["display"] == it_display].iloc[0]
    item_name = row["item"]

    action = st.radio(
        "Action",
        ["SALE", "RETURN"]
    )

    # ---- Quantity rules ----
    if action == "SALE":
        if row["quantity"] <= 0:
            st.error("❌ Stock ZERO hai. Sale allowed nahi.")
            st.stop()

        qty_tr = st.number_input(
            "Quantity to Sell",
            min_value=1,
            max_value=int(row["quantity"]),
            step=1
        )
    else:
        qty_tr = st.number_input(
            "Quantity to Return",
            min_value=1,
            step=1
        )

    # ---- Submit Transaction ----
    if st.button("Submit Transaction"):
        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        if action == "SALE":
            total = qty_tr * row["sell_price"]
            cost = qty_tr * row["cost_price"]
            new_qty = row["quantity"] - qty_tr
        else:
            total = -qty_tr * row["sell_price"]
            cost = -qty_tr * row["cost_price"]
            new_qty = row["quantity"] + qty_tr

        # ---- Update inventory ----
        c.execute(
            """
            UPDATE inventory
            SET quantity=?
            WHERE item=?
            """,
            (int(new_qty), item_name)
        )

        # ---- Insert transaction ----
        c.execute(
            """
            INSERT INTO sales
            (item, quantity, total, cost,
             user, action, date)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                item_name,
                int(qty_tr),
                float(total),
                float(cost),
                st.session_state.user,
                action,
                now
            )
        )

        conn.commit()
        st.success("✅ Transaction saved successfully")
        st.rerun()

# ================= CHANGE PASSWORD =================
st.subheader("🔑 Change Password")

op = st.text_input(
    "Old Password",
    type="password"
)
npw = st.text_input(
    "New Password",
    type="password"
)
cpw = st.text_input(
    "Confirm New Password",
    type="password"
)

if st.button("Update Password"):
    cur = c.execute(
        """
        SELECT password_hash
        FROM users
        WHERE username=?
        """,
        (st.session_state.user,)
    ).fetchone()

    if hash_password(op) != cur[0]:
        st.error("Old password incorrect")

    elif npw != cpw:
        st.error("Passwords do not match")

    else:
        c.execute(
            """
            UPDATE users
            SET password_hash=?
            WHERE username=?
            """,
            (
                hash_password(npw),
                st.session_state.user
            )
        )
        conn.commit()
        st.success("Password updated successfully")
# ================= DASHBOARD =================
st.header("📊 Dashboard")

sales = pd.read_sql(
    "SELECT * FROM sales",
    conn
)

if not sales.empty:
    sales["date"] = pd.to_datetime(
        sales["date"],
        errors="coerce"
    )
    sales["total"] = pd.to_numeric(
        sales["total"],
        errors="coerce"
    ).fillna(0.0)
    sales["cost"] = pd.to_numeric(
        sales["cost"],
        errors="coerce"
    ).fillna(0.0)

    st.metric(
        "💰 Total Sales",
        f"{sales['total'].sum():.2f}"
    )
    st.metric(
        "📈 Profit",
        f"{(sales['total'] - sales['cost']).sum():.2f}"
    )

    st.subheader("👤 User-wise Sales")
    st.dataframe(
        sales.groupby("user")["total"]
        .sum()
        .reset_index(),
        use_container_width=True
    )

    st.subheader("📅 Daily Sales")
    st.line_chart(
        sales.groupby(
            sales["date"].dt.date
        )["total"].sum()
    )
else:
    st.info("No sales yet")

# ================= TRANSACTION HISTORY =================
st.header("🧾 Transaction History")

sales = pd.read_sql(
    "SELECT * FROM sales",
    conn
)
sales["date"] = pd.to_datetime(
    sales["date"],
    errors="coerce"
)

if st.session_state.is_staff:
    sales_view = sales[
        sales["user"] == st.session_state.user
    ]
else:
    sales_view = sales

if sales_view.empty:
    st.info("No transactions yet")

else:
    sales_view = sales_view.sort_values(
        "date",
        ascending=False
    )

    tx_id = st.selectbox(
        "🔍 Select Transaction",
        sales_view["id"],
        format_func=lambda x: (
            f"ID {x} | "
            f"{sales_view.loc[sales_view.id==x,'item'].values[0]} | "
            f"{sales_view.loc[sales_view.id==x,'action'].values[0]} | "
            f"Rs {sales_view.loc[sales_view.id==x,'total'].values[0]}"
        )
    )

    tx = sales_view[
        sales_view["id"] == tx_id
    ].iloc[0]

    st.markdown("### 🧾 Transaction Details")
    st.write(f"**User:** {tx['user']}")
    st.write(f"**Item:** {tx['item']}")
    st.write(f"**Action:** {tx['action']}")
    st.write(f"**Quantity:** {tx['quantity']}")
    st.write(f"**Total:** Rs {tx['total']}")
    st.write(f"**Date:** {tx['date']}")

    # ================= INVOICE PDF =================
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(
        200, 10,
        "GREEN NURSERY",
        ln=True,
        align="C"
    )
    pdf.ln(5)

    pdf.cell(
        200, 8,
        f"Transaction ID: {tx_id}",
        ln=True
    )
    pdf.cell(
        200, 8,
        f"User: {tx['user']}",
        ln=True
    )
    pdf.cell(
        200, 8,
        f"Item: {tx['item']}",
        ln=True
    )
    pdf.cell(
        200, 8,
        f"Action: {tx['action']}",
        ln=True
    )
    pdf.cell(
        200, 8,
        f"Quantity: {tx['quantity']}",
        ln=True
    )
    pdf.cell(
        200, 8,
        f"Total: Rs {tx['total']}",
        ln=True
    )
    pdf.cell(
        200, 8,
        f"Date: {tx['date']}",
        ln=True
    )

    st.download_button(
        "📄 Download Invoice PDF",
        pdf.output(dest="S").encode("latin-1"),
        file_name=f"invoice_tx_{tx_id}.pdf",
        mime="application/pdf"
    )

# ================= DAILY CLOSING REPORT =================
st.header("🧾 Daily Closing Report")

sales = pd.read_sql(
    "SELECT * FROM sales",
    conn
)
sales["date"] = pd.to_datetime(
    sales["date"],
    errors="coerce"
)
sales["total"] = pd.to_numeric(
    sales["total"],
    errors="coerce"
).fillna(0.0)
sales["cost"] = pd.to_numeric(
    sales["cost"],
    errors="coerce"
).fillna(0.0)

today = st.date_input(
    "Select Date",
    date.today()
)

daily = sales[
    sales["date"].dt.date == today
]

if daily.empty:
    st.warning("No transactions for selected date")

else:
    st.subheader(
        f"📅 Closing Summary: {today}"
    )

    total_sale = daily[
        daily["action"] == "SALE"
    ]["total"].sum()

    total_return = daily[
        daily["action"] == "RETURN"
    ]["total"].sum()

    profit = (
        daily["total"].sum()
        - daily["cost"].sum()
    )

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "💰 Total Sale",
        f"{total_sale:.2f}"
    )
    c2.metric(
        "↩️ Total Return",
        f"{abs(total_return):.2f}"
    )
    c3.metric(
        "📈 Net Profit",
        f"{profit:.2f}"
    )

    st.subheader("👤 User-wise Closing")
    st.dataframe(
        daily.groupby("user")["total"]
        .sum()
        .reset_index()
        .rename(
            columns={"total": "Net Amount"}
        ),
        use_container_width=True
    )

    st.subheader("📋 All Transactions (Day)")
    st.dataframe(
        daily.sort_values(
            "date",
            ascending=False
        ),
        use_container_width=True
    )

# ================= STAFF VIEW =================
if st.session_state.is_staff:
    st.subheader("👤 Your Transactions")

    user_sales = sales[
        sales["user"] == st.session_state.user
    ]

    if user_sales.empty:
        st.info("No transactions found")

    else:
        st.dataframe(
            user_sales.sort_values(
                "date",
                ascending=False
            ),
            use_container_width=True
        )

        st.metric(
            "💰 Your Total Sales",
            f"{user_sales['total'].sum():.2f}"
        )
        st.metric(
            "📈 Your Profit",
            f"{(user_sales['total'] - user_sales['cost']).sum():.2f}"
        )

# ================= ADMIN VIEW =================
if st.session_state.is_admin:
    st.subheader("🛠 All Users Transactions")

    col1, col2 = st.columns(2)

    with col1:
        users = (
            ["ALL"]
            + sorted(
                sales["user"]
                .dropna()
                .unique()
                .tolist()
            )
        )
        selected_user = st.selectbox(
            "Filter by User",
            users
        )

    with col2:
        d1 = st.date_input(
            "From Date",
            date.today().replace(day=1)
        )
        d2 = st.date_input(
            "To Date",
            date.today()
        )

    filtered = sales[
        (sales["date"].dt.date >= d1) &
        (sales["date"].dt.date <= d2)
    ]

    if selected_user != "ALL":
        filtered = filtered[
            filtered["user"] == selected_user
        ]

    if filtered.empty:
        st.warning("No records for selected filters")

    else:
        st.dataframe(
            filtered.sort_values(
                "date",
                ascending=False
            ),
            use_container_width=True
        )

        st.metric(
            "💰 Total Sales",
            f"{filtered['total'].sum():.2f}"
        )
        st.metric(
            "📈 Total Profit",
            f"{(filtered['total'] - filtered['cost']).sum():.2f}"
        )
