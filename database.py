import mysql.connector
from util import logger
import threading
import Chat

db_creds = None
friendsNotfLock = threading.Lock()

def openDB():
	global db_creds
	if db_creds == None:
		db_creds = [line.rstrip('\n') for line in open('.database_creds')]
	db = mysql.connector.connect(user=db_creds[0], password=db_creds[1], host=db_creds[2], port=db_creds[3], database=db_creds[4])
	return db

def queryDB(query, params):
	db = openDB()
	cursor = db.cursor()
	cursor.execute(query, params)
	res = cursor.fetchall()
	cursor.close()
	db.close()
	return res

def insertDB(query, params):
	if len(params) == 0:
		return
	db = openDB()
	cursor = db.cursor()
	cursor.execute(query, params)
	db.commit()
	db.close()

# returns (apikey, secret, timezone, handle) or None, if no such user exists
def queryChatInfos(chatId):
	query = "SELECT apikey, secret, timezone, handle FROM tokens WHERE chatId = %s"
	res = queryDB(query, (chatId,))
	if len(res) == 0:
		return None
	else:
		return (res[0][0], res[0][1], res[0][2], res[0][3])

def updateChatInfos(chatId, apikey, secret, timezone, handle):
	query = ("INSERT INTO "
							"tokens (chatId, apikey, secret, timezone, handle) "
					"VALUES "
							"(%s, %s, %s, %s, %s) "
					"ON DUPLICATE KEY UPDATE "
							"apikey = %s , secret = %s , timezone = %s , handle = %s")
	insertDB(query, (chatId, apikey, secret, timezone, handle, apikey, secret, timezone, handle))

def getChatIds(handle):
	query = "SELECT chatId from tokens WHERE handle = %s"
	res = queryDB(query, (handle,))
	return [r[0] for r in res]

def deleteFriend(handle):
	logger.debug("deleting friends with handle " + handle)
	query = "DELETE FROM friends WHERE friend = %s"
	insertDB(query, (handle,))

	query = "SELECT chatId FROM tokens WHERE handle = %s"
	chatIds = [r[0] for r in queryDB(query, (handle,))]
	logger.debug(f"deleting chat handle {handle} for chats {chatIds}")
	for chatId in chatIds:
		Chat.getChat(chatId).handle = None # write through to DB

def deleteFriendOfUser(handle, chatId):
	logger.debug("deleting friend with handle " + handle + " from user " + str(chatId))
	query = "DELETE FROM friends WHERE friend = %s AND chatId = %s"
	insertDB(query, (handle,chatId))

def deleteUser(chatId):
	logger.debug("deleting all data of user with chatId " + str(chatId))
	query = "DELETE FROM friends WHERE chatId = %s"
	logger.debug("deleting all friend entries: " + query)
	insertDB(query, (chatId,))
	query = "DELETE FROM tokens WHERE chatId = %s"
	logger.debug("deleting all token entries: " + query)
	insertDB(query, (chatId,))

def addFriends(chatId, friends):
	query = "INSERT INTO friends (chatId, friend) VALUES "
	for f in friends:
		query += "(%s, %s), "
	query = query[:-2] + " ON DUPLICATE KEY UPDATE chatId=chatId"

	params = []
	for f in friends:
		params.append(chatId)
		params.append(f)

	insertDB(query, tuple(params))

def getFriends(chatId, selectorColumn = "True"):
	query = "SELECT friend, ratingWatch, contestWatch FROM friends WHERE chatId = %s AND " + selectorColumn + "=True"
	res = queryDB(query, (chatId,))
	return res

def getAllFriends():
	query = "SELECT DISTINCT friend FROM friends"
	res = queryDB(query, ())
	return [x[0] for x in res]

def getWhoseFriends(handle, allList = False):
	if allList:
		query = "SELECT DISTINCT chatId FROM friends WHERE friend = %s AND (ratingWatch=True OR contestWatch=True)"
	else:
		query = "SELECT DISTINCT chatId FROM friends WHERE friend = %s AND contestWatch=True"
	res = queryDB(query, (handle,))
	return [row[0] for row in res]

def getAllChatPartners():
	query = "SELECT chatId FROM tokens"
	res = queryDB(query, ())
	ret = []
	for x in res:
		ret.append(x[0])
	return ret

def toggleFriendSettings(chatId, friend, column):
	with friendsNotfLock:
		query = f"SELECT {column} contestWatch FROM friends WHERE chatId = %s AND friend = %s"
		gesetzt = str(queryDB(query, (chatId, friend))[0][0]) == '1'
		newVal = not gesetzt
		query = f"UPDATE friends SET {column}= %s WHERE chatId = %s AND friend = %s"
		insertDB(query, (newVal, chatId, friend))
		return newVal

