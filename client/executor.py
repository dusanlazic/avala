import argparse
from shared.logs import logger


def main(args):
    logger.done(f"Running exploit {args.name} against {args.targets}.")
    import time

    time.sleep(5)
    logger.debug("Attacks finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run attacks concurrently against provided teams using provided exploit."
    )
    parser.add_argument(
        "targets",
        type=str,
        nargs="+",
        help="IP addresses of targeted teams.",
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Alias of the exploit for its identification.",
    )
    parser.add_argument(
        "--module",
        type=str,
        required=True,
        help="Name of the Python module of the exploit (must contain 'exploit' function).",
    )
    parser.add_argument(
        "--timeout",
        default=30,
        type=str,
        required=True,
        help="Optional timeout for a single attack in seconds.",
    )

    args = parser.parse_args()
    main(args)
