import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="The Bank of Punjab - Digital Credit Engine", layout="wide", initial_sidebar_state="expanded")

# =============================
# BANK OF PUNJAB BRANDING & DARK MODE CSS
# =============================
st.markdown("""
<style>
    * { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Bank of Punjab Orange Theme */
    :root {
        --primary-color: #FF6B35;
        --secondary-color: #FF8C00;
        --text-dark: #1a1a1a;
        --text-light: #ffffff;
    }
    
    /* Bank Branding Header - Orange */
    .bank-header {
        background: linear-gradient(135deg, #FF6B35 0%, #FF8C00 100%);
        color: white;
        padding: 30px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
    }
    .bank-logo { 
        font-size: 28px; 
        font-weight: bold; 
        margin: 0;
        color: #ffffff;
    }
    .bank-subtitle { 
        font-size: 14px; 
        margin: 8px 0 0 0;
        color: #f0f0f0;
    }
    
    /* Metrics with Bank Colors */
    .stMetric {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 5px solid #FF6B35;
    }
    
    /* Headings - Orange */
    h1 { color: #FF6B35 !important; border-bottom: 3px solid #FF8C00; padding-bottom: 15px; }
    h2 { color: #FF6B35 !important; margin-top: 25px; }
    h3 { color: #1a1a1a !important; }
    
    /* Dark Mode Text Fix - CRITICAL */
    body { color: #1a1a1a !important; background-color: #ffffff !important; }
    [data-testid="stMarkdownContainer"] { color: #1a1a1a !important; }
    .stMarkdown { color: #1a1a1a !important; }
    .stText { color: #1a1a1a !important; }
    label { color: #1a1a1a !important; }
    p { color: #1a1a1a !important; }
    
    /* Input Fields - Text visibility in dark mode */
    input { color: #1a1a1a !important; background-color: white !important; }
    select { color: #1a1a1a !important; background-color: white !important; }
    textarea { color: #1a1a1a !important; background-color: white !important; }
    [data-testid="stNumberInput"] input { color: #1a1a1a !important; background-color: white !important; }
    [data-testid="stTextInput"] input { color: #1a1a1a !important; background-color: white !important; }
    
    /* Success/Info Boxes */
    .success-banner { background-color: #FF6B35; color: white; padding: 15px; border-radius: 8px; margin: 15px 0; font-weight: bold; }
    .info-banner { background-color: #FF8C00; color: white; padding: 12px; border-radius: 6px; }
    
    /* Metric Values - Orange */
    .metric-value { color: #FF6B35 !important; font-weight: bold; }
    
    /* Buttons */
    .stButton>button { background-color: #FF6B35; color: white; border: none; }
    .stButton>button:hover { background-color: #FF8C00; }
</style>
""", unsafe_allow_html=True)

KIBOR = 12.96 / 100

DBR_STAFF = 0.50  # Staff loans: 50% DBR
DBR = {
    "Salaried": 0.40,
    "Self-Employed": 0.50,
    "Businessman": 0.50
}

PROCESSING_FEES = {
    "Personal Loan": 2500,
    "Auto Loan": 8000,
    "Home Loan": 12000,
    "Solar Loan": 5000,
    "Business Loan": 0,
}

PRODUCTS = {
    "Personal Loan": {"rate": 0.35, "max_tenor": 5, "equity": False, "max_limit": 3_000_000, "staff_tenor": 7},
    "Auto Loan": {"rate": KIBOR + 0.05, "max_tenor": 10, "equity": True, "max_limit": 3_000_000, "staff_tenor": 10},
    "Home Loan": {"rate": KIBOR + 0.03, "max_tenor": 20, "equity": True, "max_limit": 250_000_000, "staff_tenor": 25},
    "Solar Loan": {"rate": KIBOR + 0.05, "max_tenor": 8, "equity": True, "max_limit_salaried": 5_000_000, "max_limit_other": 100_000_000, "staff_limit": 2_000_000, "staff_tenor": 20},
    "Business Loan": {"rate": KIBOR + 0.05, "max_tenor": 5, "equity": False, "max_limit": float('inf')},
}

BANKS = [
    "Habib Bank Limited", "United Bank Limited", "MCB Bank",
    "Allied Bank Limited", "Bank Alfalah", "Meezan Bank",
    "Bank Al Habib", "Faysal Bank", "The Bank of Punjab",
    "Askari Bank", "JS Bank", "Soneri Bank"
]

