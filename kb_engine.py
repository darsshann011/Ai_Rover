"""
kb_engine.py — Propositional Knowledge Base & Resolution Inference Engine

Implements:
  - Clause representation as frozensets of literals (strings).
    Positive literal: "Safe_(2,3)"
    Negative literal: "~Safe_(2,3)"
  - TELL(sentence) — adds clauses, runs unit propagation for eager inference.
  - ASK(query)     — runs PL-RESOLUTION to check if KB |= query.

Design decisions:
  - CNF clauses are frozensets of string literals for hashability and set operations.
  - Unit propagation is run after every TELL for efficiency (derives simple
    consequences immediately without full resolution).
  - Full PL-RESOLUTION is used for ASK queries where the answer is non-trivial.
  - A resolution step limit prevents runaway computation on large KBs.

Assumption: Propositional symbols follow the naming pattern "Property_(x,y)"
where Property is one of: HazardSignal, RadiationSignal, Safe, Visited, Blocked.
"""


def negate(literal):
    """Negate a propositional literal.
    
    'Safe_(2,3)' -> '~Safe_(2,3)'
    '~Safe_(2,3)' -> 'Safe_(2,3)'
    """
    if literal.startswith("~"):
        return literal[1:]
    return "~" + literal


def is_positive(literal):
    """Check if a literal is positive (not negated)."""
    return not literal.startswith("~")


def get_symbol(literal):
    """Extract the symbol name from a literal (strip negation)."""
    if literal.startswith("~"):
        return literal[1:]
    return literal


def make_clause(*literals):
    """Create a CNF clause (frozenset) from literal strings."""
    return frozenset(literals)


def is_tautology(clause):
    """Check if a clause is a tautology (contains both P and ~P)."""
    for lit in clause:
        if negate(lit) in clause:
            return True
    return False


def resolve_pair(ci, cj):
    """
    Resolve two clauses on all complementary literals.
    
    Returns a set of resolvents. Each resolvent is a frozenset of literals.
    If any resolvent is the empty clause, it means a contradiction was derived.
    """
    resolvents = set()
    for li in ci:
        neg_li = negate(li)
        if neg_li in cj:
            # Resolve on this complementary pair
            new_clause = (ci - {li}) | (cj - {neg_li})
            if not is_tautology(new_clause):
                resolvents.add(frozenset(new_clause))
    return resolvents


