import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="The Bank- Digital Credit Engine", layout="wide", initial_sidebar_state="expanded")

# =============================
# CSS - THE BANK ORANGE THEME + DARK MODE FIX
# =============================
st.markdown("""
<style>
    * { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* ORANGE BACKGROUND GRADIENT */
    :root { --bg-light: #fff8f0; --bg-mid: #ffe6d5; --orange-dark: #FF6B35; --orange-light: #FF8C00; --text-dark: #1a1a1a; }
    
    html { background: linear-gradient(135deg, var(--bg-light) 0%, var(--bg-mid) 100%) !important; }
    body { background: linear-gradient(135deg, var(--bg-light) 0%, var(--bg-mid) 100%) !important; color: var(--text-dark); }
    
    [data-testid="stAppViewContainer"] { background: linear-gradient(135deg, var(--bg-light) 0%, var(--bg-mid) 100%) !important; }
    [data-testid="stMain"] { background: linear-gradient(135deg, var(--bg-light) 0%, var(--bg-mid) 100%) !important; }
    
    /* BANK HEADER */
    .bank-header {
        background: linear-gradient(135deg, #FF6B35 0%, #FF8C00 100%);
        color: white;
        padding: 30px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 6px 16px rgba(255, 107, 53, 0.4);
    }
    .bank-logo { font-size: 32px; font-weight: 700; color: white; letter-spacing: 1px; margin: 0; }
    .bank-subtitle { font-size: 14px; margin: 8px 0 0 0; color: #f0f0f0; font-weight: 500; }
    
    /* METRICS */
    .stMetric { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(255, 107, 53, 0.15); border-left: 5px solid #FF6B35; }
    
    /* ALL HEADINGS - ORANGE */
    h1, h2, h3, h4, h5, h6 { color: #FF6B35 !important; }
    h1 { border-bottom: 3px solid #FF8C00; padding-bottom: 15px; font-weight: 700; }
    h2, h3 { font-weight: 600; }
    
    /* ALL TEXT MUST BE DARK */
    body, p, span, div, li, td, th, label { color: #1a1a1a !important; }
    
    /* MARKDOWN & TEXT CONTAINERS */
    [data-testid="stMarkdownContainer"] { color: #1a1a1a !important; }
    .stMarkdown { color: #1a1a1a !important; }
    .stText { color: #1a1a1a !important; }
    
    /* LABELS - ALWAYS VISIBLE */
    label { 
        color: #1a1a1a !important; 
        font-weight: 600 !important; 
        display: block !important;
    }
    [data-testid="stLabel"] label { color: #1a1a1a !important; font-weight: 600 !important; }
    
    /* SUCCESS & INFO BOXES */
    .success-banner { background: linear-gradient(135deg, #FF6B35 0%, #FF8C00 100%); color: white; padding: 15px; border-radius: 8px; margin: 15px 0; font-weight: 700; }
    
    /* BUTTONS */
    .stButton>button { background: linear-gradient(135deg, #FF6B35 0%, #FF8C00 100%) !important; color: white !important; border: none !important; font-weight: 600 !important; }
    .stButton>button:hover { background: #FF5722 !important; transform: scale(1.02); }
    
    /* DATAFRAME TEXT */
    [role="grid"] { color: #1a1a1a !important; }
    td, th { color: #1a1a1a !important; background-color: white !important; }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] { background: linear-gradient(135deg, var(--bg-light) 0%, var(--bg-mid) 100%) !important; }
</style>
""", unsafe_allow_html=True)

# =============================
# CONFIGURATION
# =============================

KIBOR = 12 / 100

DBR_STAFF = 0.50
DBR = {"Salaried": 0.40, "Self-Employed": 0.50, "Businessman": 0.50}

PROCESSING_FEES = {
    "Personal Loan": 5000,
    "Auto Loan": 8000,
    "Home Loan": 12000,
    "Solar Loan": 5000,
    "Business Loan": 5000,
}

PRODUCTS = {
    "Personal Loan": {"rate": 0.35, "max_tenor": 5, "equity": False, "max_limit": 3_000_000, "staff_tenor": 7},
    "Auto Loan": {"rate": KIBOR + 0.05, "max_tenor": 5, "equity": True, "max_limit": 3_000_000, "staff_tenor": 10, "insurance_rate": 0.0175},
    "Home Loan": {"rate": KIBOR + 0.03, "max_tenor": 20, "equity": True, "max_limit": 250_000_000, "staff_tenor": 25},
    "Solar Loan": {"rate": KIBOR + 0.05, "max_tenor": 8, "equity": True, "max_limit_salaried": 5_000_000, "max_limit_other": 100_000_000, "staff_limit": 2_000_000, "staff_tenor": 20},
    "Business Loan": {"rate": KIBOR + 0.05, "max_tenor": 5, "equity": False, "max_limit": float('inf')},
}

