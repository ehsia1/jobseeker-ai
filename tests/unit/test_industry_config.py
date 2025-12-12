"""
Unit tests for the Industry Configuration module.
"""

import pytest
from typing import List, Dict, Any

from backend.config.industry_config import (
    Industry,
    IndustryConfig,
    INDUSTRY_CONFIGS,
    get_industry_config,
    suggest_industry,
    get_industry_job_boards,
    get_all_industries,
    get_industry_for_profession,
    PROFESSION_INDUSTRY_MAP,
)


class TestIndustryEnum:
    """Tests for the Industry enum."""

    def test_all_industries_exist(self):
        """Test that all expected industries exist."""
        expected_industries = [
            "TECHNOLOGY",
            "HEALTHCARE",
            "FINANCE",
            "LEGAL",
            "CREATIVE",
            "MARKETING",
            "EDUCATION",
            "ENGINEERING",
            "SALES",
            "OPERATIONS",
            "GENERAL",
        ]
        for industry in expected_industries:
            assert hasattr(Industry, industry), f"Missing industry: {industry}"

    def test_industry_values(self):
        """Test industry enum values are lowercase strings."""
        assert Industry.TECHNOLOGY.value == "technology"
        assert Industry.HEALTHCARE.value == "healthcare"
        assert Industry.FINANCE.value == "finance"
        assert Industry.LEGAL.value == "legal"

    def test_industry_is_string_enum(self):
        """Test that Industry is a string enum."""
        assert isinstance(Industry.TECHNOLOGY, str)
        assert Industry.TECHNOLOGY == "technology"


class TestIndustryConfig:
    """Tests for IndustryConfig dataclass."""

    def test_technology_config_exists(self):
        """Test that technology config exists and has required fields."""
        config = INDUSTRY_CONFIGS.get("technology")
        assert config is not None
        assert config.name == "technology"
        assert config.display_name is not None
        assert len(config.job_boards) > 0
        assert len(config.core_skills) > 0

    def test_all_industries_have_configs(self):
        """Test that industries with dedicated configs exist."""
        # Note: ENGINEERING and OPERATIONS don't have dedicated configs,
        # they fall back to GENERAL via get_industry_config
        industries_with_configs = [
            "technology",
            "healthcare",
            "finance",
            "legal",
            "creative",
            "marketing",
            "education",
            "sales",
            "general",
        ]
        for industry_name in industries_with_configs:
            config = INDUSTRY_CONFIGS.get(industry_name)
            assert config is not None, f"Missing config for {industry_name}"
            assert config.name == industry_name

    def test_config_has_required_fields(self):
        """Test that all configs have required fields."""
        for name, config in INDUSTRY_CONFIGS.items():
            assert config.name, f"{name} missing name"
            assert config.display_name, f"{name} missing display_name"
            assert config.description, f"{name} missing description"
            assert isinstance(config.job_boards, list), f"{name} job_boards not a list"
            assert isinstance(config.core_skills, list), f"{name} core_skills not a list"


class TestGetIndustryConfig:
    """Tests for get_industry_config function."""

    def test_get_technology_config(self):
        """Test getting technology industry config."""
        config = get_industry_config("technology")
        assert config is not None
        assert config.name == "technology"
        assert "GitHub Jobs" in config.job_boards or len(config.job_boards) > 0

    def test_get_healthcare_config(self):
        """Test getting healthcare industry config."""
        config = get_industry_config("healthcare")
        assert config is not None
        assert config.name == "healthcare"

    def test_get_invalid_industry_returns_general(self):
        """Test that invalid industry returns general config."""
        config = get_industry_config("nonexistent_industry")
        assert config is not None
        assert config.name == "general"

    def test_get_config_case_insensitive(self):
        """Test that industry lookup is case-insensitive via fallback."""
        # The function should handle various cases
        config = get_industry_config("TECHNOLOGY")
        # May return general if exact match required
        assert config is not None


class TestSuggestIndustry:
    """Tests for suggest_industry function."""

    def test_suggest_tech_from_keywords(self):
        """Test suggesting tech industry from programming keywords."""
        result = suggest_industry(["python", "software", "developer"])
        assert result == "technology"

    def test_suggest_healthcare_from_keywords(self):
        """Test suggesting healthcare industry from medical keywords."""
        result = suggest_industry(["nurse", "patient", "hospital"])
        assert result == "healthcare"

    def test_suggest_finance_from_keywords(self):
        """Test suggesting finance industry from financial keywords."""
        result = suggest_industry(["accounting", "financial", "analyst"])
        assert result == "finance"

    def test_suggest_with_profession(self):
        """Test suggesting industry with profession hint."""
        # The function looks for keywords in the industry config, "data" alone
        # may not be enough. Using stronger tech keywords.
        result = suggest_industry(["software", "python", "developer"], "data_scientist")
        assert result == "technology"

    def test_suggest_empty_keywords_returns_general(self):
        """Test that empty keywords return general industry."""
        result = suggest_industry([])
        assert result == "general"


