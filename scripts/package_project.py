"""Build a source-only sharing archive using an explicit file allowlist."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "movielens-qa-airflow-demo"


def main():
    paths = [
        ROOT / name
        for name in (
            "README.md",
            "requirements.txt",
            "requirements-analysis.txt",
            ".gitignore",
            "main.py",
            "app.py",
            "test_main.py",
            "profiling.py",
            "tests/fixtures/ratings.tsv",
            "docs/ORIGINAL_README.md",
            "docs/PROJECT_OVERVIEW.md",
            "docs/RUNBOOK.md",
            "docs/INTERVIEW_GUIDE.md",
            ".github/workflows/tests.yml",
            "practice/airflow/compose.yaml",
            "scripts/package_project.py",
        )
    ]
    paths.extend(sorted((ROOT / "practice").glob("*.py")))
    paths.extend(sorted((ROOT / "practice/airflow/dags").glob("*.py")))

    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Expected a regular source file: {path}")

    output = ROOT / "dist" / f"{PACKAGE_NAME}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            archive.write(path, Path(PACKAGE_NAME) / path.relative_to(ROOT))

    print(f"Archive: {output}")
    print(f"Source files: {len(set(paths))}")
    print(f"Size: {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
