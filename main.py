import sys, os
from commands import bot
from utils import util

util.initLogging()

# with -t the testing mode gets enabled,
# which only communicates over stdin/stdout instead of telegram
if "-t" in sys.argv:
	bot.startTestingMode()
elif "--production" in sys.argv:
	bot.startTelegramBot()
else:
	print("invalid options")
	os._exit(0)
