from pymystem3 import Mystem
from AbstractRegularExpressions import Primitive, Pattern, PatternToken, Automata, printPattern, OR, Structure

import timeit

mystem = Mystem()

dbObjects = [
  {
    'type': 'table',
    'scheme': 'hr',
    'name': 'employees',
    'lemmas': ['сотрудник', 'работник']
  },
  {
    'type': 'table',
    'scheme': 'hr',
    'name': 'departments',
    'lemmas': ['отдел', 'подразделение', 'департамент']
  },
  {
    'type': 'table',
    'scheme': 'hr',
    'name': 'countries',
    'lemmas': ['страна', 'государство']
  },
  {
    'type': 'column',
    'scheme': 'hr',
    'table': 'employees',
    'name': 'last_name',
    'lemmas': ['фамилия']
  },
  {
    'type': 'column',
    'scheme': 'hr',
    'table': 'employees',
    'name': 'first_name',
    'lemmas': ['имя']
  },
  {
    'type': 'column',
    'scheme': 'hr',
    'table': 'employees',
    'name': 'salary',
    'lemmas': ['зарплата', 'получка', 'оклад', 'заработок']
  },
  {
    'type': 'column',
    'scheme': 'hr',
    'table': 'employees',
    'name': 'manager_id',
    'lemmas': ['менеджер', 'начальник', 'руководитель']
  },
]
dbObjectsLemmas = {}
for obj in dbObjects:
  for lemma in obj['lemmas']:
    dbObjectsLemmas[lemma] = obj

class Token:
  def __init__(self, text, tokenType='text', lemma='', grammar='', index=-1):
    self.text = text
    self.type = tokenType
    self.lemma = lemma
    self.grammar = grammar
    self.index = index
  def __str__(self):
    return str({ 'type': self.type, 'text': self.text, 'lemma': self.lemma, 'grammar': self.grammar, 'index': self.index })

def textCompare(token, texts):
  for t in texts:
    if t == token.text: return True
  return False

def lemmasTextCompare(token, lemmas):
  text = token.text if not token.lemma else token.lemma
  for l in lemmas:
    if l == text: return True
  return False

connector = Primitive('connector', lambda token: lemmasTextCompare(token, [',', 'и']))
table = Primitive('table', lambda token: token.type == 'table')
column = Primitive('column', lambda token: token.type == 'column')
listOfTables = Pattern('listOfTables', [table, ([connector, table], '*')])
listOfColumns = Pattern('listOfColumns', [column, ([connector, column], '*'), (table, '?')])
selectExpr = Pattern('selectExpr', [listOfColumns |OR| listOfTables])

literal = Primitive('literal', lambda token: token.type in ['number', 'text'])
gt = Primitive('gt', lambda token: textCompare(token, ['>', 'больше']))
lt = Primitive('lt', lambda token: textCompare(token, ['<', 'меньше']))
eq = Primitive('eq', lambda token: lemmasTextCompare(token, ['=', 'равный']))
compare = Pattern('compare', [column |OR| literal, gt |OR| lt |OR| eq, column |OR| literal])
logicalConnector = Primitive(
  'logicalConnector',
  lambda token: lemmasTextCompare(token, [',', 'и', 'или'])
)
whereExpr = Pattern('whereExpr', [compare, ([logicalConnector, compare], '*')])

class StructureParser:
  patternToSQL = {
    'gt': ' > ',
    'lt': ' < ',
    'ge': ' >= ',
    'le': ' <= ',
    'eq': ' = '
  }
  def __init__(self, dbObjects, dbObjectsLemmas):
    self.dbObjects = dbObjects
    self.dbObjectsLemmas = dbObjectsLemmas
  def getDbObjectName(self, patternToken):
    obj = self.dbObjectsLemmas[patternToken.token.lemma]
    scheme = obj['scheme']
    name = obj['name']
    return f'{scheme}.{name}'
  def parseLiteral(self, patternToken):
    return patternToken.token.text
  def parseLogicalConnector(self, patternToken):
    operator = patternToken.token.lemma
    return {
      ',': ' AND ',
      'и': ' AND ',
      'или': ' OR '
    }[operator]
  def parseCompare(self, structure):
    result = ''
    for patternToken in structure.elements:
      if (patternToken.pattern.name == 'column'): result += self.getDbObjectName(patternToken)
      elif (patternToken.pattern.name == 'literal'): result += self.parseLiteral(patternToken)
      else: result += self.patternToSQL[patternToken.pattern.name]
    return result
  def parseWhereExpr(self, structure):
    result = ''
    for element in structure.elements:
      if (isinstance(element, Structure)):
        if (element.name == 'compare'):
          result += self.parseCompare(element)
      else:
        if (element.pattern.name == 'logicalConnector'):
          result += self.parseLogicalConnector(element)
    return result

