from datetime import datetime as dt, timedelta, date
from contextlib import contextmanager, suppress
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from os import path
import toml
from copy import deepcopy
import functools

ALTER_LOG = False

aDay = timedelta(days=1)

datetime_fmt = "%d-%m-%Y, %H:%M:%S"
timedelta_fmt = "%H:%M:%S"



print_dc = deepcopy(print)
def _print(*args, **kwargs):
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
            .replace(tomorrow, "tomorrow"))

        elif isinstance(el, timedelta):
            processed = Round.timedelta(el)
        else:
            processed = el

        _args.append(processed)

    print_dc(*_args, **kwargs)

print = _print
 

class File(ABC):

    def exists(self):
        return path.exists(self.FILE__NAME)

    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def load(self):
        pass

    @contextmanager
    def open(self, mode):
        try:
            file = open(self.FILE__NAME, mode)
            yield file
        finally:
            file.close()


class Act(Enum):
    asleep = "asleep"
    awake = "awake"

@dataclass
class LogRow:
    state: Act
    time: dt

    def as_str(self):
        return f'{self.state.value} {self.time.strftime(datetime_fmt)}\n'

    @staticmethod
    def parse(row: str, failproof=False):
        try:
            state, time = row.rstrip('\n').split(maxsplit=1)
            for state_name, _state in Act.__members__.items():
                if state_name == state:
                    state: Act = _state
                    break
            else:
                raise Exception("Invalid state", state)
            
            time: dt = dt.strptime(time, datetime_fmt)

            return LogRow(state=state, time=time)
        except:
            if failproof:
                return ""
            else:
                raise


@dataclass
class Config(File):
    rest_per_day: str

    FILE__NAME = "conf.toml"

    def __init__(self):
        if not self.exists():
            self.create()

        self.get_data()
        self.rest_per_day = self.data['rest_per_day']


    def load(self):
        assert self.exists()
        return toml.load(self.FILE__NAME)

    @staticmethod
    def receive_data():

        print('? Planned rest per day')
        
        try:
            td: timedelta = receive_timedelta()
        except (ValueError, AssertionError):
            exit('Invalid input')


        data = dict(rest_per_day = str(td))

        return data

    def create(self):
        print(': SETUP\n')

        data = self.receive_data()

        with self.open('w') as conf_file:
            toml.dump(data, conf_file)

    def update(self):
        self.create()

    def get_data(self):
        def notify_update_load_config():
            print('! Config file is corrupped')
            self.update()
            data = self.load()
            return data
                
        data = self.load()

        for field_name, field in self.__dataclass_fields__.items():
            if not isinstance(data.get(field_name), field.type):
                data = notify_update_load_config()
                break

        if not (rpd := parseHM_(data['rest_per_day'])):
            data = notify_update_load_config()
        else:
            data['rest_per_day'] = rpd

        self.data = data


class Log(File):
    FILE__NAME = "log.txt"


    def __init__(self):
        if not self.exists():
            self.create()
        
        self.get_content()
        self.sync()

    def load(self):
        assert self.exists()
        with self.open('r') as log_file:
            return log_file.readlines()

    def create(self):
        with self.open('w'): pass

    def get_content(self):
        try:
            self.content = list(LogRow.parse(row) for row in self.load())

            if self.content:
                assert self.check_pair(self.last_session)
        except:
            print("! Log seems to be corrupted")
            confirm = get_confirmation("? Try to repair automatically")

            if confirm:
                self.repair()
                print("! Considering data was corrupted, first\n"
                        "  calcultations may not be accurate.\n")

            else: exit()


    def append(self, log_row: LogRow):
        assert isinstance(log_row, LogRow)
        self.content.append(log_row)

        with self.open('a') as log_file:
            log_file.write(log_row.as_str())

    def sync(self):
        assert hasattr(self, "content")

        with self.open('w') as log_file:
            log_file.writelines(map(lambda row: row.as_str(), self.content))


    ### It won`t save againts drastical
    ### manual log interruption. So don`t.
    def repair(self):
        assert self.exists()

        repaired_records = []

        for row in self.load():
            if record := LogRow.parse(row, failproof=True):
                repaired_records.append(record)

        if repaired_records and repaired_records[-1].state is not Act.awake:
            del repaired_records[-1]
        
        self.content = repaired_records
        
        
    @staticmethod
    def check_pair(pair):
        asleep, awake = pair
        return asleep.state is Act.asleep and awake.state is Act.awake

    def alter_last_session(self, f: callable):
        ls_start, ls_end = self.last_session
        while True:
            if (changed_session := f(ls_start, ls_end)) is not None:
                self.last_session = changed_session
                break

        self.last_session = ls_start, ls_end

    @property
    def last_session(self):
        if len(self.content) > 1:
            result = self.content[-2:]
            assert self.check_pair(result)
        else:
            result = []
        
        return result

    @last_session.setter
    def last_session(self, tup):
        assert self.check_pair(tup)
        self.content[-2] = tup[0]
        self.content[-1] = tup[1]

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


