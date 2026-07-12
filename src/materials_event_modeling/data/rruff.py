"""Parse the deposited RRUFF processed-spectrum text format."""

from __future__ import annotations

import numpy as np


def parse_spectrum_text(text: str) -> tuple[dict[str, str], np.ndarray, np.ndarray]:
    """Return RRUFF headers, wavenumbers, and intensities from one text export."""
    metadata: dict[str, str] = {}
    wavenumbers: list[float] = []
    intensities: list[float] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("##") and "=" in line:
            key, value = line[2:].split("=", 1)
            metadata[key.strip()] = value.strip()
        elif line and "," in line:
            parts = line.split(",")
            try:
                wavenumbers.append(float(parts[0]))
                intensities.append(float(parts[1]))
            except (ValueError, IndexError):
                continue
    return metadata, np.asarray(wavenumbers), np.asarray(intensities)