BANKS = ["The Bank of Punjab", "United Bank Limited", "MCB Bank", "Allied Bank Limited", "Bank Alfalah", 
         "Meezan Bank", "Bank Al Habib", "Faysal Bank", "Habib Bank Limited", "Askari Bank", "JS Bank", "Soneri Bank"]

# =============================
# SCORECARD CRITERIA
# =============================

INDIVIDUAL_CRITERIA = {
    "Age of Borrower": {"Over 50 years & upto max. age as per PPMs": 5, "Over 30 & upto 50 years": 4, "Over 18 & upto 30 years": 2},
    "Gender": {"Male": 4, "Female": 5},
    "Marital Status": {"Un-married": 5, "Married": 3},
    "No. of Dependents": {"Upto 3": 5, "4 to 5": 3, "More than 5": 1},
    "Qualification": {"Masters & Above": 10, "Graduate": 8, "Below Graduate": 5},
    "Type of Occupation": {"Employees maintaining salary with BOP & 'A' category": 10, "Govt. Employees & 'B' category / under MOU financing": 7, "Employee of all other accepted employers/SEB/SEP": 4},
    "Job Status": {"Permanent": 5, "Contractual": 2},
    "Length of Employment": {"5 years & over": 10, "3 years & over": 7, "Less than 3 years": 4},
    "Monthly Income": {"Above Rs.100,000-SI / Above Rs.150,000-SEB/SEP": 10, "Rs.50,000 & above-SI / Rs.80,000 & above-SEB/SEP": 7, "Below Rs.50,000-SI / Below Rs.80,000-SEB/SEP": 4},
    "Type of Residence": {"Owned/Parents'": 5, "Rented": 3},
    "Collateral": {"Leased/mortgage/Liquid Security": 5, "Personal Loans (clean)": 0},
    "Debt Burden": {"If existing debt/burden=upto 30% of disposable income": 5, "If existing debt/burden=40% of disposable income": 3, "If existing debt/burden=50% of disposable income": 1},
    "Repayment History": {"If no default during last 12 months": 15, "1 Instance of OD-30/60/90 days (No current existence)": 10, "2 Instances of OD-30/60/90 days (No current existence)/ No credit history": 6, "3 or more instances of OD-30/60/90 days": 0},
    "Length of Credit History": {"Over 5 years": 5, "From 3-5 years": 4, "Less than 3 years / No Previous Credit History": 2},
}

SME_NEW_BUSINESS_CRITERIA = {
    "Business Commitment": {"Full Time": 100, "Part Time": 50},
    "Age": {"42 - 60": 50, "39-41.9": 45, "35-38.9": 40, "30-34.9": 30, "25-29.9": 25, "Not Applicable in case of Entities": 50},
    "Credit Turnover Of Existing Limit With Any Bank": {"No such requirement": 100, "No Limit Availed": 100, "More than 4 times": 100, "More than 3 times": 80, "More than 2 times": 50, "2 times or less": 30},
    "Experience": {"Relevant > 3 Years": 100, "Relevant 1-3 years": 80, "Family background": 70, "Unrelated": 50, "Never worked": 0},
    "Present Employment Status": {"Relevant Job": 50, "Family business": 50, "Non-relevant job": 25, "Previous experience": 35, "Never worked": 0},
    "Training": {"Trained & Certified": 100, "Not required": 100, "Trained only": 80, "Not trained": 0, "Not applicable": 100},
    "License/Certification": {"Required & Held": 100, "No requirement": 100, "Required but not held": 0, "Learner": 60, "Drivers name": 100, "Applied": 60},
    "Applicant's Understanding": {"Absolutely clear": 100, "Good": 50, "Very little": -100},
    "Applicant's Business Place": {"Not required": 100, "Owned with docs": 100, "Family owned": 80, "Owned no docs": 60, "Rented with docs": 50, "Rented no docs": 40, "To be rented": 20},
    "Debt Burden Ratio": {"<20%": 100, "20-30%": 90, "30-40%": 80, "40-50%": 70, ">50%": -1800},
    "Vehicle Ownership": {"Own vehicle": 50, "Family owned": 40, "Not applicable": 50, "None": 0, "Not applicable entity": 50},
    "Is Sim On Customer Name": {"Yes": 100, "No": -1800},
    "Tax Filer": {"NTN Filer": 100, "Tax exempted zone": 80, "NTN Non-Filer": 40, "No NTN": 0},
    "Security": {"Vehicle": 100, "Property": 100, "Partly rented": 80, "Agri": 70, "Rented property": 60, "Liquid": 100},
}

