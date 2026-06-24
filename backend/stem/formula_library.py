"""Curated formula explanations for the STEM Formula Assistant.

This library provides fast, offline formula descriptions for common formulas.
It is intentionally small and focused on formulas that learners often see in
science and math content.
"""

from __future__ import annotations

import re
from typing import Any


def normalize_formula_key(formula: str) -> str:
    """Normalize formulas for library lookup."""

    if not formula:
        return ""

    key = re.sub(r"\s+", "", formula.strip())
    key = key.replace("−", "-")
    key = key.replace("÷", "/")
    key = key.replace("×", "*")
    key = key.replace("⋅", "*")
    key = key.replace("·", "*")
    key = key.replace("∕", "/")
    key = key.replace("⁄", "/")
    # Remove implicit multiplication operator (*) between variables
    # This aligns with the library's use of implicit multiplication (e.g., IR for I*R)
    key = re.sub(r"\*(?=[A-Za-z\d])", "", key)
    key = re.sub(r"(?<=[A-Za-z\d])\*(?=[A-Za-z\d])", "", key)
    return key.casefold()


FORMULA_LIBRARY: dict[str, dict[str, Any]] = {
    "F=ma": {
        "formula": "F = ma",
        "terms": {
            "F": "Force (push or pull)",
            "m": "Mass (how heavy something is)",
            "a": "Acceleration (how quickly speed changes)",
        },
        "meaning": "More force makes an object speed up faster.",
        "example": "A shopping cart needs more force when it is heavy.",
    },
    "E=mc^2": {
        "formula": "E = mc^2",
        "terms": {
            "E": "Energy (how much power something has)",
            "m": "Mass (how much matter is there)",
            "c": "Speed of light (a very fast constant)",
        },
        "meaning": "A small amount of mass becomes a lot of energy.",
        "example": "A tiny mass can release huge energy in a reaction.",
    },
    "a^2+b^2=c^2": {
        "formula": "a^2 + b^2 = c^2",
        "terms": {
            "a": "One side of a right triangle",
            "b": "Another side of a right triangle",
            "c": "The longest side of the triangle",
        },
        "meaning": "The longest side squared equals the sum of the other squares.",
        "example": "A right triangle with sides 3 and 4 has hypotenuse 5.",
    },
    "V=IR": {
        "formula": "V = IR",
        "terms": {
            "V": "Voltage (electrical push)",
            "I": "Current (flow of charge)",
            "R": "Resistance (how hard it is to flow)",
        },
        "meaning": "Voltage is current pushed through resistance.",
        "example": "A light bulb uses current based on battery voltage.",
    },
    "PV=nRT": {
        "formula": "PV = nRT",
        "terms": {
            "P": "Pressure (force on a space)",
            "V": "Volume (amount of space)",
            "n": "Amount of gas (moles)",
            "R": "Gas constant (fixed number)",
            "T": "Temperature (how hot it is)",
        },
        "meaning": "Gas pressure and volume depend on amount and temperature.",
        "example": "Hot gas in a container makes pressure rise.",
    },
    "A=\u03c0r^2": {
        "formula": "A = π r^2",
        "terms": {
            "A": "Area (space inside a circle)",
            "π": "Pi (circle number)",
            "r": "Radius (distance from center to edge)",
        },
        "meaning": "Circle area grows with the square of its radius.",
        "example": "A circle with radius 2 has area 4π.",
    },
    "C=2\u03c0r": {
        "formula": "C = 2 π r",
        "terms": {
            "C": "Circumference (distance around a circle)",
            "π": "Pi (circle number)",
            "r": "Radius (distance from center to edge)",
        },
        "meaning": "Circle edge length is twice pi times radius.",
        "example": "A circle with radius 3 has circumference 6π.",
    },
    "p=F/A": {
        "formula": "p = F / A",
        "terms": {
            "p": "Pressure (force per area)",
            "F": "Force (push or pull)",
            "A": "Area (space over which force acts)",
        },
        "meaning": "Pressure is force spread across an area.",
        "example": "A smaller shoe spreads weight over less area.",
    },
    "P=VI": {
        "formula": "P = V I",
        "terms": {
            "P": "Power (energy used each second)",
            "V": "Voltage (electrical push)",
            "I": "Current (flow of charge)",
        },
        "meaning": "Power is voltage times current.",
        "example": "A stronger voltage and current give more power.",
    },
}

FORMULA_LIBRARY = {
    normalize_formula_key(key): value
    for key, value in FORMULA_LIBRARY.items()
}


def get_formula_library_explanation(formula: str) -> dict[str, Any] | None:
    """Return a curated formula explanation when available."""

    return FORMULA_LIBRARY.get(normalize_formula_key(formula))
