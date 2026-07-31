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


@st.cache_data(show_spinner=False)
def calculate_solar_rows(lat: float, lon: float, tz_name: str, date_start, date_end) -> list:
    city = LocationInfo(name="", region="", timezone=tz_name, latitude=lat, longitude=lon)
    rows = []
    current = date_start
    while current <= date_end:
        try:
            s = sun(city.observer, date=current, tzinfo=city.timezone)
            sunrise_dt = s["sunrise"]
            sunset_dt  = s["sunset"]
            rows.append({
                "date":       current,
                "sunrise_dt": sunrise_dt,
                "sunset_dt":  sunset_dt,
                "duration":   sunset_dt - sunrise_dt,
            })
        except Exception:
            pass
        current += timedelta(days=1)
    return rows


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


def solar_events(year: int, hemisphere: str) -> list:
    """4 eventos astronômicos do ano em ordem calendário, com labels corretos por hemisfério."""
    raw = [
        (date(year, 3, 20),  "Equinócio de Outono"    if hemisphere == "sul" else "Equinócio de Primavera"),
        (date(year, 6, 21),  "Solstício de Inverno"   if hemisphere == "sul" else "Solstício de Verão"),
        (date(year, 9, 22),  "Equinócio de Primavera" if hemisphere == "sul" else "Equinócio de Outono"),
        (date(year, 12, 21), "Solstício de Verão"     if hemisphere == "sul" else "Solstício de Inverno"),
    ]
    return [(label, d) for d, label in raw]


EVENT_COLORS = {
    "Solstício de Inverno":    "#fef08a",
    "Solstício de Verão":      "#fca5a5",
    "Equinócio de Primavera":  "#86efac",
    "Equinócio de Outono":     "#fdba74",
}

CELL = "background-color: {}; color: #111111"
C_DATE     = CELL.format("#bfdbfe")
C_SUNRISE  = CELL.format("#fef08a")
C_SUNSET   = CELL.format("#fed7aa")
C_DUR      = CELL.format("#f9a8d4")
C_ABOVE12H = CELL.format("#bbf7d0")  # verde pastel — duração imediatamente acima de 12h
C_BELOW12H = CELL.format("#ddd6fe")  # lavanda pastel — duração imediatamente abaixo de 12h


# ─── Input: cidade ────────────────────────────────────────────────────────────

city_input = st.text_input("Cidade", placeholder="Ex: Porto Alegre, Buenos Aires, Lisboa...")

location = None
city_info = None
tz_name   = "UTC"

if city_input:
    with st.spinner("Buscando localização..."):
        location = geocode_city(city_input)

    if location:
        st.success(f"**{location.address}**")
        col_lat, col_lon = st.columns(2)
        col_lat.metric("Latitude",  f"{location.latitude:.6f}°")
        col_lon.metric("Longitude", f"{location.longitude:.6f}°")

        try:
            from timezonefinder import TimezoneFinder
            tz_name = TimezoneFinder().timezone_at(lat=location.latitude, lng=location.longitude) or "UTC"
        except ImportError:
            tz_name = "UTC"

        city_info = LocationInfo(
            name=city_input, region="",
            timezone=tz_name,
            latitude=location.latitude,
            longitude=location.longitude,
        )
    else:
        st.error("Cidade não encontrada. Tente um nome diferente.")


