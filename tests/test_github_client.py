import subprocess

from phoenix_agent.github_client import GitHubClient


def _git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True
    )


def test_repair_branch_commit_and_push(tmp_path):
    bare_repo = tmp_path / "origin.git"
    worktree = tmp_path / "worktree"
    bare_repo.mkdir()
    worktree.mkdir()
    _git(bare_repo, "init", "--bare")
    _git(worktree, "init")
    _git(worktree, "config", "user.name", "PhoenixCI test")
    _git(worktree, "config", "user.email", "phoenixci-test@example.com")
    (worktree / "source.js").write_text("const priority = 'P4';\n", encoding="utf-8")
    _git(worktree, "add", "source.js")
    _git(worktree, "commit", "-m", "Add test source")
    base_sha = _git(worktree, "rev-parse", "HEAD").stdout.strip()
    _git(worktree, "remote", "add", "origin", str(bare_repo))
    _git(worktree, "push", "-u", "origin", "HEAD:main")
    (worktree / "source.js").write_text("const priority = 'P1';\n", encoding="utf-8")

    client = GitHubClient(
        repo_root=str(worktree),
        token="test-token",
        repository="example/project"
    )
    branch_name = "phoenix/repair-test"

    assert client.create_repair_branch(branch_name, base_sha)
    committed, commit_sha = client.commit_changes("Repair priority", ["source.js"])
    assert committed
    assert commit_sha != base_sha
    pushed, message = client.push_branch(branch_name)

    assert pushed, message
    remote_content = _git(
        bare_repo, "--git-dir", str(bare_repo), "show", f"{branch_name}:source.js"
    ).stdout
    assert remote_content == "const priority = 'P1';\n"


def test_create_pull_request_uses_bearer_token(monkeypatch, tmp_path):
    class Response:
        status_code = 201

        @staticmethod
        def json():
            return {"number": 9, "html_url": "https://github.com/example/project/pull/9"}

    calls = []
    response = Response()

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return response

    monkeypatch.setattr("phoenix_agent.github_client.requests.post", post)
    client = GitHubClient(
        repo_root=str(tmp_path),
        token="test-token",
        repository="example/project"
    )

    success, number, url = client.create_pull_request(
        branch_name="phoenix/fix",
        base_branch="main",
        title="Fix",
        body="Details"
    )

    assert success
    assert number == 9
    assert url.endswith("/pull/9")
    assert calls[0][1]["headers"]["Authorization"] == "Bearer test-token"

    response.status_code = 204
    dispatched, message = client.dispatch_workflow("ci.yml", "phoenix/fix")

    assert dispatched, message
    assert calls[1][0].endswith("/actions/workflows/ci.yml/dispatches")
    assert calls[1][1]["json"] == {"ref": "phoenix/fix"}
    assert calls[1][1]["headers"]["Authorization"] == "Bearer test-token"
