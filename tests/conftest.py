import os
import sys
from pathlib import Path
import pytest

# Ensure phoenixci/agent is in Python module search path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent"))

@pytest.fixture
def repo_root():
    return str(REPO_ROOT)

@pytest.fixture
def policy_path():
    return str(REPO_ROOT / "config" / "repair-policy.yaml")

@pytest.fixture
def fixtures_dir():
    return REPO_ROOT / "fixtures"