def now():
    return Round.datetime(dt.now())

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
        if arg == "y" or arg == "yes":
            return True
        elif arg == "n" or arg == "no":
            return False

    print(message)
    return input_until_correct("y|n", "yes|no", parse_confirmation)

def receive_timedelta() -> timedelta:
    def input_hours_minutes() -> (str, str):
        return input('\tHours: '), input('\tMinutes: ')

    h, m = input_hours_minutes()
    print()
    return parse_time_period(h, m)

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


def parseHM_(s):
    h, m, _ = s.split(':')
    return parse_time_period(h, m)


def parse_cli_input(n: str, choices: int):
    def parse_int(n: str):
        if n.isnumeric():
            return int(n)

    if (num := parse_int(n)) is not None:
        if num in range(1, choices + 1):
            return Level(num)

def show_and_select(choices):
    for i, c in enumerate(choices):
        print(f"{i+1}. {c.capitalize()}.")

    return input_until_correct("Enter", "Try again", parse_cli_input, choices = len(choices))

def lazy_yield(x) -> callable:
    return lambda: x

def get_asleep_awake(duration: timedelta, start: callable = now):
    start = start()
    end = start + duration
    asleep = LogRow(state=Act.asleep, time=start)
    awake = LogRow(state=Act.awake, time=end)
    return asleep, awake

def alter_record_time_by_td(record, fname: str):
    td = receive_timedelta()
    return getattr(record.time, fname)(td)

def calculate_amount_of_sleep(log, rest_per_day, time_limiter = 4 * aDay):
    
    def get_latest_records(log):
        nonlocal time_limiter
        begin = now()
        start_moment = begin - time_limiter

        if log:
            for i, record in enumerate(log):
                if record.time >= start_moment:
                    if record.state is Act.awake:
                        log = log[i-1:]
                    elif record.state is Act.asleep:
                        log = log[i:]

                    time_limiter = begin - log[0].time
                    break
        return log

    def get_sleep_amount(records):
        total = timedelta()
        for i in range(0, len(records), 2):
            total += records[i+1].time - records[i].time

        return total

    def get_awake_amount(records):
        records.append(
            LogRow(
                state=Act.asleep,
                time=now()
            )
        )

        total = timedelta()
        for i in range(1, len(records), 2):
            assert records[i+1].time > records[i].time
            # print('Awake from', records[i].time, "to", records[i+1].time, 'Delta:', records[i+1].time - records[i].time)
            total += records[i+1].time - records[i].time

        return total

    def get_timeline(records):
        assert records
        return records[0].time, records[-1].time

    def get_timeline_delta(records):
        start, end = get_timeline(records)
        return end - start

    if latest_records := get_latest_records(log):
        latest_sleep_amount = get_sleep_amount(latest_records)
        latest_awake_amount = get_awake_amount(latest_records)

        gap = get_timeline_delta(latest_records)

        assert gap == latest_sleep_amount + latest_awake_amount

        print("Gap", gap)
        print("Slept", latest_sleep_amount)
        print("Was awake", latest_awake_amount)

        result = ((rest_per_day / aDay) * gap - latest_sleep_amount) / (1 - (rest_per_day / aDay))
    else:
        result = rest_per_day

    return result


class Clock:
    hours = list(range(0, 25))

    @classmethod
    def between(cls, start, end):
        if start <= end:
            return cls.hours[start:end+1]
        else:
            return cls.hours[start:] + cls.hours[:end+1]

    @classmethod
    def part_of_day(cls):
        this_hour = now().hour

        if this_hour in cls.between(4, 11):
            return "morning"
        elif this_hour in cls.between(12, 16):
            return "afternoon"
        elif this_hour in cls.between(17, 20):
            return "evening"
        elif this_hour in cls.between(21, 3):
            return "night"



class Level:

    def __init__(self, *sub_levels):
        assert all(isinstance(el, int) for el in sub_levels)
        self.levels: list = sub_levels
        self.parent = Level(*sub_levels[:-1]) if len(sub_levels) > 1 else None

    def __str__(self):
        return f"{self.__class__.__name__}({':'.join(map(lambda self: str(self), self.levels))})"

    def __repr__(self):
        return str(self)

    def __bool__(self):
        return self.levels != (0,)

    def __add__(self, other):
        if isinstance(other, Level):
            if not self:
                return other
            else:
                return Level(*(self.levels + other.levels))
        else:
            raise NotImplemented

    def __eq__(self, other):
        if isinstance(other, Level):
            return self.levels == other.levels
        else:
            raise NotImplemented

