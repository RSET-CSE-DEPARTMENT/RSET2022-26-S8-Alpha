import math

def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + \
        math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * \
        math.sin(dlon/2)**2

    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))


def check_geofence(lat, lng, fence):
    dist = distance_m(lat, lng, fence["lat"], fence["lng"])

    if dist <= fence["radius"] * 0.3:
        return "INSIDE_30"
    elif dist <= fence["radius"]:
        return "INSIDE"
    else:
        return "OUTSIDE"
