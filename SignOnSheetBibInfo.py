import re
from io import StringIO

import Model
import Utils
from html import escape

reSeparators = re.compile( '[,;:.]+' )

class BibInfo:
	AllFields = (
		'Name',
		'License',
		'UCIID',
		'Team',
		'Wave',
	)

	def __init__(self):
		self.race = Model.race
		excelLink = getattr(self.race, 'excelLink', None)
		if excelLink:
			self.externalInfo = excelLink.read()
			self.fields = ['Name'] + [f for f in self.AllFields if excelLink.hasField(f)] + ['Wave']
		else:
			self.externalInfo = {}
			self.fields = []

	def getData(self, bib):
		try:
			bib = int(bib)
		except Exception:
			return {}

		try:
			data = {k: '{}'.format(v) for k, v in self.externalInfo.get(bib, {}).items()}
		except ValueError:
			data = {}

		data['Name'] = ', '.join(v for v in (data.get('LastName', None), data.get('FirstName', None)) if v)

		category = self.race.getCategory(bib)
		data['Wave'] = category.name if category else ''
		return data

	def bibField(self, bib):
		data = self.getData(bib)
		if not data:
			return '{}'.format(bib)
		values = [('<strong>{}</strong>' if 'Name' in f else '{}').format(escape(data[f])) for f in self.fields if
		          data.get(f, None)]
		return '{}: {}'.format(bib, ', '.join(values))

	def bibList(self, bibs):
		bibs = [b for b in bibs if b]
		html = StringIO()
		tag = Utils.tag
		with tag(html, 'ul', 'bibList'):
			for bib in bibs:
				with tag(html, 'li'):
					html.write(self.bibField(bib))
		return html.getvalue()

	def bibTable(self, bibs):
		bibs = [b for b in bibs if b]
		if not bibs:
			return '<br/>'
		GetTranslation = _
		html = StringIO()
		tag = Utils.tag
		with tag(html, 'table', 'bibTable'):
			with tag(html, 'thead'):
				with tag(html, 'tr'):
					for f in ['Bib#'] + self.fields:
						with tag(html, 'th', {'style': "text-align:left"} if 'Bib' in f else {'style': "text-align:left"}):
							html.write(GetTranslation(f))
			with tag(html, 'tbody'):
				for bib in bibs:
					with tag(html, 'tr'):
						data = self.getData(bib)
						with tag(html, 'td', {'style': "text-align:right"}):
							html.write('{}'.format(bib))
						for f in self.fields:
							with tag(html, 'td', {'style': "text-align:left"}):
								if 'Name' in f:
									with tag(html, 'strong'):
										html.write(escape(data.get(f, '')))
								else:
									html.write(escape(data.get(f, '')))
		return html.getvalue()

	def getSubValue(self, subkey):
		if subkey.startswith('BibTable'):  # {=BibTable 132,110,98}
			return self.bibTable(reSeparators.sub(' ', subkey).split()[1:])
		elif subkey.startswith('BibList'):  # {=BibList 132,110,98}
			return self.bibList(reSeparators.sub(' ', subkey).split()[1:])
		elif subkey.startswith('Bib'):  # {=Bib 111}
			return self.bibField(' '.join(reSeparators.sub(' ', subkey).split()[1:]))
		return None