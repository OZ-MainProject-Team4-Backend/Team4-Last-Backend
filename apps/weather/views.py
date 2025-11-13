from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as py_tz
from typing import List, Tuple

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.weather import repository as repo
from apps.weather.models import WeatherData, WeatherLocation
from apps.weather.serializers import (
    CurrentQuerySerializer,
    ForecastQuerySerializer,
    HistoryQuerySerializer,
)
from apps.weather.services import geocoding
from apps.weather.services import openweather as ow


class WeatherDataOutSerializer(serializers.ModelSerializer):
    location_name = serializers.SerializerMethodField()

    class Meta:
        model = WeatherData
        fields = [
            "id",
            "location_name",
            "base_time",
            "valid_time",
            "temperature",
            "feels_like",
            "humidity",
            "rain_probability",
            "rain_volume",
            "wind_speed",
            "condition",
            "icon",
        ]

    def get_location_name(self, obj: WeatherData) -> str:
        loc = obj.location
        return getattr(loc, "dp_name", f"{loc.city} {loc.district}".strip())


class WeatherViewSet(viewsets.GenericViewSet):
    serializer_class = WeatherDataOutSerializer

    def _resolve_coords_from_query(self, request) -> Tuple[float, float, str, str]:
        q = CurrentQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        lat = q.validated_data.get("lat")
        lon = q.validated_data.get("lon")
        city = q.validated_data.get("city")
        district = q.validated_data.get("district") or ""
        if lat is not None and lon is not None:
            return float(lat), float(lon), (city or ""), district
        g = geocoding.geocode_city_district(city=city, district=district or None)
        if not g:
            raise serializers.ValidationError(
                {"detail": "해당 지역을 변환 할 수 없습니다."}
            )
        return float(g["lat"]), float(g["lon"]), g["city"], (g["district"] or "")

    def _get_or_create_location(
        self, *, lat: float, lon: float, city: str, district: str
    ) -> WeatherLocation:
        loc, _ = WeatherLocation.objects.get_or_create(
            city=city or "",
            district=district or "",
            defaults={
                "lat": lat,
                "lon": lon,
                "dp_name": f"{(city or '').strip()} {(district or '').strip()}".strip(),
            },
        )
        to_update = []
        if loc.lat != lat:
            loc.lat = lat
            to_update.append("lat")
        if loc.lon != lon:
            loc.lon = lon
            to_update.append("lon")
        dp = f"{(city or '').strip()} {(district or '').strip()}".strip()
        if getattr(loc, "dp_name", "") != dp:
            loc.dp_name = dp
            to_update.append("dp_name")
        if to_update:
            loc.save(update_fields=to_update)
        return loc

    @extend_schema(
        summary="현재 날씨 조회",
        parameters=[
            OpenApiParameter(
                name="city", type=str, location=OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                name="district",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="lat", type=float, location=OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                name="lon", type=float, location=OpenApiParameter.QUERY, required=False
            ),
        ],
        responses=WeatherDataOutSerializer,
    )
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        try:
            lat, lon, city, district = self._resolve_coords_from_query(request)
            try:
                cur = ow.get_current(lat=lat, lon=lon)
            except ow.ProviderTimeout:
                return Response(
                    {"detail": "provider_timeout"}, status=status.HTTP_502_BAD_GATEWAY
                )
            except ow.ProviderError as e:
                return Response(
                    {"detail": str(e) or "provider_error"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            raw_city = (cur.get("raw") or {}).get("name")
            if raw_city and not city:
                city = raw_city
            loc = self._get_or_create_location(
                lat=lat, lon=lon, city=city or "", district=district or ""
            )
            with transaction.atomic():
                obj = repo.save_current(location=loc, current=cur)
            return Response(
                WeatherDataOutSerializer(obj).data, status=status.HTTP_200_OK
            )
        except serializers.ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "weather_fetch_failed"}, status=status.HTTP_502_BAD_GATEWAY
            )

    @extend_schema(
        summary="날씨 예보 조회",
        parameters=[
            OpenApiParameter(
                name="city", type=str, location=OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                name="district",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="lat", type=float, location=OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                name="lon", type=float, location=OpenApiParameter.QUERY, required=False
            ),
        ],
        responses=WeatherDataOutSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="forecast")
    def forecast(self, request):
        try:
            q = ForecastQuerySerializer(data=request.query_params)
            q.is_valid(raise_exception=True)
            lat, lon, city, district = self._resolve_coords_from_query(request)
            try:
                fc = ow.get_forecast(lat=lat, lon=lon)
            except ow.ProviderTimeout:
                return Response(
                    {"detail": "provider_timeout"}, status=status.HTTP_502_BAD_GATEWAY
                )
            except ow.ProviderError as e:
                return Response(
                    {"detail": str(e) or "provider_error"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            payload_city = ((fc.get("city") or {}).get("name")) or city
            loc = self._get_or_create_location(
                lat=lat, lon=lon, city=payload_city or "", district=district or ""
            )
            with transaction.atomic():
                saved_count = repo.save_forecast(location=loc, forecast_payload=fc)
            dts = []
            for item in fc.get("list", []):
                ts = int(item.get("dt", 0))
                dts.append(datetime.fromtimestamp(ts, tz=py_tz.utc))
            objs = list(
                WeatherData.objects.filter(location=loc, valid_time__in=dts).order_by(
                    "valid_time"
                )
            )
            return Response(
                {
                    "count": saved_count,
                    "items": WeatherDataOutSerializer(objs, many=True).data,
                },
                status=status.HTTP_200_OK,
            )
        except serializers.ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "weather_fetch_failed"}, status=status.HTTP_502_BAD_GATEWAY
            )

    @extend_schema(
        summary="날씨 히스토리 조회",
        parameters=[
            OpenApiParameter(
                name="location_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="lat", type=float, location=OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                name="lon", type=float, location=OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                name="start", type=str, location=OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                name="end", type=str, location=OpenApiParameter.QUERY, required=False
            ),
        ],
        responses=WeatherDataOutSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        try:
            q = HistoryQuerySerializer(data=request.query_params)
            q.is_valid(raise_exception=True)
            loc = None
            if q.validated_data.get("location_id"):
                loc = WeatherLocation.objects.filter(
                    id=q.validated_data["location_id"]
                ).first()
                if not loc:
                    return Response(
                        {"detail": "location_not_found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                lat = q.validated_data.get("lat")
                lon = q.validated_data.get("lon")
                if lat is None or lon is None:
                    return Response(
                        {"detail": "location_id 또는 lat/lon 중 하나는 필수"},
                        status=400,
                    )
                loc = (
                    WeatherLocation.objects.filter(lat=float(lat), lon=float(lon))
                    .order_by("-id")
                    .first()
                )
                if not loc:
                    loc = WeatherLocation.objects.create(
                        city="",
                        district="",
                        lat=float(lat),
                        lon=float(lon),
                        dp_name=f"{lat},{lon}",
                    )
            start = q.validated_data.get("start")
            end = q.validated_data.get("end")
            if not start or not end:
                end_dt = timezone.now()
                start_dt = end_dt - timedelta(days=3)
            else:
                start_dt = datetime.combine(start, datetime.min.time()).replace(
                    tzinfo=py_tz.utc
                )
                end_dt = datetime.combine(end, datetime.max.time()).replace(
                    tzinfo=py_tz.utc
                )
            qs = WeatherData.objects.filter(
                location=loc, valid_time__range=(start_dt, end_dt)
            ).order_by("valid_time")
            return Response(
                WeatherDataOutSerializer(qs, many=True).data, status=status.HTTP_200_OK
            )
        except serializers.ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "history_fetch_failed"}, status=status.HTTP_502_BAD_GATEWAY
            )


#
