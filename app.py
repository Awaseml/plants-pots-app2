import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime, date
from fpdf import FPDF

import psycopg2
import streamlit as st

def get_conn():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets["DB_PORT"]
    )

conn = get_conn()
c = conn.cursor()

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Plants & Pots Business App",
    layout="wide"
)

# ================= DATABASE =================



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
# ================= SECURE LOGIN + OTP =================
import random
import smtplib
from email.message import EmailMessage

# ---------- SECRETS ----------
EMAIL_SENDER = st.secrets["email"]["sender"]
EMAIL_PASS   = st.secrets["email"]["password"]

ADMIN_USER = st.secrets["admin"]["username"]
ADMIN_PASS = st.secrets["admin"]["password"]



# ---------- SESSION FLAGS ----------
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "is_staff" not in st.session_state:
    st.session_state.is_staff = False
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "step" not in st.session_state:
    st.session_state.step = "login"
if "otp" not in st.session_state:
    st.session_state.otp = ""
if "pwd_mode" not in st.session_state:
    st.session_state.pwd_mode = None   # None | change | forgot
if "pwd_user" not in st.session_state:
    st.session_state.pwd_user = ""
if "pwd_otp_login" not in st.session_state:
    st.session_state.pwd_otp_login = ""

# ---------- SEND LOGIN OTP ----------
def send_otp(to_email):
    otp = str(random.randint(100000, 999999))
    st.session_state.otp = otp

    msg = EmailMessage()
    msg.set_content(f"Your login OTP is: {otp}")
    msg["Subject"] = "Plants & Pots – Login OTP"
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASS)
        server.send_message(msg)

# ---------- SEND PASSWORD OTP ----------
def send_password_otp():
    otp = str(random.randint(100000, 999999))
    st.session_state.pwd_otp_login = otp

    msg = EmailMessage()
    msg.set_content(f"Your password OTP is: {otp}")
    msg["Subject"] = "Plants & Pots – Password OTP"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_SENDER   # abhi admin email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASS)
        server.send_message(msg)

# =====================================================
# ================= LOGIN SCREEN ======================
# =====================================================
# ================= LOGIN SCREEN ======================
# =====================================================
if not st.session_state.logged_in and st.session_state.step == "login":

    # -------- NORMAL LOGIN --------
    if st.session_state.pwd_mode is None:

        st.title("🔐 Secure Login")

        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            user = c.execute(
                "SELECT username, role, password_hash FROM users WHERE username=?",
                (u,)
            ).fetchone()

            if user and hash_password(p) == user[2]:
                st.session_state.user = user[0]
                st.session_state.role = user[1]
                st.session_state.is_admin = user[1] == "admin"
                st.session_state.is_staff = user[1] == "staff"

                send_otp(EMAIL_SENDER)
                st.session_state.step = "otp"
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔁 Change Password"):
                st.session_state.pwd_mode = "change"
                st.rerun()
        with c2:
            if st.button("❓ Forgot Password"):
                st.session_state.pwd_mode = "forgot"
                st.rerun()

        st.stop()

    # -------- CHANGE PASSWORD --------
    if st.session_state.pwd_mode == "change":

        st.title("🔁 Change Password")

        uname = st.text_input("Username")
        old_pw = st.text_input("Old Password", type="password")

        if st.button("Send OTP"):
            user = c.execute(
                "SELECT password_hash FROM users WHERE username=?",
                (uname,)
            ).fetchone()

            if not user or hash_password(old_pw) != user[0]:
                st.error("❌ Invalid credentials")
                st.stop()

            st.session_state.pwd_user = uname
            send_password_otp()
            st.success("📩 OTP sent")
            st.stop()

        otp = st.text_input("OTP")
        new_pw = st.text_input("New Password", type="password")
        confirm_pw = st.text_input("Confirm Password", type="password")

        if st.button("Update Password"):
            if otp != st.session_state.pwd_otp_login:
                st.error("❌ Wrong OTP")
            elif new_pw != confirm_pw:
                st.error("❌ Password mismatch")
            else:
                c.execute(
                    "UPDATE users SET password_hash=? WHERE username=?",
                    (hash_password(new_pw), st.session_state.pwd_user)
                )
                conn.commit()
                st.success("✅ Password updated")
                st.session_state.pwd_mode = None
                st.rerun()

        st.stop()

    # -------- FORGOT PASSWORD --------
    if st.session_state.pwd_mode == "forgot":

        st.title("❓ Forgot Password")

        uname = st.text_input("Username")

        if st.button("Send OTP"):
            user = c.execute(
                "SELECT 1 FROM users WHERE username=?",
                (uname,)
            ).fetchone()

            if not user:
                st.error("❌ User not found")
                st.stop()

            st.session_state.pwd_user = uname
            send_password_otp()
            st.success("📩 OTP sent")
            st.stop()

        otp = st.text_input("OTP")
        new_pw = st.text_input("New Password", type="password")
        confirm_pw = st.text_input("Confirm Password", type="password")

        if st.button("Reset Password"):
            if otp != st.session_state.pwd_otp_login:
                st.error("❌ Wrong OTP")
            elif new_pw != confirm_pw:
                st.error("❌ Password mismatch")
            else:
                c.execute(
                    "UPDATE users SET password_hash=? WHERE username=?",
                    (hash_password(new_pw), st.session_state.pwd_user)
                )
                conn.commit()
                st.success("✅ Password reset successful")
                st.session_state.pwd_mode = None
                st.rerun()

        st.stop()