# =============================
# INDIVIDUAL SCORECARD
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
    "Credit Turnover Of Existing Limit With Any Bank": {"No such requirement - Logistics loans": 100, "No such Limit Availed from any bank": 100, "More than 4 times of RF Limit": 100, "More than 3 times of RF Limit": 80, "More than 2 times of RF limit": 50, "2 times or less of the RF limit": 30},
    "Experience": {"Relevant Experience - > 3 Years": 100, "Relevant Experience -1- 3 years": 80, "No Experience but has family background in the chosen business.": 70, "Unrelated work experience": 50, "Applicant has never worked": 0},
    "Present Employment Status": {"Employed in Relevant Job": 50, "Working in relevant family owned business": 50, "Employed in non-relevant job": 25, "Previous relevant experience": 35, "Applicant has Never Worked / Un-Employed": 0},
    "Training": {"Trained & Certified in Relevant Field - Evidence Provided": 100, "Training not required": 100, "Trained in Relevant Field but not certified (No evidence)": 80, "Not Trained": 0, "Not Applicable in case of Entities": 100},
    "License/ Certification/ Permission": {"Required & Held": 100, "No such requirement": 100, "Required But not Held": 0, "license Required but Learner Held": 60, "license Required but Held in Drivers name (incase of logistic companies)": 100, "license Required and is applied (other than Logistics) supported by evidence": 60},
    "Applicant's Understanding": {"Absolutely clear and perfect": 100, "Good but not perfect": 50, "Very little or no understanding": -100},
    "Applicant's Business Place": {"Logistics Business - Not required in case of new business": 100, "Owned - Documents Provided (Self/business/company)": 100, "Family owned - Document Provided": 80, "Owned / Family owned- Documents not Provided": 60, "Rented  - Document Provided (Self/business/company)": 50, "Rented  - Document Not Provided": 40, "To be rented": 20},
    "Debt Burden Ratio": {"20% <": 100, "20% - 30%": 90, "30% - 40%": 80, "40% - 50%": 70, "Exceeding 50%": -1800},
    "Vehicle Ownership": {"Car / Tractor / Morotrcycle / Any registered Vehicle": 50, "Family Owned (Father/Husband/ Mother/Wife)": 40, "Not Applicable for Logistic loan": 50, "No vehicle owned by applicant": 0, "Not Applicable in case of Entities": 50},
    "Is Sim On Customer Name": {"Yes": 100, "No": -1800},
    "Tax Filer": {"NTN held and Filer": 100, "No NTN as Business located / to be established in TAX EXPEMTED ZONES": 80, "NTN held and NON-Filer": 40, "No NTN held and NON-Filer": 0},
    "Security": {"Vehicle incase of Logistics": 100, "Mortgage of self-occupied residential/ Commercial/ Industrial / land": 100, "Mortgage of partly-rented residential/ Commercial / Industrial property": 80, "Mortgage of Rural / Agri Property": 70, "Mortgage of rented residential / Commercial / Industrial property": 60, "Liquid security / Near Cash Security": 100},
}

