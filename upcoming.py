import bot
import util
import database as db
import time, datetime
import codeforces as cf
import telegram as tg

def getDescription(contest, chat, timez = None):
	if timez is None:
		timez = chat.timezone
	tim = contest['startTimeSeconds']

	timeLeft = int(contest['startTimeSeconds'] - time.time())
	delta = datetime.timedelta(seconds=timeLeft)

	timeStr = "*" + util.displayTime(tim, timez)
	timeStr += '* (in ' + ':'.join(str(delta).split(':')[:2]) + ' hours' + ')'

	res = timeStr.ljust(35)
	res += ":\n" + contest['name'] + ""
	res += '\n'
	return res

def handleUpcoming(chat, req):
	bot.setOpenCommandFunc(chat.chatId, None)
	timez = chat.timezone
	msg = ""
	for c in sorted(cf.getFutureContests(), key=lambda x: x['startTimeSeconds']):
		if msg != "":
			msg += "\n"
		msg += getDescription(c, chat, timez)
	chat.sendMessage(msg)

