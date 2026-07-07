"""
Solar Plant Performance Monitoring & Alert System -- entry point.

Usage:
    python main.py --generate-sample        # create synthetic incoming CSVs
    python main.py --once                    # process everything in data/incoming once
    python main.py --run                     # run continuously on a schedule (every N min)
"""
import argparse

import generate_sample_data


def main():
    parser = argparse.ArgumentParser(description="Solar Plant Performance Monitoring & Alert System")
    parser.add_argument("--generate-sample", action="store_true",
                         help="Generate synthetic sensor CSVs into data/incoming/")
    parser.add_argument("--batches", type=int, default=12, help="Number of sample batches to generate")
    parser.add_argument("--once", action="store_true", help="Run the pipeline once on current incoming files")
    parser.add_argument("--run", action="store_true", help="Run the pipeline continuously on a schedule")
    args = parser.parse_args()

    if args.generate_sample:
        generate_sample_data.main(batches=args.batches)

    if args.once or args.run:
        from src import scheduler  # imported lazily so --generate-sample works
                                    # even before installing scheduling deps

    if args.once:
        scheduler.run_pipeline_once()

    if args.run:
        scheduler.start_scheduler()

    if not any([args.generate_sample, args.once, args.run]):
        parser.print_help()


if __name__ == "__main__":
    main()
