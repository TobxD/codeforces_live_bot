import sys, os, time, re, datetime
from telegram import Chat
from utils import util
from utils.util import logger
from telegram import telegram as tg

util.initLogging()
Chat.initChats()

if len(sys.argv) != 1:
	try:
		msgText = open(sys.argv[1]).read()[:-1] # discard trailing newline
		logger.info("sending broadcast message:\n" + msgText)
		for chatId in Chat.chats:
			msg = msgText
			chat = Chat.chats[chatId]
			while (m := re.search("\[%t [0-9]*\]", msg)):
				tInSec = int(m.group()[4: -1])
				timeLeft = int(tInSec - time.time())
				delta = datetime.timedelta(seconds=timeLeft)
				dTime = f"*{util.displayTime(tInSec, chat.timezone)}* (in {':'.join(str(delta).split(':')[:2])} hours)"
				msg = msg[:m.span()[0]] + + msg[m.span()[1]:]
			print(f"chat: {chatId}: {msg}")
			#chat.sendMessage(msg)
		time.sleep(1)
		while tg.requestSpooler._q[0].qsize() > 0:
			try:
				print(f"waiting {tg.requestSpooler._q[0].qsize()}")
			except Exception as ex:
				print(ex)
			time.sleep(1)
		logger.info("sending broadcasts finished")
	except Exception as e:
		logger.critical(str(e))
else:
	logger.error("wrong command line options\nusage: python3 sendBroadcast.py <file with text>")
os._exit(0)
