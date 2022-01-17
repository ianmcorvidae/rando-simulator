import argparse
import json
import multiprocessing
import os
import sys

from . import summary
from . import simulation
from .parse_file import parse_file


def cmdline():
    parser = argparse.ArgumentParser(description="Simulate playing through a randomized game, gathering statistics.")
    sub = parser.add_subparsers()

    analyze = sub.add_parser('analyze', help="Analyze some files")
    analyze.add_argument('-b', '--base', help="The base game description file", type=argparse.FileType('r'), required=True)
    analyze.add_argument('-s', '--simulation', help="The file specifying the simulation to run", type=argparse.FileType('r'), required=True)
    #analyze.add_argument('-d', '--database', help="The sqlite database file to store results in.", required=False)
    # string for this one, we'll open each one in the loop
    analyze.add_argument('choices', help="The file(s) describing randomized choices to use for simulating", nargs='*')

    args = parser.parse_args()
    base = parse_file(args.base)
    sim = parse_file(args.simulation)
    if len(args.choices) == 0:
        summary.summarize_options(base)
    else:
        with multiprocessing.Pool(max(1, os.cpu_count() - 2)) as pool:
            simulator = simulation.RandomizerSimulator(args.choices, base, sim, pool=pool)
            simulator.run()
        print(json.dumps(simulator.reports))
        import pprint
        for f in simulator.reports["files"].keys():
            for s in simulator.reports["files"][f]["simulations"].keys():
                for r in simulator.reports["files"][f]["simulations"][s]["summary"].keys():
                    print(f + "\t" + s + "\t" + r, file=sys.stderr)
                    pprint.pprint(simulator.reports["files"][f]["simulations"][s]["summary"][r], compact=True, stream=sys.stderr)
                    print("----------", file=sys.stderr)
        for s in simulator.reports["simulations"].keys():
            for r in simulator.reports["simulations"][s]["summary"].keys():
                print("<all files>\t" + s + "\t" + r, file=sys.stderr)
                pprint.pprint(simulator.reports["simulations"][s]["summary"][r], compact=True, stream=sys.stderr)
                print("----------", file=sys.stderr)
        for r in simulator.reports["summary"].keys():
            print("<all files>\t<all simulations>\t" + r, file=sys.stderr)
            pprint.pprint(simulator.reports["summary"][r], compact=True, stream=sys.stderr)
            print("----------", file=sys.stderr)

        #print(simulator.reports)
