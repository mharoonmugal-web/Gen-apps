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
# INDIVIDUAL SCORING MODEL
# =============================

INDIVIDUAL_SCORE_CRITERIA = {
    "Age of Borrower": {
        "Over 50 years": {"score": 5, "weight": 0.05},
        "Over 30 & upto 50 years": {"score": 4, "weight": 0.05},
        "Over 18 & upto 30 years": {"score": 2, "weight": 0.05},
    },
    "Gender": {
        "Male": {"score": 4, "weight": 0.05},
        "Female": {"score": 5, "weight": 0.05},
    },
    "Marital Status": {
        "Unmarried": {"score": 5, "weight": 0.05},
        "Married": {"score": 3, "weight": 0.05},
    },
    "Dependents": {
        "Upto 3": {"score": 5, "weight": 0.05},
        "4 to 5": {"score": 3, "weight": 0.05},
        "More than 5": {"score": 1, "weight": 0.05},
    },
    "Qualification": {
        "Masters & Above": {"score": 10, "weight": 0.10},
        "Graduate": {"score": 8, "weight": 0.10},
        "Below Graduate": {"score": 5, "weight": 0.10},
    },
    "Type of Occupation": {
        "Employees maintaining salary with BOP & A category": {"score": 10, "weight": 0.10},
        "Govt. Employees & B category / under MOU financing": {"score": 7, "weight": 0.10},
        "Employee of all other accepted employers": {"score": 4, "weight": 0.10},
    },
    "Job Status": {
        "Permanent": {"score": 5, "weight": 0.05},
        "Contractual": {"score": 2, "weight": 0.05},
    },
    "Employment Length": {
        "5 years & over": {"score": 10, "weight": 0.10},
        "3 years & over": {"score": 7, "weight": 0.10},
        "Less than 3 years": {"score": 4, "weight": 0.10},
    },
    "Monthly Income": {
        "Above Rs.100,000": {"score": 10, "weight": 0.10},
        "Rs.50,000 & above": {"score": 7, "weight": 0.10},
        "Below Rs.50,000": {"score": 4, "weight": 0.10},
    },
    "Type of Residence": {
        "Owned/Parents'": {"score": 5, "weight": 0.05},
        "Rented": {"score": 3, "weight": 0.05},
    },
    "Collateral": {
        "Leased vehicle/mortgage/Liquid Security": {"score": 5, "weight": 0.05},
        "Personal Loans (clean)": {"score": 0, "weight": 0.05},
    },
    "Debt Burden": {
        "Upto 30%": {"score": 5, "weight": 0.05},
        "40%": {"score": 3, "weight": 0.05},
        "50%": {"score": 1, "weight": 0.05},
    },
    "Repayment History": {
        "No default last 12 months": {"score": 15, "weight": 0.15},
        "1 Instance of OD": {"score": 10, "weight": 0.15},
        "2 Instances of OD": {"score": 6, "weight": 0.15},
        "3+ Instances of OD": {"score": 0, "weight": 0.15},
    },
    "Credit History Length": {
        "Over 5 years": {"score": 5, "weight": 0.05},
        "From 3-5 years": {"score": 4, "weight": 0.05},
        "Less than 3 years": {"score": 2, "weight": 0.05},
    },
}

# =============================
# SME SCORING MODEL
# =============================

