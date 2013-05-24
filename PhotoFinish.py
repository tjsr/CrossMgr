import os
import wx
import sys
import math
import datetime
import Utils
from Version import AppVerName

sys.path.append( Utils.dirName )	# Required for PIL to find the font files.

def formatTime( secs ):
	if secs is None:
		secs = 0
	if secs < 0:
		sign = '-'
		secs = -secs
	else:
		sign = ''
	f, ss = math.modf(secs)
	secs = int(ss)
	hours = int(secs // (60*60))
	minutes = int( (secs // 60) % 60 )
	secs = secs % 60
	decimal = int( f * 1000.0 )
	return "%s%02d:%02d:%02d.%03d" % (sign, hours, minutes, secs, decimal)

def fileFormatTime( secs ):
	return formatTime(secs).replace(':', '-').replace('.', '-')
	
#import Image	# Required for VideoCapture (PIL library)
#import VideoCapture
#from VideoCapture import Device

try:
	from VideoCapture import Device
except:
	Device = None

def HasPhotoFinish():
	return Device is not Null

def PilImageToWxImage( myPilImage, copyAlpha=True ) :
	hasAlpha = myPilImage.mode[ -1 ] == 'A'
	if copyAlpha and hasAlpha :  # Make sure there is an alpha layer copy.

		myWxImage = wx.EmptyImage( *myPilImage.size )
		myPilImageCopyRGBA = myPilImage.copy()
		myPilImageCopyRGB = myPilImageCopyRGBA.convert( 'RGB' )    # RGBA --> RGB
		myPilImageRgbData = myPilImageCopyRGB.tostring()
		myWxImage.SetData( myPilImageRgbData )
		myWxImage.SetAlphaData( myPilImageCopyRGBA.tostring()[3::4] )  # Create layer and insert alpha values.

	else :    # The resulting image will not have alpha.

		myWxImage = wx.EmptyImage( *myPilImage.size )
		myPilImageCopy = myPilImage.copy()
		myPilImageCopyRGB = myPilImageCopy.convert( 'RGB' )    # Discard any alpha from the PIL image.
		myPilImageRgbData =myPilImageCopyRGB.tostring()
		myWxImage.SetData( myPilImageRgbData )

	return myWxImage
	
#--------------------------------------------------------------------------------------
	
camera = None
font = None
photoCache = set()		# Cache of all photo file names.

def getPhotoDirName( raceFileName ):
	fileName, fileExtension = os.path.splitext( raceFileName )
	# Get the directory to write the photo in.
	dirName = os.path.dirname( raceFileName )
	if not dirName:
		dirName = '.'
	dirName = os.path.join( dirName, fileName + '_Photos' )
	return dirName

def ResetPhotoInfoCache( raceFileName ):
	global photoCache
	photoCache = set()
	dir = getPhotoDirName( raceFileName )
	if not os.path.isdir(dir):
		return
	photoCache = set( file for file in os.listdir(dir) if file.startswith('bib') and file.endswith('.jpg') )
	
def hasPhoto( bib, raceSeconds ):
	return GetPhotoFName(bib, raceSeconds) in photoCache

fileFormat = 'bib-%04d-time-%s.jpg'
def GetPhotoFName( bib, raceSeconds ):
	return fileFormat % (bib if bib else 0, fileFormatTime(raceSeconds) )

if Device:
	def AddBibToPhoto( bib, raceSeconds ):
		dirName = getPhotoDirName( raceFileName )
		
		fnameOld = GetPhotoFName( None, raceSeconds )
		fnameNew = GetPhotoFName( bib, raceSeconds )
		
		fileNameOld = os.path.join( dirName, fnameOld )
		fileNameNew = os.path.join( dirName, fnameNew )
		try:
			os.rename( fileNameOld, fileNameNew )
		except:
			pass
			
	def TakePhoto( raceFileName, bib, raceSeconds ):
		global camera, font
		
		# Get the directory to write the photo in.
		dirName = getPhotoDirName( raceFileName )
		if not os.path.isdir( dirName ):
			try:
				os.mkdir( dirName )
			except:
				return 1
		
		fname = GetPhotoFName( bib, raceSeconds )
		fileName = os.path.join( dirName, fname )
		
		# Write the photo.
		if camera is None:
			SetCameraState( True )
			
		if camera:
			bitmap = wx.BitmapFromImage( PilImageToWxImage(camera.getImage()) )
			w, h = bitmap.GetSize()
			dc = wx.MemoryDC( bitmap )
			dc.SetTextForeground( wx.WHITE )
			fontHeight = h//25
			if not font:
				font = wx.FontFromPixelSize( wx.Size(0,fontHeight), wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL )
				
			if bib:
				txt = 'Bib: %d  RaceTime: %s  %s  %s' % (
					bib, formatTime(raceSeconds), datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), AppVerName)
			else:
				txt = 'RaceTime: %s  %s  %s' % (
					formatTime(raceSeconds), datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), AppVerName)
				
			dc.SetFont( font )
			dc.DrawText( txt, fontHeight * 0.5, h - fontHeight*1.25 )
			wx.ImageFromBitmap(bitmap).SaveFile( fileName, wx.BITMAP_TYPE_JPEG )
			photoCache.add( fname )		# Add the photo to the cache.
			return 1
			
		return 0
		
	def SetCameraState( state = False ):
		global camera, font
		camera = None
		font = None
		if state:
			try:
				camera = Device()
			except:
				camera = None
else:
	def TakePhoto( raceFileName, bib, raceSeconds ):
		pass
	def SetCameraState( state ):
		pass
	def AddBibToPhoto( bib, raceSeconds ):
		pass

if __name__ == '__main__':
	app = wx.App()
	SetCameraState( True )
	import datetime
	for i in xrange(5):
		d = datetime.datetime.now()
		TakePhoto( 'test.cmn', 100, 129.676 + i )
		print 'Video Frame Capture Time', (datetime.datetime.now() - d).total_seconds()
