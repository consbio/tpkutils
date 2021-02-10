import math


def geo_bounds(xmin, ymin, xmax, ymax):
    """
    Project web mercator bounds to geographic.

    Parameters
    ----------
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    Returns
    -------
    [xmin, ymin, xmax, ymax] in geographic coordinates
    """

    merc_max = 20037508.342789244
    if any(abs(v) > merc_max for v in (xmin, xmax, ymin, ymax)):
        raise ValueError('Web Mercator bounds must be within world domain')

    sma = 6378137.0  # semi-major axis for WGS84
    rad2deg = 180.0 / math.pi  # radians to degrees

    lons = [(x * rad2deg / sma) for x in (xmin, xmax)]
    lats = [
        ((math.pi * 0.5) - 2.0 * math.atan(math.exp(-y / sma))) * rad2deg
        for y in (ymin, ymax)
    ]
    return [lons[0], lats[0], lons[1], lats[1]]
