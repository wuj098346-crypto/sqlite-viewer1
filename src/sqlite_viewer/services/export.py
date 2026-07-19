import csv
from pathlib import Path

from sqlite_viewer.models.errors import ExportError


class ExportService:
    def write_csv(
        self,
        destination: Path,
        columns: tuple[str, ...],
        rows: tuple[tuple[object, ...], ...],
    ) -> None:
        try:
            with destination.open("w", encoding="utf-8", newline="") as output_file:
                writer = csv.writer(output_file)
                writer.writerow(columns)
                writer.writerows(
                    tuple("" if value is None else value for value in row)
                    for row in rows
                )
        except (OSError, csv.Error) as error:
            raise ExportError(f"Could not export CSV: {destination}") from error
