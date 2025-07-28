"""Basic tests for the CRPM pipeline module."""

import unittest
import tempfile
from pathlib import Path
import pandas as pd
from datetime import date
from crpm.pipeline import (
    load_csv,
    csv_to_event_log,
    filter_date_range,
    split_by_date,
    discover_heuristics_net,
    discover_petri_inductive,
    alignment_fitness,
    token_replay_fitness,
    precision,
)
from pm4py.objects.log.importer.xes import importer as xes_importer


class TestPipeline(unittest.TestCase):
    """Test cases for pipeline functions."""

    def setUp(self):
        """Set up test data."""
        # Create a simple test CSV
        self.test_data = pd.DataFrame({
            "case_id": ["1", "1", "2", "2"],
            "activity": ["A", "B", "A", "C"],
            "timestamp": ["2024-01-01 10:00:00", "2024-01-01 11:00:00",
                          "2024-01-02 10:00:00", "2024-01-02 11:00:00"]
        })

        # Use the example log included in the repo
        self.log_path = Path(__file__).parent.parent / "xes_logs" / "running-example.xes"
        self.log = xes_importer.apply(str(self.log_path))

    def test_load_csv(self):
        """Test CSV loading."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            self.test_data.to_csv(f.name, index=False)
            csv_path = Path(f.name)

        try:
            df = load_csv(csv_path)
            self.assertIsInstance(df, pd.DataFrame)
            self.assertEqual(len(df), 4)
        finally:
            csv_path.unlink()

    def test_csv_to_event_log(self):
        """Test CSV to event log conversion."""
        log = csv_to_event_log(self.test_data, "case_id", "activity", "timestamp")
        self.assertGreater(len(log), 0)
        self.assertEqual(len(log), 2)  # Two cases

    def test_filter_date_range(self):
        """Test date range filtering."""
        # Test with no dates
        filtered = filter_date_range(self.log, None, None)
        self.assertEqual(len(filtered), len(self.log))

    def test_split_by_date(self):
        """Test log splitting by date."""
        cutoff = date(2024, 1, 1)
        before, after = split_by_date(self.log, cutoff)
        # Both should be EventLog objects
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)

    def test_discover_heuristics_net(self):
        """Test heuristics net discovery."""
        if len(self.log) > 0:
            heu_net, net, im, fm = discover_heuristics_net(self.log)
            self.assertIsNotNone(heu_net)
            self.assertIsNotNone(net)
            self.assertIsNotNone(im)
            self.assertIsNotNone(fm)

    def test_discover_petri_inductive(self):
        """Test inductive miner discovery."""
        if len(self.log) > 0:
            net, im, fm = discover_petri_inductive(self.log)
            self.assertIsNotNone(net)
            self.assertIsNotNone(im)
            self.assertIsNotNone(fm)

    def test_alignment_fitness(self):
        """Test alignment fitness calculation."""
        if len(self.log) > 0:
            _, net, im, fm = discover_heuristics_net(self.log)
            fitness = alignment_fitness(self.log, net, im, fm)
            self.assertIsInstance(fitness, (int, float))
            self.assertGreaterEqual(fitness, 0)
            self.assertLessEqual(fitness, 1)

    def test_token_replay_fitness(self):
        """Test token replay fitness calculation."""
        if len(self.log) > 0:
            _, net, im, fm = discover_heuristics_net(self.log)
            fitness = token_replay_fitness(self.log, net, im, fm)
            self.assertIsInstance(fitness, (int, float))
            self.assertGreaterEqual(fitness, 0)
            self.assertLessEqual(fitness, 1)

    def test_precision(self):
        """Test precision calculation."""
        if len(self.log) > 0:
            _, net, im, fm = discover_heuristics_net(self.log)
            prec = precision(self.log, net, im, fm)
            self.assertIsInstance(prec, (int, float))
            self.assertGreaterEqual(prec, 0)
            self.assertLessEqual(prec, 1)


if __name__ == "__main__":
    unittest.main()
