import threading
import time
import traceback
import util

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
				traceback.print_exc()
				util.log(traceback.format_exc(), isError=True)
			lastTime = time.time()

	def _doTask(self): #to be overridden
		pass
