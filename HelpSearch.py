from queue import Queue

import wx
import os
import sys
import time
import traceback
import webbrowser
from io import StringIO

from urllib.request import url2pathname
from urllib.parse import urlparse
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
import wx.html as html
import wx.lib.wxpTag
from http.server import BaseHTTPRequestHandler, HTTPServer

import Utils
from Application import setExitSignal, gotExitSignal
from Log import getLogger
from ThreadUtils import startDaemon, JoinAndCheckThreads

log = getLogger()

PORT_NUMBER = 8761

try:
	with open( os.path.join(Utils.getImageFolder(), 'CrossMgr.ico'), 'rb' ) as f:
		favicon = f.read()
except Exception:
	favicon = None

class HelpHandler( BaseHTTPRequestHandler ):
	html_content = 'text/html; charset=utf-8'
	
	def do_GET(self):
		up = urlparse( self.path )
		try:
			if up.path=='/favicon.ico' and favicon:
				content = favicon
				content_type = 'image/x-icon'
			else:
				file = url2pathname(os.path.basename(up.path.split('#')[0]))
				fname = os.path.join( Utils.getHelpFolder(), file )
				with open(fname, 'r', encoding='utf8') as fp:
					content = fp.read()
				content_type = self.html_content
		except Exception as e:
			self.send_error(404,'File Not Found: {} {}\n{}'.format(self.path, e, traceback.format_exc()))
			return
		
		self.send_response( 200 )
		self.send_header('Content-type',content_type)
		if content_type == self.html_content:
			self.send_header( 'Cache-Control', 'no-cache, no-store, must-revalidate' )
			self.send_header( 'Pragma', 'no-cache' )
			self.send_header( 'Expires', '0' )
		self.end_headers()
		self.wfile.write( content if isinstance(content,bytes) else content.encode('utf8', 'replace') )
	
	def log_message(self, format, *args):
		return

def getHelpURL( fname ):
	return 'http://localhost:{}/{}'.format(PORT_NUMBER, os.path.basename(fname))

def showHelp( url ):
	if not url.startswith('http://'):
		url = getHelpURL( url )
	try:
		webbrowser.open( url )
	except Exception as e:
		pass
	
class HelpSearch( wx.Panel ):
	_f: StringIO

	def __init__( self, parent, id = wx.ID_ANY, style = 0, size=(-1-1) ):
		super().__init__( parent, id, style=style, size=size )

		self.searchLabel = wx.StaticText( self, label=_('Search Text:') )
		self.search = wx.SearchCtrl( self, style=wx.TE_PROCESS_ENTER, value='main screen', size=(200,-1) )
		self.Bind( wx.EVT_TEXT_ENTER, self.doSearch, self.search )
		self.Bind( wx.EVT_TEXT, self.doSearch, self.search )
		self.Bind( wx.EVT_SEARCHCTRL_SEARCH_BTN, self.doSearch, self.search )
		
		hs = wx.BoxSizer( wx.HORIZONTAL )
		hs.Add( self.searchLabel, 0, flag=wx.ALIGN_CENTRE_VERTICAL )
		hs.Add( self.search, 1, flag=wx.EXPAND|wx.LEFT, border=4 )
		
		self.vbs = wx.BoxSizer(wx.VERTICAL)
		
		self.html = html.HtmlWindow( self, size=(800,600), style=wx.BORDER_SUNKEN )
		self.Bind( wx.html.EVT_HTML_LINK_CLICKED, self.doLink, self.html )
		
		self.vbs.Add( hs, 0, flag=wx.BOTTOM|wx.EXPAND, border=4 )
		self.vbs.Add( self.html, 1, flag=wx.EXPAND )
		
		self.SetSizer(self.vbs)
		self.doSearch()

	def doLink( self, event ):
		info = event.GetLinkInfo()
		href = info.GetHref()
		showHelp( href )
		
	def doSearch( self, event = None ):
		with wx.BusyCursor():
			text = self.search.GetValue()
			
			self._f = StringIO()
			try:
				ix = open_dir( Utils.getHelpIndexFolder(), readonly=True )
			except Exception as e:
				Utils.logException( e, sys.exc_info() )
				ix = None
				
			self._f.write('<html>\n')
			
			if ix is not None:
				with ix.searcher() as searcher:
					query = QueryParser('content', ix.schema).parse(text)
					results = searcher.search(query, limit=20)
					
					# Allow larger fragments
					results.formatter.maxchars = 300
					# Show more context before and after
					results.formatter.surround = 50
					
					self._f.write('<table>\n')
					for i, hit in enumerate(results):
						file = os.path.splitext(hit['path'].split('#')[0])[0]
						url = getHelpURL( os.path.basename(hit['path']) )
						if not file.startswith('Menu'):
							section = '{}: {}'.format(file, hit['section'])
						else:
							section = 'Menu: {}'.format( hit['section'] )
						self._f.write('''<tr>
								<td valign="top">
									<font size=+1><a href="{url}">{section}</a></font><br></br>
									{content}
									<font size=+1><br></br></font>
								</td>
							</tr>\n'''.format(url=url, section=section, content=hit.highlights('content') ))
					self._f.write('</table>\n')
				ix.close()
			
			self._f.write( '</html>\n' )
		
		self.html.SetPage( self._f.getvalue() )

