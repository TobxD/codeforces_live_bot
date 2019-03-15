import json, requests, time
import sys, traceback, random, hashlib
import database as db
import util

codeforcesUrl = 'https://codeforces.com/api/'
friendsLastUpdated = {}

def sendRequest(method, params, authorized = False, chatId = -1):
  rnd = random.randint(0, 100000)
  rnd = str(rnd).zfill(6)
  tailPart = method + '?'


  if authorized:
    try:
      key, secret = db.getAuth(chatId)
      params['apiKey'] = key
      params['time'] = str(int(time.time()))
    except Exception as e:
      return False

  for key in sorted(params):
    tailPart += key + '=' + str(params[key]) + '&'
  request = codeforcesUrl

  if authorized:
    hsh = util.sha512Hex(rnd + '/' + tailPart[:-1] + '#' + secret) # ignore last '&'
    tailPart += 'apiSig=' + rnd + hsh
  request += tailPart
  r = requests.get(request)
  r = r.json()
  if r['status'] == 'OK':
    return r['result']
  else:
    return False

def getUserInfos(userNameArr):
  usrList = ';'.join(userNameArr)
  r = sendRequest('user.info', {'handles':usrList})
  return r

def getFriendsWithDetails(chatId):
  if time.time() - friendsLastUpdated.get(chatId, 0) > 1200:
    p = {}
    p['onlyOnline'] = 'false'
    f = sendRequest("user.friends", p, True, chatId)
    if f != False:
      db.addFriends(chatId, f)
      friendsLastUpdated['userId'] = time.time()
      util.log('friends updated for user ' + str(chatId))
  return db.getFriends(chatId)

def getFriends(chatId):
  friends = getFriendsWithDetails(chatId)
  return [f[0] for f in friends if f[1] == 1] # only output if ratingWatch is enabled

def getStandings(contestId, handleList):
  handleString = ";".join(handleList)
  return sendRequest('contest.standings', {'contestId':contestId, 'handles':handleString, 'showUnofficial':True})

aktuelleContests = []
currentContests = []

def getContestStatus(contest):
  if contest['startTimeSeconds'] >= time.time():
    return 'before'
  elif contest['startTimeSeconds']+contest['durationSeconds'] >= time.time():
    return 'running'
  else:
    return 'finished'

def selectImportantContests(contestList):
  global aktuelleContests
  global currentContests
  lastStart = 0
  currentContests = []
  aktuelleContests = []
  for c in contestList:
    status = getContestStatus(c)
    if status == 'running':
      aktuelleContests.append(c)
      currentContests.append(c['id'])
    elif status == 'finished':
      lastStart = max(lastStart, c.get('startTimeSeconds', -1))
    else:
      aktuelleContests.append(c)
  if len(currentContests) == 0:
    for c in contestList:
      if c.get('startTimeSeconds', -2) == lastStart:
        aktuelleContests.append(c)
        currentContests.append(c['id'])

def loadCurrentContests():
  util.log('loading current contests')
  allContests = sendRequest('contest.list', {'gym':'false'})
  selectImportantContests(allContests)
  util.log('loding contests finished')

def getCurrentContests():
  #return [1114]
  return [1133]
  global aktuelleContests
  global currentContests
  selectImportantContests(aktuelleContests)
  return currentContests
