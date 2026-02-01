import time
from virtual_trash_bin import VirtualTrashBin
import sys

bins = [VirtualTrashBin(bin_id=f"B{i+1}") for i in range(10)]

try:
    for b in bins:
        b.start()
    print("Running simulation. Press Ctrl+C to stop...")

    # Keep main thread alive
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping all bins...")

    for b in bins:
        b.stop()

    for b in bins:
        b.join()

    print("All bins stopped. Exiting.")
    sys.exit(0)
