from datetime import datetime as dt, timedelta
from contextlib import contextmanager, suppress
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from os import path
import toml
from copy import deepcopy

ALTER_LOG = False

aDay = timedelta(days=1)

datetime_fmt = "%d-%m-%Y, %H:%M:%S"
timedelta_fmt = "%H:%M:%S"



print_dc = deepcopy(print)
def _print(*args):
    _args = []
    for el in args:
        if isinstance(el, float):
            processed = Round.float(el)
        elif isinstance(el, dt):
            processed = Round.datetime(el)
        elif isinstance(el, timedelta):
            processed = Round.timedelta(el)
        else:
            processed = el

        _args.append(processed)

    print_dc(*_args)

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
    def parse(row, failproof=False):
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

        parsed_config_data = self.get()

        self.rest_per_day = parsed_config_data['rest_per_day']


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

    def get(self):
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

        return data

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
                assert self.content[-1].state is Act.awake
        except:
            print("! Log seems to be corrupted")
            print("? Try to repair automatically")
            while True: 
                inp = input("{y, n} ")
                if inp == "y":
                    self.repair()
                    print("! Considering data was corrupted, first\n"
                          "  calcultations may not be accurate.\n")
                    break
                elif inp == "n": exit()
                else: continue


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
        
        
    def alter_last_session(self):
        pass

class Round:
    @staticmethod
    def timedelta(td):
        assert isinstance(td, timedelta)
        return parseHM_(str(td).split('.')[0])

    @staticmethod
    def float(fl):
        assert isinstance(fl, float)
        return round(fl, ndigits=1)

    @staticmethod
    def datetime(d):
        assert isinstance(d, dt)
        return d.replace(microsecond=0, second=0)


def now():
    return Round.datetime(dt.now())

def input_until_correct(message, subsequent_try_message, /, parser: callable, **kwargs):
    lap = 0
    while True:
        if (parsed := parser(input(message), **kwargs)) is not None:
            return parsed
        lap += 1
        if lap:
            message = subsequent_try_message

def receive_timedelta() -> timedelta:
    def input_hours_minutes() -> (str, str):
        return input('\tHours: '), input('\tMinutes: ')

    h, m = input_hours_minutes()
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
        self.levels: list = sub_levels
        self.parent = Level(*sub_levels[:-1]) if len(sub_levels) > 1 else None

    def __str__(self):
        return f"{self.__class__.__name__}({self.levels if len(self.levels)>1 else self.levels[0]})"

    def __repr__(self):
        return str(self)

    def __add__(self, other):
        if isinstance(other, Level):
            return Level(self.levels + other.levels)
        else:
            raise NotImplemented

    def __eq__(self, other):
        if isinstance(other, Level):
            return self.levels == other.levels
        else:
            raise NotImplemented



class Layer:
    contents = []

    def __init__(self, **kwargs):
        assert len(set(el.levels for el in kwargs.values())) == len(kwargs.values()), \
            "Layer must not own equal levels"

        assert all(len(el.levels) == len(self.contents) + 1 for el in kwargs.values()), \
            "Some levels do not belong to this layer"

        self.levels = kwargs

    @classmethod
    def add(cls, d):
        cls.contents.append(cls(**d))

    @classmethod
    def get(cls, number):
        assert 0 < number <= len(cls.contents)
        return cls.contents[number - 1]

    @classmethod
    def children(cls, *args):
        parent = Level(*args)
        children = []
        if layer := cls.get(len(args) + 1):
            for lvl in layer.levels.values():
                if lvl.parent == parent:
                    children.append(lvl)

        return children

    @classmethod
    def find(cls, name):
        for layer in cls.contents:
            return layer.__dict__['levels'].get(name)

    @classmethod
    def find_name(cls, lvl):
        if layer := cls.get(len(lvl.levels)):
            for name, level in layer.__dict__['levels'].items():
                if level == lvl:
                    return name

    @classmethod
    def all_levels(cls):
        result = {}

        for layer in cls.contents:
            result.update(layer.levels)

        return result


def init_cli_layers():
    Layer.add(dict(
        calc = Level(1),
        correct = Level(2),
        update_conf = Level(3),
        leave = Level(4),
    ))

    # Layer.add(dict(
    #     overslept = Level(2, 1),
    #     underslept = Level(2, 2),    
    #     idk = Level(3, 1),
    # ))


# print(Layer.children(2, 1))
# print(Layer.find("calc"))
# print(Layer.find_name(Level(2)))
# print(Layer.all_levels())


class Commander:
    def __init__(self, config, log):
        self.config = config
        self.log = log

    def calc(self):
        sleep_for = calculate_amount_of_sleep(self.log.content, self.config.rest_per_day)
        asleep, awake = get_asleep_awake(sleep_for)

        if ALTER_LOG:
            self.log.append(asleep)
            self.log.append(awake)

        print("\nSleep for", sleep_for, "\nSet alarm to", now() + sleep_for)

        return sleep_for

    def correct(self):
        return Level(4)

    def update_conf(self):
        self.config.update()

    def leave(self):
        exit("Bye")


def cli(commander, case = None):

    if not case:
        print(
        f"Good {Clock.part_of_day()}. Please select:\n"
        "1. Calculate sleep duration.\n"
        "2. Correct last sleep session.\n"
        "3. Update configuration.\n"
        "4. Exit.\n"
        )
    
    case = case or input_until_correct(
                                "Enter: ", "Try again: ", 
                                parser = parse_cli_input,
                                choices = 4)

    if func_name := Layer.find_name(case):
        return getattr(Commander, func_name)(commander)


def lazy_yield(x) -> callable:
    return lambda: x

def get_asleep_awake(duration: timedelta, start: callable = now):
    start = start()
    end = start + duration
    asleep = LogRow(state=Act.asleep, time=start)
    awake = LogRow(state=Act.awake, time=end)
    return asleep, awake

def calculate_amount_of_sleep(log, rest_per_day, time_limiter = 1.4 * aDay):
    
    def get_latest_records(log):
        nonlocal time_limiter
        start_moment = now() - time_limiter

        if log:
            for i, record in enumerate(log):
                if record.time >= start_moment:
                    if record.state is Act.awake:
                        log = log[i-1:]
                    elif record.state is Act.asleep:
                        log = log[i:]

                    time_limiter = start_moment - log[0].time
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
            print('Awake from', records[i].time, "to", records[i+1].time, 'Delta:', records[i+1].time - records[i].time)
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

        assert not gap - (latest_sleep_amount + latest_awake_amount)

        print(rest_per_day)
        print("Slept", latest_sleep_amount.seconds/3600, "h.")
        print("Was awake", latest_awake_amount.seconds/3600, "h.")

        # print("Delta:", end - start)
        # print("Calculated:", latest_sleep_amount + latest_awake_amount)


        result = (latest_sleep_amount + rest_per_day * (time_limiter / aDay)) / (1 - (rest_per_day / aDay))
    else:
        result = rest_per_day

    return result

def main():
    def run_while_jumps(f, *args, **kwags):
        while True:
            if not isinstance((res := f(*args, **kwags)), Level):
                break
            else:
                kwags['case'] = res

    init_cli_layers()
    config = Config()
    log = Log()
    commander = Commander(config, log)

    run_while_jumps(cli, commander)



if __name__ == "__main__":
    main()