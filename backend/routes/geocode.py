"""
Геокодирование через Яндекс API
"""
from fastapi import APIRouter, HTTPException, Query
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
from config import settings


router = APIRouter(prefix="/api/geocode", tags=["geocode"])


@router.get("/reverse")
def reverse_geocode(
    lat: float = Query(..., description="Широта"),
    lon: float = Query(..., description="Долгота")
):
    if not settings.YANDEX_GEOCODER_API_KEY:
        raise HTTPException(status_code=500, detail="Не задан ключ Яндекс Геокодера")

    params = {
        "apikey": settings.YANDEX_GEOCODER_API_KEY,
        "format": "json",
        "geocode": f"{lon},{lat}",
        "kind": "house",
        "results": 1,
        "lang": "ru_RU",
    }
    url = f"https://geocode-maps.yandex.ru/1.x/?{urlencode(params)}"

    try:
        request = Request(url, headers={"User-Agent": "heritage-routes"})
        with urlopen(request, timeout=10) as response:
            data = json.load(response)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка геокодера: {exc}") from exc

    try:
        collection = data["response"]["GeoObjectCollection"]["featureMember"]
        if not collection:
            return {"address": ""}

        geo_object = collection[0]["GeoObject"]
        address = geo_object["metaDataProperty"]["GeocoderMetaData"]["text"]
        return {"address": address}
    except Exception:
        return {"address": ""}
