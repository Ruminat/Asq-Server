import cx_Oracle
# @localhost:1521/orcl
def SELECT(query, cb):
  connection = cx_Oracle.connect(u'C##Yasos/Bib@localhost:1521/xe')
  cursor = connection.cursor()
  cursor.execute(query)
  result = cb(cursor)
  connection.close()
  return result

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

print(SELECT("""
  SELECT * FROM dual
""", SELECT2String))
