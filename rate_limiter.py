import time

login_attempts = {}

# Function to check if a user is rate-limited
def is_rate_limited(username, max_attempts=5, time_window=900):  # 900 seconds = 15 minutes
    now = time.time()
    
    attempts = login_attempts.get(username, [])
    attempts = [t for t in attempts if now - t < time_window]
    
    if len(attempts) >= max_attempts:
        return True
    
    # Add the new attempt and update dictionary
    attempts.append(now)
    login_attempts[username] = attempts
    return False