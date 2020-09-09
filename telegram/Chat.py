import threading

from telegram import telegram as tg
from utils import database as db

chatsLock = threading.Lock()
chats = {}

def getChat(chatId : str):
	with chatsLock:
		if chatId not in chats:
			chats[chatId] = Chat(chatId)
	return chats[chatId]

def initChats():
	with chatsLock:
		chatIds = db.getAllChatPartners()
		for chatId in chatIds:
			chats[chatId] = Chat(chatId)

class Chat:
	def __init__(self, chatId:str):
		self._chatId = chatId
		self._activeMsgGroups = set()
		self._editLaterLock = threading.Lock()
		self._notifications = []	# all upsolving etc. msgs to be grouped
		self._notificationLock = threading.Lock()
		infos = db.queryChatInfos(chatId)
		if infos is None:
			self._apikey = None
			self._secret = None
			self._timezone = None
			self._handle = None
			self._notifyLevel = 3
			self._polite = False
			self._reply = True
			self._width = 6
			self._reminder2h = True
			self._reminder1d = True
			self._reminder3d = False
			self._settings_msgid = None
			self._updateDB()
		else:
			(self._apikey, self._secret, self._timezone, self._handle,
			 self._notifyLevel,
			 self._polite, self._reply, self._width,
			 self._reminder2h, self._reminder1d, self._reminder3d,
			 self._settings_msgid) = infos
		if self._timezone is None:
			self._timezone = "UTC"

	@property
	def chatId(self):
		return self._chatId

	@chatId.setter
	def chatId(self, chatId:str):
		self._chatId = chatId
		self._updateDB()

	@property
	def apikey(self):
		return self._apikey

	@apikey.setter
	def apikey(self, key):
		self._apikey = key
		self._updateDB()

	@property
	def secret(self):
		return self._secret

	@secret.setter
	def secret(self, scr):
		self._secret = scr
		self._updateDB()

	@property
	def timezone(self):
		return self._timezone

	@timezone.setter
	def timezone(self, tz):
		self._timezone = tz
		self._updateDB()

	@property
	def handle(self):
		return self._handle

	@handle.setter
	def handle(self, h):
		self._handle = h
		self._updateDB()

	@property
	def notifyLevel(self):
		return self._notifyLevel

	@notifyLevel.setter
	def notifyLevel(self, l):
		self._notifyLevel = l
		self._updateDB()

	@property
	def polite(self):
		return self._polite
	
	@polite.setter
	def polite(self, l):
		self._polite = l
		self._updateDB()

	@property
	def reply(self):
		return self._reply
	
	@reply.setter
	def reply(self, newVal):
		self._reply = newVal
		self._updateDB()

	@property
	def width(self):
		return self._width
	
	@width.setter
	def width(self, newVal):
		self._width = newVal
		self._updateDB()

	@property
	def reminder2h(self):
		return self._reminder2h
	
	@reminder2h.setter
	def reminder2h(self, newVal):
		self._reminder2h = newVal
		self._updateDB()

	@property
	def reminder1d(self):
		return self._reminder1d
	
	@reminder1d.setter
	def reminder1d(self, newVal):
		self._reminder1d = newVal
		self._updateDB()

	@property
	def reminder1d(self):
		return self._reminder1d
	
	@reminder1d.setter
	def reminder1d(self, newVal):
		self._reminder1d = newVal
		self._updateDB()

	@property
	def reminder3d(self):
		return self._reminder3d
	
	@reminder3d.setter
	def reminder3d(self, newVal):
		self._reminder3d = newVal
		self._updateDB()

	@property
	def settings_msgid(self):
		return self._settings_msgid
	
	@settings_msgid.setter
	def settings_msgid(self, newVal):
		self._settings_msgid = newVal
		self._updateDB()

	def _updateDB(self):
		db.updateChatInfos(self.chatId, self.apikey, self.secret, self.timezone,
			self.handle, self._notifyLevel,
			self.polite, self.reply, self.width, self.reminder2h,
			self.reminder1d, self.reminder3d, self.settings_msgid)

	def sendMessage(self, text, reply_markup = None, callback=None):
		if self.chatId == '0':
			print('\n----- message sent: ------------\n' + text + "\n--------- End Message ----------\n")
			return 0
		else:
			tg.requestSpooler.put(lambda : tg.sendMessage(self.chatId, text, reply_markup, callback), priority=0)

	# message which can be grouped
	def sendNotifcation(self, text):
		if self.chatId == '0':
			print('\n----- message sent: ------------\n' + text + "\n--------- End Message ----------\n")
			return
		def sendGroupedNotifications():
			with self._notificationLock:
				msgText = "\n".join(self._notifications)
				self._notifications = []
			tg.sendMessage(self._chatId, msgText)

		with self._notificationLock:
			self._notifications.append(text)
			if len(self._notifications) == 1: # add to spooler queue
				tg.requestSpooler.put(sendGroupedNotifications, priority=1)

	def editMessageText(self, msgId, msg, reply_markup = None):
		if self.chatId == '0':
			print('\n----- message edited to: ---------\n' + msg + "\n--------- End Message ----------\n")
		else:
			tg.requestSpooler.put(lambda : tg.editMessageText(self.chatId, msgId, msg, reply_markup), priority=0)

	def editMessageTextLater(self, msgId, msgGroup, fun):
		if self.chatId == '0':
			msg = fun(self)
			if msg:
				print('\n----- message sent: ------------\n' + msg + "\n--------- End Message ----------\n")
			return
		with self._editLaterLock:
			if msgGroup not in self._activeMsgGroups:
				self._activeMsgGroups.add(msgGroup)
			else:
				return

		def editMsgNow():
			msg = fun(self, msgGroup)
			if msg:
				tg.editMessageText(self.chatId, msgId, msg)
			with self._editLaterLock:
				self._activeMsgGroups.remove(msgGroup)
		tg.requestSpooler.put(editMsgNow, priority=2)

	def deleteMessage(self, msgId):
		if self.chatId == '0':
			print('\n----- message deleted:' + msgId + '---------\n')
		else:
			tg.requestSpooler.put(lambda : tg.deleteMessage(self.chatId, msgId), priority=1)
