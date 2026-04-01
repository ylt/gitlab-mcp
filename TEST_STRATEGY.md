# GitLab MCP Test Strategy

## Overview

This document synthesizes the architectural findings into a comprehensive testing strategy for the gitlab-mcp-py project (112+ MCP tools across 18 domains).

**Key constraints:**
- FastMCP framework with `@mcp.tool` decorator auto-registration
- python-gitlab as HTTP client (makes real HTTP calls to GitLab API)
- Singleton patterns for both `_client` and `_config` 
- Pydantic models with `from_gitlab()` classmethod that **rejects plain dicts**, only accepts RESTObject
- 12 existing test files establishing proven patterns
- Full async support with pytest-asyncio

---

## Part 1: Mocking Strategy for python-gitlab

### The Challenge
`get_client()` creates a `python-gitlab.Gitlab` instance that makes real HTTP calls. Tools call `get_project()` which calls `get_client().projects.get(pid)` — a network operation.

### Solution: Patch at Module Level
Use `@patch("gitlab_mcp.client.gitlab.Gitlab")` to mock the Gitlab class before instantiation:

```python
from unittest.mock import MagicMock, patch

@patch("gitlab_mcp.client.gitlab.Gitlab")
def test_my_tool(mock_gitlab_class):
    """Mock python-gitlab's Gitlab class."""
    # Set up the mock Gitlab instance
    mock_client = MagicMock()
    mock_gitlab_class.return_value = mock_client
    
    # Create mock project
    mock_project = MagicMock()
    mock_client.projects.get.return_value = mock_project
    
    # Now get_client() returns our mock
    from gitlab_mcp.client import get_client
    client = get_client()  # Returns our mocked client
    assert client == mock_client
```

### Pattern for Tool Tests
Test tools by:
1. Patching `get_project()` directly (simpler for single-tool tests)
2. Patching `gitlab.Gitlab` at class level (simpler for client initialization tests)

**Preferred approach for tool tests:**
```python
@patch("gitlab_mcp.tools.merge_requests.get_project")
def test_list_merge_requests(mock_get_project):
    """List merge requests with filters."""
    # Create mock project
    mock_project = MagicMock()
    mock_project.mergerequests = MagicMock()
    
    # Create mock MR response
    mock_mr = MagicMock()
    mock_mr.iid = 1
    mock_mr.title = "Test MR"
    # ... set other attributes ...
    
    mock_project.mergerequests.get.return_value = mock_mr
    mock_get_project.return_value = mock_project
    
    # Now call the tool
    result = get_merge_request("myproject", 1)
    
    # Verify the result
    assert result.iid == 1
    assert result.title == "Test MR"
```

### HTTP-Level Testing (Optional)
For integration tests that validate HTTP retry/backoff logic:
```python
@patch("gitlab_mcp.client._create_session_with_retries")
def test_retry_logic(mock_session):
    """Test that retries work for 429/500/502/503/504."""
    # Mock a session with Retry strategy
    mock_retry = MagicMock()
    mock_retry.total = 3
    mock_retry.backoff_factor = 0.5
    mock_retry.status_forcelist = {429, 500, 502, 503, 504}
    mock_session.return_value = (mock_session, mock_retry)
    
    # Verify the retry configuration is applied
    assert mock_retry.backoff_factor == 0.5
```

---

## Part 2: Singleton Pattern Testing

### The Challenge
`_client` and `_config` are global singletons created via `get_client()` and `get_config()`. Tests must reset them between runs to avoid state leakage.

### Solution: Autouse Fixtures for Isolation

**From test_client.py (proven pattern):**
```python
import pytest
from gitlab_mcp.client import _client as _client_module
from gitlab_mcp.config import _config as _config_module

@pytest.fixture(autouse=True)
def reset_client():
    """Reset global _client singleton between tests."""
    _client_module._client = None
    yield
    _client_module._client = None

@pytest.fixture(autouse=True)
def reset_config():
    """Reset global _config singleton between tests."""
    _config_module._config = None
    yield
    _config_module._config = None
```

