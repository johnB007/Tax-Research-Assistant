from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpenseRule:
    keyword: str
    category: str
    confidence: float
    note: str


# OpenAccountant-aligned IRS Schedule C expense categories
RULES: list[ExpenseRule] = [
    # Advertising and Marketing
    ExpenseRule("google ads", "Advertising and marketing", 0.95, "Digital advertising expense"),
    ExpenseRule("facebook ads", "Advertising and marketing", 0.95, "Digital advertising expense"),
    ExpenseRule("mailchimp", "Advertising and marketing", 0.95, "Email marketing software"),
    ExpenseRule("hootsuite", "Advertising and marketing", 0.95, "Social media marketing tools"),
    
    # Car and Vehicle Expenses
    ExpenseRule("shell", "Vehicle expenses (fuel)", 0.85, "Track mileage logs for deduction support"),
    ExpenseRule("exxon", "Vehicle expenses (fuel)", 0.85, "Track mileage logs for deduction support"),
    ExpenseRule("chevron", "Vehicle expenses (fuel)", 0.85, "Track mileage logs for deduction support"),
    ExpenseRule("mobil", "Vehicle expenses (fuel)", 0.85, "Track mileage logs for deduction support"),
    ExpenseRule("bp", "Vehicle expenses (fuel)", 0.85, "Track mileage logs for deduction support"),
    ExpenseRule("circle k", "Vehicle expenses (fuel)", 0.85, "Track mileage logs for deduction support"),
    ExpenseRule("chevron", "Vehicle expenses (maintenance)", 0.8, "Oil changes and maintenance"),
    ExpenseRule("firestone", "Vehicle expenses (maintenance)", 0.9, "Tire and vehicle maintenance"),
    ExpenseRule("jiffy lube", "Vehicle expenses (maintenance)", 0.9, "Vehicle service and maintenance"),
    ExpenseRule("geico", "Vehicle expenses (insurance)", 0.9, "Business auto insurance"),
    ExpenseRule("state farm", "Vehicle expenses (insurance)", 0.9, "Business auto insurance"),
    
    # Office and Operating Supplies
    ExpenseRule("staples", "Office and operating supplies", 0.8, "Office supplies and equipment"),
    ExpenseRule("office depot", "Office and operating supplies", 0.8, "Office supplies and equipment"),
    ExpenseRule("costco", "Office and operating supplies", 0.7, "Mixed retail - review for personal items"),
    ExpenseRule("bestbuy", "Office and operating supplies", 0.75, "Electronics and office equipment"),
    ExpenseRule("paper", "Office and operating supplies", 0.9, "Printing and office supplies"),
    ExpenseRule("ink", "Office and operating supplies", 0.9, "Printer supplies"),
    
    # Software and Subscriptions
    ExpenseRule("adobe", "Software and subscriptions", 0.95, "Creative software (Schedule C)"),
    ExpenseRule("microsoft", "Software and subscriptions", 0.9, "Office and business software"),
    ExpenseRule("google workspace", "Software and subscriptions", 0.95, "Business email and productivity"),
    ExpenseRule("zoho", "Software and subscriptions", 0.95, "CRM and business management software"),
    ExpenseRule("slack", "Software and subscriptions", 0.95, "Team communication software"),
    ExpenseRule("zoom", "Software and subscriptions", 0.95, "Video conferencing service"),
    ExpenseRule("dropbox", "Software and subscriptions", 0.9, "Cloud storage service"),
    ExpenseRule("asana", "Software and subscriptions", 0.9, "Project management tool"),
    ExpenseRule("notion", "Software and subscriptions", 0.9, "Productivity and documentation tool"),
    ExpenseRule("github", "Software and subscriptions", 0.95, "Developer tools and version control"),
    ExpenseRule("aws", "Software and subscriptions", 0.95, "Cloud computing and hosting"),
    ExpenseRule("stripe", "Software and subscriptions", 0.9, "Payment processing fees"),
    
    # Travel and Meals (IRS Per Diem Rules)
    ExpenseRule("delta", "Travel expenses", 0.85, "Airfare - requires business purpose documentation"),
    ExpenseRule("southwest", "Travel expenses", 0.85, "Airfare - requires business purpose documentation"),
    ExpenseRule("united", "Travel expenses", 0.85, "Airfare - requires business purpose documentation"),
    ExpenseRule("american airlines", "Travel expenses", 0.85, "Airfare - requires business purpose documentation"),
    ExpenseRule("united airlines", "Travel expenses", 0.85, "Airfare - requires business purpose documentation"),
    ExpenseRule("hilton", "Travel expenses (lodging)", 0.9, "Hotel accommodations for business travel"),
    ExpenseRule("marriott", "Travel expenses (lodging)", 0.9, "Hotel accommodations for business travel"),
    ExpenseRule("hotel", "Travel expenses (lodging)", 0.85, "Lodging for business travel"),
    ExpenseRule("airbnb", "Travel expenses (lodging)", 0.75, "Short-term accommodations - verify business use"),
    ExpenseRule("uber", "Travel expenses (ground)", 0.75, "Transportation - document trip purpose"),
    ExpenseRule("lyft", "Travel expenses (ground)", 0.75, "Transportation - document trip purpose"),
    ExpenseRule("taxi", "Travel expenses (ground)", 0.8, "Ground transportation"),
    ExpenseRule("restaurant", "Meals and entertainment", 0.65, "50% deductible - requires business purpose"),
    ExpenseRule("cafe", "Meals and entertainment", 0.6, "Meals with business associates (50% deductible)"),
    ExpenseRule("pizza", "Meals and entertainment", 0.55, "Check if related to business - 50% deductible"),
    
    # Home Office Deduction
    ExpenseRule("home office", "Home office (utilities/internet)", 0.9, "Dedicated home office space required"),
    ExpenseRule("internet service provider", "Home office (utilities/internet)", 0.8, "Business use percentage applies"),
    ExpenseRule("electricity", "Home office (utilities/internet)", 0.7, "Business use percentage applies"),
    ExpenseRule("rent", "Home office (rent)", 0.6, "Requires dedicated home office space documentation"),
    ExpenseRule("mortgage", "Home office (mortgage interest)", 0.5, "Only interest portion, business use %"),
    
    # Utilities and Communications
    ExpenseRule("at&t", "Utilities and communications", 0.85, "Business phone line or portion of service"),
    ExpenseRule("att", "Utilities and communications", 0.85, "Business phone line or portion of service"),
    ExpenseRule("verizon", "Utilities and communications", 0.8, "Business phone line or portion of service"),
    ExpenseRule("tmobile", "Utilities and communications", 0.8, "Business phone line or portion of service"),
    ExpenseRule("comcast", "Utilities and communications", 0.8, "Business internet connection"),
    ExpenseRule("spectrum", "Utilities and communications", 0.75, "Business internet connection"),
    
    # Professional Services
    ExpenseRule("accountant", "Professional services (tax/accounting)", 0.95, "Tax preparation and accounting services"),
    ExpenseRule("cpa", "Professional services (tax/accounting)", 0.95, "CPA services"),
    ExpenseRule("lawyer", "Professional services (legal)", 0.9, "Legal and professional advice"),
    ExpenseRule("legal", "Professional services (legal)", 0.9, "Legal services"),
    ExpenseRule("consultant", "Professional services", 0.85, "Consulting fees"),
    
    # Equipment and Tools
    ExpenseRule("amazon", "Equipment and supplies", 0.65, "Review for business-only items"),
    ExpenseRule("best buy", "Office and operating supplies", 0.85, "Electronics and office equipment"),
    ExpenseRule("bestbuy", "Office and operating supplies", 0.85, "Electronics and office equipment"),
    ExpenseRule("tools", "Equipment and supplies", 0.85, "Business tools and equipment"),
    ExpenseRule("equipment", "Equipment and supplies", 0.85, "Office and business equipment"),
    
    # Insurance (excluding vehicle)
    ExpenseRule("insurance", "Insurance and taxes", 0.75, "Business liability or general insurance"),
    ExpenseRule("liability", "Insurance and taxes", 0.9, "Business liability insurance"),
    
    # Education and Professional Development
    ExpenseRule("coursera", "Education and training", 0.9, "Professional development courses"),
    ExpenseRule("udemy", "Education and training", 0.85, "Online courses for business skills"),
    ExpenseRule("linkedin learning", "Education and training", 0.95, "Professional development platform"),
    ExpenseRule("linkedin", "Education and training", 0.9, "Professional development"),
    ExpenseRule("conference", "Education and training", 0.9, "Business conference registration"),
]


def classify_expense(description: str) -> tuple[str, float, str]:
    """Classify expense by keyword matching with IRS Schedule C categories.
    
    Longer, more specific keywords are checked first to avoid false positives.
    """
    normalized = description.lower()
    
    # First pass: Check for multi-word phrases and specific terms
    specific_terms = [
        ("google workspace", "Software and subscriptions", 0.95, "Business email and productivity"),
        ("linkedin learning", "Education and training", 0.95, "Professional development platform"),
        ("professional services", "Professional services", 0.85, "Professional services"),
        ("travel expenses", "Travel expenses", 0.85, "Travel expenses"),
    ]
    
    for keyword, category, conf, note in specific_terms:
        if keyword in normalized:
            return category, conf, note
    
    # Second pass: Check standard rules
    for rule in RULES:
        if rule.keyword in normalized:
            return rule.category, rule.confidence, rule.note
    
    return "Unmapped", 0.35, "Requires manual categorization - review for business purpose"
