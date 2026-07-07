#!/usr/bin/env python3
"""
Test suite for enhanced expense categorization rules from OpenAccountant.
Validates IRS Schedule C category mapping and deduction guidance.
"""

import sys
from pathlib import Path
from tax_agent.expense_rules import classify_expense

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))


# Sample transactions extracted from typical Chase/Bank of America statements
TEST_TRANSACTIONS = [
    # Vehicle expenses
    ("SHELL GAS STATION 4157 SC", "Vehicle expenses (fuel)"),
    ("EXXON MOBIL 1234 SC", "Vehicle expenses (fuel)"),
    ("CHEVRON STATION 5678", "Vehicle expenses (fuel)"),
    ("JIFFY LUBE INC 901 SC", "Vehicle expenses (maintenance)"),
    ("FIRESTONE AUTO CARE 234", "Vehicle expenses (maintenance)"),
    ("GEICO INSURANCE PAYMENT", "Vehicle expenses (insurance)"),
    
    # Software and subscriptions
    ("ADOBE CREATIVE CLOUD", "Software and subscriptions"),
    ("MICROSOFT 365 SUBSCRIPTION", "Software and subscriptions"),
    ("GOOGLE WORKSPACE ANNUAL", "Software and subscriptions"),
    ("SLACK TECHNOLOGIES", "Software and subscriptions"),
    ("AWS AMAZON WEB SERVICES", "Software and subscriptions"),
    ("GITHUB ENTERPRISE", "Software and subscriptions"),
    ("STRIPE PAYMENT PROCESSOR", "Software and subscriptions"),
    ("ZOOM VIDEO CONFERENCE", "Software and subscriptions"),
    
    # Travel expenses
    ("DELTA AIRLINES TICKET", "Travel expenses"),
    ("SOUTHWEST AIRLINES BOOKING", "Travel expenses"),
    ("HILTON HOTEL CORP SC", "Travel expenses (lodging)"),
    ("MARRIOTT INTERNATIONAL", "Travel expenses (lodging)"),
    ("AIRBNB RESERVATION", "Travel expenses (lodging)"),
    ("UBER TRIP CHARGE", "Travel expenses (ground)"),
    ("LYFT RIDE SHARE", "Travel expenses (ground)"),
    ("TAXI YELLOW CAB 234", "Travel expenses (ground)"),
    
    # Meals and entertainment
    ("LOCAL RESTAURANT LLC", "Meals and entertainment"),
    ("STARBUCKS CAFE 1234", "Meals and entertainment"),
    ("PIZZA PLACE DOWNTOWN", "Meals and entertainment"),
    
    # Office supplies
    ("STAPLES OFFICE SUPPLY", "Office and operating supplies"),
    ("OFFICE DEPOT STORE 567", "Office and operating supplies"),
    ("BEST BUY ELECTRONICS", "Office and operating supplies"),
    ("COSTCO WHOLESALE 234", "Office and operating supplies"),
    
    # Professional services
    ("CPA ACCOUNTING SERVICES", "Professional services (tax/accounting)"),
    ("LEGAL ASSOCIATES LLP", "Professional services (legal)"),
    ("MANAGEMENT CONSULTANT LLC", "Professional services"),
    
    # Communications
    ("AT&T WIRELESS MONTHLY", "Utilities and communications"),
    ("VERIZON MONTHLY BILL", "Utilities and communications"),
    ("COMCAST INTERNET SERVICE", "Utilities and communications"),
    
    # Education
    ("COURSERA ONLINE COURSE", "Education and training"),
    ("UDEMY SKILL DEVELOPMENT", "Education and training"),
    ("LINKEDIN LEARNING PRO", "Education and training"),
    
    # Advertising
    ("GOOGLE ADS CAMPAIGN", "Advertising and marketing"),
    ("FACEBOOK ADS MANAGER", "Advertising and marketing"),
    ("MAILCHIMP EMAIL SERVICE", "Advertising and marketing"),
    
    # Home office
    ("INTERNET SERVICE PROVIDER", "Home office (utilities/internet)"),
    
    # Unknown
    ("RANDOM STORE 234", "Unmapped"),
    ("GROCERY MARKET INC", "Unmapped"),
]


def run_tests():
    """Run categorization tests and report results."""
    passed = 0
    failed = 0
    results = []
    
    print("=" * 100)
    print("EXPENSE CATEGORIZATION TEST SUITE")
    print("Testing OpenAccountant-aligned IRS Schedule C Categories")
    print("=" * 100)
    print()
    
    for description, expected_category in TEST_TRANSACTIONS:
        actual_category, confidence, note = classify_expense(description)
        
        # Check if categorization is correct
        is_pass = actual_category.lower() == expected_category.lower()
        
        if is_pass:
            passed += 1
            status = "[PASS]"
        else:
            failed += 1
            status = "[FAIL]"
        
        results.append({
            "description": description,
            "expected": expected_category,
            "actual": actual_category,
            "confidence": confidence,
            "note": note,
            "pass": is_pass
        })
        
        # Print detailed result
        print(f"{status} | {description:40} | {actual_category:40} | {confidence:.2f}")
        if not is_pass:
            print(f"       Expected: {expected_category}")
        if note and confidence < 0.9:
            print(f"       Note: {note}")
        print()
    
    # Summary
    print("=" * 100)
    print("TEST SUMMARY")
    print("=" * 100)
    total = len(TEST_TRANSACTIONS)
    pass_rate = (passed / total) * 100
    print(f"Total Tests:     {total}")
    print(f"Passed:          {passed}")
    print(f"Failed:          {failed}")
    print(f"Pass Rate:       {pass_rate:.1f}%")
    print()
    
    # Category breakdown
    print("=" * 100)
    print("CATEGORY COVERAGE")
    print("=" * 100)
    categories = {}
    for result in results:
        cat = result["actual"]
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1
    
    for cat in sorted(categories.keys()):
        print(f"  {cat:45} : {categories[cat]:2} transactions")
    print()
    
    # High confidence results (for publishing)
    print("=" * 100)
    print("HIGH CONFIDENCE CATEGORIZATIONS (90%+ - READY FOR PUBLISHING)")
    print("=" * 100)
    high_conf = [r for r in results if r["confidence"] >= 0.90]
    print(f"High Confidence Results: {len(high_conf)}/{total} ({(len(high_conf)/total)*100:.1f}%)")
    print()
    for result in high_conf:
        print(f"  {result['description']:40} -> {result['actual']:40} ({result['confidence']:.2f})")
    print()
    
    # Medium confidence results (needs review)
    print("=" * 100)
    print("MEDIUM CONFIDENCE CATEGORIZATIONS (70-90% - NEEDS REVIEW)")
    print("=" * 100)
    med_conf = [r for r in results if 0.70 <= r["confidence"] < 0.90]
    print(f"Medium Confidence Results: {len(med_conf)}/{total}")
    print()
    for result in med_conf:
        print(f"  {result['description']:40} -> {result['actual']:40} ({result['confidence']:.2f})")
        print(f"     Action: {result['note']}")
    print()
    
    # Low confidence / unmapped
    print("=" * 100)
    print("LOW CONFIDENCE / UNMAPPED (needs manual review)")
    print("=" * 100)
    low_conf = [r for r in results if r["confidence"] < 0.70]
    print(f"Low Confidence/Unmapped: {len(low_conf)}/{total}")
    print()
    for result in low_conf:
        print(f"  {result['description']:40} -> {result['actual']:40} ({result['confidence']:.2f})")
        print(f"     Action: {result['note']}")
    print()
    
    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
