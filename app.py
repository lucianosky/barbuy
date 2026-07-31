from datetime import date, timedelta
import streamlit as st
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from astral import LocationInfo
from astral.sun import sun
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Barbuy — Calculadora Solar", page_icon="☀️", layout="wide")

st.title("☀️ Barbuy — Calculadora Solar")
st.caption("Precisão de segundos para nascer do sol, pôr do sol e duração do dia.")


@st.cache_data(show_spinner=False)
def geocode_city(city_name: str):
    geolocator = Nominatim(user_agent="barbuy-solar-calculator")
    try:
        location = geolocator.geocode(city_name, language="pt", timeout=10)
        return location
    except (GeocoderTimedOut, GeocoderServiceError):
        return None


def format_time(dt) -> str:
    ms = dt.microsecond // 1000
    return dt.strftime("%H:%M:%S") + f".{ms:03d}"


def format_duration(delta) -> str:
    total = delta.total_seconds()
    h = int(total) // 3600
    m = (int(total) % 3600) // 60
    s = int(total) % 60
    ms = int((total - int(total)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def format_delta(td) -> str:
    return f"{td.total_seconds():.3f}"


def time_to_td(t):
    return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second, microseconds=t.microsecond)


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


@st.cache_data(show_spinner=False)
def calculate_solar_rows(lat: float, lon: float, tz_name: str, date_start, date_end) -> list:
    from astral import LocationInfo
    city = LocationInfo(name="", region="", timezone=tz_name, latitude=lat, longitude=lon)
    rows = []
    current = date_start
    while current <= date_end:
        try:
            s = sun(city.observer, date=current, tzinfo=city.timezone)
            sunrise_dt = s["sunrise"]
            sunset_dt  = s["sunset"]
            duration   = sunset_dt - sunrise_dt
            rows.append({
                "date":       current,
                "sunrise_dt": sunrise_dt,
                "sunset_dt":  sunset_dt,
                "duration":   duration,
                "d_nascer":   None,
                "d_por":      None,
                "d_duracao":  None,
            })
        except Exception:
            pass
        current += timedelta(days=1)
    return rows


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
        period_days = st.selectbox("Período (dias antes e depois)", [10, 30, 60, 90, 120, 180, 360], index=1)

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

    with st.spinner(f"Calculando {total_days} dias..."):
        rows = calculate_solar_rows(
            location.latitude, location.longitude, tz_name, date_start, date_end
        )

    if rows:
        max_sunrise  = max(r["sunrise_dt"].replace(tzinfo=None).time() for r in rows)
        min_sunset   = min(r["sunset_dt"].replace(tzinfo=None).time() for r in rows)
        min_duration = min(r["duration"] for r in rows)

        table = []
        flags = []
        for r in rows:
            sunrise_time = r["sunrise_dt"].replace(tzinfo=None).time()
            sunset_time  = r["sunset_dt"].replace(tzinfo=None).time()

            delta_sunrise  = time_to_td(max_sunrise) - time_to_td(sunrise_time)
            delta_sunset   = time_to_td(sunset_time)  - time_to_td(min_sunset)
            delta_duration = r["duration"] - min_duration

            r["d_nascer"]  = delta_sunrise.total_seconds()
            r["d_por"]     = delta_sunset.total_seconds()
            r["d_duracao"] = delta_duration.total_seconds()

            flags.append({
                "is_selected":     r["date"] == selected_date,
                "is_max_sunrise":  delta_sunrise.total_seconds() < 0.005,
                "is_min_sunset":   delta_sunset.total_seconds() < 0.005,
                "is_min_duration": delta_duration.total_seconds() < 0.005,
            })

            table.append({
                "Data":                r["date"].strftime("%Y-%m-%d"),
                "Nascer do sol":       format_time(r["sunrise_dt"]),
                "Pôr do sol":          format_time(r["sunset_dt"]),
                "Duração":             format_duration(r["duration"]),
                "Δ nascer tardio (s)": format_delta(delta_sunrise),
                "Δ pôr cedo (s)":      format_delta(delta_sunset),
                "Δ duração curto (s)": format_delta(delta_duration),
            })

        df = pd.DataFrame(table)

        CELL = "background-color: {}; color: #111111"
        C_DATE    = CELL.format("#bfdbfe")  # azul pastel
        C_SUNRISE = CELL.format("#fef08a")  # amarelo pastel
        C_SUNSET  = CELL.format("#fed7aa")  # laranja pastel
        C_DUR     = CELL.format("#f9a8d4")  # rosa pastel

        def highlight(df):
            styles = pd.DataFrame("", index=df.index, columns=df.columns)
            for i, f in enumerate(flags):
                if f["is_selected"]:
                    styles.at[i, "Data"] = C_DATE
                if f["is_max_sunrise"]:
                    styles.at[i, "Nascer do sol"]       = C_SUNRISE
                    styles.at[i, "Δ nascer tardio (s)"] = C_SUNRISE
                if f["is_min_sunset"]:
                    styles.at[i, "Pôr do sol"]     = C_SUNSET
                    styles.at[i, "Δ pôr cedo (s)"] = C_SUNSET
                if f["is_min_duration"]:
                    styles.at[i, "Duração"]             = C_DUR
                    styles.at[i, "Δ duração curto (s)"] = C_DUR
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

        st.caption("Δ (s) = diferença em segundos (precisão de milissegundo) em relação ao extremo do período. Horários no fuso da cidade selecionada.")

        # --- Gráfico ---
        st.divider()
        st.subheader("Curvas dos deltas")

        dates      = [r["date"] for r in rows]
        d_nascer   = [r["d_nascer"]   for r in rows]
        d_por      = [r["d_por"]      for r in rows]
        d_duracao  = [r["d_duracao"]  for r in rows]

        idx_nascer  = d_nascer.index(min(d_nascer))
        idx_por     = d_por.index(min(d_por))
        idx_duracao = d_duracao.index(min(d_duracao))

        fig = go.Figure()

        # curvas
        fig.add_trace(go.Scatter(
            x=dates, y=d_nascer, name="Δ nascer tardio",
            line=dict(color="#ca8a04", width=2),
            hovertemplate="%{x}<br>%{y:.3f}s<extra>Δ nascer</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=d_por, name="Δ pôr cedo",
            line=dict(color="#c2410c", width=2),
            hovertemplate="%{x}<br>%{y:.3f}s<extra>Δ pôr</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=d_duracao, name="Δ duração curto",
            line=dict(color="#be185d", width=2),
            hovertemplate="%{x}<br>%{y:.3f}s<extra>Δ duração</extra>",
        ))

        # pontos de mínimo
        for idx, d_list, color, label in [
            (idx_nascer,  d_nascer,  "#ca8a04", "nascer tardio"),
            (idx_por,     d_por,     "#c2410c", "pôr cedo"),
            (idx_duracao, d_duracao, "#be185d", "duração curta"),
        ]:
            fig.add_trace(go.Scatter(
                x=[dates[idx]], y=[d_list[idx]],
                mode="markers",
                marker=dict(color=color, size=10, symbol="circle"),
                name=f"mín {label}",
                hovertemplate=f"{dates[idx]}<br>{d_list[idx]:.3f}s<extra>mín {label}</extra>",
                showlegend=False,
            ))
            fig.add_vline(
                x=str(dates[idx]),
                line=dict(color=color, width=1, dash="dot"),
                annotation_text=dates[idx].strftime("%d/%m"),
                annotation_position="top",
                annotation_font=dict(color=color, size=11),
            )

        # data selecionada — só desenha se não coincidir com nenhum mínimo
        minima_dates = {dates[idx_nascer], dates[idx_por], dates[idx_duracao]}
        if selected_date not in minima_dates:
            fig.add_vline(
                x=str(selected_date),
                line=dict(color="#93c5fd", width=1.5, dash="dash"),
                annotation_text=selected_date.strftime("%d/%m"),
                annotation_position="top right",
                annotation_font=dict(color="#93c5fd", size=11),
            )

        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Δ (segundos)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            hovermode="x unified",
            margin=dict(t=60, b=40),
            height=420,
        )

        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("Barbuy · homenagem à astrônoma brasileira Beatriz Barbuy (IAG/USP) · cálculos via [astral](https://sffjunkie.github.io/astral/)")