SME_EXISTING_BUSINESS_CRITERIA = {
    "Business Commitment": {"Full Time": 100, "Part Time": 50},
    "Age": {"42-60": 50, "39-41.9": 45, "35-38.9": 40, "30-34.9": 30, "25-29.9": 25, "Not applicable": 50},
    "Training": {"Certified": 100, "Not required": 100, "Trained only": 80, "Not trained": 0, "Not applicable": 100},
    "License/Certification": {"Required & Held": 100, "No requirement": 100, "Required but not": 0, "Learner": 60, "Drivers": 100, "Applied": 60},
    "Vehicle Ownership": {"Own": 60, "Family": 40, "Not applicable": 60, "None": 0, "Entity": 60},
    "Applicants Business Outlook": {"Positive": 100, "Neutral": 50, "Negative": -200},
    "Debt Burden Ratio": {"<20%": 100, "20-30%": 90, "30-40%": 80, "40-50%": 70, ">50%": -1800},
    "Tax Filer Status": {"NTN Filer": 60, "Tax exempted": 50, "NTN Non-Filer": 40, "No NTN": 0},
    "Security": {"Vehicle": 100, "Property": 100, "Partly rented": 80, "Agri": 70, "Rented": 60, "Liquid": 100},
    "Applicant'S Business Place": {"Not required": 100, "Owned": 100, "Family": 80, "Owned no docs": 60, "Rented": 50, "Rented no docs": 40, "To rent": 20},
    "Is Sim On Customer Name": {"Yes": 100, "No": -1800},
    "Length Of Business Existence": {"5+ Years": 100, "2-5 Years": 80, "1-2 Years": 25, "<1 Year": 0},
    "Accounts": {"CA prepared": 100, "Professional": 90, "Self": 80, "Mandatory not provided": -1800, "No requirement": 100, "Not prepared": 50},
    "Revenues": {"Growing": 100, "Stagnant": 80, "Declined <30%": 60, "Declined >30%": 0},
    "Profitability": {"Growing": 80, "Static": 60, "Declined <30%": 40, "Declined >30%": 0},
    "Applicant'S Bank Account": {"Yes with docs": 80, "Yes no docs": 40, "Not required": 80, "No": 0},
    "Credit Turnover": {"Not required": 100, "No limit": 100, ">4 times": 100, ">3 times": 80, ">2 times": 50, "≤2 times": 30},
}

# =============================
# HELPER FUNCTIONS
# =============================

def emi(p, r, n):
    m = r / 12
    if m == 0:
        return p / n
    return p * m * (1 + m) ** n / ((1 + m) ** n - 1)

def loan_from_emi(e, r, n):
    m = r / 12
    if m == 0:
        return e * n
    return e * ((1 + m) ** n - 1) / (m * (1 + m) ** n)

def schedule(p, r, n, e, insurance_schedule=None):
    m = r / 12
    bal = p
    rows = []
    for i in range(1, n + 1):
        interest = bal * m
        principal = e - interest
        bal -= principal
        if insurance_schedule:
            insurance_cost = insurance_schedule.get(i, 0)
            rows.append([i, e, principal, interest, insurance_cost, e + insurance_cost, max(bal, 0)])
        else:
            rows.append([i, e, principal, interest, max(bal, 0)])
    
    cols = ["Month", "EMI", "Principal", "Markup", "Insurance", "Total", "Balance"] if insurance_schedule else ["Month", "EMI", "Principal", "Markup", "Balance"]
    return pd.DataFrame(rows, columns=cols[:len(rows[0])])

def staff_loan_schedule(p, r, n):
    """Staff loan: Phase 1 (6/7): Principal only, Phase 2 (1/7): Markup only"""
    monthly_rate = r / 12
    principal_months = int(n * 6 / 7)
    markup_months = n - principal_months
    fixed_principal = p / principal_months
    
    rows = []
    bal = p
    total_markup = 0
    
    for i in range(1, principal_months + 1):
        markup_accrued = bal * monthly_rate
        total_markup += markup_accrued
        bal -= fixed_principal
        rows.append([i, fixed_principal, markup_accrued, fixed_principal, max(bal, 0)])
    
    markup_emi = total_markup / markup_months if markup_months > 0 else 0
    for i in range(principal_months + 1, n + 1):
        rows.append([i, 0, markup_emi, markup_emi, 0])
    
    return pd.DataFrame(rows, columns=["Month", "Principal", "Markup Accrued/Payment", "Payment", "Balance"])

