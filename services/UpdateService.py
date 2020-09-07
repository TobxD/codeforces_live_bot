import threading
import time

from utils.util import logger, perfLogger

class UpdateService (threading.Thread):
	def __init__(self, updateInterval, logPerf=True):
		threading.Thread.__init__(self)
		self._updateInterval = updateInterval
		self._logPerf = logPerf

	def run(self):
		lastTime = -1
		while True:
			waitTime = lastTime + self._updateInterval - time.time()
			if waitTime > 0:
				time.sleep(waitTime)
			try:
				startT = time.time()
				self._doTask()
				if self._logPerf:
					perfLogger.info("service: {:.3f}s".format(time.time()-startT))
			except Exception as e:
				logger.critical('Run error %s', e, exc_info=True)
			lastTime = time.time()

	def _doTask(self): #to be overridden
		pass
