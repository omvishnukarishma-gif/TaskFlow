"""
inspect_sort.py — Verify no Python built-in sorted() or .sort() calls
exist as actual function invocations in the algorithm modules or task router.

Uses the AST to walk only real Call nodes — ignores comments and docstrings.
"""
import ast
import sys

files = [
    "backend/algorithms/sorting.py",
    "backend/algorithms/searching.py",
    "backend/routers/tasks.py",
    "backend/routers/users.py",
    "backend/routers/projects.py",
    "backend/main.py",
    "check_algorithms.py",
]

found_any = False


class ForbiddenSortVisitor(ast.NodeVisitor):
    """Walk AST call nodes to find sorted() or .sort() invocations."""
    def __init__(self, path):
        self.path = path
        self.violations = []

    def visit_Call(self, node):
        # sorted(...)  — a bare Name call
        if isinstance(node.func, ast.Name) and node.func.id == "sorted":
            self.violations.append(
                f"  sorted() call at line {node.lineno}"
            )
        # something.sort(...)  — an Attribute call
        if isinstance(node.func, ast.Attribute) and node.func.attr == "sort":
            self.violations.append(
                f"  .sort() call at line {node.lineno}"
            )
        self.generic_visit(node)


for path in files:
    with open(path, encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        print(f"SYNTAX ERROR in {path}: {e}")
        found_any = True
        continue

    visitor = ForbiddenSortVisitor(path)
    visitor.visit(tree)

    if visitor.violations:
        print(f"VIOLATION  {path}:")
        for v in visitor.violations:
            print(v)
        found_any = True
    else:
        print(f"CLEAN:  {path}")

print()
if not found_any:
    print("PASS: No sorted() or .sort() calls found in any file.")
    sys.exit(0)
else:
    print("FAIL: Built-in sort usage detected — see above.")
    sys.exit(1)
