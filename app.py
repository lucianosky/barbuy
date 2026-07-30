from datetime import date, timedelta, time
import streamlit as st
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from astral import LocationInfo
from astral.sun import sun

st.set_page_config(page_title="Barbuy — Calculadora Solar", page_icon="☀️", layout="wide")

st.title("☀️ Barbuy — Calculadora Solar")
st.caption("Precisão de segundos para nascer do sol, pôr do sol e duração do dia.")


def geocode_city(city_name: str):
    geolocator = Nominatim(user_agent="barbuy-solar-calculator")
    try:
        location = geolocator.geocode(city_name, language="pt", timeout=10)
        return location
    except (GeocoderTimedOut, GeocoderServiceError):
        return None


def format_time(dt) -> str:
    return dt.strftime("%H:%M:%S")


def format_duration(delta) -> str:
    total = int(delta.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def delta_seconds(td) -> int:
    return int(td.total_seconds())


# --- Input: cidade ---
col1, col2 = st.columns([2, 1])

with col1:
    city_input = st.text_input("Cidade", placeholder="Ex: Porto Alegre, Buenos Aires, Lisboa...")

location = None
city_info = None

if city_input:
    with st.spinner("Buscando localização..."):
        location = geocode_city(city_input)

    if location:
        st.success(f"**{location.address}**")
        col_lat, col_lon = st.columns(2)
        col_lat.metric("Latitude", f"{location.latitude:.6f}°")
        col_lon.metric("Longitude", f"{location.longitude:.6f}°")

        city_info = LocationInfo(
            name=city_input,
            region="",
            timezone="UTC",
            latitude=location.latitude,
            longitude=location.longitude,
        )

        # tenta obter timezone via geopy
        try:
            from geopy.geocoders import Nominatim as Nom
            raw = location.raw
            # extrai timezone do endereço completo se disponível
        except Exception:
            pass

    else:
        st.error("Cidade não encontrada. Tente um nome diferente.")

# --- Input: data e período ---
if city_info:
    st.divider()
    col_date, col_period = st.columns([1, 1])

    with col_date:
        selected_date = st.date_input("Data", value=date.today())

    with col_period:
        period_days = st.selectbox("Período (dias antes e depois)", [10, 30, 60], index=1)

    # --- Cálculo ---
    st.divider()

    date_start = selected_date - timedelta(days=period_days)
    date_end = selected_date + timedelta(days=period_days)
    total_days = period_days * 2 + 1

    rows = []
    current = date_start

    # precisamos de timezone — usamos timezonefinder se disponível, senão UTC
    try:
        from timezonefinder import TimezoneFinder
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=location.latitude, lng=location.longitude) or "UTC"
    except ImportError:
        tz_name = "UTC"

    city_info = LocationInfo(
        name=city_input,
        region="",
        timezone=tz_name,
        latitude=location.latitude,
        longitude=location.longitude,
    )

    with st.spinner(f"Calculando {total_days} dias..."):
        while current <= date_end:
            try:
                s = sun(city_info.observer, date=current, tzinfo=city_info.timezone)
                sunrise_dt = s["sunrise"]
                sunset_dt = s["sunset"]
                duration = sunset_dt - sunrise_dt
                rows.append({
                    "date": current,
                    "sunrise_dt": sunrise_dt,
                    "sunset_dt": sunset_dt,
                    "duration": duration,
                })
            except Exception:
                pass
            current += timedelta(days=1)

    if rows:
        # calcula extremos
        max_sunrise = max(r["sunrise_dt"].replace(tzinfo=None).time() for r in rows)
        min_sunset = min(r["sunset_dt"].replace(tzinfo=None).time() for r in rows)
        min_duration = min(r["duration"] for r in rows)

        # monta tabela
        table = []
        for r in rows:
            sunrise_time = r["sunrise_dt"].replace(tzinfo=None).time()
            sunset_time = r["sunset_dt"].replace(tzinfo=None).time()

            def time_to_td(t):
                return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

            delta_sunrise = time_to_td(max_sunrise) - time_to_td(sunrise_time)
            delta_sunset = time_to_td(sunset_time) - time_to_td(min_sunset)
            delta_duration = r["duration"] - min_duration

            is_selected = r["date"] == selected_date

            table.append({
                "Data": r["date"].strftime("%Y-%m-%d") + (" ◀" if is_selected else ""),
                "Nascer do sol": format_time(r["sunrise_dt"]),
                "Pôr do sol": format_time(r["sunset_dt"]),
                "Duração": format_duration(r["duration"]),
                "Δs nascer (tardio)": delta_seconds(delta_sunrise),
                "Δs pôr (cedo)": delta_seconds(delta_sunset),
                "Δs duração (curto)": delta_seconds(delta_duration),
            })

        import pandas as pd
        df = pd.DataFrame(table)

        st.subheader(f"Resultados — {city_input} ({tz_name})")
        st.caption(
            f"Período: {date_start.strftime('%d/%m/%Y')} a {date_end.strftime('%d/%m/%Y')} · "
            f"{total_days} dias · "
            f"Nascer mais tardio: {max_sunrise.strftime('%H:%M:%S')} · "
            f"Pôr mais cedo: {min_sunset.strftime('%H:%M:%S')} · "
            f"Dia mais curto: {format_duration(min_duration)}"
        )

        st.dataframe(df, use_container_width=True, hide_index=True)

        st.caption("Δs = diferença em segundos em relação ao extremo do período. Horários no fuso da cidade selecionada.")

st.divider()
st.caption("Barbuy · homenagem à astrônoma brasileira Beatriz Barbuy (IAG/USP) · cálculos via [astral](https://sffjunkie.github.io/astral/)")
