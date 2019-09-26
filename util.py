import hashlib
import datetime
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from pytz import timezone, utc

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

def log(msg, isError=False):
	timeString = '[' + str(datetime.datetime.now()) + '] '
	text = timeString + msg
	print(text)
	writeToFile("log.txt", text)
	if isError:
		writeToFile("error.txt", text)

def writeToFile(file, text):
	of = open(file, 'a')
	of.write(text + "\n")
	of.close()
