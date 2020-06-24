"""
  patterns.py

  Search patterns.
"""

from AbstractRegularExpressions import Primitive, Pattern, PatternToken, Automata, printPattern, OR, Structure

class Token:
  def __init__(self, text, tokenType='text', lemma='', grammar='', index=-1):
    self.text = text
    self.type = tokenType
    self.lemma = lemma
    self.grammar = grammar
    self.index = index
  def __str__(self):
    return str({ 'type': self.type, 'text': self.text, 'lemma': self.lemma, 'grammar': self.grammar, 'index': self.index })

# Compares the token's text to a primitive.
def textCompare(token, texts):
  for t in texts:
    if t == token.text: return True
  return False

# Compares the token's lemma or text (if lemma isn't available) to a primitive.
def lemmasCompare(token, lemmas):
  text = token.text if not token.lemma else token.lemma
  for l in lemmas:
    if l == text: return True
  return False

# Checks if the token's lemma or text (if lemma isn't available) contains the primitive.
def lemmasPart(token, lemmas):
  text = token.text if not token.lemma else token.lemma
  for l in lemmas:
    if l in text: return True
  return False

# Basic primitives
connector = Primitive('connector', lambda token: lemmasCompare(token, [',', 'и']))

# Number
numberP = Primitive('number', lambda token: token.type in ['number'])
# String
quoteP = Primitive('quote', lambda token: lemmasPart(token, ['\'']))
doubleQuoteP = Primitive('doubleQuote', lambda token: lemmasPart(token, ['"']))
nonQuoteP = Primitive('nonQuote', lambda token: not lemmasPart(token, ['\'']))
nonDoubleQuoteP = Primitive('nonDoubleQuote', lambda token: not lemmasPart(token, ['"']))
stringQuoteContent = Pattern('stringQuoteContent', (nonQuoteP, '*'))
stringDoubleQuoteContent = Pattern('stringDoubleQuoteContent', (nonDoubleQuoteP, '*'))
stringP = Pattern(
  'string',
       [quoteP, stringQuoteContent, quoteP]
  |OR| [[doubleQuoteP, stringDoubleQuoteContent, doubleQuoteP]]
)
# Literal (Number | String)
literal = Pattern('literal', numberP |OR| stringP)

# Operators
isNullP = Primitive('isNull', lambda token: lemmasCompare(token, ['без', 'нет']))
isNotNullP = Primitive('isNotNull', lambda token: lemmasCompare(token, ['быть']))
notP = Primitive('not', lambda token: lemmasCompare(token, ['не']))

# Functions
roundP = Primitive('round', lambda token: lemmasCompare(token, ['округлять']))

# Aggregate functions
avgP = Primitive('avg', lambda token: lemmasCompare(token, ['средний', 'усреднять', 'avg']))
maxP = Primitive('max', lambda token: lemmasCompare(token, ['большой', 'высокий', 'максимальный']))
minP = Primitive('min', lambda token: lemmasCompare(token, ['маленький', 'низкий', 'минимальный']))
countP = Primitive('count', lambda token: lemmasCompare(token, ['сколько', 'количество']))
sumP = Primitive('sum', lambda token: lemmasCompare(token, ['сумма', 'суммировать']))

# Operator's patterns
function = Pattern('function', roundP)
aggregateFunction = Pattern('aggregateFunction', avgP |OR| maxP |OR| minP |OR| countP |OR| sumP)
operator = Pattern('operator', function |OR| aggregateFunction)

# Selecting
table = Primitive('table', lambda token: token.type == 'table')
column = Primitive('column', lambda token: token.type == 'column')
columnExpr = Pattern('columnExpr', [(operator, '*'), column])
columnLiteralExpr = Pattern('columnExpr', [(operator, '*'), column |OR| literal])
listOfTables = Pattern('listOfTables', [table])
listOfColumns = Pattern('listOfColumns', [columnExpr, ([connector, columnExpr], '*'), (table, '?')])
selectExpr = Pattern('selectExpr', [listOfColumns |OR| listOfTables])

# Conditions
orP = Primitive('or', lambda token: lemmasCompare(token, ['или']))
gt = Primitive('gt', lambda token: textCompare(token, ['>', 'больше', 'выше', 'превышать']))
lt = Primitive('lt', lambda token: textCompare(token, ['<', 'меньше', 'ниже']))
eq = Primitive('eq', lambda token: lemmasCompare(token, ['=', 'равный']))
ge = Pattern('ge', [gt, orP, eq] |OR| [notP, lt])
le = Pattern('le', [lt, orP, eq] |OR| [notP, gt])
logicalConnector = Primitive('logicalConnector', lambda token: lemmasCompare(token, [',', 'и', 'или']))
compareOperator = Pattern('compareOperator', gt |OR| lt |OR| eq |OR| ge |OR| le)
compare = Pattern('compare', [(notP, '?'), columnLiteralExpr, compareOperator, columnLiteralExpr])
check = Pattern('check', [(notP, '?'), isNullP |OR| isNotNullP, columnExpr])
whereExpr = Pattern('whereExpr', [compare |OR| check, ([logicalConnector, compare |OR| check], '*')])

# Grouping
groupPreposition = Primitive('groupPreposition', lambda token: lemmasCompare(token, ['по', 'среди']))
groupByExpr = Pattern(
  'groupByExpr',
  [groupPreposition, columnExpr, ([connector, (groupPreposition, '?'), columnExpr], '*'), (table, '?')]
)

# Sorting
sortP = Primitive('sort', lambda token: lemmasPart(token, ['сортиров']))
by = Primitive('by', lambda token: lemmasCompare(token, ['по']))
ascP = Primitive('asc', lambda token: lemmasCompare(token, ['возрастание']))
descP = Primitive('desc', lambda token: lemmasCompare(token, ['убывание']))
asc = Pattern('asc', [by, ascP])
desc = Pattern('desc', [by, descP])
sortColumn = Pattern('sortColumn', [(by, '?'), columnExpr, (asc |OR| desc, '?')])
orderByExpr = Pattern('orderByExpr', [sortP, sortColumn, ([connector, sortColumn], '*')])
