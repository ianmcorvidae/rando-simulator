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
        for f in simulator.reports["files"].keys():
            for s in simulator.reports["files"][f]["simulations"].keys():
                #for k in simulator.reports["files"][f]["simulations"][s].keys():
                #    if isinstance(k, int):
                #        print(", ".join(simulator.reports["files"][f]["simulations"][s][k]["choices"]), simulator.reports["files"][f]["simulations"][s][k]["Go Mode"])
                for r in simulator.reports["files"][f]["simulations"][s]["summary"].keys():
                    print(f + "\t" + s + "\t" + r)
                    pprint.pprint(simulator.reports["files"][f]["simulations"][s]["summary"][r], compact=True)
                    print("----------")
        for s in simulator.reports["simulations"].keys():
            for r in simulator.reports["simulations"][s]["summary"].keys():
                print("<all files>\t" + s + "\t" + r)
                pprint.pprint(simulator.reports["simulations"][s]["summary"][r], compact=True)
                print("----------")
        for r in simulator.reports["summary"].keys():
            print("<all files>\t<all simulations>\t" + r)
            pprint.pprint(simulator.reports["summary"][r], compact=True)
            print("----------")

        #print(simulator.reports)
