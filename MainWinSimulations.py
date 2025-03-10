import copy
import datetime
import os
import random
import shutil
from abc import ABC, abstractmethod
from collections import defaultdict

import xlsxwriter
import wx

import ChipReader
import Model
import OutputStreamer
import SimulationLapTimes
import Utils
import WebServer
from CrossMgrPageController import CrossMgrPageController
from SimulateData import SimulateData
from SimulateDialog import SimulateDialog
from Undo import undo

from ReadSignOnSheet import SignOnSheetExcelLink

class MainWinCalls(ABC):
	def __init__(self):
		pass

	@abstractmethod
	def closeFindDialog( self ) -> None:
		pass

	@abstractmethod
	def menuPublishHtmlTTStart(self, event=None, silent: bool=False) -> None:
		pass

	@abstractmethod
	def showPage( self, iPage, commitFirst=True ) -> None:
		pass

	@abstractmethod
	def refresh( self ) -> None:
		pass

	@abstractmethod
	def showResultsPage( self ) -> None:
		pass

	@abstractmethod
	def updateLapCounter( self, labels=None ) -> None:
		pass

	@abstractmethod
	def updateRaceClock(self, event=None) -> None:
		pass

	@abstractmethod
	def updateRecentFiles( self ) -> None:
		pass

	@abstractmethod
	def writeRace( self, doCommit = True ):
		pass


class IMainWinSimulations(ABC):
	@abstractmethod
	def addSimulateMenuItem(self, toolsMenu: wx.Menu):
		pass


