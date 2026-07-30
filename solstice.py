from datetime import date, timedelta, time
from astral import LocationInfo
from astral.sun import sun
from string import Template


class DeltaTemplate(Template):
    delimiter = "%"


def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["M"] = '{:02d}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


def extract_time(dt):
    return time(dt.hour, dt.minute, dt.second)


def info_city(city):
    print((
        f"Information for {city.name}/{city.region}\n"
        f"Timezone: {city.timezone}\n"
        f"Latitude: {city.latitude:.02f}; Longitude: {city.longitude:.02f}\n"
    ))


def seconds_interval(time_1, time_2):
    delta_1 = timedelta(hours=time_1.hour,minutes=time_1.minute,seconds=time_1.second)
    delta_2 = timedelta(hours=time_2.hour,minutes=time_2.minute,seconds=time_2.second)
    delta = delta_2 - delta_1
    return delta.total_seconds()


def build_min(value, min_value):
    if min_value is None or value < min_value:
        return value
    else:
        return min_value


def build_max(value, max_value):
    if max_value is None or value > max_value:
        return value
    else:
        return max_value


def winter_solstice():
    # city = LocationInfo("Porto Alegre", "Brasil", "America/Sao_Paulo", -30.0277, -51.2287)
    # city = LocationInfo("Palmas", "Brasil", "America/Sao_Paulo", -10.1689,  -48.3317)
    city = LocationInfo("Mar del Plata", "Argentina", "America/Buenos_Aires", -38.00042,  -57.5562)
    solstice_2020 = date(2020, 6, 20)
    days = 30
    date_1 = solstice_2020 - timedelta(days=days)
    date_2 = solstice_2020 + timedelta(days=days)
    hms = "%H:%M:%S"
    period = {}
    max_sunrise = None
    min_sunset = None
    min_duration = None

    while date_1 <= date_2:
        sun_times = sun(city.observer, date=date_1, tzinfo=city.timezone)
        sunrise = sun_times["sunrise"]
        sunset = sun_times["sunset"]
        time_sunrise = extract_time(sunrise)
        time_sunset = extract_time(sunset)
        duration = sunset - sunrise
        f_date = date_1.strftime("%Y-%m-%d")
        f_sunrise = sunrise.strftime(hms)
        f_sunset = sunset.strftime(hms)

        period[f_date] = {
            "date": date_1,
            "f_sunrise": f_sunrise,
            "f_sunset": f_sunset,
            "time_sunrise": time_sunrise,
            "time_sunset": time_sunset,
            "duration": duration,
        }

        max_sunrise = build_max(time_sunrise, max_sunrise)
        min_sunset = build_min(time_sunset, min_sunset)
        min_duration = build_min(duration, min_duration)

        date_1 += timedelta(days=1)

    print("date sunrise sunset duration s(sunrise) s(sunset) s(duration)")
    for value in period.values():
        seconds_sunrise = seconds_interval(value["time_sunrise"], max_sunrise)
        seconds_duration = (value["duration"] - min_duration).total_seconds()
        seconds_sunset = seconds_interval(min_sunset, value["time_sunset"])
        print(value["date"],
            value["f_sunrise"], value["f_sunset"], strfdelta(value["duration"],hms),
            int(seconds_sunrise), int(seconds_sunset), int(seconds_duration))

    print("max_sunrise:", max_sunrise)
    print("min_sunset:", min_sunset)
    print("min_duration:", strfdelta(min_duration, hms))
    print(info_city(city))
