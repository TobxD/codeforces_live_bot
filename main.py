import sys, time
import bot
import telegram as tg
import util

util.initLogging()

# with -t the testing mode gets enabled,
# which only communicates over stdin/stdout instead of telegram
if "-t" in sys.argv:
	bot.startTestingMode()
elif "--production" in sys.argv:
	bot.startTelegramBot()
