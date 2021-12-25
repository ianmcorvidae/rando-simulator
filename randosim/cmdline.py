import argparse
import json

from . import summary
from . import simulation
from .parse_file import parse_file

def cmdline():
    parser = argparse.ArgumentParser(description="Simulate playing through a randomized game, gathering statistics.")
    parser.add_argument('base', help="The base game description file", type=argparse.FileType('r'))
    parser.add_argument('simulation', help="The file specifying the simulation to run", type=argparse.FileType('r'))
    # string for this one, we'll open each one in the loop
    parser.add_argument('choices', help="The file(s) describing randomized choices to use for simulating", nargs='*')
    args = parser.parse_args()
    print(args)
    base = parse_file(args.base)
    sim = parse_file(args.simulation)
    print(base)
    print(sim)
    if len(args.choices) == 0:
        summary.summarize_options(base)
    else:
        import pprint
        simulator = simulation.RandomizerSimulator(args.choices, base, sim)
        simulator.run()
        pprint.pprint(simulator.reports)
