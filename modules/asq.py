"""
  Asq.py

  Main module, contains the parse and translate functions.
"""

from pymystem3 import Mystem
from AbstractRegularExpressions import Primitive, Pattern, PatternToken, Automata, printPattern, OR, Structure
from dbObjects import dbObjects, dbObjectsLemmas, primaryKeys, references, paths
from patterns import Token, selectExpr, whereExpr, groupByExpr, orderByExpr
from OracleTranslator import OracleTranslator
from StructureParser import StructureParser
import json

mystem = Mystem()

structureParser = StructureParser(dbObjects, dbObjectsLemmas)
oracleTranslator = OracleTranslator(primaryKeys, references, paths)

patterns = [Automata(pattern) for pattern in [selectExpr, whereExpr, groupByExpr, orderByExpr]]

# Used for excluding redundant substructures.
class DeadOrAlive:
  def __init__(self, startIndex, finalIndex, data):
    self.startIndex = startIndex
    self.finalIndex = finalIndex
    self.data = data
    self.alive = True

# Parses a query in Russian language to JSON format.
def parse(text):
  analyzed = mystem.analyze(text)
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
      if (not isinstance(dbObjectsLemmas[lemma], list)):
        tokenType = dbObjectsLemmas[lemma]['type']
      else:
        tokenType = 'column'
    elif (text.isnumeric()):
      tokenType = 'number'
    else:
      tokenType = 'text'

    token = Token(text, tokenType, lemma, grammar, len(tokens))
    # print(token)
    for p in patterns: p.feedToken(token)
    tokens.append(token)

  # Pretty print a structure.
  def printStucture(structure, padding=2):
    print((padding - 2)*' ' + f'={structure.name}=' + ' [')
    for a in structure.elements:
      if (isinstance(a, Structure)):
        printStucture(a, padding + 2)
      else:
        print(padding*' ' + f'{a}')
    print((padding - 2)*' ' + ']')

  # Feed token to patterns.
  for p in patterns: p.feedToken(Token('', '', '', '', len(tokens)))
  
  # Eliminating redundant substructures.
  opponents = []
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

  # The left structers, sorted by startIndex.
  structures = [
    opponent.data
    for opponent in sorted(opponents, key = lambda o: o.startIndex)
    if opponent.alive
  ]
  try:
    parsed = {
      'tablesUsed': []
    }
    for structure in structures:
      structureParser.parse(parsed, structure)
    return { 'status': 'success', 'result': parsed }
  except ValueError as err:
    return { 'status': 'error', 'message': str(err) }

# Translates a query in JSON format to SQL-code.
def translate(parsed):
  try:
    SQL = oracleTranslator.translate(parsed['result'])
    return { 'status': 'success', 'result': SQL }
  except ValueError as err:
    return { 'status': 'error', 'message': str(err) }
