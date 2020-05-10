# Abstract Regular Expressions.
# They are like regular expressions, but can work with any kinds of objects,
# not just characters as in regex.
# This code is based on Mark-Jason Dominus's article «How Regexes Work»,
# you can find it here: https://perl.plover.com/Regex/article.html

# NFA - Nondeterministic Finite Automata (machine).

# Used for defining custuom operators.
# http://code.activestate.com/recipes/384122/
class Infix:
  def __init__(self, function):
    self.function = function
  def __ror__(self, other):
    return Infix(lambda x, self=self, other=other: self.function(other, x))
  def __or__(self, other):
    return self.function(other)
  def __rlshift__(self, other):
    return Infix(lambda x, self=self, other=other: self.function(other, x))
  def __rshift__(self, other):
    return self.function(other)
  def __call__(self, value1, value2):
    return self.function(value1, value2)

# Alternatives («|» in regex): a|b|c (in regex) <==> a |OR| b |OR| c (here). 
class Cases:
  def __init__(self, cases):
    self.cases = cases
  def add(self, case):
    self.cases.append(case)
    return self
# Operator for joining cases, used like this: a |OR| b |OR| c.
OR = Infix(lambda x, y: x.add(y) if isinstance(x, Cases) else Cases([x, y]))

# Primitives are used to test one token for some predicate.
# In regex there's only one primitive — whether a token is equal to some character or not.
# Examples of primitives: «is token a table column?», «is token's type — string» etc.
class Primitive:
  def __init__(self, name, predicate):
    self.predicate = predicate
    self.name = name
  def test(self, *args):
    return self.predicate(*args)
  def __str__(self):
    return self.name

# Transitions are the arrows in NFAs,
# one transition leads from one state to another if the pattern's condition is met for a token.
# If there is no pattern (pattern = None), then you can always go to the next state (epsilon-transition).
class Transition:
  def __init__(self, pattern, nextState=None):
    self.pattern = pattern
    self.nextState = nextState

stateID = 0 # Only used for pretty-printing Patterns (machines).
# State is just a bunch of transitions leading to other states or the final state (None).
class State:
  def __init__(self, transitions):
    global stateID
    stateID += 1
    self.ID = stateID
    self.transitions = transitions
  def __str__(self):
    return str(self.ID)

# Recursively creates an NFA
# (makes simple NFAs from primitives and then connects them with connectMachines).
def makeMachine(pattern):
  # Subpatterns are treated the same as primitives.
  if (isinstance(pattern, Pattern) or isinstance(pattern, Primitive)):
    return State({ Transition(pattern) })
  # Make a machine out of each member of a list and then connect them with connectMachines.
  elif (isinstance(pattern, list)):
    if (len(pattern) == 0): return None
    accMachine = makeMachine(pattern[-1])
    for i in range(1, len(pattern)):
      accMachine = connectMachines(makeMachine(pattern[-1 - i]), accMachine)
    return accMachine
  # Quantifiers (+, ?, *).
  elif (isinstance(pattern, tuple)):
    (p, quantifier) = pattern
    machine = makeMachine(p)
    if (quantifier == '+' or quantifier == '*'):
      endTransitions = []
      for state in statesIterator(machine, set()):
        for transition in state.transitions:
          if transition.nextState == None:
            endTransitions.append((state, transition))
      for (state, transition) in endTransitions:
        transition.nextState = machine
        state.transitions.add(Transition(transition.pattern, None))
    if (quantifier == '?' or quantifier == '*'):
      if (len([m for m in machine.transitions if m.pattern == None and m.nextState == None]) == 0):
        machine.transitions.add(Transition(None))
    return machine
  # For cases (a |OR| b |OR| c).
  elif (isinstance(pattern, Cases)):
    return combineMachines([makeMachine(p) for p in pattern.cases])

# Goes through each state of a machine.
def statesIterator(state, passedStates = set()):
  if (state != None): yield state
  else: return
  passedStates.add(state)
  for transition in state.transitions:
    if (not transition.nextState in passedStates):
      for s in statesIterator(transition.nextState, passedStates):
        yield s

# Connects two machine into one (replaces finish states of machineA with start states of machineB).
def connectMachines(machineA, machineB):
  endTransitions = []
  for state in statesIterator(machineA, set()):
    for transition in state.transitions:
      if transition.nextState == None:
        endTransitions.append(transition)
  for transition in endTransitions:
    transition.nextState = machineB
  return machineA

# Connects cases of machines (machineA |OR| machineB |OR| ... |OR| machineN) into one machine.
def combineMachines(machines):
  return State({ t for machine in machines for t in machine.transitions })

