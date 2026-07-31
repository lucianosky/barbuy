from datetime import date, timedelta
import streamlit as st
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from astral import LocationInfo
from astral.sun import sun
import pandas as pd

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


def time_to_td(t):
    return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)


def nearest_solstices(ref_date: date, hemisphere: str) -> list[tuple[str, date]]:
    """Retorna os 2 solstícios anteriores e 2 posteriores à ref_date.
    Hemisfério sul: inverno = junho, verão = dezembro.
    Hemisfério norte: inverno = dezembro, verão = junho.
    """
    # datas aproximadas dos solstícios (dia 21 de junho e dezembro)
    candidates = []
    for year in range(ref_date.year - 2, ref_date.year + 3):
        if hemisphere == "sul":
            candidates.append(("Inverno", date(year, 6, 21)))
            candidates.append(("Verão",   date(year, 12, 21)))
        else:
            candidates.append(("Verão",   date(year, 6, 21)))
            candidates.append(("Inverno", date(year, 12, 21)))

    candidates.sort(key=lambda x: x[1])

    before = [(label, d) for label, d in candidates if d < ref_date]
    after  = [(label, d) for label, d in candidates if d >= ref_date]

    return before[-2:] + after[:2]


# --- Input: cidade ---
city_input = st.text_input("Cidade", placeholder="Ex: Porto Alegre, Buenos Aires, Lisboa...")

location = None
city_info = None
tz_name = "UTC"

if city_input:
    with st.spinner("Buscando localização..."):
        location = geocode_city(city_input)

    if location:
        st.success(f"**{location.address}**")
        col_lat, col_lon = st.columns(2)
        col_lat.metric("Latitude", f"{location.latitude:.6f}°")
        col_lon.metric("Longitude", f"{location.longitude:.6f}°")

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
    else:
        st.error("Cidade não encontrada. Tente um nome diferente.")

# --- Input: data e período ---
if city_info:
    st.divider()

    hemisphere = "sul" if location.latitude < 0 else "norte"
    solstices = nearest_solstices(date.today(), hemisphere)

    solstice_labels = [f"Solstício de {label} — {d.strftime('%d/%m/%Y')}" for label, d in solstices]
    solstice_dates  = [d for _, d in solstices]

    col_date, col_period, col_solstice = st.columns([1, 1, 2])

    with col_date:
        selected_date = st.date_input("Data", value=date.today())

    with col_period:
        period_days = st.selectbox("Período (dias antes e depois)", [10, 30, 60], index=1)

    with col_solstice:
        solstice_choice = st.selectbox("Ir para solstício", ["—"] + solstice_labels)
        if solstice_choice != "—":
            idx = solstice_labels.index(solstice_choice)
            selected_date = solstice_dates[idx]
            st.caption(f"Data ajustada para {selected_date.strftime('%d/%m/%Y')}")

    # --- Cálculo ---
    st.divider()

    date_start  = selected_date - timedelta(days=period_days)
    date_end    = selected_date + timedelta(days=period_days)
    total_days  = period_days * 2 + 1

    rows = []
    current = date_start

    with st.spinner(f"Calculando {total_days} dias..."):
        while current <= date_end:
            try:
                s = sun(city_info.observer, date=current, tzinfo=city_info.timezone)
                sunrise_dt = s["sunrise"]
                sunset_dt  = s["sunset"]
                duration   = sunset_dt - sunrise_dt
                rows.append({
                    "date":       current,
                    "sunrise_dt": sunrise_dt,
                    "sunset_dt":  sunset_dt,
                    "duration":   duration,
                })
            except Exception:
                pass
            current += timedelta(days=1)

    if rows:
        max_sunrise  = max(r["sunrise_dt"].replace(tzinfo=None).time() for r in rows)
        min_sunset   = min(r["sunset_dt"].replace(tzinfo=None).time() for r in rows)
        min_duration = min(r["duration"] for r in rows)

        table = []
        for r in rows:
            sunrise_time = r["sunrise_dt"].replace(tzinfo=None).time()
            sunset_time  = r["sunset_dt"].replace(tzinfo=None).time()

            delta_sunrise  = time_to_td(max_sunrise) - time_to_td(sunrise_time)
            delta_sunset   = time_to_td(sunset_time)  - time_to_td(min_sunset)
            delta_duration = r["duration"] - min_duration

            is_selected       = r["date"] == selected_date
            is_max_sunrise    = sunrise_time == max_sunrise
            is_min_sunset     = sunset_time == min_sunset
            is_min_duration   = r["duration"] == min_duration

            table.append({
                "Data":               r["date"].strftime("%Y-%m-%d") + (" ◀" if is_selected else ""),
                "Nascer do sol":      format_time(r["sunrise_dt"]) + (" ◀" if is_max_sunrise else ""),
                "Pôr do sol":         format_time(r["sunset_dt"])  + (" ◀" if is_min_sunset else ""),
                "Duração":            format_duration(r["duration"]) + (" ◀" if is_min_duration else ""),
                "Δs nascer (tardio)": delta_seconds(delta_sunrise),
                "Δs pôr (cedo)":      delta_seconds(delta_sunset),
                "Δs duração (curto)": delta_seconds(delta_duration),
            })

        df = pd.DataFrame(table)

        def highlight(df):
            styles = pd.DataFrame("", index=df.index, columns=df.columns)
            for i, row in df.iterrows():
                if "◀" in str(row["Data"]):
                    styles.at[i, "Data"] = "background-color: #dbeafe"
                if "◀" in str(row["Nascer do sol"]):
                    styles.at[i, "Nascer do sol"] = "background-color: #fef9c3"
                if "◀" in str(row["Pôr do sol"]):
                    styles.at[i, "Pôr do sol"] = "background-color: #ffedd5"
                if "◀" in str(row["Duração"]):
                    styles.at[i, "Duração"] = "background-color: #fce7f3"
            return styles

        styled = df.style.apply(highlight, axis=None)
        table_height = len(df) * 35 + 38

        st.subheader(f"Resultados — {city_input} ({tz_name})")
        st.caption(
            f"Período: {date_start.strftime('%d/%m/%Y')} a {date_end.strftime('%d/%m/%Y')} · "
            f"{total_days} dias · "
            f"Nascer mais tardio: {max_sunrise.strftime('%H:%M:%S')} · "
            f"Pôr mais cedo: {min_sunset.strftime('%H:%M:%S')} · "
            f"Dia mais curto: {format_duration(min_duration)}"
        )

        st.dataframe(styled, use_container_width=True, hide_index=True, height=table_height)

        st.caption("Δs = diferença em segundos em relação ao extremo do período. Horários no fuso da cidade selecionada.")

st.divider()
st.caption("Barbuy · homenagem à astrônoma brasileira Beatriz Barbuy (IAG/USP) · cálculos via [astral](https://sffjunkie.github.io/astral/)")
