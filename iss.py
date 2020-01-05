import ephem
import datetime
from calendar import timegm
from math import degrees
import redis
import json
import os

REDIS_URL = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.StrictRedis.from_url(REDIS_URL)


def get_location():
    """Compute the current location of the ISS"""

    # Get latest TLE from redis
    tle = json.loads(r.get("iss_tle"))
    iss = ephem.readtle(str(tle[0]), str(tle[1]), str(tle[2]))

    # Compute for now
    now = datetime.datetime.utcnow()
    iss.compute(now)
    lon = degrees(iss.sublong)
    lat = degrees(iss.sublat)

    # Return the relevant timestamp and data
    return {"timestamp": timegm(now.timetuple()), "iss_position": {"latitude": lat, "longitude": lon}}


def get_tle():
    """Grab the current TLE"""
    return json.loads(r.get("iss_tle"))


def get_tle_time():
    """Grab the current TLE time"""
    return r.get("iss_tle_time")


def get_tle_update():
    """Grab the tle update time"""
    return r.get("iss_tle_last_update")


def get_passes(lon, lat, alt, n, horizon='599:00'):
    """Compute n number of passes of the ISS for a location"""




    # Get latest TLE from redis
    tle = json.loads(r.get("iss_tle"))
    iss = ephem.readtle(str(tle[0]), str(tle[1]), str(tle[2]))

    # Set location
    location = ephem.Observer()
    location.lat = str(lat)
    location.long = str(lon)
    location.elevation = alt
    location.pressure = 0

    # Reset horizon to our horizon threshold to see the space 
    # station.
    location.horizon = horizon

    # Set time now
    now = datetime.datetime.utcnow()
    location.date = now
    # Predict passes
    passes = []
    for p in xrange(n):
        tr, azr, tt, altt, ts, azs = location.next_pass(iss)
        duration = int((ts - tr) * 60 * 60 * 24)
        year, month, day, hour, minute, second = tr.tuple()
        dt = datetime.datetime(year, month, day, hour, minute, int(second))

        if duration > 30:

            # check if the time of day is appropriate for station viewing 
            sunchecker = ephem.Observer()
            sunchecker.date = ephem.Date(tt)
            sunchecker.lat = str(lat)
            sunchecker.long = str(lon)
            sunchecker.elevation = 408773
            sunchecker.pressure = 0
            sunchecker.horizon = '-6'
            
            last_sunrise = sunchecker.previous_rising(ephem.Sun())
            next_sunset = sunchecker.next_setting(ephem.Sun())

            # TODO compute actual twilight times; for now, just say it's two hours..?
            visible = False
            vws = ephem.Date(last_sunrise + (-90*ephem.minute))
            vwe = ephem.Date(last_sunrise + (90*ephem.minute))

            if vws < tt < vwe:
                visible = True
            # or sunset
#            if (tt < (next_sunset + (90*ephem.minute))):
#                visible = True
            
            if visible:
                passes.append({
                                "transit start time" : str(tr),
                                "transit end time" : str(ts),
                                "transit max elevation time" : str(tt),
                                "duration in seconds"  : duration,
                                "riseazimuth":str(azr),
                                "setazimuth" :str(azs),
                                "maxalt" : str(altt),
                                "maxalttype" : str(type(altt)),
                                "maxaltdeg" : str(ephem.degrees(altt)),
                                "visible" : str(visible),
                                "sunrise" : str(last_sunrise), 
                                "sunset"  : str(next_sunset),
                                "vws"     : str(vws),
                                "vwe"     : str(vwe),
                                "types"   : "{},{},{}".format(type(tt), type(vws), type(vwe))
                                    })

        # Increase the time by more than a pass and less than an orbit
        location.date = tr + 25*ephem.minute

    # Return object
    obj = {"request": {
        "datetime": timegm(now.timetuple()),
        "latitude": lat,
        "longitude": lon,
        "altitude": alt,
        "passes": n,
        "horizon":horizon
        },
        "response": passes,
    }

    return obj
