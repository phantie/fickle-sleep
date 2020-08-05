from models import Config, Log, Level
from routes import Route


def cli(config, log, case = Level(0)):
    if route := Route.get(case):
        return route(config, log)
    else:
        raise Exception("Nonexistent route", case)


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