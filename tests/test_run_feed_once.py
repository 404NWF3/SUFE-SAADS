from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from saads_wp12.config import get_config
from saads_wp12.run_feed_once import run_feed_once


class RunFeedOnceTest(unittest.TestCase):
    def _make_registry_path(self) -> Path:
        root = Path("tests") / "_tmp_run_feed_once" / uuid.uuid4().hex
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root / "processed_attack_ids.json"

    def test_run_feed_once_processes_only_unseen_items(self) -> None:
        registry_path = self._make_registry_path()
        registry_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "processed_attacks": {
                        "atk-001": {
                            "run_id": "existing-run",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        with patch.dict(
            "os.environ",
            {
                "WP12_FEED_SOURCE": "mock",
                "WP12_PROCESS_LIMIT": "2",
                "WP12_DEDUP_REGISTRY_PATH": str(registry_path),
            },
            clear=False,
        ), patch(
            "saads_wp12.run_feed_once.graph.invoke",
            side_effect=[
                {
                    "run_id": "run-atk-002",
                    "verdict": "planned",
                    "persistence_path": "artifacts/run-atk-002",
                },
                {
                    "run_id": "run-atk-003",
                    "verdict": "planned",
                    "persistence_path": "artifacts/run-atk-003",
                },
            ],
        ):
            get_config.cache_clear()
            try:
                summary = run_feed_once()
            finally:
                get_config.cache_clear()

        self.assertEqual(summary["status"], "done")
        self.assertEqual(summary["requested_to_process"], 2)
        self.assertEqual(summary["processed_count"], 2)
        self.assertEqual(summary["error_count"], 0)
        self.assertEqual(summary["results"][0]["attack_id"], "atk-002")
        self.assertEqual(summary["results"][1]["attack_id"], "atk-003")

        saved_registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertIn("atk-001", saved_registry["processed_attacks"])
        self.assertIn("atk-002", saved_registry["processed_attacks"])
        self.assertIn("atk-003", saved_registry["processed_attacks"])

    def test_run_feed_once_is_idle_when_everything_is_processed(self) -> None:
        registry_path = self._make_registry_path()
        registry_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "processed_attacks": {
                        f"atk-00{index}": {"run_id": f"run-{index}"}
                        for index in range(1, 8)
                    },
                }
            ),
            encoding="utf-8",
        )

        with patch.dict(
            "os.environ",
            {
                "WP12_FEED_SOURCE": "mock",
                "WP12_DEDUP_REGISTRY_PATH": str(registry_path),
            },
            clear=False,
        ):
            get_config.cache_clear()
            try:
                summary = run_feed_once()
            finally:
                get_config.cache_clear()

        self.assertEqual(summary["status"], "idle")
        self.assertEqual(summary["processed_count"], 0)
        self.assertEqual(summary["skipped_existing"], 7)