structureParser = StructureParser(dbObjects, dbObjectsLemmas)

# print(structureParser.getDbObjectName(PatternToken(column, Token(text='сотрудников', lemma='сотрудник'))))
# print(structureParser.parseLogicalConnector(PatternToken(logicalConnector, Token(text='или', lemma='или'))))

# def parseStructure(structure):
#   if (structure.name == '')


patterns = [Automata(pattern) for pattern in [selectExpr, whereExpr]]
# patterns = [Automata(pattern) for pattern in [selectExpr]]

class DeadOrAlive:
  def __init__(self, startIndex, finalIndex, data):
    self.startIndex = startIndex
    self.finalIndex = finalIndex
    self.data = data
    self.alive = True

def parse(text):
  analyzed = analyze(text)
  tokens = []
  for index, token in enumerate(analyzed):
    text = token['text'].strip()
    if (text == ""):
      continue
    analysis = {}
    if ('analysis' in token and len(token['analysis']) > 0):
      analysis = token['analysis'][0]
    lemma = analysis['lex'] if 'lex' in analysis else ''
    grammar = analysis['gr'] if 'gr' in analysis else ''

    tokenType = ''
    if (lemma in dbObjectsLemmas):
      tokenType = dbObjectsLemmas[lemma]['type']
    elif (text.isnumeric()):
      tokenType = 'number'
    else:
      tokenType = 'text'

    token = Token(text, tokenType, lemma, grammar, len(tokens))
    # print(token)
    for p in patterns: p.feedToken(token)
    tokens.append(token)

  def printStucture(structure, padding=2):
    print((padding - 2)*' ' + f'--{structure.name}--')
    for a in structure.elements:
      if (isinstance(a, Structure)):
        printStucture(a, padding + 2)
      else:
        print(padding*' ' + f'{a}')

  for p in patterns: p.feedToken(Token('', '', '', '', len(tokens)))
  
  opponents = [] # We will eliminate redundant substructures.
  for p in patterns:
    for f in p.finalStates:
      ((startIndex, finalIndex), structure) = f.connect(p.pattern.name)
      opponents.append(DeadOrAlive(startIndex, finalIndex, structure))
  for opponentA in opponents:
    for opponentB in opponents:
      if (opponentA == opponentB): continue
      if (opponentA.finalIndex < opponentB.startIndex or opponentB.finalIndex < opponentA.startIndex):
        continue # If they don't cross, continue.
      lengthA = opponentA.finalIndex - opponentA.startIndex
      lengthB = opponentB.finalIndex - opponentB.startIndex
      if   (lengthA > lengthB): opponentB.alive = False
      elif (lengthB > lengthA): opponentA.alive = False
      elif (opponentA.alive and opponentB.alive):
        if (str(opponentA.data) == str(opponentB.data)):
          opponentB.alive = False

  structures = [opponent.data for opponent in opponents if opponent.alive]
  for s in structures:
    printStucture(s)
    # if (s.name == 'whereExpr'):
    #   print(structureParser.parseWhereExpr(s))
    print('\n\n')

  pseudoCode = f'Parsed your text "{text}"'
  return pseudoCode


def analyze(text):
  # nameMatches = namesExtractor(text)
  # for match in nameMatches:
  #   print(match.span, match.fact)
  return mystem.analyze(text)

# text = 'выведи сотрудников, отделы и страны'
# text = 'выведи фамилию, имя и зарплату'
text = 'Вывести имя, фамилию и зарплату сотрудников с зарплатой больше 10000'
parse(text)

# print(timeit.timeit("parse('фамилия равна имени или зарплата > 10000')", setup="from __main__ import parse", number=5))