def calculate_auto_insurance(asset_value, months):
    """Year 1: Full asset, Year 2+: Depreciated 10% annually"""
    insurance_schedule = {}
    year1_insurance = asset_value * 0.0175
    
    for month in range(1, months + 1):
        year = (month - 1) // 12 + 1
        total_years = (months - 1) // 12 + 1
        if year == total_years:
            insurance_schedule[month] = 0
        else:
            depreciation = 0.90 ** (year - 1)
            insurance_schedule[month] = (asset_value * depreciation * 0.0175) / 12
    
    return year1_insurance, insurance_schedule

def calculate_individual_score(selections):
    score_breakdown = []
    total_score = 0
    for criterion, selected in selections.items():
        if selected and selected in INDIVIDUAL_CRITERIA[criterion]:
            score = INDIVIDUAL_CRITERIA[criterion][selected]
            score_breakdown.append({"Criterion": criterion, "Selected": selected, "Score": score})
            total_score += score
    
    percentage = (total_score / 100 * 100) if 100 > 0 else 0
    
    if percentage >= 96: grade, grade_name = 1, "G1"
    elif percentage >= 91: grade, grade_name = 2, "G2"
    elif percentage >= 81: grade, grade_name = 3, "G3"
    elif percentage >= 71: grade, grade_name = 4, "G4"
    elif percentage >= 61: grade, grade_name = 5, "G5"
    elif percentage >= 51: grade, grade_name = 6, "G6"
    elif percentage >= 41: grade, grade_name = 7, "G7"
    elif percentage >= 31: grade, grade_name = 8, "G8"
    elif percentage >= 21: grade, grade_name = 9, "G9"
    elif percentage >= 11: grade, grade_name = 10, "G10"
    elif percentage >= 6: grade, grade_name = 11, "G11"
    else: grade, grade_name = 12, "G12"
    
    return {"breakdown": score_breakdown, "total": total_score, "percentage": percentage, "grade": grade, "name": grade_name, "approved": grade <= 6}

def calculate_sme_score(selections, business_type):
    score_breakdown = []
    total_score = 0
    criteria = SME_EXISTING_BUSINESS_CRITERIA if business_type == "Existing Business" else SME_NEW_BUSINESS_CRITERIA
    max_score = 1530 if business_type == "Existing Business" else 1250
    
    for criterion, selected in selections.items():
        if criterion in criteria and selected and selected in criteria[criterion]:
            score = criteria[criterion][selected]
            score_breakdown.append({"Criterion": criterion, "Selected": selected, "Score": score})
            total_score += score
    
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    if percentage >= 90: grade, grade_name = 1, "G1"
    elif percentage >= 80: grade, grade_name = 2, "G2"
    elif percentage >= 70: grade, grade_name = 3, "G3"
    elif percentage >= 60: grade, grade_name = 4, "G4"
    elif percentage >= 55: grade, grade_name = 5, "G5"
    elif percentage >= 50: grade, grade_name = 6, "G6"
    elif percentage >= 40: grade, grade_name = 7, "G7"
    elif percentage >= 30: grade, grade_name = 8, "G8"
    elif percentage >= 20: grade, grade_name = 9, "G9"
    elif percentage >= 10: grade, grade_name = 10, "G10"
    elif percentage >= 5: grade, grade_name = 11, "G11"
    else: grade, grade_name = 12, "G12"
    
    return {"breakdown": score_breakdown, "total": total_score, "percentage": percentage, "grade": grade, "name": grade_name, "approved": grade <= 6}

# =============================
# MAIN APP
# =============================

st.markdown("""
<div class="bank-header">
    <div class="bank-logo">🏦 THE BANK</div>
    <div class="bank-subtitle">Digital Credit Engine - Intelligent Loan Originating & Underwriting System</div>
</div>
""", unsafe_allow_html=True)

st.markdown("### 👤 Applicant Information")

c1, c2, c3 = st.columns(3)
with c1:
    name = st.text_input("Full Name *")