**Usage:**
- Fixtures are `autouse=True` — they run before and after every test automatically
- Each test starts with clean singletons
- No explicit fixture injection needed in test functions
- Isolation is guaranteed

### Why This Works
1. `yield` divides the fixture into setup (before) and teardown (after)
2. `autouse=True` means every test gets this fixture automatically
3. Before each test: `_client = None` and `_config = None`
4. Test runs with fresh instances
5. After each test: cleanup clears the instance again

---

## Part 3: Fixture Design Patterns

### Environment Variable Isolation (Config Testing)
**From test_config.py (proven pattern):**
```python
def test_personal_access_token(monkeypatch):
    """Test personal access token loading from env."""
    monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-pat-token")
    config = Config.from_env()
    assert config.token == "test-pat-token"

def test_default_values(monkeypatch):
    """Test defaults when no env vars are set."""
    # Clear all GITLAB_* env vars
    for key in list(os.environ.keys()):
        if key.startswith("GITLAB_"):
            monkeypatch.delenv(key, raising=False)
    
    config = Config.from_env()
    assert config.gitlab_url == "https://gitlab.com"
    assert config.token == ""
    assert config.oauth_token is None
```

**Key points:**
- `monkeypatch` is a built-in pytest fixture for temporary environment changes
- Changes are automatically reverted after the test
- No manual cleanup needed
- Use `monkeypatch.delenv(key, raising=False)` to safely clear variables

### Mock Object Fixtures (Tool Testing)
**From test_merge_requests.py (proven pattern):**
```python
@pytest.fixture
def mock_project():
    """Create a mock GitLab project."""
    project = MagicMock()
    project.mergerequests = MagicMock()
    return project

@pytest.fixture
def mock_mr():
    """Create a mock merge request object."""
    mr = MagicMock()
    mr.iid = 1
    mr.title = "Test MR"
    mr.description = "This is a test MR"
    mr.state = "opened"
    mr.author = {"username": "testuser"}
    mr.assignees = []
    mr.reviewers = []
    mr.labels = ["feature"]
    mr.web_url = "https://gitlab.com/project/-/merge_requests/1"
    mr.created_at = "2024-01-15T10:00:00Z"
    mr.updated_at = "2024-01-15T10:05:00Z"
    mr.source_branch = "feature-branch"
    mr.target_branch = "main"
    mr.merge_status = "can_be_merged"
    mr.draft = False
    mr.work_in_progress = False
    mr.has_conflicts = False
    mr.blocking_discussions_resolved = True
    mr.upvotes = 2
    mr.downvotes = 0
    mr.head_pipeline = None
    mr.detailed_merge_status = None
    mr.approvals_required = 0
    mr.approvals_left = 0
    
    # Mock the approvals.get() method
    mock_approvals = MagicMock()
    mock_approvals.get.return_value = MagicMock(approvals_required=0, approvals_left=0)
    mr.approvals = mock_approvals
    return mr
```

**Key points:**
- Create comprehensive fixtures with all attributes tools may access
- Include nested mocks for complex objects (e.g., `mr.approvals`)
- Fixtures are reusable across multiple tests
- Use specific attribute values (not defaults) so assertions are meaningful

---

## Part 4: Model Transformation Testing

### The Challenge
`BaseGitLabModel.from_gitlab()` has strict requirements:
- **Accepts:** Single `RESTObject` or `list[RESTObject]` from python-gitlab
- **Rejects:** Plain dicts (raises `TypeError`)
- **Only method:** `from_gitlab()` for API objects; `model_validate()` for dicts

### Strategy: Test Both Valid and Invalid Cases

```python
from gitlab.base import RESTObject
from gitlab_mcp.models import IssueSummary

def test_from_gitlab_with_rest_object(mock_issue):
    """from_gitlab() accepts RESTObject."""
    # mock_issue is a MagicMock that looks like RESTObject
    result = IssueSummary.from_gitlab(mock_issue)
    assert result.iid == 1

def test_from_gitlab_with_list(mock_issue):
    """from_gitlab() accepts list of RESTObjects."""
    results = IssueSummary.from_gitlab([mock_issue, mock_issue])
    assert len(results) == 2

def test_from_gitlab_rejects_dict():
    """from_gitlab() rejects plain dicts."""
    with pytest.raises(TypeError, match="expects a GitLab RESTObject"):
        IssueSummary.from_gitlab({"iid": 1})

def test_model_validate_accepts_dict():
    """model_validate() accepts dicts."""
    result = IssueSummary.model_validate({"iid": 1})
    assert result.iid == 1
```

