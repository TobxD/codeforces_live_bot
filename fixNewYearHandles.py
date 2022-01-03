from time import sleep
import urllib
import requests
from utils import database as db

renamed = {}

def renameHandle(oldHandle, newHandle):
  query = "update ignore friends set friend=%s where friend=%s"
  db.insertDB(query, (newHandle, oldHandle))
  query2 = "update tokens set handle=%s where handle=%s"
  db.insertDB(query2, (newHandle, oldHandle))
  query3 = "delete from friends where friend=%s"
  db.insertDB(query3, (oldHandle, ))
  renamed[oldHandle] = newHandle

def requestHandles(handleList):
  handleStr = ";".join(handleList)
  codeforcesUrl = 'https://codeforces.com/api/'
  reqUrl = codeforcesUrl + "user.info?handles=" + urllib.parse.quote(handleStr)
  res = requests.get(reqUrl).json()
  sleep(1)
  startS = "handles: User with handle "
  endS = " not found"
  if 'comment' in res and res['comment'].startswith(startS) and res['comment'].endswith(endS):
    handle = res['comment'][len(startS):-len(endS)]
    #db.deleteFriend(handle)
    return handle
  else:
    return None

def getNewName(handle):
  prefix = "https://codeforces.com/profile/"
  res = requests.get(prefix + handle)
  sleep(1)
  if res.url != "https://codeforces.com/":
    newHandle = res.url[len(prefix):]
    print(handle, "->", newHandle)
    renameHandle(oldHandle=handle, newHandle=newHandle)
    return newHandle
  else:
    print(handle, "not found")
    return None

def getAllHandles():
  print("requesting all friends from DB")
  friends = db.getAllFriends()
  print("requesting all users from DB")
  query = "select distinct handle from tokens"
  users = [x[0] for x in db.queryDB(query, ()) if x[0] != None]
  res = list(set(friends + users))
  print(res[:100])
  return res

def fixBatch(handles):
  curLen = len(handles)
  while True:
    failed = requestHandles(handles)
    if failed is not None:
      getNewName(failed)
    handles = [h for h in handles if h not in renamed]
    newLen = len(handles)
    if newLen == curLen or newLen == 0:
      break
    curLen = newLen

handles = getAllHandles()
batchSize = 200
split = [handles[batchSize*i:batchSize*(i+1)] for i in range((len(handles)+batchSize-1)//batchSize)]
res = []
batchNum = 1
for part in split:
  print("starting batch", batchNum, "/", len(split))
  fixBatch(part)
  batchNum += 1

print(renamed)
print("done")