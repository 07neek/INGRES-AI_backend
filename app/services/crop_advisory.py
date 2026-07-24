"""
crop_advisory.py
"""

from typing import Dict, List

ADVISORY: Dict[str, List[str]] = {
    "Safe": [
        "Water-intensive crops (paddy, sugarcane) remain viable, but continued monitoring is advised.",
        "Good conditions to diversify into higher-value crops while maintaining efficient irrigation.",
        "Consider community-level recharge structures now to protect long-term sustainability.",
    ],
    "Semi-Critical": [
        "Gradually shift a portion of area from paddy/sugarcane toward maize, soybean, or groundnut.",
        "Adopt sprinkler irrigation for existing water-intensive crops to cut withdrawal.",
        "New borewells should be spaced and depth-regulated per state groundwater authority norms.",
    ],
    "Critical": [
        "Prioritize millets (bajra, jowar, ragi), pulses (moong, urad, arhar) and oilseeds (mustard).",
        "Drip irrigation is strongly recommended over flood irrigation for all remaining crops.",
        "Avoid sanctioning new high-discharge borewells; consider farm ponds and check dams for recharge.",
    ],
    "Over-Exploited": [
        "Shift decisively to drought-resilient crops: millets, pulses, and low-water horticulture (ber, custard apple).",
        "Discourage paddy and sugarcane expansion; explore crop insurance and MSP support for the transition.",
        "Mandatory rainwater harvesting / artificial recharge structures alongside strict extraction regulation.",
    ],
    "Saline": [
        "Favor salt-tolerant varieties and species suited to saline/coastal soils.",
        "Improve sub-surface drainage and consider gypsum-based soil treatment where advised locally.",
        "Blend or conjunctive-use irrigation (surface + treated water) can reduce reliance on saline groundwater.",
    ],
}

DISCLAIMER = (
    "General guidance based on groundwater category, not an individualized farm plan — "
    "please confirm specifics with your local Krishi Vigyan Kendra or agriculture extension officer."
)


def get_advisory(records: List[dict]) -> List[str]:
    """Given matched groundwater records, returns de-duplicated advisory bullet
    points for every category present, plus a closing disclaimer line."""
    if not records:
        return []

    categories_present = []
    for r in records:
        cat = r.get("category")
        if cat and cat not in categories_present:
            categories_present.append(cat)

    tips: List[str] = []
    for cat in categories_present:
        tips.extend(ADVISORY.get(cat, []))

    if tips:
        tips.append(DISCLAIMER)
    return tips
