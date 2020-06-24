"""
  StructureParser.py

  Module for parsing found patterns to JSON format.
"""

from AbstractRegularExpressions import Structure, PatternToken

class StructureParser:
  def __init__(self, dbObjects, dbObjectsLemmas):
    self.dbObjects = dbObjects
    self.dbObjectsLemmas = dbObjectsLemmas
  # Parses the highest level structures (SELECT, WHERE, GROUP BY, ORDER BY).
  def parse(self, parsed, structure):
    if (structure.name not in parsed):
      # parsed is the final result.
      parsed[structure.name] = {}
    # Calling the right parsing function depending on the structure.
    {
      'selectExpr': self.parseSelect,
      'whereExpr': self.parseWhere,
      'groupByExpr': self.parseGroupBy,
      'orderByExpr': self.parseOrderBy
    }[structure.name](parsed, parsed[structure.name], structure.elements)

  # SELECT
  def parseSelect(self, parsed, struct, elements):
    if ('selectObjects' not in struct):
      struct['selectObjects'] = []
    for el in elements:
      if (isinstance(el, Structure)):
        if (el.name == 'listOfTables'):
          for maybeTable in el.elements:
            self.tryToAddTable(parsed, struct, maybeTable)
        elif (el.name == 'listOfColumns'):
          self.parseColumns(parsed, struct, el.elements)

  # WHERE and HAVING
  def parseWhere(self, parsed, struct, elements):
    if ('where' not in struct):
      struct['where'] = []
      struct['having'] = []
    self.parseCondition(parsed, struct, 'и', elements[0])
    for i in range(2, len(elements), 2):
      self.parseCondition(parsed, struct, elements[i - 1].token.text, elements[i])

  # GROUP BY
  def parseGroupBy(self, parsed, struct, elements):
    if ('groupObjects' not in struct):
      struct['groupObjects'] = []
    table = self.tryToGetTable(elements[-1])
    for el in elements:
      if (isStruct(el, 'columnExpr')):
        self.addObject(struct['groupObjects'], self.parseColumnExpr(parsed, table, el.elements))

  # ORDER BY
  def parseOrderBy(self, parsed, struct, elements):
    if ('orderObjects' not in struct):
      struct['orderObjects'] = []
    for el in elements:
      if (isStruct(el, 'sortColumn')):
        self.parseSortColumn(parsed, struct, el.elements)

  # Tries to get table from token and returns None when fails.
  def tryToGetTable(self, maybeTable):
    if (isPrimitive(maybeTable, 'table')):
      return self.dbObjectsLemmas[maybeTable.token.lemma]
    else: return None

  # Parse the columns pattern.
  def parseColumns(self, parsed, struct, elements):
    table = self.tryToGetTable(elements[-1])
    for el in elements:
      if (isStruct(el, 'columnExpr')):
        self.addObject(struct['selectObjects'], self.parseColumnExpr(parsed, table, el.elements))

  # Parses cokumn or literal with operators.
  def parseColumnExpr(self, parsed, table, columnExpr):
    column = None
    expr = columnExpr[-1]
    # Literal
    if (isStruct(expr, 'literal')):
      literal = expr.elements[0]
      # String
      if (isStruct(literal, 'string')):
        for el in literal.elements:
          if (isStruct(el, 'stringQuoteContent') or isStruct(el, 'stringDoubleQuoteContent')):
            column = {
              'type': 'string',
              'value': ' '.join([t.token.text for t in el.elements])
            }
      # Number
      elif (isPrimitive(literal, 'number')):
        column = {
          'type': 'number',
          'value': literal.token.text
        }
    # Column
    else:
      colName = expr.token.lemma
      maybeColumn = self.dbObjectsLemmas[colName]
      if (isinstance(maybeColumn, list)):
        if (not table):
          for col in maybeColumn:
            if (col['table'] in [t['name'] for t in parsed['tablesUsed']]):
              column = col
          if (not column):
            raise ValueError(f'Не указана таблица, которой принадлежит столбец «{colName}»!')
        else:
          for col in maybeColumn:
            if (col['table'] == table['name']):
              column = col
          tableName = table['lemmas'][0]
          if (not column):
            raise ValueError(f'У таблицы «{tableName}» нет столбца «{colName}»!')
      else:
        column = maybeColumn
      self.addTable(parsed, self.getTableByName(column['table']))
    if (len(columnExpr) > 1):
      return self.applyOperators(columnExpr[0:-1][::-1], column)
    else: return column

  # Applies operators to column or literal expression.
  def applyOperators(self, operators, target):
    result = target
    for o in operators:
      operator = o.elements[0].elements[0].pattern.name.upper()
      result = {
        'operator': operator,
        'target': result
      }
    return result

  # If maybeTable is found to be a table, add it to parsed.
  def tryToAddTable(self, parsed, struct, maybeTable):
    table = self.tryToGetTable(maybeTable)
    if (table):
      self.addTable(parsed, table)
      self.addObject(struct['selectObjects'], table)

  # Returns the db object from table name.
  def getTableByName(self, name):
    return [o for o in self.dbObjects if o['name'] == name][0]

  # Adds the table to parsed.
  def addTable(self, parsed, table):
    if (table not in parsed['tablesUsed']):
      parsed['tablesUsed'].append(table)

  # Adds the objects if not already present in elements.
  def addObject(self, elements, obj):
    if (obj not in elements):
      elements.append(obj)

  # Parses a WHERE/HAVING condition with it's corresponding connector (AND/OR).
  def parseCondition(self, parsed, struct, connector, condition):
    inHaving = False
    result = {
      'not': isPrimitive(condition.elements[0], 'not')
    }
    for el in condition.elements:
      if (isPrimitive(el, 'isNull')): result['operator'] = 'IS NULL'
      elif (isPrimitive(el, 'isNotNull')): result['operator'] = 'IS NOT NULL'
      elif (isStruct(el, 'compareOperator')):
        result['operator'] = el.elements[0].pattern.name
      elif (isStruct(el, 'columnExpr') or isStruct(el, 'columnLiteralExpr')):
        if (any([
          isinstance(e, Structure) and isStruct(e.elements[0], 'aggregateFunction')
          for e in el.elements
        ])):
          inHaving = True
        if ('target' in result):
          result['target'] = [result['target'], self.parseColumnExpr(parsed, None, el.elements)]
        else:
          expr = self.parseColumnExpr(parsed, None, el.elements)
          result['target'] = expr
    target = struct['having'] if inHaving else struct['where']
    if (len(target) > 0): target.append(connector)
    target.append(result)

  # Parses a column expression from ORDER BY.
  def parseSortColumn(self, parsed, struct, sortColumn):
    isDesc = isStruct(sortColumn[-1], 'desc')
    for el in sortColumn:
      if (isStruct(el, 'columnExpr')):
        col = self.parseColumnExpr(parsed, None, el.elements)
        self.addObject(struct['orderObjects'], { 'column': col, 'desc': isDesc })

# Checks whether the element is a Structure and it's name is structName.
def isStruct(element, structName):
  return isinstance(element, Structure) and element.name == structName
# Checks whether the element is a Primitive and it's name is name.
def isPrimitive(element, name):
  return isinstance(element, PatternToken) and element.pattern.name == name
