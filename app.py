import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Digital Credit Engine", layout="wide")

# =============================
# CONFIGURATION
# =============================

KIBOR = 12.96 / 100

DBR = {
    "Salaried": 0.40,
    "Self-Employed": 0.50,
    "Businessman": 0.50
}

PRODUCTS = {
    "Personal Loan": {"rate": 0.35, "max_tenor": 5, "fee": "PKR 2,500", "equity": False},
    "Auto Loan": {"rate": KIBOR + 0.05, "max_tenor": 10, "fee": "PKR 8,000", "equity": True},
    "Home Loan": {"rate": KIBOR + 0.03, "max_tenor": 20, "fee": "PKR 12,000", "equity": True},
    "Solar Loan": {"rate": KIBOR + 0.05, "max_tenor": 8, "fee": "PKR 5,000", "equity": True},
    "Business Loan": {"rate": 0.35, "max_tenor": 5, "fee": "TBA", "equity": False},
}

BANKS = [
    "Habib Bank Limited", "United Bank Limited", "MCB Bank",
    "Allied Bank Limited", "Bank Alfalah", "Meezan Bank",
    "Bank Al Habib", "Faysal Bank", "The Bank of Punjab",
    "Askari Bank", "JS Bank", "Soneri Bank"
]

# =============================
# FUNCTIONS
# =============================

def emi(p, r, n):
    m = r / 12
    if m == 0:
        return p / n
    return p * m * (1 + m) ** n / ((1 + m) ** n - 1)


def loan_from_emi(e, r, n):
    m = r / 12
    return e * ((1 + m) ** n - 1) / (m * (1 + m) ** n)


def schedule(p, r, n, e):
    m = r / 12
    bal = p
    rows = []

    for i in range(1, n + 1):
        interest = bal * m
        principal = e - interest
        bal -= principal
        rows.append([i, e, principal, interest, max(bal, 0)])

    return pd.DataFrame(rows, columns=["Month", "EMI", "Principal", "Markup", "Balance"])


# =============================
# UI
# =============================

st.title("Digital Credit Engine")
st.header("Applicant Information")

c1, c2, c3 = st.columns(3)

name = c1.text_input("Full Name")

# CNIC validation
cnic_raw = c2.text_input("CNIC (13 digits)")
cnic_digits = re.sub(r"\D", "", cnic_raw)[:13]
cnic_valid = len(cnic_digits) == 13

if cnic_raw and not cnic_valid:
    c2.error("CNIC must be exactly 13 digits")

gender = c3.selectbox("Gender", ["Male", "Female"])

c4, c5, c6 = st.columns(3)

profession = c4.selectbox("Profession", list(DBR.keys()))
income = c5.number_input("Net Monthly Income (PKR)", min_value=0)
experience = c6.number_input("Experience (Years)", min_value=0)

# =============================
# STAFF LOGIC
# =============================

staff_loan = False
basic_salary = 0

if profession == "Salaried":
    staff_loan = st.checkbox("Staff Loan")

if staff_loan:
    basic_salary = st.number_input("Basic Salary (PKR)", min_value=0)

# =============================
# PRODUCT SELECTION
# =============================

if profession == "Salaried":
    allowed_products = ["Personal Loan", "Auto Loan", "Home Loan", "Solar Loan"]
elif profession == "Self-Employed":
    allowed_products = ["Personal Loan", "Auto Loan", "Home Loan", "Solar Loan", "Business Loan"]
else:
    allowed_products = ["Personal Loan", "Auto Loan", "Home Loan", "Solar Loan", "Business Loan"]

st.header("Loan Product")
product = st.selectbox("Select Product", allowed_products)

rate_used = 0.05 if staff_loan else PRODUCTS[product]["rate"]
base_tenor = PRODUCTS[product]["max_tenor"]
equity_allowed = PRODUCTS[product]["equity"]

# =============================
# TENOR CONTROL
# =============================

