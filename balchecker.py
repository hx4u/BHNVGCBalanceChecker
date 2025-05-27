#!/usr/bin/env python3

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import VisaGiftCard
import signal
import sys

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

def signal_handler(sig, frame):
    """Handle graceful shutdown on Ctrl+C."""
    print("\nInterrupt received. Cancelling all threads...")
    sys.exit(0)  # Exit the program

if __name__ == "__main__":
    # Register the signal handler to catch Ctrl+C (KeyboardInterrupt)
    signal.signal(signal.SIGINT, signal_handler)

    # Execute only if run as a script
    try:
        with open(fileName, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip the header

            titles = ['Last 4', 'Available', 'Initial', 'Cashback', 'Override']
            separator = '  '
            header = separator.join(titles)
            print(header)
            print('=' * len(header))

            valid_cards = []

            # Use ThreadPoolExecutor to process the cards concurrently
            with ThreadPoolExecutor() as executor:
                # Start processing the rows asynchronously
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

    except (OSError, IOError):
        print(f'"{fileName}" is not found.\nPlease make a copy from "{sampleFileName}".')
        exit()
