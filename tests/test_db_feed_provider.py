from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from saads_wp12.config import get_config
from saads_wp12.data.db_feed_provider import DbAttackFeedProvider


class DbFeedProviderTaxonomyFilterTest(unittest.TestCase):
    def test_matches_taxonomy_filter_accepts_primary_taxonomy_code(self) -> None:
        provider = DbAttackFeedProvider(
            main_backend_path="C:/tmp/backend",
            taxonomy_codes=("OWASP-LLM-04",),
        )
        row = SimpleNamespace(taxonomy_code="OWASP-LLM-04")

        self.assertTrue(provider._matches_taxonomy_filter(row))

    def test_matches_taxonomy_filter_accepts_joined_taxonomy_map_code(self) -> None:
        provider = DbAttackFeedProvider(
            main_backend_path="C:/tmp/backend",
            taxonomy_codes=("OWASP-LLM-04",),
        )
        row = SimpleNamespace(taxonomy_code="")
        taxonomy_maps = [SimpleNamespace(taxonomy_code="OWASP-LLM-04")]

        self.assertTrue(provider._matches_taxonomy_filter(row, taxonomy_maps))

    def test_matches_taxonomy_filter_rejects_non_matching_taxonomy_code(self) -> None:
        provider = DbAttackFeedProvider(
            main_backend_path="C:/tmp/backend",
            taxonomy_codes=("OWASP-LLM-04",),
        )
        row = SimpleNamespace(taxonomy_code="OWASP-LLM-02")
        taxonomy_maps = [SimpleNamespace(taxonomy_code="OWASP-LLM-03")]

        self.assertFalse(provider._matches_taxonomy_filter(row, taxonomy_maps))

    def test_matches_taxonomy_filter_allows_everything_when_filter_disabled(self) -> None:
        provider = DbAttackFeedProvider(main_backend_path="C:/tmp/backend")
        row = SimpleNamespace(taxonomy_code="")

        self.assertTrue(provider._matches_taxonomy_filter(row))

    def test_apply_backend_db_env_overrides_sets_expected_values(self) -> None:
        provider = DbAttackFeedProvider(
            main_backend_path="C:/tmp/backend",
            backend_db_env={
                "POSTGRES_MIN_SIZE": "1",
                "POSTGRES_MAX_SIZE": "2",
                "POSTGRES_CONNECT_TIMEOUT": "10",
            },
        )

        provider._apply_backend_db_env_overrides()

        self.assertEqual(os.environ["POSTGRES_MIN_SIZE"], "1")
        self.assertEqual(os.environ["POSTGRES_MAX_SIZE"], "2")
        self.assertEqual(os.environ["POSTGRES_CONNECT_TIMEOUT"], "10")


class DbFeedConfigTaxonomyCodesTest(unittest.TestCase):
    def test_config_parses_db_feed_taxonomy_codes(self) -> None:
        with patch.dict(
            os.environ,
            {"WP12_DB_FEED_TAXONOMY_CODES": "OWASP-LLM-01, OWASP-LLM-04,OWASP-LLM-10"},
            clear=False,
        ):
            get_config.cache_clear()
            try:
                config = get_config()
                self.assertEqual(
                    config.db_feed_taxonomy_codes,
                    ("OWASP-LLM-01", "OWASP-LLM-04", "OWASP-LLM-10"),
                )
            finally:
                get_config.cache_clear()

    def test_config_parses_batch_db_pool_settings(self) -> None:
        with patch.dict(
            os.environ,
            {
                "WP12_DB_POOL_MIN_SIZE": "1",
                "WP12_DB_POOL_MAX_SIZE": "3",
                "WP12_DB_POOL_CONNECT_TIMEOUT": "12",
                "WP12_DB_POOL_STATEMENT_TIMEOUT_MS": "45000",
                "WP12_DB_POOL_APPLICATION_NAME": "wp12-batch-test",
            },
            clear=False,
        ):
            get_config.cache_clear()
            try:
                config = get_config()
                self.assertEqual(config.db_pool_min_size, 1)
                self.assertEqual(config.db_pool_max_size, 3)
                self.assertEqual(config.db_pool_connect_timeout, 12)
                self.assertEqual(config.db_pool_statement_timeout_ms, 45000)
                self.assertEqual(config.db_pool_application_name, "wp12-batch-test")
            finally:
                get_config.cache_clear()
