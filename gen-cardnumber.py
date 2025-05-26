import threading

from queue import Queue

import os

import sys

import time



# Config

PREFIX = "455172200"  # 9-digit prefix

SUFFIX_LENGTH = 16 - len(PREFIX)  # 7 digits remaining

OUTPUT_FILE = "raw_digits.txt"

NUM_THREADS = 10



# Shared resources

write_lock = threading.Lock()

count_lock = threading.Lock()

latest_lock = threading.Lock()



task_queue = Queue()

written_count = 0

latest_code = ""  # now starts as empty string, not None





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

    global written_count, latest_code

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

            with latest_lock:

                latest_code = code

        task_queue.task_done()





def live_display():

    last_display = ""

    while not task_queue.empty() or any(t.is_alive() for t in threading.enumerate() if t.name.startswith("worker")):

        with count_lock:

            count = written_count

        with latest_lock:

            code = latest_code if latest_code else "(waiting...)"

        display = f"\r[+] Written: {count:,} | Latest: {code}"

        if display != last_display:

            sys.stdout.write(display)

            sys.stdout.flush()

            last_display = display

        time.sleep(0.5)

    print("\n[*] Generation complete.")





def main():

    print("[*] Loading existing codes...")

    existing_codes = load_existing()

    print(f"[*] Loaded {len(existing_codes):,} existing codes.")



    # Start worker threads

    threads = []

    for i in range(NUM_THREADS):

        t = threading.Thread(target=worker, args=(existing_codes,), name=f"worker-{i}")

        t.start()

        threads.append(t)



    # Enqueue suffixes after threads are ready

    for i in range(10 ** SUFFIX_LENGTH):

        suffix = str(i).zfill(SUFFIX_LENGTH)

        code = PREFIX + suffix

        if code not in existing_codes:

            task_queue.put(i)



    # Start live display thread

    display_thread = threading.Thread(target=live_display, daemon=True)

    display_thread.start()



    task_queue.join()



    # Signal threads to shut down

    for _ in threads:

        task_queue.put(None)

    for t in threads:

        t.join()



    display_thread.join(timeout=1)





if __name__ == "__main__":

    main()

