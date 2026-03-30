"""Tests for src/core/result.py"""

import pytest

from src.core.result import SkillResult


class TestSkillResultConstructors:
    def test_ok_sets_success_true(self):
        r = SkillResult.ok("done", rows_affected=10)
        assert r.success is True
        assert r.rows_affected == 10
        assert r.message == "done"
        assert r.error is None

    def test_fail_sets_success_false(self):
        err = ValueError("something broke")
        r = SkillResult.fail("error occurred", error=err)
        assert r.success is False
        assert r.error is err
        assert r.rows_affected == 0

    def test_ok_with_data(self):
        r = SkillResult.ok("extracted", rows_affected=5, data={"fixture_ids": [1, 2, 3]})
        assert r.data == {"fixture_ids": [1, 2, 3]}

    def test_fail_without_error(self):
        r = SkillResult.fail("no data available")
        assert r.success is False
        assert r.error is None


class TestSkillResultDefaults:
    def test_default_rows_affected_is_zero(self):
        r = SkillResult(success=True, message="ok")
        assert r.rows_affected == 0

    def test_default_data_is_none(self):
        r = SkillResult(success=True, message="ok")
        assert r.data is None

    def test_default_error_is_none(self):
        r = SkillResult(success=True, message="ok")
        assert r.error is None


class TestSkillResultStr:
    def test_str_ok(self):
        r = SkillResult.ok("all good", rows_affected=42)
        assert "OK" in str(r)
        assert "42" in str(r)

    def test_str_fail(self):
        r = SkillResult.fail("it failed")
        assert "FAIL" in str(r)
