import wx
import sys
import bisect
import operator
import itertools
import Utils
import Model
from Utils import formatTime, formatTimeGap, SetLabel
from Utils import logException
import ColGrid
import StatusBar
import OutputStreamer
import NumKeypad
from PhotoFinish import TakePhoto, okTakePhoto
from GetResults import GetResults, GetResultsWithData, IsRiderFinished
from EditEntry import CorrectNumber, SplitNumber, ShiftNumber, InsertNumber, DeleteEntry, DoDNS, DoDNF, DoPull
from FixCategories import SetCategory
from FtpWriteFile import realTimeFtpPublish
from GridHoverRow import AugmentGridHoverRow

def getExpectedRecorded( tCutoff=0.0 ):
	race = Model.race
	if not race:
		return [], []
	Entry = Model.Entry
	Finisher = Model.Rider.Finisher
	bisect_left = bisect.bisect_left
	
	tCur = race.lastRaceTime()
	
	expected, recorded, resultsIndex = [], [], {}
	
	results = GetResults( None )
	
	considerStartTime = (race.isTimeTrial or (race.resetStartClockOnFirstTag and race.enableJChipIntegration))
	
	if considerStartTime:
		Finisher = Model.Rider.Finisher
		NP = Model.Rider.NP
		if race.isTimeTrial:
			bibsWithoutResults = set( rr.num for rr in results if rr.status == NP )
		else:
			bibsWithoutResults = set( rr.num for rr in results if rr.status == Finisher and not rr.lapTimes )
		
		# Include the rider's start time.  This is will not be in the results if there are no results yet.
		interpValue = race.isTimeTrial
		
		for bib in bibsWithoutResults:
			rider = race.riders[bib]
			if rider.status == Finisher and rider.firstTime is not None:
				e = Entry( rider.num, 0, rider.firstTime, interpValue )
				if rider.firstTime >= tCur and e.interp:
					expected.append( e )
				else:
					recorded.append( e )
	
	lapMin = 1
	for rr in results:
		resultsIndex[rr.num] = rr
		if not rr.raceTimes or rr.status != Finisher:
			continue
		offset = (getattr(rr,'startTime',None) or 0.0) if race.isTimeTrial else 0.0
		
		i = bisect_left( rr.raceTimes, tCur - offset )
		
		# Get the next expected lap.  Consider that the rider could have been missed from the last lap.
		try:
			lap = i
			if lap > 1 and rr.interp[lap-1] and rr.raceTimes[lap-1] + offset >= tCutoff:
				lap -= 1
			t = rr.raceTimes[lap] + offset if rr.interp[lap] else None
		except IndexError:
			t = None
		if t is not None and lap >= lapMin:
			expected.append( Entry(rr.num, lap, t, rr.interp[lap]) )
		
		# Get the last recorded lap.
		try:
			lap = i - 1
			while lap > 0 and rr.interp[lap] and rr.raceTimes[lap-1] + offset >= tCutoff:
				lap -= 1
			t = rr.raceTimes[lap] + offset if (lap == 0 or not rr.interp[lap]) else None
		except IndexError:
			t = None
		if t is not None and lap >= lapMin:
			recorded.append( Entry(rr.num, lap, t, rr.interp[lap]) )
	
	expected.sort( key=Entry.key )
	recorded.sort( key=Entry.key )
	return expected, recorded, resultsIndex
	
# Define columns for recorded and expected grids.
iRecordedNumCol, iRecordedNoteCol, iRecordedTimeCol, iRecordedGapCol, iRecordedLapCol, iRecordedNameCol, iRecordedWaveCol, iRecordedColMax = range(8)
recordedColnames = [None] * iRecordedColMax
recordedColnames[iRecordedNumCol]  = _('Bib')
recordedColnames[iRecordedNoteCol] = _('Note')
recordedColnames[iRecordedTimeCol] = _('Time')
recordedColnames[iRecordedGapCol]  = _('Gap')
recordedColnames[iRecordedLapCol]  = _('Lap')
recordedColnames[iRecordedNameCol] = _('Name')
recordedColnames[iRecordedWaveCol] = _('Wave')

