from pathlib import Path

from watchfiles import run_process


if __name__ == "__main__":
    run_process(str(Path(__file__).resolve().parent), target="main.main")
