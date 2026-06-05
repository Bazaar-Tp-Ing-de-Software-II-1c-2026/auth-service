from geopy.geocoders import Nominatim


geolocator = Nominatim(user_agent="bazaar-backend")


def validate_address(
    address: str,
    city: str,
    state: str,
    country: str,
):
    query = f"{address}, {city}, {state}, {country}"

    location = geolocator.geocode(query)

    if not location:
        return None

    return {
        "formatted_address": location.address,
        "latitude": location.latitude,
        "longitude": location.longitude,
    }