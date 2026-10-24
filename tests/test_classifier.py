import pytest
from phoenix_agent.classifier import FailureClassifier


def test_classify_dependency_failure(fixtures_dir):
    log_content = (fixtures_dir / "mock_dependency_failure.log").read_text(encoding="utf-8")
    category, confidence, evidence = FailureClassifier.classify(log_content, "npm-install")
    assert category == "dependency_version"
    assert confidence >= 0.70
    assert len(evidence) > 0
    assert any("ETARGET" in e or "notarget" in e for e in evidence)


def test_classify_dockerfile_failure(fixtures_dir):
    log_content = (fixtures_dir / "mock_docker_failure.log").read_text(encoding="utf-8")
    category, confidence, evidence = FailureClassifier.classify(log_content, "docker-build")
    assert category == "dockerfile_error"
    assert confidence >= 0.70
    assert len(evidence) > 0


def test_classify_unit_test_failure(fixtures_dir):
    log_content = (fixtures_dir / "mock_test_failure.log").read_text(encoding="utf-8")
    category, confidence, evidence = FailureClassifier.classify(log_content, "npm-test")
    assert category == "unit_test_regression"
    assert confidence >= 0.70
    assert len(evidence) > 0


def test_classify_unsupported_failure(fixtures_dir):
    log_content = (fixtures_dir / "mock_unsupported_failure.log").read_text(encoding="utf-8")
    category, confidence, evidence = FailureClassifier.classify(log_content, "git-merge")
    assert category == "unsupported"
    assert confidence <= 0.50


def test_classify_empty_log():
    category, confidence, evidence = FailureClassifier.classify("", "")
    assert category == "unsupported"
    assert confidence == 0.0