### Testing Validators
Test the field validators in `BaseGitLabModel`:

```python
def test_empty_strings_convert_to_none():
    """Empty strings are converted to None by validator."""
    result = IssueSummary.model_validate({
        "iid": 1,
        "description": ""  # Empty string
    })
    assert result.description is None

def test_relative_time_formatting():
    """Relative time fields format correctly."""
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    result = IssueSummary.model_validate({
        "iid": 1,
        "created_at": now.isoformat()
    })
    # RelativeTime serializer should format as "just now" or similar
    assert "ago" in result.created_at or "just now" in result.created_at
```

---

## Part 5: Tool Testing Strategy (112+ Tools, 18 Domains)

### Overview of Domains
```
18 tool modules: graphql, uploads, draft_notes, iterations, labels, 
namespaces, milestones, releases, users, projects, wiki, issues, 
realtime, pipelines, discussions, merge_requests, repository, __init__
```

### Generic Tool Test Pattern
All tools follow similar pattern: `get_project()` → API call → model transformation → return.

**Template for any domain:**
```python
import pytest
from unittest.mock import MagicMock, patch
from gitlab_mcp.server import mcp

def get_tool_function(tool_name: str):
    """Extract tool function from MCP server."""
    for tool in mcp._tool_manager._tools.values():
        if tool.name == tool_name:
            return tool.fn
    raise ValueError(f"Tool {tool_name} not found")

@pytest.fixture
def mock_project():
    """Mock GitLab project."""
    project = MagicMock()
    return project

class TestMyDomainTools:
    """Test tools in my_domain module."""
    
    @patch("gitlab_mcp.tools.my_domain.get_project")
    def test_list_things(self, mock_get_project, mock_project):
        """Test list_things tool."""
        mock_get_project.return_value = mock_project
        mock_project.things = MagicMock()
        mock_project.things.list.return_value = [
            MagicMock(id=1, name="Thing 1"),
            MagicMock(id=2, name="Thing 2"),
        ]
        
        # Extract and call the tool
        list_things = get_tool_function("list_things")
        result = list_things("myproject")
        
        # Verify
        assert len(result) == 2
        assert result[0].id == 1
        
        # Verify the API call was made with correct params
        mock_project.things.list.assert_called_once()
    
    @patch("gitlab_mcp.tools.my_domain.get_project")
    def test_get_thing(self, mock_get_project, mock_project):
        """Test get_thing tool."""
        mock_get_project.return_value = mock_project
        mock_thing = MagicMock(id=1, name="Thing 1")
        mock_project.things.get.return_value = mock_thing
        
        get_thing = get_tool_function("get_thing")
        result = get_thing("myproject", 1)
        
        assert result.id == 1
        assert result.name == "Thing 1"
        mock_project.things.get.assert_called_once_with(1)
    
    @patch("gitlab_mcp.tools.my_domain.get_project")
    def test_create_thing(self, mock_get_project, mock_project):
        """Test create_thing tool."""
        mock_get_project.return_value = mock_project
        mock_thing = MagicMock(id=1, name="New Thing")
        mock_project.things.create.return_value = mock_thing
        
        create_thing = get_tool_function("create_thing")
        result = create_thing("myproject", name="New Thing")
        
        assert result.id == 1
        mock_project.things.create.assert_called_once()
        # Verify the data passed to create
        call_args = mock_project.things.create.call_args[0][0]
        assert call_args["name"] == "New Thing"
```

### Testing Filters and Parameters
Most tools support filters (state, author_username, labels, etc.):

