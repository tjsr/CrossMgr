import os
import sys
import pickle

import SeriesModel
import Results

def CmdLine( args ):
	
	seriesFileName = None
	if args.series: 
		seriesFileName = args.series
		ext = os.path.splitext( seriesFileName )
		if ext != '.smn':
			print( 'series file "{}" lacks .smn extension.'.format(seriesFileName), file=sys.stderr )
			return 1
		try:
			with open(seriesFileName, 'rb') as fp:
				SeriesModel.model = pickle.load( fp, encoding='latin1', errors='replace' )
		except IOError:
			print( 'cannot open series file "{}".'.format(seriesFileName), file=sys.stderr )
			return 1
		SeriesModel.model.postReadFix()

	races = []
	for r in args.races:
		# Parse the points structure.
		pos = r.rfind( '=' )
		if pos >= 0:
			pointStructuresName = r[pos+1:].strip()
			r = r[:pos]
		else:
			pointStructuresName = None

		fileName, sheetName = None, None
		
		# Now, parse the file reference.
		if r.endswith( '.cmn' ):
			# This is a crossmgr file.
			fileName = r
		else:
			# This must be a spreadsheet.
			components = r.split( '::' )
			if len(components) == 2:
				fileName, sheetName = components
			else:
				fileName = components[0]
			if not any( fileName.endswith(suffix) for suffix in ('.xlsx', 'xlsm', '.xls') ):
				print( 'unrecognized file suffix "{}".'.format(fileName), file=sys.stderr )
				return 2
				
		pointStructures = None
		for ps in SeriesModel.model.pointStructures:
			if pointStructuresName is None or ps.name == pointStructuresName:
				pointStructures = ps
				break
				
		if pointStructures is None:
			print( 'cannot find points structure "{}".'.format(pointStructuresName), file=sys.stderr )
			return 3
		
		races.append( SeriesModel.Race(fileName, pointStructures) )
		
	if races:
		SeriesModel.model.races = races
			
	score_by_points, score_by_time, score_by_percent = True, False, False
	if args.score_by_time:
		score_by_points, score_by_time, score_by_percent = False, True, False
	if args.score_by_percent:
		score_by_points, score_by_time, score_by_percent = False, False, True
		
	output_file = args.output or ((os.path.splitext(args.series)[0] + '.html') if args.series else 'SeriesMgr.html')
	SeriesModel.model.extractAllRaceResults()
	with open( output_file, 'w', encoding='utf8' ) as f:
		f.write( Results.getHtml(seriesFileName) )
	
	return 0
