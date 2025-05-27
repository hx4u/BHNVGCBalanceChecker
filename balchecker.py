#!/usr/bin/env python3

import argparse
import csv
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import VisaGiftCard
from time import sleep

fileName = 'cards.csv'
sampleFileName = 'cards.sample.csv'
outputFileName = 'valid_cards.csv'

def process_card(row):
    """Process a single card row."""
    vgc = VisaGiftCard.fromRow(row)
    vgc.getBalanceAndTransactions()

    # Formatting for output
    formatStr = '{:>%i}'
    formatFloat = '{:>%i.2f}'

    if vgc.valid:
        return (vgc.lastFour, vgc.availableBalance, vgc.initialBalance, vgc.cashback, vgc.override)
    else:
        return (vgc.lastFour, 'ERROR: ' + vgc.errorMessage)

def write_output(valid_cards):
    """Write the valid cards to the output CSV file."""
    with open(outputFileName, 'w', newline='', encoding='utf-8') as out_file:
        writer = csv.writer(out_file)
        writer.writerow(['Last 4', 'Available', 'Initial', 'Cashback', 'Override'])
        writer.writerows(valid_cards)

def signal_handler(sig, frame, executor):
    """Handle graceful shutdown on Ctrl+C."""
    print("\nInterrupt received. Cancelling all threads...")
    executor.shutdown(wait=True)  # Gracefully shut down threads
    sys.exit(0)  # Exit the program

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Process a CSV of Visa gift cards, retrieve balances, and write valid cards to an output file.")
    
    # Optional arguments
    parser.add_argument('-i', '--input', default=fileName, help=f"Input CSV file (default: {fileName})")
    parser.add_argument('-o', '--output', default=outputFileName, help=f"Output CSV file for valid cards (default: {outputFileName})")
    parser.add_argument('--sample', action='store_true', help="Print sample file info and exit")
    parser.add_argument('--threads', type=int, default=os.cpu_count(), help=f"Number of threads to use (default: {os.cpu_count()})")

    return parser.parse_args()

def show_loading_message():
    """Display a loading message while processing the file."""
    print("Loading cards.csv...")
    for _ in range(3):  # Display a simple loading animation
        print(".", end="", flush=True)
        sleep(0.5)
    print("\n")

if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()

    if args.sample:
        print(f"Sample file should be named: {sampleFileName}")
        exit()

    # Register the signal handler to catch Ctrl+C (KeyboardInterrupt)
    executor = ThreadPoolExecutor(max_workers=args.threads)
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, executor))

    # Execute only if run as a script
    try:
        with open(args.input, 'r', newline='', encoding='utf-8') as f:
            show_loading_message()  # Show loading message while reading the file

            reader = csv.reader(f)
            next(reader)  # Skip the header

            titles = ['Last 4', 'Available', 'Initial', 'Cashback', 'Override']
            separator = '  '
            header = separator.join(titles)
            print(header)
            print('=' * len(header))

            valid_cards = []

            # Use ThreadPoolExecutor to process the cards concurrently with the specified thread count
            future_to_row = {executor.submit(process_card, row): row for row in reader}

            # Collect results as they are completed
            for future in as_completed(future_to_row):
                try:
                    result = future.result()
                    valid_cards.append(result)

                except Exception as e:
                    print(f"Error processing card: {e}")

            # Print valid cards to console
            for card in valid_cards:
                print(separator.join(map(str, card)))

            # Write valid cards to the output file
            write_output(valid_cards)

            # Gracefully shutdown the executor after finishing processing
            executor.shutdown(wait=True)

    except (OSError, IOError):
        print(f'"{args.input}" is not found.\nPlease make a copy from "{sampleFileName}".')
        exit()
