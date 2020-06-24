"""
  OracleTranslator.py

  Module for translating parsed query to SQL-code.
"""

class OracleTranslator:
  def __init__(self, primaryKeys, references, paths):
    self.primaryKeys = primaryKeys
    self.references = references
    self.paths = paths

  # Translates a query in JSON format to SQL-code.
  def translate(self, parsed):
    self.result = {
      'SELECT': [],
      'FROM': [],
      'WHERE': [],
      'GROUP BY': [],
      'HAVING': [],
      'ORDER BY': []
    }
    # Prefixes before columns (if there are multiple tables used).
    self.prefixes = {}
    # Counter for creating prefixes ("t-1", "t-2", "t-3", ...)
    self.counter = 0 
    tables = [t['name'] for t in parsed['tablesUsed']]
    if (len(tables) == 0): # If there are no tables in the query.
      raise ValueError(f'Запрос не содержит ни столбцов, ни таблиц!')
    if (len(tables) == 1): # If there's only one table in the query.
      self.result['FROM'].append(tables[0])
      self.prefixes[tables[0]] = ''
    else: # If there are multiple tables in the query.
      self.connectMultipleTables(tables)

    # SELECT
    for obj in parsed['selectExpr']['selectObjects']:
      self.result['SELECT'].append(self.parseObject(obj))
    # WHERE and HAVING
    if ('whereExpr' in parsed):
      for conditionSection in parsed['whereExpr']:
        self.parseConditionSection(conditionSection.upper(), parsed['whereExpr'][conditionSection])
    # GROUP BY
    if ('groupByExpr' in parsed):
      for obj in parsed['groupByExpr']['groupObjects']:
        self.result['GROUP BY'].append(self.parseObject(obj))
    # ORDER BY
    if ('orderByExpr' in parsed):
      for obj in parsed['orderByExpr']['orderObjects']:
        self.result['ORDER BY'].append(self.parseOrderObject(obj))
    
    return self.stringifyResult()

  # Convert the result to string (SQL-code).
  def stringifyResult(self):
    query = []
    # SELECT
    selectExpressions = ', '.join(self.result['SELECT'])
    query.append(f'SELECT {selectExpressions}')
    # FROM
    fromTables = '\n  '.join(self.result['FROM'])
    query.append(f'FROM {fromTables}')
    # WHERE
    if (len(self.result['WHERE']) > 0):
      whereConditions = '\n  '.join(self.result['WHERE'])
      query.append(f'WHERE {whereConditions}')
    # GROUP BY
    if (len(self.result['GROUP BY']) > 0):
      groupExpressions = ', '.join(self.result['GROUP BY'])
      query.append(f'GROUP BY {groupExpressions}')
    # HAVING
    if (len(self.result['HAVING']) > 0):
      havingConditions = '\n  '.join(self.result['HAVING'])
      query.append(f'HAVING {havingConditions}')
    # ORDER BY
    if (len(self.result['ORDER BY']) > 0):
      orderExpressions = ', '.join(self.result['ORDER BY'])
      query.append(f'ORDER BY {orderExpressions}')

    return '\n'.join(query)

  # Parses a condition section (WHERE/HAVING).
  def parseConditionSection(self, section, objects):
    if (len(objects) == 0): return
    condition = objects[0]
    self.result[section].append(self.parseCondition(condition))
    for i in range(2, len(objects), 2):
      connector = {
        'или': 'OR ',
        'и': 'AND ',
        ',': 'AND '
      }[objects[i - 1]]
      condition = objects[i]
      self.result[section].append(self.parseCondition(condition, connector))

  # Parses one condition.
  def parseCondition(self, condition, connector=''):
    prefix = 'NOT ' if condition['not'] else ''
    if ('NULL' in condition['operator']):
      operator = condition['operator']
      target = condition['target']
      return f'{connector}{prefix}{self.parseObject(target)} {operator}'
    else:
      operator = {
        'gt': '>',
        'lt': '<',
        'eq': '=',
        'ge': '>=',
        'le': '<='
      }[condition['operator']]
      targetA = condition['target'][0]
      targetB = condition['target'][1]
      return f'{connector}{prefix}{self.parseObject(targetA)} {operator} {self.parseObject(targetB)}'

  # Parses a column in the ORDER BY clause.
  def parseOrderObject(self, obj):
    suffix = ' DESC' if obj['desc'] else ''
    column = obj['column']
    return f'{self.parseObject(column)}{suffix}'

  # Parses a column or literal.
  def parseObject(self, obj):
    if (checkField(obj, 'type', 'column')):
      table = obj['table']
      prefix = self.prefixes[table] if table in self.prefixes else ''
      column = obj['name']
      return f'{prefix}{column}'
    elif (checkField(obj, 'type', 'table')):
      table = obj['name']
      prefix = self.prefixes[table] if table in self.prefixes else f'{table}.'
      return f'{prefix}*'
    elif (checkField(obj, 'type', 'number')):
      value = obj['value']
      return value
    elif (checkField(obj, 'type', 'string')):
      value = obj['value']
      return f'\'{value}\''
    elif ('operator' in obj):
      operator = obj['operator']
      target = obj['target']
      return f'{operator}({self.parseObject(target)})'

  # The case when we need to JOIN multiple tables.
  def connectMultipleTables(self, tables):
    hasConnection = [t for t in tables[1:] if (tables[0], t) in self.paths]
    if (len(hasConnection) > 0):
      firstJoinTable = min(
        tables[1:],
        key = lambda table: len(self.paths[(tables[0], table)])
      )
      self.createConnection(tables[0], firstJoinTable)
    else:
      hasConnection = [t for t in tables[1:] if (t, tables[0]) in self.paths]
      if (len(hasConnection) == 0): raise ValueError(f'Невозможно соединить таблицы из запроса!')
      firstJoinTable = min(
        tables[1:],
        key = lambda table: len(self.paths[(table, tables[0])])
      )
      self.createConnection(firstJoinTable, tables[0])
    self.connectRemaining(tables)

  # Connecting the remaining tables after we connected the first 2.
  def connectRemaining(self, tables):
    tablesAdded = [t for t in tables if t in self.prefixes]
    tablesLeft = [t for t in tables if t not in self.prefixes]
    if (len(tablesLeft) == 0): return
    connections = [(t1, t2) for t1 in tablesAdded for t2 in tablesLeft if (t1, t2) in self.paths]
    if (len(connections) == 0):
      connections = [(t2, t1) for t1 in tablesAdded for t2 in tablesLeft if (t2, t1) in self.paths]
      if (len(connections) == 0):
        raise ValueError(f'Невозможно соединить таблицы из запроса!')
    (mainTable, refTable) = min(
        connections,
        key = lambda c: len(self.paths[(c[0], c[1])])
      )
    self.createConnection(mainTable, refTable)
    self.connectRemaining(tables)

  # Joins 2 tables.
  def createConnection(self, tableA, tableB):
    if (self.counter == 0):
      self.addTable(tableA)
    mainTable = tableA
    for table in self.paths[(tableA, tableB)]:
      if (table not in self.prefixes):
        self.addJoin(mainTable, table)
      mainTable = table

  # Adds JOIN to the result dictionary.
  def addJoin(self, mainTable, refTable):
    self.addPrefix(refTable)
    fk = [fk for fk in self.references[mainTable][refTable]][0]
    cols = self.references[mainTable][refTable][fk]
    onClause = []
    for (colA, colB) in cols:
      onClause.append(f'{self.prefixes[mainTable]}{colA} = {self.prefixes[refTable]}{colB}')
    onClause = ' AND '.join(onClause)
    synonim = self.prefixes[refTable][0:-1]
    self.result['FROM'].append(f'JOIN {refTable} {synonim} ON {onClause}')  

  # Adds table name with it's index to the result dictionary.
  def addTable(self, table):
    self.addPrefix(table)
    synonim = self.prefixes[table][0:-1]
    self.result['FROM'].append(f'{table} {synonim}')

  # Creatings a prefix for a table.
  def addPrefix(self, table):
    if (table not in self.prefixes):
      self.counter += 1
      self.prefixes[table] = f'"t-{self.counter}".'

# Checks if the field is present int the dictionary and it's euqal to the value.
def checkField(dictionary, field, value):
  return field in dictionary and dictionary[field] == value