SME_EXISTING_BUSINESS_CRITERIA = {
    "Business Commitment": {"Full Time": 100, "Part Time": 50},
    "Age": {"42 - 60": 50, "39-41.9": 45, "35-38.9": 40, "30-34.9": 30, "25-29.9": 25, "Not Applicable in case of Entities": 50},
    "Training": {"Trained & Certified in Relevant Field - Evidence Provided": 100, "Training not required": 100, "Trained in Relevant Field but not certified (No evidence)": 80, "Not Trained": 0, "Not Applicable in case of Entities": 100},
    "License/ Certification/ Permission": {"Required & Held": 100, "No such requirement": 100, "Required But not Held": 0, "license Required but Learner Held": 60, "license Required but Held in Drivers name (incase of logistic companies)": 100, "license Required and is applied (other than Logistics) supported by evidence": 60},
    "Vehicle Ownership": {"Car / Tractor / Morotrcycle / Any registered Vehicle": 60, "Family Owned (Father/Husband/ Mother/Wife)": 40, "Not Applicable for Logistic loan": 60, "No vehicle owned by applicant": 0, "Not Applicable in case of Entities": 60},
    "Applicants Business Outlook": {"Positive": 100, "Neutral": 50, "Negative": -200},
    "Debt Burden Ratio": {"20% <": 100, "20% - 30%": 90, "30% - 40%": 80, "40% - 50%": 70, "Exceeding 50%": -1800},
    "Tax Filer Status": {"NTN held and Filer": 60, "No NTN as Business located / to be established in TAX EXPEMTED ZONES": 50, "NTN held and NON-Filer": 40, "No NTN held and NON-Filer": 0},
    "Security": {"Vehicle incase of Logistics": 100, "Mortgage of self-occupied residential/ Commercial/ Industrial / land": 100, "Mortgage of partly-rented residential/ Commercial / Industrial property": 80, "Mortgage of Rural / Agri Property": 70, "Mortgage of rented residential / Commercial / Industrial property": 60, "Liquid security / Near Cash Security": 100},
    "Applicant'S Business Place": {"Logistics Business - Not required in case of new business": 100, "Owned - Documents Provided (Self/business/company)": 100, "Family owned - Document Provided": 80, "Owned / Family owned- Documents not Provided": 60, "Rented  - Document Provided (Self/business/company)": 50, "Rented  - Document Not Provided": 40, "To be rented": 20},
    "Is Sim On Customer Name": {"Yes": 100, "No": -1800},
    "Length Of Business Existence": {"More than 5 Years": 100, "2 - 5 Years": 80, "1 - 2 Years": 25, "Less than 1 Year": 0},
    "Accounts": {"Prepared by Chartered Accountant": 100, "Prepared by Professional Accountant": 90, "Self prepared": 80, "Mandatory PR Requirement but not provided": -1800, "No Scuh Mandatory requirement": 100, "Not prepared": 50},
    "Revenues": {"Growing": 100, "Stagnant": 80, "Declined up to 30%": 60, "Declined more than 30%": 0},
    "Profitability": {"Growing": 80, "Static": 60, "Declined up to 30%": 40, "Declined more than 30%": 0},
    "Applicant'S Bank Account": {"Yes - Evidence provided": 80, "Yes - Evidence not provided": 40, "No such requirement": 80, "No Bank Account": 0},
    "Credit Turnover Of Existing Limit With Any Bank": {"No such requirement - Logistics loans": 100, "No such Limit Availed from any bank": 100, "More than 4 times of RF Limit": 100, "More than 3 times of RF Limit": 80, "More than 2 times of RF limit": 50, "2 times or less of the RF limit": 30},
}

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
            total_payment = e + insurance_cost
            rows.append([i, e, principal, interest, insurance_cost, total_payment, max(bal, 0)])
        else:
            rows.append([i, e, principal, interest, max(bal, 0)])
    
    if insurance_schedule:
        cols = ["Month", "EMI", "Principal", "Markup", "Insurance", "Total Payment", "Balance"]
    else:
        cols = ["Month", "EMI", "Principal", "Markup", "Balance"]
    
    return pd.DataFrame(rows, columns=cols)

def staff_loan_schedule(p, r, n):
    """Staff loan: 
    Phase 1: Pay ONLY Principal (markup accrues on outstanding, not paid)
    Phase 2: Pay ONLY Markup (after principal fully recovered)
    Total tenor unchanged (7, 10, 20 etc years)
    """
    monthly_rate = r / 12
    principal_months = int(n * 6 / 7)  # First 6/7 of tenor for principal
    markup_months = n - principal_months  # Last 1/7 for markup
    
    fixed_principal = p / principal_months  # Fixed monthly principal payment
    
    rows = []
    bal = p
    total_accrued_markup = 0
    
    # PHASE 1: Pay Principal Only (Markup Accrues on Outstanding)
    for i in range(1, principal_months + 1):
        accrued_markup_this_month = bal * monthly_rate  # Accrues but NOT paid
        total_accrued_markup += accrued_markup_this_month
        bal -= fixed_principal
        rows.append([i, fixed_principal, accrued_markup_this_month, fixed_principal, max(bal, 0)])
    
    # PHASE 2: Pay Markup Only (Principal Done)
    markup_emi = total_accrued_markup / markup_months if markup_months > 0 else 0
    
    for i in range(principal_months + 1, n + 1):
        rows.append([i, 0, markup_emi, markup_emi, 0])
    
    cols = ["Month", "Principal Scheduled", "Markup Accrued/Payment", "Monthly Payment", "Outstanding Balance"]
    return pd.DataFrame(rows, columns=cols)

