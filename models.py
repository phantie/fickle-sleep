from utils import now, get_confirmation, receive_timedelta, parse_time_period, print, is_none, not_none
from datetime import datetime as dt, timedelta, date
from contextlib import contextmanager
from abc import ABC, abstractmethod
from constants import datetime_fmt
from dataclasses import dataclass
from enum import Enum
from os import path
import functools
import toml


class File(ABC):

    @property
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

    def __str__(self):
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

    def alter_time_by_td(self, fname: str):
        td = receive_timedelta()
        return getattr(self.time, fname)(td)

    @classmethod
    def get_asleep_awake_pair(cls, duration: timedelta, start: callable = now):
        start = start()
        end = start + duration
        asleep = cls(state=Act.asleep, time=start)
        awake = cls(state=Act.awake, time=end)
        return asleep, awake


@dataclass
class Config(File):
    rest_per_day: str

    FILE__NAME = "conf.toml"

    def __init__(self):
        if not self.exists:
            self.create()

        self.get_data()
        

    def load(self):
        assert self.exists
        return toml.load(self.FILE__NAME)


    def receive_data(self):

        print('? Planned rest per day')
        
        rest_per_day: timedelta = str(receive_timedelta())
        
        if all(not_none(locals().get(fname)) for fname in self.__dataclass_fields__.keys()):
            exit('Invalid input')

        data = dict(rest_per_day = rest_per_day)
        return data

    def create(self):
        print(': SETUP\n')

        data = self.receive_data()

        with self.open('w') as conf_file:
            toml.dump(data, conf_file)

    def update(self):
        self.create()

    def get_data(self):

        def parseHM_(s):
            try:
                h, m, _ = s.split(':')
            except:
                return
                
            return parse_time_period(h, m)

        while True:
            fine_state = True
            data = self.load()

            for field_name, field in self.__dataclass_fields__.items():
                if not isinstance(data.get(field_name), field.type):
                    print('! Config file is corrupped')
                    self.update()
                    fine_state = False
                    break

            if not fine_state:
                continue
                
            data['rest_per_day'] = parseHM_(data['rest_per_day'])


            if not all(not_none(var) for var in data.values()):
                print("Corrupted data")
                self.update()
                continue

            break

        self.rest_per_day = data['rest_per_day']



class Log(File):
    FILE__NAME = "log.txt"

    def __init__(self):
        if not self.exists:
            self.create()
        
        self.get_content()
        self.sync()

    def load(self):
        assert self.exists
        with self.open('r') as log_file:
            return log_file.readlines()

    def create(self):
        with self.open('w'): pass

    def get_content(self):
        try:
            self.content = list(LogRow.parse(row) for row in self.load())

            if not self.empty:
                assert self.check_pair(self.last_session)
        except:
            print("! Log seems to be corrupted")
            confirm = get_confirmation("? Try to repair automatically")

            if confirm:
                self.repair()
                print("! Considering data was corrupted, first\n"
                        "  calcultations may not be accurate.\n")

            else: exit()

    @property
    def empty(self):
        return not bool(self.content)

    def append(self, log_row: LogRow):
        assert isinstance(log_row, LogRow)
        self.content.append(log_row)

        with self.open('a') as log_file:
            log_file.write(str(log_row))

    def sync(self):
        assert hasattr(self, "content")

        with self.open('w') as log_file:
            log_file.writelines(map(lambda row: str(row), self.content))

    ### It won`t save againts drastical
    ### manual log interruption. So don`t.
    def repair(self):
        assert self.exists

        repaired_records = []

        for row in self.load():
            if record := LogRow.parse(row, failproof=True):
                repaired_records.append(record)

        if repaired_records and repaired_records[-1].state is not Act.awake:
            del repaired_records[-1]
        
        self.content = repaired_records
        
    @staticmethod
    def check_pair(pair: (LogRow, LogRow)):
        asleep, awake = pair
        return asleep.state is Act.asleep and awake.state is Act.awake

    def alter_last_session(self, f: callable):
        assert not_none(self.last_session)

        ls_start, ls_end = self.last_session
        while True:
            if not_none(changed_session := f(ls_start, ls_end)):
                self.last_session = changed_session
                break

        self.last_session = ls_start, ls_end

    @property
    def last_session(self):
        if not self.empty:
            result = self.content[-2:]
            assert self.check_pair(result)
        else:
            result = None
        
        return result

    @last_session.setter
    def last_session(self, tup):
        assert not self.empty
        assert self.check_pair(tup)
        assert len(tup) == 2
        self.content[-2] = tup[0]
        self.content[-1] = tup[1]

    def print(self):
        print(": Log")
        for row in self.content:
            print(' ', row, end='')


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

    destination: Level
    message: str = None

    contents = {}

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
        assert is_none(cls.contents.get(str(lvl))), "ambiguity in levels hierarchy"
        cls.contents[str(lvl)] = func
