from __future__ import annotations

import builtins
import operator
from typing import Iterable, List, Set, Tuple
from .expression import Variable, Expression, Context, Constant, FunctionApplication
from .basic_expression import BasicExpression
from .z3_expression import Z3SolverExpression, Z3Expression


class ClosedInterval(BasicExpression):
    """ [lower_bound, upper_bound] """
    def __init__(self, lower_bound, upper_bound):
        super().__init__(Set)
        self._lower_bound = lower_bound
        self._upper_bound = upper_bound

    @property
    def lower_bound(self) -> Expression:
        return self._lower_bound

    @property
    def upper_bound(self) -> Expression:
        return self._upper_bound

    @property
    def subexpressions(self) -> List[Expression]:
        return [self.lower_bound, self.upper_bound]

    def set(self, i: int, new_expression: Expression) -> Expression:
        if i == 0:
            return ClosedInterval(new_expression, self.upper_bound)
        if i == 1:
            return ClosedInterval(self.lower_bound, new_expression)
        raise IndexError("out of scope.")

    def replace(self, from_expression: Expression, to_expression: Expression) -> Expression:
        if self.syntactic_eq(from_expression):
            return to_expression
        return ClosedInterval(self.lower_bound.replace(from_expression, to_expression),
                              self.upper_bound.replace(from_expression, to_expression))

    def internal_object_eq(self, other) -> bool:
        if not isinstance(other, ClosedInterval):
            return False
        return self.lower_bound.internal_object_eq(other.lower_bound) and \
               self.upper_bound.internal_object_eq(other.upper_bound)

    def __iter__(self) -> Iterable[Int]:
        """
        If upper and lower bounds are constant, return a range that's iterable.
        Otherwise, raise
        """
        match self.lower_bound, self.upper_bound:
            case Constant(value=l, type=builtins.int), Constant(value=r, type=builtins.int):
                return range(l, r)
            case _:
                raise TypeError("Lower and upper bounds must both be Constants!")

    @property
    def size(self) -> Expression:
        return self.upper_bound - self.lower_bound + 1

    def to_context(self, index: Variable) -> Context:
        result = Z3SolverExpression() & index >= self.lower_bound & index <= self.upper_bound
        assert isinstance(result, Context)  # otherwise lower_bound <= upper_bound is unsatisfiable
        return result


class DottedIntervals(BasicExpression):
    def __init__(self, interval: ClosedInterval, dots: List[Expression]):
        super().__init__(Set)
        self._interval = interval
        self._dots = dots

    @property
    def interval(self) -> ClosedInterval:
        return self._interval

    @property
    def dots(self) -> List[Expression]:
        return self._dots

    @property
    def subexpressions(self) -> List[Expression]:
        return [self.interval] + self.dots

    def set(self, i: int, new_expression: Expression) -> Expression:
        raise NotImplementedError("TODO")

    def replace(self, from_expression: Expression, to_expression: Expression) -> Expression:
        raise NotImplementedError("TODO")

    def internal_object_eq(self, other) -> bool:
        raise NotImplementedError("TODO")

    @property
    def __iter__(self) -> Iterable[Constant]:
        raise NotImplementedError("TODO")


def from_constraints(index: Variable, constraint: Context) -> Expression:
    """
    @param index:
    @param constraint:
    @return: an if-then-else tree whose leaves are DottedIntervals

    This currently only supports the most basic of constraints
    For example, x > 0 and x <= 5
    This should return an interval [1, 5]
    More complicated cases will be added later
    """
    closed_interval = ClosedInterval(None, None)
    exceptions = []
    for subexpression in constraint.subexpressions:
        if (isinstance(subexpression, FunctionApplication)):
            closed_interval, exceptions = _extract_bound_from_constraint(index, subexpression, closed_interval, exceptions)

    return DottedIntervals(closed_interval, exceptions)

def _extract_bound_from_constraint(
    index: Variable,
    constraint: Expression,
    closed_interval: ClosedInterval,
    exceptions: List[Expression]
) -> Tuple(ClosedInterval, List[Expression]):
    """
    Helper function for from_constraints
    Gets the possible lower or upper bound
    Sets the possible bound if it's greater than the current lower or less than the current upper
    """
    possible_inequality = constraint.subexpressions[0].value

    variable_index = None
    bound = None
    if constraint.subexpressions[1].syntactic_eq(index):
        variable_index = 1
        bound = constraint.subexpressions[2]
    elif constraint.subexpressions[2].syntactic_eq(index):
        variable_index = 2
        bound = constraint.subexpressions[1]
    else:
        raise ValueError("intervals is not yet ready to handle more complicated cases")

    match possible_inequality:
        case operator.ge:
            if variable_index == 1:
                closed_interval, exceptions = _check_and_set_bounds(0, bound, closed_interval, exceptions)
            if variable_index == 2:
                closed_interval, exceptions = _check_and_set_bounds(1, bound, closed_interval, exceptions)
        case operator.le:
            if variable_index == 1:
                closed_interval, exceptions = _check_and_set_bounds(1, bound, closed_interval, exceptions)
            if variable_index == 2:
                closed_interval, exceptions = _check_and_set_bounds(0, bound, closed_interval, exceptions)
        case operator.gt:
            if variable_index == 1:
                bound = Z3Expression.new_constant(bound.value + 1)
                closed_interval, exceptions = _check_and_set_bounds(0, bound, closed_interval, exceptions)
            if variable_index == 2:
                bound = Z3Expression.new_constant(bound.value - 1)
                closed_interval, exceptions = _check_and_set_bounds(1, bound, closed_interval, exceptions)
        case operator.lt:
            if variable_index == 1:
                bound = Z3Expression.new_constant(bound.value - 1)
                closed_interval, exceptions = _check_and_set_bounds(1, bound, closed_interval, exceptions)
            if variable_index == 2:
                bound = Z3Expression.new_constant(bound.value + 1)
                closed_interval, exceptions = _check_and_set_bounds(0, bound, closed_interval, exceptions)
        case _:
            raise ValueError(f"interval doesn't support {possible_inequality} yet")
    return closed_interval, exceptions

def _check_and_set_bounds(
    index: int,
    bound: Expression,
    closed_interval: ClosedInterval,
    exceptions: List[Expression]
) -> Tuple(ClosedInterval, List[Expression]):
    match index:
        case 0:
            if closed_interval.lower_bound is None or bound >= closed_interval.lower_bound():
                closed_interval = closed_interval.set(0, bound)
        case 1:
            if closed_interval.upper_bound is None or bound <= closed_interval.upper_bound():
                closed_interval =  closed_interval.set(1, bound)
        case _:
            raise IndexError(f"{index} is out of bounds")

    return closed_interval, exceptions
