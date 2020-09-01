import queue, time, random, re
from collections import defaultdict
import threading

from utils import database as db
from telegram import telegram as tg
from codeforces import codeforces as cf
from utils import util
from utils.util import logger
from services import AnalyseStandingsService, UpcomingService, SummarizingService
from codeforces import standings, upcoming
from commands import settings
from telegram import Chat

#funs[pref](chat, suff, callback)
def handleChatCallback(chat, data, callback):
	pass