with c2:
    cnic_raw = st.text_input("CNIC (13 digits) *", placeholder="12345678901234")
    cnic_digits = re.sub(r"\D", "", cnic_raw)
    cnic_valid = len(cnic_digits) == 13
    if cnic_raw and not cnic_valid:
        st.error(f"❌ CNIC must be exactly 13 digits")
with c3:
    app_date = datetime.today().strftime("%d-%m-%Y")
    st.text_input("Application Date", value=app_date, disabled=True)

c4, c5, c6 = st.columns(3)
with c4:
    gender = st.selectbox("Gender *", ["Male", "Female"])
with c5:
    profession = st.selectbox("Profession *", list(DBR.keys()))
with c6:
    income = st.number_input("Net Monthly Income (PKR) *", min_value=0, value=0)

c7, c8, c9 = st.columns(3)
with c7:
    experience_years = st.number_input("Experience (Years) *", min_value=0, value=0)
with c8:
    staff_loan = False
    basic_salary = 0
    if profession == "Salaried":
        staff_loan = st.checkbox("✓ Staff Loan Eligible")
with c9:
    if staff_loan:
        basic_salary = st.number_input("Basic Salary (PKR) *", min_value=0, value=0)

st.markdown("### 💳 Loan Product Details")

c1, c2 = st.columns(2)
with c1:
    allowed_products = ["Personal Loan", "Auto Loan", "Home Loan", "Solar Loan"] if profession == "Salaried" else ["Personal Loan", "Auto Loan", "Home Loan", "Solar Loan", "Business Loan"]
    product = st.selectbox("Select Loan Product *", allowed_products)
with c2:
    if staff_loan:
        tenor = PRODUCTS[product]["staff_tenor"]
        st.info(f"Tenor: {tenor} Years (Staff Fixed)")
    else:
        base_tenor = PRODUCTS[product]["max_tenor"]
        tenor = st.selectbox("Tenor (Years) *", list(range(1, base_tenor + 1)))

months = tenor * 12

st.markdown("**Loan Details**")

if staff_loan:
    desired_amount = st.number_input("Desired Loan Amount (PKR) - Optional", min_value=0, value=0)
else:
    desired_amount = st.number_input("Desired Loan Amount (PKR) *", min_value=0, value=0)

if not staff_loan:
    c1, c2 = st.columns(2)
    with c1:
        bank = st.selectbox("Bank", BANKS)
    with c2:
        relationship_years = st.number_input("Relationship with Bank (Years)", min_value=0, value=0)
else:
    bank = "The Bank of Pune (Employees Loans)"
    relationship_years = 0

asset_value = 0
equity_pct = 20

if not staff_loan and PRODUCTS[product]["equity"]:
    c1, c2 = st.columns(2)
    with c1:
        asset_value = st.number_input("Asset Value (PKR) *", min_value=0, value=0)
    with c2:
        equity_pct = st.slider("Minimum Equity % Required", 20, 50, 20)

# =============================
# SCORECARD SECTION
# =============================

individual_score = None
sme_score = None

