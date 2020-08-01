from datetime import datetime as dt, timedelta, date
from contextlib import suppress
from constants import aDay
from copy import deepcopy


class Round:
    @staticmethod
    def timedelta(td):
        assert isinstance(td, timedelta)
        return str(td).split('.')[0]

    @staticmethod
    def float(fl):
        assert isinstance(fl, float)
        return round(fl, ndigits=2)

    @staticmethod
    def datetime(d):
        assert isinstance(d, dt)
        return d.replace(microsecond=0, second=0)


def input_until_correct(message, subsequent_try_message, /, parser: callable, **kwargs):

    def wrap_message(message):
        return "   " + message + ": "

    lap = 0
    message = wrap_message(message)
    subsequent_try_message = wrap_message(subsequent_try_message)
    while True:
        if (parsed := parser(input(message), **kwargs)) is not None:
            print()
            return parsed
        lap += 1
        if lap == 1:
            message = subsequent_try_message


def get_confirmation(message = "? Correct") -> bool:
    def parse_confirmation(arg):
        if arg in ("y", "yes"):
            return True
        elif arg in ("n", "no"):
            return False

    print(message)
    return input_until_correct("y|n", "yes|no", parse_confirmation)


def receive_timedelta() -> timedelta:
    def input_hours_minutes() -> (str, str):
        return input('\tHours: '), input('\tMinutes: ')

    h, m = input_hours_minutes()
    print()
    return parse_time_period(h, m)


def show_and_select(choices, exclude = []):
    def parse_cli_input(n: str, choices: int):
        def parse_int(n: str):
            if n.isnumeric():
                return int(n)

        if (num := parse_int(n)) is not None:
            if num in range(1, choices + 1):
                return num

    assert len(choices) >= len(exclude)
    assert len(exclude) == len(set(exclude))
    assert all(el in range(1, len(choices) + 1) for el in exclude)


    left_indices = list(sorted(set(range(len(choices))) - set(i-1 for i in exclude)))
    left = []

    for el in left_indices:
        left.append(choices[el])

    for i, c in enumerate(left):
        print(f"{i+1}. {c.capitalize()}.")

    res = input_until_correct("Enter", "Try again", parse_cli_input, choices = len(left))
    return left_indices[res - 1] + 1


def lazy_yield(x) -> callable:
    return lambda: x


def parse_time_period(hours: str, minutes: str) -> timedelta:
    def within_bounds(duration, upper_bound, lower_bound = 0):
        return lower_bound <= duration <= upper_bound

    with suppress(ValueError, AssertionError):
        assert isinstance(hours, str) and isinstance(minutes, str)

        hours, minutes = int(hours), int(minutes)
        hours += minutes // 60
        minutes %= 60

        assert within_bounds(hours, 24) and within_bounds(minutes, 60)
        assert (tp := timedelta(hours=hours, minutes=minutes)) < aDay

        return tp


print_dc = deepcopy(print)
def print(*args, **kwargs):
    _args = []
    for el in args:
        if isinstance(el, float):
            processed = Round.float(el)
        elif isinstance(el, dt):
            def datetime_to_date_str(dt):
                return str(dt.date())

            freezed_moment = now()
            yesterday = datetime_to_date_str(freezed_moment - aDay)
            today = datetime_to_date_str(freezed_moment)
            tomorrow = datetime_to_date_str(freezed_moment + aDay)

            processed = (str(Round.datetime(el))
            .replace(yesterday, "yesterday")
            .replace(today, "today")
            .replace(tomorrow, "tomorrow")).rsplit(':', maxsplit=1)[0]

        elif isinstance(el, timedelta):
            processed = Round.timedelta(el)
        else:
            processed = el

        _args.append(processed)

    print_dc(*_args, **kwargs)


def now():
    return Round.datetime(dt.now())
