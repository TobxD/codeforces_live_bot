import sys, time
import bot
import telegram as tg

# with -r restart and dont send msg for 30sec
if "-r" in sys.argv:
	tg.RESTART = time.time()
else:
	tg.RESTART = 0

# with -t the testing mode gets enabled,
# which only communicates over stdin/stdout instead of telegram
if "-t" in sys.argv:
	bot.startTestingMode()

#bot.mainLoop()
