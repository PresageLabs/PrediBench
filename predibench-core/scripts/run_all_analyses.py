#!/usr/bin/env python3
"""
Script to run all Python analysis scripts using uv.
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Run all Python scripts in the analyses directory."""
    script_dir = Path(__file__).parent
    analyses_dir = script_dir / "analyses"

    if not analyses_dir.exists():
        print(f"Error: analyses directory not found at {analyses_dir}")
        sys.exit(1)

    # Find all Python scripts in analyses directory
    python_scripts = list(analyses_dir.glob("*.py"))

    if not python_scripts:
        print("No Python scripts found in analyses directory")
        return

    print(f"Found {len(python_scripts)} Python scripts to run:")
    for script in python_scripts:
        print(f"  - {script.name}")

    print("\nRunning scripts...")

    failed_scripts = []

    for script in python_scripts:
        print(f"\n{'='*60}")
        print(f"Running {script.name}...")
        print(f"{'='*60}")

        try:
            # Run script using uv
            result = subprocess.run(
                ["uv", "run", str(script)],
                cwd=script_dir.parent,  # Run from predibench-core directory
                check=True
            )
            print(f"✓ {script.name} completed successfully")

        except subprocess.CalledProcessError as e:
            print(f"✗ {script.name} failed with exit code {e.returncode}")
            failed_scripts.append(script.name)
        except Exception as e:
            print(f"✗ {script.name} failed with error: {e}")
            failed_scripts.append(script.name)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total scripts: {len(python_scripts)}")
    print(f"Successful: {len(python_scripts) - len(failed_scripts)}")
    print(f"Failed: {len(failed_scripts)}")

    if failed_scripts:
        print("\nFailed scripts:")
        for script in failed_scripts:
            print(f"  - {script}")
        sys.exit(1)
    else:
        print("\nAll scripts completed successfully!")


if __name__ == "__main__":
    main()