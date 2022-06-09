"""
Test of Z3Py. Most parts are covered in `https://ericpony.github.io/z3py-tutorial/guide-examples.htm`.
"""
from z3 import Solver, Not, sat, unsat, Int, Implies, Or, simplify, Ints, And, Reals, BitVecVal, Function, IntSort, \
    ForAll, Exists, ExprRef, Sum


def is_valid(predicate: ExprRef) -> bool:
    """
    If we want to ask Z3 to check if a predicate PRED is valid (i.e., always true), we need to
    ask in a not very intuitive way: "is `not PRED` unsatisfiable?"
    If `not PRED` is sat, then PRED is NOT always true, since there must exist a counter-example that satisfies
    `not PRED`, which we can get by calling s.model().
    If `not PRED` is unsat, then PRED is always true.
    """
    s = Solver()
    s.add(Not(predicate))
    return s.check() == unsat


def test_is_valid():
    """ Test that is_valid() is implemented correctly. """
    x = Int('x')
    assert is_valid(Or(x > 0, x <= 0))
    assert is_valid(Implies(x > 1, x > 0))
    assert not is_valid(x > 0)
    assert not is_valid(Implies(x > 0, x > 1))


def test_z3_simplification():
    """ Test of z3's simplify() function. """
    x, y = Ints('x y')

    # simplify() can perform some trivial simplification.
    # == and != are overloaded. So we just use repr().
    assert repr(simplify(x < y + x + 2)) == "Not(y <= -2)"

    # We start from two equivalent condition. Ideally we want to derive cond2 automatically from cond1.
    cond1 = And(x > 2, x < 4)
    cond2 = x == 3
    # However, Z3 cannot simplify 2 < x < 4 into x == 3
    assert repr(simplify(cond1)) == "And(Not(x <= 2), Not(4 <= x))"
    # But we can always ask z3 to solve the problem "is 2 < x < 4 equivalent to x == 3?"
    assert is_valid(cond1 == cond2)


def test_z3_solve_nonlinear_polynomial():
    """
    Z3 can solve nonlinear polynomial constraints,although to a lesser extent than SymPy which
    also supports powers, exp/log and trigonometric.
    """
    x, y = Reals('x y')
    s = Solver()
    s.add(x ** 2 + y ** 2 > 3, x ** 3 + y < 5)
    assert s.check() == sat
    # one can call always s.model() to get a solution if check() == sat


def test_bitvec():
    """ BitVec is Z3's term for bit-vector. For example, 16-bit integer is a bit-vector. """
    a = BitVecVal(-1, 16)
    b = BitVecVal(65535, 16)
    assert is_valid(a == b)  # -1 (signed) is 65535 (unsigned) in 16-bit representation.
    a = BitVecVal(-1, 32)
    b = BitVecVal(65535, 32)
    assert is_valid(a != b)  # -1 is not 65535 in 32-bit representation.


def test_function():
    """ In Z3, functions are uninterpreted and total. Uninterpreted means it's just a name, we cannot give it
    any definition or interpretation; total means it has no side effects, like functions in functional language.
    """
    x = Int('x')
    f = Function('f', IntSort(), IntSort())
    assert is_valid(Implies(f(x) == x, f(f(f(x))) == x))


def test_quantifier():
    """ Z3 also supports quantifiers, such as `forall`, `exists`. """
    x, y = Ints('x y')
    f = Function('f', IntSort(), IntSort(), IntSort())
    assert is_valid(Implies(ForAll([x, y], f(x, y) >= x), f(0, 5) >= 0))  # if forall x y, f(x,y)>=x, then f(0,5)>=0
    assert is_valid(Implies(Exists([x], f(x, y) == x), Not(ForAll([x], f(x, y) != x))))  # exists


def test_sum():
    """
    `Sum` is not a quantifier in Z3, it's just an interpreted function.
    """
    # simple usage of Sum()
    x, i = Ints('x i')
    assert is_valid(Sum([1, 2, x]) == x + 3)
    # Now, say we want to check the theorem of Gauss Summation: 1 + 2 + ... n = (1 + n) * n / 2,
    # we can only do this when n is static to Z3.
    # We cannot state something like "forall n, 1 + 2 + ... n = (1 + n) * n / 2"
    N = 1000
    assert (is_valid(Sum([j for j in range(N+1)]) == (1 + N)*N/2))
    assert (is_valid(Sum([x for _ in range(N+1)]) == (1 + N)*x))
    assert (is_valid(Sum([x + j for j in range(N+1)]) == (1 + N)*x + (1 + N)*N/2))
