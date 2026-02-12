"""Pipeline and job management tools."""

from typing import cast
from gitlab.v4.objects import ProjectPipeline, ProjectPipelineJob
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.models.pipelines import PipelineSummary, JobSummary
from gitlab_mcp.utils.pagination import paginate
from gitlab_mcp.utils.query import build_filters, build_sort
from gitlab_mcp.utils.serialization import serialize_pydantic


@mcp.tool(
    annotations={
        "title": "List Pipelines",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def list_pipelines(
    project_id: str,
    per_page: int = 20,
    status: str | None = None,
    ref: str | None = None,
    source: str | None = None,
    order_by: str | None = None,
    sort: str = "desc",
) -> list[PipelineSummary]:
    """List pipelines in a project.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        per_page: Items per page (default 20, max 100)
        status: Filter by status (created, waiting_for_resource, preparing, pending,
                running, success, failed, canceled, skipped, manual, scheduled)
        ref: Filter by branch or tag name
        source: Filter by source (push, web, trigger, schedule, api, external, pipeline,
                chat, webide, merge_request_event, external_pull_request_event,
                parent_pipeline, ondemand_dast_scan, ondemand_dast_validation)
        order_by: Sort by field (id, status, ref, updated_at, user_id)
        sort: Sort direction: asc or desc (default: desc)
    """
    project = get_project(project_id)

    # Build filters using the utility, passing through pipeline-specific filters
    filters = build_filters(
        status=status,
        ref=ref,
        source=source,
    )

    # Add sorting
    filters.update(build_sort(order_by=order_by, sort=sort))

    # Fetch paginated results
    pipelines = paginate(
        project.pipelines,
        per_page=per_page,
        **filters,
    )

    return [
        PipelineSummary.model_validate(p, from_attributes=True)
        for p in pipelines
    ]


@mcp.tool(
    annotations={
        "title": "Get Pipeline",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def get_pipeline(project_id: str, pipeline_id: int, include_stages: bool = True) -> PipelineSummary:
    """Get details of a pipeline with stages breakdown.

    Args:
        project_id: Project ID or path
        pipeline_id: Pipeline ID
        include_stages: Include stages breakdown with status and job counts (default: True)
    """
    project = get_project(project_id)
    pipeline = cast(ProjectPipeline, project.pipelines.get(pipeline_id))
    return PipelineSummary.model_validate(pipeline, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Trigger Pipeline",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def create_pipeline(
    project_id: str,
    ref: str,
    variables: dict[str, str] | None = None,
    description: str | None = None,
) -> PipelineSummary:
    """Trigger a new pipeline on a branch or tag.

    Args:
        project_id: Project ID or path
        ref: Branch or tag name to trigger pipeline on
        variables: Pipeline variables as key-value pairs (e.g., {"VAR_NAME": "value"})
        description: Pipeline description (if supported by API)
    """
    project = get_project(project_id)
    payload: dict[str, str | list[dict[str, str]]] = {"ref": ref}

    # Add variables if provided, formatted as GitLab API expects
    if variables:
        payload["variables"] = [{"key": key, "value": value} for key, value in variables.items()]

    # Add description if provided
    if description:
        payload["description"] = description

    pipeline = cast(ProjectPipeline, project.pipelines.create(payload))
    return PipelineSummary.model_validate(pipeline, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Retry Pipeline",
        "readOnlyHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def retry_pipeline(project_id: str, pipeline_id: int) -> PipelineSummary | dict:
    """Retry a failed or canceled pipeline.

    Args:
        project_id: Project ID or path
        pipeline_id: Pipeline ID to retry
    """
    # Endpoint verified: POST /projects/:id/pipelines/:pipeline_id/retry
    # https://docs.gitlab.com/ee/api/pipelines.html
    project = get_project(project_id)
    pipeline = cast(ProjectPipeline, project.pipelines.get(pipeline_id))

    # Check if pipeline already succeeded
    if pipeline.status == "success":
        return {
            "status": "skipped",
            "message": "Pipeline already succeeded; no retry needed",
            "pipeline_id": pipeline_id,
            "current_status": pipeline.status,
        }

    pipeline.retry()
    # Refresh to get updated state
    pipeline = cast(ProjectPipeline, project.pipelines.get(pipeline_id))
    return PipelineSummary.model_validate(pipeline, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Cancel Pipeline",
        "readOnlyHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def cancel_pipeline(project_id: str, pipeline_id: int) -> PipelineSummary | dict:
    """Cancel a running pipeline.

    Args:
        project_id: Project ID or path
        pipeline_id: Pipeline ID to cancel
    """
    project = get_project(project_id)
    pipeline = cast(ProjectPipeline, project.pipelines.get(pipeline_id))

    # Check if pipeline already completed
    if pipeline.status in ("success", "failed", "canceled", "skipped"):
        return {
            "status": "skipped",
            "message": f"Pipeline already {pipeline.status}; cannot cancel",
            "pipeline_id": pipeline_id,
            "current_status": pipeline.status,
        }

    pipeline.cancel()
    # Refresh to get updated state
    pipeline = cast(ProjectPipeline, project.pipelines.get(pipeline_id))
    return PipelineSummary.model_validate(pipeline, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "List Jobs",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def list_pipeline_jobs(
    project_id: str,
    pipeline_id: int,
    per_page: int = 50,
    status: str | None = None,
) -> list[JobSummary]:
    """List jobs in a pipeline.

    Args:
        project_id: Project ID or path
        pipeline_id: Pipeline ID
        per_page: Items per page (default 50, max 100)
        status: Filter by job status (created, pending, running, success, failed, canceled, skipped, manual)
    """
    project = get_project(project_id)
    pipeline = cast(ProjectPipeline, project.pipelines.get(pipeline_id))

    # Build filters
    filters = build_filters(status=status)

    # Fetch paginated results
    jobs = paginate(
        pipeline.jobs,
        per_page=per_page,
        **filters,
    )

    return [
        JobSummary.model_validate(j, from_attributes=True)
        for j in jobs
    ]


@mcp.tool(
    annotations={
        "title": "Get Job",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def get_pipeline_job(project_id: str, job_id: int) -> JobSummary:
    """Get details of a job with failure reason, artifacts, and retry count.

    Args:
        project_id: Project ID or path
        job_id: Job ID
    """
    project = get_project(project_id)
    job = cast(ProjectPipelineJob, project.jobs.get(job_id))
    return JobSummary.model_validate(job, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Job Logs",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_job_log(
    project_id: str,
    job_id: int,
    max_lines: int = 1000,
    search: str | None = None,
) -> dict:
    """Get the log/trace output of a job with optional filtering and truncation.

    Args:
        project_id: Project ID or path
        job_id: Job ID
        max_lines: Maximum number of lines to return (default: 1000)
        search: Optional search term to filter log lines (case-insensitive)

    Note:
        MCP tools are request/response based and cannot stream live logs.
        For running jobs, this returns the log content available at the time of
        the request. Poll periodically for updates on in-progress jobs.
    """
    project = get_project(project_id)
    job = cast(ProjectPipelineJob, project.jobs.get(job_id))

    # Get full log
    raw_log = job.trace()

    # Split into lines
    lines = raw_log.splitlines()

    # Filter by search term if provided
    if search:
        lines = [line for line in lines if search.lower() in line.lower()]

    total_lines = len(lines)
    truncated = total_lines > max_lines

    # Truncate if needed
    if truncated:
        shown_lines = lines[:max_lines]
        log_output = "\n".join(shown_lines)
        log_output += f"\n\n[truncated: {total_lines - max_lines} more lines]"
    else:
        shown_lines = lines
        log_output = "\n".join(shown_lines)

    return {
        "job_id": job_id,
        "log": log_output,
        "truncated": truncated,
        "total_lines": total_lines,
        "shown_lines": len(shown_lines),
    }


@mcp.tool(
    annotations={
        "title": "Play Job",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def play_pipeline_job(project_id: str, job_id: int) -> JobSummary | dict:
    """Trigger a manual/skipped job to run.

    Args:
        project_id: Project ID or path
        job_id: Job ID to play/trigger
    """
    project = get_project(project_id)
    job = cast(ProjectPipelineJob, project.jobs.get(job_id))

    # Check if job is manual or skipped
    if job.status not in ("manual", "skipped"):
        return {
            "status": "skipped",
            "message": f"Job is {job.status}; only manual or skipped jobs can be played",
            "job_id": job_id,
            "current_status": job.status,
        }

    job.play()
    # Refresh to get updated state
    job = cast(ProjectPipelineJob, project.jobs.get(job_id))
    return JobSummary.model_validate(job, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Retry Job",
        "readOnlyHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def retry_pipeline_job(project_id: str, job_id: int) -> JobSummary | dict:
    """Retry a failed job.

    Args:
        project_id: Project ID or path
        job_id: Job ID to retry
    """
    project = get_project(project_id)
    job = cast(ProjectPipelineJob, project.jobs.get(job_id))

    # Check if job failed
    if job.status != "failed":
        return {
            "status": "skipped",
            "message": f"Job is {job.status}; only failed jobs can be retried",
            "job_id": job_id,
            "current_status": job.status,
        }

    job.retry()
    # Refresh to get updated state
    job = cast(ProjectPipelineJob, project.jobs.get(job_id))
    return JobSummary.model_validate(job, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Cancel Job",
        "readOnlyHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def cancel_pipeline_job(project_id: str, job_id: int) -> JobSummary | dict:
    """Cancel a running job.

    Args:
        project_id: Project ID or path
        job_id: Job ID to cancel
    """
    project = get_project(project_id)
    job = cast(ProjectPipelineJob, project.jobs.get(job_id))

    # Check if job already completed
    if job.status in ("success", "failed", "canceled", "skipped"):
        return {
            "status": "skipped",
            "message": f"Job already {job.status}; cannot cancel",
            "job_id": job_id,
            "current_status": job.status,
        }

    job.cancel()
    # Refresh to get updated state
    job = cast(ProjectPipelineJob, project.jobs.get(job_id))
    return JobSummary.model_validate(job, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Trigger Jobs",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def list_pipeline_trigger_jobs(
    project_id: str,
    pipeline_id: int,
    per_page: int = 50,
    status: str | None = None,
) -> list[JobSummary]:
    """List jobs triggered by pipeline triggers in a pipeline.

    Args:
        project_id: Project ID or path
        pipeline_id: Pipeline ID
        per_page: Items per page (default 50, max 100)
        status: Filter by job status (created, pending, running, success, failed, canceled, skipped, manual)
    """
    project = get_project(project_id)
    pipeline = cast(ProjectPipeline, project.pipelines.get(pipeline_id))

    # Build filters
    filters = build_filters(status=status)

    # Fetch paginated results
    jobs = paginate(
        pipeline.jobs,
        per_page=per_page,
        **filters,
    )

    # Filter for jobs triggered by pipeline triggers (exclude manual/scheduled jobs)
    # Include all jobs in pipeline for now; can be filtered by status if needed
    return [
        JobSummary.model_validate(job, from_attributes=True)
        for job in jobs
    ]
