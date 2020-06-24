"""
  db.py

  Database module, used to connect to Oracle Database.
"""

import cx_Oracle

# Parses a DB row into an HTML-row.
def parseRow(row, separetor, header=False):
  cols = row.split(separetor)
  colsHTML = ''
  for col in cols:
    if (header): colsHTML += '<th>' + col.strip() + '</th>'
    else:        colsHTML += '<td>' + col.strip() + '</td>'
  return '<tr>' + colsHTML + '</tr>'

# Makes an HTML table.
def SQLtable(code, separetor='\t', caption=''):
  if ('\\n' in code):
    lines = code.split('\\n')
  else:
    lines = code.split('\n')
  rows = []
  if (len(lines) > 0):
    rows.append(parseRow(lines[0], separetor, header=True))
  if (len(lines) > 1):
    for i in range(1, len(lines)):
      rows.append(parseRow(lines[i], separetor, header=False))
  table = '<row class="aligment-center">'
  table += '<table class="table table-scroll table-SQL table-striped table-hover">'
  if (caption != ''): table += '<caption>' + caption + '</caption>'
  if (len(lines) > 0):
    table += '<thead class="thead-dark">'
    table += rows[0]
    table += '</thead>'
  if (len(lines) > 1):
    table += '<tbody>'
    for r in range(1, len(rows)):
      table += rows[r]
    table += '</tbody>'
  table += '</table>'
  table += '</row>'
  return table

# Selects data from database.
# @localhost:1521/orcl
def SELECT(query, cb):
  connection = cx_Oracle.connect(u'C##Yasos/Bib@localhost:1521/xe')
  cursor = connection.cursor()
  cursor.execute(query)
  result = cb(cursor)
  connection.close()
  return result

# Converts SELECT data to a tuple of header and rows of the result.
def SELECT2Data(cursor, separator='\t'):
  cols = []
  for col in cursor.description:
    cols.append(col[0])
  # names of the columns
  header = cols
  rows = []
  for row in cursor:
    cols = []
    for col in row:
      cols.append(str(col))
    rows.append(cols)
  return (header, rows)

# Converts SELECT data to string.
def SELECT2String(cursor, separator='\t'):
  cols = []
  for col in cursor.description:
    cols.append(col[0])
  # names of the columns
  tableHeader = separator.join(cols)
  rows = []
  for row in cursor:
    cols = []
    for col in row:
      cols.append(str(col))
    rows.append(separator.join(cols))
  # the SELECT query rows
  tableBody = '\n'.join(rows)
  return tableHeader + '\n' + tableBody