def calculate_auto_insurance(asset_value, months):
    """Calculate auto insurance - Year 1 upfront on FULL asset, then depreciated"""
    insurance_schedule = {}
    year1_insurance = asset_value * 0.0175
    monthly_rate = 0.0175
    
    for month in range(1, months + 1):
        year = (month - 1) // 12 + 1
        total_years = (months - 1) // 12 + 1
        
        if year == total_years:
            insurance_schedule[month] = 0
        else:
            depreciation = 0.90 ** (year - 1)
            year_insurance = asset_value * depreciation * monthly_rate
            monthly_insurance = year_insurance / 12
            insurance_schedule[month] = monthly_insurance
    
    return year1_insurance, insurance_schedule

def calculate_individual_score(selections):
    score_breakdown = []
    total_score = 0
    for criterion, selected_option in selections.items():
        if selected_option and selected_option in INDIVIDUAL_CRITERIA[criterion]:
            score = INDIVIDUAL_CRITERIA[criterion][selected_option]
            score_breakdown.append({"Criterion": criterion, "Selected": selected_option, "Score": score})
            total_score += score
    
    max_score = 100
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    if percentage >= 96:
        grade, grade_name = 1, "G1"
    elif percentage >= 91:
        grade, grade_name = 2, "G2"
    elif percentage >= 81:
        grade, grade_name = 3, "G3"
    elif percentage >= 71:
        grade, grade_name = 4, "G4"
    elif percentage >= 61:
        grade, grade_name = 5, "G5"
    elif percentage >= 51:
        grade, grade_name = 6, "G6"
    elif percentage >= 41:
        grade, grade_name = 7, "G7"
    elif percentage >= 31:
        grade, grade_name = 8, "G8"
    elif percentage >= 21:
        grade, grade_name = 9, "G9"
    elif percentage >= 11:
        grade, grade_name = 10, "G10"
    elif percentage >= 6:
        grade, grade_name = 11, "G11"
    else:
        grade, grade_name = 12, "G12"
    
    is_approved = grade <= 6
    return {"breakdown": score_breakdown, "total_score": total_score, "max_score": max_score, "percentage": percentage, "grade": grade, "grade_name": grade_name, "is_approved": is_approved}

def calculate_sme_score(selections, business_type):
    score_breakdown = []
    total_score = 0
    criteria = SME_EXISTING_BUSINESS_CRITERIA if business_type == "Existing Business" else SME_NEW_BUSINESS_CRITERIA
    max_score = 1530 if business_type == "Existing Business" else 1250
    
    for criterion, selected_option in selections.items():
        if criterion in criteria and selected_option and selected_option in criteria[criterion]:
            score = criteria[criterion][selected_option]
            score_breakdown.append({"Criterion": criterion, "Selected": selected_option, "Score": score})
            total_score += score
    
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    if percentage >= 90:
        grade, grade_name = 1, "G1"
    elif percentage >= 80:
        grade, grade_name = 2, "G2"
    elif percentage >= 70:
        grade, grade_name = 3, "G3"
    elif percentage >= 60:
        grade, grade_name = 4, "G4"
    elif percentage >= 55:
        grade, grade_name = 5, "G5"
    elif percentage >= 50:
        grade, grade_name = 6, "G6"
    elif percentage >= 40:
        grade, grade_name = 7, "G7"
    elif percentage >= 30:
        grade, grade_name = 8, "G8"
    elif percentage >= 20:
        grade, grade_name = 9, "G9"
    elif percentage >= 10:
        grade, grade_name = 10, "G10"
    elif percentage >= 5:
        grade, grade_name = 11, "G11"
    else:
        grade, grade_name = 12, "G12"
    
    is_approved = grade <= 6
    return {"breakdown": score_breakdown, "total_score": total_score, "max_score": max_score, "percentage": percentage, "grade": grade, "grade_name": grade_name, "is_approved": is_approved}

# =============================
# MAIN APP - BANK HEADER
# =============================

