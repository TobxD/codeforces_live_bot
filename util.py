import hashlib
import datetime
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from pytz import timezone, utc
import threading
import logging, os
from logging.handlers import TimedRotatingFileHandler

# global and exported (init at initLogging)
logger = None


def cleanString(s):
	return s.lower().strip()

def sha512Hex(s):
	return hashlib.sha512(s.encode()).hexdigest()

def getLocFromName(name):
	geolocator = Nominatim(user_agent="codeforces_live_bot")
	res = geolocator.geocode(name)
	if res:
		return res.latitude, res.longitude
	return None, None

def getTimeZoneFromLatLong(lat, lng):
	tf = TimezoneFinder()
	tz_name = tf.timezone_at(lng=lng, lat=lat)
	return tz_name

def getTimeZone(name):
	lat, lng = getLocFromName(name)
	if not lat:
		return None
	return getTimeZoneFromLatLong(lat, lng)

def getUTCTime():
	return datetime.datetime.now(timezone("UTC"))

# date: UTC datetime object
# timezone: string e.g "Europe/Berlin"
def dateToTimezone(date, timez):
	date.replace(tzinfo=timezone("UTC"))
	return date.astimezone(timezone(timez))

def formatDate(date, f):
	months = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
	days = ["Mon.", "Tue.", "Wen.", "Thu.", "Fri.", "Sat.", "Sun."]
	f = f.replace('#hh#', date.strftime("%H"))
	f = f.replace('#h#', date.strftime("%-H"))
	f = f.replace('#mm#', date.strftime("%M"))
	f = f.replace('#DD#', date.strftime("%d"))
	f = f.replace('#DDD#', days[date.weekday()])
	f = f.replace('#MM#', date.strftime("%m"))
	f = f.replace('#MMM#', months[date.month -1])
	f = f.replace('#YYYY#', date.strftime("%Y"))
	f = f.replace('#YY#', date.strftime("%y"))
	return f

def displayTime(t, timez):
	if t is None:
		return "forever"
	if timez is None or timez == "":
		timez = "UTC"
	now = datetime.datetime.now(timezone(timez))
	t = datetime.datetime.utcfromtimestamp(t).replace(tzinfo=timezone("UTC")).astimezone(timezone(timez))

	diff = (t - now).total_seconds()
	outText = ""
	if diff < 60*1:
		outText = "Now"
	elif diff < 60*60*24:
		if now.date() != t.date():
			outText = "Tomorrow "
		else:
			outText = "Today "
		outText += formatDate(t,"#hh#:#mm#")
	elif diff < 60*60*24*14:
		outText = formatDate(t,"#DDD# #DD# #MMM# #hh#:#mm#")
	elif diff < 60*60*24*14:
		outText = formatDate(t,"#DD#. #MMM# #hh#:#mm#")
	elif diff < 60*60*24*30*3:
		outText = formatDate(t,"#DD#. #MMM#")
	else:
		outText = formatDate(t,"#DD#.#MM#.#YYYY#")

	return outText

def formatSeconds(s, useExcl = False):
	s = s//60
	if s < 60:
		out = "0:" + str(s).zfill(2)
	else:
		out = str(s//60) + ":" + str(s%60).zfill(2)
	return out.replace(":", "!") if useExcl else out

def getUserSmiley(rating):
	rating = int(rating)
	if rating < 1200:
		return "🧟"
	elif rating < 1400:
		return "👷🏻"
	elif rating < 1600:
		return "🧑🏻‍🎓"
	elif rating < 1900:
		return "🧑🏻‍🔬"
	elif rating < 2100:
		return "🧑🏻‍🚀"
	elif rating < 2400:
		return "🧙🏻"
	else:
		return "🦸🏻"

def initLogging():
	global logger
	if not os.path.exists("log"):
		os.mkdir("log")
	logger = logging.getLogger()
	logger.setLevel(logging.DEBUG)
	hConsole = logging.StreamHandler()
	# rotating every wednesday at 04:00
	rotSettings = {"when": "W2", "interval" : 1, "atTime": datetime.time(4, 0), 
								"backupCount": 10}
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s: %(message)s')

	hDebug = TimedRotatingFileHandler("log/debug.txt", **rotSettings)
	hInfo  = TimedRotatingFileHandler("log/info.txt",  **rotSettings)
	hError = TimedRotatingFileHandler("log/error.txt", **rotSettings)
	hCrit  = TimedRotatingFileHandler("log/crit.txt",  **rotSettings)
	
	hConsole.setLevel(logging.INFO)
	hDebug.setLevel(logging.DEBUG)
	hInfo.setLevel(logging.INFO)
	hError.setLevel(logging.ERROR)
	hCrit.setLevel(logging.CRITICAL)

	for h in [hConsole, hDebug, hInfo, hError, hCrit]:
		h.setFormatter(formatter)
		logger.addHandler(h)
