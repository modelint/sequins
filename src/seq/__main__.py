"""
Blueprint Sequins Diagram Generator

"""
# System
import logging
import logging.config
import sys
import argparse
from pathlib import Path
import atexit

# MDB
from seq.SeqDiagram import SeqDiagram
from seq import version

_logpath = Path("seq.log")
_progname = 'Blueprint Model Sequins Diagram Generator'

def clean_up():
    """Normal and exception exit activities"""
    _logpath.unlink(missing_ok=True)

def get_logger():
    """Initiate the logger"""
    log_conf_path = Path(__file__).parent / 'log.conf'  # Logging configuration is in this file
    logging.config.fileConfig(fname=log_conf_path, disable_existing_loggers=False)
    return logging.getLogger(__name__)  # Create a logger for this module


# Configure the expected parameters and actions for the argparse module
def parse(cl_input):
    parser = argparse.ArgumentParser(description=_progname)
    parser.add_argument('-s', '--scenario', action='store',
                        help='Name of the scenario *.yaml file')
    parser.add_argument('-L', '--log', action='store_true',
                        help='Generate a diagnostic log file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose messages')
    parser.add_argument('-V', '--version', action='store_true',
                        help='Print the current version of the model execution app')
    return parser.parse_args(cl_input)


def main():
    # Start logging
    logger = get_logger()
    msg = f'{_progname} version: {version}\n'
    logger.info(msg)

    # Parse the command line args
    args = parse(sys.argv[1:])

    if args.version:
        # Just print the version and quit
        print(f'{_progname} version: {version}')
        sys.exit(0)

    if not args.log:
        # If no log file is requested, remove the log file before termination
        atexit.register(clean_up)

    print(f"\n{msg}")
    if args.verbose:
        print("\nVerbose mode set\n")

    # All pathnames are optional since the user can specify them in the debug session
    diagram = SeqDiagram()  # Create the singleton instance
    SeqDiagram.initialize(
        # system_path=Path(args.system) if args.system else None,
        scenario_name=args.scenario if args.scenario else None,
        verbose=args.verbose)

    logger.info("No problemo")  # We didn't die on an exception, basically
    if args.verbose:
        print("\nNo problemo")


if __name__ == "__main__":
    main()
