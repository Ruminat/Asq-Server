"""
  dbObjects.py

  Description of database objects.
"""

from db import SELECT, SELECT2Data

# Synonyms in Russian language for database objects. 
dbObjects = [
  {
    'type': 'table',
    'schema': 'hr',
    'name': 'employees',
    'lemmas': ['сотрудник', 'работник']
  },
  {
    'type': 'table',
    'schema': 'hr',
    'name': 'departments',
    'lemmas': ['отдел', 'подразделение', 'департамент']
  },
  {
    'type': 'table',
    'schema': 'hr',
    'name': 'countries',
    'lemmas': ['страна', 'государство']
  },
  {
    'type': 'table',
    'schema': 'hr',
    'name': 'regions',
    'lemmas': ['регион']
  },
  {
    'type': 'table',
    'schema': 'hr',
    'name': 'locations',
    'lemmas': ['локация', 'место']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'employees',
    'name': 'employee_id',
    'lemmas': ['номер', 'идентификатор']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'employees',
    'name': 'first_name',
    'lemmas': ['имя']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'employees',
    'name': 'last_name',
    'lemmas': ['фамилия']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'employees',
    'name': 'email',
    'lemmas': ['почта']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'employees',
    'name': 'phone_number',
    'lemmas': ['телефон']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'employees',
    'name': 'commission_pct',
    'lemmas': ['комиссионные']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'employees',
    'name': 'salary',
    'lemmas': ['зарплата', 'получка', 'оклад', 'заработок']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'employees',
    'name': 'manager_id',
    'lemmas': ['менеджер', 'начальник', 'руководитель']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'departments',
    'name': 'department_id',
    'lemmas': ['номер', 'идентификатор']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'departments',
    'name': 'department_name',
    'lemmas': ['название']
  },
  {
    'type': 'column',
    'schema': 'hr',
    'table': 'departments',
    'name': 'manager_id',
    'lemmas': ['менеджер', 'начальник', 'руководитель']
  },
]

# Links from lemmas to DB objects.
dbObjectsLemmas = {}
for obj in dbObjects:
  for lemma in obj['lemmas']:
    if (lemma in dbObjectsLemmas):
      if (isinstance(dbObjectsLemmas[lemma], list)):
        dbObjectsLemmas[lemma].append(obj)
      else:
        dbObjectsLemmas[lemma] = [dbObjectsLemmas[lemma], obj]
    else:
      dbObjectsLemmas[lemma] = obj

# Primary keys query
(header, rows) = SELECT("""
  SELECT LOWER(col.owner), LOWER(col.table_name), LOWER(col.column_name)
  FROM USER_CONSTRAINTS con
    JOIN USER_CONS_COLUMNS col ON con.constraint_name = col.constraint_name
  WHERE con.constraint_type = 'P'
""", SELECT2Data)

# Primary keys
primaryKeys = {}
for row in rows:
  [schema, table, column] = row
  if (table not in primaryKeys):
    primaryKeys[table] = [column]
  else:
    primaryKeys[table].append(column)

# Foreign keys query
(header, rows) = SELECT("""
  WITH constraints AS (
    SELECT con.constraint_name
         , con.r_constraint_name
         , con.constraint_type
         , col.owner
         , col.table_name
         , col.column_name
         , col.position
    FROM USER_CONSTRAINTS con
      JOIN USER_CONS_COLUMNS col ON con.constraint_name = col.constraint_name
  )
  SELECT LOWER(L.constraint_name)
       , LOWER(L.owner)
       , LOWER(L.table_name)
       , LOWER(L.column_name)
       , LOWER(R.owner)
       , LOWER(R.table_name)
       , LOWER(R.column_name)
  FROM constraints L
    JOIN constraints R ON L.r_constraint_name = R.constraint_name
                      AND L.Constraint_Type = 'R'
                      AND L.position = R.position
                      AND L.constraint_type = 'R'
""", SELECT2Data)

# Foreign keys
references = {}
for row in rows:
  [refName, ownerL, tableL, columnL, ownerR, tableR, columnR] = row
  if (tableL not in references):
    references[tableL] = {}
  if (tableR not in references[tableL]):
    references[tableL][tableR] = {}
  if (refName not in references[tableL][tableR]):
    references[tableL][tableR][refName] = []
  references[tableL][tableR][refName].append((columnL, columnR))

# Shortest paths
paths = {}

# Finds the shortest path from tableL to tableR.
def findShortestPath(tableL, tableR, currentPath=[], passedTables=set()):
  if (len(passedTables) == 0): passedTables = { tableL }
  if (len(currentPath) == 0): currentPath = [tableL]
  if (tableL == tableR): return currentPath[1:]
  if (tableL not in references): return None
  allPaths = []
  for (nextTable, ref) in references[tableL].items():
    if (nextTable not in passedTables):
      path = findShortestPath(nextTable, tableR, currentPath + [nextTable], passedTables | {nextTable})
      if (path):
        allPaths.append(path)
  if (len(allPaths) == 0): return None
  else: return min(allPaths, key = lambda p: len(p))

# Fills in the «paths» dictionary.
for (tableL, refs) in references.items():
  for (tableR, PKs) in primaryKeys.items():
    if (tableL == tableR): continue
    path = findShortestPath(tableL, tableR)
    if (path):
      paths[(tableL, tableR)] = path
