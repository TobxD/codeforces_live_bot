import mysql.connector
import util

db_creds = None

def openDB():
  global db_creds
  if db_creds == None:
    db_creds = [line.rstrip('\n') for line in open('.database_creds')]
  db = mysql.connector.connect(user=db_creds[0], password=db_creds[1], host=db_creds[2], port=db_creds[3], database=db_creds[4])
  return db

def queryDB(query, params):
  util.log("start db query: " + query)
  db = openDB()
  cursor = db.cursor()
  cursor.execute(query, params)
  res = cursor.fetchall()
  db.close()
  util.log("db query finished")
  return res

def insertDB(query, params):
  if len(params) == 0:
    return
  db = openDB()
  cursor = db.cursor()
  cursor.execute(query, params)
  db.commit()
  db.close()

def getAuth(chatId):
  query = "SELECT apikey, secret FROM tokens WHERE chatId = %s"
  res = queryDB(query, (chatId,))
  return res[0][0], res[0][1]

def setApiKey(chatId, apikey):
  query = "INSERT INTO tokens (chatId, apikey) VALUES (%s, %s) ON DUPLICATE KEY UPDATE apikey = %s"
  insertDB(query, (chatId, apikey, apikey))

def setApiSecret(chatId, secret):
  query = "INSERT INTO tokens (chatId, secret) VALUES (%s, %s) ON DUPLICATE KEY UPDATE secret = %s"
  insertDB(query, (chatId, secret, secret))

def setTimezone(chatId, tz):
  query = "INSERT INTO tokens (chatId, timezone) VALUES (%s, %s) ON DUPLICATE KEY UPDATE timezone = %s"
  insertDB(query, (chatId, tz, tz))

def setUserHandle(chatId, handle):
  query = "INSERT INTO tokens (chatId, handle) VALUES (%s, %s) ON DUPLICATE KEY UPDATE handle = %s"
  insertDB(query, (chatId, handle, handle))

def setFriendSettings(chatId, friend, column, value):
  query = "UPDATE friends SET "+column+ "= %s WHERE chatId = %s AND friend = %s"
  insertDB(query, (value, chatId, friend))

def hasHandle(chatId):
  query = "SELECT handle from tokens WHERE chatId = %s"
  res = queryDB(query, (chatId,))
  return res and len(res) > 0 and res[0][0]

def getHandle(chatId):
  query = "SELECT handle from tokens WHERE chatId = %s"
  res = queryDB(query, (chatId,))
  return res[0][0] if res and len(res) > 0 else None

def getChatId(handle):
  query = "SELECT chatId from tokens WHERE handle = %s"
  res = queryDB(query, (handle,))
  return res[0][0] if res and len(res) > 0 else None

def getUserTimezone(chatId):
  query = "SELECT timezone from tokens WHERE chatId = %s"
  res = queryDB(query, (chatId,))
  if res and len(res) > 0:
    return res[0][0]
  return "UTC"

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