# =====================================================
# ================= OTP SCREEN ========================
# =====================================================
if not st.session_state.logged_in and st.session_state.step == "otp":

    st.title("📩 OTP Verification")

    otp_input = st.text_input("Enter OTP")

    if st.button("Verify OTP"):
        if otp_input == st.session_state.otp:
            st.session_state.logged_in = True
            st.session_state.step = "done"
            st.rerun()
        else:
            st.error("❌ Wrong OTP")

    if st.button("⬅ Back"):
        st.session_state.step = "login"
        st.session_state.otp = ""
        st.rerun()

    st.stop()

# ================= LOGIN GATE =================
if not st.session_state.logged_in or st.session_state.step != "done":
    st.stop()


# ================= TOP BAR =================
t1, t2 = st.columns([6, 1])
t1.title("🌱 Plants & Pots Business App")

if t2.button("🚪 Logout"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


    
st.caption(
    f"Logged in as **{st.session_state.user.upper()} "
    f"({st.session_state.role.upper()})**"
)

# ================= MOBILE NAVIGATION =================
with st.sidebar:
    st.title("📂 Menu")

    section = st.radio(
        "Go to",
        [
            "Inventory",
            "Sale / Return",
            "Dashboard",
            "Transactions",
            "Daily Closing"
        ]
    )


# Change Password sirf ADMIN ko
# =====================================================
# ================= CHANGE PASSWORD (ADMIN ONLY) ======


# ================= MOBILE FRIENDLY UI =================
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* ❌ DO NOT hide header — needed for mobile sidebar */

/* Improve mobile layout */
@media (max-width: 768px) {
    section[data-testid="stSidebar"] {
        width: 80vw !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ================= ADD USER / STAFF =================
if st.session_state.is_admin:
    with st.expander("➕ Add New User / Staff"):
        nu = st.text_input("Username", key="add_user_name")
        npw = st.text_input("Password", type="password", key="add_user_pass")
        nr = st.selectbox("Role", ["staff", "admin"], key="add_user_role")

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
                    INSERT INTO users (username, password_hash, role)
                    VALUES (?,?,?)
                    """,
                    (nu, hash_password(npw), nr)
                )
                conn.commit()
                st.success(f"✅ User '{nu}' created successfully as {nr}")

# ================= TYPE MAP =================
TYPE_MAP = {
    "Plants": ["Flower","Succulent","Indoor","Outdoor","Bonsai","Cactus"],
    "Pots": ["Ceramic","Plastic","Terracotta","Hanging","Large","Small"],
    "Tools": ["Cutter","Pruner","Shovel","Sprayer"],
    "Other": ["Other"]
}

# =====================================================
# ================= INVENTORY SECTION =================
# =====================================================
if section == "Inventory":

    # ================= ADD / UPDATE ITEM =================
    if st.session_state.is_admin:
        st.header("➕ Add / Update Item")

        c1, c2 = st.columns(2)

        with c1:
            item = st.text_input("Item Name").strip()
            category = st.selectbox("Category", list(TYPE_MAP.keys()))
            item_type = st.selectbox("Type", TYPE_MAP[category])

        with c2:
            qty = st.number_input("Set Stock Quantity", min_value=0, step=1)
            cost = st.number_input("Cost Price", min_value=0.0)
            sell = st.number_input("Selling Price", min_value=0.0)
            low = st.number_input("Low Stock Alert At", min_value=1, value=10)

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

    # ================= INVENTORY LIST =================
    st.header("📦 Inventory")

    inv = pd.read_sql("SELECT * FROM inventory", conn)

    if not inv.empty:
        inv["quantity"] = pd.to_numeric(inv["quantity"], errors="coerce").fillna(0).astype(int)
        inv["low_stock_limit"] = pd.to_numeric(inv["low_stock_limit"], errors="coerce").fillna(10).astype(int)

    st.dataframe(inv, use_container_width=True)

    # ================= DELETE ITEM =================
    if st.session_state.is_admin and not inv.empty:
        st.subheader("❌ Delete Item")
        di = st.selectbox("Select Item", inv["item"])
        if st.button("Delete Item"):
            c.execute("DELETE FROM inventory WHERE item=?", (di,))
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
# =====================================================
# ================= SALE / RETURN =====================
# =====================================================
if section == "Sale / Return":

    st.header("🧾 Sale / Return")

    inv = pd.read_sql("SELECT * FROM inventory", conn)

    if inv.empty:
        st.info("📦 Inventory empty. Pehle item add karein.")
    else:
        inv["quantity"] = pd.to_numeric(inv["quantity"], errors="coerce").fillna(0).astype(int)

        inv["display"] = (
            inv["item"] + " (Stock " + inv["quantity"].astype(str) + ")"
        )

        it_display = st.selectbox("Item", inv["display"])
        row = inv[inv["display"] == it_display].iloc[0]
        item_name = row["item"]

        action = st.radio("Action", ["SALE", "RETURN"])

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

        if st.button("Submit Transaction"):
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if action == "SALE":

                # 🔴 SELL PRICE CHECK
                if row["sell_price"] <= 0:
                    st.error("❌ Selling price 0 hai. Pehle Inventory me price set karo.")
                    st.stop()

                # 🔴 STOCK CHECK
                if row["quantity"] <= 0:
                    st.error("❌ Stock ZERO hai. Sale allowed nahi.")
                    st.stop()

                total = qty_tr * row["sell_price"]
                cost = qty_tr * row["cost_price"]
                new_qty = row["quantity"] - qty_tr

            else:  # RETURN
                total = -qty_tr * row["sell_price"]
                cost = -qty_tr * row["cost_price"]
                new_qty = row["quantity"] + qty_tr

            c.execute(
                "UPDATE inventory SET quantity=? WHERE item=?",
                (int(new_qty), item_name)
            )

            c.execute("""
                INSERT INTO sales
                (item, quantity, total, cost, user, action, date)
                VALUES (?,?,?,?,?,?,?)
            """, (
                item_name,
                int(qty_tr),
                float(total),
                float(cost),
                st.session_state.user,
                action,
                now
            ))

            conn.commit()
            st.success("✅ Transaction saved successfully")
            st.rerun()

# 


# =====================================================
# ================= DASHBOARD =========================
# =====================================================
if section == "Dashboard":

    st.header("📊 Dashboard")

    sales = pd.read_sql("SELECT * FROM sales", conn)

    if not sales.empty:
        sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
        sales["total"] = pd.to_numeric(sales["total"], errors="coerce").fillna(0.0)
        sales["cost"] = pd.to_numeric(sales["cost"], errors="coerce").fillna(0.0)

        st.metric("💰 Total Sales", f"{sales['total'].sum():.2f}")
        st.metric("📈 Profit", f"{(sales['total'] - sales['cost']).sum():.2f}")

        st.subheader("👤 User-wise Sales")
        st.dataframe(
            sales.groupby("user")["total"].sum().reset_index(),
            use_container_width=True
        )

        st.subheader("📅 Daily Sales")
        st.line_chart(
            sales.groupby(sales["date"].dt.date)["total"].sum()
        )
    else:
        st.info("No sales yet")

# =====================================================
# ================= TRANSACTION HISTORY ===============
if section == "Transactions":

    st.header("🧾 Transaction History")

    sales = pd.read_sql("SELECT * FROM sales", conn)
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")

    if st.session_state.is_staff:
        sales_view = sales[sales["user"] == st.session_state.user]
    else:
        sales_view = sales

    if sales_view.empty:
        st.info("No transactions yet")

    else:
        sales_view = sales_view.sort_values("date", ascending=False)

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

        tx = sales_view[sales_view["id"] == tx_id].iloc[0]

        if st.button("🧾 Generate Invoice"):

            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)

            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 10, "GREEN NURSERY", ln=True, align="C")

            pdf.set_font("Arial", size=11)
            pdf.cell(0, 6, "Plants | Pots | Gardening Tools", ln=True, align="C")

            pdf.ln(6)

            pdf.set_font("Arial", size=11)
            pdf.cell(95, 8, f"Invoice No: {tx_id}", ln=False)
            pdf.cell(0, 8, f"Date: {pd.to_datetime(tx['date']).strftime('%d-%m-%Y %I:%M %p')}"
            , ln=True)

            pdf.ln(6)

            pdf.set_font("Arial", "B", 11)
            pdf.cell(80, 9, "Item", border=1)
            pdf.cell(30, 9, "Qty", border=1, align="C")
            pdf.cell(40, 9, "Rate (Rs)", border=1, align="C")
            pdf.cell(40, 9, "Amount (Rs)", border=1, align="C")
            pdf.ln()

            amount = abs(tx["total"])
            rate = abs(tx["total"] / tx["quantity"]) if tx["quantity"] != 0 else 0


            pdf.set_font("Arial", size=11)
            pdf.cell(80, 9, tx["item"].title(), border=1)
            pdf.cell(30, 9, str(tx["quantity"]), border=1, align="C")
            pdf.cell(40, 9, f"{rate:.2f}", border=1, align="C")
            pdf.cell(40, 9, f"{amount:.2f}", border=1, align="C")

            pdf.ln(10)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(150, 10, "TOTAL AMOUNT", border=1)
            pdf.cell(40, 10, f"Rs {amount:.2f}", border=1, align="C")

            
            st.download_button(
                "📄 Download Invoice PDF",
                pdf.output(dest="S").encode("latin-1"),
                file_name=f"invoice_{tx_id}.pdf",
                mime="application/pdf"
            )

        
# ================= DAILY CLOSING REPORT ==============
# =====================================================
if section == "Daily Closing":

    st.header("🧾 Daily Closing Report")

    sales = pd.read_sql("SELECT * FROM sales", conn)
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    sales["total"] = pd.to_numeric(sales["total"], errors="coerce").fillna(0.0)
    sales["cost"] = pd.to_numeric(sales["cost"], errors="coerce").fillna(0.0)

    today = st.date_input("Select Date", date.today())
    daily = sales[sales["date"].dt.date == today]

    if daily.empty:
        st.warning("No transactions for selected date")
    else:
        total_sale = daily[daily["action"] == "SALE"]["total"].sum()
        total_return = daily[daily["action"] == "RETURN"]["total"].sum()
        profit = daily["total"].sum() - daily["cost"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Total Sale", f"{total_sale:.2f}")
        c2.metric("↩️ Total Return", f"{abs(total_return):.2f}")
        c3.metric("📈 Net Profit", f"{profit:.2f}")

        st.subheader("👤 User-wise Closing")
        st.dataframe(
            daily.groupby("user")["total"].sum().reset_index(),
            use_container_width=True
        )

        # ================= STAFF VIEW =================
        if st.session_state.is_staff:
            st.subheader("👤 Your Transactions")
            user_sales = daily[daily["user"] == st.session_state.user]
            st.dataframe(user_sales, use_container_width=True)

        # ================= ADMIN VIEW =================
        if st.session_state.is_admin:
            st.subheader("🛠 All Users Transactions")
            st.dataframe(daily, use_container_width=True)































