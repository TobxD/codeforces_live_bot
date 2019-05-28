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
      util.log(traceback.format_exc())
      return False

  for key in sorted(params):
    tailPart += key + '=' + str(params[key]) + '&'
  request = codeforcesUrl

  if authorized:
    hsh = util.sha512Hex(rnd + '/' + tailPart[:-1] + '#' + secret) # ignore last '&'
    tailPart += 'apiSig=' + rnd + hsh
  request += tailPart
  r = requests.get(request, timeout=5)
  r = r.json()
  if r['status'] == 'OK':
    return r['result']
  else:
    return False

def getUserInfos(userNameArr):
  usrList = ';'.join(userNameArr)
  util.log('requesting info of ' + str(len(userNameArr)) + ' users ')
  r = sendRequest('user.info', {'handles':usrList})
  util.log('requesting infos finished')
  return r

def getUserRating(handle):
  info = cf.getUserInfos([handle])
  if info == False:
    return 0
  return info[0]["rating"]

def getFriendsWithDetails(chatId):
  global friendsLastUpdated
  if time.time() - friendsLastUpdated.get(chatId, 0) > 1200:
    p = {}
    p['onlyOnline'] = 'false'
    util.log('request friends of user with chat_id ' + str(chatId))
    f = sendRequest("user.friends", p, True, chatId)
    util.log('requesting friends finished')
    if f != False:
      db.addFriends(chatId, f)
      friendsLastUpdated[chatId] = time.time()
      util.log('friends updated for user ' + str(chatId))
  return db.getFriends(chatId)

def getFriends(chatId):
  friends = getFriendsWithDetails(chatId)
  return [f[0] for f in friends if f[1] == 1] # only output if ratingWatch is enabled

def getStandings(contestId, handleList):
  handleString = ";".join(handleList)
  util.log('request standings for contest ' + str(contestId) + ' for ' + str(len(handleList)) + ' users')
  standings = sendRequest('contest.standings', {'contestId':contestId, 'handles':handleString, 'showUnofficial':True})
  util.log('standings received')
  return standings

aktuelleContests = []
currentContests = []

def getContestStatus(contest):
  if contest['startTimeSeconds'] >= time.time():
    return 'before'
  elif contest['startTimeSeconds']+contest['durationSeconds'] >= time.time():
    return 'running'
  elif contest['phase'] != 'FINISHED':
    return 'testing'
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
      currentContests.append(c)
    elif status == 'finished' or status == 'testing':
      lastStart = max(lastStart, c.get('startTimeSeconds', -1))
    else:
      aktuelleContests.append(c)
  if len(currentContests) == 0:
    for c in contestList:
      twoDaysOld = time.time()-(c.get('startTimeSeconds', -2)+c.get('durationSeconds', -2)) > 60*60*24*2
      if c.get('startTimeSeconds', -2) == lastStart or (not twoDaysOld):
        aktuelleContests.append(c)
        currentContests.append(c)

def loadCurrentContests():
  util.log('loading current contests')
  allContests = sendRequest('contest.list', {'gym':'false'})
  selectImportantContests(allContests)
  util.log('loding contests finished')

def getCurrentContests():
  selectImportantContests(aktuelleContests)
  return currentContests

def getCurrentContestsId():
  return [c['id'] for c in getCurrentContests()]

def getFutureContests():
  res = []
  for c in aktuelleContests:
    if c.get('startTimeSeconds', -1) > time.time():
      res.append(c)
  return res
