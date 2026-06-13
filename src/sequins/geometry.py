"""Geometry value types.

These collapse the model's lexical types (``Position``, ``Rect Size``, ``Coordinate``,
``Distance``) onto plain ``float`` pairs.  All coordinates are expressed in Tablet's
**lower-left origin, y-up** space; the model's notion of bead *depth* (downward from the
rod) is converted to these coordinates by the layout pass -- Sequins owns that flip.
"""
from __future__ import annotations

from dataclasses import dataclass

# The model distinguishes Coordinate / Distance lexically; in code they are just floats.
Coordinate = float
Distance = float


@dataclass(frozen=True, slots=True)
class Position:
    """A point (model type: ``Position``)."""

    x: Coordinate
    y: Coordinate


@dataclass(frozen=True, slots=True)
class RectSize:
    """The width and height of a rectangle (model type: ``Rect Size``)."""

    width: Distance
    height: Distance


@dataclass(frozen=True, slots=True)
class Padding:
    """Canvas padding that frames the diagram interior (model type: ``Padding``)."""

    top: Distance
    bottom: Distance
    left: Distance
    right: Distance
