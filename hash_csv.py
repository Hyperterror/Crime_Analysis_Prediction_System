import bcrypt
import csv

# Input file (replace this with your actual CSV file)
csv_filename = "data/credentials.csv"

# Read existing users
users = []
with open(csv_filename, "r", newline="") as file:
    reader = csv.reader(file)
    for row in reader:
        username, password = row
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        users.append([username, hashed_password])

# Save hashed passwords back to CSV
with open(csv_filename, "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerows(users)

print("Passwords hashed and saved securely.")
