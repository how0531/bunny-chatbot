import time
from collections import defaultdict
import threading

class RateLimiter:
    def __init__(self, limit=10, window=60):
        self.limit = limit
        self.window = window
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, user_id):
        with self.lock:
            now = time.time()
            user_requests = self.requests[user_id]
            
            # Clean up old requests
            user_requests = [t for t in user_requests if now - t < self.window]
            self.requests[user_id] = user_requests
            
            if len(user_requests) < self.limit:
                self.requests[user_id].append(now)
                return True, self.limit - len(user_requests) - 1
            
            return False, 0

# Global Limiter Instance
limiter = RateLimiter(limit=15, window=60)
