"""Integration and unit tests for bin/worktree-cleanup using real git repositories."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

_SCRIPT_PATH = Path(__file__).resolve().parent / "worktree-cleanup"
_LOADER = importlib.machinery.SourceFileLoader("worktree_cleanup", str(_SCRIPT_PATH))
_SPEC = importlib.util.spec_from_loader("worktree_cleanup", _LOADER)
assert _SPEC is not None
wc = importlib.util.module_from_spec(_SPEC)
sys.modules["worktree_cleanup"] = wc
_LOADER.exec_module(wc)


def _git(repo: Path, *args: str, commit_ts: int | None = None) -> str:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test User"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test User"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    if commit_ts is not None:
        stamp = f"{commit_ts} +0000"
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return proc.stdout.strip()


def _age_worktree(wt: Path, hours_ago: float) -> None:
    target_ts = time.time() - (hours_ago * 3600)
    info = wc._resolve_repo_info(wt)
    assert info is not None
    _, git_dir = info
    for p in (wt, git_dir / "HEAD", git_dir / "index", git_dir / "logs" / "HEAD"):
        if p.exists():
            os.utime(p, (target_ts, target_ts))


class TestWorktreeCleanup(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.remote = self.root / "origin.git"
        self.primary = self.root / "repo"
        self.wt_root = self.root / "worktrees"
        self.wt_repo_dir = self.wt_root / "repo"
        self.wt_repo_dir.mkdir(parents=True)

        old_ts = int(time.time() - (48 * 3600))
        subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "clone", str(self.remote), str(self.primary)], check=True, capture_output=True)
        _git(self.primary, "checkout", "-B", "main")
        (self.primary / "README.md").write_text("init\n", encoding="utf-8")
        _git(self.primary, "add", "README.md")
        _git(self.primary, "commit", "-m", "chore: init", commit_ts=old_ts)
        _git(self.primary, "push", "-u", "origin", "main")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _add_worktree(self, name: str, branch: str, *, hours_ago: float = 48.0) -> Path:
        wt = self.wt_repo_dir / name
        _git(self.primary, "worktree", "add", str(wt), "-b", branch, "origin/main")
        _age_worktree(wt, hours_ago)
        return wt

    def test_removes_old_merged_and_cherry_merged_skips_unsafe(self) -> None:
        old_ts = int(time.time() - (48 * 3600))

        # 1. Merged branch (>24h old, clean) -> removed
        wt_merged = self._add_worktree("wt_merged", "feat/merged", hours_ago=48)
        (wt_merged / "a.txt").write_text("a\n", encoding="utf-8")
        _git(wt_merged, "add", "a.txt")
        _git(wt_merged, "commit", "-m", "feat: a", commit_ts=old_ts)
        _git(self.primary, "merge", "--no-ff", "feat/merged", "-m", "merge feat/merged", commit_ts=old_ts)
        _git(self.primary, "push", "origin", "main")
        _age_worktree(wt_merged, 48)

        # 2. Rebased/cherry-equivalent branch (>24h old, clean) -> removed
        wt_cherry = self._add_worktree("wt_cherry", "feat/cherry", hours_ago=48)
        (wt_cherry / "b.txt").write_text("b\n", encoding="utf-8")
        _git(wt_cherry, "add", "b.txt")
        _git(wt_cherry, "commit", "-m", "feat: b", commit_ts=old_ts)
        _git(self.primary, "cherry-pick", "feat/cherry")
        _git(self.primary, "push", "origin", "main")
        _age_worktree(wt_cherry, 48)

        # 3. Unmerged branch (>24h old, clean) -> skipped
        wt_unmerged = self._add_worktree("wt_unmerged", "feat/unmerged", hours_ago=48)
        (wt_unmerged / "c.txt").write_text("c\n", encoding="utf-8")
        _git(wt_unmerged, "add", "c.txt")
        _git(wt_unmerged, "commit", "-m", "feat: c", commit_ts=old_ts)
        _age_worktree(wt_unmerged, 48)

        # 4. Dirty merged worktree -> skipped
        wt_dirty = self._add_worktree("wt_dirty", "feat/dirty", hours_ago=48)
        (wt_dirty / "untracked.txt").write_text("wip\n", encoding="utf-8")

        # 5. Recent clean worktree (<24h old) -> skipped
        wt_recent = self._add_worktree("wt_recent", "feat/recent", hours_ago=1)

        # 6. Locked worktree -> skipped
        wt_locked = self._add_worktree("wt_locked", "feat/locked", hours_ago=48)
        _git(self.primary, "worktree", "lock", str(wt_locked))

        # Dry-run removes nothing
        rc = wc.main(["--dry-run", "--root", str(self.wt_root), "--no-gh"])
        self.assertEqual(rc, 0)
        self.assertTrue(wt_merged.exists())

        # Real run removes only merged + cherry-merged
        rc = wc.main(["--root", str(self.wt_root), "--no-gh"])
        self.assertEqual(rc, 0)
        self.assertFalse(wt_merged.exists())
        self.assertFalse(wt_cherry.exists())
        self.assertTrue(wt_unmerged.exists())
        self.assertTrue(wt_dirty.exists())
        self.assertTrue(wt_recent.exists())
        self.assertTrue(wt_locked.exists())

    def test_skips_active_cwd_and_prunes_empty_parent(self) -> None:
        wt_cwd = self._add_worktree("wt_cwd", "feat/cwd", hours_ago=48)
        outcome = wc.evaluate_and_clean(
            wt_cwd,
            cwd=wt_cwd.resolve(),
            fetched=set(),
            min_age_hours=24.0,
            dry_run=False,
            no_fetch=True,
            use_gh=False,
        )
        self.assertEqual(outcome.status, "skipped")
        self.assertEqual(outcome.reason, "active cwd")
        self.assertTrue(wt_cwd.exists())

        # Removing from outside cwd removes the worktree and its empty parent dir
        rc = wc.main(["--root", str(self.wt_root), "--no-gh"])
        self.assertEqual(rc, 0)
        self.assertFalse(wt_cwd.exists())
        self.assertFalse(self.wt_repo_dir.exists())

    def test_gh_pr_squash_merge_requires_exact_head_sha(self) -> None:
        old_ts = int(time.time() - (48 * 3600))
        wt_sq = self._add_worktree("wt_sq", "feat/squash", hours_ago=48)
        (wt_sq / "sq.txt").write_text("sq\n", encoding="utf-8")
        _git(wt_sq, "add", "sq.txt")
        _git(wt_sq, "commit", "-m", "feat: squash", commit_ts=old_ts)
        _age_worktree(wt_sq, 48)
        head_sha = _git(wt_sq, "rev-parse", "HEAD")

        real_run = subprocess.run

        def fake_gh(stdout: str):
            def _runner(cmd, *args, **kwargs):
                if cmd and cmd[0] == "gh":
                    return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
                return real_run(cmd, *args, **kwargs)

            return _runner

        # Stale merged PR for same branch name with different SHA -> must NOT remove
        with mock.patch.object(wc.shutil, "which", return_value="/usr/bin/gh"), mock.patch.object(
            wc.subprocess, "run", side_effect=fake_gh('[{"headRefOid": "deadbeef"}]')
        ):
            outcome = wc.evaluate_and_clean(
                wt_sq,
                cwd=self.root.resolve(),
                fetched=set(),
                min_age_hours=24.0,
                dry_run=False,
                no_fetch=True,
                use_gh=True,
            )
            self.assertEqual(outcome.status, "skipped")
            self.assertEqual(outcome.reason, "unmerged vs origin/main")
            self.assertTrue(wt_sq.exists())

        # Exact headRefOid match -> removes cleanly
        with mock.patch.object(wc.shutil, "which", return_value="/usr/bin/gh"), mock.patch.object(
            wc.subprocess, "run", side_effect=fake_gh(f'[{{"headRefOid": "{head_sha}"}}]')
        ):
            outcome = wc.evaluate_and_clean(
                wt_sq,
                cwd=self.root.resolve(),
                fetched=set(),
                min_age_hours=24.0,
                dry_run=False,
                no_fetch=True,
                use_gh=True,
            )
            self.assertEqual(outcome.status, "removed")
            self.assertFalse(wt_sq.exists())

    def test_unbacked_env_files_and_repo_parent_safety(self) -> None:
        old_ts = int(time.time() - (48 * 3600))
        (self.primary / ".gitignore").write_text(".env*\n!.env.example\n", encoding="utf-8")
        _git(self.primary, "add", ".gitignore")
        _git(self.primary, "commit", "-m", "chore: ignore env", commit_ts=old_ts)
        _git(self.primary, "push", "origin", "main")
        (self.primary / ".env").write_text("KEY=primary\n", encoding="utf-8")

        # 1. Worktree with modified gitignored .env -> skipped
        wt_diff = self._add_worktree("wt_env_diff", "feat/env-diff", hours_ago=48)
        (wt_diff / ".env").write_text("KEY=unique_secret\n", encoding="utf-8")
        _age_worktree(wt_diff, 48)
        outcome = wc.evaluate_and_clean(
            wt_diff, cwd=self.root.resolve(), fetched=set(), min_age_hours=24.0, dry_run=False, no_fetch=True, use_gh=False
        )
        self.assertEqual(outcome.status, "skipped")
        self.assertEqual(outcome.reason, "unbacked .env file")
        self.assertTrue(wt_diff.exists())

        # 2. Worktree with identical .env + --repo outside managed roots -> removed, parent kept
        ext_parent = self.root / "external_parent"
        ext_parent.mkdir()
        wt_ext = ext_parent / "wt_ext"
        _git(self.primary, "worktree", "add", str(wt_ext), "-b", "feat/ext", "origin/main")
        (wt_ext / ".env").write_text("KEY=primary\n", encoding="utf-8")
        _age_worktree(wt_ext, 48)
        empty_root = self.root / "empty_root"
        empty_root.mkdir()
        rc = wc.main(["--root", str(empty_root), "--repo", str(self.primary), "--no-fetch", "--no-gh"])
        self.assertEqual(rc, 0)
        self.assertFalse(wt_ext.exists())
        self.assertTrue(ext_parent.exists())

    def test_run_git_handles_timeout(self) -> None:
        with mock.patch.object(wc.subprocess, "run", side_effect=subprocess.TimeoutExpired(["git"], 15)):
            proc = wc._run_git(self.primary, ["status"], timeout=15)
        self.assertEqual(proc.returncode, 124)
        self.assertIn("timed out", proc.stderr)


def run_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestWorktreeCleanup)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