# Pattern, as in regular expressions.
# Example: p = Pattern('name', [a, b, c, (d, '+') |OR| e])
# which gives you a regex «abc(d+|e)»,
# where a, b, c, d and e are another patterns or primitives.
class Pattern:
  def __init__(self, name, pattern):
    global stateID
    stateID = 0
    self.name = name
    self.machine = makeMachine(pattern)
  def __str__(self):
    return self.name

class Structure:
  def __init__(self, name, elements=None):
    self.name = name
    self.elements = elements if elements != None else []
  def __str__(self):
    return f' --- {self.name} --- \n{[str(el) for el in self.elements]}'

class PatternToken:
  def __init__(self, pattern, token):
    self.pattern = pattern
    self.token = token
  def __str__(self):
    return f'{self.pattern}: {self.token.text}'

class CurrentState:
  def __init__(self, token, transition=None, previousState=None, patternsStack=[]):
    self.transition = transition
    self.token = token
    self.previousState = previousState
    self.patternsStack = patternsStack
  def __str__(self):
    t = self.token.text if self.token != None else ''
    return f'== [{self.transition.pattern.name} ({len(self.patternsStack)}): {t}]\n{self.previousState}'
  def connect(self, name):
    state = self
    structuresStack = []
    result = []
    indexes = []
    while True:
      token = state.token
      transition = state.transition
      if (isinstance(transition.pattern, Pattern)):
        if (len(structuresStack) == 0):
          structuresStack.append(Structure(transition.pattern.name))
        else:
          structure = structuresStack.pop()
          structure.elements = structure.elements[::-1]
          result.append(structure)
      elif (isinstance(transition.pattern, Primitive)):
        indexes.append(token.index)
        if (len(structuresStack) == 0):
          result.append(PatternToken(transition.pattern, token))
        else:
          structuresStack[-1].elements.append(PatternToken(transition.pattern, token))
      state = state.previousState
      if (state == None): break
    return ((min(indexes), max(indexes)), Structure(name, result[::-1]))

# Used for running a pattern on a list of tokens.
class Automata:
  def __init__(self, pattern):
    self.pattern = pattern
    self.finalStates = set()
    self.currentStates = set()
  def feedToken(self, token):
    currentStates = set(self.currentStates)
    self.currentStates = set()
    for state in currentStates:
      for transition in state.transition.nextState.transitions:
        self.processTransition(transition, token, state)
    for transition in self.pattern.machine.transitions:
      self.processTransition(transition, token)
  def __str__(self):
    return "\n\n".join([str(state) for state in self.finalStates])
  def processTransition(self, transition, token, previousState=None):
    # Epsilon
    if (transition.pattern == None):
      if (transition.nextState != None):
        for t in transition.nextState.transitions:
          self.processTransition(t, token, previousState)
      elif (len(previousState.patternsStack) == 0):
        self.finalStates.add(previousState)
      else:
        newState = previousState
        while True:
          if (len(newState.patternsStack) == 0):
            self.finalStates.add(newState)
            break
          patternsStack = list(newState.patternsStack)
          patternState = patternsStack.pop()
          newState = CurrentState(None, patternState.transition, newState, patternsStack)
          if (newState.transition.nextState != None):
            self.processTransition(newState.transition, token, newState)
            break
    # Primitive
    elif (isinstance(transition.pattern, Primitive)):
      if (transition.pattern.test(token)):
        patternsStack = previousState.patternsStack if previousState != None else []
        newState = CurrentState(token, transition, previousState, list(patternsStack))
        if (newState.transition.nextState != None):
          self.currentStates.add(newState)
        elif (len(newState.patternsStack) == 0):
          while True:
            if (len(newState.patternsStack) == 0):
              self.finalStates.add(newState)
              break
            patternsStack = list(newState.patternsStack)
            patternState = patternsStack.pop()
            newState = CurrentState(None, patternState.transition, newState, patternsStack)
            if (newState.transition.nextState != None):
              self.currentStates.add(newState)
              break
    # Pattern
    elif (isinstance(transition.pattern, Pattern)):
      patternsStack = previousState.patternsStack if previousState != None else []
      newState = CurrentState(None, transition, previousState, list(patternsStack))
      newState.patternsStack.append(newState)
      for t in transition.pattern.machine.transitions:
        self.processTransition(t, token, newState)

# Pretty-print a machine.
def printMachine(machine):
  padding = 0
  for state in statesIterator(machine, set()):
    for t in state.transitions:
      print(padding*' ' + f'{state}: --{t.pattern}->{t.nextState}')
    padding += 1


# Pretty-print a pattern.
def printPattern(pattern):
  print(f'-=-=-=-=-= {pattern.name} =-=-=-=-=-')
  printMachine(pattern.machine)
