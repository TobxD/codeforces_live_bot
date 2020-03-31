import telegram as tg
import database as db
import threading

chatsLock = threading.Lock()
chats = {}

# the chatId has to be a string
def getChat(chatId):
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
	def __init__(self, chatId):
		self._chatId = chatId
		infos = db.queryChatInfos(chatId)
		if infos is None:
			self._apikey = None
			self._secret = None
			self._timezone = None
			self._handle = None
			self._updateDB()
		else:
			(self._apikey, self._secret, self._timezone, self._handle) = infos
		if self._timezone is None:
			self._timezone = "UTC"
		openCommand = None

	@property
	def chatId(self):
		return self._chatId

	@chatId.setter
	def chatId(self, chatId):
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

	def _updateDB(self):
		db.updateChatInfos(self.chatId, self.apikey, self.secret, self.timezone, self.handle)

	def sendMessage(self, text, reply_markup = None):
		if self.chatId == '0':
			print('\n----- message sent: ------------\n' + text + "\n--------- End Message ----------\n")
		else:
			return tg.sendMessage(self.chatId, text, reply_markup)

	def editMessageReplyMarkup(self, msgId, reply_markup):
		if self.chatId == '0':
			print('\n----- message edited to: ---------\n' + reply_markup + "\n--------- End Message ----------\n")
		else:
			tg.editMessageReplyMarkup(self.chatId, msgId, reply_markup)

	def editMessageText(self, msgId, msg):
		if self.chatId == '0':
			print('\n----- message edited to: ---------\n' + msg + "\n--------- End Message ----------\n")
		else:
			tg.editMessageText(self.chatId, msgId, msg)
