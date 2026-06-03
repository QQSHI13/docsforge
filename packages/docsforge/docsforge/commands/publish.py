"""DocsForge publish command — one-command deploy to hosting platforms."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from docsforge import config as config_module

log = logging.getLogger(__name__)

# Known hosting platforms and their detection patterns
PLATFORMS = {
    'github_pages': {
        'name': 'GitHub Pages',
        'detect': ['.github/workflows/pages.yml', '.github/workflows/gh-pages.yml'],
        'deploy': 'gh_pages',
    },
    'netlify': {
        'name': 'Netlify',
        'detect': ['netlify.toml'],
        'deploy': 'netlify',
    },
    'vercel': {
        'name': 'Vercel',
        'detect': ['vercel.json'],
        'deploy': 'vercel',
    },
    'cloudflare_pages': {
        'name': 'Cloudflare Pages',
        'detect': ['wrangler.toml'],
        'deploy': 'cloudflare',
    },
}


def publish(config_file=None, site_dir=None, force_platform=None) -> int:
    """Build and publish documentation to detected hosting platform.
    
    Auto-detects the platform based on config files in the repo.
    Falls back to GitHub Pages if no platform is detected.
    
    Returns exit code: 0 = success, 1 = failure.
    """
    print()
    print("=" * 60)
    print("  DOCSFORGE PUBLISH")
    print("=" * 60)
    print()
    
    # 1. Find config and build
    try:
        cfg = config_module.load_config(config_file=config_file, site_dir=site_dir)
    except Exception as e:
        log.error(f"Failed to load config: {e}")
        print()
        print("  Run 'docsforge check' to diagnose configuration issues.")
        print()
        return 1
    
    # 2. Build first
    print("  Building site...")
    from docsforge.commands import build
    try:
        build.build(cfg, dirty=False)
        print("  ✓ Build complete")
    except Exception as e:
        log.error(f"Build failed: {e}")
        return 1
    
    # 3. Detect platform
    platform = force_platform or _detect_platform()
    
    if not platform:
        # Default to GitHub Pages
        platform = 'github_pages'
        print("  No platform detected. Defaulting to GitHub Pages.")
    
    print(f"  Platform:      {PLATFORMS[platform]['name']}")
    print()
    
    # 4. Deploy
    deploy_fn = globals()[f'_deploy_{PLATFORMS[platform]["deploy"]}']
    return deploy_fn(cfg)


def _detect_platform() -> str | None:
    """Detect hosting platform from repository files."""
    for platform_id, info in PLATFORMS.items():
        for indicator in info['detect']:
            if Path(indicator).exists():
                return platform_id
    return None


def _deploy_gh_pages(cfg) -> int:
    """Deploy to GitHub Pages using git push to gh-pages branch."""
    # Check if we're in a git repo
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            check=True,
        )
        git_dir = Path(result.stdout.strip()).parent
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.error("Not in a git repository. GitHub Pages requires git.")
        print()
        print("  To set up:")
        print("    git init")
        print("    git remote add origin https://github.com/USER/REPO.git")
        print()
        return 1
    
    # Get remote URL
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True,
            check=True,
        )
        remote_url = result.stdout.strip()
    except subprocess.CalledProcessError:
        log.error("No git remote 'origin' configured.")
        print()
        print("  Set up a remote:")
        print("    git remote add origin https://github.com/USER/REPO.git")
        print()
        return 1
    
    # Parse GitHub URL
    if 'github.com' not in remote_url:
        log.error("Remote is not GitHub. GitHub Pages only works with GitHub repos.")
        print(f"  Current remote: {remote_url}")
        return 1
    
    # Extract user/repo from URL
    match = re.match(r'(?:https://github\.com/|git@github\.com:)([^/]+)/([^/]+?)(?:\.git)?$', remote_url)
    if not match:
        log.error(f"Could not parse GitHub URL: {remote_url}")
        return 1
    
    user, repo = match.groups()
    site_url = f"https://{user}.github.io/{repo}/"
    
    print(f"  GitHub repo:     {user}/{repo}")
    print(f"  Site will be at: {site_url}")
    print()
    
    # Check if gh-pages branch exists or needs creating
    try:
        subprocess.run(
            ['git', 'show-ref', '--verify', '--quiet', 'refs/heads/gh-pages'],
            capture_output=True,
            check=True,
        )
        branch_exists = True
    except subprocess.CalledProcessError:
        branch_exists = False
    
    # Use git worktree to deploy
    site_dir = cfg.site_dir
    if not Path(site_dir).exists():
        log.error(f"Site directory not found: {site_dir}")
        return 1
    
    print("  Deploying to gh-pages branch...")
    
    try:
        # Create a temporary worktree for gh-pages
        tmp_dir = '/tmp/docsforge-gh-pages'
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        
        if branch_exists:
            # Clone existing gh-pages
            subprocess.run(
                ['git', 'clone', '--branch', 'gh-pages', '--single-branch', '.', tmp_dir],
                capture_output=True,
                check=True,
            )
        else:
            # Initialize orphan branch
            subprocess.run(
                ['git', 'init', tmp_dir],
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ['git', '-C', tmp_dir, 'checkout', '--orphan', 'gh-pages'],
                capture_output=True,
                check=True,
            )
        
        # Clear and copy new site
        for item in Path(tmp_dir).iterdir():
            if item.name != '.git':
                if item.is_dir():
                    import shutil
                    shutil.rmtree(item)
                else:
                    item.unlink()
        
        import shutil
        for item in Path(site_dir).iterdir():
            dest = Path(tmp_dir) / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        
        # Commit and push
        subprocess.run(
            ['git', '-C', tmp_dir, 'add', '-A'],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ['git', '-C', tmp_dir, 'commit', '-m', 'DocsForge publish'],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ['git', '-C', tmp_dir, 'push', 'origin', 'gh-pages'],
            capture_output=True,
            check=True,
        )
        
        print("  ✓ Published!")
        print()
        print(f"  Site live at: {site_url}")
        print()
        return 0
        
    except subprocess.CalledProcessError as e:
        log.error(f"Deploy failed: {e}")
        if e.stderr:
            log.error(e.stderr.decode())
        return 1


def _deploy_netlify(cfg) -> int:
    """Deploy to Netlify using netlify-cli."""
    # Check for netlify-cli
    try:
        subprocess.run(['netlify', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.error("netlify-cli not found. Install it:")
        print("  npm install -g netlify-cli")
        print()
        return 1
    
    site_dir = cfg.site_dir
    print(f"  Deploying {site_dir} to Netlify...")
    
    try:
        result = subprocess.run(
            ['netlify', 'deploy', '--dir', site_dir, '--prod'],
            capture_output=True,
            text=True,
            check=True,
        )
        print("  ✓ Published!")
        print()
        # Extract URL from output
        for line in result.stdout.splitlines():
            if 'URL:' in line or 'Live URL:' in line:
                print(f"  {line.strip()}")
        print()
        return 0
    except subprocess.CalledProcessError as e:
        log.error(f"Netlify deploy failed: {e.stderr}")
        return 1


def _deploy_vercel(cfg) -> int:
    """Deploy to Vercel using vercel CLI."""
    try:
        subprocess.run(['vercel', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.error("vercel CLI not found. Install it:")
        print("  npm install -g vercel")
        print()
        return 1
    
    site_dir = cfg.site_dir
    print(f"  Deploying {site_dir} to Vercel...")
    
    try:
        result = subprocess.run(
            ['vercel', '--cwd', site_dir, '--prod'],
            capture_output=True,
            text=True,
            check=True,
        )
        print("  ✓ Published!")
        print()
        for line in result.stdout.splitlines():
            if 'https://' in line:
                print(f"  Site: {line.strip()}")
        print()
        return 0
    except subprocess.CalledProcessError as e:
        log.error(f"Vercel deploy failed: {e.stderr}")
        return 1


def _deploy_cloudflare(cfg) -> int:
    """Deploy to Cloudflare Pages using Wrangler."""
    try:
        subprocess.run(['wrangler', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.error("wrangler not found. Install it:")
        print("  npm install -g wrangler")
        print()
        return 1
    
    site_dir = cfg.site_dir
    print(f"  Deploying {site_dir} to Cloudflare Pages...")
    
    try:
        result = subprocess.run(
            ['wrangler', 'pages', 'deploy', site_dir],
            capture_output=True,
            text=True,
            check=True,
        )
        print("  ✓ Published!")
        print()
        for line in result.stdout.splitlines():
            if 'https://' in line:
                print(f"  Site: {line.strip()}")
        print()
        return 0
    except subprocess.CalledProcessError as e:
        log.error(f"Cloudflare deploy failed: {e.stderr}")
        return 1
