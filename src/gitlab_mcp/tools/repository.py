"""Repository and file tools."""

from typing import Any, cast
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project, get_client
from gitlab_mcp.models import (
    FileSummary,
    FileContents,
    CommitSummary,
    BranchSummary,
    FileOperationResult,
    BranchDeleteResult,
    CommitPushResult,
    CommitDetails,
    CommitDiffResult,
    BranchDiffResult,
    BranchComparison,
    FileDeleteResult,
    FileChange,
    ComparisonCommit,
)


@mcp.tool(annotations={"title": "Get File", "readOnlyHint": True, "openWorldHint": True})
def get_file_contents(
    project_id: str,
    file_path: str,
    ref: str = "HEAD",
) -> FileContents:
    """Get the contents of a file from the repository.

    Args:
        project_id: Project ID or path
        file_path: Path to the file in the repository
        ref: Branch, tag, or commit SHA (default: HEAD)
    """
    project = get_project(project_id)
    f = project.files.get(file_path=file_path, ref=ref)
    content = f.decode().decode("utf-8")

    return FileContents.model_validate(
        {
            "path": file_path,
            "content": content,
            "size": len(content),
            "last_commit": f.last_commit_id[:8],
        },
        from_attributes=True,
    )


@mcp.tool(annotations={"title": "List Files", "readOnlyHint": True, "openWorldHint": True})
def list_directory(
    project_id: str,
    path: str = "",
    ref: str = "HEAD",
) -> list[FileSummary]:
    """List files and directories in a repository path.

    Args:
        project_id: Project ID or path
        path: Directory path (empty for root)
        ref: Branch, tag, or commit SHA
    """
    project = get_project(project_id)
    items: Any = project.repository_tree(path=path, ref=ref)
    return FileSummary.from_gitlab(items)