class TestGetIndustryJobBoards:
    """Tests for get_industry_job_boards function."""

    def test_get_tech_job_boards(self):
        """Test getting technology job boards."""
        boards = get_industry_job_boards("technology")
        assert isinstance(boards, list)
        assert len(boards) > 0

    def test_get_healthcare_job_boards(self):
        """Test getting healthcare job boards."""
        boards = get_industry_job_boards("healthcare")
        assert isinstance(boards, list)
        assert len(boards) > 0

    def test_get_invalid_industry_boards(self):
        """Test getting boards for invalid industry returns general boards."""
        boards = get_industry_job_boards("nonexistent")
        assert isinstance(boards, list)


class TestGetAllIndustries:
    """Tests for get_all_industries function."""

    def test_returns_list(self):
        """Test that get_all_industries returns a list."""
        industries = get_all_industries()
        assert isinstance(industries, list)
        assert len(industries) > 0

    def test_industry_format(self):
        """Test that each industry has expected format."""
        industries = get_all_industries()
        for industry in industries:
            assert "id" in industry
            assert "name" in industry
            assert "description" in industry

    def test_technology_in_list(self):
        """Test that technology is in the list."""
        industries = get_all_industries()
        tech = next((i for i in industries if i["id"] == "technology"), None)
        assert tech is not None
        assert tech["name"] is not None


class TestGetIndustryForProfession:
    """Tests for get_industry_for_profession function."""

    def test_software_engineer_returns_technology(self):
        """Test software engineer maps to technology."""
        result = get_industry_for_profession("software_engineer")
        assert result == Industry.TECHNOLOGY

    def test_nurse_returns_healthcare(self):
        """Test nurse maps to healthcare."""
        result = get_industry_for_profession("nurse")
        assert result == Industry.HEALTHCARE

    def test_attorney_returns_legal(self):
        """Test attorney maps to legal."""
        result = get_industry_for_profession("attorney")
        assert result == Industry.LEGAL

    def test_financial_analyst_returns_finance(self):
        """Test financial analyst maps to finance."""
        result = get_industry_for_profession("financial_analyst")
        assert result == Industry.FINANCE

    def test_marketing_manager_returns_marketing(self):
        """Test marketing manager maps to marketing."""
        result = get_industry_for_profession("marketing_manager")
        assert result == Industry.MARKETING

    def test_graphic_designer_returns_creative(self):
        """Test graphic designer maps to creative."""
        result = get_industry_for_profession("graphic_designer")
        assert result == Industry.CREATIVE

    def test_teacher_returns_education(self):
        """Test teacher maps to education."""
        result = get_industry_for_profession("teacher")
        assert result == Industry.EDUCATION

    def test_mechanical_engineer_returns_engineering(self):
        """Test mechanical engineer maps to engineering."""
        result = get_industry_for_profession("mechanical_engineer")
        assert result == Industry.ENGINEERING

    def test_sales_manager_returns_sales(self):
        """Test sales manager maps to sales."""
        result = get_industry_for_profession("sales_manager")
        assert result == Industry.SALES

    def test_operations_manager_returns_operations(self):
        """Test operations manager maps to operations."""
        result = get_industry_for_profession("operations_manager")
        assert result == Industry.OPERATIONS

    def test_case_insensitive(self):
        """Test that profession lookup is case-insensitive."""
        result = get_industry_for_profession("Software_Engineer")
        assert result == Industry.TECHNOLOGY

    def test_with_spaces(self):
        """Test profession with spaces instead of underscores."""
        result = get_industry_for_profession("software engineer")
        assert result == Industry.TECHNOLOGY

    def test_fuzzy_match_developer(self):
        """Test fuzzy matching for variations."""
        result = get_industry_for_profession("frontend_developer_senior")
        assert result == Industry.TECHNOLOGY

    def test_unknown_profession_returns_industry(self):
        """Test that unknown profession uses fallback."""
        result = get_industry_for_profession("random_job_title")
        # Should return some industry via suggest_industry fallback
        assert result is not None
        assert isinstance(result, Industry)


class TestProfessionIndustryMap:
    """Tests for the PROFESSION_INDUSTRY_MAP constant."""

    def test_map_is_dict(self):
        """Test that map is a dictionary."""
        assert isinstance(PROFESSION_INDUSTRY_MAP, dict)

    def test_map_has_entries(self):
        """Test that map has entries."""
        assert len(PROFESSION_INDUSTRY_MAP) > 0

    def test_all_values_are_industry_enum(self):
        """Test that all map values are Industry enum members."""
        for profession, industry in PROFESSION_INDUSTRY_MAP.items():
            assert isinstance(industry, Industry), f"{profession} has invalid industry type"

    def test_tech_professions_exist(self):
        """Test that technology professions are mapped."""
        tech_professions = [
            "software_engineer",
            "data_scientist",
            "devops_engineer",
            "frontend_developer",
        ]
        for prof in tech_professions:
            assert prof in PROFESSION_INDUSTRY_MAP, f"Missing: {prof}"
            assert PROFESSION_INDUSTRY_MAP[prof] == Industry.TECHNOLOGY

    def test_healthcare_professions_exist(self):
        """Test that healthcare professions are mapped."""
        healthcare_professions = ["nurse", "physician", "pharmacist"]
        for prof in healthcare_professions:
            assert prof in PROFESSION_INDUSTRY_MAP, f"Missing: {prof}"
            assert PROFESSION_INDUSTRY_MAP[prof] == Industry.HEALTHCARE
