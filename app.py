import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="Digital Credit Engine", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    * { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .main { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .stMetric { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); border-left: 5px solid #1e88e5; }
    h1 { color: #1a237e; border-bottom: 3px solid #1e88e5; padding-bottom: 10px; font-size: 2.5em; font-weight: 700; }
    h2 { color: #1e88e5; font-size: 1.8em; margin-top: 20px; margin-bottom: 15px; }
    h3 { color: #424242; font-size: 1.3em; }
</style>
""", unsafe_allow_html=True)

KIBOR = 12.96 / 100

DBR = {
    "Salaried": 0.40,
    "Self-Employed": 0.50,
    "Businessman": 0.50
}

PRODUCTS = {
    "Personal Loan": {"rate": 0.35, "max_tenor": 5, "equity": False},
    "Auto Loan": {"rate": KIBOR + 0.05, "max_tenor": 10, "equity": True},
    "Home Loan": {"rate": KIBOR + 0.03, "max_tenor": 20, "equity": True},
    "Solar Loan": {"rate": KIBOR + 0.05, "max_tenor": 8, "equity": True},
    "Business Loan": {"rate": KIBOR + 0.05, "max_tenor": 5, "equity": False},
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
        "Over 50 years & upto max. age as per PPMs": 5,
        "Over 30 & upto 50 years": 4,
        "Over 18 & upto 30 years": 2,
    },
    "Gender": {
        "Male": 4,
        "Female": 5,
    },
    "Marital Status": {
        "Un-married": 5,
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
        "Employees maintaining salary with BOP & 'A' category": 10,
        "Govt. Employees & 'B' category / under MOU financing": 7,
        "Employee of all other accepted employers/SEB/SEP": 4,
    },
    "Job Status": {
        "Permanent": 5,
        "Contractual": 2,
    },
    "Length of Employment/Age of Business": {
        "5 years & over": 10,
        "3 years & over": 7,
        "Less than 3 years": 4,
    },
    "Monthly Take Home Salary/Income": {
        "Above Rs.100,000-SI / Above Rs.150,000-SEB/SEP": 10,
        "Rs.50,000 & above-SI / Rs.80,000 & above-SEB/SEP": 7,
        "Below Rs.50,000-SI / Below Rs.80,000-SEB/SEP": 4,
    },
    "Type of Residence": {
        "Owned/Parents'": 5,
        "Rented": 3,
    },
    "Collateral": {
        "Leased vehicle/mortgage of property/Liquid Security": 5,
        "Personal Loans (clean)": 0,
    },
    "Debt Burden": {
        "If existing debt/burden=upto 30% of disposable income": 5,
        "If existing debt/burden=40% of disposable income": 3,
        "If existing debt/burden=50% of disposable income": 1,
    },
    "Repayment History": {
        "If no default during last 12 months": 15,
        "1 Instance of OD-30/60/90 days (No current existence)": 10,
        "2 Instances of OD-30/60/90 days (No current existence)/ No credit history": 6,
        "3 or more instances of OD-30/60/90 days": 0,
    },
    "Length of Credit History": {
        "Over 5 years": 5,
        "From 3-5 years": 4,
        "Less than 3 years / No Previous Credit History": 2,
    },
}

# =============================
# SME NEW BUSINESS (EXACT FROM EXCEL)
# =============================

SME_NEW_BUSINESS_CRITERIA = {
    "Business Commitment": {
        "Full Time": 100,
        "Part Time": 50,
    },
    "Age": {
        "42 - 60": 50,
        "39-41.9": 45,
        "35-38.9": 40,
        "30-34.9": 30,
        "25-29.9": 25,
        "Not Applicable in case of Entities": 50,
    },
    "Credit Turnover Of Existing Limit With Any Bank": {
        "No such requirement - Logistics loans": 100,
        "No such Limit Availed from any bank": 100,
        "More than 4 times of RF Limit": 100,
        "More than 3 times of RF Limit": 80,
        "More than 2 times of RF limit": 50,
        "2 times or less of the RF limit": 30,
    },
    "Experience": {
        "Relevant Experience - > 3 Years": 100,
        "Relevant Experience -1- 3 years": 80,
        "No Experience but has family background in the chosen business.": 70,
        "Unrelated work experience": 50,
        "Applicant has never worked": 0,
    },
    "Present Employment Status": {
        "Employed in Relevant Job": 50,
        "Working in relevant family owned business": 50,
        "Employed in non-relevant job": 25,
        "Previous relevant experience": 35,
        "Applicant has Never Worked / Un-Employed": 0,
    },
    "Training": {
        "Trained & Certified": 100,
        "Training not required": 100,
        "Trained in Relevant Field but not certified (No evidence)": 80,
        "Not Trained": 0,
        "Not Applicable in case of Entities": 100,
    },
    "License/ Certification/ Permission": {
        "Required & Held": 100,
        "No such requirement": 100,
        "Required But not Held": 0,
        "license Required but Learner Held": 60,
        "license Required but Held in Drivers name (in case of logistic companies)": 100,
        "license Required and is applied (other than Logistics) supported by evidence": 60,
    },
    "Applicant's Understanding": {
        "Absolutely clear and perfect": 100,
        "Good but not perfect": 50,
        "Very little or no understanding": -100,
    },
    "Applicant's Business Place": {
        "Logistics Business - Not required in case of new business": 100,
        "Owned - Documents Provided (Self/business/company)": 100,
        "Family owned - Document Provided": 80,
        "Owned / Family owned- Documents not Provided": 60,
        "Rented  - Document Provided (Self/business/company)": 50,
        "Rented  - Document Not Provided": 40,
        "To be rented": 20,
    },
    "Debt Burden Ratio": {
        "20% <": 100,
        "20% - 30%": 90,
        "30% - 40%": 80,
        "40% - 50%": 70,
        "Exceeding 50%": -1800,
    },
    "Vehicle Ownership": {
        "Car / Tractor / Morotrcycle / Any registered Vehicle": 50,
        "Family Owned (Father/Husband/ Mother/Wife)": 40,
        "Not Applicable for Logistic loan": 50,
        "No vehicle owned by applicant": 0,
        "Not Applicable in case of Entities": 50,
    },
    "Is Sim on your Name": {
        "Yes": 100,
        "No": -1800,
    },
    "Tax Filer": {
        "NTN held and Filer": 100,
        "No NTN as Business located / to be established in TAX EXPEMTED ZONES": 80,
        "NTN held and NON-Filer": 40,
        "No NTN held and NON-Filer": 0,
    },
    "Security": {
        "Vehicle in case of Logistics": 100,
        "Mortgage of self-occupied residential/ Commercial/ Industrial / land": 100,
        "Mortgage of partly-rented residential/ Commercial / Industrial property": 80,
        "Mortgage of Rural / Agri Property": 70,
        "Mortgage of rented residential / Commercial / Industrial property": 60,
        "Liquid security / Near Cash Security": 100,
    },
}

# =============================
# SME EXISTING BUSINESS (EXACT FROM EXCEL)
# =============================

SME_EXISTING_BUSINESS_CRITERIA = {
    "Business Commitment": {
        "Full Time": 100,
        "Part Time": 50,
    },
    "Age": {
        "42 - 60": 50,
        "39-41.9": 45,
        "35-38.9": 40,
        "30-34.9": 30,
        "25-29.9": 25,
        "Not Applicable in case of Entities": 50,
    },
    "Training": {
        "Trained & Certified in Relevant Field - Evidence Provided": 100,
        "Training not required": 100,
        "Trained in Relevant Field but not certified (No evidence)": 80,
        "Not Trained": 0,
        "Not Applicable in case of Entities": 100,
    },
    "License/ Certification/ Permission": {
        "Required & Held": 100,
        "No such requirement": 100,
        "Required But not Held": 0,
        "license Required but Learner Held": 60,
        "license Required but Held in Drivers name (in case of logistic companies)": 100,
        "license Required and is applied (other than Logistics) supported by evidence": 60,
    },
    "Vehicle Ownership": {
        "Car / Tractor / Morotrcycle / Any registered Vehicle": 60,
        "Family Owned (Father/Husband/ Mother/Wife)": 40,
        "Not Applicable for Logistic loan": 60,
        "No vehicle owned by applicant": 0,
        "Not Applicable in case of Entities": 60,
    },
    "Applicants Business Outlook": {
        "Positive": 100,
        "Neutral": 50,
        "Negative": -200,
    },
    "Debt Burden Ratio": {
        "20% <": 100,
        "20% - 30%": 90,
        "30% - 40%": 80,
        "40% - 50%": 70,
        "Exceeding 50%": -1800,
    },
    "Tax Filer Status": {
        "NTN held and Filer": 60,
        "No NTN as Business located / to be established in TAX EXPEMTED ZONES": 50,
        "NTN held and NON-Filer": 40,
        "No NTN held and NON-Filer": 0,
    },
    "Security": {
        "Vehicle in case of Logistics": 100,
        "Mortgage of self-occupied residential/ Commercial/ Industrial / land": 100,
        "Mortgage of partly-rented residential/ Commercial / Industrial property": 80,
        "Mortgage of Rural / Agri Property": 70,
        "Mortgage of rented residential / Commercial / Industrial property": 60,
        "Liquid security / Near Cash Security": 100,
    },
    "Applicant'S Business Place": {
        "Logistics Business - Not required in case of new business": 100,
        "Owned - Documents Provided (Self/business/company)": 100,
        "Family owned - Document Provided": 80,
        "Owned / Family owned- Documents not Provided": 60,
        "Rented  - Document Provided (Self/business/company)": 50,
        "Rented  - Document Not Provided": 40,
        "To be rented": 20,
    },
    "Is Sim On Customer Name": {
        "Yes": 100,
        "No": -1800,
    },
    "Length Of Business Existence": {
        "More than 5 Years": 100,
        "2 - 5 Years": 80,
        "1 - 2 Years": 25,
        "Less than 1 Year": 0,
    },
    "Accounts": {
        "Prepared by Chartered Accountant": 100,
        "Prepared by Professional Accountant": 90,
        "Self prepared": 80,
        "Mandatory PR Requirement but not provided": -1800,
        "No Scuh Mandatory requirement": 100,
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
    "Applicant'S Bank Account": {
        "Yes - Evidence provided": 80,
        "Yes - Evidence not provided": 40,
        "No such requirement": 80,
        "No Bank Account": 0,
    },
    "Credit Turnover Of Existing Limit With Any Bank": {
        "No such requirement - Logistics loans": 100,
        "No such Limit Availed from any bank": 100,
        "More than 4 times of RF Limit": 100,
        "More than 3 times of RF Limit": 80,
        "More than 2 times of RF limit": 50,
        "2 times or less of the RF limit": 30,
    },
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
    """Calculate individual scorecard"""
    score_breakdown = []
    total_score = 0
    
    for criterion, selected_option in selections.items():
        if selected_option and selected_option in INDIVIDUAL_CRITERIA[criterion]:
            score = INDIVIDUAL_CRITERIA[criterion][selected_option]
            score_breakdown.append({
                "Criterion": criterion,
                "Selected": selected_option,
                "Score": score
            })
            total_score += score
    
    max_score = 100
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    if percentage >= 96:
        grade, grade_name = 1, "Exceptional"
    elif percentage >= 91:
        grade, grade_name = 2, "Superior"
    elif percentage >= 81:
        grade, grade_name = 3, "Very Good"
    elif percentage >= 71:
        grade, grade_name = 4, "Good"
    elif percentage >= 61:
        grade, grade_name = 5, "Satisfactory"
    elif percentage >= 51:
        grade, grade_name = 6, "Acceptable"
    elif percentage >= 41:
        grade, grade_name = 7, "Marginal"
    elif percentage >= 31:
        grade, grade_name = 8, "Watch List"
    elif percentage >= 21:
        grade, grade_name = 9, "Substandard"
    elif percentage >= 11:
        grade, grade_name = 10, "Doubtful"
    else:
        grade, grade_name = 12, "Loss"
    
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

def calculate_sme_score(selections, business_type):
    """Calculate SME scorecard"""
    score_breakdown = []
    total_score = 0
    
    criteria = SME_EXISTING_BUSINESS_CRITERIA if business_type == "Existing Business" else SME_NEW_BUSINESS_CRITERIA
    max_score = 1530 if business_type == "Existing Business" else 1250
    
    for criterion, selected_option in selections.items():
        if criterion in criteria and selected_option:
            if selected_option in criteria[criterion]:
                score = criteria[criterion][selected_option]
                score_breakdown.append({
                    "Criterion": criterion,
                    "Selected": selected_option,
                    "Score": score
                })
                total_score += score
    
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    if percentage >= 90:
        grade, grade_name = 1, "Exceptional"
    elif percentage >= 80:
        grade, grade_name = 2, "Superior"
    elif percentage >= 70:
        grade, grade_name = 3, "Very Good"
    elif percentage >= 60:
        grade, grade_name = 4, "Good"
    elif percentage >= 55:
        grade, grade_name = 5, "Satisfactory"
    elif percentage >= 50:
        grade, grade_name = 6, "Acceptable"
    elif percentage >= 40:
        grade, grade_name = 7, "Marginal"
    elif percentage >= 30:
        grade, grade_name = 8, "Watch List"
    elif percentage >= 20:
        grade, grade_name = 9, "Substandard"
    elif percentage >= 6:
        grade, grade_name = 11, "Doubtful"
    else:
        grade, grade_name = 12, "Loss"
    
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
# MAIN APP
# =============================

col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown("""
    <div style='text-align: center; padding: 20px;'>
        <h1 style='margin: 0; color: #1a237e;'>🏦 DIGITAL CREDIT ENGINE</h1>
        <p style='color: #1e88e5; font-size: 14px; margin: 5px 0;'>Intelligent Loan Underwriting Platform</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("### 👤 Applicant Information")

c1, c2, c3 = st.columns(3)

with c1:
    name = st.text_input("Full Name *", key="name")

with c2:
    cnic_raw = st.text_input("CNIC (13 digits only) *", key="cnic", placeholder="12345678901234")
    cnic_digits = re.sub(r"\D", "", cnic_raw)
    cnic_valid = len(cnic_digits) == 13
    if cnic_raw and not cnic_valid:
        st.error(f"⚠️ CNIC must be exactly 13 digits (you entered {len(cnic_digits)})")

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

c7, c8 = st.columns(2)

with c7:
    experience_years = st.number_input("Experience (Years) *", min_value=0, value=0)

with c8:
    staff_loan = False
    if profession == "Salaried":
        staff_loan = st.checkbox("✓ Staff Loan Eligible")
        if staff_loan:
            basic_salary = st.number_input("Basic Salary (PKR)", min_value=0, value=0)
        else:
            basic_salary = 0
    else:
        basic_salary = 0

st.markdown("### 💳 Loan Product Details")

c1, c2 = st.columns(2)

with c1:
    allowed_products = ["Personal Loan", "Auto Loan", "Home Loan", "Solar Loan"] if profession == "Salaried" else ["Personal Loan", "Auto Loan", "Home Loan", "Solar Loan", "Business Loan"]
    product = st.selectbox("Select Loan Product *", allowed_products)

with c2:
    if staff_loan:
        staff_tenor = {"Personal Loan": 7, "Auto Loan": 10, "Home Loan": 25, "Solar Loan": 20}
        tenor = staff_tenor.get(product, 5)
        st.info(f"Tenor: {tenor} Years (Staff Fixed)")
    else:
        base_tenor = PRODUCTS[product]["max_tenor"]
        tenor = st.selectbox("Tenor (Years) *", list(range(1, base_tenor + 1)))

months = tenor * 12

st.markdown("**Loan Amount & Details**")
desired_amount = st.number_input("Desired Loan Amount (PKR) *", min_value=0, value=0)

if not staff_loan:
    c1, c2 = st.columns(2)
    with c1:
        bank = st.selectbox("Bank", BANKS)
    with c2:
        relationship_years = st.number_input("Relationship with Bank (Years)", min_value=0, value=0)

asset_value = 0
equity_pct = 0

if PRODUCTS[product]["equity"]:
    c1, c2 = st.columns(2)
    with c1:
        asset_value = st.number_input("Asset Value (PKR)", min_value=0, value=0)
    with c2:
        equity_pct = st.slider("Equity % Required", 20, 50, 20)

st.markdown("---")
st.markdown("### 📊 Credit Risk Assessment")

individual_score_result = None
sme_score_result = None

if product != "Business Loan":
    with st.expander("📋 **Individual Scorecard Assessment**", expanded=True):
        st.info("Complete all fields below for credit evaluation")
        
        ind_selections = {}
        c1, c2 = st.columns(2)
        
        with c1:
            ind_selections["Age of Borrower"] = st.selectbox("Age of Borrower", list(INDIVIDUAL_CRITERIA["Age of Borrower"].keys()))
            ind_selections["Gender"] = st.selectbox("Gender", list(INDIVIDUAL_CRITERIA["Gender"].keys()))
            ind_selections["Marital Status"] = st.selectbox("Marital Status", list(INDIVIDUAL_CRITERIA["Marital Status"].keys()))
            ind_selections["No. of Dependents"] = st.selectbox("No. of Dependents", list(INDIVIDUAL_CRITERIA["No. of Dependents"].keys()))
            ind_selections["Qualification"] = st.selectbox("Qualification", list(INDIVIDUAL_CRITERIA["Qualification"].keys()))
            ind_selections["Type of Occupation"] = st.selectbox("Type of Occupation", list(INDIVIDUAL_CRITERIA["Type of Occupation"].keys()))
            ind_selections["Job Status"] = st.selectbox("Job Status", list(INDIVIDUAL_CRITERIA["Job Status"].keys()))
        
        with c2:
            ind_selections["Length of Employment/Age of Business"] = st.selectbox("Length of Employment", list(INDIVIDUAL_CRITERIA["Length of Employment/Age of Business"].keys()))
            ind_selections["Monthly Take Home Salary/Income"] = st.selectbox("Monthly Take Home Salary/Income", list(INDIVIDUAL_CRITERIA["Monthly Take Home Salary/Income"].keys()))
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
        
        c1, c2 = st.columns(2)
        for idx, param in enumerate(params):
            if idx % 2 == 0:
                c1, c2 = st.columns(2)
            with (c1 if idx % 2 == 0 else c2):
                sme_selections[param] = st.selectbox(param, list(criteria[param].keys()))
        
        sme_score_result = calculate_sme_score(sme_selections, business_type)

st.markdown("---")

col_submit, col_space = st.columns([1, 4])
with col_submit:
    submit_button = st.button("🔍 CALCULATE ELIGIBILITY", use_container_width=True)

# =============================
# RESULTS
# =============================

if submit_button:
    if not cnic_valid:
        st.error(f"❌ CNIC must be exactly 13 digits")
        st.stop()
    
    if not name or income == 0 or desired_amount == 0:
        st.error("❌ Please fill all required fields")
        st.stop()
    
    # Check scores
    if product != "Business Loan" and individual_score_result:
        if not individual_score_result["is_approved"]:
            st.markdown("---")
            st.error(f"❌ APPLICATION DECLINED")
            
            with st.sidebar:
                st.markdown("### 🔐 Banker's Confidential Dashboard")
                st.warning("For Authorized Use Only")
                st.metric("Credit Score", f"{individual_score_result['total_score']}/{individual_score_result['max_score']}")
                st.metric("% Score", f"{individual_score_result['percentage']:.2f}%")
                st.metric("Risk Grade", f"{individual_score_result['grade']} - {individual_score_result['grade_name']}")
                with st.expander("Score Breakdown"):
                    st.dataframe(pd.DataFrame(individual_score_result["breakdown"]), use_container_width=True, hide_index=True)
            st.stop()
    
    if product == "Business Loan" and sme_score_result:
        if not sme_score_result["is_approved"]:
            st.markdown("---")
            st.error(f"❌ APPLICATION DECLINED")
            
            with st.sidebar:
                st.markdown("### 🔐 Banker's Confidential Dashboard")
                st.warning("For Authorized Use Only")
                st.metric("Credit Score", f"{sme_score_result['total_score']}/{sme_score_result['max_score']}")
                st.metric("% Score", f"{sme_score_result['percentage']:.2f}%")
                st.metric("Risk Grade", f"{sme_score_result['grade']} - {sme_score_result['grade_name']}")
                with st.expander("Score Breakdown"):
                    st.dataframe(pd.DataFrame(sme_score_result["breakdown"]), use_container_width=True, hide_index=True)
            st.stop()
    
    # =============================
    # NEW DBR LOGIC - SIDE-BY-SIDE COMPARISON
    # =============================
    
    rate_used = 0.05 if staff_loan else PRODUCTS[product]["rate"]
    dbr_limit = DBR[profession]
    
    # CALCULATE ACTUAL DBR FOR DESIRED AMOUNT
    desired_emi = emi(desired_amount, rate_used, months)
    desired_dbr = (desired_emi / income * 100) if income > 0 else 0
    
    # CALCULATE MAX AVAILABLE BASED ON DBR LIMIT
    max_emi_allowed = income * dbr_limit
    max_available = loan_from_emi(max_emi_allowed, rate_used, months)
    max_available_emi = emi(max_available, rate_used, months)
    
    # APPLY ASSET CONSTRAINT IF APPLICABLE
    if PRODUCTS[product]["equity"]:
        asset_limit = asset_value * (1 - equity_pct / 100)
        max_available = min(max_available, asset_limit)
    
    # APPLY STAFF CAPS IF APPLICABLE
    if staff_loan:
        staff_caps = {
            "Personal Loan": basic_salary * 8,
            "Auto Loan": basic_salary * 50,
            "Home Loan": basic_salary * 150,
            "Solar Loan": min(3_000_000, max_available),
        }
        max_available = min(max_available, staff_caps.get(product, max_available))
    
    # FOR BUSINESS LOAN, CAP AT REQUESTED AMOUNT
    if product == "Business Loan":
        max_available = min(max_available, desired_amount)
    
    # FINAL APPROVED AMOUNT
    if desired_dbr <= dbr_limit * 100:
        approved = desired_amount
        approval_status = "✅ APPROVED"
    elif desired_amount > max_available:
        approved = max_available
        approval_status = "⚠️ APPROVED (Less than Desired)"
    else:
        approved = desired_amount
        approval_status = "✅ APPROVED"
    
    # RECALCULATE FOR APPROVED AMOUNT
    approved_emi = emi(approved, rate_used, months)
    approved_dbr = (approved_emi / income * 100) if income > 0 else 0
    total_repayment = approved_emi * months
    markup = total_repayment - approved
    
    # =============================
    # DISPLAY APPROVAL STATUS
    # =============================
    
    st.markdown("---")
    if approved_dbr <= dbr_limit * 100:
        st.success(f"✅ APPLICATION APPROVED")
    else:
        st.warning(f"⚠️ APPROVAL WITH MODIFICATIONS")
    
    # =============================
    # BANKER'S CONFIDENTIAL DASHBOARD
    # =============================
    
    with st.sidebar:
        st.markdown("### 🔐 Banker's Confidential Dashboard")
        st.warning("⚠️ For Authorized Personnel Only")
        
        if individual_score_result:
            st.metric("Credit Score", f"{individual_score_result['total_score']}/{individual_score_result['max_score']}")
            st.metric("% Score", f"{individual_score_result['percentage']:.2f}%")
            st.metric("Risk Grade", f"{individual_score_result['grade']} - {individual_score_result['grade_name']}")
            with st.expander("📊 Score Breakdown"):
                st.dataframe(pd.DataFrame(individual_score_result["breakdown"]), use_container_width=True, hide_index=True)
        
        if sme_score_result:
            st.metric("Credit Score", f"{sme_score_result['total_score']}/{sme_score_result['max_score']}")
            st.metric("% Score", f"{sme_score_result['percentage']:.2f}%")
            st.metric("Risk Grade", f"{sme_score_result['grade']} - {sme_score_result['grade_name']}")
            with st.expander("📊 Score Breakdown"):
                st.dataframe(pd.DataFrame(sme_score_result["breakdown"]), use_container_width=True, hide_index=True)
        
        st.divider()
        st.markdown(f"**CNIC:** {cnic_digits}")
        st.markdown(f"**Date:** {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    
    # =============================
    # SIDE-BY-SIDE LOAN COMPARISON (APPLICANT SEES)
    # =============================
    
    st.markdown("### 💰 Loan Comparison - Desired vs Available")
    
    comp_col1, comp_col2, comp_col3 = st.columns(3)
    
    with comp_col1:
        st.markdown("**YOU DESIRED**")
        st.metric("Loan Amount", f"PKR {desired_amount:,.0f}")
        st.metric("Monthly EMI", f"PKR {desired_emi:,.0f}")
        st.metric("DBR Required", f"{desired_dbr:.2f}%", delta=f"Limit: {dbr_limit*100:.0f}%")
    
    with comp_col2:
        if desired_amount != approved:
            st.markdown("**YOU CAN GET**")
            st.metric("Loan Amount", f"PKR {max_available:,.0f}", delta=f"({max_available - desired_amount:,.0f})" if max_available > desired_amount else f"({max_available - desired_amount:,.0f})")
            st.metric("Monthly EMI", f"PKR {emi(max_available, rate_used, months):,.0f}")
            st.metric("DBR at Max", f"{(emi(max_available, rate_used, months) / income * 100):.2f}%")
        else:
            st.markdown("**APPROVED AMOUNT**")
            st.metric("Loan Amount", f"PKR {approved:,.0f}")
            st.metric("Monthly EMI", f"PKR {approved_emi:,.0f}")
            st.metric("DBR Utilization", f"{approved_dbr:.2f}%")
    
    with comp_col3:
        if desired_dbr > dbr_limit * 100:
            st.warning("⚠️ Desired DBR exceeds limit")
            st.info(f"Max feasible: PKR {max_available:,.0f}")
        else:
            st.success("✓ DBR within limit")
            if desired_amount < max_available:
                st.info(f"You can also borrow up to PKR {max_available:,.0f}")
    
    # =============================
    # FINAL LOAN OFFER
    # =============================
    
    st.markdown("---")
    st.markdown("### 💼 Final Loan Offer")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Approved Amount", f"PKR {approved:,.0f}")
    col2.metric("Monthly EMI", f"PKR {approved_emi:,.0f}")
    col3.metric("DBR", f"{approved_dbr:.2f}%")
    col4.metric("Tenure", f"{tenor} Years")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Repayment", f"PKR {total_repayment:,.0f}")
    col2.metric("Total Markup", f"PKR {markup:,.0f}")
    col3.metric("Interest Rate", f"{rate_used:.2%} p.a.")
    
    if PRODUCTS[product]["equity"]:
        st.markdown("**Collateral Details**")
        col1, col2 = st.columns(2)
        col1.metric("Asset Value", f"PKR {asset_value:,.0f}")
        col2.metric("Equity Contribution", f"PKR {asset_value * equity_pct / 100:,.0f}")
    
    # Amortization Schedule
    st.markdown("### 📅 Amortization Schedule")
    
    df_schedule = schedule(approved, rate_used, months, approved_emi)
    display_df = pd.concat([df_schedule.head(12), df_schedule.tail(12)]) if months > 24 else df_schedule
    
    fmt_df = display_df.copy()
    for col in fmt_df.columns[1:]:
        fmt_df[col] = fmt_df[col].apply(lambda x: f"PKR {x:,.0f}")
    
    st.dataframe(fmt_df, use_container_width=True, hide_index=True)
    
    csv = df_schedule.to_csv(index=False)
    st.download_button("📥 Download Full Schedule", csv, f"schedule_{cnic_digits}_{datetime.now().strftime('%d%m%Y')}.csv", "text/csv")
    
    # Summary
    st.markdown("---")
    st.markdown("### ⚖️ Offer Summary")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        - **Approved Amount:** PKR {approved:,.0f}
        - **Tenor:** {tenor} Years
        - **Interest Rate:** {rate_used:.2%}
        - **Monthly EMI:** PKR {approved_emi:,.0f}
        """)
    
    with col2:
        st.markdown(f"""
        - **Applicant:** {name}
        - **CNIC:** {cnic_digits}
        - **Total Repayment:** PKR {total_repayment:,.0f}
        - **Approval Date:** {datetime.now().strftime('%d-%m-%Y')}
        """)
    
    st.info("✓ This is a preliminary offer. Final approval is subject to document verification and compliance review.")
