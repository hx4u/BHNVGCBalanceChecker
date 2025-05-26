import threading
from queue import Queue
import os
import sys
import time

# Config
PREFIX = "455172200"  # 9 digits
SUFFIX_LENGTH = 16 - len(PREFIX)  # 7 digits remaining
OUTPUT_FILE = "raw_digits.txt"
NUM_THREADS = 10

# Thread-safe
write_lock = threading.Lock()
count_lock = threading.Lock()
task_queue = Queue()
written_count = 0

def load_existing():
    existing = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            for line in f:
                code = line.strip()
                if len(code) == 16 and code.startswith(PREFIX):
                    existing.add(code)
    return existing

def worker(existing_codes):
    global written_count
    while True:
        suffix = task_queue.get()
        if suffix is None:
            break
        code = PREFIX + str(suffix).zfill(SUFFIX_LENGTH)
        if code not in existing_codes:
            with write_lock:
                with open(OUTPUT_FILE, "a") as f:
                    f.write(code + "\n")
                existing_codes.add(code)
            with count_lock:
                written_count += 1
        task_queue.task_done()

def live_counter():
    global written_count
    while not task_queue.empty():
        with count_lock:
            count = written_count
        sys.stdout.write(f"\r[+] Codes written: {count:,}")
        sys.stdout.flush()
        time.sleep(0.5)
    # Final update
    with count_lock:
        count = written_count
    sys.stdout.write(f"\r[+] Final count: {count:,}\n")

def main():
    print("[*] Loading existing codes...")
    existing_codes = load_existing()
    print(f"[*] {len(existing_codes):,} existing codes loaded.")

    # Start worker threads
    threads = []
    for _ in range(NUM_THREADS):
        t = threading.Thread(target=worker, args=(existing_codes,))
        t.start()
        threads.append(t)

    # Start live counter thread
    counter_thread = threading.Thread(target=live_counter, daemon=True)
    counter_thread.start()

    # Enqueue all 7-digit combinations
    for i in range(10 ** SUFFIX_LENGTH):
        task_queue.put(i)

    task_queue.join()

    # Signal threads to stop
    for _ in range(NUM_THREADS):
        task_queue.put(None)
    for t in threads:
        t.join()

    # Wait for final counter update
    counter_thread.join(timeout=1)
    print("[*] Generation complete.")

if __name__ == "__main__":
    main()
