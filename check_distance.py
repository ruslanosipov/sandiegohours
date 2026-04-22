import math

def calculate_distance_meters(lat1, lng1, lat2, lng2):
    R = 6371000
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat / 2) * math.sin(d_lat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lng / 2) * math.sin(d_lng / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Your location
center_lat, center_lng = 32.762889, -117.119922

# The Hangout
hangout_lat, hangout_lng = 32.7632105, -117.134357

distance = calculate_distance_meters(center_lat, center_lng, hangout_lat, hangout_lng)
print(f"Distance to The Hangout: {distance:.0f}m ({distance/1609:.2f} miles)")
print(f"Within 800m radius: {distance <= 800}")