class MainWinSimulations(IMainWinSimulations, ABC):
	__calls: MainWinCalls
	__frame: wx.Frame
	__page_controller: CrossMgrPageController

	def __init__(self, calls: MainWinCalls | wx.Frame, controller: CrossMgrPageController):
		super().__init__()
		self.__frame = calls
		self.__calls = calls
		self.__page_controller = controller

		self.__simulateSeen = set()

	def Bind(self, event, handler, *args, **kwargs):
		return self.__frame.Bind(event, handler, *args, **kwargs)

	def addSimulateMenuItem(self, toolsMenu: wx.Menu):
		item = toolsMenu.Append( wx.ID_ANY, _("&Simulate Race..."), _("Simulate a race") )
		self.Bind(wx.EVT_MENU, self.menuSimulate, item )

	def genTimes(self, regen=False):
		if regen:
			for k, v in SimulateData(200, 40).items():
				setattr(self, k, v)
		else:
			self.raceMinutes = SimulationLapTimes.raceMinutes
			self.lapTimes = copy.copy(SimulationLapTimes.lapTimes)

			self.riderInfo = None
			self.categories = [
				{'name': 'Junior', 'catStr': '100-199', 'startOffset': '00:00', 'distance': 0.5, 'gender': 'Men'},
				{'name': 'Senior', 'catStr': '200-299', 'startOffset': '00:10', 'distance': 0.5, 'gender': 'Women',
				 'raceMinutes': 6}
			]

			# Add some out-of-category numbers to test.
			for e in range(10, 50, 10):
				self.lapTimes[e] = (self.lapTimes[e][0], 1111 + e)

		return self.lapTimes

	def updateSimulation(self, num):
		if Model.race is None:
			return

		'''
		if self.nextNum is not None and self.nextNum not in self.simulateSeen:
			self.forecastHistory.logNum( self.nextNum )

		with Model.LockRace() as race:
			if race.curRaceTime() > race.minutes * 60.0:
				self.simulateSeen.add( self.nextNum )

		try:
			t, self.nextNum = self.lapTimes.pop()
			with Model.LockRace() as race:
				if t < (self.raceMinutes*60.0 + race.getAverageLapTime()*1.5):
					self.simulateTimer.Restart( int(max(1,(t - race.curRaceTime()) * 1000)), True )
					return
		except IndexError:
			pass
		'''

		race = Model.race
		aveLapTime = race.getAverageLapTime()
		curRaceTime = race.curRaceTime()
		tRaceEnd = self.raceMinutes * 60.0 + aveLapTime * 1.5
		nums = []
		while self.lapTimes:
			t, nextNum = self.lapTimes[-1]
			if t < curRaceTime:
				self.lapTimes.pop()
				if t < tRaceEnd:
					nums.append(nextNum)
				else:
					self.__simulateSeen.add(nextNum)
			else:
				break

		if nums:
			self.forecastHistory.logNum(nums)

		if self.lapTimes:
			self.simulateTimer.Restart(random.randint(200, 600), True)
			return

		self.simulateTimer.Stop()
		nextNum = None
		with Model.LockRace() as race:
			race.finishRaceNow()
		ChipReader.chipReaderCur.CleanupListener()

		OutputStreamer.writeRaceFinish()
		# Give the streamer a chance to write the last message.
		wx.CallLater(2000, OutputStreamer.StopStreamer)

		Utils.writeRace()
		self.__calls.refresh()

	# @logCall
	def menuSimulate(self, event=None, userConfirm=True, isTimeTrial=False):
		# Put simulation in user's home directory.
		simulationDir = os.path.join(os.path.expanduser('~'), 'CrossMgrSimulation')

		# Create the stub of the race so we can get the file name.
		race = Model.Race()
		race.name = 'Simulation'
		race.raceNum = 1
		race.organizer = 'Edward Sitarski'
		race.memo = ''

		race.simulation = True  # Flag this as a simulation race.
		# race.setNoDataDNS = True	# Show all entries in the spreadsheet as NP or DNS.

		fName = os.path.join(simulationDir, race.getFileName())
		if userConfirm:
			with SimulateDialog(self.__frame, fName) as dlg:
				ret = dlg.ShowModal()
				if ret == wx.ID_CANCEL:
					return
				rfidResetStartClockOnFirstTag = dlg.rfidResetStartClockOnFirstTag.GetValue()
				isTimeTrial = (ret == SimulateDialog.ID_TIME_TRIAL)
		else:
			rfidResetStartClockOnFirstTag = False
			isTimeTrial = isTimeTrial

		# Delete any pre-existing Simulation directory.
		try:
			shutil.rmtree(simulationDir, ignore_errors=True)
		except Exception:
			pass

		# Create the simulation directory.
		try:
			os.makedirs(simulationDir)
		except Exception:
			pass

		# Test if we can write something there.
		try:
			with open(fName, 'wb'):
				pass
		except IOError:
			Utils.MessageOK(self, '{} "{}".'.format(_('Cannot open file'), fName), _('File Open Error'),
			                iconMask=wx.ICON_ERROR)
			return

		self.__page_controller.showResultsPage()
		# self.__calls.showResultsPage()  # Switch to a read-only view and force a commit.
		self.__calls.updateLapCounter()
		self.__calls.closeFindDialog()
		self.__calls.refresh()

		# Get the simulation times.
		bigSimulation = False
		self.lapTimes = self.genTimes(bigSimulation)
		tMin = self.lapTimes[0][0]
		self.lapTimes.reverse()  # Reverse the times so we can pop them from the end later.

		# Commit to the new race and file for the simulation.
		undo.clear()
		Model.setRace(race)
		if fName is not None:
			self.__calls.fileName = fName
			WebServer.SetFileName(self.__calls.fileName)
			self.__calls.updateRecentFiles()

		race.isTimeTrial = isTimeTrial
		race.enableUSBCamera = True
		race.minutes = self.raceMinutes
		race.enableJChipIntegration = race.resetStartClockOnFirstTag = rfidResetStartClockOnFirstTag
		race.minPossibleLapTime = 0.0  # Override any defaults so that laps will show up.
		# race.photosAtRaceEndOnly = True

		# Prep the simulation data.
		self.__simulateSeen = set()
		categories = getattr(self, 'categories', None)
		if not categories:
			categories = [
				{'name': 'Junior', 'catStr': '100-199', 'startOffset': '00:00', 'distance': 0.5, 'firstLapDistance': 0.0,
				 'gender': 'Men'},
				{'name': 'Senior', 'catStr': '200-299', 'startOffset': '00:10', 'distance': 0.5, 'firstLapDistance': 0.0,
				 'gender': 'Women', 'raceMinutes': 6}]
		if race.isTimeTrial:
			for c in categories:
				c.pop('raceMinutes', None)
				c['lappedRidersMustContinue'] = True
			categories[0]['numLaps'] = 3
			categories[1]['numLaps'] = 2
			race.setCategories(categories)
			for c in race.getCategories():
				c.distance = 0.5
				c.firstLapDistance = 0.0

			scheduledStart = datetime.datetime.now() + datetime.timedelta(seconds=120)
			scheduledStart -= datetime.timedelta(seconds=scheduledStart.second) + datetime.timedelta(
				seconds=scheduledStart.microsecond / 1000000.0)
			race.scheduledStart = '{:02d}:{:02d}'.format(scheduledStart.hour, scheduledStart.minute)

			nums = set()
			numTimes = defaultdict(list)
			for t, num in self.lapTimes:
				if num < 500:
					nums.add(num)
					numTimes[num].append(t)

			numRaceTimes = {}
			for num, times in numTimes.items():
				times.sort()
				numRaceTimes[num] = [t - times[0] for t in times[1:]]  # Convert race times to zero start.

			timeBeforeFirstRider = 120.0
			startGap = 30.0
			nums = sorted(nums, reverse=True)
			numStartTime = {n: timeBeforeFirstRider + i * startGap for i, n in
			                enumerate(nums)}  # Set start times for all competitors.
			self.lapTimes = []
			for num, raceTimes in numRaceTimes.items():
				startTime = numStartTime[num]
				race.getRider(num).firstTime = startTime
				self.lapTimes.extend([(t + startTime, num) for t in raceTimes])
			self.lapTimes.sort(reverse=True)
		else:
			scheduledStart = datetime.datetime.now()
			race.scheduledStart = '{:02d}:{:02d}'.format(scheduledStart.hour, scheduledStart.minute)

			race.setCategories(categories)
			for c in race.getCategories():
				c.distance = 0.5
				c.firstLapDistance = 0.0

			self.lapTimes = [(t + race.getStartOffset(num), num) for t, num in self.lapTimes]
			if race.enableJChipIntegration and race.resetStartClockOnFirstTag:
				self.lapTimes.extend(
					(race.getStartOffset(num) + 2.0 * random.random(), num) for num in set(tn[1] for tn in self.lapTimes))
				self.lapTimes = [(t + 4.0, num) for t, num in self.lapTimes]
				self.lapTimes.sort(reverse=True)

		# Create an Excel rider data file.
		riderInfo = getattr(self, 'riderInfo', None)
		if not riderInfo:
			riderInfo = []
			fnameInfo = os.path.join(Utils.getImageFolder(), 'NamesTeams.csv')
			try:
				with open(fnameInfo, encoding='iso-8859-1') as fp:
					header = None
					for r, line in enumerate(fp):
						if not header:
							header = line.split(',')
							continue
						riderInfo.append([r + 100] + line.split(','))
			except IOError:
				pass

		if riderInfo:
			fnameRiderInfo = os.path.join(simulationDir, 'SimulationRiderData.xlsx')
			sheetName = 'Registration'
			wb = xlsxwriter.Workbook(fnameRiderInfo)
			ws = wb.add_worksheet(sheetName)
			for c, h in enumerate(['Bib#', 'LastName', 'FirstName', 'Team']):
				ws.write(0, c, h)
			for r, row in enumerate(riderInfo):
				for c, v in enumerate(row):
					ws.write(r + 1, c, v)
			wb.close()

			race.excelLink = SignOnSheetExcelLink()
			race.excelLink.setFileName(fnameRiderInfo)
			race.excelLink.setSheetName(sheetName)
			race.excelLink.setFieldCol({'Bib#': 0, 'LastName': 1, 'FirstName': 2, 'Team': 3})

		# Start the simulation.
		record_page_index = self.__page_controller.get_page_index_by_name('record')
		chart_page_index = self.__page_controller.get_page_index_by_name('chart')

		record_page = self.__page_controller.get_page(record_page_index)
		self.__calls.showPage(self.iRecordPage if isTimeTrial else self.iChartPage)

		self.__calls.showPage(self.iRecordPage if isTimeTrial else self.iChartPage)
		self.record.setTimeTrialInput(race.isTimeTrial)

		ChipReader.chipReaderCur.reset(race.chipReaderType)

		# Start the race.
		self.nextNum = None
		if race.isTimeTrial:
			# If a TT, start the race at the start time in the future.
			def startRaceInFuture(aSelf, aRace):
				aRace.startRaceNow()
				aSelf.simulateTimer = wx.CallLater(1, aSelf.updateSimulation, True)
				OutputStreamer.writeRaceStart()
				wx.CallAfter(self.__calls.refresh)

			wx.CallLater(max(0, int((scheduledStart - datetime.datetime.now()).total_seconds() * 1000.0)), startRaceInFuture,
			             self, race)
			Utils.MessageOK(
				self,
				'{}\n\n{}'.format(_('TT will start automatically in 1-2 minutes'),
				                  _('Review the TTCountdown page (from Web/Index).')),
				_('TT Start'),
			)
			self.__calls.menuPublishHtmlTTStart()
		else:
			# If a Mass Start, start the race now.
			race.startRaceNow()
			if not (race.enableJChipIntegration and race.resetStartClockOnFirstTag):
				# Backup all the events and race start so we don't have to wait for the first lap.
				race.startTime -= datetime.timedelta(seconds=(tMin - 5))
			self.simulateTimer = wx.CallLater(1, self.updateSimulation, True)
			OutputStreamer.writeRaceStart()

		self.__calls.writeRace()
		self.__calls.updateRaceClock()
		self.__calls.refresh()

	def _doCleanup(self) -> None:
		try:
			self.simulateTimer.Stop()
			self.simulateTimer = None
		except AttributeError:
			pass
		except Exception as e:
			Utils.writeLog( 'call: doCleanup: (3) "{}"'.format(e) )
