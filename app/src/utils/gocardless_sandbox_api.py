import requests
from dotenv import load_dotenv
import os
load_dotenv()


import socket
try:
    socket.gethostbyname("bankaccountdata-sandbox.gocardless.com")
    print("DNS resolution works!")
except socket.gaierror:
    print("DNS resolution failed. Check network settings.")
# Sandbox API key (different from production!)
GC_SANDBOX_KEY = "your_sandbox_api_key_here"
headers = {"Authorization": f"Bearer {os.getenv('GOCARDLESS_SANDBOX_KEY')}"}

# 1. Link a fake Revolut account
response = requests.post(
    "https://bankaccountdata-sandbox.gocardless.com/api/v2/bank-connections/",
    headers=headers,
    json={
        "institution_id": "REVOLUT_REVOGB21",  # Sandbox Revolut ID
        "redirect": "https://your-test-site.com/oauth-callback"  # Fake callback URL
    }
)
auth_url = response.json()["authorisation_url"]
print(f"Open this in browser: {auth_url}")

# Simulate OAuth success by logging in as "user_good"
# GoCardless Sandbox will return a mock bank_connection_id.

# 2. Fetch fake transactions
accounts_response = requests.get(
    f"https://bankaccountdata-sandbox.gocardless.com/api/v2/bank-connections/{bank_connection_id}/accounts",
    headers=headers
)
account_id = accounts_response.json()["accounts"][0]["id"]

transactions_response = requests.get(
    f"https://bankaccountdata-sandbox.gocardless.com/api/v2/accounts/{account_id}/transactions",
    headers=headers
)
print(transactions_response.json())  # Returns mock Revolut transactions