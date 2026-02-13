# PyCharm Type Stub Configuration

PyCharm is showing TypeVar errors because it's not picking up our custom stubs.

## Solution 1: Mark stubs directory
1. In PyCharm, right-click on the `stubs/` directory
2. Select "Mark Directory as" → "Sources Root"
3. Restart PyCharm or "Invalidate Caches / Restart"

## Solution 2: Add to Python path
1. Open PyCharm Settings (Cmd+, on Mac)
2. Go to Project → Project Structure
3. Add `stubs/` directory as a "Source" folder

## Solution 3: pyproject.toml configuration
Add this to pyproject.toml (already added):
```toml
[tool.pyright]
stubPath = "stubs"
```

## Verify
After configuration, TypeVar errors should disappear:
- `label.unsubscribe()` will be recognized
- `issue.time_stats()` will be recognized
- All GitLab object attributes will work

If still seeing errors, try: File → Invalidate Caches / Restart
