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
    }

    def visit_functiondef(self, node: nodes.FunctionDef) -> None:
        """Check function definitions for MCP tool violations."""
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


def register(linter):
    """Register the checker with pylint."""
    linter.register_checker(MCPToolChecker(linter))
