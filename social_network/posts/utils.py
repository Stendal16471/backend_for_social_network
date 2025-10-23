from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time


def get_geolocation(location_name):
    """
    Получает географические координаты по названию местоположения.

    Использует сервис Nominatim для геокодирования.

    Args:
        location_name (str): Название местоположения (например, "Москва, Россия")

    Returns:
        dict|null: Словарь с координатами и адресом или None при ошибке
        {
            'latitude': float,
            'longitude': float,
            'address': str
        }

    Example:
        >>> get_geolocation("Москва, Россия")
        {'latitude': 55.7558, 'longitude': 37.6173, 'address': 'Москва, Россия'}
    """
    if not location_name:
        return None

    geolocator = Nominatim(user_agent="social_network_app")

    try:
        location = geolocator.geocode(location_name, timeout=5)
        if location:
            return {
                'latitude': location.latitude,
                'longitude': location.longitude,
                'address': location.address
            }
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error: {e}")
        return None

    return None


def get_location_name(latitude, longitude):
    """
    Получает название местоположения по географическим координатам.

    Использует обратное геокодирование через Nominatim.

    Args:
        latitude (float): Географическая широта
        longitude (float): Географическая долгота

    Returns:
        str|null: Название местоположения или None при ошибке

    Example:
        >>> get_location_name(55.7558, 37.6173)
        'Москва, Центральный федеральный округ, Россия'
    """
    geolocator = Nominatim(user_agent="social_network_app")

    try:
        location = geolocator.reverse((latitude, longitude),
                                      exactly_one=True,
                                      timeout=5)
        if location:
            return location.address
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Reverse geocoding error: {e}")

    return None