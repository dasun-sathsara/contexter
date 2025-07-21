from pathlib import Path
import pathspec


def load_gitignore_patterns(start_path):
    """Load all .gitignore patterns from start_path up to root"""
    patterns = []
    current = Path(start_path).resolve()

    # Traverse up to root
    for parent in [current] + list(current.parents):
        gitignore_file = parent / ".gitignore"
        if gitignore_file.is_file():
            with gitignore_file.open("r") as f:
                lines = f.readlines()
                patterns.extend(
                    [
                        line.strip()
                        for line in lines
                        if line.strip() and not line.strip().startswith("#")
                    ]
                )

    if patterns:
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    else:
        return None


def is_ignored(path, specs):
    """Check if path is ignored by any PathSpec"""
    if not specs:
        return False
    # Accept list of PathSpec or single
    if isinstance(specs, list):
        return any(spec.match_file(path) for spec in specs if spec)
    else:
        return specs.match_file(path)
