#!/usr/bin/env python3
"""Example usage of the CRPM library.

This script demonstrates how to use the CRPM library programmatically
to perform process mining analysis.
"""

from pathlib import Path
from datetime import date
from crpm.pipeline import (
    discover_heuristics_net,
    alignment_fitness,
    token_replay_fitness,
    precision,
)
from crpm.conformance import load_log


def main():
    """Run a basic process mining example."""
    # Path to the example log included in the repository
    log_path = Path(__file__).parent / "xes_logs" / "running-example.xes"
    
    if not log_path.exists():
        print(f"Error: Example log not found at {log_path}")
        return
    
    print("CRPM - Process Mining Example")
    print("=" * 40)
    
    # Load the event log
    print(f"Loading log from: {log_path}")
    log = load_log(log_path)
    
    if log is None:
        print("Error: Failed to load the log file")
        return
    
    print(f"Log loaded successfully with {len(log)} traces")
    
    # Discover a process model using heuristics miner
    print("Discovering process model using Heuristics Miner...")
    heu_net, net, im, fm = discover_heuristics_net(log)
    
    print("Process model discovered successfully!")
    
    # Compute conformance metrics
    print("Computing conformance metrics...")
    
    align_fitness = alignment_fitness(log, net, im, fm)
    token_fitness = token_replay_fitness(log, net, im, fm)
    prec = precision(log, net, im, fm)
    
    # Print results
    print("\nConformance Metrics:")
    print("-" * 20)
    print(f"Alignment Fitness: {align_fitness:.4f}")
    print(f"Token Replay Fitness: {token_fitness:.4f}")
    print(f"Precision: {prec:.4f}")
    
    print("\nExample completed successfully!")
    print("To run the Streamlit apps:")
    print("  streamlit run app.py")
    print("  streamlit run pipeline_app.py")


if __name__ == "__main__":
    main()