@mcp.tool(
    annotations={
        "title": "Save File",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def create_or_update_file(
    project_id: str,
    file_path: str,
    content: str,
    commit_message: str,
    branch: str,
    create_branch: bool = False,
) -> FileOperationResult:
    """Create or update a file in the repository.

    Args:
        project_id: Project ID or path
        file_path: Path for the file
        content: File content
        commit_message: Commit message
        branch: Branch to commit to
        create_branch: If True and branch doesn't exist, create it from default branch
    """
    project = get_project(project_id)

    # Check if branch exists, create if needed
    if create_branch:
        try:
            project.branches.get(branch)
        except Exception:
            # Branch doesn't exist, create it
            default_branch = project.default_branch or "main"
            project.branches.create({"branch": branch, "ref": default_branch})

    # Get old content for diff calculation
    old_content = ""
    try:
        f = project.files.get(file_path=file_path, ref=branch)
        old_content = f.decode().decode("utf-8")
        f.content = content
        f.save(branch=branch, commit_message=commit_message)
        action = "updated"
    except Exception:
        # File doesn't exist, create it
        project.files.create(
            {
                "file_path": file_path,
                "branch": branch,
                "content": content,
                "commit_message": commit_message,
            }
        )
        action = "created"

    # Calculate diff stats
    old_lines = old_content.splitlines() if old_content else []
    new_lines = content.splitlines() if content else []
    lines_added = len([line for line in new_lines if line not in old_lines])
    lines_removed = len([line for line in old_lines if line not in new_lines])

    return FileOperationResult.model_validate(
        {
            "path": file_path,
            "action": action,
            "branch": branch,
            "commit_message": commit_message,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
        }
    )


@mcp.tool(annotations={"title": "List Commits", "readOnlyHint": True, "openWorldHint": True})
def list_commits(
    project_id: str,
    ref: str = "HEAD",
    limit: int = 20,
    path: str = "",
    include_stats: bool = False,
) -> list[CommitSummary]:
    """List commits in a repository.

    Args:
        project_id: Project ID or path
        ref: Branch, tag, or commit SHA to start from
        limit: Maximum number of commits
        path: Filter by file path (only commits touching this path)
        include_stats: If True, fetch commit statistics (files changed, insertions, deletions)
    """
    project = get_project(project_id)
    kwargs = {"ref_name": ref, "per_page": limit}
    if path:
        kwargs["path"] = path
    if include_stats:
        kwargs["with_stats"] = True
    commits = project.commits.list(**kwargs)

    return CommitSummary.from_gitlab(commits)


@mcp.tool(
    annotations={
        "title": "Create Branch",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_branch(
    project_id: str,
    branch_name: str,
    ref: str = "HEAD",
) -> BranchSummary:
    """Create a new branch.

    Args:
        project_id: Project ID or path
        branch_name: Name for the new branch
        ref: Source branch, tag, or commit SHA
    """
    project = get_project(project_id)
    branch = project.branches.create({"branch": branch_name, "ref": ref})
    return BranchSummary.from_gitlab(branch)


@mcp.tool(
    annotations={
        "title": "Delete Branch",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_branch(
    project_id: str,
    branch_name: str,
) -> BranchDeleteResult:
    """Delete a branch from the repository.

    Args:
        project_id: Project ID or path
        branch_name: Name of the branch to delete

    Note: Cannot delete protected branches without unprotecting first.
    """
    project = get_project(project_id)
    branch = project.branches.get(branch_name)

    if branch.protected:
        return BranchDeleteResult.model_validate(
            {
                "deleted": False,
                "branch": branch_name,
                "error": "Cannot delete protected branch",
                "protected": True,
            }
        )

    project.branches.delete(branch_name)
    return BranchDeleteResult.model_validate(
        {
            "deleted": True,
            "branch": branch_name,
        }
    )


@mcp.tool(annotations={"title": "Search Repositories", "readOnlyHint": True, "openWorldHint": True})
def search_repositories(
    query: str,
    limit: int = 10,
) -> list[dict]:
    """Search for GitLab projects/repositories.

    Args:
        query: Search query
        limit: Maximum number of results
    """
    gl = get_client()
    projects = gl.projects.list(search=query, per_page=limit)
    return [
        {
            "id": p.id,
            "path": p.path_with_namespace,
            "name": p.name,
            "description": p.description or "",
            "url": p.web_url,
            "default_branch": p.default_branch,
        }
        for p in projects
    ]


@mcp.tool(annotations={"title": "Get Repository Tree", "readOnlyHint": True, "openWorldHint": True})
def get_repository_tree(
    project_id: str,
    path: str = "",
    ref: str = "HEAD",
    recursive: bool = False,
) -> list[FileSummary]:
    """List files recursively in a repository path.

    Args:
        project_id: Project ID or path
        path: Directory path (empty for root)
        ref: Branch, tag, or commit SHA
        recursive: Whether to list files recursively
    """
    project = get_project(project_id)
    items = project.repository_tree(path=path, ref=ref, recursive=recursive)
    return FileSummary.from_gitlab(items)


@mcp.tool(
    annotations={
        "title": "Push Files",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def push_files(
    project_id: str,
    branch: str,
    commit_message: str,
    files: list[dict],
) -> CommitPushResult:
    """Commit multiple files in a single commit.

    Args:
        project_id: Project ID or path
        branch: Branch to commit to
        commit_message: Commit message
        files: List of files to commit. Each file dict should have:
            - path: File path in repository
            - content: File content
            - action: "create", "update", or "delete"
    """
    project = get_project(project_id)

    # Convert file dicts to GitLab API actions format
    actions = []
    for file_obj in files:
        action = {
            "file_path": file_obj["path"],
            "action": file_obj.get("action", "update"),
        }
        if file_obj.get("action") != "delete":
            action["content"] = file_obj["content"]
        actions.append(action)

    # Create commit with multiple file changes
    commit = project.commits.create(
        {
            "branch": branch,
            "commit_message": commit_message,
            "actions": actions,
        }
    )

    return CommitPushResult.model_validate(
        {
            "commit_sha": commit.id[:8],
            "branch": branch,
            "message": commit.message,
            "files_changed": len(files),
        }
    )


@mcp.tool(annotations={"title": "Get Commit", "readOnlyHint": True, "openWorldHint": True})
def get_commit(
    project_id: str,
    sha: str,
) -> CommitDetails:
    """Get details of a specific commit.

    Args:
        project_id: Project ID or path
        sha: Commit SHA (full or short)
    """
    project = get_project(project_id)
    commit = project.commits.get(sha)

    return CommitDetails.model_validate(
        {
            "sha": commit.id[:8],
            "full_sha": commit.id,
            "message": commit.message,
            "title": commit.title,
            "author": commit.author_name,
            "email": commit.author_email,
            "created": commit.created_at,
            "web_url": commit.web_url,
            "parent_ids": [p[:8] for p in commit.parent_ids],
        }
    )


@mcp.tool(annotations={"title": "Get Commit Diff", "readOnlyHint": True, "openWorldHint": True})
def get_commit_diff(
    project_id: str,
    sha: str,
) -> CommitDiffResult:
    """Get the changes in a specific commit.

    Args:
        project_id: Project ID or path
        sha: Commit SHA (full or short)
    """
    project = get_project(project_id)
    commit = project.commits.get(sha, lazy=True)
    diff = commit.diff()

    files_changed = []
    for change in diff:
        files_changed.append(
            FileChange.model_validate(
                {
                    "path": change["new_path"] or change["old_path"],
                    "status": change["new_file"]
                    and "new"
                    or (change["deleted_file"] and "deleted" or "modified"),
                    "additions": change.get("additions", 0),
                    "deletions": change.get("deletions", 0),
                }
            )
        )

    return CommitDiffResult.model_validate(
        {
            "commit_sha": sha[:8],
            "files_changed": files_changed,
            "total_files": len(files_changed),
        }
    )


@mcp.tool(annotations={"title": "Get Branch Diffs", "readOnlyHint": True, "openWorldHint": True})
def get_branch_diffs(
    project_id: str,
    from_ref: str,
    to_ref: str,
) -> BranchDiffResult:
    """Compare two branches and get the differences.

    Args:
        project_id: Project ID or path
        from_ref: Source branch/tag/commit
        to_ref: Target branch/tag/commit
    """
    project = get_project(project_id)
    comparison = project.repository_compare(from_ref, to_ref)
    comparison_dict = cast(dict, comparison)

    files_changed = []
    for change in comparison_dict["diffs"]:
        files_changed.append(
            FileChange.model_validate(
                {
                    "path": change["new_path"] or change["old_path"],
                    "status": change["new_file"]
                    and "new"
                    or (change["deleted_file"] and "deleted" or "modified"),
                    "additions": change.get("additions", 0),
                    "deletions": change.get("deletions", 0),
                }
            )
        )

    return BranchDiffResult.model_validate(
        {
            "from_ref": from_ref,
            "to_ref": to_ref,
            "commits": len(comparison_dict["commits"]),
            "files_changed": files_changed,
            "total_files": len(files_changed),
        }
    )


@mcp.tool(annotations={"title": "Compare Branches", "readOnlyHint": True, "openWorldHint": True})
def compare_branches(
    project_id: str,
    from_ref: str,
    to_ref: str,
    straight: bool = False,
) -> BranchComparison:
    """Compare two branches, tags, or commits.

    Args:
        project_id: Project ID or path
        from_ref: Source branch/tag/commit
        to_ref: Target branch/tag/commit
        straight: Use straight comparison (no merge base)
    """
    project = get_project(project_id)
    comparison = project.repository_compare(from_ref, to_ref, straight=straight)
    comparison_dict = cast(dict, comparison)

    commits = [
        ComparisonCommit.model_validate(
            {
                "sha": c["id"][:8],
                "message": c["title"],
                "author": c["author_name"],
                "created": c["created_at"],
            }
        )
        for c in comparison_dict["commits"]
    ]

    diffs = [
        FileChange.model_validate(
            {
                "path": d["new_path"] or d["old_path"],
                "status": d["new_file"] and "new" or (d["deleted_file"] and "deleted" or "modified"),
                "additions": 0,  # Not available in comparison
                "deletions": 0,  # Not available in comparison
            }
        )
        for d in comparison_dict["diffs"]
    ]

    return BranchComparison.model_validate(
        {
            "from_ref": from_ref,
            "to_ref": to_ref,
            "commits": commits,
            "diffs": diffs,
            "compare_timeout": comparison_dict.get("compare_timeout", False),
            "compare_same_ref": comparison_dict.get("compare_same_ref", False),
        }
    )


@mcp.tool(annotations={"title": "Get File Blame", "readOnlyHint": True, "openWorldHint": True})
def get_blame(
    project_id: str,
    file_path: str,
    ref: str = "HEAD",
) -> list[dict]:
    """Get blame information for a file.

    Args:
        project_id: Project ID or path
        file_path: Path to the file in the repository
        ref: Branch, tag, or commit SHA (default: HEAD)
    """
    project = get_project(project_id)
    blame = project.files.blame(file_path=file_path, ref=ref)

    return [
        {
            "commit": {
                "sha": entry["commit"]["id"][:8],
                "author": entry["commit"]["author_name"],
                "message": entry["commit"]["message"],
                "created": entry["commit"]["created_at"],
            },
            "lines": entry["lines"],
        }
        for entry in blame
    ]


@mcp.tool(annotations={"title": "Get Contributors", "readOnlyHint": True, "openWorldHint": True})
def get_contributors(
    project_id: str,
    order_by: str | None = None,
    sort: str = "desc",
) -> list[dict]:
    """Get project contributors with commit statistics.

    Args:
        project_id: Project ID or path
        order_by: Order results by field (name, email, commits)
        sort: Sort order (asc or desc)
    """
    project = get_project(project_id)
    kwargs = {"order_by": order_by, "sort": sort} if order_by else {}
    contributors = project.repository_contributors(**kwargs)

    return [
        {
            "name": c["name"],
            "email": c["email"],
            "commits": c["commits"],
            "additions": c["additions"],
            "deletions": c["deletions"],
        }
        for c in contributors
    ]


@mcp.tool(
    annotations={
        "title": "Delete File",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def delete_file(
    project_id: str,
    file_path: str,
    commit_message: str,
    branch: str,
) -> FileDeleteResult:
    """Delete a file from the repository.

    Args:
        project_id: Project ID or path
        file_path: Path to the file to delete
        commit_message: Commit message for the deletion
        branch: Branch to commit to
    """
    project = get_project(project_id)
    project.files.delete(file_path=file_path, branch=branch, commit_message=commit_message)
    return FileDeleteResult.model_validate(
        {
            "deleted": True,
            "path": file_path,
            "branch": branch,
        }
    )