```python
@patch("gitlab_mcp.tools.merge_requests.paginate")
@patch("gitlab_mcp.tools.merge_requests.get_project")
def test_list_with_filters(mock_get_project, mock_paginate, mock_project):
    """Test filtering parameters are passed correctly."""
    mock_get_project.return_value = mock_project
    mock_paginate.return_value = []
    
    list_merge_requests = get_tool_function("list_merge_requests")
    list_merge_requests(
        "myproject",
        state="closed",
        author_username="alice",
        labels="bug,urgent"
    )
    
    # Verify all filters were passed to paginate
    call_args = mock_paginate.call_args[1]
    assert call_args["state"] == "closed"
    assert call_args["author_username"] == "alice"
    assert call_args["labels"] == "bug,urgent"
```

### Testing Sorting and Pagination
```python
@patch("gitlab_mcp.tools.issues.paginate")
@patch("gitlab_mcp.tools.issues.get_project")
def test_list_with_sorting(mock_get_project, mock_paginate, mock_project):
    """Test sort parameters."""
    mock_get_project.return_value = mock_project
    mock_paginate.return_value = []
    
    list_issues = get_tool_function("list_issues")
    list_issues("myproject", order_by="updated_at", sort="asc", per_page=50)
    
    call_args = mock_paginate.call_args[1]
    assert call_args["order_by"] == "updated_at"
    assert call_args["sort"] == "asc"
    assert call_args["per_page"] == 50
```

### Testing Read-Only Mode
Tools respect `GITLAB_READ_ONLY_MODE` flag. Test this:

```python
@patch.dict(os.environ, {"GITLAB_READ_ONLY_MODE": "true"})
@patch("gitlab_mcp.tools.merge_requests.get_project")
def test_create_mr_in_readonly_mode(mock_get_project):
    """Test that create tool respects read-only mode."""
    # get_config() should have read_only=True
    from gitlab_mcp.config import get_config
    config = get_config()
    assert config.read_only is True
    
    create_merge_request = get_tool_function("create_merge_request")
    with pytest.raises(Exception, match="read-only"):
        create_merge_request("myproject", "feature", "main", "Title")
```

---

## Part 6: Integration Testing Approach

### Strategy: Test Multiple Layers Together
Instead of mocking everything, some tests should verify integration between:
- Config loading
- Client initialization with config
- Tool execution with model transformation

```python
class TestIntegration:
    """Integration tests across multiple layers."""
    
    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_end_to_end_get_issue(self, mock_gitlab_class):
        """End-to-end: config → client → tool → model."""
        # Set up environment
        os.environ["GITLAB_PERSONAL_ACCESS_TOKEN"] = "test-token"
        os.environ["GITLAB_API_URL"] = "https://gitlab.example.com"
        
        # Mock the Gitlab client
        mock_client = MagicMock()
        mock_gitlab_class.return_value = mock_client
        
        # Mock the project
        mock_project = MagicMock()
        mock_client.projects.get.return_value = mock_project
        
        # Mock the issue
        mock_issue = MagicMock()
        mock_issue.iid = 1
        mock_issue.title = "Test Issue"
        mock_issue.created_at = "2024-01-15T10:00:00Z"
        mock_project.issues.get.return_value = mock_issue
        
        # Execute the tool (this goes through full stack)
        get_issue = get_tool_function("get_issue")
        result = get_issue("myproject", 1)
        
        # Verify result is properly transformed
        assert result.iid == 1
        assert result.title == "Test Issue"
        assert "ago" in result.created_at or "just now" in result.created_at
        
        # Verify correct API calls were made
        mock_client.projects.get.assert_called_once_with("myproject")
        mock_project.issues.get.assert_called_once_with(1)
```

### Testing Error Handling
```python
@patch("gitlab_mcp.tools.issues.get_project")
def test_issue_not_found(mock_get_project, mock_project):
    """Test handling of 404 errors."""
    mock_get_project.return_value = mock_project
    mock_project.issues.get.side_effect = Exception("404 Not Found")
    
    get_issue = get_tool_function("get_issue")
    with pytest.raises(Exception, match="404"):
        get_issue("myproject", 999)
```

---

## Part 7: Test File Organization

