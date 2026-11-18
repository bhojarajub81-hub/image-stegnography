import argparse
import os
import sys

import steg_analysis as sa


def main():
    parser = argparse.ArgumentParser(description="Analyze an image for steganographic content.")
    parser.add_argument("image", help="Image file to analyze")
    args = parser.parse_args()

    try:
        report = sa.analyze_file(args.image)
    except (FileNotFoundError, OSError) as error:
        sys.exit(f"Error: {error}")

    print(sa.format_report(os.path.basename(args.image), report))


if __name__ == "__main__":
    main()
