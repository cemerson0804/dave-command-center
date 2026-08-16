from supabase import create_client

url = "https://rrnbbdophflohmirtxuv.supabase.co"
key = "sb_publishable_zqoYzmdFSnlVWUoc7fIoww_RzQx1L9x"
client = create_client(url, key)

debts = [
    {"name": "Home Depot", "profile": "cody", "balance": 0.0, "apr": 29.99, "minimum": 0, "status": "PAID OFF", "killed_date": "07/23/2026", "daily_interest": 0.0},
    {"name": "Best Buy", "profile": "cody", "balance": 444.21, "apr": 29.74, "minimum": 67, "status": "CURRENT TARGET", "promo_deadline": "05/16/2027", "daily_interest": 0.36},
    {"name": "Chase Sapphire", "profile": "cody", "balance": 16335.33, "apr": 25.49, "minimum": 500, "status": "Active", "daily_interest": 11.41},
    {"name": "Robinhood CC", "profile": "cody", "balance": 12013.14, "apr": 24.24, "minimum": 259, "status": "Active", "daily_interest": 7.98},
    {"name": "Southern FCU", "profile": "cody", "balance": 4249.70, "apr": 10.25, "minimum": 205, "status": "Active", "daily_interest": 1.19},
    {"name": "Wells Fargo (0% transfer)", "profile": "cody", "balance": 3000.00, "apr": 0.0, "minimum": 143, "status": "0% Promo", "promo_deadline": "05/2028", "daily_interest": 0.0},
    {"name": "Figure HELOC", "profile": "cody", "balance": 58137.37, "apr": 10.30, "minimum": 522.76, "status": "Baby Step 6", "daily_interest": 16.41},
]

for d in debts:
    client.table("debts").upsert(d, on_conflict="name,profile").execute()
    print(f"Seeded: {d['name']} - ${d['balance']:,.2f}")

print()
print("All debts seeded successfully.")
