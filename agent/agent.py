#!/usr/bin/env python3
import argparse
import sys

try:
    import yaml
except Exception:
    yaml = None


def load_config(path="agent/config.yaml"):
    if yaml is None:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def main():
    parser = argparse.ArgumentParser(description="Simple local agent scaffold")
    parser.add_argument("--config", "-c", default="agent/config.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    name = cfg.get("name", "agent")
    print(f"Starting agent '{name}' (Ctrl+C to exit)")
    try:
        while True:
            cmd = input("> ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit"):
                print("Goodbye")
                break
            # echo back for now
            print(f"Received command: {cmd}")
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")


if __name__ == "__main__":
    main()