if not staff_loan:
    st.markdown("---")
    st.markdown("### 📊 Credit Risk Assessment")
    
    if product != "Business Loan":
        with st.expander("📋 Individual Scorecard Assessment", expanded=True):
            ind_sel = {}
            c1, c2 = st.columns(2)
            with c1:
                ind_sel["Age of Borrower"] = st.selectbox("Age of Borrower", list(INDIVIDUAL_CRITERIA["Age of Borrower"].keys()))
                st.text_input("Gender (Auto-populated)", value=gender, disabled=True)
                ind_sel["Gender"] = gender
                ind_sel["Marital Status"] = st.selectbox("Marital Status", list(INDIVIDUAL_CRITERIA["Marital Status"].keys()))
                ind_sel["No. of Dependents"] = st.selectbox("No. of Dependents", list(INDIVIDUAL_CRITERIA["No. of Dependents"].keys()))
                ind_sel["Qualification"] = st.selectbox("Qualification", list(INDIVIDUAL_CRITERIA["Qualification"].keys()))
                ind_sel["Type of Occupation"] = st.selectbox("Type of Occupation", list(INDIVIDUAL_CRITERIA["Type of Occupation"].keys()))
                ind_sel["Job Status"] = st.selectbox("Job Status", list(INDIVIDUAL_CRITERIA["Job Status"].keys()))
            
            with c2:
                if experience_years >= 5:
                    exp_lov = "5 years & over"
                elif experience_years >= 3:
                    exp_lov = "3 years & over"
                else:
                    exp_lov = "Less than 3 years"
                st.text_input("Length of Employment (Auto-populated)", value=exp_lov, disabled=True)
                ind_sel["Length of Employment"] = exp_lov
                
                if income <= 50000:
                    income_lov = "Below Rs.50,000-SI / Below Rs.80,000-SEB/SEP"
                elif income <= 100000:
                    income_lov = "Rs.50,000 & above-SI / Rs.80,000 & above-SEB/SEP"
                else:
                    income_lov = "Above Rs.100,000-SI / Above Rs.150,000-SEB/SEP"
                st.text_input("Monthly Income (Auto-populated)", value=f"PKR {income:,.0f}", disabled=True)
                ind_sel["Monthly Income"] = income_lov
                
                ind_sel["Type of Residence"] = st.selectbox("Type of Residence", list(INDIVIDUAL_CRITERIA["Type of Residence"].keys()))
                ind_sel["Collateral"] = st.selectbox("Collateral", list(INDIVIDUAL_CRITERIA["Collateral"].keys()))
                ind_sel["Debt Burden"] = st.selectbox("Debt Burden", list(INDIVIDUAL_CRITERIA["Debt Burden"].keys()))
                ind_sel["Repayment History"] = st.selectbox("Repayment History", list(INDIVIDUAL_CRITERIA["Repayment History"].keys()))
                ind_sel["Length of Credit History"] = st.selectbox("Length of Credit History", list(INDIVIDUAL_CRITERIA["Length of Credit History"].keys()))
            
            individual_score = calculate_individual_score(ind_sel)
    
    if product == "Business Loan":
        with st.expander("📊 SME/Business Scorecard Assessment", expanded=True):
            business_type = st.radio("Business Type *", ["New Business", "Existing Business"], horizontal=True)
            sme_sel = {}
            criteria = SME_EXISTING_BUSINESS_CRITERIA if business_type == "Existing Business" else SME_NEW_BUSINESS_CRITERIA
            
            cols = st.columns(2)
            for idx, param in enumerate(list(criteria.keys())):
                with cols[idx % 2]:
                    sme_sel[param] = st.selectbox(param, list(criteria[param].keys()), key=f"sme_{idx}")
            
            sme_score = calculate_sme_score(sme_sel, business_type)

st.markdown("---")
col_submit, col_space = st.columns([1, 4])
with col_submit:
    submit_button = st.button("🔍 CALCULATE ELIGIBILITY", use_container_width=True)

# =============================
# RESULTS
# =============================

