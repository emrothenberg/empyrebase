from empyrebase.types.private import Private


class GeoPoint(object):
    latitude: Private[float]
    longitude: Private[float]

    def __init__(self, latitude, longitude):
        self.latitude = Private(latitude)
        self.longitude = Private(longitude)

    def to_dict(self):
        return {
            "latitude": self.latitude.get(),
            "longitude": self.longitude.get(),
        }

    def __repr__(self):
        return f"<GeoPoint latitude={self.latitude.get()} longitude={self.longitude.get()}>"
