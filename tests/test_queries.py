"""Unit tests for mcp_disaster query functions.

These tests call the pure pandas functions in mcp_disaster/queries.py directly
(no MCP subprocess needed), satisfying ASR-3 (testability without infrastructure).
"""
import pandas as pd

from mcp_disaster.queries import get_disaster_statistics_impl, search_disasters_impl


class TestSearchDisasters:
    def test_no_filter_returns_rows(self, sample_df: pd.DataFrame) -> None:
        result = search_disasters_impl(sample_df)
        assert "No matching" not in result
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert len(lines) >= 2  # header + at least one data row

    def test_filter_by_type_flood(self, sample_df: pd.DataFrame) -> None:
        result = search_disasters_impl(sample_df, disaster_type="Flood")
        if "No matching" not in result:
            data_lines = result.splitlines()[1:]
            for line in data_lines:
                if line.strip():
                    assert "flood" in line.lower()

    def test_filter_by_country_china(self, sample_df: pd.DataFrame) -> None:
        result = search_disasters_impl(sample_df, country="China")
        if "No matching" not in result:
            data_lines = result.splitlines()[1:]
            for line in data_lines:
                if line.strip():
                    assert "china" in line.lower()

    def test_year_range_filters(self, sample_df: pd.DataFrame) -> None:
        result = search_disasters_impl(sample_df, year_min=2000, year_max=2010)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_results_message(self, sample_df: pd.DataFrame) -> None:
        result = search_disasters_impl(sample_df, country="Atlantis")
        assert "No matching" in result

    def test_limit_applied(self, sample_df: pd.DataFrame) -> None:
        result = search_disasters_impl(sample_df, limit=3)
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert len(lines) <= 4  # header + max 3 rows

    def test_case_insensitive_type(self, sample_df: pd.DataFrame) -> None:
        r_lower = search_disasters_impl(sample_df, disaster_type="flood")
        r_upper = search_disasters_impl(sample_df, disaster_type="Flood")
        assert r_lower == r_upper

    def test_combined_filters(self, sample_df: pd.DataFrame) -> None:
        result = search_disasters_impl(
            sample_df, disaster_type="Flood", year_min=2000, year_max=2021
        )
        assert isinstance(result, str)

    def test_empty_df_returns_no_match(self) -> None:
        empty = pd.DataFrame(
            columns=["year", "disaster_type", "country", "region",
                     "continent", "total_deaths", "total_affected"]
        )
        result = search_disasters_impl(empty)
        assert "No matching" in result


class TestGetDisasterStatistics:
    def test_default_group_by_disaster_type(self, sample_df: pd.DataFrame) -> None:
        result = get_disaster_statistics_impl(sample_df)
        assert "disaster_type" in result
        assert "No matching" not in result

    def test_group_by_country(self, sample_df: pd.DataFrame) -> None:
        result = get_disaster_statistics_impl(sample_df, group_by="country")
        assert "country" in result

    def test_metric_event_count(self, sample_df: pd.DataFrame) -> None:
        result = get_disaster_statistics_impl(
            sample_df, group_by="disaster_type", metric="event_count"
        )
        assert "event_count" in result

    def test_metric_total_affected(self, sample_df: pd.DataFrame) -> None:
        result = get_disaster_statistics_impl(
            sample_df, group_by="continent", metric="total_affected"
        )
        assert "total_affected" in result

    def test_top_n_limits_rows(self, sample_df: pd.DataFrame) -> None:
        result = get_disaster_statistics_impl(
            sample_df, group_by="disaster_type", metric="event_count", top_n=3
        )
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert len(lines) <= 4  # header + max 3 rows

    def test_invalid_group_by_returns_error(self, sample_df: pd.DataFrame) -> None:
        result = get_disaster_statistics_impl(sample_df, group_by="bad_column")
        assert "Unknown group_by" in result
        assert "Available" in result

    def test_invalid_metric_returns_error(self, sample_df: pd.DataFrame) -> None:
        result = get_disaster_statistics_impl(sample_df, metric="bad_metric")
        assert "Unknown metric" in result
        assert "Available" in result

    def test_group_by_year(self, sample_df: pd.DataFrame) -> None:
        result = get_disaster_statistics_impl(
            sample_df, group_by="year", metric="total_deaths"
        )
        assert "year" in result