class HelpSearchDialog( wx.Dialog ):
	def __init__(
			self, parent, ID = wx.ID_ANY, title='Help Search', size=wx.DefaultSize, pos=wx.DefaultPosition, 
			style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER ):

		super().__init__(parent, ID, title, pos, size, style)

		sizer = wx.BoxSizer(wx.VERTICAL)

		self.search = HelpSearch( self, size=(600,400) )
		sizer.Add(self.search, 1, wx.ALL|wx.EXPAND, 5)
		
		self.SetSizer(sizer)
		sizer.Fit(self)

def HelpServerEnabled() -> bool:
	return True

helpServer: HTTPServer | None = None

def MessageQueueHandler ( q, serverQueue ):
	global helpServer
	keepGoing = True
	while keepGoing:
		message = q.get()
		cmd = message.get('cmd', None)
		if cmd == 'exit':
			log.info('MessageQueueHandler got exit signal.')
			keepGoing = False
		q.task_done()

	assert helpServer is not None
	if serverQueue:
		log.info('Shutting down generic HelpServer on port {}'.format(HELP_SERVER_PORT_NUMBER))
		serverQueue.shutdown()
		log.info('Generic server shut down')
	elif helpServer:
		log.info('Shutting down HelpServer on port {}'.format(HELP_SERVER_PORT_NUMBER))
		helpServer.shutdown()
		log.info('HelpServer shut down')
		helpServer = None


HELP_SERVER_PORT_NUMBER = PORT_NUMBER
def HelpServer():
	global helpServer
	while not gotExitSignal():
		try:
			log.info('Starting HelpServer on port {}'.format(HELP_SERVER_PORT_NUMBER) )
			helpServer = HTTPServer(('localhost', HELP_SERVER_PORT_NUMBER), HelpHandler)
			helpServer.serve_forever(poll_interval = 2)

		except Exception as e:
			helpServer = None
			time.sleep( 5 )

	log.exiting('HelpServer thread complete.')

helpMessageQueue = Queue()
webThreadQ = startDaemon(target=MessageQueueHandler, name='HelpServerQ', args=(helpMessageQueue,helpServer,))
webThread = startDaemon( target=HelpServer, name='HelpServer' )


def ShutdownHelpServer():
	setExitSignal()
	assert helpMessageQueue is not None
	if helpMessageQueue:
		helpMessageQueue.put( {'cmd':'exit'} )


def WaitForHelpSearchServerShutdown() -> None:
	threadList = [webThread]
	JoinAndCheckThreads(threadList, 5, 'HelpServer')


if __name__ == '__main__':
	app = wx.App(False)
	mainWin = wx.Frame(None,title="CrossMan", size=(600,400))
	mainWin.Show()
	searchDialog = HelpSearchDialog( mainWin, size=(600,400) )
	searchDialog.Show()
	app.MainLoop()
