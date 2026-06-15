from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


class CsvSplitError(RuntimeError):
    """Raised when a CSV cannot be split into import chunks."""


@dataclass(frozen=True)
class SplitResult:
    files: list[Path]
    total_rows: int
    rows_per_file: int


def split_csv(
    source: Path,
    rows_per_file: int = 300,
    output_dir: Path | None = None,
    delimiter: str = ";",
) -> SplitResult:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise CsvSplitError(f"File CSV non trovato: {source}")
    if rows_per_file < 1:
        raise CsvSplitError("rows_per_file deve essere maggiore di zero")
    if len(delimiter) != 1:
        raise CsvSplitError("Il delimitatore deve essere un singolo carattere")

    output_dir = (output_dir or source.parent / f"{source.stem}_split").expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    total_rows = 0

    with source.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.reader(input_file, delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise CsvSplitError(f"CSV vuoto: {source}") from exc

        writer: csv.writer | None = None
        output_file = None
        try:
            for row in reader:
                if total_rows % rows_per_file == 0:
                    if output_file:
                        output_file.close()
                    part_number = len(created) + 1
                    part_path = output_dir / f"{source.stem}_part{part_number:03d}.csv"
                    output_file = part_path.open("w", encoding="utf-8", newline="")
                    writer = csv.writer(output_file, delimiter=delimiter)
                    writer.writerow(header)
                    created.append(part_path)

                assert writer is not None
                writer.writerow(row)
                total_rows += 1
        finally:
            if output_file:
                output_file.close()

    if total_rows == 0:
        raise CsvSplitError(f"CSV senza righe dati: {source}")

    return SplitResult(files=created, total_rows=total_rows, rows_per_file=rows_per_file)
