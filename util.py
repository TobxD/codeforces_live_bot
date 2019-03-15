import hashlib
import datetime

def cleanString(s):
  return s.lower().strip()

def sha512Hex(s):
  return hashlib.sha512(s.encode()).hexdigest()

def formatSeconds(s, useExcl = False):
  s = s//60
  if s < 60:
    out = "0:" + str(s).zfill(2)
  else:
    out = str(s//60) + ":" + str(s%60).zfill(2)
  return out.replace(":", "!") if useExcl else out

def getDividerHead(colW, totalW):
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

def getDividerBottom(colW, totalW):
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

def getDividerHalfBottom(colW, totalW):
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

def getDivider(colW, totalW):
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

def formatTableWide(header, rows):
  colW = 4
  totalW = len(header)*(colW+1)+1
  msg = "```\n"
  msg += getDividerHead(colW, totalW)
  for h in header:
    msg += "┃" + h.center(colW)
  msg += "┃\n"

  for row in rows:
    msg += getDividerHalfBottom(colW, totalW)
    msg += "┃" + row["head"].center(totalW-2) + "┃\n"
    if "head2" in row:
      msg += "┃" + row["head2"].center(totalW-2) + "┃\n"
    for v in row["body"]:
      msg += "┃" + str(v).center(colW)
    msg += "┃\n"

  msg += getDividerBottom(colW, totalW)
  msg += "```"
  return msg.replace("┃","|")

def formatTableNarrow(header, rows): # 2 rows per row
  colW = 4
  #colC = (len(header)+1)//2
  colC = 4
  totalW = colC*(colW+1)+1
  msg = "```\n"
  msg += getDividerHead(colW, totalW)
  for i in range(2*colC):
    if i == colC:
      msg += "┃\n"
    v = header[i] if i < len(header) else ""
    msg += "┃" + v.center(colW)

  msg += "┃\n"

  for row in rows:
    msg += getDividerHalfBottom(colW, totalW)
    msg += "┃" + row["head"].center(totalW-2) + "┃\n"
    if "head2" in row:
      msg += "┃" + row["head2"].center(totalW-2) + "┃\n"
    for i in range(2*colC):
      if i == colC:
        msg += "┃\n"
      v = row["body"][i] if i < len(row["body"]) else ""
      msg += "┃" + str(v).center(colW)
    msg += "┃\n"

  msg += getDividerBottom(colW, totalW)
  msg += "```"
  return msg.replace("┃","|")

def formatTable(header, rows):
  if len(header) <= 6:
    return formatTableWide(header, rows)
  else:
    return formatTableNarrow(header, rows)

def log(msg):
  timeString = '[' + str(datetime.datetime.now()) + '] '
  print(timeString + msg)
