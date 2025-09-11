#!/bin/bash
# Create a git worktree for an issue and open Claude Code there
# Can be run with: source claude-worktree.sh <issue-number> or source claude-worktree.sh <existing-upstream-branch-name>

# Set up alias for cl
alias cl="claude --dangerously-skip-permissions"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    return 1 2>/dev/null || exit 1
fi

if [ $# -eq 0 ]; then
    echo "Usage: source $0 <issue-number|branch-name>"
    echo "Example: source $0 18"
    echo "Example: source $0 feature-branch"
    return 1 2>/dev/null || exit 1
fi

# Fetch latest changes from remote
echo "Fetching latest changes from remote..."
git fetch

ARG=$1

# Check if argument is a number (issue) or string (branch name)
if [[ "$ARG" =~ ^[0-9]+$ ]]; then
    # It's an issue number
    ISSUE_NUM=$ARG
    WORKTREE_DIR="../$(basename $(pwd))-issue-$ISSUE_NUM"

    # Check if worktree already exists
    if [ -d "$WORKTREE_DIR" ]; then
        echo "Worktree already exists at $WORKTREE_DIR, changing directory..."
        cd "$WORKTREE_DIR"
        return 0 2>/dev/null || exit 0
    fi

    # Use Claude to determine the appropriate branch name based on the issue
    echo "Asking Claude for branch name based on issue #$ISSUE_NUM..."
    BRANCH_NAME=$(cl -p "Run gh issue view $ISSUE_NUM and suggest a short branch name based on the issue title. The branch name should be in the format 'issue-NUMBER-short-description' where the description is 2-4 words in kebab-case. Output ONLY the branch name, nothing else." --allowedTools "Bash" 2>/dev/null | tail -1)

    # Fallback if Claude fails
    if [ -z "$BRANCH_NAME" ] || [ "$BRANCH_NAME" = "" ]; then
        BRANCH_NAME="issue-$ISSUE_NUM"
        echo "Using fallback branch name: $BRANCH_NAME"
    else
        echo "Claude suggested branch name: $BRANCH_NAME"
    fi
else
    # It's a branch name
    BRANCH_NAME=$ARG
    WORKTREE_DIR="../$(basename $(pwd))-$BRANCH_NAME"

    # Check if worktree already exists
    if [ -d "$WORKTREE_DIR" ]; then
        echo "Worktree already exists at $WORKTREE_DIR, changing directory..."
        cd "$WORKTREE_DIR"
        return 0 2>/dev/null || exit 0
    fi

    echo "Using provided branch name: $BRANCH_NAME"
fi

# Check if branch already exists locally
if git show-ref --verify --quiet refs/heads/"$BRANCH_NAME"; then
    echo "Branch $BRANCH_NAME already exists locally, creating worktree..."
    git worktree add "$WORKTREE_DIR" "$BRANCH_NAME"
# Check if branch exists on remote
elif git show-ref --verify --quiet refs/remotes/origin/"$BRANCH_NAME"; then
    echo "Branch $BRANCH_NAME exists on remote, creating worktree and tracking remote branch..."
    git worktree add -b "$BRANCH_NAME" "$WORKTREE_DIR" "origin/$BRANCH_NAME"
else
    echo "Creating worktree at $WORKTREE_DIR with new branch $BRANCH_NAME..."
    git worktree add -b "$BRANCH_NAME" "$WORKTREE_DIR"
fi

# Copy .env file if it exists
if [ -f .env ]; then
    echo "Copying .env file to new worktree..."
    cp .env "$WORKTREE_DIR/"
fi

# Symlink .venv if it exists
if [ -d .venv ]; then
    echo "Creating symlink to .venv..."
    ln -sf "$(pwd)/.venv" "$WORKTREE_DIR/.venv"
fi

# Symlink .cache if it exists
if [ -d .cache ]; then
    echo "Creating symlink to .cache..."
    ln -sf "$(pwd)/.cache" "$WORKTREE_DIR/.cache"
fi

# Symlink .pytest_cache if it exists
if [ -d .pytest_cache ]; then
    echo "Creating symlink to .pytest_cache..."
    ln -sf "$(pwd)/.pytest_cache" "$WORKTREE_DIR/.pytest_cache"
fi

# Symlink uv.lock if it exists (for dependency consistency)
if [ -f uv.lock ]; then
    echo "Creating symlink to uv.lock..."
    ln -sf "$(pwd)/uv.lock" "$WORKTREE_DIR/uv.lock"
fi

echo "Changing to worktree directory..."
cd "$WORKTREE_DIR"

# Authenticate with GitHub if GH_TOKEN is set
if [ -n "$GH_TOKEN" ]; then
    echo "Authenticating with GitHub..."
    gh auth login --with-token < <(echo $GH_TOKEN)
fi

# Ready to start Claude Code
if [[ "$ARG" =~ ^[0-9]+$ ]]; then
    echo "Worktree setup complete. Ready to work on issue #$ISSUE_NUM"
else
    echo "Worktree setup complete. Ready to work on branch $BRANCH_NAME"
fi