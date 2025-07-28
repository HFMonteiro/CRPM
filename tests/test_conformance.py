"""Basic tests for the CRPM conformance module."""

import unittest
from pathlib import Path
from crpm.conformance import (
    load_log,
    filter_start_event,
    run_heuristics_miner,
    compute_alignments,
    compute_token_replay,
    summarize_metrics,
)


class TestConformance(unittest.TestCase):
    """Test cases for conformance checking functions."""

    def setUp(self):
        """Set up test data."""
        # Use the example log included in the repo
        self.log_path = Path(__file__).parent.parent / "xes_logs" / "running-example.xes"
        self.log = load_log(self.log_path)

    def test_load_log(self):
        """Test log loading functionality."""
        self.assertIsNotNone(self.log)
        self.assertGreater(len(self.log), 0)

    def test_filter_start_event(self):
        """Test filtering by start event."""
        # Test with no filter
        filtered_none = filter_start_event(self.log, None)
        self.assertEqual(len(filtered_none), len(self.log))

        # Test with empty string
        filtered_empty = filter_start_event(self.log, "")
        self.assertEqual(len(filtered_empty), len(self.log))

        # Test with actual event (assuming the log has some events)
        if len(self.log) > 0 and len(self.log[0]) > 0:
            first_event = self.log[0][0]["concept:name"]
            filtered = filter_start_event(self.log, first_event)
            self.assertGreaterEqual(len(filtered), 0)
            if len(filtered) > 0:
                self.assertEqual(filtered[0][0]["concept:name"], first_event)

    def test_run_heuristics_miner(self):
        """Test heuristics miner functionality."""
        if len(self.log) > 0:
            heu_net, net, im, fm = run_heuristics_miner(self.log)
            self.assertIsNotNone(heu_net)
            self.assertIsNotNone(net)
            self.assertIsNotNone(im)
            self.assertIsNotNone(fm)

    def test_compute_alignments(self):
        """Test alignment computation."""
        if len(self.log) > 0:
            _, net, im, fm = run_heuristics_miner(self.log)
            align_res = compute_alignments(self.log, net, im, fm)
            self.assertIn("aligned_traces", align_res)
            self.assertIn("fitness", align_res)

    def test_compute_token_replay(self):
        """Test token replay computation."""
        if len(self.log) > 0:
            _, net, im, fm = run_heuristics_miner(self.log)
            token_res = compute_token_replay(self.log, net, im, fm)
            self.assertIn("token_results", token_res)
            self.assertIn("fitness", token_res)

    def test_summarize_metrics(self):
        """Test metrics summarization."""
        if len(self.log) > 0:
            _, net, im, fm = run_heuristics_miner(self.log)
            align_res = compute_alignments(self.log, net, im, fm)
            token_res = compute_token_replay(self.log, net, im, fm)
            summary = summarize_metrics(align_res, token_res)
            self.assertIn("alignment_fitness", summary)
            self.assertIn("token_fitness", summary)


if __name__ == "__main__":
    unittest.main()
