import bcrypt
import pandas as pd

def validate_login(username, entered_password):
    try:
        credentials = pd.read_csv("data/credentials.csv")  # Load CSV file
        
        # Ensure CSV has correct columns
        if "user_id" not in credentials.columns or "pwd" not in credentials.columns:
            print("Error: CSV does not have required columns.")
            return False
        
        for _, row in credentials.iterrows():
            if row["user_id"] == username and bcrypt.checkpw(entered_password.encode(), row["pwd"].encode()):
                return True  # Login successful
    except Exception as e:
        print("Error reading CSV:", e)

    return False  # Login failed
