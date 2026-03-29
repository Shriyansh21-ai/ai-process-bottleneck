import sys
import os

# Add src/ to Python path
sys.path.append(os.path.abspath("src"))

from core.security import generate_api_key, hash_api_key

api_key = generate_api_key()
api_key_hash = hash_api_key(api_key)

print("===================================")
print("RAW_API_KEY (SAVE THIS SECURELY)")
print(api_key)
print("===================================")
print("API_KEY_HASH (STORE IN DB)")
print(api_key_hash)
print("===================================")
