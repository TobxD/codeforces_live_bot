class Table:
	def __init__(self, header, rows):
		self._header = header
		self._rows = rows

	def formatTable(self):
		if len(self._header) <= 6:
			return self.formatTableWide()
		else:
			return self.formatTableNarrow()

	def formatTableWide(self):
		colW = 4
		totalW = len(self._header)*(colW+1)+1
		msg = "```\n"
		msg += self._getDividerHead(colW, totalW)
		for h in self._header:
			msg += "┃" + h.center(colW)
		msg += "┃\n"

		for row in self._rows:
			msg += self._getDividerHalfBottom(colW, totalW)
			msg += "┃" + row["head"].center(totalW-2) + "┃\n"
			if "head2" in row:
				msg += "┃" + row["head2"].center(totalW-2) + "┃\n"
			for v in row["body"]:
				msg += "┃" + str(v).center(colW)
			msg += "┃\n"

		msg += self._getDividerBottom(colW, totalW)
		msg += "```"
		return msg.replace("┃","|")

	def formatTableNarrow(self): # 2 self._rows per row
		colW = 4
		colC = min(len(self._header), 6)
		rowC = (len(self._header)+colC-1)//colC
		totalW = colC*(colW+1)+1
		msg = "```\n"
		msg += self._getDividerHead(colW, totalW)
		for i in range(rowC*colC):
			if i % colC == 0 and i > 0:
				msg += "┃\n"
			v = self._header[i] if i < len(self._header) else ""
			msg += "┃" + v.center(colW)

		msg += "┃\n"

		for row in self._rows:
			msg += self._getDividerHalfBottom(colW, totalW)
			msg += "┃" + row["head"].center(totalW-2) + "┃\n"
			if "head2" in row:
				msg += "┃" + row["head2"].center(totalW-2) + "┃\n"
			for i in range(rowC*colC):
				if i % colC == 0 and i > 0:
					msg += "┃\n"
				v = row["body"][i] if i < len(row["body"]) else ""
				msg += "┃" + str(v).center(colW)
			msg += "┃\n"

		msg += self._getDividerBottom(colW, totalW)
		msg += "```"
		return msg.replace("┃","|")

	def _getDividerHead(self, colW, totalW):
		msg = ""
		for i in range(totalW):
			if i == 0:
				msg += "+"#"┏"
			elif i == totalW-1:
				msg += "+"#"┓"
			elif i % (colW+1) == 0:
				msg += "+"#"┳"
			else:
				msg += "-"
		return msg + "\n"

	def _getDividerBottom(self, colW, totalW):
		msg = ""
		for i in range(totalW):
			if i == 0:
				msg += "+"#"┗"
			elif i == totalW-1:
				msg += "+"#"┛"
			elif i % (colW+1) == 0:
				msg += "+"#"┻"
			else:
				msg += "-"
		return msg + "\n"

	def _getDividerHalfBottom(self, colW, totalW):
		msg = ""
		for i in range(totalW):
			if i == 0:
				msg += "+"#"┣"
			elif i == totalW-1:
				msg += "+"#"┫"
			elif i % (colW+1) == 0:
				msg += "+"#"┻"
			else:
				msg += "-"#"━"
		return msg + "\n"

	def _getDivider(self, colW, totalW):
		msg = ""
		for i in range(totalW):
			if i == 0:
				msg += "+"#"┣"
			elif i == totalW-1:
				msg += "+"#"┫"
			elif i % (colW+1) == 0:
				msg += "+"#"╋"
			else:
				msg += "-"#"━"
		return msg + "\n"
