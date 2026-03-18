"""Pylint checker for MCP tool conventions."""

from astroid import nodes
from pylint.checkers import BaseChecker


class MCPToolChecker(BaseChecker):
    """Check that MCP tools follow architectural conventions."""

    name = "mcp-tool-checker"
    msgs = {
        "W9001": (
            "MCP tool '%s' returns dict instead of Pydantic model",
            "mcp-dict-return",
            "MCP tools must ONLY return Pydantic models, NEVER dicts. "
            "Success: return Model.from_gitlab(obj). "
            "Failure: RAISE ValueError('reason') or RuntimeError('reason'). "
            "Do not return error dicts - raise exceptions instead!",
        ),
        "W9002": (
            "MCP tool '%s' contains nested function '%s'",
            "mcp-nested-function",
            "MCP tools should be thin controllers. "
            "Move helper functions to utils/ or add logic to Pydantic models.",
        ),
        "W9003": (
            "MCP tool '%s' manually constructs model instead of using from_gitlab()",
            "mcp-manual-construction",
            "Use Model.from_gitlab(obj) instead of manual field mapping. "
            "Keep controllers thin - models handle transformation.",
        ),
        "W9004": (
            "MCP tool '%s' uses list comprehension with from_gitlab()",
            "mcp-manual-list-comprehension",
            "from_gitlab() accepts lists - use Model.from_gitlab(items) instead of "
            "[Model.from_gitlab(item) for item in items]",
        ),
        "W9005": (
            "Field serializer '%s' just delegates to function - use type alias instead",
            "simple-field-serializer",
            "Replace simple @field_serializer with type alias. "
            "Example: Use RelativeTime type alias instead of @field_serializer that calls relative_time()",
        ),
    }

    def visit_functiondef(self, node: nodes.FunctionDef) -> None:
        """Check function definitions for MCP tool violations."""
        # Check for simple field serializers and validators in models
        if self._has_field_serializer_decorator(node) and self._is_simple_delegation(node):
            self.add_message("simple-field-serializer", node=node, args=(node.name,))

        # Check for @computed_field that just calls relative_time()
        if self._has_computed_field_decorator(node) and self._is_relative_time_delegation(node):
            self.add_message("simple-field-serializer", node=node, args=(node.name,))

        # Check for @computed_field that just returns another field
        if self._has_computed_field_decorator(node) and self._is_field_alias(node):
            self.add_message("simple-field-serializer", node=node, args=(node.name,))

        # Check for @field_validator that just calls safe_str()
        if self._has_field_validator_decorator(node) and self._is_safe_str_delegation(node):
            self.add_message("simple-field-serializer", node=node, args=(node.name,))

        # Check for @field_validator that loops and calls from_gitlab()
        if self._has_field_validator_decorator(node) and self._is_list_from_gitlab_delegation(node):
            self.add_message("simple-field-serializer", node=node, args=(node.name,))

        # Check if function has @mcp.tool decorator
        if not self._has_mcp_tool_decorator(node):
            return

        # Check if return type is dict or list[dict] or union with dict
        if self._returns_dict(node):
            self.add_message("mcp-dict-return", node=node, args=(node.name,))

        # Check for nested function definitions
        for child in node.body:
            if isinstance(child, nodes.FunctionDef):
                self.add_message(
                    "mcp-nested-function",
                    node=child,
                    args=(node.name, child.name)
                )

        # Check for manual model construction
        if self._has_manual_construction(node):
            self.add_message("mcp-manual-construction", node=node, args=(node.name,))

        # Check for dict literals in return statements
        if self._returns_dict_literal(node):
            self.add_message("mcp-dict-return", node=node, args=(node.name,))

        # Check for list comprehensions with from_gitlab
        if self._has_from_gitlab_list_comprehension(node):
            self.add_message("mcp-manual-list-comprehension", node=node, args=(node.name,))

    def _has_mcp_tool_decorator(self, node: nodes.FunctionDef) -> bool:
        """Check if function has @mcp.tool decorator."""
        if not node.decorators:
            return False

        for decorator in node.decorators.nodes:
            # Handle @mcp.tool or @mcp.tool(...)
            if isinstance(decorator, nodes.Attribute):
                if decorator.attrname == "tool":
                    return True
            elif isinstance(decorator, nodes.Call):
                if isinstance(decorator.func, nodes.Attribute):
                    if decorator.func.attrname == "tool":
                        return True
        return False

    def _returns_dict(self, node: nodes.FunctionDef) -> bool:
        """Check if function returns dict or list[dict] or union with dict."""
        if not node.returns:
            return False

        return_annotation = node.returns

        # Check for union types (A | B)
        if isinstance(return_annotation, nodes.BinOp):
            # Check both sides of the union
            if self._contains_dict(return_annotation.left) or self._contains_dict(return_annotation.right):
                return True

        # Check for dict[...] or dict
        if isinstance(return_annotation, nodes.Subscript):
            if isinstance(return_annotation.value, nodes.Name):
                if return_annotation.value.name == "dict":
                    return True
                # Check for list[dict[...]]
                if return_annotation.value.name == "list":
                    # Check if subscript contains dict
                    if isinstance(return_annotation.slice, nodes.Subscript):
                        if isinstance(return_annotation.slice.value, nodes.Name):
                            if return_annotation.slice.value.name == "dict":
                                return True

        # Check for bare dict
        if isinstance(return_annotation, nodes.Name):
            if return_annotation.name == "dict":
                return True

        return False

    def _contains_dict(self, node) -> bool:
        """Check if a node is or contains dict."""
        if isinstance(node, nodes.Name):
            return node.name == "dict"
        if isinstance(node, nodes.Subscript):
            if isinstance(node.value, nodes.Name):
                return node.value.name == "dict"
        return False

    def _has_manual_construction(self, node: nodes.FunctionDef) -> bool:
        """Check if function manually constructs models with field mapping."""
        for child in node.body:
            if isinstance(child, nodes.Return):
                if isinstance(child.value, nodes.Call):
                    # Check if it's a model constructor with keyword arguments
                    if child.value.keywords:
                        # If there are multiple keyword args, it's likely manual construction
                        if len(child.value.keywords) > 1:
                            return True
        return False

    def _returns_dict_literal(self, node: nodes.FunctionDef) -> bool:
        """Check if function returns dict literals anywhere in its body."""
        for child in node.body:
            if self._check_return_dict(child):
                return True
        return False

    def _check_return_dict(self, node) -> bool:
        """Recursively check if a node or its children return dict literals."""
        if isinstance(node, nodes.Return):
            if isinstance(node.value, nodes.Dict):
                return True
        # Check if statements (both branches)
        if isinstance(node, nodes.If):
            for child in node.body:
                if self._check_return_dict(child):
                    return True
            for child in node.orelse:
                if self._check_return_dict(child):
                    return True
        return False

    def _has_from_gitlab_list_comprehension(self, node: nodes.FunctionDef) -> bool:
        """Check if function uses list comprehension with from_gitlab."""
        for child in node.body:
            if isinstance(child, nodes.Return) and child.value:
                if self._is_from_gitlab_listcomp(child.value):
                    return True
        return False

    def _is_from_gitlab_listcomp(self, node) -> bool:
        """Check if node is a list comprehension calling from_gitlab."""
        if isinstance(node, nodes.ListComp):
            # Check if the element expression calls from_gitlab
            if isinstance(node.elt, nodes.Call):
                if isinstance(node.elt.func, nodes.Attribute):
                    if node.elt.func.attrname == "from_gitlab":
                        return True
        return False

    def _has_field_serializer_decorator(self, node: nodes.FunctionDef) -> bool:
        """Check if function has @field_serializer decorator."""
        if not node.decorators:
            return False

        for decorator in node.decorators.nodes:
            # Handle @field_serializer(...) call
            if isinstance(decorator, nodes.Call):
                if isinstance(decorator.func, nodes.Name):
                    if decorator.func.name == "field_serializer":
                        return True
        return False

    def _is_simple_delegation(self, node: nodes.FunctionDef) -> bool:
        """Check if method body is just a simple function call delegation.

        Matches patterns like:
        - return func(v)
        - return func(v) if v else None
        """
        if len(node.body) != 1:
            return False

        stmt = node.body[0]
        if not isinstance(stmt, nodes.Return):
            return False

        # Pattern: return func(v) if v else None
        if isinstance(stmt.value, nodes.IfExp):
            # Check if test is just a name (the parameter)
            if isinstance(stmt.value.test, nodes.Name):
                # Check if body is a simple function call
                if isinstance(stmt.value.body, nodes.Call):
                    return True

        # Pattern: return func(v)
        if isinstance(stmt.value, nodes.Call):
            # Check if it's a simple function call with one argument
            if len(stmt.value.args) == 1:
                return True

        return False

    def _has_computed_field_decorator(self, node: nodes.FunctionDef) -> bool:
        """Check if function has @computed_field decorator."""
        if not node.decorators:
            return False

        for decorator in node.decorators.nodes:
            # Handle @computed_field
            if isinstance(decorator, nodes.Name):
                if decorator.name == "computed_field":
                    return True
            # Handle @computed_field(...)
            elif isinstance(decorator, nodes.Call):
                if isinstance(decorator.func, nodes.Name):
                    if decorator.func.name == "computed_field":
                        return True
        return False

    def _has_field_validator_decorator(self, node: nodes.FunctionDef) -> bool:
        """Check if function has @field_validator decorator."""
        if not node.decorators:
            return False

        for decorator in node.decorators.nodes:
            # Handle @field_validator(...) call
            if isinstance(decorator, nodes.Call):
                if isinstance(decorator.func, nodes.Name):
                    if decorator.func.name == "field_validator":
                        return True
        return False

    def _is_relative_time_delegation(self, node: nodes.FunctionDef) -> bool:
        """Check if @computed_field just calls relative_time().

        Matches pattern like:
        - return relative_time(self.field) if self.field else None
        """
        if len(node.body) != 1:
            return False

        stmt = node.body[0]
        if not isinstance(stmt, nodes.Return):
            return False

        # Pattern: return relative_time(...) if ... else None
        if isinstance(stmt.value, nodes.IfExp):
            if isinstance(stmt.value.body, nodes.Call):
                if isinstance(stmt.value.body.func, nodes.Name):
                    if stmt.value.body.func.name == "relative_time":
                        return True

        # Pattern: return relative_time(...)
        if isinstance(stmt.value, nodes.Call):
            if isinstance(stmt.value.func, nodes.Name):
                if stmt.value.func.name == "relative_time":
                    return True

        return False

    def _is_field_alias(self, node: nodes.FunctionDef) -> bool:
        """Check if @computed_field just returns another field.

        Matches pattern like:
        - return self.other_field
        """
        if len(node.body) != 1:
            return False

        stmt = node.body[0]
        if not isinstance(stmt, nodes.Return):
            return False

        # Pattern: return self.field_name
        if isinstance(stmt.value, nodes.Attribute):
            if isinstance(stmt.value.expr, nodes.Name):
                if stmt.value.expr.name == "self":
                    return True

        return False

    def _is_safe_str_delegation(self, node: nodes.FunctionDef) -> bool:
        """Check if @field_validator just calls safe_str().

        Matches pattern like:
        - return safe_str(v)
        """
        if len(node.body) != 1:
            return False

        stmt = node.body[0]
        if not isinstance(stmt, nodes.Return):
            return False

        # Pattern: return safe_str(v)
        if isinstance(stmt.value, nodes.Call):
            if isinstance(stmt.value.func, nodes.Name):
                if stmt.value.func.name == "safe_str":
                    # Check if it has exactly one argument
                    if len(stmt.value.args) == 1:
                        return True

        return False

    def _is_list_from_gitlab_delegation(self, node: nodes.FunctionDef) -> bool:
        """Check if @field_validator loops and calls from_gitlab() on each item.

        Matches pattern like:
        - if not v:
        -     return []
        - return [SomeModel.from_gitlab(item) for item in v]

        This is unnecessary because Pydantic's list[SomeModel] type annotation
        automatically validates list elements.
        """
        # Should have exactly 3 statements: if-check, return empty, return list comprehension
        if len(node.body) != 2:
            return False

        # First statement should be: if not v: return []
        first_stmt = node.body[0]
        if not isinstance(first_stmt, nodes.If):
            return False

        # Check if body has return statement with empty list
        if len(first_stmt.body) != 1 or not isinstance(first_stmt.body[0], nodes.Return):
            return False

        return_stmt = first_stmt.body[0]
        if not isinstance(return_stmt.value, nodes.List):
            return False

        if len(return_stmt.value.elts) != 0:
            return False

        # Second statement should be: return [SomeModel.from_gitlab(item) for item in v]
        second_stmt = node.body[1]
        if not isinstance(second_stmt, nodes.Return):
            return False

        # Check if it's a list comprehension calling from_gitlab
        if self._is_from_gitlab_listcomp(second_stmt.value):
            return True

        return False


def register(linter):
    """Register the checker with pylint."""
    linter.register_checker(MCPToolChecker(linter))
