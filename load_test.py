#!/usr/bin/env python3
import requests
import threading
import time

def hammer_server(url, num_requests=500):
    """Just blast the server with requests as fast as possible"""
    
    def send_request(i):
        try:
            response = requests.get(url, timeout=2)
            if i % 50 == 0:  # Print every 50th request
                print(f"Request {i}: {response.status_code}")
        except Exception as e:
            print(f"Request {i} failed: {e}")
    
    print(f"Sending {num_requests} requests to {url}")
    print("Press Ctrl+C to stop")
    
    start_time = time.time()
    threads = []
    
    # Fire off all requests at once
    for i in range(num_requests):
        thread = threading.Thread(target=send_request, args=(i,))
        thread.start()
        threads.append(thread)
    
    # Wait for all to complete
    for thread in threads:
        thread.join()
    
    duration = time.time() - start_time
    print(f"Done! {num_requests} requests in {duration:.2f} seconds")
    print(f"Average: {num_requests/duration:.1f} requests/second")

if __name__ == "__main__":
    url = "http://localhost:3000/"
    hammer_server(url)