import datetime as dt
import toml
from pprint import pprint
from os import path
from enum import Enum, auto
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from contextlib import contextmanager

ALTER_LOG = False

aDay = dt.timedelta(days=1)
now = dt.datetime.now

datetime_fmt = "%d-%m-%Y, %H:%M:%S"

class File(ABC):
    def exists(self):
        return path.exists(self.FILE__NAME)

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
    time: dt.datetime

    def as_str(self):
        return f'{self.state.value} {self.time.strftime(datetime_fmt)}\n'

    @classmethod
    def parse(cls, row):
        state, time = row.rstrip('\n').split(maxsplit=1)
        for state_name, _state in Act.__members__.items():
            if state_name == state:
                state: Act = _state
                break
        else:
            raise Exception("Invalid state", state)
        
        time: dt.datetime = dt.datetime.strptime(time, datetime_fmt)

        return LogRow(state=state, time=time)

    @classmethod
    def safe_parse(cls, row):
        try:
            return cls.parse(row)
        except:
            return ""

@dataclass
class Config(File):
    rest_per_day: int #seconds

    FILE__NAME = "conf.toml"

    def __init__(self):
        parsed_config_file_data = self.get()

        self.rest_per_day = dt.timedelta(seconds=parsed_config_file_data['rest_per_day'])

    def load(self):
        assert self.exists()
        return toml.load(self.FILE__NAME)

    @classmethod
    def receive_data(cls):
        def parse_time_period(hours, minutes):
            def within_bounds(duration, upper_bound, lower_bound = 0):
                return lower_bound <= duration <= upper_bound

            try:
                hours, minutes = int(hours), int(minutes)
                hours += minutes // 60
                minutes %= 60

                assert within_bounds(hours, 24) and within_bounds(minutes, 60)
                assert (tp := dt.timedelta(hours=hours, minutes=minutes)) < aDay

                return tp

            except (ValueError, AssertionError):
                exit('Invalid input')

        print('? Planned rest per day')
        hours, minutes = input_hours_minutes()
        tp = parse_time_period(hours, minutes)

        data = dict(rest_per_day = tp.seconds)

        return data

    def create(self):
        print(': SETUP\n')

        data = self.receive_data()

        with self.open('w') as conf_file:
            toml.dump(data, conf_file)

    def update(self):
        self.create()

    def get(self):

        if not self.exists():
            self.create()

        data = self.load()

        for field_name, field in self.__dataclass_fields__.items():
            if not isinstance(data.get(field_name), field.type):
                print('! Config file is corrupped')
                self.update()
                data = self.load()
                break

        return data

class Log(File):
    FILE__NAME = "log.txt"


    def __init__(self):
        if not self.exists():
            with self.open('w'): pass

        self.get_content()
        self.sync()

    def load(self):
        assert self.exists()
        with self.open('r') as log_file:
            return log_file.readlines()

    def get_content(self):
        try:
            self.content = list(LogRow.parse(row) for row in self.load())
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

        with self.open('r') as log_file:
            for row in log_file.readlines():
                if record := LogRow.safe_parse(row):
                    repaired_records.append(record)

        if len(repaired_records) > 0 and repaired_records[-1].state is not Act.awake:
            del repaired_records[-1]
        
        self.content = repaired_records
        
        
    def alter_last_session(self):
        pass


def input_hours_minutes() -> (str, str):
    return input('\tHours: '), input('\tMinutes: ')



class Clock:
    hours = list(range(0, 25))

    @classmethod
    def between(self, start, end):
        if start <= end:
            return self.hours[start:end+1]
        else:
            return self.hours[start:] + self.hours[:end+1]

def part_of_day():
    this_hour = now().hour

    if this_hour in Clock.between(4, 11):
        return "morning"
    elif this_hour in Clock.between(12, 16):
        return "afternoon"
    elif this_hour in Clock.between(17, 20):
        return "evening"
    elif this_hour in Clock.between(21, 3):
        return "night"



def cli(config, log):
    print(
        f"Good {part_of_day()}. Please select:\n"
        "1. Calculate sleep duration.\n"
        "2. Correct last sleep session.\n"
        "3. Update configuration.\n"
        "4. Exit.\n"
        )
    
    num = input("Enter: ")

    if num.isnumeric() and (num := int(num)) in range(1, 5):
        if num == 1:
            calculated_amount = calculate_amount_of_sleep(log.content, config.rest_per_day)
            asleep, awake = get_asleep_awake(calculated_amount)

            if ALTER_LOG:
                log.append(asleep)
                log.append(awake)
            
            print("\nSleep for", calculated_amount, "\nSet alarm to", now() + calculated_amount)

        elif num == 2:
            print("? How much did you sleep last time")
            hours, minutes = input_hours_minutes()

        elif num == 3:
            config.update()

        elif num == 4:
            exit("Bye")
    else:
        exit("Invalid input")

def yield_datetime(dt: dt.datetime):
    def wrap():
        return dt

    return wrap

def get_asleep_awake(time: dt.timedelta, start: callable = now):
    start = start()
    end = start + time
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

    def get_latest_sleep_amount(records):
        total = dt.timedelta()
        for i in range(0, len(records), 2):
            total += records[i+1].time - records[i].time

        return total

    def get_latest_awake_amount(records):
        total = dt.timedelta()
        for i in range(0, len(records), 2):
            total += records[i+1].time - records[i].time

        return total

    if latest_records := get_latest_records(log):
        latest_sleep_amount = get_latest_sleep_amount(latest_records)
        print(f"Slept {latest_sleep_amount.seconds/3600} h.")

        result = (latest_sleep_amount + rest_per_day * (time_limiter / aDay)) / (1 - (rest_per_day / aDay))
    else:
        result = rest_per_day

    return result

def main():
    config = Config()
    log = Log()

    cli(config, log)


if __name__ == "__main__":
    main()