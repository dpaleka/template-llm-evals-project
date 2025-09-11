#!/bin/bash
# Remove git worktrees for branches that have been merged into main
# Usage: ./clean-worktrees.sh
#   Prompts once to apply the same answer (Yes to all) to all removals.

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Disallow deprecated/destructive flags
if [ "${1:-}" = "--all" ] || [ "${1:-}" = "-all" ]; then
    echo "Error: --all is not supported. The script prompts once for 'yes to all' instead."
    exit 1
fi

# Helper: list worktree paths for a given local branch using porcelain output
get_worktrees_for_branch() {
    local branch_name="$1"
    git worktree list --porcelain | awk -v b="refs/heads/${branch_name}" '
        BEGIN { RS=""; FS="\n" }
        {
            wt=""; br="";
            for (i = 1; i <= NF; i++) {
                line = $i
                if (line ~ /^worktree /) { wt = substr(line, 10) }
                else if (line ~ /^branch /) { br = substr(line, 8) }
            }
            if (br == b && wt != "") { print wt }
        }
    '
}

# Get list of branches from merged PRs using gh
echo "Fetching merged pull requests..."
MERGED_BRANCHES=$(gh pr list --state merged --limit 100 --json headRefName --jq '.[].headRefName' | sort -u)

if [ -z "$MERGED_BRANCHES" ]; then
    echo "No merged branches found."
    exit 0
fi

# Check which merged branches actually have worktrees
BRANCHES_WITH_WORKTREES=()
while IFS= read -r branch; do
    # Skip if branch doesn't exist locally
    if ! git show-ref --verify --quiet "refs/heads/${branch}"; then
        continue
    fi

    # Check if this branch has any worktrees
    WORKTREES=($(get_worktrees_for_branch "$branch"))
    if [ ${#WORKTREES[@]} -gt 0 ]; then
        BRANCHES_WITH_WORKTREES+=("$branch")
    fi
done <<< "$MERGED_BRANCHES"

if [ ${#BRANCHES_WITH_WORKTREES[@]} -eq 0 ]; then
    echo "No worktrees found for merged branches."
    exit 0
fi

echo "Found worktrees for the following merged branches:"
printf '%s\n' "${BRANCHES_WITH_WORKTREES[@]}"
echo

# Ask once whether to apply "yes to all" for removals
APPLY_YES_TO_ALL=false
read -p "Apply 'yes' to all removals? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    APPLY_YES_TO_ALL=true
fi

# Counter for removed worktrees
REMOVED_COUNT=0

# Process each branch that has worktrees
for branch in "${BRANCHES_WITH_WORKTREES[@]}"; do
    # Collect all worktrees attached to this branch using porcelain mapping
    WORKTREES=()
    while IFS= read -r line; do
        WORKTREES+=("$line")
    done < <(get_worktrees_for_branch "$branch")

    for WORKTREE_DIR in "${WORKTREES[@]}"; do
        echo "Found worktree for merged branch '${branch}' at ${WORKTREE_DIR}"

        # Confirm removal (per worktree unless applying yes to all)
        if [ "$APPLY_YES_TO_ALL" = true ]; then
            RESP="y"
            echo "Removing worktree (yes-to-all enabled)"
        else
            read -p "Remove this worktree? (y/N) " -n 1 -r
            echo
            RESP="$REPLY"
        fi

        if [[ $RESP =~ ^[Yy]$ ]]; then
            echo "Removing worktree at ${WORKTREE_DIR}..."

            removed_from_git=false
            if git worktree remove --force "${WORKTREE_DIR}"; then
                removed_from_git=true
            fi

            # If directory still exists, attempt to trash it if available
            if [ -d "${WORKTREE_DIR}" ]; then
                if command -v trash >/dev/null 2>&1; then
                    echo "Trashing directory ${WORKTREE_DIR}..."
                    if trash "${WORKTREE_DIR}"; then
                        :
                    else
                        echo "Warning: trash command failed for ${WORKTREE_DIR}"
                    fi
                else
                    echo "Warning: 'trash' command not found; directory remains at ${WORKTREE_DIR}"
                fi
            fi

            # Verify removal: not listed in worktrees AND directory gone
            still_listed=false
            if git worktree list | grep -F -q -- "${WORKTREE_DIR}"; then
                still_listed=true
            fi
            dir_exists=false
            if [ -d "${WORKTREE_DIR}" ]; then
                dir_exists=true
            fi

            if [ "$still_listed" = false ] && [ "$dir_exists" = false ]; then
                echo "Successfully removed worktree"
                ((REMOVED_COUNT++))
            else
                echo "Removal incomplete for ${WORKTREE_DIR}:" \
                     "listed_in_git=${still_listed}" \
                     "dir_exists=${dir_exists}"
            fi
        else
            echo "Skipping ${WORKTREE_DIR}"
            echo
        fi
    done

    # If no worktrees remain for this branch, attempt to delete the branch
    if ! git worktree list --porcelain | grep -q "^branch refs/heads/${branch}$"; then
        echo "Deleting branch '${branch}'..."
        git branch -D "${branch}" 2>/dev/null || git branch -d "${branch}"
        echo
    fi

done

echo "Removed $REMOVED_COUNT worktree(s)"

# List remaining worktrees
echo
echo "Remaining worktrees:"
git worktree list