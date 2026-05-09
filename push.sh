#!/usr/bin/env bash
# Create demo site and push to GitHub
set -euo pipefail

cd /home/qq/.openclaw/workspace/projects/docsforge

# Check if git remote exists
if ! git remote get-url origin >/dev/null 2>&1; then
    echo "No remote set. Creating GitHub repo..."
    # Note: Need GitHub CLI or manual creation
    echo "Please create repo at https://github.com/new"
    echo "Then run: git remote add origin https://github.com/YOURNAME/docsforge.git"
    exit 1
fi

echo "Pushing to origin..."
git push -u origin master

echo "Done!"