SME_SCORE_CRITERIA = {
    "Business Commitment": {
        "Full Time": {"score": 100},
        "Part Time": {"score": 50},
    },
    "Age": {
        "42 - 60": {"score": 50},
        "39 - 41": {"score": 45},
        "35 - 38": {"score": 40},
        "30 - 34": {"score": 30},
        "25 - 29": {"score": 25},
    },
    "Experience": {
        "Relevant Experience > 3 Years": {"score": 100},
        "Relevant Experience 1-3 Years": {"score": 80},
        "Family background in business": {"score": 70},
        "Unrelated work experience": {"score": 50},
        "Never worked": {"score": 0},
    },
    "Training": {
        "Trained & Certified": {"score": 100},
        "Training not required": {"score": 100},
        "Trained but not certified": {"score": 80},
        "Not Trained": {"score": 0},
    },
    "License/Certification": {
        "Required & Held": {"score": 100},
        "No such requirement": {"score": 100},
        "Required but not Held": {"score": 0},
        "Learner Held": {"score": 60},
        "License Applied": {"score": 60},
    },
    "Vehicle Ownership": {
        "Own registered vehicle": {"score": 60},
        "Family Owned": {"score": 40},
        "Not Applicable": {"score": 50},
        "No vehicle": {"score": 0},
    },
    "Business Outlook": {
        "Positive": {"score": 100},
        "Neutral": {"score": 50},
        "Negative": {"score": -200},
    },
    "Debt Burden Ratio": {
        "20% or less": {"score": 100},
        "20% - 30%": {"score": 90},
        "30% - 40%": {"score": 80},
        "40% - 50%": {"score": 70},
        "Exceeding 50%": {"score": -1800},
    },
    "Tax Filer Status": {
        "NTN held and Filer": {"score": 100},
        "Tax Exempted Zone": {"score": 80},
        "NTN held NON-Filer": {"score": 40},
        "No NTN": {"score": 0},
    },
    "Security": {
        "Vehicle": {"score": 100},
        "Owned property": {"score": 100},
        "Partly rented property": {"score": 80},
        "Rural/Agri Property": {"score": 70},
        "Rented property": {"score": 60},
        "Liquid security": {"score": 100},
    },
    "Business Premise": {
        "Owned": {"score": 100},
        "Family owned": {"score": 80},
        "Owned no docs": {"score": 60},
        "Rented with docs": {"score": 50},
        "Rented no docs": {"score": 40},
        "To be rented": {"score": 20},
    },
    "Credit Turnover": {
        "No requirement": {"score": 100},
        "No limit availed": {"score": 100},
        "More than 4x RF": {"score": 100},
        "More than 3x RF": {"score": 80},
        "More than 2x RF": {"score": 50},
        "2x or less RF": {"score": 30},
    },
    "SIM Registration": {
        "Yes": {"score": 100},
        "No": {"score": -1800},
    },
}

