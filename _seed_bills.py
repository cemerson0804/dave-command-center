from supabase import create_client

url = "https://rrnbbdophflohmirtxuv.supabase.co"
key = "sb_publishable_zqoYzmdFSnlVWUoc7fIoww_RzQx1L9x"
client = create_client(url, key)

cody_bills = [
    {"name": "Mortgage (Onity)", "profile": "cody", "amount": 829.45, "day": 1, "autopay": True, "category": "Housing"},
    {"name": "HELOC (Figure)", "profile": "cody", "amount": 313.66, "day": 1, "autopay": True, "apr": 10.30, "category": "Housing"},
    {"name": "Toyota Camry", "profile": "cody", "amount": 692.59, "day": 1, "autopay": True, "apr": 7.90, "category": "Auto"},
    {"name": "Camper (US Bank)", "profile": "cody", "amount": 405.00, "day": 1, "autopay": True, "category": "Auto"},
    {"name": "C-Spire Fiber", "profile": "cody", "amount": 52.27, "day": 1, "autopay": True, "category": "Housing"},
    {"name": "Spartan Gym", "profile": "cody", "amount": 75.00, "day": 1, "autopay": True, "category": "Fitness"},
    {"name": "Brookhaven Academy", "profile": "cody", "amount": 281.33, "day": 1, "autopay": False, "category": "Kids"},
    {"name": "GMC Canyon", "profile": "cody", "amount": 335.98, "day": 3, "autopay": True, "apr": 7.24, "category": "Auto"},
    {"name": "Chase Sapphire", "profile": "cody", "amount": 500.00, "day": 5, "autopay": True, "apr": 25.49, "category": "Debt"},
    {"name": "Robinhood CC", "profile": "cody", "amount": 259.00, "day": 10, "autopay": False, "apr": 24.24, "category": "Debt"},
    {"name": "Best Buy", "profile": "cody", "amount": 67.00, "day": 12, "autopay": False, "apr": 29.74, "category": "Debt"},
    {"name": "Alfa Insurance", "profile": "cody", "amount": 319.34, "day": 13, "autopay": True, "category": "Auto"},
    {"name": "IRS Installment", "profile": "cody", "amount": 124.50, "day": 15, "autopay": True, "category": "Taxes"},
    {"name": "Southern FCU", "profile": "cody", "amount": 205.00, "day": 16, "autopay": True, "apr": 10.25, "category": "Debt"},
    {"name": "Voice Lessons", "profile": "cody", "amount": 60.00, "day": 15, "autopay": False, "category": "Kids"},
    {"name": "AT&T Wireless", "profile": "cody", "amount": 323.52, "day": 22, "autopay": True, "category": "Phone"},
    {"name": "Nissan Sentra", "profile": "cody", "amount": 232.00, "day": 24, "autopay": True, "apr": 6.84, "category": "Auto"},
    {"name": "Entergy Electric", "profile": "cody", "amount": 162.00, "day": 28, "autopay": True, "category": "Housing"},
    {"name": "Cable", "profile": "cody", "amount": 45.00, "day": 28, "autopay": False, "category": "Housing"},
]

deidra_bills = [
    {"name": "Mortgage (her 40%)", "profile": "deidra", "amount": 552.97, "day": 1, "autopay": True, "category": "Housing"},
    {"name": "HELOC (her 40%)", "profile": "deidra", "amount": 209.10, "day": 1, "autopay": True, "category": "Housing"},
    {"name": "Entergy (her 40%)", "profile": "deidra", "amount": 108.00, "day": 28, "autopay": True, "category": "Housing"},
    {"name": "C-Spire (her 40%)", "profile": "deidra", "amount": 34.84, "day": 1, "autopay": True, "category": "Housing"},
    {"name": "Cable (her 50%)", "profile": "deidra", "amount": 45.00, "day": 28, "autopay": False, "category": "Housing"},
    {"name": "AT&T (her lines)", "profile": "deidra", "amount": 307.94, "day": 22, "autopay": True, "category": "Phone"},
    {"name": "Alfa Insurance (her vehicles)", "profile": "deidra", "amount": 285.12, "day": 13, "autopay": True, "category": "Auto"},
    {"name": "GMC Canyon (her 40%)", "profile": "deidra", "amount": 224.00, "day": 3, "autopay": True, "category": "Auto"},
    {"name": "350Z", "profile": "deidra", "amount": 129.82, "day": 9, "autopay": True, "category": "Auto"},
    {"name": "IRS (her 50%)", "profile": "deidra", "amount": 124.50, "day": 15, "autopay": True, "category": "Taxes"},
    {"name": "Americor Debt Mgmt", "profile": "deidra", "amount": 235.53, "day": 6, "autopay": True, "category": "Debt"},
    {"name": "Voice Lessons (her 50%)", "profile": "deidra", "amount": 60.00, "day": 15, "autopay": False, "category": "Kids"},
]

all_bills = cody_bills + deidra_bills

for b in all_bills:
    client.table("bills").upsert(b, on_conflict="name,profile").execute()
    print(f"  {b['profile']}: {b['name']} - ${b['amount']:,.2f}")

print(f"\nSeeded {len(all_bills)} bills successfully.")
