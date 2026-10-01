"""Privacy and Location Masking Domain Logic
Per NOTE.md §6.3 / §7:
- Viewer role: masked location geohash5 only (approx 4.9km x 4.9km bounding area, precise lat/lon suppressed)
- Fleet Manager & Admin roles: full precision lat/lon (geohash7)
"""

from typing import Tuple, Optional, Dict, Any
import pygeohash as pgh


def mask_location_for_role(
    lat: Optional[float],
    lon: Optional[float],
    geohash: Optional[str],
    user_role: str,
) -> Tuple[Optional[float], Optional[float], Optional[str], bool]:
    """Applies role-aware masking to location coordinates and geohash.
    Returns:
        (lat, lon, geohash, is_masked)
    """
    if user_role == "viewer":
        # Viewer only sees geohash5; exact lat/lon are masked
        masked_gh = geohash[:5] if geohash and len(geohash) >= 5 else None
        if masked_gh:
            # Decode to center of geohash5 cell for approximate mapping
            c_lat, c_lon = pgh.decode(masked_gh)
            return round(c_lat, 3), round(c_lon, 3), masked_gh, True
        return None, None, None, True
    else:
        # fleet_manager, admin, system receive exact telemetry coordinates
        return lat, lon, geohash, False


def apply_vehicle_masking(vehicle_dict: Dict[str, Any], user_role: str) -> Dict[str, Any]:
    """Applies privacy masking to vehicle dictionary in-place or returns updated copy."""
    lat = vehicle_dict.get("lat")
    lon = vehicle_dict.get("lon")
    geohash = vehicle_dict.get("geohash") or vehicle_dict.get("geohash7")

    m_lat, m_lon, m_gh, is_masked = mask_location_for_role(lat, lon, geohash, user_role)

    vehicle_dict["lat"] = m_lat
    vehicle_dict["lon"] = m_lon
    vehicle_dict["geohash"] = m_gh
    if "geohash7" in vehicle_dict and is_masked:
        vehicle_dict["geohash7"] = m_gh
    vehicle_dict["location_masked"] = is_masked
    return vehicle_dict
