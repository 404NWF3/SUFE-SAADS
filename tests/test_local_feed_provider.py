from __future__ import annotations

import json
import unittest
from pathlib import Path
import shutil
import uuid
from unittest.mock import patch

from saads_wp12.config import get_config
from saads_wp12.data.feed_provider import get_attack_feed_provider
from saads_wp12.data.local_feed_provider import LocalAttackFeedProvider


def _write_feed_fixture(root: Path) -> None:
    items_dir = root / "items"
    manifests_dir = root / "manifests"
    items_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    item_one = {
        "attack_id": "attack-001",
        "attack_code": "code-001",
        "canonical_name": "Prompt Injection Fixture",
        "attack_family": "prompt_injection",
        "severity_level": "high",
        "entry_status": "active",
        "summary": "Fixture one",
        "last_seen_at": "",
        "primary_cvss_version": "3.1",
        "primary_cvss_base_score": 8.2,
        "primary_cvss_vector": "",
        "primary_cvss_severity_label": "high",
        "taxonomy_type": "OWASP_LLM",
        "taxonomy_code": "OWASP-LLM-01",
        "taxonomy_name": "Prompt Injection",
        "component_id": "",
        "component_name": "",
        "version_constraint_raw": "",
        "normalized_constraint": "",
        "component_impact_scope": "",
        "asset_id": "",
        "asset_type": "",
        "asset_name": "",
        "artifact_uri": "",
        "qa_status": "",
        "active": True,
        "all_taxonomies": [
            {
                "map_id": 1,
                "taxonomy_type": "OWASP_LLM",
                "taxonomy_code": "OWASP-LLM-01",
                "taxonomy_name": "Prompt Injection",
                "is_primary": True,
                "confidence_score": 0.9,
            },
            {
                "map_id": 2,
                "taxonomy_type": "OWASP_LLM",
                "taxonomy_code": "OWASP-LLM-05",
                "taxonomy_name": "Supply Chain Vulnerabilities",
                "is_primary": False,
                "confidence_score": 0.6,
            },
        ],
        "description": "Detailed description",
        "exploit_preconditions": "",
        "attack_impact_scope": "",
        "attack_confidence_score": 0.8,
        "stix_type": "",
        "stix_payload": {},
        "component_context": {},
        "published_seed_assets": [],
        "component_risk_overview": {},
    }
    item_two = {
        **item_one,
        "attack_id": "attack-002",
        "attack_code": "code-002",
        "canonical_name": "Output Handling Fixture",
        "attack_family": "tool_hijack",
        "primary_cvss_base_score": 6.5,
        "taxonomy_code": "OWASP-LLM-02",
        "taxonomy_name": "Insecure Output Handling",
        "all_taxonomies": [
            {
                "map_id": 3,
                "taxonomy_type": "OWASP_LLM",
                "taxonomy_code": "OWASP-LLM-02",
                "taxonomy_name": "Insecure Output Handling",
                "is_primary": True,
                "confidence_score": 0.85,
            }
        ],
    }

    (items_dir / "attack-001.json").write_text(
        json.dumps(item_one, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (items_dir / "attack-002.json").write_text(
        json.dumps(item_two, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (manifests_dir / "attack_index.json").write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-04-05T19:00:00+08:00",
                "taxonomy_filter": ["OWASP-LLM-01", "OWASP-LLM-02"],
                "items": [
                    {
                        "attack_id": "attack-001",
                        "attack_code": "code-001",
                        "path": "items/attack-001.json",
                        "taxonomy_codes": ["OWASP-LLM-01", "OWASP-LLM-05"],
                        "attack_family": "prompt_injection",
                        "severity_level": "high",
                        "qa_status": "",
                    },
                    {
                        "attack_id": "attack-002",
                        "attack_code": "code-002",
                        "path": "items/attack-002.json",
                        "taxonomy_codes": ["OWASP-LLM-02"],
                        "attack_family": "tool_hijack",
                        "severity_level": "medium",
                        "qa_status": "",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


class LocalFeedProviderTest(unittest.TestCase):
    def _make_fixture_root(self) -> Path:
        root = Path("tests") / "_tmp_local_feed_provider" / uuid.uuid4().hex
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_list_attack_feed_refs_returns_filtered_rows(self) -> None:
        root = self._make_fixture_root()
        _write_feed_fixture(root)
        provider = LocalAttackFeedProvider(
            root_path=str(root),
            taxonomy_codes=("OWASP-LLM-01",),
        )

        refs = provider.list_attack_feed_refs()

        self.assertEqual(refs, [("attack-001", "code-001")])

    def test_get_attack_feed_item_maps_taxonomies(self) -> None:
        root = self._make_fixture_root()
        _write_feed_fixture(root)
        provider = LocalAttackFeedProvider(root_path=str(root))

        item = provider.get_attack_feed_item("attack-001")

        self.assertEqual(item.attack_id, "attack-001")
        self.assertEqual(item.taxonomy_code, "OWASP-LLM-01")
        self.assertEqual(len(item.all_taxonomies), 2)
        self.assertEqual(item.all_taxonomies[1].taxonomy_code, "OWASP-LLM-05")

    def test_get_attack_feed_provider_returns_local_json_provider(self) -> None:
        root = self._make_fixture_root()
        _write_feed_fixture(root)
        with patch.dict(
            "os.environ",
            {
                "WP12_FEED_SOURCE": "local_json",
                "WP12_LOCAL_FEED_ROOT": str(root),
                "WP12_DB_FEED_LIMIT": "10",
            },
            clear=False,
        ):
            get_config.cache_clear()
            try:
                provider = get_attack_feed_provider()
                self.assertIsInstance(provider, LocalAttackFeedProvider)
                self.assertEqual(provider.get_attack_feed_item().attack_id, "attack-001")
            finally:
                get_config.cache_clear()