class KnowledgeBase:
    """Propositional Knowledge Base with Resolution inference."""

    # Maximum resolution steps to prevent infinite loops on large KBs
    MAX_RESOLUTION_STEPS = 5000

    def __init__(self):
        self.clauses = set()          # Set of frozenset clauses (CNF)
        self.facts = {}               # Direct facts: symbol -> True/False (from unit clauses)
        self._tell_log = []           # Log of recent TELL operations (consumed by logger)
        self._ask_log = []            # Log of recent ASK operations (consumed by logger)

    @property
    def clause_count(self):
        return len(self.clauses)

    def tell(self, clause_or_clauses, source=""):
        """
        Add clause(s) to the KB and run unit propagation.

        Args:
            clause_or_clauses: A single frozenset clause, or a list of frozenset clauses.
            source: Human-readable description of why this was told (for logging).

        Returns:
            list of newly inferred facts (symbol, value) pairs from unit propagation.
        """
        if isinstance(clause_or_clauses, frozenset):
            clauses_to_add = [clause_or_clauses]
        else:
            clauses_to_add = list(clause_or_clauses)

        new_clauses = []
        for clause in clauses_to_add:
            if clause not in self.clauses and not is_tautology(clause):
                self.clauses.add(clause)
                new_clauses.append(clause)

        # Run unit propagation on newly added clauses
        inferred = self._unit_propagate(new_clauses)

        # Build log entry
        self._tell_log.append({
            "source": source,
            "new_clauses": new_clauses,
            "inferred": inferred,
            "total_clauses": self.clause_count,
        })

        return inferred

    def _unit_propagate(self, new_clauses):
        """
        Eagerly derive consequences from unit clauses (clauses with one literal).

        When a unit clause {L} is found:
          1. Record the fact: L is true.
          2. Remove all clauses containing L (they're satisfied).
          3. Remove ~L from all remaining clauses (it's false in those).
          4. If this produces new unit clauses, repeat.

        Returns:
            list of (symbol, bool_value) newly inferred facts.
        """
        inferred = []
        queue = [c for c in new_clauses if len(c) == 1]

        while queue:
            unit = queue.pop(0)
            if len(unit) != 1:
                continue
            literal = next(iter(unit))
            symbol = get_symbol(literal)
            value = is_positive(literal)

            # Skip if already known
            if symbol in self.facts:
                if self.facts[symbol] != value:
                    # Contradiction detected — log but don't crash
                    # ASSUMPTION: The percepts from the grid are consistent,
                    # so contradictions indicate a logic bug, not normal operation.
                    pass
                continue

            self.facts[symbol] = value
            inferred.append((symbol, value))

            neg = negate(literal)

            # Simplify KB — collect changes first, then apply (avoid mutating during iteration)
            satisfied = set()
            new_units = []
            to_add = []
            for clause in self.clauses:
                if literal in clause:
                    satisfied.add(clause)
                elif neg in clause:
                    reduced = clause - {neg}
                    if reduced != clause:
                        satisfied.add(clause)
                        if len(reduced) == 0:
                            # Empty clause — contradiction in KB
                            pass
                        else:
                            to_add.append(reduced)
                            if len(reduced) == 1:
                                new_units.append(reduced)

            self.clauses -= satisfied
            self.clauses.update(to_add)
            # Keep unit clauses for the facts we've established
            self.clauses.add(frozenset({literal}))
            queue.extend(new_units)

        return inferred

    def ask(self, query_symbol, positive=True):
        """
        Check if KB entails the query using PL-RESOLUTION.

        To check KB |= Q:
          1. Add ~Q to the KB clauses (temporarily).
          2. Run resolution. If empty clause is derived, KB |= Q.
          3. Clean up temporary clauses.

        Args:
            query_symbol: The propositional symbol to query (e.g., "Safe_(2,3)").
            positive: If True, ask "is query_symbol true?". If False, ask "is ~query_symbol true?".

        Returns:
            bool — True if KB entails the query, False otherwise.
        """
        # Fast path: check direct facts first
        if query_symbol in self.facts:
            result = self.facts[query_symbol] == positive
            self._ask_log.append({
                "query": query_symbol,
                "positive": positive,
                "result": result,
                "method": "direct fact lookup",
                "steps": 0,
            })
            return result

        # Full resolution
        query_literal = query_symbol if positive else negate(query_symbol)
        negated_query = frozenset({negate(query_literal)})

        # Working set = KB clauses + negated query
        working = set(self.clauses)
        working.add(negated_query)

        new = set()
        steps = 0

        clauses_list = list(working)

        while steps < self.MAX_RESOLUTION_STEPS:
            # Try all pairs
            pairs_tried = 0
            new_this_round = set()

            for i in range(len(clauses_list)):
                for j in range(i + 1, len(clauses_list)):
                    resolvents = resolve_pair(clauses_list[i], clauses_list[j])
                    steps += 1

                    for resolvent in resolvents:
                        if len(resolvent) == 0:
                            # Empty clause derived — entailment proved
                            self._ask_log.append({
                                "query": query_symbol,
                                "positive": positive,
                                "result": True,
                                "method": f"resolution ({steps} steps)",
                                "steps": steps,
                            })
                            return True

                        if resolvent not in working and resolvent not in new:
                            new_this_round.add(resolvent)

                    if steps >= self.MAX_RESOLUTION_STEPS:
                        break
                if steps >= self.MAX_RESOLUTION_STEPS:
                    break

            if not new_this_round:
                # No new resolvents — cannot prove entailment
                self._ask_log.append({
                    "query": query_symbol,
                    "positive": positive,
                    "result": False,
                    "method": f"resolution exhausted ({steps} steps)",
                    "steps": steps,
                })
                return False

            working |= new_this_round
            clauses_list = list(working)

        # Step limit reached — conservatively return False (cannot prove)
        # ASSUMPTION: If we can't prove it within the step limit, we treat
        # it as not entailed. This is sound (never claims something is true
        # when it isn't) but incomplete (might miss valid entailments).
        self._ask_log.append({
            "query": query_symbol,
            "positive": positive,
            "result": False,
            "method": f"resolution step limit ({steps} steps)",
            "steps": steps,
        })
        return False

    def ask_is_safe(self, x, y):
        """Convenience: ASK if Safe_(x,y) is entailed."""
        return self.ask(f"Safe_({x},{y})", positive=True)

    def ask_is_blocked(self, x, y):
        """Convenience: ASK if Blocked_(x,y) is entailed."""
        return self.ask(f"Blocked_({x},{y})", positive=True)

    def consume_tell_log(self):
        """Return and clear the TELL log entries (for the logger to consume)."""
        log = list(self._tell_log)
        self._tell_log.clear()
        return log

    def consume_ask_log(self):
        """Return and clear the ASK log entries (for the logger to consume)."""
        log = list(self._ask_log)
        self._ask_log.clear()
        return log

    def get_known_facts_summary(self):
        """Return a dict of all known facts for display."""
        return dict(self.facts)


def encode_percept_rules(x, y):
    """
    Generate the CNF clauses for the standard percept rules at cell (x, y).

    Rules encoded:
      1. HazardSignal_(x,y) -> Blocked_(x,y)
         CNF: {~HazardSignal_(x,y), Blocked_(x,y)}

      2. RadiationSignal_(x,y) -> Blocked_(x,y)
         CNF: {~RadiationSignal_(x,y), Blocked_(x,y)}

      3. ~HazardSignal_(x,y) ^ ~RadiationSignal_(x,y) -> Safe_(x,y)
         CNF: {HazardSignal_(x,y), RadiationSignal_(x,y), Safe_(x,y)}

      4. Blocked_(x,y) -> ~Safe_(x,y)
         CNF: {~Blocked_(x,y), ~Safe_(x,y)}

    Returns:
        list of frozenset clauses.
    """
    h = f"HazardSignal_({x},{y})"
    r = f"RadiationSignal_({x},{y})"
    s = f"Safe_({x},{y})"
    b = f"Blocked_({x},{y})"

    return [
        frozenset({f"~{h}", b}),          # Rule 1: hazard -> blocked
        frozenset({f"~{r}", b}),          # Rule 2: radiation -> blocked
        frozenset({h, r, s}),             # Rule 3: no hazard & no radiation -> safe
        frozenset({f"~{b}", f"~{s}"}),    # Rule 4: blocked -> not safe
    ]