SME_EXISTING_BUSINESS_CRITERIA = {
    "Business Existence": {
        "More than 5 Years": {"score": 100},
        "2 - 5 Years": {"score": 80},
        "1 - 2 Years": {"score": 25},
        "Less than 1 Year": {"score": 0},
    },
    "Accounts": {
        "Chartered Accountant": {"score": 100},
        "Professional Accountant": {"score": 90},
        "Self prepared": {"score": 80},
        "Not provided": {"score": 50},
    },
    "Revenues": {
        "Growing": {"score": 100},
        "Stagnant": {"score": 80},
        "Declined upto 30%": {"score": 60},
        "Declined more than 30%": {"score": 0},
    },
    "Profitability": {
        "Growing": {"score": 80},
        "Static": {"score": 60},
        "Declined upto 30%": {"score": 40},
        "Declined more than 30%": {"score": 0},
    },
    "Bank Account": {
        "Yes with evidence": {"score": 80},
        "Yes without evidence": {"score": 40},
        "No account": {"score": 0},
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


def calculate_individual_score(age_group, gender, marital_status, dependents, 
                               qualification, occupation, job_status, employment_years,
                               income, residence, collateral, debt_burden, 
                               repayment_history, credit_history):
    """Calculate credit score for Individual"""
    
    score_data = []
    total_score = 0
    max_score = 0
    
    # Age scoring
    age_score = INDIVIDUAL_SCORE_CRITERIA["Age of Borrower"].get(age_group, {}).get("score", 0)
    age_weight = INDIVIDUAL_SCORE_CRITERIA["Age of Borrower"].get(age_group, {}).get("weight", 0)
    score_data.append(["Age of Borrower", age_group, age_score, 5, age_score])
    total_score += age_score * age_weight
    max_score += 5
    
    # Gender scoring
    gender_score = INDIVIDUAL_SCORE_CRITERIA["Gender"].get(gender, {}).get("score", 0)
    gender_weight = INDIVIDUAL_SCORE_CRITERIA["Gender"].get(gender, {}).get("weight", 0)
    score_data.append(["Gender", gender, gender_score, 5, gender_score])
    total_score += gender_score * gender_weight
    max_score += 5
    
    # Marital Status
    marital_score = INDIVIDUAL_SCORE_CRITERIA["Marital Status"].get(marital_status, {}).get("score", 0)
    marital_weight = INDIVIDUAL_SCORE_CRITERIA["Marital Status"].get(marital_status, {}).get("weight", 0)
    score_data.append(["Marital Status", marital_status, marital_score, 5, marital_score])
    total_score += marital_score * marital_weight
    max_score += 5
    
    # Dependents
    dependents_score = INDIVIDUAL_SCORE_CRITERIA["Dependents"].get(dependents, {}).get("score", 0)
    dependents_weight = INDIVIDUAL_SCORE_CRITERIA["Dependents"].get(dependents, {}).get("weight", 0)
    score_data.append(["No. of Dependents", dependents, dependents_score, 5, dependents_score])
    total_score += dependents_score * dependents_weight
    max_score += 5
    
    # Qualification
    qual_score = INDIVIDUAL_SCORE_CRITERIA["Qualification"].get(qualification, {}).get("score", 0)
    qual_weight = INDIVIDUAL_SCORE_CRITERIA["Qualification"].get(qualification, {}).get("weight", 0)
    score_data.append(["Qualification", qualification, qual_score, 10, qual_score])
    total_score += qual_score * qual_weight
    max_score += 10
    
    # Occupation
    occ_score = INDIVIDUAL_SCORE_CRITERIA["Type of Occupation"].get(occupation, {}).get("score", 0)
    occ_weight = INDIVIDUAL_SCORE_CRITERIA["Type of Occupation"].get(occupation, {}).get("weight", 0)
    score_data.append(["Type of Occupation", occupation, occ_score, 10, occ_score])
    total_score += occ_score * occ_weight
    max_score += 10
    
    # Job Status
    job_score = INDIVIDUAL_SCORE_CRITERIA["Job Status"].get(job_status, {}).get("score", 0)
    job_weight = INDIVIDUAL_SCORE_CRITERIA["Job Status"].get(job_status, {}).get("weight", 0)
    score_data.append(["Job Status", job_status, job_score, 5, job_score])
    total_score += job_score * job_weight
    max_score += 5
    
    # Employment Length
    emp_score = INDIVIDUAL_SCORE_CRITERIA["Employment Length"].get(employment_years, {}).get("score", 0)
    emp_weight = INDIVIDUAL_SCORE_CRITERIA["Employment Length"].get(employment_years, {}).get("weight", 0)
    score_data.append(["Length of Employment", employment_years, emp_score, 10, emp_score])
    total_score += emp_score * emp_weight
    max_score += 10
    
    # Income
    income_score = INDIVIDUAL_SCORE_CRITERIA["Monthly Income"].get(income, {}).get("score", 0)
    income_weight = INDIVIDUAL_SCORE_CRITERIA["Monthly Income"].get(income, {}).get("weight", 0)
    score_data.append(["Monthly Income", income, income_score, 10, income_score])
    total_score += income_score * income_weight
    max_score += 10
    
    # Residence
    res_score = INDIVIDUAL_SCORE_CRITERIA["Type of Residence"].get(residence, {}).get("score", 0)
    res_weight = INDIVIDUAL_SCORE_CRITERIA["Type of Residence"].get(residence, {}).get("weight", 0)
    score_data.append(["Type of Residence", residence, res_score, 5, res_score])
    total_score += res_score * res_weight
    max_score += 5
    
    # Collateral
    coll_score = INDIVIDUAL_SCORE_CRITERIA["Collateral"].get(collateral, {}).get("score", 0)
    coll_weight = INDIVIDUAL_SCORE_CRITERIA["Collateral"].get(collateral, {}).get("weight", 0)
    score_data.append(["Collateral", collateral, coll_score, 5, coll_score])
    total_score += coll_score * coll_weight
    max_score += 5
    
    # Debt Burden
    debt_score = INDIVIDUAL_SCORE_CRITERIA["Debt Burden"].get(debt_burden, {}).get("score", 0)
    debt_weight = INDIVIDUAL_SCORE_CRITERIA["Debt Burden"].get(debt_burden, {}).get("weight", 0)
    score_data.append(["Debt Burden", debt_burden, debt_score, 5, debt_score])
    total_score += debt_score * debt_weight
    max_score += 5
    
    # Repayment History
    repay_score = INDIVIDUAL_SCORE_CRITERIA["Repayment History"].get(repayment_history, {}).get("score", 0)
    repay_weight = INDIVIDUAL_SCORE_CRITERIA["Repayment History"].get(repayment_history, {}).get("weight", 0)
    score_data.append(["Repayment History", repayment_history, repay_score, 15, repay_score])
    total_score += repay_score * repay_weight
    max_score += 15
    
    # Credit History
    ch_score = INDIVIDUAL_SCORE_CRITERIA["Credit History Length"].get(credit_history, {}).get("score", 0)
    ch_weight = INDIVIDUAL_SCORE_CRITERIA["Credit History Length"].get(credit_history, {}).get("weight", 0)
    score_data.append(["Length of Credit History", credit_history, ch_score, 5, ch_score])
    total_score += ch_score * ch_weight
    max_score += 5
    
    # Calculate percentage score
    percentage_score = (total_score / max_score * 100) if max_score > 0 else 0
    
    # Determine Risk Grade
    if percentage_score >= 96:
        risk_grade = "1 (Exceptional)"
    elif percentage_score >= 91:
        risk_grade = "2 (Superior)"
    elif percentage_score >= 81:
        risk_grade = "3 (Very Good)"
    elif percentage_score >= 71:
        risk_grade = "4 (Good)"
    elif percentage_score >= 61:
        risk_grade = "5 (Satisfactory)"
    elif percentage_score >= 51:
        risk_grade = "6 (Acceptable)"
    elif percentage_score >= 41:
        risk_grade = "7 (Marginal)"
    elif percentage_score >= 31:
        risk_grade = "8 (Watch List)"
    elif percentage_score >= 21:
        risk_grade = "9 (Substandard)"
    elif percentage_score >= 11:
        risk_grade = "10 (Doubtful)"
    else:
        risk_grade = "11 (Loss)"
    
    return {
        "score_data": score_data,
        "total_score": total_score,
        "max_score": max_score,
        "percentage_score": percentage_score,
        "risk_grade": risk_grade
    }


def calculate_sme_score(business_type, business_commitment, age_group, experience, 
                       training, license, vehicle, outlook, debt_burden, 
                       tax_status, security, business_premise, credit_turnover, 
                       sim_registration, existing_business=False, business_years=None,
                       accounts=None, revenues=None, profitability=None, bank_account=None):
    """Calculate credit score for SME/Business"""
    
    score_data = []
    total_score = 0
    
    # Basic criteria
    commitment_score = SME_SCORE_CRITERIA["Business Commitment"].get(business_commitment, {}).get("score", 0)
    score_data.append(["Business Commitment", business_commitment, commitment_score, 100])
    total_score += commitment_score
    
    age_score = SME_SCORE_CRITERIA["Age"].get(age_group, {}).get("score", 0)
    score_data.append(["Age", age_group, age_score, 50])
    total_score += age_score
    
    experience_score = SME_SCORE_CRITERIA["Experience"].get(experience, {}).get("score", 0)
    score_data.append(["Experience", experience, experience_score, 100])
    total_score += experience_score
    
    training_score = SME_SCORE_CRITERIA["Training"].get(training, {}).get("score", 0)
    score_data.append(["Training", training, training_score, 100])
    total_score += training_score
    
    license_score = SME_SCORE_CRITERIA["License/Certification"].get(license, {}).get("score", 0)
    score_data.append(["License/Certification", license, license_score, 100])
    total_score += license_score
    
    vehicle_score = SME_SCORE_CRITERIA["Vehicle Ownership"].get(vehicle, {}).get("score", 0)
    score_data.append(["Vehicle Ownership", vehicle, vehicle_score, 60])
    total_score += vehicle_score
    
    outlook_score = SME_SCORE_CRITERIA["Business Outlook"].get(outlook, {}).get("score", 0)
    score_data.append(["Business Outlook", outlook, outlook_score, 100])
    total_score += outlook_score
    
    debt_score = SME_SCORE_CRITERIA["Debt Burden Ratio"].get(debt_burden, {}).get("score", 0)
    score_data.append(["Debt Burden Ratio", debt_burden, debt_score, 100])
    total_score += debt_score
    
    tax_score = SME_SCORE_CRITERIA["Tax Filer Status"].get(tax_status, {}).get("score", 0)
    score_data.append(["Tax Filer Status", tax_status, tax_score, 100])
    total_score += tax_score
    
    security_score = SME_SCORE_CRITERIA["Security"].get(security, {}).get("score", 0)
    score_data.append(["Security", security, security_score, 100])
    total_score += security_score
    
    premise_score = SME_SCORE_CRITERIA["Business Premise"].get(business_premise, {}).get("score", 0)
    score_data.append(["Business Premise", business_premise, premise_score, 100])
    total_score += premise_score
    
    turnover_score = SME_SCORE_CRITERIA["Credit Turnover"].get(credit_turnover, {}).get("score", 0)
    score_data.append(["Credit Turnover", credit_turnover, turnover_score, 100])
    total_score += turnover_score
    
    sim_score = SME_SCORE_CRITERIA["SIM Registration"].get(sim_registration, {}).get("score", 0)
    score_data.append(["SIM Registration", sim_registration, sim_score, 100])
    total_score += sim_score
    
    max_score = 1250
    
    # Existing Business criteria
    if existing_business:
        years_score = SME_EXISTING_BUSINESS_CRITERIA["Business Existence"].get(business_years, {}).get("score", 0)
        score_data.append(["Business Existence", business_years, years_score, 100])
        total_score += years_score
        
        accounts_score = SME_EXISTING_BUSINESS_CRITERIA["Accounts"].get(accounts, {}).get("score", 0)
        score_data.append(["Accounts", accounts, accounts_score, 100])
        total_score += accounts_score
        
        revenues_score = SME_EXISTING_BUSINESS_CRITERIA["Revenues"].get(revenues, {}).get("score", 0)
        score_data.append(["Revenues", revenues, revenues_score, 100])
        total_score += revenues_score
        
        profit_score = SME_EXISTING_BUSINESS_CRITERIA["Profitability"].get(profitability, {}).get("score", 0)
        score_data.append(["Profitability", profitability, profit_score, 80])
        total_score += profit_score
        
        bank_score = SME_EXISTING_BUSINESS_CRITERIA["Bank Account"].get(bank_account, {}).get("score", 0)
        score_data.append(["Bank Account", bank_account, bank_score, 80])
        total_score += bank_score
        
        max_score = 1530
    
    percentage_score = (total_score / max_score * 100) if max_score > 0 else 0
    
    # Determine Risk Grade
    if percentage_score >= 90:
        risk_grade = "1 (Exceptional)"
    elif percentage_score >= 80:
        risk_grade = "2 (Superior)"
    elif percentage_score >= 70:
        risk_grade = "3 (Very Good)"
    elif percentage_score >= 60:
        risk_grade = "4 (Good)"
    elif percentage_score >= 55:
        risk_grade = "5 (Satisfactory)"
    elif percentage_score >= 50:
        risk_grade = "6 (Acceptable)"
    elif percentage_score >= 40:
        risk_grade = "7 (Marginal)"
    elif percentage_score >= 30:
        risk_grade = "8 (Watch List)"
    elif percentage_score >= 20:
        risk_grade = "9 (Substandard)"
    elif percentage_score >= 6:
        risk_grade = "11 (Doubtful)"
    else:
        risk_grade = "12 (Loss)"
    
    return {
        "score_data": score_data,
        "total_score": total_score,
        "max_score": max_score,
        "percentage_score": percentage_score,
        "risk_grade": risk_grade
    }


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
# CREDIT SCORING SECTION (NEW)
# =============================

scoring_enabled = st.checkbox("Enable Credit Scoring Analysis", value=False)

individual_score_result = None
sme_score_result = None

if scoring_enabled:
    st.header("Credit Scoring Analysis")
    
    if profession == "Salaried":
        st.subheader("Individual Scorecard")
        
        scor_c1, scor_c2 = st.columns(2)
        
        with scor_c1:
            age_group = st.selectbox("Age Group", 
                                    ["Over 50 years", "Over 30 & upto 50 years", "Over 18 & upto 30 years"])
            marital_status = st.selectbox("Marital Status", ["Unmarried", "Married"])
            dependents = st.selectbox("Number of Dependents", ["Upto 3", "4 to 5", "More than 5"])
            qualification = st.selectbox("Qualification", ["Masters & Above", "Graduate", "Below Graduate"])
            occupation = st.selectbox("Type of Occupation",
                                     ["Employees maintaining salary with BOP & A category",
                                      "Govt. Employees & B category / under MOU financing",
                                      "Employee of all other accepted employers"])
        
        with scor_c2:
            job_status = st.selectbox("Job Status", ["Permanent", "Contractual"])
            employment_years = st.selectbox("Length of Employment",
                                           ["5 years & over", "3 years & over", "Less than 3 years"])
            income_bracket = st.selectbox("Income Bracket",
                                         ["Above Rs.100,000", "Rs.50,000 & above", "Below Rs.50,000"])
            residence = st.selectbox("Type of Residence", ["Owned/Parents'", "Rented"])
            collateral = st.selectbox("Collateral",
                                     ["Leased vehicle/mortgage/Liquid Security", "Personal Loans (clean)"])
        
        scor_c3, scor_c4 = st.columns(2)
        
        with scor_c3:
            debt_burden = st.selectbox("Debt Burden", ["Upto 30%", "40%", "50%"])
            repayment_history = st.selectbox("Repayment History",
                                            ["No default last 12 months", "1 Instance of OD",
                                             "2 Instances of OD", "3+ Instances of OD"])
        
        with scor_c4:
            credit_history = st.selectbox("Credit History Length",
                                         ["Over 5 years", "From 3-5 years", "Less than 3 years"])
        
        individual_score_result = calculate_individual_score(
            age_group, gender, marital_status, dependents, qualification, occupation,
            job_status, employment_years, income_bracket, residence, collateral,
            debt_burden, repayment_history, credit_history
        )
    
    else:  # Self-Employed or Businessman
        st.subheader("SME/Business Scorecard")
        
        business_type = st.selectbox("Business Type", ["New Business", "Existing Business"])
        
        scor_c1, scor_c2 = st.columns(2)
        
        with scor_c1:
            business_commitment = st.selectbox("Business Commitment", ["Full Time", "Part Time"])
            age_group = st.selectbox("Age Group",
                                    ["42 - 60", "39 - 41", "35 - 38", "30 - 34", "25 - 29"])
            sme_experience = st.selectbox("Experience",
                                         ["Relevant Experience > 3 Years", "Relevant Experience 1-3 Years",
                                          "Family background in business", "Unrelated work experience",
                                          "Never worked"])
            training = st.selectbox("Training",
                                   ["Trained & Certified", "Training not required",
                                    "Trained but not certified", "Not Trained"])
            license = st.selectbox("License/Certification",
                                  ["Required & Held", "No such requirement", "Required but not Held",
                                   "Learner Held", "License Applied"])
        
        with scor_c2:
            vehicle = st.selectbox("Vehicle Ownership",
                                  ["Own registered vehicle", "Family Owned", "Not Applicable", "No vehicle"])
            outlook = st.selectbox("Business Outlook", ["Positive", "Neutral", "Negative"])
            debt_burden = st.selectbox("Debt Burden Ratio",
                                      ["20% or less", "20% - 30%", "30% - 40%", "40% - 50%", "Exceeding 50%"])
            tax_status = st.selectbox("Tax Filer Status",
                                     ["NTN held and Filer", "Tax Exempted Zone",
                                      "NTN held NON-Filer", "No NTN"])
            security = st.selectbox("Security",
                                   ["Vehicle", "Owned property", "Partly rented property",
                                    "Rural/Agri Property", "Rented property", "Liquid security"])
        
        scor_c3, scor_c4 = st.columns(2)
        
        with scor_c3:
            business_premise = st.selectbox("Business Premise",
                                           ["Owned", "Family owned", "Owned no docs",
                                            "Rented with docs", "Rented no docs", "To be rented"])
            credit_turnover = st.selectbox("Credit Turnover",
                                          ["No requirement", "No limit availed",
                                           "More than 4x RF", "More than 3x RF",
                                           "More than 2x RF", "2x or less RF"])
        
        with scor_c4:
            sim_registration = st.selectbox("SIM Registration", ["Yes", "No"])
        
        # Existing business criteria
        business_years = None
        accounts = None
        revenues = None
        profitability = None
        bank_account = None
        
        if business_type == "Existing Business":
            st.subheader("Existing Business Details")
            
            exist_c1, exist_c2 = st.columns(2)
            
            with exist_c1:
                business_years = st.selectbox("Business Existence",
                                             ["More than 5 Years", "2 - 5 Years", "1 - 2 Years", "Less than 1 Year"])
                accounts = st.selectbox("Accounts",
                                       ["Chartered Accountant", "Professional Accountant",
                                        "Self prepared", "Not provided"])
                revenues = st.selectbox("Revenues", ["Growing", "Stagnant", "Declined upto 30%",
                                                     "Declined more than 30%"])
            
            with exist_c2:
                profitability = st.selectbox("Profitability", ["Growing", "Static",
                                                               "Declined upto 30%", "Declined more than 30%"])
                bank_account = st.selectbox("Bank Account", ["Yes with evidence",
                                                            "Yes without evidence", "No account"])
        
        sme_score_result = calculate_sme_score(
            business_type, business_commitment, age_group, sme_experience, training, license,
            vehicle, outlook, debt_burden, tax_status, security, business_premise,
            credit_turnover, sim_registration, existing_business=(business_type == "Existing Business"),
            business_years=business_years, accounts=accounts, revenues=revenues,
            profitability=profitability, bank_account=bank_account
        )

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
    # CREDIT SCORING OUTPUT (NEW)
    # =============================

    if scoring_enabled:
        st.header("Credit Scoring Results")
        
        if individual_score_result:
            st.subheader("Individual Scorecard Analysis")
            
            score_df = pd.DataFrame(individual_score_result["score_data"],
                                   columns=["Criteria", "Selected", "Score", "Max Score", "Allocated"])
            
            st.dataframe(score_df, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Score", f"{individual_score_result['total_score']:.2f} / {individual_score_result['max_score']}")
            col2.metric("Percentage Score", f"{individual_score_result['percentage_score']:.2f}%")
            col3.metric("Risk Grade", individual_score_result["risk_grade"])
        
        elif sme_score_result:
            st.subheader("SME/Business Scorecard Analysis")
            
            score_df = pd.DataFrame(sme_score_result["score_data"],
                                   columns=["Criteria", "Selected", "Score", "Max Score"])
            
            st.dataframe(score_df, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Score", f"{sme_score_result['total_score']} / {sme_score_result['max_score']}")
            col2.metric("Percentage Score", f"{sme_score_result['percentage_score']:.2f}%")
            col3.metric("Risk Grade", sme_score_result["risk_grade"])

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