if submit_button:
    if not cnic_valid:
        st.error("❌ CNIC must be exactly 13 digits")
        st.stop()
    if not name or income == 0:
        st.error("❌ Please fill all required fields")
        st.stop()
    if not staff_loan and desired_amount == 0:
        st.error("❌ Please enter desired loan amount")
        st.stop()
    if not staff_loan and PRODUCTS[product]["equity"] and asset_value == 0:
        st.error("❌ Please enter asset value")
        st.stop()
    
    # STAFF LOAN PATH
    if staff_loan:
        st.markdown("---")
        st.markdown('<div class="success-banner">✅ STAFF LOAN - AUTO APPROVED</div>', unsafe_allow_html=True)
        st.info("Staff loans are approved based on lowest of salary multiples or 50% DBR limit")
        
        rate_used = 0.05
        salary_multiples = {"Personal Loan": basic_salary * 8, "Auto Loan": basic_salary * 50, "Home Loan": basic_salary * 150, "Solar Loan": min(2_000_000, basic_salary * 100)}
        max_by_salary = salary_multiples.get(product, basic_salary * 5)
        max_by_dbr = loan_from_emi(income * DBR_STAFF, rate_used, months)
        approved = min(desired_amount if desired_amount > 0 else max_by_salary, max_by_salary, max_by_dbr)
        
        principal_months = int(months * 6 / 7)
        markup_months = months - principal_months
        fixed_principal = approved / principal_months
        
        bal = approved
        total_markup = 0
        for i in range(principal_months):
            total_markup += bal * (rate_used / 12)
            bal -= fixed_principal
        
        markup_emi = total_markup / markup_months if markup_months > 0 else 0
        total_repay = approved + total_markup
        
        with st.sidebar:
            st.markdown("### 🔐 Banker's Dashboard")
            st.metric("Loan Type", "Staff Loan")
            st.metric("Max by Salary Multiples", f"PKR {max_by_salary:,.0f}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**YOUR DESIRED**")
            st.metric("Amount", f"PKR {desired_amount:,.0f}" if desired_amount > 0 else "Salary multiples")
        with col2:
            st.markdown("**MAX CONSTRAINTS**")
            st.metric("By Salary Multiples", f"PKR {max_by_salary:,.0f}")
            
        with col3:
            st.markdown("**APPROVED**")
            st.metric("Amount", f"PKR {approved:,.0f}")
            st.metric("Phase 1 EMI", f"PKR {fixed_principal:,.0f}")
            st.metric("Phase 2 EMI", f"PKR {markup_emi:,.0f}")
        
        st.markdown("### 📅 Tentative Repayment Schedule")
        df = staff_loan_schedule(approved, rate_used, months)
        display_df = pd.concat([df.head(12), df.tail(12)]) if len(df) > 24 else df
        fmt_df = display_df.copy()
        for col in fmt_df.columns[1:]:
            fmt_df[col] = fmt_df[col].apply(lambda x: f"PKR {x:,.0f}" if x >= 0 else "PKR 0")
        st.dataframe(fmt_df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Schedule", csv, f"staff_loan_{cnic_digits}.csv", "text/csv")
        
        st.markdown("### ⚖️ Final Offer")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Loan Details:**\n- **Amount:** PKR {approved:,.0f}\n- **Tenor:** {tenor} Years\n- **Phase 1 ({principal_months}m):** PKR {fixed_principal:,.0f}/month\n- **Phase 2 ({markup_months}m):** PKR {markup_emi:,.0f}/month\n- **Total Interest:** PKR {total_markup:,.0f}")
        with col2:
            st.markdown(f"**Applicant:**\n- **Name:** {name}\n- **CNIC:** {cnic_digits}\n- **Income:** PKR {income:,.0f}\n- **Bank:** {bank}\n- **Date:** {datetime.now().strftime('%d-%m-%Y')}")
        st.stop()
    
    # NON-STAFF LOAN PATH
    if product != "Business Loan" and individual_score and not individual_score["approved"]:
        st.markdown("---")
        st.error(f"❌ APPLICATION DECLINED")
        with st.sidebar:
            st.markdown("### 🔐 Banker's Dashboard")
            st.warning("For Authorized Use Only")
            st.metric("Credit Score", f"{individual_score['total']}/{individual_score['total']}")
            st.metric("Risk Grade", f"G{individual_score['grade']}")
        st.stop()
    
    if product == "Business Loan" and sme_score and not sme_score["approved"]:
        st.markdown("---")
        st.error(f"❌ APPLICATION DECLINED")
        with st.sidebar:
            st.markdown("### 🔐 Banker's Dashboard")
            st.warning("For Authorized Use Only")
            st.metric("Credit Score", f"{sme_score['total']}")
            st.metric("Risk Grade", f"ORR {sme_score['grade']}")
        st.stop()
    
    st.markdown("---")
    st.markdown('<div class="success-banner">✅ APPLICATION APPROVED</div>', unsafe_allow_html=True)
    
    if individual_score:
        with st.sidebar:
            st.markdown("### 🔐 Banker's Dashboard")
            st.warning("For Authorized Use Only")
            st.metric("Credit Score", f"{individual_score['total']}/100")
            st.metric("Risk Grade", f"ORR {individual_score['grade']}")
    
    if sme_score:
        with st.sidebar:
            st.markdown("### 🔐 Banker's Dashboard")
            st.warning("For Authorized Use Only")
            st.metric("Credit Score", f"{sme_score['total']}")
            st.metric("Risk Grade", f"ORR {sme_score['grade']}")
    
    rate_used = PRODUCTS[product]["rate"]
    dbr_limit = DBR[profession]
    
    max_emi_dbr = income * dbr_limit
    max_by_dbr = loan_from_emi(max_emi_dbr, rate_used, months)
    
    if product == "Solar Loan":
        product_cap = 5_000_000 if profession == "Salaried" else 100_000_000
    elif product == "Auto Loan":
        product_cap = 3_000_000
    else:
        product_cap = PRODUCTS[product].get("max_limit", float('inf'))
    
    max_approvable = min(max_by_dbr, product_cap)
    
    # EQUITY CONSTRAINT
    if PRODUCTS[product]["equity"]:
        max_by_equity = asset_value - (asset_value * equity_pct / 100)
        max_approvable = min(max_approvable, max_by_equity)
        equity_contribution = asset_value - max_approvable
    else:
        max_by_equity = float('inf')
        equity_contribution = 0
    
    approved = min(desired_amount, max_approvable)
    
    limiting_factor = "None (Full Approval)"
    if approved < desired_amount:
        if approved == product_cap:
            limiting_factor = f"Product Cap (PKR {product_cap:,.0f})"
        elif PRODUCTS[product]["equity"] and approved == max_by_equity:
            limiting_factor = f"Equity Constraint ({equity_pct}%)"
        else:
            limiting_factor = f"DBR Limit ({dbr_limit*100:.0f}%)"
    
    approved_emi = emi(approved, rate_used, months)
    approved_dbr = (approved_emi / income * 100) if income > 0 else 0
    total_repay = approved_emi * months
    markup = total_repay - approved
    processing_fee = PROCESSING_FEES.get(product, 0)
    
    year1_insurance = 0
    insurance_schedule = None
    total_insurance = 0
    if product == "Auto Loan":
        year1_insurance, insurance_schedule = calculate_auto_insurance(asset_value, months)
        total_insurance = year1_insurance + sum(insurance_schedule.values())
    
    total_down_payment = processing_fee + year1_insurance + equity_contribution
    
    st.markdown("### 💰 Loan Comparison")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**YOUR REQUEST**")
        st.metric("Desired", f"PKR {desired_amount:,.0f}")
    with col2:
        st.markdown("**CONSTRAINTS**")
        st.metric("As per DBR Cushion", f"PKR {max_by_dbr:,.0f}")
        if product_cap != float('inf'):
            st.metric("Product Cap", f"PKR {product_cap:,.0f}")
    with col3:
        st.markdown("**APPROVED**")
        st.metric("Loan Amount", f"PKR {approved:,.0f}")
        st.metric("Monthly EMI", f"PKR {approved_emi:,.0f}")
    if approved < desired_amount:
        st.warning(f"⚠️ LIMITED BY: {limiting_factor}")
    else:
        st.success("✓ Full Amount Approved")
    
    st.markdown("### 📋 Down Payment Breakdown")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Processing Fee:** PKR {processing_fee:,.0f}")
        if product == "Auto Loan":
            st.write(f"**Year 1 Insurance:** PKR {year1_insurance:,.0f}")
            st.write("Note: Above charges are tentative and final down payment will be calculated at the time of final approval by bank")
    with col2:
      if PRODUCTS[product]["equity"]:
            st.write(f"**Equity Contribution:** PKR {equity_contribution:,.0f}")
            st.write(f"*(Asset {asset_value:,.0f} - Loan {approved:,.0f})*")
    with col3:
        st.metric("Total Down Payment", f"PKR {total_down_payment:,.0f}")
    
    st.markdown("### 📅 Tentative Repayment Schedule")
    if product == "Auto Loan" and insurance_schedule:
        df = schedule(approved, rate_used, months, approved_emi, insurance_schedule)
    else:
        df = schedule(approved, rate_used, months, approved_emi)
    
    display_df = pd.concat([df.head(12), df.tail(12)]) if len(df) > 24 else df
    fmt_df = display_df.copy()
    for col in fmt_df.columns[1:]:
        fmt_df[col] = fmt_df[col].apply(lambda x: f"PKR {x:,.0f}")
    st.dataframe(fmt_df, use_container_width=True, hide_index=True)
    
    csv = df.to_csv(index=False)
    st.download_button("📥 Download Schedule", csv, f"loan_schedule_{cnic_digits}.csv", "text/csv")
    
    st.markdown("### ⚖️ Final Loan Offer")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Loan Details:**\n- **Approved:** PKR {approved:,.0f}\n- **Tenor:** {tenor} Years\n- **Rate:** {rate_used:.2%} p.a.\n- **Monthly EMI:** PKR {approved_emi:,.0f}\n- **Total Repay:** PKR {total_repay:,.0f}\n- **Total Interest:** PKR {markup:,.0f}\n- **Total Insurance:** PKR {total_insurance:,.0f}")
    with col2:
        st.markdown(f"**Charges & Down Payment:**\n- **Processing Fee:** PKR {processing_fee:,.0f}\n- **Insurance (Y1):** PKR {year1_insurance:,.0f}\n- **Equity:** PKR {equity_contribution:,.0f}\n- **Total Down:** PKR {total_down_payment:,.0f}\n- **Name:** {name}\n- **CNIC:** {cnic_digits}\n- **Bank:** {bank}\n- **Date:** {datetime.now().strftime('%d-%m-%Y')}")
    
    st.info("✓ Preliminary offer - subject to verification of the application & approval by Bank")