if staff_loan:
    staff_tenor = {
        "Personal Loan": 7,
        "Auto Loan": 10,
        "Home Loan": 25,
        "Solar Loan": 20,
        "Business Loan": 5
    }
    tenor = staff_tenor[product]
    st.info(f"Staff Fixed Tenor: {tenor} Years")
else:
    tenor = st.selectbox("Tenor (Years)", list(range(1, base_tenor + 1)))

months = tenor * 12

# =============================
# BANKING DETAILS
# =============================

if not staff_loan:
    st.subheader("Banking Details")
    bank = st.selectbox("Bank", BANKS)
    relationship_years = st.number_input("Relationship Years", min_value=0)

# =============================
# ASSET + EQUITY
# =============================

asset_value = 0
equity_pct = 0
equity_amount = 0

if equity_allowed:
    st.subheader("Asset Details")
    asset_value = st.number_input("Asset Value (PKR)", min_value=0)
    equity_pct = st.slider("Equity %", 20, 50, 20)
    equity_amount = asset_value * equity_pct / 100

# =============================
# BUSINESS LOAN DETAILS (NEW FIX)
# =============================

business_details = None
requested_amount = 0

if product == "Business Loan":
    st.subheader("Business Information")
    business_details = st.text_area("Brief Business Description")
    requested_amount = st.number_input("Desired Loan Amount (PKR)", min_value=0)

# =============================
# CALCULATION ENGINE
# =============================

if st.button("Calculate Eligibility"):

    if not cnic_valid:
        st.error("Invalid CNIC")
        st.stop()

    dbr_limit = DBR[profession]
    max_emi = income * dbr_limit
    max_loan_dbr = loan_from_emi(max_emi, rate_used, months)

    # asset constraint
    asset_limit = asset_value * (1 - equity_pct / 100) if equity_allowed else max_loan_dbr

    # staff caps
    if staff_loan:
        if product == "Personal Loan":
            cap = basic_salary * 8
        elif product == "Auto Loan":
            cap = basic_salary * 50
        elif product == "Home Loan":
            cap = basic_salary * 150
        elif product == "Solar Loan":
            cap = min(3_000_000, max_loan_dbr)
        else:
            cap = max_loan_dbr
    else:
        cap = max_loan_dbr

    # =============================
    # FINAL APPROVAL LOGIC
    # =============================

    if product == "Business Loan":
        approved = min(requested_amount, cap, max_loan_dbr)
    else:
        approved = min(cap, asset_limit, max_loan_dbr)

    emi_value = emi(approved, rate_used, months)
    total = emi_value * months
    markup = total - approved

    dbr_actual = emi_value / income if income else 0

    # =============================
    # OUTPUT
    # =============================

    st.subheader("Credit Decision Summary")

    if product == "Business Loan":
        st.write("Business Details:", business_details)
        st.write("Requested Amount:", f"PKR {requested_amount:,.0f}")

    st.write("Approved Loan:", f"PKR {approved:,.0f}")
    st.write("DBR Utilization:", f"{dbr_actual*100:.2f}%")

    st.metric("EMI", f"PKR {emi_value:,.0f}")

    st.write("Total Repayment:", f"PKR {total:,.0f}")
    st.write("Markup:", f"PKR {markup:,.0f}")

    if equity_allowed:
        st.subheader("Equity Details")
        st.write("Equity Amount:", f"PKR {equity_amount:,.0f}")

    # =============================
    # SCHEDULE
    # =============================

    st.subheader("Amortization Schedule")

    df = schedule(approved, rate_used, months, emi_value)

    fmt = df.copy()
    for col in fmt.columns[1:]:
        fmt[col] = fmt[col].apply(lambda x: f"{x:,.0f}")

    st.dataframe(fmt, use_container_width=True)

    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        "schedule.csv",
        "text/csv"
    )

    # =============================
    # NOTES
    # =============================

    st.subheader("Bank Notes")
    st.info(f"Rate Applied: {rate_used:.2%}")
    st.info(f"DBR Limit: {dbr_limit*100:.0f}%")

    if staff_loan:
        st.success("Staff Pricing Applied (Concessional Rate)")
