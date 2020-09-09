import sys, os, time
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
			Chat.chats[chatId].sendMessage(msgText)
		time.sleep(1)
		while tg.requestSpooler._q[0].qsize() > 0:
			print("waiting")
			time.sleep(1)
		logger.info("sending broadcasts finished")
	except Exception as e:
		logger.critical(str(e))
else:
	logger.error("wrong command line options\nusage: python3 sendBroadcast.py <file with text>")
os._exit(0)
