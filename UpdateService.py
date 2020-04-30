import threading
import time
from util import logger

class UpdateService (threading.Thread):
	def __init__(self, updateInterval):
		threading.Thread.__init__(self)
		self._updateInterval = updateInterval

	def run(self):
		lastTime = -1
		while True:
			waitTime = lastTime + self._updateInterval - time.time()
			if waitTime > 0:
				time.sleep(waitTime)
			try:
				self._doTask()
			except Exception as e:
				logger.critical('Run error %s', e, exc_info=True)
			lastTime = time.time()

	def _doTask(self): #to be overridden
		pass
