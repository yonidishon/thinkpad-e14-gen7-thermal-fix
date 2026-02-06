#!/usr/bin/env python3
"""
CPU Stress Test for ThinkPad E14 Gen 7
Tests thermal behavior under various CPU loads
"""

import multiprocessing
import time
import argparse
import sys
import math

class Colors:
    CYAN = '\033[0;36m'
    YELLOW = '\033[1;33m'
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    NC = '\033[0m'

def cpu_intensive_work(duration, worker_id):
    """Perform CPU-intensive calculations"""
    print(f"  Worker {worker_id}: Starting CPU stress...")
    end_time = time.time() + duration

    # Busy loop with actual calculations to maximize CPU usage
    while time.time() < end_time:
        # Mix of integer and floating point operations
        result = 0
        for i in range(10000):
            result += math.sqrt(i) * math.sin(i) * math.cos(i)
            result += i ** 2
            result %= 999999

    print(f"  Worker {worker_id}: Completed")

def run_stress_test(num_cores, duration, ramp_up=False):
    """Run CPU stress test on specified number of cores"""

    print(f"\n{Colors.CYAN}{Colors.BOLD}=== CPU Stress Test ==={Colors.NC}")
    print(f"CPU cores to stress: {num_cores}")
    print(f"Duration: {duration} seconds")
    print(f"Ramp up: {'Yes' if ramp_up else 'No'}")
    print()

    if ramp_up:
        print(f"{Colors.YELLOW}Ramping up load gradually...{Colors.NC}")
        # Start with 1 core, gradually add more
        for cores in range(1, num_cores + 1):
            print(f"\n{Colors.CYAN}Starting {cores} core(s)...{Colors.NC}")
            processes = []
            for i in range(cores):
                p = multiprocessing.Process(target=cpu_intensive_work, args=(duration // num_cores, i))
                p.start()
                processes.append(p)

            # Wait for this batch to complete
            for p in processes:
                p.join()

            print(f"{Colors.GREEN}Completed {cores} core batch{Colors.NC}")
            time.sleep(2)  # Brief pause between ramps
    else:
        # Full load immediately
        print(f"{Colors.YELLOW}Starting full load on {num_cores} cores...{Colors.NC}\n")
        processes = []

        for i in range(num_cores):
            p = multiprocessing.Process(target=cpu_intensive_work, args=(duration, i))
            p.start()
            processes.append(p)

        # Wait for all to complete
        for p in processes:
            p.join()

    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Stress test completed!{Colors.NC}")
    print(f"{Colors.YELLOW}Check your temperature monitor for results.{Colors.NC}\n")

def main():
    parser = argparse.ArgumentParser(
        description='CPU Stress Test for thermal monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Stress all CPU cores for 60 seconds
  python3 cpu_stress_test.py -d 60

  # Stress 4 cores for 30 seconds
  python3 cpu_stress_test.py -c 4 -d 30

  # Ramp up load gradually
  python3 cpu_stress_test.py -d 60 --ramp-up

  # Quick 10-second test
  python3 cpu_stress_test.py --quick
        '''
    )

    parser.add_argument('-c', '--cores', type=int,
                        default=multiprocessing.cpu_count(),
                        help='Number of CPU cores to stress (default: all cores)')
    parser.add_argument('-d', '--duration', type=int, default=30,
                        help='Duration in seconds (default: 30)')
    parser.add_argument('--ramp-up', action='store_true',
                        help='Gradually ramp up load instead of full load immediately')
    parser.add_argument('--quick', action='store_true',
                        help='Quick 10-second test (same as -d 10)')

    args = parser.parse_args()

    if args.quick:
        args.duration = 10

    # Get CPU info
    cpu_count = multiprocessing.cpu_count()
    print(f"\n{Colors.BOLD}System Info:{Colors.NC}")
    print(f"  Available CPU cores: {cpu_count}")

    if args.cores > cpu_count:
        print(f"{Colors.RED}Warning: Requested {args.cores} cores but only {cpu_count} available.{Colors.NC}")
        print(f"Using {cpu_count} cores instead.")
        args.cores = cpu_count

    # Warn user
    print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  WARNING:{Colors.NC}")
    print(f"{Colors.YELLOW}This will put your CPU under heavy load.{Colors.NC}")
    print(f"{Colors.YELLOW}Make sure your temperature monitor is running!{Colors.NC}")
    print(f"\n{Colors.YELLOW}Check monitor with: tail -f ~/.temp_monitor.log{Colors.NC}")

    try:
        response = input(f"\n{Colors.CYAN}Continue? [y/N]: {Colors.NC}")
        if response.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)

    try:
        run_stress_test(args.cores, args.duration, args.ramp_up)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Stress test interrupted by user.{Colors.NC}")
        sys.exit(0)

if __name__ == "__main__":
    main()
