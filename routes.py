from utils import get_confirmation, show_and_select, print, now
from datetime import datetime as dt, timedelta, date
from models import Route, Level, Clock, LogRow
from calc import calculate_amount_of_sleep
from constants import ALTER_LOG


@Route.new(Level(0))
def welcoming(config, log):
    print(f"\nGood {Clock.part_of_day()}. Please select:")

    exclude = []
    if log.empty:
        exclude.append(2) 


    case = show_and_select([
        "calculate sleep duration",
        "tune the previous sleep session",
        "update configuration",
        "quit",
        ], exclude=exclude)

    return Level(case)


@Route.new(Level(1))
def calc(config, log):
    sleep_for = calculate_amount_of_sleep(log.content, config.rest_per_day)

    if sleep_for < timedelta():
        print("You should not sleep for at least", abs(sleep_for))
    else:
        if ALTER_LOG:
            asleep, awake = LogRow.get_asleep_awake_pair(sleep_for)
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

    return Level(case)


@Route.new(Level(2, 1))
def overslept(config, log):

    def alter(ls_start, ls_end):
        print("? You overslept by")
        
        new_dt = ls_end.alter_time_by_td('__add__')
        

        print("You awoke at", new_dt)

        if get_confirmation():
            ls_end.time = new_dt
            return ls_start, ls_end

    log.alter_last_session(alter)
    log.sync()

    return Route(Level(2), message = "You can also tune the time when you fell asleep")


@Route.new(Level(2, 2))
def underslept(config, log):

    def alter(ls_start, ls_end):
        print("? You underslept by")
        
        new_dt = ls_end.alter_time_by_td('__sub__')

        print("You awoke at", new_dt)

        if get_confirmation():
            ls_end.time = new_dt
            return ls_start, ls_end

    log.alter_last_session(alter)
    log.sync()

    return Route(Level(2), message = "You can also tune the time when you fell asleep")


@Route.new(Level(2, 3))
def fell_asleep_early(config, log):
    def alter(ls_start, ls_end):
        print("? You fell asleep early by")
        
        new_dt = ls_start.alter_time_by_td('__sub__')

        print("You fell asleep", new_dt)

        if get_confirmation():
            ls_start.time = new_dt
            return ls_start, ls_end


    log.alter_last_session(alter)
    log.sync()

    return Route(Level(2), message = "You can also tune the time when you woke up")


@Route.new(Level(2, 4))
def fell_asleep_late(config, log):
    def alter(ls_start, ls_end):
        print("? You fell asleep late by")
        
        new_dt = ls_start.alter_time_by_td('__add__')

        print("You fell asleep at", new_dt)

        if get_confirmation():
            ls_start.time = new_dt
            return ls_start, ls_end


    log.alter_last_session(alter)
    log.sync()

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
