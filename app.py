import streamlit as st
import pandas as pd
import re
from datetime import datetime

# =============================
# PAGE CONFIGURATION & STYLING
# =============================

st.set_page_config(
    page_title="Digital Credit Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for banker-styled interface
st.markdown("""
<style>
    * {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    .stMetric {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        border-left: 5px solid #1e88e5;
    }
    
    h1 {
        color: #1a237e;
        border-bottom: 3px solid #1e88e5;
        padding-bottom: 10px;
        font-size: 2.5em;
        font-weight: 700;
    }
    
    h2 {
        color: #1e88e5;
        font-size: 1.8em;
        margin-top: 20px;
        margin-bottom: 15px;
    }
    
    h3 {
        color: #424242;
        font-size: 1.3em;
    }
    
    .info-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 5px solid #1e88e5;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .success-box {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        border-left: 5px solid #43a047;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .danger-box {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        border-left: 5px solid #e53935;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        border-left: 5px solid #f57c00;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin: 15px 0;
    }
    
    .button-primary {
        background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        font-size: 16px;
        border-radius: 8px;
        cursor: pointer;
    }
    
    .status-approved {
        color: #2e7d32;
        font-weight: 700;
        font-size: 1.2em;
    }
    
    .status-declined {
        color: #c62828;
        font-weight: 700;
        font-size: 1.2em;
    }
    
    .data-grid {
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

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
# INDIVIDUAL SCORECARD (EXACT FROM EXCEL)
# =============================

INDIVIDUAL_CRITERIA = {
    "Age of Borrower": {
        "Over 50 years": 5,
        "Over 30 & upto 50 years": 4,
        "Over 18 & upto 30 years": 2,
    },
    "Gender": {
        "Male": 4,
        "Female": 5,
    },
    "Marital Status": {
        "Unmarried": 5,
        "Married": 3,
    },
    "No. of Dependents": {
        "Upto 3": 5,
        "4 to 5": 3,
        "More than 5": 1,
    },
    "Qualification": {
        "Masters & Above": 10,
        "Graduate": 8,
        "Below Graduate": 5,
    },
    "Type of Occupation": {
        "Employees with BOP & A category": 10,
        "Govt. Employees & B category / MOU financing": 7,
        "Employee of all other accepted employers": 4,
    },
    "Job Status": {
        "Permanent": 5,
        "Contractual": 2,
    },
    "Length of Employment": {
        "5 years & over": 10,
        "3 years & over": 7,
        "Less than 3 years": 4,
    },
    "Monthly Take Home Salary/Income": {
        "Above Rs.100,000": 10,
        "Rs.50,000 & above": 7,
        "Below Rs.50,000": 4,
    },
    "Type of Residence": {
        "Owned/Parents'": 5,
        "Rented": 3,
    },
    "Collateral": {
        "Leased vehicle/mortgage/Liquid Security": 5,
        "Personal Loans (clean)": 0,
    },
    "Debt Burden": {
        "Upto 30% of disposable income": 5,
        "40% of disposable income": 3,
        "50% of disposable income": 1,
    },
    "Repayment History": {
        "No default during last 12 months": 15,
        "1 Instance of OD (No current existence)": 10,
        "2 Instances of OD (No current existence)": 6,
        "3 or more instances of OD": 0,
    },
    "Length of Credit History": {
        "Over 5 years": 5,
        "From 3-5 years": 4,
        "Less than 3 years / No Previous Credit": 2,
    },
}

# Maximum Individual Score = 100 (sum of all max values)
INDIVIDUAL_MAX_SCORE = sum([max(v.values()) for v in INDIVIDUAL_CRITERIA.values()])

# =============================
# SME SCORECARD - NEW BUSINESS (EXACT FROM EXCEL)
# =============================

SME_NEW_BUSINESS_CRITERIA = {
    "Business Commitment": {
        "Full Time": 100,
        "Part Time": 50,
    },
    "Age": {
        "42 - 60": 50,
        "39 - 41.9": 45,
        "35 - 38.9": 40,
        "30 - 34.9": 30,
        "25 - 29.9": 25,
    },
    "Credit Turnover": {
        "No requirement - Logistics loans": 100,
        "No limit availed from any bank": 100,
        "More than 4x RF Limit": 100,
        "More than 3x RF Limit": 80,
        "More than 2x RF limit": 50,
        "2x or less of the RF limit": 30,
    },
    "Experience": {
        "Relevant Experience > 3 Years": 100,
        "Relevant Experience 1-3 Years": 80,
        "Family background in business": 70,
        "Unrelated work experience": 50,
        "Never worked": 0,
    },
    "Present Employment Status": {
        "Employed in Relevant Job": 50,
        "Working in family owned business": 50,
        "Employed in non-relevant job": 25,
        "Previous relevant experience": 35,
        "Never Worked / Un-Employed": 0,
    },
    "Training": {
        "Trained & Certified - Evidence Provided": 100,
        "Training not required": 100,
        "Trained but not certified": 80,
        "Not Trained": 0,
    },
    "License/Certification/Permission": {
        "Required & Held": 100,
        "No such requirement": 100,
        "Required but not Held": 0,
        "Learner Held": 60,
        "License in Driver's name": 100,
        "License Applied": 60,
    },
    "Applicant's Understanding": {
        "Absolutely clear and perfect": 100,
        "Good but not perfect": 50,
        "Very little or no understanding": -100,
    },
    "Applicant's Business Place": {
        "Logistics Business / Not required": 100,
        "Owned - Documents Provided": 100,
        "Family Owned - Documents Provided": 80,
        "Owned/Family - No Documents": 60,
        "Rented - Documents Provided": 50,
        "Rented - No Documents": 40,
        "To be rented": 20,
    },
    "Debt Burden Ratio": {
        "20% or less": 100,
        "20% - 30%": 90,
        "30% - 40%": 80,
        "40% - 50%": 70,
        "Exceeding 50%": -1800,
    },
    "Vehicle Ownership": {
        "Car/Tractor/Motorcycle/Registered Vehicle": 50,
        "Family Owned": 40,
        "Not Applicable for Logistic loan": 50,
        "No vehicle": 0,
    },
    "Is SIM Registered in Customer Name": {
        "Yes": 100,
        "No": -1800,
    },
    "Tax Filer Status": {
        "NTN held and Filer": 100,
        "Tax Exempted Zone": 80,
        "NTN held NON-Filer": 40,
        "No NTN": 0,
    },
    "Security": {
        "Vehicle": 100,
        "Self-occupied property": 100,
        "Partly-rented property": 80,
        "Rural/Agri Property": 70,
        "Rented property": 60,
        "Liquid/Near Cash Security": 100,
    },
}

SME_NEW_BUSINESS_MAX = 1250

# =============================
# SME SCORECARD - EXISTING BUSINESS (EXACT FROM EXCEL)
# =============================

SME_EXISTING_BUSINESS_ADDITIONAL = {
    "Length of Business Existence": {
        "More than 5 Years": 100,
        "2 - 5 Years": 80,
        "1 - 2 Years": 25,
        "Less than 1 Year": 0,
    },
    "Accounts & Books": {
        "Prepared by Chartered Accountant": 100,
        "Prepared by Professional Accountant": 90,
        "Self prepared": 80,
        "No Such Mandatory requirement": 100,
        "Not prepared": 50,
    },
    "Revenues": {
        "Growing": 100,
        "Stagnant": 80,
        "Declined up to 30%": 60,
        "Declined more than 30%": 0,
    },
    "Profitability": {
        "Growing": 80,
        "Static": 60,
        "Declined up to 30%": 40,
        "Declined more than 30%": 0,
    },
    "Applicant's Bank Account": {
        "Yes - Evidence provided": 80,
        "Yes - Evidence not provided": 40,
        "No such requirement": 80,
        "No Bank Account": 0,
    },
}

SME_EXISTING_BUSINESS_MAX = 1530

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

def calculate_individual_score(selections):
    """Calculate individual scorecard (simple addition)"""
    score_breakdown = []
    total_score = 0
    
    for criterion, selected_option in selections.items():
        if selected_option and selected_option in INDIVIDUAL_CRITERIA[criterion]:
            score = INDIVIDUAL_CRITERIA[criterion][selected_option]
            max_score = max(INDIVIDUAL_CRITERIA[criterion].values())
            score_breakdown.append({
                "Criterion": criterion,
                "Selected": selected_option,
                "Score": score,
                "Max": max_score
            })
            total_score += score
    
    percentage = (total_score / INDIVIDUAL_MAX_SCORE * 100) if INDIVIDUAL_MAX_SCORE > 0 else 0
    
    # Grade determination
    if percentage >= 96:
        grade = 1
        grade_name = "Exceptional"
    elif percentage >= 91:
        grade = 2
        grade_name = "Superior"
    elif percentage >= 81:
        grade = 3
        grade_name = "Very Good"
    elif percentage >= 71:
        grade = 4
        grade_name = "Good"
    elif percentage >= 61:
        grade = 5
        grade_name = "Satisfactory"
    elif percentage >= 51:
        grade = 6
        grade_name = "Acceptable"
    elif percentage >= 41:
        grade = 7
        grade_name = "Marginal"
    elif percentage >= 31:
        grade = 8
        grade_name = "Watch List"
    elif percentage >= 21:
        grade = 9
        grade_name = "Substandard"
    elif percentage >= 11:
        grade = 10
        grade_name = "Doubtful"
    else:
        grade = 12
        grade_name = "Loss"
    
    is_approved = grade <= 6
    
    return {
        "breakdown": score_breakdown,
        "total_score": total_score,
        "max_score": INDIVIDUAL_MAX_SCORE,
        "percentage": percentage,
        "grade": grade,
        "grade_name": grade_name,
        "is_approved": is_approved
    }

def calculate_sme_score(selections, business_type):
    """Calculate SME scorecard (simple addition)"""
    score_breakdown = []
    total_score = 0
    max_score = SME_NEW_BUSINESS_MAX if business_type == "New Business" else SME_EXISTING_BUSINESS_MAX
    
    # New Business criteria
    for criterion, selected_option in selections.items():
        if criterion in SME_NEW_BUSINESS_CRITERIA and selected_option:
            if selected_option in SME_NEW_BUSINESS_CRITERIA[criterion]:
                score = SME_NEW_BUSINESS_CRITERIA[criterion][selected_option]
                score_breakdown.append({
                    "Criterion": criterion,
                    "Selected": selected_option,
                    "Score": score
                })
                total_score += score
    
    # Existing Business additional criteria
    if business_type == "Existing Business":
        existing_selections = {k: v for k, v in selections.items() if k in SME_EXISTING_BUSINESS_ADDITIONAL}
        for criterion, selected_option in existing_selections.items():
            if selected_option and selected_option in SME_EXISTING_BUSINESS_ADDITIONAL[criterion]:
                score = SME_EXISTING_BUSINESS_ADDITIONAL[criterion][selected_option]
                score_breakdown.append({
                    "Criterion": criterion,
                    "Selected": selected_option,
                    "Score": score
                })
                total_score += score
    
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    # Grade determination for SME
    if percentage >= 90:
        grade = 1
        grade_name = "Exceptional"
    elif percentage >= 80:
        grade = 2
        grade_name = "Superior"
    elif percentage >= 70:
        grade = 3
        grade_name = "Very Good"
    elif percentage >= 60:
        grade = 4
        grade_name = "Good"
    elif percentage >= 55:
        grade = 5
        grade_name = "Satisfactory"
    elif percentage >= 50:
        grade = 6
        grade_name = "Acceptable"
    elif percentage >= 40:
        grade = 7
        grade_name = "Marginal"
    elif percentage >= 30:
        grade = 8
        grade_name = "Watch List"
    elif percentage >= 20:
        grade = 9
        grade_name = "Substandard"
    elif percentage >= 6:
        grade = 11
        grade_name = "Doubtful"
    else:
        grade = 12
        grade_name = "Loss"
    
    is_approved = grade <= 6
    
    return {
        "breakdown": score_breakdown,
        "total_score": total_score,
        "max_score": max_score,
        "percentage": percentage,
        "grade": grade,
        "grade_name": grade_name,
        "is_approved": is_approved
    }

# =============================
# MAIN APP UI
# =============================

# Header with branding
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown("""
    <div style='text-align: center; padding: 20px;'>
        <h1 style='margin: 0; color: #1a237e;'>🏦 DIGITAL CREDIT ENGINE</h1>
        <p style='color: #1e88e5; font-size: 14px; margin: 5px 0;'>Intelligent Loan Underwriting Platform</p>
    </div>
    """, unsafe_allow_html=True)

# =============================
# APPLICANT INFORMATION SECTION
# =============================

st.markdown("### 👤 Applicant Information")

c1, c2, c3 = st.columns(3)

with c1:
    name = st.text_input("Full Name *", key="name")

with c2:
    cnic_raw = st.text_input("CNIC (13 digits) *", key="cnic")
    cnic_digits = re.sub(r"\D", "", cnic_raw)[:13]
    cnic_valid = len(cnic_digits) == 13
    if cnic_raw and not cnic_valid:
        st.error("⚠️ CNIC must be 13 digits")

with c3:
    app_date = st.date_input("Application Date", value=datetime.today())

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
    if profession == "Salaried":
        staff_loan = st.checkbox("✓ Staff Loan Eligible")

with c9:
    basic_salary = 0
    if staff_loan:
        basic_salary = st.number_input("Basic Salary (PKR)", min_value=0, value=0)

# =============================
# LOAN PRODUCT SECTION
# =============================

st.markdown("### 💳 Loan Product Details")

c1, c2, c3 = st.columns(3)

with c1:
    if profession == "Salaried":
        allowed_products = ["Personal Loan", "Auto Loan", "Home Loan", "Solar Loan"]
    else:
        allowed_products = ["Personal Loan", "Auto Loan", "Home Loan", "Solar Loan", "Business Loan"]
    
    product = st.selectbox("Select Loan Product *", allowed_products)

with c2:
    rate_used = 0.05 if staff_loan else PRODUCTS[product]["rate"]
    base_tenor = PRODUCTS[product]["max_tenor"]
    
    if staff_loan:
        staff_tenor = {"Personal Loan": 7, "Auto Loan": 10, "Home Loan": 25, "Solar Loan": 20, "Business Loan": 5}
        tenor = staff_tenor[product]
        st.info(f"Tenor: {tenor} Years (Staff Fixed)")
    else:
        tenor = st.selectbox("Tenor (Years) *", list(range(1, base_tenor + 1)))

with c3:
    equity_allowed = PRODUCTS[product]["equity"]
    st.metric("Interest Rate", f"{rate_used:.2%}")

months = tenor * 12

# Banking details for non-staff
if not staff_loan:
    st.markdown("**Banking Details**")
    c1, c2 = st.columns(2)
    with c1:
        bank = st.selectbox("Bank", BANKS)
    with c2:
        relationship_years = st.number_input("Relationship with Bank (Years)", min_value=0, value=0)

# Asset & Equity
asset_value = 0
equity_pct = 0

if equity_allowed:
    st.markdown("**Asset Details (Collateral)**")
    c1, c2 = st.columns(2)
    with c1:
        asset_value = st.number_input("Asset Value (PKR)", min_value=0, value=0)
    with c2:
        equity_pct = st.slider("Equity % Required", 20, 50, 20)

# Business Loan Details
business_details = None
requested_amount = 0

if product == "Business Loan":
    st.markdown("**Business Information**")
    business_details = st.text_area("Brief Business Description *", max_chars=500)
    requested_amount = st.number_input("Desired Loan Amount (PKR) *", min_value=0, value=0)

# =============================
# CREDIT SCORING SECTION (MANDATORY - HIDDEN FROM APPLICANT VIEW)
# =============================

st.markdown("---")
st.markdown("### 📊 Credit Risk Assessment")

individual_score_result = None
sme_score_result = None

# Only show individual scorecard for non-business products
if product != "Business Loan":
    with st.expander("📋 **Individual Scorecard Assessment**", expanded=True):
        st.info("Complete all fields below for credit evaluation")
        
        ind_selections = {}
        
        c1, c2 = st.columns(2)
        
        with c1:
            ind_selections["Age of Borrower"] = st.selectbox(
                "Age of Borrower",
                list(INDIVIDUAL_CRITERIA["Age of Borrower"].keys())
            )
            ind_selections["Gender"] = st.selectbox(
                "Gender",
                list(INDIVIDUAL_CRITERIA["Gender"].keys())
            )
            ind_selections["Marital Status"] = st.selectbox(
                "Marital Status",
                list(INDIVIDUAL_CRITERIA["Marital Status"].keys())
            )
            ind_selections["No. of Dependents"] = st.selectbox(
                "No. of Dependents",
                list(INDIVIDUAL_CRITERIA["No. of Dependents"].keys())
            )
            ind_selections["Qualification"] = st.selectbox(
                "Qualification",
                list(INDIVIDUAL_CRITERIA["Qualification"].keys())
            )
            ind_selections["Type of Occupation"] = st.selectbox(
                "Type of Occupation",
                list(INDIVIDUAL_CRITERIA["Type of Occupation"].keys())
            )
            ind_selections["Job Status"] = st.selectbox(
                "Job Status",
                list(INDIVIDUAL_CRITERIA["Job Status"].keys())
            )
        
        with c2:
            ind_selections["Length of Employment"] = st.selectbox(
                "Length of Employment",
                list(INDIVIDUAL_CRITERIA["Length of Employment"].keys())
            )
            ind_selections["Monthly Take Home Salary/Income"] = st.selectbox(
                "Monthly Take Home Salary/Income",
                list(INDIVIDUAL_CRITERIA["Monthly Take Home Salary/Income"].keys())
            )
            ind_selections["Type of Residence"] = st.selectbox(
                "Type of Residence",
                list(INDIVIDUAL_CRITERIA["Type of Residence"].keys())
            )
            ind_selections["Collateral"] = st.selectbox(
                "Collateral",
                list(INDIVIDUAL_CRITERIA["Collateral"].keys())
            )
            ind_selections["Debt Burden"] = st.selectbox(
                "Debt Burden",
                list(INDIVIDUAL_CRITERIA["Debt Burden"].keys())
            )
            ind_selections["Repayment History"] = st.selectbox(
                "Repayment History",
                list(INDIVIDUAL_CRITERIA["Repayment History"].keys())
            )
            ind_selections["Length of Credit History"] = st.selectbox(
                "Length of Credit History",
                list(INDIVIDUAL_CRITERIA["Length of Credit History"].keys())
            )
        
        individual_score_result = calculate_individual_score(ind_selections)

# Business Loan - Show SME Scorecard
if product == "Business Loan":
    with st.expander("📊 **SME/Business Scorecard Assessment**", expanded=True):
        business_type = st.radio("Business Type *", ["New Business", "Existing Business"])
        
        sme_selections = {}
        
        c1, c2 = st.columns(2)
        
        with c1:
            for criterion in list(SME_NEW_BUSINESS_CRITERIA.keys())[:7]:
                sme_selections[criterion] = st.selectbox(
                    criterion,
                    list(SME_NEW_BUSINESS_CRITERIA[criterion].keys())
                )
        
        with c2:
            for criterion in list(SME_NEW_BUSINESS_CRITERIA.keys())[7:]:
                sme_selections[criterion] = st.selectbox(
                    criterion,
                    list(SME_NEW_BUSINESS_CRITERIA[criterion].keys())
                )
        
        if business_type == "Existing Business":
            st.markdown("**Existing Business Additional Information**")
            c1, c2 = st.columns(2)
            
            with c1:
                for criterion in list(SME_EXISTING_BUSINESS_ADDITIONAL.keys())[:3]:
                    sme_selections[criterion] = st.selectbox(
                        criterion,
                        list(SME_EXISTING_BUSINESS_ADDITIONAL[criterion].keys())
                    )
            
            with c2:
                for criterion in list(SME_EXISTING_BUSINESS_ADDITIONAL.keys())[3:]:
                    sme_selections[criterion] = st.selectbox(
                        criterion,
                        list(SME_EXISTING_BUSINESS_ADDITIONAL[criterion].keys())
                    )
        
        sme_score_result = calculate_sme_score(sme_selections, business_type)

# =============================
# CALCULATE BUTTON
# =============================

st.markdown("---")

col_submit, col_space = st.columns([1, 4])

with col_submit:
    submit_button = st.button("🔍 CALCULATE ELIGIBILITY", use_container_width=True, key="calc_btn")

# =============================
# RESULTS SECTION
# =============================

if submit_button:
    # Validation
    if not cnic_valid:
        st.error("❌ Invalid CNIC. Please enter a valid 13-digit CNIC.")
        st.stop()
    
    if not name:
        st.error("❌ Please enter applicant name.")
        st.stop()
    
    if income == 0:
        st.error("❌ Please enter valid monthly income.")
        st.stop()
    
    # Check scores
    if product != "Business Loan" and individual_score_result:
        if not individual_score_result["is_approved"]:
            st.markdown("---")
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-left: 5px solid #e53935; padding: 20px; border-radius: 8px; text-align: center;'>
                <h2 style='color: #c62828; margin: 0;'>❌ APPLICATION DECLINED</h2>
                <p style='color: #b71c1c; font-size: 18px; margin: 10px 0;'>Risk Grade {individual_score_result["grade"]} ({individual_score_result["grade_name"]})</p>
                <p style='color: #666;'>Applicant does not meet minimum credit quality requirements.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show banker dashboard in sidebar
            with st.sidebar:
                st.markdown("### 🔐 Banker's Confidential Dashboard")
                st.warning("For Authorized Use Only")
                st.metric("Credit Score", f"{individual_score_result['total_score']}/{individual_score_result['max_score']}")
                st.metric("Percentage Score", f"{individual_score_result['percentage']:.2f}%")
                st.metric("Risk Grade", f"{individual_score_result['grade']} - {individual_score_result['grade_name']}")
                
                with st.expander("Detailed Score Breakdown"):
                    score_df = pd.DataFrame(individual_score_result["breakdown"])
                    st.dataframe(score_df, use_container_width=True, hide_index=True)
            
            st.stop()
    
    if product == "Business Loan" and sme_score_result:
        if not sme_score_result["is_approved"]:
            st.markdown("---")
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-left: 5px solid #e53935; padding: 20px; border-radius: 8px; text-align: center;'>
                <h2 style='color: #c62828; margin: 0;'>❌ APPLICATION DECLINED</h2>
                <p style='color: #b71c1c; font-size: 18px; margin: 10px 0;'>Risk Grade {sme_score_result["grade"]} ({sme_score_result["grade_name"]})</p>
                <p style='color: #666;'>Business does not meet minimum credit quality requirements.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show banker dashboard
            with st.sidebar:
                st.markdown("### 🔐 Banker's Confidential Dashboard")
                st.warning("For Authorized Use Only")
                st.metric("Credit Score", f"{sme_score_result['total_score']}/{sme_score_result['max_score']}")
                st.metric("Percentage Score", f"{sme_score_result['percentage']:.2f}%")
                st.metric("Risk Grade", f"{sme_score_result['grade']} - {sme_score_result['grade_name']}")
                
                with st.expander("Detailed Score Breakdown"):
                    score_df = pd.DataFrame(sme_score_result["breakdown"])
                    st.dataframe(score_df, use_container_width=True, hide_index=True)
            
            st.stop()
    
    # Calculate loan eligibility
    dbr_limit = DBR[profession]
    max_emi = income * dbr_limit
    max_loan_dbr = loan_from_emi(max_emi, rate_used, months)
    
    asset_limit = asset_value * (1 - equity_pct / 100) if equity_allowed else max_loan_dbr
    
    # Staff caps
    if staff_loan:
        cap_map = {
            "Personal Loan": basic_salary * 8,
            "Auto Loan": basic_salary * 50,
            "Home Loan": basic_salary * 150,
            "Solar Loan": min(3_000_000, max_loan_dbr),
            "Business Loan": max_loan_dbr
        }
        cap = cap_map.get(product, max_loan_dbr)
    else:
        cap = max_loan_dbr
    
    # Final approval
    if product == "Business Loan":
        approved = min(requested_amount, cap, max_loan_dbr)
    else:
        approved = min(cap, asset_limit, max_loan_dbr)
    
    emi_value = emi(approved, rate_used, months)
    total_repayment = emi_value * months
    markup = total_repayment - approved
    dbr_actual = emi_value / income if income else 0
    
    # Display APPROVED decision prominently (No scores shown to applicant)
    st.markdown("---")
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-left: 5px solid #43a047; padding: 30px; border-radius: 8px; text-align: center;'>
        <h2 style='color: #2e7d32; margin: 0;'>✅ APPLICATION APPROVED</h2>
        <p style='color: #558b2f; font-size: 16px; margin: 10px 0;'>Congratulations! Your application has been approved for processing.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show banker's confidential scoring in sidebar
    with st.sidebar:
        st.markdown("### 🔐 Banker's Confidential Dashboard")
        st.warning("⚠️ For Authorized Personnel Only")
        
        if individual_score_result:
            st.metric("Credit Score", f"{individual_score_result['total_score']}/{individual_score_result['max_score']}")
            st.metric("Percentage Score", f"{individual_score_result['percentage']:.2f}%")
            st.metric("Risk Grade", f"{individual_score_result['grade']} - {individual_score_result['grade_name']}")
            
            with st.expander("📊 Score Breakdown"):
                score_df = pd.DataFrame(individual_score_result["breakdown"])
                st.dataframe(score_df, use_container_width=True, hide_index=True)
        
        if sme_score_result:
            st.metric("Credit Score", f"{sme_score_result['total_score']}/{sme_score_result['max_score']}")
            st.metric("Percentage Score", f"{sme_score_result['percentage']:.2f}%")
            st.metric("Risk Grade", f"{sme_score_result['grade']} - {sme_score_result['grade_name']}")
            
            with st.expander("📊 Score Breakdown"):
                score_df = pd.DataFrame(sme_score_result["breakdown"])
                st.dataframe(score_df, use_container_width=True, hide_index=True)
        
        st.divider()
        st.markdown(f"**Application ID:** {cnic_digits}")
        st.markdown(f"**Date:** {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    
    # LOAN OFFER DETAILS (What applicant sees)
    st.markdown("### 💰 Loan Offer Details")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Approved Loan Amount", f"PKR {approved:,.0f}")
    col2.metric("Monthly EMI", f"PKR {emi_value:,.0f}")
    col3.metric("DBR Utilization", f"{dbr_actual*100:.2f}%")
    col4.metric("Tenure", f"{tenor} Years")
    
    st.markdown("**Repayment Summary**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Repayment", f"PKR {total_repayment:,.0f}")
    col2.metric("Total Markup", f"PKR {markup:,.0f}")
    col3.metric("Interest Rate", f"{rate_used:.2%}")
    
    if equity_allowed:
        st.markdown("**Collateral Details**")
        col1, col2 = st.columns(2)
        col1.metric("Asset Value", f"PKR {asset_value:,.0f}")
        col2.metric("Equity Contribution", f"PKR {asset_value * equity_pct / 100:,.0f}")
    
    if product == "Business Loan" and business_details:
        st.markdown("**Business Information**")
        st.info(business_details)
    
    # Amortization Schedule
    st.markdown("### 📅 Amortization Schedule")
    
    df_schedule = schedule(approved, rate_used, months, emi_value)
    
    # Display first and last 12 months
    display_df = pd.concat([df_schedule.head(12), df_schedule.tail(12)])
    
    fmt_df = display_df.copy()
    for col in fmt_df.columns[1:]:
        fmt_df[col] = fmt_df[col].apply(lambda x: f"PKR {x:,.0f}")
    
    st.dataframe(fmt_df, use_container_width=True, hide_index=True)
    
    # Download button
    csv = df_schedule.to_csv(index=False)
    st.download_button(
        "📥 Download Full Amortization Schedule (CSV)",
        csv,
        f"amortization_{cnic_digits}_{datetime.now().strftime('%d%m%Y')}.csv",
        "text/csv"
    )
    
    # Terms and Conditions
    st.markdown("---")
    st.markdown("### ⚖️ Terms & Conditions")
    
    terms_col1, terms_col2 = st.columns(2)
    
    with terms_col1:
        st.markdown(f"""
        - **Loan Amount:** PKR {approved:,.0f}
        - **Tenor:** {tenor} Years ({months} months)
        - **Interest Rate:** {rate_used:.2%}
        - **Bank:** {bank if not staff_loan else 'Internal'}
        - **Processing Fee:** {PRODUCTS[product]['fee']}
        """)
    
    with terms_col2:
        st.markdown(f"""
        - **Applicant:** {name}
        - **CNIC:** {cnic_digits}
        - **Monthly EMI:** PKR {emi_value:,.0f}
        - **Total Repayment:** PKR {total_repayment:,.0f}
        - **Approval Date:** {datetime.now().strftime('%d-%m-%Y')}
        """)
    
    st.info("✓ This is a preliminary offer. Final approval is subject to document verification and compliance review.")