iExpectedNumCol, iExpectedNoteCol, iExpectedTimeCol, iExpectedLapCol, iExpectedNameCol, iExpectedWaveCol, iExpectedColMax = range(7)
expectedColnames = [None] * iExpectedColMax
expectedColnames[iExpectedNumCol]  = _('Bib')
expectedColnames[iExpectedNoteCol] = _('Note')
expectedColnames[iExpectedLapCol]  = _('Lap')
expectedColnames[iExpectedTimeCol] = _('ETA')
expectedColnames[iExpectedNameCol] = _('Name')
expectedColnames[iExpectedWaveCol] = _('Wave')

fontSize = 11

def GetLabelGrid( parent, bigFont=False, colnames=[], leftAlignCols=[] ):
	font = wx.Font( fontSize + (fontSize//3 if bigFont else 0), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL )
	dc = wx.WindowDC( parent )
	dc.SetFont( font )
	w, h = dc.GetTextExtent( '999' )

	label = wx.StaticText( parent, label = '{}:'.format(_('Recorded')) )
	
	grid = ColGrid.ColGrid( parent, colnames = colnames )
	AugmentGridHoverRow( grid )
	grid.SetLeftAlignCols( leftAlignCols )
	grid.SetRowLabelSize( 0 )
	grid.SetRightAlign( True )
	grid.AutoSizeColumns( True )
	grid.DisableDragColSize()
	grid.DisableDragRowSize()
	grid.SetDefaultCellFont( font )
	grid.SetDefaultRowSize( int(h * 1.15), True )
	grid.SetSelectionBackground( wx.Colour(200,200,200) )
	grid.SetSelectionForeground( wx.Colour(  0,  0,  0) )
	return label, grid
		
class LabelGrid( wx.Panel ):
	def __init__( self, parent, id=wx.ID_ANY, style=0, bigFont=False, colnames=[], leftAlignCols=[] ):
		super().__init__(parent, id, style=style)
		
		bsMain = wx.BoxSizer( wx.VERTICAL )
		
		self.label, self.grid = GetLabelGrid( self, bigFont, colnames, leftAlignCols )
		bsMain.Add( self.label, 0, flag=wx.ALL, border=4 )
		bsMain.Add( self.grid, 1, flag=wx.ALL|wx.EXPAND, border = 4 )
		
		self.SetSizer( bsMain )
		self.Layout()

class ForecastHistory( wx.Panel ):
	def __init__( self, parent, id = wx.ID_ANY, style = 0 ):
		super().__init__(parent, id, style=style)
		
		self.quickRecorded = None
		self.quickExpected = None
		self.entryCur = None
		self.orangeColour = wx.Colour(255, 165,   0)
		self.redColour    = wx.Colour(255,  51,  51)
		self.groupColour  = wx.Colour(220, 220, 220)

		self.callFutureRefresh = None
		self.SetDoubleBuffered( True )
		
		# Main sizer.
		bsMain = wx.BoxSizer( wx.VERTICAL )
		
		# Put Recorded and Expected in a splitter window.
		self.splitter = wx.SplitterWindow( self )
		
		self.lgExpected = LabelGrid( self.splitter, style=wx.BORDER_SUNKEN, bigFont=True,
			colnames=expectedColnames, leftAlignCols=[iExpectedNameCol,iExpectedWaveCol] )
		self.expectedName = self.lgExpected.label
		self.expectedGrid = self.lgExpected.grid
		self.expectedName.SetLabel( _('Expected (click Bib to record entry)') )
		self.expectedGrid.SetDefaultCellBackgroundColour( wx.Colour(230,255,255) )
		self.Bind( wx.grid.EVT_GRID_SELECT_CELL, self.doExpectedSelect, self.expectedGrid )
		self.Bind( wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.doExpectedPopup, self.expectedGrid )	
				
		self.lgHistory = LabelGrid( self.splitter, style=wx.BORDER_SUNKEN,
			colnames=recordedColnames, leftAlignCols=[iRecordedNameCol,iRecordedWaveCol] )
		self.historyName = self.lgHistory.label
		self.historyName.SetLabel( _('Recorded') )
		self.historyGrid = self.lgHistory.grid
		self.Bind( wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.doNumDrilldown, self.historyGrid )
		self.Bind( wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.doHistoryPopup, self.historyGrid )
		
		self.splitter.SetMinimumPaneSize( 4 )
		self.splitter.SetSashGravity( 0.5 )
		self.splitter.SplitHorizontally( self.lgExpected, self.lgHistory, 100 )
		self.Bind( wx.EVT_SPLITTER_DCLICK, self.doSwapOrientation, self.splitter )
		
		bsMain.Add( self.splitter, 1, flag=wx.EXPAND | wx.ALL, border = 4 )
				
		self.historyGrid.Reset()
		self.expectedGrid.Reset()
		
		self.SetSizer( bsMain )
		self.refresh()
		self.Layout()
		
	def setSash( self ):
		size = self.GetClientSize()
		if self.splitter.GetSplitMode() == wx.SPLIT_VERTICAL:
			self.splitter.SetSashPosition( size.width // 2 )
		else:
			self.splitter.SetSashPosition( size.height // 2 )

	def swapOrientation( self ):
		width = 285
		if self.splitter.GetSplitMode() == wx.SPLIT_VERTICAL:
			self.splitter.SetSplitMode( wx.SPLIT_HORIZONTAL )
			mainWin = Utils.getMainWin()
			if mainWin:
				mainWin.splitter.SetSashPosition( width )
		else:
			self.splitter.SetSplitMode( wx.SPLIT_VERTICAL )
			mainWin = Utils.getMainWin()
			if mainWin:
				mainWin.splitter.SetSashPosition( width * 2 )
		self.setSash()
	
	def doSwapOrientation( self, event ):
		self.swapOrientation()
	
	def doNumDrilldown( self, event ):
		with Model.LockRace() as race:
			if not race or not race.isRunning():
				return
		grid = event.GetEventObject()
		row = event.GetRow()
		value = ''
		if row < grid.GetNumberRows():
			value = grid.GetCellValue(row, 0).strip()
		if not value:
			return
		numSelect = value
		mainWin = Utils.getMainWin()
		if mainWin:
			mainWin.setNumSelect( numSelect )
			mainWin.showPage( mainWin.iRiderDetailPage )
	
	def doHistoryPopup( self, event ):
		r = event.GetRow()
		with Model.LockRace() as race:
			if not self.quickRecorded or r >= len(self.quickRecorded) or not race or not race.isRunning() or self.quickRecorded[r].isGap():
				return
		value = ''
		if r < self.historyGrid.GetNumberRows():
			value = self.historyGrid.GetCellValue( r, 0 )
		if not value:
			return
		
		self.entryCur = self.quickRecorded[r]
		if not hasattr(self, 'historyPopupInfo'):
			self.historyPopupInfo = [
				('{}...'.format(_('Correct')),	self.OnPopupHistoryCorrect),
				('{}...'.format(_('Split')),	self.OnPopupHistorySplit),
				('{}...'.format(_('Shift')),	self.OnPopupHistoryShift),
				('{}...'.format(_('Insert')),	self.OnPopupHistoryInsert),
				('{}...'.format(_('Delete')),	self.OnPopupHistoryDelete),
				(None,				    		None),
				('{}...'.format(_('DNF')),		self.OnPopupHistoryDNF),
				(None,				    		None),
				(_('RiderDetail'),				self.OnPopupHistoryRiderDetail),
				(_('Results'),					self.OnPopupHistoryResults),
				(_('Passings'),					self.OnPopupHistoryPassings),
				(_('Chart'),					self.OnPopupHistoryChart),
			]
			
			menu = wx.Menu()
			for name, callback in self.historyPopupInfo:
				if name:
					item = menu.Append( wx.ID_ANY, name )
					self.Bind( wx.EVT_MENU, callback, item )
				else:
					menu.AppendSeparator()
			self.menuHistory = menu
		
		self.PopupMenu( self.menuHistory )
	
	def fixTTEntry( self, e ):
		race = Model.race
		if race and race.isTimeTrial:
			rider = race.riders.get(e.num, None)
			startTime = (getattr(rider,'firstTime',0.0) or 0.0) if rider else 0.0
			return Model.Entry( e.num, e.lap, e.t-startTime, e.interp )
		return e
	
	def OnPopupHistoryCorrect( self, event ):
		if self.entryCur:
			CorrectNumber( self, self.fixTTEntry(self.entryCur) )
		
	def OnPopupHistorySplit( self, event ):
		if self.entryCur:
			SplitNumber( self, self.fixTTEntry(self.entryCur) )
		
	def OnPopupHistoryShift( self, event ):
		if self.entryCur:
			ShiftNumber( self, self.fixTTEntry(self.entryCur) )
		
	def OnPopupHistoryInsert( self, event ):
		if self.entryCur:
			InsertNumber( self, self.fixTTEntry(self.entryCur) )
		
	def OnPopupHistoryDelete( self, event ):
		if self.entryCur:
			DeleteEntry( self, self.fixTTEntry(self.entryCur) )
			
	def OnPopupHistoryDNF( self, event ):
		try:
			num = self.entryCur.num
			NumKeypad.DoDNF( self, num )
		except Exception:
			pass
	
	def SelectNumShowPage( self, num, iPageAttr ):
		race = Model.race
		mainWin = Utils.getMainWin()
		if not race or not mainWin or not num:
			return
		
		mainWin.setNumSelect( num )
			
		# If this page supports a category, make sure we show it too.
		category = None
		CatComponent = Model.Category.CatComponent
		if iPageAttr != 'iPassingsPage':
			# Check Component categories first.
			for c in race.getCategories( startWaveOnly=False ):
				if c.catType == CatComponent and race.inCategory(num, c):
					category = c
					break
			# Then check wave categories.
			if not category:
				for c in race.getCategories( startWaveOnly=True ):
					if race.inCategory(num, c):
						category = c
						break

		# Set the category of the num.
		iPage = getattr(mainWin, iPageAttr, 0)
		a = mainWin.attrClassName[iPage][0]
		try:
			getattr(mainWin, a).setCategory( category )
		except AttributeError:
			pass
		
		mainWin.showPage( iPage )
		
	def OnPopupHistoryRiderDetail( self, event ):
		self.SelectNumShowPage( self.entryCur.num, 'iRiderDetailPage' )
	
	def OnPopupHistoryResults( self, event ):
		self.SelectNumShowPage( self.entryCur.num, 'iResultsPage' )
	
	def OnPopupHistoryPassings( self, event ):
		self.SelectNumShowPage( self.entryCur.num, 'iPassingsPage' )
				
	def OnPopupHistoryChart( self, event ):
		self.SelectNumShowPage( self.entryCur.num, 'iChartPage' )
				
	#--------------------------------------------------------------------
	
	def doExpectedSelect( self, event ):
		race = Model.race
		if not race or not race.isRunning():
			return
		r = event.GetRow()
		value = self.expectedGrid.GetCellValue(r, 0) if r < self.expectedGrid.GetNumberRows() else ''
		if value:
			self.logNum( value )
		
	def doExpectedPopup( self, event ):
		race = Model.race
		if not race or not race.isRunning():
			return
		r = event.GetRow()
		value = self.expectedGrid.GetCellValue(r, 0) if r < self.expectedGrid.GetNumberRows() else ''
		if not value:
			return
		
		value = int(value)
		
		self.entryCur = None
		for k in range(1, 2*max(r, len(self.quickExpected) - r)):
			i = r + (k//2 if k&1 else -k//2)
			if 0 <= i < len(self.quickExpected):
				if self.quickExpected[i].num == value:
					self.entryCur = self.quickExpected[i]
					break
				
		if not self.entryCur:
			return
		
		if not hasattr(self, 'expectedPopupInfo'):
			self.expectedPopupInfo = [
				('{}...'.format(_('DNF')),		self.OnPopupExpectedDNF),
				('{}...'.format(_('Pull')),	self.OnPopupExpectedPull),
				(None,							None),
				(_('RiderDetail'),				self.OnPopupExpectedRiderDetail),
				(_('Results'),					self.OnPopupExpectedResults),
				(_('Passings'),					self.OnPopupExpectedPassings),
				(_('Chart'),					self.OnPopupExpectedChart),
			]

			menu = wx.Menu()
			for name, callback in self.expectedPopupInfo:
				if name:
					item = menu.Append( wx.ID_ANY, name )
					self.Bind( wx.EVT_MENU, callback, item )
				else:
					menu.AppendSeparator()
			self.menuExpected = menu
		
		self.PopupMenu( self.menuExpected )
		
	def OnPopupExpectedEnter( self, event ):
		try:
			num = self.entryCur.num
			self.logNum( num )
		except Exception:
			pass
		
	def OnPopupExpectedDNF( self, event ):
		try:
			num = self.entryCur.num
			NumKeypad.DoDNF( self, num )
		except Exception:
			pass
		
	def OnPopupExpectedPull( self, event ):
		try:
			num = self.entryCur.num
			NumKeypad.DoPull( self, num )
		except Exception:
			pass

	def OnPopupExpectedRiderDetail( self, event ):
		self.SelectNumShowPage( self.entryCur.num, 'iRiderDetailPage' )
	
	def OnPopupExpectedResults( self, event ):
		self.SelectNumShowPage( self.entryCur.num, 'iResultsPage' )
	
	def OnPopupExpectedPassings( self, event ):
		self.SelectNumShowPage( self.entryCur.num, 'iPassingsPage' )
				
	def OnPopupExpectedChart( self, event ):
		self.SelectNumShowPage( self.entryCur.num, 'iChartPage' )
				
	#--------------------------------------------------------------------
	
	def playBlip( self ):
		Utils.PlaySound( 'blip6.wav' )
	
	def logNum( self, nums ):
		if not nums:
			return
		
		race = Model.race
		if not race or not race.isRunning():
			return
		
		t = race.curRaceTime()
		
		if not isinstance(nums, (list, tuple)):
			nums = [nums]
			
		# Add the times to the model.
		numTimes = []
		for num in nums:
			try:
				num = int(num)
			except Exception:
				continue
			race.addTime( num, t, False )
			numTimes.append( (num, t) )
		
		# Write to the log.
		OutputStreamer.writeNumTimes( numTimes )
			
		# Schedule a photo.
		if race.enableUSBCamera:
			for num in nums:
				try:
					num = int(num)
				except Exception:
					continue
				
				race.photoCount += TakePhoto(num, t) if okTakePhoto(num, t) else 0
			
		self.playBlip()
		race.setChanged()
		
		mainWin = Utils.getMainWin()
		if mainWin:
			mainWin.record.keypad.numEdit.SetValue( '' )
			mainWin.record.refreshLaps()
			wx.CallAfter( mainWin.refresh )
		if race.ftpUploadDuringRace:
			realTimeFtpPublish.publishEntry()
		
	def clearGrids( self ):
		self.historyGrid.Set( data = [] )
		self.historyGrid.Reset()
		self.expectedGrid.Set( data = [] )
		self.expectedGrid.Reset()
	
	def getETATimeFunc( self ):
		return operator.attrgetter('t')
	
	def updatedExpectedTimes( self, tRace = None ):
		if not self.quickExpected:
			return
		race = Model.race
		if not tRace:
			tRace = race.curRaceTime()
		getT = self.getETATimeFunc()
		self.expectedGrid.SetColumn(
			iExpectedTimeCol,
			[formatTime(getT(e) - tRace) if (e.lap or 0) > 0 else ('[{}]'.format(formatTime(max(0.0, getT(e) - tRace + 0.0000001)))) for e in self.quickExpected]
		)
	
	def addGaps( self, recorded ):
		if not (Model.race and Model.race.enableJChipIntegration):
			return recorded
		
		recordedWithGaps = []
		groupCount = 0
		Entry = Model.Entry
		for i, e in enumerate(recorded):
			if i and e.t - recorded[i-1].t > 1.0:
				recordedWithGaps.append( Entry(-groupCount, None, e.t - recorded[i-1].t, True) )
				groupCount = 0
			recordedWithGaps.append( e )
			groupCount += 1
		if groupCount:
			recordedWithGaps.append( Model.Entry(-groupCount, None, None, True) )
		return recordedWithGaps

	def updateFuture( self, milliSeconds ):
		if self.callFutureRefresh is None:
			def doUpdate():
				self.refresh()
				if Utils.mainWin:
					Utils.mainWin.refreshTTStart()
			class RefreshTimer( wx.Timer ):
				def Notify( self ):
					wx.CallAfter( doUpdate )
			self.callFutureRefresh = RefreshTimer()
		
		if not self.callFutureRefresh.IsRunning():
			self.callFutureRefresh.StartOnce( milliSeconds )

	def refresh( self ):
		race = Model.race
		if race is None or not race.isRunning():
			self.quickExpected = None
			self.clearGrids()
			return
			
		try:
			externalInfo = race.excelLink.read( True )
		except Exception:
			externalInfo = {}
					
		tRace = race.curRaceTime()
		tRaceLength = race.minutes * 60.0
		
		expected, recorded, resultsIndex = getExpectedRecorded()
		
		isTimeTrial = race.isTimeTrial
		if isTimeTrial:
			try:
				e = next( e for e in expected if (e.lap or 0) == 0 )
			except StopIteration:
				e = None
			if e:
				# Schedule a refresh update riders as they start.
				milliSeconds = int(((e.t or 0.0) - tRace)*1000.0 + 10.0)
				if milliSeconds > 0:
					self.updateFuture( milliSeconds )

		#------------------------------------------------------------------
		# Highlight interpolated entries at race time.
		leaderPrev, leaderNext = race.getPrevNextLeader( tRace )
		averageLapTime = race.getAverageLapTime()
		
		expectedShowMax = 80
		
		expected = expected[:expectedShowMax]
		
		#-----------------------------------------------------------
		nextCatLeaders = {}
		prevRiderPosition, nextRiderPosition = {}, {}
		prevRiderGap = {}
		
		if race.riders and race.isRunning():
			Finisher = Model.Rider.Finisher
			for c in race.getCategories(startWaveOnly=True):
				results = GetResultsWithData( c )
				if not results:
					continue
				rr = results[0]
				if rr.status != Finisher:
					continue
				nextCatLeaders[rr.num] = c
				for pos, rr in enumerate(results, 1):
					if rr.status != Finisher:
						break
					prevRiderPosition[rr.num] = nextRiderPosition[rr.num] = pos
					prevRiderGap[rr.num] = rr.gap
	
		#-----------------------------------------------------------
		
		backgroundColour = {}
		textColour = {}
		#------------------------------------------------------------------
		# Highlight the missing riders.
		tMissing = tRace - averageLapTime / 8.0
		iNotMissing = 0
		for r in (i for i, e in enumerate(expected) if e.t < tMissing):
			for c in range(iExpectedColMax):
				backgroundColour[(r, c)] = self.orangeColour
			iNotMissing = r + 1
			
		#------------------------------------------------------------------
		# Highlight the leaders in the expected list.
		iBeforeLeader = None
		# Highlight the leader by category.
		catNextTime = {}
		outsideTimeBound = set()
		for r, e in enumerate(expected):
			if e.num in nextCatLeaders:
				backgroundColour[(r, iExpectedNoteCol)] = wx.GREEN
				catNextTime[nextCatLeaders[e.num]] = e.t
				if e.num == leaderNext:
					backgroundColour[(r, iExpectedNumCol)] = wx.GREEN
					iBeforeLeader = r
			elif tRace < tRaceLength and race.isOutsideTimeBound(e.num):
				backgroundColour[(r, iExpectedNoteCol)] = self.redColour
				textColour[(r, iExpectedNoteCol)] = wx.WHITE
				outsideTimeBound.add( e.num )
		
		data = [None] * iExpectedColMax
		data[iExpectedNumCol] = ['{}'.format(e.num) for e in expected]
		getT = self.getETATimeFunc()
		data[iExpectedTimeCol] = [formatTime(getT(e) - tRace) if (e.lap or 0) > 0
			else ('[{}]'.format(formatTime(max(0.0, getT(e) - tRace + 0.99999999)))) for e in expected]
		data[iExpectedLapCol] = ['{}'.format(e.lap) if (e.lap or 0) > 0 else '' for e in expected]
		
		def getNoteExpected( e ):
			if (e.lap or 0) == 0:
				return _('Start')
			try:
				position =(prevRiderPosition.get(e.num, -1) if e.t < catNextTime[race.getCategory(e.num)] else
						   nextRiderPosition.get(e.num, -1) )
			except KeyError:
				position = prevRiderPosition.get(e.num, -1)
				
			if position == 1:
				return resultsIndex[e.num].getExpectedLapChar(tRace) + _('Lead')
			elif e.t < tMissing:
				return _('miss')
			elif position >= 0:
				return resultsIndex[e.num].getExpectedLapChar(tRace) + Utils.ordinal(position)
			else:
				return ' '
		
		data[iExpectedNoteCol] = [getNoteExpected(e) for e in expected]
		def getName( e ):
			info = externalInfo.get(e.num, {})
			last = info.get('LastName','')
			first = info.get('FirstName','')
			if last and first:
				return '{}, {}'.format(last, first)
			return last or first or ' '
		data[iExpectedNameCol] = [getName(e) for e in expected]
		
		def getWave( e ):
			try:
				return race.getCategory(e.num).fullname
			except Exception:
				return ' '
		data[iExpectedWaveCol] = [getWave(e) for e in expected]
		
		self.quickExpected = expected
		
		self.expectedGrid.Set( data = data, backgroundColour = backgroundColour, textColour = textColour )
		self.expectedGrid.AutoSizeColumns()
		self.expectedGrid.AutoSizeRows()
		
		if iBeforeLeader:
			Utils.SetLabel( self.expectedName, '{}: {} {}'.format(_('Expected'), iBeforeLeader, _('before race leader')) )
		else:
			Utils.SetLabel( self.expectedName, _('Expected (click Bib to record entry)') )
		
		#------------------------------------------------------------------
		# Update recorded.
		recorded = self.quickRecorded = self.addGaps( recorded )
			
		backgroundColour = {}
		textColour = {}
		outsideTimeBound = set()
		# Highlight the leader in the recorded list.
		for r, e in enumerate(recorded):
			if e.isGap():
				for i in range( iRecordedColMax ):
					backgroundColour[(r, i)] = self.groupColour
			if prevRiderPosition.get(e.num,-1) == 1:
				backgroundColour[(r, iRecordedNoteCol)] = wx.GREEN
				if e.num == leaderPrev:
					backgroundColour[(r, iRecordedNumCol)] = wx.GREEN
			elif tRace < tRaceLength and race.isOutsideTimeBound(e.num):
				backgroundColour[(r, iRecordedNoteCol)] = self.redColour
				textColour[(r, iRecordedNoteCol)] = wx.WHITE
				outsideTimeBound.add( e.num )
								
		data = [None] * iRecordedColMax
		data[iRecordedNumCol] = ['{}{}'.format(e.num,"\u2190" if IsRiderFinished(e.num, e.t) else '') if e.num > 0 else ' ' for e in recorded]
		data[iRecordedTimeCol] = [
			formatTime(e.t) if (e.lap or -1) > 0 else
			('{}'.format(formatTimeGap(e.t)) if e.t is not None else ' ') if e.isGap() else
			'[{}]'.format(formatTime(e.t)) for e in recorded]
		data[iRecordedLapCol] = ['{}'.format(e.lap) if e.lap else ' ' for e in recorded]
		
		def getNoteHistory( e ):
			if e.isGap():
				return '{}'.format(e.groupCount)
			
			if (e.lap or 0) == 0:
				return _('Start')

			position = nextRiderPosition.get(e.num, -1)
			if position == 1:
				return resultsIndex[e.num].getRecordedLapChar(tRace) + _('Lead')
			elif position >= 0:
				return resultsIndex[e.num].getRecordedLapChar(tRace) + Utils.ordinal(position)
			else:
				return ' '
		
		data[iRecordedNoteCol] = [getNoteHistory(e) for e in recorded]
		def getGapHistory( e ):
			if (e.lap or 0) == 0:
				return ' '
			return prevRiderGap.get(e.num, '')
		data[iRecordedGapCol] = [getGapHistory(e) for e in recorded]
		data[iRecordedNameCol] = [getName(e) for e in recorded]
		data[iRecordedWaveCol] = [getWave(e) for e in recorded]

		self.historyGrid.Set( data = data, backgroundColour = backgroundColour, textColour = textColour )
		self.historyGrid.AutoSizeColumns()
		self.historyGrid.AutoSizeRows()
		
		# Show the relevant cells in each table.
		if recorded:
			self.historyGrid.MakeCellVisible( len(recorded)-1, 0 )
		if iNotMissing < self.expectedGrid.GetNumberRows():
			self.expectedGrid.MakeCellVisible( iNotMissing, 0 )

if __name__ == '__main__':
	app = wx.App(False)
	mainWin = wx.Frame(None,title="CrossMan", size=(600,400))
	
	fh = ForecastHistory(mainWin)
	Model.setRace( Model.Race() )
	Model.getRace()._populate()
	for i, rider in enumerate(Model.getRace().riders.values()):
		rider.firstTime = i * 30.0
	Model.getRace().isTimeTrial = True
	fh.refresh()
	mainWin.Show()
	fh.setSash()
	fh.swapOrientation()
	app.MainLoop()