@dataclass
class Route:
    contents = {}

    destination: Level
    message: str = None

    @classmethod
    def new(cls, lvl):
        assert isinstance(lvl, Level)
        def decorator_route(func):
            @functools.wraps(func)
            def wrapper_route(*args, **kwargs):
                if isinstance((res := func(*args, **kwargs)), Level):
                    return lvl + res
                elif isinstance(res, Route):
                    if transition_message := res.message:
                        print(transition_message, end="\n\n")

                    return res.destination
                else:
                    return res
                
            cls._set(lvl, wrapper_route)
            return wrapper_route

        return decorator_route

    @classmethod
    def get(cls, lvl):
        return cls.contents.get(str(lvl))

    @classmethod
    def _set(cls, lvl, func):
        assert cls.contents.get(str(lvl)) is None, "ambiguity in levels hierarchy"
        cls.contents[str(lvl)] = func



@Route.new(Level(0))
def welcoming(config, log):
    print(f"\nGood {Clock.part_of_day()}. Please select:")
    case = show_and_select([
        "calculate sleep duration",
        "tune the previous sleep session",
        "update configuration",
        "quit",
    ])

    return case

@Route.new(Level(1))
def calc(config, log):
    sleep_for = calculate_amount_of_sleep(log.content, config.rest_per_day)

    if sleep_for < timedelta():
        print("You should not sleep for at least", abs(sleep_for))
    else:
        if ALTER_LOG:
            asleep, awake = get_asleep_awake(sleep_for)
            log.append(asleep)
            log.append(awake)

        print("\nSleep for", sleep_for, "\nSet alarm to", now() + sleep_for)

    return sleep_for

@Route.new(Level(2))
def correct(config, log):
    case = show_and_select([
        "woke up early",
        "woke up late",
        "fell asleep early",
        "fell asleep late",
        "back",
    ])

    return case



@Route.new(Level(2, 1))
def overslept(config, log):

    def alter(ls_start, ls_end):
        print("? You overslept by")
        
        new_dt = alter_record_time_by_td(ls_end, '__add__')

        print("You awoke at", new_dt)

        if get_confirmation():
            ls_end.time = new_dt
            return ls_start, ls_end


    log.alter_last_session(alter)

    return Route(Level(2), message = "You can also tune the time when you fell asleep")


@Route.new(Level(2, 2))
def underslept(config, log):

    def alter(ls_start, ls_end):
        print("? You underslept by")
        
        new_dt = alter_record_time_by_td(ls_end, '__sub__')

        print("You awoke at", new_dt)

        if get_confirmation():
            ls_end.time = new_dt
            return ls_start, ls_end

    log.alter_last_session(alter)

    return Route(Level(2), message = "You can also tune the time when you fell asleep")


@Route.new(Level(2, 3))
def fell_asleep_early(config, log):
    def alter(ls_start, ls_end):
        print("? You fell asleep early by")
        
        new_dt = alter_record_time_by_td(ls_start, '__sub__')

        print("You fell asleep", new_dt)

        if get_confirmation():
            ls_start.time = new_dt
            return ls_start, ls_end


    log.alter_last_session(alter)

    return Route(Level(2), message = "You can also tune the time when you woke up")

@Route.new(Level(2, 4))
def fell_asleep_late(config, log):
    def alter(ls_start, ls_end):
        print("? You fell asleep late by")
        
        new_dt = alter_record_time_by_td(ls_start, '__add__')

        print("You fell asleep at", new_dt)

        if get_confirmation():
            ls_start.time = new_dt
            return ls_start, ls_end


    log.alter_last_session(alter)

    return Route(Level(2), message = "You can also tune the time when you woke up")


@Route.new(Level(2, 5))
def correct_back(config, log):
    return Route(Level(0))

@Route.new(Level(3))
def update_conf(config, log):
    config.update()

@Route.new(Level(4))
def leave(config, log):
    exit("Bye")


def cli(config, log, case = Level(0)):
    if route := Route.get(case):
        return route(config, log)
    else:
        raise Exception("Nonexsitent route", case)


def main():
    def run_while_jumps(f, *args, **kwargs):
        while True:
            if not isinstance((res := f(*args, **kwargs)), Level):
                break
            else:
                kwargs['case'] = res

    config = Config()
    log = Log()

    run_while_jumps(cli, config, log)



if __name__ == "__main__":
    main()