if city_info:
    st.divider()

    hemisphere = "sul" if location.latitude < 0 else "norte"
    year       = date.today().year
    events     = solar_events(year, hemisphere)

    col_window, _ = st.columns([1, 3])
    with col_window:
        window = st.selectbox("Janela ao redor de cada evento (dias)", [10, 20, 30], index=1)

    # ─── Gráfico anual ────────────────────────────────────────────────────────

    st.divider()
    st.subheader(f"Curvas dos deltas — {city_input} · {year}")

    with st.spinner("Calculando ano completo..."):
        year_rows = calculate_solar_rows(
            location.latitude, location.longitude, tz_name,
            date(year, 1, 1), date(year, 12, 31),
        )

    yr_dates = [r["date"] for r in year_rows]

    yr_max_sunrise  = max(r["sunrise_dt"].replace(tzinfo=None).time() for r in year_rows)
    yr_min_sunset   = min(r["sunset_dt"].replace(tzinfo=None).time() for r in year_rows)
    yr_min_duration = min(r["duration"] for r in year_rows)

    yr_d_nascer  = []
    yr_d_por     = []
    yr_d_duracao = []
    for r in year_rows:
        sunrise_time = r["sunrise_dt"].replace(tzinfo=None).time()
        sunset_time  = r["sunset_dt"].replace(tzinfo=None).time()
        yr_d_nascer.append((time_to_td(yr_max_sunrise) - time_to_td(sunrise_time)).total_seconds())
        yr_d_por.append((time_to_td(sunset_time) - time_to_td(yr_min_sunset)).total_seconds())
        yr_d_duracao.append((r["duration"] - yr_min_duration).total_seconds())

    fig_year = go.Figure()
    fig_year.add_trace(go.Scatter(
        x=yr_dates, y=yr_d_nascer, name="Δ nascer tardio",
        line=dict(color="#ca8a04", width=2),
        hovertemplate="%{x}<br>%{y:.3f}s<extra>Δ nascer</extra>",
    ))
    fig_year.add_trace(go.Scatter(
        x=yr_dates, y=yr_d_por, name="Δ pôr cedo",
        line=dict(color="#c2410c", width=2),
        hovertemplate="%{x}<br>%{y:.3f}s<extra>Δ pôr</extra>",
    ))
    fig_year.add_trace(go.Scatter(
        x=yr_dates, y=yr_d_duracao, name="Δ duração curto",
        line=dict(color="#be185d", width=2),
        hovertemplate="%{x}<br>%{y:.3f}s<extra>Δ duração</extra>",
    ))

    # marcadores de mínimo (próximos ao solstício de inverno)
    for d_list, c, lbl in [
        (yr_d_nascer,  "#ca8a04", "nascer tardio"),
        (yr_d_por,     "#c2410c", "pôr cedo"),
        (yr_d_duracao, "#be185d", "duração curta"),
    ]:
        idx_min = d_list.index(min(d_list))
        idx_max = d_list.index(max(d_list))
        for idx, symbol, tag in [(idx_min, "circle", "mín"), (idx_max, "diamond", "máx")]:
            fig_year.add_trace(go.Scatter(
                x=[yr_dates[idx]], y=[d_list[idx]],
                mode="markers",
                marker=dict(color=c, size=9, symbol=symbol),
                showlegend=False,
                hovertemplate=f"{tag} {lbl}<br>{yr_dates[idx]}<br>{d_list[idx]:.3f}s<extra></extra>",
            ))

    # vlines dos 4 eventos (solstícios + equinócios)
    ann_positions = ["top left", "top right", "top left", "top right"]
    for (ev_label, d), ann_pos in zip(events, ann_positions):
        ev_color = EVENT_COLORS.get(ev_label, "#ffffff")
        fig_year.add_vline(
            x=str(d),
            line=dict(color=ev_color, width=1.5, dash="dot"),
            annotation_text=f"{ev_label}<br>{d.strftime('%d/%m')}",
            annotation_position=ann_pos,
            annotation_font=dict(color=ev_color, size=10),
        )

    fig_year.update_layout(
        xaxis_title="Data",
        yaxis_title="Δ (segundos)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        margin=dict(t=90, b=40),
        height=420,
    )
    st.plotly_chart(fig_year, use_container_width=True)

    # ─── Mini gráficos dos solstícios ────────────────────────────────────────

    equinoxes = [(lbl, d) for lbl, d in events if "Solstício" in lbl]
    eq_cols   = st.columns(2)

    for col, (eq_label, eq_date) in zip(eq_cols, equinoxes):
        eq_color  = EVENT_COLORS.get(eq_label, "#ffffff")
        eq_start  = eq_date - timedelta(days=15)
        eq_end    = eq_date + timedelta(days=15)

        with st.spinner(f"Calculando {eq_label}..."):
            eq_rows = calculate_solar_rows(
                location.latitude, location.longitude, tz_name, eq_start, eq_end
            )

        if not eq_rows:
            continue

        eq_dates    = [r["date"] for r in eq_rows]
        eq_max_sr   = max(r["sunrise_dt"].replace(tzinfo=None).time() for r in eq_rows)
        eq_min_ss   = min(r["sunset_dt"].replace(tzinfo=None).time() for r in eq_rows)
        eq_min_dur  = min(r["duration"] for r in eq_rows)

        eq_d_nascer  = []
        eq_d_por     = []
        eq_d_duracao = []
        for r in eq_rows:
            st_ = r["sunrise_dt"].replace(tzinfo=None).time()
            ss_ = r["sunset_dt"].replace(tzinfo=None).time()
            eq_d_nascer.append((time_to_td(eq_max_sr) - time_to_td(st_)).total_seconds())
            eq_d_por.append((time_to_td(ss_) - time_to_td(eq_min_ss)).total_seconds())
            eq_d_duracao.append((r["duration"] - eq_min_dur).total_seconds())

        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            x=eq_dates, y=eq_d_nascer, name="Δ nascer tardio",
            line=dict(color="#ca8a04", width=2),
            hovertemplate="%{x}<br>%{y:.3f}s<extra>Δ nascer</extra>",
        ))
        fig_eq.add_trace(go.Scatter(
            x=eq_dates, y=eq_d_por, name="Δ pôr cedo",
            line=dict(color="#c2410c", width=2),
            hovertemplate="%{x}<br>%{y:.3f}s<extra>Δ pôr</extra>",
        ))
        fig_eq.add_trace(go.Scatter(
            x=eq_dates, y=eq_d_duracao, name="Δ duração curto",
            line=dict(color="#be185d", width=2),
            hovertemplate="%{x}<br>%{y:.3f}s<extra>Δ duração</extra>",
        ))

        for d_list, c, lbl in [
            (eq_d_nascer,  "#ca8a04", "nascer tardio"),
            (eq_d_por,     "#c2410c", "pôr cedo"),
            (eq_d_duracao, "#be185d", "duração curta"),
        ]:
            idx_min = d_list.index(min(d_list))
            idx_max = d_list.index(max(d_list))
            for idx, symbol, tag in [(idx_min, "circle", "mín"), (idx_max, "diamond", "máx")]:
                fig_eq.add_trace(go.Scatter(
                    x=[eq_dates[idx]], y=[d_list[idx]],
                    mode="markers",
                    marker=dict(color=c, size=8, symbol=symbol),
                    showlegend=False,
                    hovertemplate=f"{tag} {lbl}<br>{eq_dates[idx]}<br>{d_list[idx]:.3f}s<extra></extra>",
                ))

        fig_eq.add_vline(
            x=str(eq_date),
            line=dict(color=eq_color, width=1.5, dash="dash"),
            annotation_text=f"{eq_label}<br>{eq_date.strftime('%d/%m')}",
            annotation_position="top",
            annotation_font=dict(color=eq_color, size=10),
        )

        fig_eq.update_layout(
            xaxis_title="Data",
            yaxis_title="Δ (segundos)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            hovermode="x unified",
            margin=dict(t=70, b=40),
            height=340,
        )

        with col:
            st.plotly_chart(fig_eq, use_container_width=True)

    # ─── 4 seções de evento ───────────────────────────────────────────────────

    for label, event_date in events:
        color   = EVENT_COLORS.get(label, "#ffffff")
        d_start = event_date - timedelta(days=window)
        d_end   = event_date + timedelta(days=window)

        st.divider()
        st.subheader(f"{label} — {event_date.strftime('%d/%m/%Y')}")
        st.caption(f"{d_start.strftime('%d/%m')} a {d_end.strftime('%d/%m/%Y')} · {window*2+1} dias · {tz_name}")

        with st.spinner(f"Calculando {window*2+1} dias..."):
            rows = calculate_solar_rows(
                location.latitude, location.longitude, tz_name, d_start, d_end
            )

        if not rows:
            continue

        is_equinox = "Equinócio" in label

        max_sunrise  = max(r["sunrise_dt"].replace(tzinfo=None).time() for r in rows)
        min_sunset   = min(r["sunset_dt"].replace(tzinfo=None).time() for r in rows)
        min_duration = min(r["duration"] for r in rows)

        # Para equinócios: encontrar os dois dias que cruzam 12h de duração
        TWELVE_HOURS  = timedelta(hours=12)
        above_12h_date = below_12h_date = None
        if is_equinox:
            min_above = min_below = None
            for r in rows:
                diff = r["duration"] - TWELVE_HOURS
                if diff >= timedelta(0):
                    if min_above is None or diff < min_above:
                        min_above = diff
                        above_12h_date = r["date"]
                else:
                    neg = TWELVE_HOURS - r["duration"]
                    if min_below is None or neg < min_below:
                        min_below = neg
                        below_12h_date = r["date"]

        table          = []
        flags          = []
        d_nascer_list  = []
        d_por_list     = []
        d_duracao_list = []

        for r in rows:
            sunrise_time = r["sunrise_dt"].replace(tzinfo=None).time()
            sunset_time  = r["sunset_dt"].replace(tzinfo=None).time()

            delta_sunrise  = time_to_td(max_sunrise) - time_to_td(sunrise_time)
            delta_sunset   = time_to_td(sunset_time)  - time_to_td(min_sunset)
            delta_duration = r["duration"] - min_duration

            d_nascer_list.append(delta_sunrise.total_seconds())
            d_por_list.append(delta_sunset.total_seconds())
            d_duracao_list.append(delta_duration.total_seconds())

            flags.append({
                "is_selected":     r["date"] == event_date,
                "is_max_sunrise":  not is_equinox and delta_sunrise.total_seconds()  < 0.005,
                "is_min_sunset":   not is_equinox and delta_sunset.total_seconds()   < 0.005,
                "is_min_duration": not is_equinox and delta_duration.total_seconds() < 0.005,
                "is_above_12h":    is_equinox and r["date"] == above_12h_date,
                "is_below_12h":    is_equinox and r["date"] == below_12h_date,
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

        captured_flags = flags  # capture for closure

        def highlight(df, _flags=captured_flags):
            styles = pd.DataFrame("", index=df.index, columns=df.columns)
            for i, f in enumerate(_flags):
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
                if f["is_above_12h"]:
                    styles.at[i, "Duração"] = C_ABOVE12H
                if f["is_below_12h"]:
                    styles.at[i, "Duração"] = C_BELOW12H
            return styles

        table_height = len(df) * 35 + 38
        styled = df.style.apply(highlight, axis=None)
        st.dataframe(styled, use_container_width=True, hide_index=True, height=table_height)

st.divider()
st.caption("Barbuy · homenagem à astrônoma brasileira Beatriz Barbuy (IAG/USP) · cálculos via [astral](https://sffjunkie.github.io/astral/)")
