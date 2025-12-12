import asyncio
import os
import shutil
import subprocess
from importlib.resources import files as importlib_files
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape

from .config import assets


def gather_files(catalog_path: Path) -> list[Path]:
    return sorted(
        [file_path for file_path in catalog_path.rglob("*.xml") if file_path.is_file()]
    )


def get_template_env():
    templates_path = os.getenv('TEMPLATE_PATH')
    if templates_path is None:
        env = Environment(loader=PackageLoader("terms", "templates"), autoescape=select_autoescape())
    else:
        env = Environment(loader=FileSystemLoader(templates_path))

    return env


def copy_static(static_path: Path):
    shutil.copytree(str(importlib_files('terms') / 'static'), static_path, dirs_exist_ok=True)


async def download_assets(assets_path: Path) -> None:
    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            *[
                download_asset(client, asset_name, asset_url, assets_path)
                for asset_name, asset_url in assets
            ]
        )


async def download_asset(client: httpx.AsyncClient, asset_name: str, asset_url: str, assets_path: Path) -> None:
    response = await client.get(asset_url)
    response.raise_for_status()

    asset_path = assets_path / asset_name
    asset_path.parent.mkdir(exist_ok=True, parents=True)
    asset_path.write_bytes(response.content)

def get_git_info(file_path: Path) -> dict[str, str] | None:
    """Return metadata for the last commit touching ``file_path``.

    The information is collected directly from Git (if available) so it works
    for local paths as well as checked out submodules.
    """

    repo_root = _run_git_command(["rev-parse", "--show-toplevel"], file_path.parent)
    if not repo_root:
        return None

    relative_path = file_path.resolve().relative_to(Path(repo_root))

    commit_raw = _run_git_command(
        ["log", "-1", "--date=iso", "--format=%H%n%an%n%ad%n%s", "--", str(relative_path)],
        repo_root,
    )
    if not commit_raw:
        return None

    try:
        commit_hash, author, date, message = commit_raw.splitlines()
    except ValueError:
        return None

    remote_url = _normalize_remote_url(_run_git_command(["config", "--get", "remote.origin.url"], repo_root))
    branch = _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], repo_root) or "main"

    file_url = commit_url = None
    if remote_url:
        file_url = f"{remote_url}/blob/{branch}/{relative_path.as_posix()}"
        commit_url = f"{remote_url}/commit/{commit_hash}"

    return {
        "path": str(relative_path),
        "commit": commit_hash,
        "author": author,
        "date": date,
        "message": message,
        "file_url": file_url,
        "commit_url": commit_url,
        "repository": remote_url,
        "branch": branch,
    }


def _run_git_command(args: list[str], cwd: Path | str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    return result.stdout.strip()


def _normalize_remote_url(remote_url: str | None) -> str | None:
    if not remote_url:
        return None

    remote = remote_url
    if remote.startswith("git@"):
        remote = remote.replace(":", "/", 1)
        remote = remote.replace("git@", "https://", 1)

    if remote.endswith(".git"):
        remote = remote[:-4]

    return remote