st.markdown("""
<div class="bank-header">
    <div class="bank-logo">🏦 THE BANK OF PUNJAB</div>
    <div class="bank-subtitle">Digital Credit Engine - Intelligent Loan Underwriting</div>
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
        staff_tenor = PRODUCTS[product]["staff_tenor"]
        st.info(f"Tenor: {staff_tenor} Years (Staff Fixed)")
        tenor = staff_tenor
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
    bank = "The Bank of Punjab (Staff)"
    relationship_years = 0

asset_value = 0
equity_pct = 20

if not staff_loan and PRODUCTS[product]["equity"]:
    c1, c2 = st.columns(2)
    with c1:
        asset_value = st.number_input("Asset Value (PKR) *", min_value=0, value=0)
    with c2:
        equity_pct = st.slider("Equity % Reference", 20, 50, 20)

# =============================
# SCORECARD SECTION
# =============================

individual_score_result = None
sme_score_result = None

if not staff_loan:
    st.markdown("---")
    st.markdown("### 📊 Credit Risk Assessment (MANDATORY)")
    
    if product != "Business Loan":
        with st.expander("📋 **Individual Scorecard Assessment**", expanded=True):
            ind_selections = {}
            
            c1, c2 = st.columns(2)
            with c1:
                ind_selections["Age of Borrower"] = st.selectbox("Age of Borrower", list(INDIVIDUAL_CRITERIA["Age of Borrower"].keys()))
                st.text_input("Gender (Auto-populated)", value=gender, disabled=True)
                ind_selections["Gender"] = gender
                ind_selections["Marital Status"] = st.selectbox("Marital Status", list(INDIVIDUAL_CRITERIA["Marital Status"].keys()))
                ind_selections["No. of Dependents"] = st.selectbox("No. of Dependents", list(INDIVIDUAL_CRITERIA["No. of Dependents"].keys()))
                ind_selections["Qualification"] = st.selectbox("Qualification", list(INDIVIDUAL_CRITERIA["Qualification"].keys()))
                ind_selections["Type of Occupation"] = st.selectbox("Type of Occupation", list(INDIVIDUAL_CRITERIA["Type of Occupation"].keys()))
                ind_selections["Job Status"] = st.selectbox("Job Status", list(INDIVIDUAL_CRITERIA["Job Status"].keys()))
            
            with c2:
                if experience_years >= 5:
                    exp_lov = "5 years & over"
                elif experience_years >= 3:
                    exp_lov = "3 years & over"
                else:
                    exp_lov = "Less than 3 years"
                st.text_input("Length of Employment (Auto-populated)", value=exp_lov, disabled=True)
                ind_selections["Length of Employment"] = exp_lov
                
                if income <= 50000:
                    income_lov = "Below Rs.50,000-SI / Below Rs.80,000-SEB/SEP"
                elif income <= 100000:
                    income_lov = "Rs.50,000 & above-SI / Rs.80,000 & above-SEB/SEP"
                else:
                    income_lov = "Above Rs.100,000-SI / Above Rs.150,000-SEB/SEP"
                st.text_input("Monthly Income (Auto-populated)", value=f"PKR {income:,.0f}", disabled=True)
                ind_selections["Monthly Income"] = income_lov
                
                ind_selections["Type of Residence"] = st.selectbox("Type of Residence", list(INDIVIDUAL_CRITERIA["Type of Residence"].keys()))
                ind_selections["Collateral"] = st.selectbox("Collateral", list(INDIVIDUAL_CRITERIA["Collateral"].keys()))
                ind_selections["Debt Burden"] = st.selectbox("Debt Burden", list(INDIVIDUAL_CRITERIA["Debt Burden"].keys()))
                ind_selections["Repayment History"] = st.selectbox("Repayment History", list(INDIVIDUAL_CRITERIA["Repayment History"].keys()))
                ind_selections["Length of Credit History"] = st.selectbox("Length of Credit History", list(INDIVIDUAL_CRITERIA["Length of Credit History"].keys()))
            
            individual_score_result = calculate_individual_score(ind_selections)
    
    if product == "Business Loan":
        with st.expander("📊 **SME/Business Scorecard Assessment**", expanded=True):
            business_type = st.radio("Business Type *", ["New Business", "Existing Business"], horizontal=True)
            
            sme_selections = {}
            criteria = SME_EXISTING_BUSINESS_CRITERIA if business_type == "Existing Business" else SME_NEW_BUSINESS_CRITERIA
            params = list(criteria.keys())
            
            cols = st.columns(2)
            for idx, param in enumerate(params):
                with cols[idx % 2]:
                    sme_selections[param] = st.selectbox(param, list(criteria[param].keys()), key=f"sme_{idx}")
            
            sme_score_result = calculate_sme_score(sme_selections, business_type)

st.markdown("---")

col_submit, col_space = st.columns([1, 4])
with col_submit:
    submit_button = st.button("🔍 CALCULATE ELIGIBILITY", use_container_width=True)

# =============================
# RESULTS SECTION
# =============================

if submit_button:
    if not cnic_valid:
        st.error(f"❌ CNIC must be exactly 13 digits")
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
    
    # =============================
    # STAFF LOAN PATH
    # =============================
    
    if staff_loan:
        st.markdown("---")
        st.markdown('<div class="success-banner">✅ STAFF LOAN - AUTO APPROVED</div>', unsafe_allow_html=True)
        st.info("Staff loans approved based on salary multiples and 50% DBR limit")
        
        rate_used = 0.05
        dbr_staff = DBR_STAFF
        
        salary_multiples = {
            "Personal Loan": basic_salary * 8,
            "Auto Loan": basic_salary * 50,
            "Home Loan": basic_salary * 150,
            "Solar Loan": min(2_000_000, basic_salary * 100),
        }
        
        max_by_salary = salary_multiples.get(product, basic_salary * 5)
        max_emi_allowed = income * dbr_staff
        max_by_dbr_amount = loan_from_emi(max_emi_allowed, rate_used, months)
        
        approved = min(desired_amount if desired_amount > 0 else max_by_salary, max_by_salary, max_by_dbr_amount)
        
        # Calculate staff EMI correctly - Phase 1: Principal Only
        principal_months = int(months * 6 / 7)
        markup_months = months - principal_months
        fixed_principal = approved / principal_months
        
        # Calculate total markup accrued
        bal = approved
        total_accrued_markup = 0
        for i in range(principal_months):
            accrued_markup = bal * (rate_used / 12)
            total_accrued_markup += accrued_markup
            bal -= fixed_principal
        
        # Phase 1 EMI = Fixed Principal (no markup payment)
        # Phase 2 EMI = Markup only
        markup_emi = total_accrued_markup / markup_months if markup_months > 0 else 0
        staff_phase1_emi = fixed_principal
        staff_phase2_emi = markup_emi
        
        processing_fee = PROCESSING_FEES.get(product, 0)
        down_payment = processing_fee
        
        with st.sidebar:
            st.markdown("### 🔐 Banker's Dashboard")
            st.metric("Loan Type", "Staff Loan (Auto-Approved)")
            st.metric("Max by Salary", f"PKR {max_by_salary:,.0f}")
        
        st.markdown("### 💰 Loan Comparison")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**YOUR DESIRED**")
            st.metric("Amount", f"PKR {desired_amount:,.0f}" if desired_amount > 0 else "Using salary formula")
        
        with col2:
            st.markdown("**MAX CONSTRAINTS**")
            st.metric("By Salary", f"PKR {max_by_salary:,.0f}")
            st.metric("By DBR (50%)", f"PKR {max_by_dbr_amount:,.0f}")
        
        with col3:
            st.markdown("**APPROVED**")
            st.metric("Loan Amount", f"PKR {approved:,.0f}")
            st.markdown("**Phase 1 (Principal):**")
            st.metric("Months", f"{principal_months}")
            st.metric("EMI", f"PKR {staff_phase1_emi:,.0f}")
            st.markdown("**Phase 2 (Markup):**")
            st.metric("Months", f"{markup_months}")
            st.metric("EMI", f"PKR {staff_phase2_emi:,.0f}")
        
        st.markdown("---")
        st.markdown("### 📋 Down Payment Breakdown")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Processing Fee:** PKR {processing_fee:,.0f}")
        with col2:
            st.metric("Total Down Payment", f"PKR {down_payment:,.0f}")
        
        st.markdown("### 📅 Amortization Schedule (Staff Loan - Phase 1: Principal | Phase 2: Markup)")
        
        df_schedule = staff_loan_schedule(approved, rate_used, months)
        display_df = pd.concat([df_schedule.head(12), df_schedule.tail(12)]) if len(df_schedule) > 24 else df_schedule
        
        fmt_df = display_df.copy()
        for col in fmt_df.columns[1:]:
            fmt_df[col] = fmt_df[col].apply(lambda x: f"PKR {x:,.0f}")
        
        st.dataframe(fmt_df, use_container_width=True, hide_index=True)
        
        csv = df_schedule.to_csv(index=False)
        st.download_button("📥 Download Schedule", csv, f"schedule_{cnic_digits}_{datetime.now().strftime('%d%m%Y')}.csv", "text/csv")
        
        st.markdown("---")
        st.markdown("### ⚖️ Final Loan Offer")
        
        total_repayment_phase1 = staff_phase1_emi * principal_months
        total_repayment_phase2 = staff_phase2_emi * markup_months
        total_repayment = total_repayment_phase1 + total_repayment_phase2
        total_markup = total_repayment - approved
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
**Loan Details:**
- **Approved Amount:** PKR {approved:,.0f}
- **Tenor:** {tenor} Years ({months} months total)
- **Interest Rate:** 5.00% p.a.

**Phase 1 (Principal Recovery):**
- **Duration:** {principal_months} months
- **Monthly EMI:** PKR {staff_phase1_emi:,.0f} (Principal only)
- **Total Phase 1:** PKR {total_repayment_phase1:,.0f}

**Phase 2 (Markup Recovery):**
- **Duration:** {markup_months} months
- **Monthly EMI:** PKR {staff_phase2_emi:,.0f} (Markup only)
- **Total Phase 2:** PKR {total_repayment_phase2:,.0f}

- **Total Repayment:** PKR {total_repayment:,.0f}
- **Total Interest:** PKR {total_markup:,.0f}
            """)
        
        with col2:
            st.markdown(f"""
**Applicant Details:**
- **Name:** {name}
- **CNIC:** {cnic_digits}
- **Monthly Income:** PKR {income:,.0f}
- **Bank:** {bank}
- **Approval Date:** {datetime.now().strftime('%d-%m-%Y')}

**Note:**
Phase 1: Pay principal only, markup accrues on outstanding balance
Phase 2: After principal paid, pay markup in equal instalments
Total tenor remains {tenor} years unchanged
            """)
        
        st.info("✓ Preliminary offer - subject to document verification")
        st.stop()
    
    # =============================
    # NON-STAFF LOAN PATH
    # =============================
    
    if product != "Business Loan" and individual_score_result:
        if not individual_score_result["is_approved"]:
            st.markdown("---")
            st.error(f"❌ APPLICATION DECLINED - Risk Grade {individual_score_result['grade']}")
            
            with st.sidebar:
                st.markdown("### 🔐 Banker's Dashboard")
                st.warning("For Authorized Use Only")
                st.metric("Credit Score", f"{individual_score_result['total_score']}/{individual_score_result['max_score']}")
                st.metric("Risk Grade", f"G{individual_score_result['grade']}")
            st.stop()
    
    if product == "Business Loan" and sme_score_result:
        if not sme_score_result["is_approved"]:
            st.markdown("---")
            st.error(f"❌ APPLICATION DECLINED - Risk Grade {sme_score_result['grade']}")
            
            with st.sidebar:
                st.markdown("### 🔐 Banker's Dashboard")
                st.warning("For Authorized Use Only")
                st.metric("Credit Score", f"{sme_score_result['total_score']}/{sme_score_result['max_score']}")
                st.metric("Risk Grade", f"G{sme_score_result['grade']}")
            st.stop()
    
    # =============================
    # APPROVED - CALCULATE LOAN
    # =============================
    
    st.markdown("---")
    st.markdown('<div class="success-banner">✅ APPLICATION APPROVED</div>', unsafe_allow_html=True)
    
    if individual_score_result:
        with st.sidebar:
            st.markdown("### 🔐 Banker's Dashboard")
            st.warning("For Authorized Use Only")
            st.metric("Credit Score", f"{individual_score_result['total_score']}/{individual_score_result['max_score']}")
            st.metric("Risk Grade", f"G{individual_score_result['grade']}")
    
    if sme_score_result:
        with st.sidebar:
            st.markdown("### 🔐 Banker's Dashboard")
            st.warning("For Authorized Use Only")
            st.metric("Credit Score", f"{sme_score_result['total_score']}/{sme_score_result['max_score']}")
            st.metric("Risk Grade", f"G{sme_score_result['grade']}")
    
    rate_used = PRODUCTS[product]["rate"]
    dbr_limit = DBR[profession]
    
    max_emi_allowed = income * dbr_limit
    max_by_dbr_amount = loan_from_emi(max_emi_allowed, rate_used, months)
    
    # Product-specific cap
    if product == "Solar Loan":
        product_cap = 5_000_000 if profession == "Salaried" else 100_000_000
    elif product == "Auto Loan":
        product_cap = 3_000_000
    else:
        product_cap = PRODUCTS[product].get("max_limit", float('inf'))
    
    max_approvable = min(max_by_dbr_amount, product_cap)
    approved = min(desired_amount, max_approvable)
    
    # Determine limiting factor
    if approved < desired_amount:
        if approved == product_cap:
            limiting_msg = f"LIMITED BY PRODUCT CAP: PKR {product_cap:,.0f}"
        else:
            limiting_msg = f"LIMITED BY DBR ({dbr_limit*100:.0f}%): Max EMI PKR {max_emi_allowed:,.0f}"
    else:
        limiting_msg = "✓ Full Amount Approved"
    
    approved_emi = emi(approved, rate_used, months)
    approved_dbr = (approved_emi / income * 100) if income > 0 else 0
    total_repayment = approved_emi * months
    markup = total_repayment - approved
    processing_fee = PROCESSING_FEES.get(product, 0)
    
    # Insurance (non-staff auto only)
    year1_insurance = 0
    insurance_schedule = None
    total_insurance_cost = 0
    
    if product == "Auto Loan":
        year1_insurance, insurance_schedule = calculate_auto_insurance(asset_value, months)
        total_insurance_cost = year1_insurance + sum(insurance_schedule.values())
    
    # Equity = Asset Value - Approved Loan
    if PRODUCTS[product]["equity"]:
        equity_amount = asset_value - approved
    else:
        equity_amount = 0
    
    st.markdown("### 💰 Loan Comparison")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**YOUR REQUEST**")
        st.metric("Desired", f"PKR {desired_amount:,.0f}")
    
    with col2:
        st.markdown("**CONSTRAINTS**")
        st.metric("DBR Max", f"PKR {max_by_dbr_amount:,.0f}")
        if product_cap != float('inf'):
            st.metric("Product Cap", f"PKR {product_cap:,.0f}")
    
    with col3:
        st.markdown("**APPROVED**")
        st.metric("Loan Amount", f"PKR {approved:,.0f}")
        st.metric("Monthly EMI", f"PKR {approved_emi:,.0f}")
    
    if approved < desired_amount:
        st.warning(f"⚠️ {limiting_msg}")
    else:
        st.success("✓ Full Amount Approved")
    
    st.markdown("---")
    st.markdown("### 📋 Down Payment Breakdown")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Processing Fee:** PKR {processing_fee:,.0f}")
        if product == "Auto Loan":
            st.write(f"**Year 1 Insurance:** PKR {year1_insurance:,.0f}")
    
    with col2:
        if PRODUCTS[product]["equity"]:
            st.write(f"**Equity Contribution:** PKR {equity_amount:,.0f}")
            st.write(f"*(Asset {asset_value:,.0f} - Loan {approved:,.0f})*")
    
    with col3:
        total_down_payment = processing_fee + year1_insurance + equity_amount
        st.metric("Total Down Payment", f"PKR {total_down_payment:,.0f}")
    
    st.markdown("### 📅 Amortization Schedule")
    
    if product == "Auto Loan" and insurance_schedule:
        df_schedule = schedule(approved, rate_used, months, approved_emi, insurance_schedule)
    else:
        df_schedule = schedule(approved, rate_used, months, approved_emi)
    
    display_df = pd.concat([df_schedule.head(12), df_schedule.tail(12)]) if len(df_schedule) > 24 else df_schedule
    
    fmt_df = display_df.copy()
    for col in fmt_df.columns[1:]:
        fmt_df[col] = fmt_df[col].apply(lambda x: f"PKR {x:,.0f}")
    
    st.dataframe(fmt_df, use_container_width=True, hide_index=True)
    
    csv = df_schedule.to_csv(index=False)
    st.download_button("📥 Download Schedule", csv, f"schedule_{cnic_digits}_{datetime.now().strftime('%d%m%Y')}.csv", "text/csv")
    
    st.markdown("---")
    st.markdown("### ⚖️ Final Loan Offer")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
**Loan Details:**
- **Approved Amount:** PKR {approved:,.0f}
- **Tenor:** {tenor} Years ({months} months)
- **Interest Rate:** {rate_used:.2%} p.a.
- **Monthly EMI:** PKR {approved_emi:,.0f}
- **Total Repayment:** PKR {total_repayment:,.0f}
- **Total Interest:** PKR {markup:,.0f}
- **Total Insurance:** PKR {total_insurance_cost:,.0f}
        """)
    
    with col2:
        st.markdown(f"""
**Charges & Down Payment:**
- **Processing Fee:** PKR {processing_fee:,.0f}
- **Insurance (Year 1):** PKR {year1_insurance:,.0f}
- **Equity Contribution:** PKR {equity_amount:,.0f}
- **Total Down Payment:** PKR {total_down_payment:,.0f}

**Applicant:**
- **Name:** {name} | **CNIC:** {cnic_digits}
- **Bank:** {bank}
- **Approval Date:** {datetime.now().strftime('%d-%m-%Y')}
        """)
    
    st.info("✓ Preliminary offer - subject to document verification and compliance review")
