import argparse
from src.rag.ingest.youtube import main as ingest_main

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True, help="YouTube URL")
    p.add_argument("--out", default="data/raw", help="Output dir")
    return p.parse_args()

def main():
    args = parse_args()
    ingest_main(url=args.url, out_dir=args.out)


