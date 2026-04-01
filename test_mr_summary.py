#!/usr/bin/env python3
"""Test MergeRequestSummary optimizations."""

from gitlab_mcp.models.merge_requests import MergeRequestSummary
from gitlab_mcp.models.misc import UserRef

# Test 1: Description truncation
long_desc = "A" * 300
mr_data = {
    "iid": 123,
    "title": "Test MR",
    "description": long_desc,
    "state": "opened",
    "author": {"id": 1, "username": "test", "name": "Test User"},
    "source_branch": "feature",
    "target_branch": "main",
    "created_at": "2026-02-10T12:00:00Z",
    "updated_at": "2026-02-13T00:00:00Z",
}

mr = MergeRequestSummary.model_validate(mr_data)
print(f"✓ Description truncated: {len(mr.description)} chars (was 300)")
assert len(mr.description) == 200  # 197 + "..."
assert mr.description.endswith("...")

# Test 2: No web_url field
mr_dict = mr.model_dump()
print(f"✓ web_url removed: 'url' in output = {('url' in mr_dict)}")
assert "url" not in mr_dict
assert "web_url" not in mr_dict

# Test 3: Approvals condensed (no approvals case)
print(f"✓ No approvals needed: approvals = {mr.approvals}")
assert mr.approvals is None

# Test 4: Approvals condensed (with approvals)
# Create a mock object with approvals attribute
class MockApprovals:
    def get(self):
        class ApprovalObj:
            approvals_required = 2
            approvals_left = 1
        return ApprovalObj()

class MockMRData:
    def __init__(self, base_data):
        for k, v in base_data.items():
            setattr(self, k, v)
        self.approvals = MockApprovals()

mock_data = MockMRData(mr_data)
mr_with_approvals = MergeRequestSummary.model_validate(mock_data, from_attributes=True)
print(f"✓ Approvals condensed: approvals = {mr_with_approvals.approvals}")
assert mr_with_approvals.approvals == "1/2"

# Test 5: No summary field
print(f"✓ summary removed: 'summary' in output = {('summary' in mr_dict)}")
assert "summary" not in mr_dict

# Test 6: No redundant status fields
print(f"✓ Status fields private: merge_status in output = {('merge_status' in mr_dict)}")
assert "merge_status" not in mr_dict
assert "detailed_merge_status" not in mr_dict
assert "_merge_status" not in mr_dict  # Private fields excluded
assert "_detailed_merge_status" not in mr_dict

# Test 7: Blockers still work with private fields
mr_with_blockers = MergeRequestSummary.model_validate({
    **mr_data,
    "_approvals_left": 2,
    "_detailed_merge_status": "draft",
})
print(f"✓ Blockers computed correctly: {mr_with_blockers.blockers}")
assert "2 approvals needed" in mr_with_blockers.blockers
assert "MR is draft" in mr_with_blockers.blockers

print("\n✅ All optimizations working correctly!")
print("\nSample output:")
import json
print(json.dumps(mr_dict, indent=2))