### Current Structure (Proven)
```
tests/
├── test_config.py           # Config loading, env vars
├── test_client.py           # Client init, auth, singletons
├── test_issues.py           # Issues domain tools
├── test_merge_requests.py   # MR domain tools
├── test_namespaces.py       # Namespace domain tools
├── test_pipelines.py        # Pipeline domain tools
├── utils/
│   ├── test_query.py        # Helper function tests
│   ├── test_validation.py   # Validation logic tests
│   ├── test_cache.py        # Caching logic tests
│   ├── test_pagination.py   # Pagination logic tests
└── models/
    ├── test_pipelines.py    # Pipeline model tests
    └── test_projects.py     # Project model tests
```

### Recommended Additions
Add test modules for remaining 11 domains:
- `test_graphql.py`
- `test_uploads.py`
- `test_draft_notes.py`
- `test_iterations.py`
- `test_labels.py`
- `test_milestones.py`
- `test_releases.py`
- `test_users.py`
- `test_projects.py`
- `test_wiki.py`
- `test_realtime.py`
- `test_discussions.py`
- `test_repository.py`

### conftest.py (Shared Fixtures)
Create `tests/conftest.py` to centralize common fixtures:

```python
import pytest
from unittest.mock import MagicMock
from gitlab_mcp.client import _client as _client_module
from gitlab_mcp.config import _config as _config_module

@pytest.fixture(autouse=True)
def reset_client():
    """Reset global _client singleton between tests."""
    _client_module._client = None
    yield
    _client_module._client = None

@pytest.fixture(autouse=True)
def reset_config():
    """Reset global _config singleton between tests."""
    _config_module._config = None
    yield
    _config_module._config = None

@pytest.fixture
def mock_project():
    """Reusable mock project fixture."""
    project = MagicMock()
    return project

def get_tool_function(tool_name: str):
    """Extract tool function from MCP server."""
    from gitlab_mcp.server import mcp
    for tool in mcp._tool_manager._tools.values():
        if tool.name == tool_name:
            return tool.fn
    raise ValueError(f"Tool {tool_name} not found")

@pytest.fixture
def get_tool_function_fixture():
    """Provide get_tool_function as a fixture."""
    return get_tool_function
```

---

## Part 8: Running Tests

### Commands
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/gitlab_mcp --cov-report=html

# Run specific test file
uv run pytest tests/test_merge_requests.py

# Run specific test class
uv run pytest tests/test_merge_requests.py::TestListMergeRequests

# Run specific test
uv run pytest tests/test_merge_requests.py::TestListMergeRequests::test_list_merge_requests_default_params

# Run with verbose output
uv run pytest -vv

# Run and show print statements
uv run pytest -s
```

### Configuration
The `pyproject.toml` already specifies:
- `pytest>=9.0.2`
- `pytest-asyncio>=1.3.0`
- `basedpyright` type checking

No additional pytest.ini or setup.cfg needed — pytest discovers tests automatically via `tests/test_*.py` pattern.

---

## Part 9: Coverage Goals

| Layer | Target | Approach |
|-------|--------|----------|
| Config | 100% | Test all env var combinations, defaults, parsing |
| Client | 95% | Test auth priority, singleton, retry logic, pooling |
| Models | 100% | Test from_gitlab() with/without RESTObject, validators, serializers |
| Tools | 80% | Test all 112+ tools with typical filters/parameters, error cases |
| Utilities | 100% | Test helpers (paginate, build_filters, build_sort, relative_time) |

---

## Summary: The Testing Pyramid

```
┌─────────────────────────────────────┐
│   Integration Tests (End-to-End)    │  Few, slow, high confidence
│  config → client → tool → model     │
├─────────────────────────────────────┤
│  Unit Tests (Tool/Model Tests)      │  Many, fast, mocked APIs
│  Test 112+ tools with MagicMock     │
├─────────────────────────────────────┤
│  Unit Tests (Config/Client)         │  Foundational layer tests
│  Test singletons, env vars, auth    │
└─────────────────────────────────────┘
```

**Key Insight:** The singleton pattern (config + client) is the foundation. Test it thoroughly first, then leverage those patterns for 112+ tool tests using mocks.

