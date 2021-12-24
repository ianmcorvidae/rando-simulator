import random
import copy

from . import summary
from .parse_file import parse_file

### Making choices

class WeightedRandomSimulation:
    def __init__(self, simulation):
        self.first_choices = simulation.get('first-choices', [])
        self.weights = simulation.get('weights', {})
    def choose(self, available):
        for choice in self.first_choices:
            if choice in available:
                print(">> found first-choice option: " + choice)
                return choice
        if len(self.weights.keys()) == 0:
            return random.choice(available)
        else:
            weights = [self.weights.get(w, 1) for w in available]
            return random.choices(available, weights=weights)[0]

def choose_unlockable(simulation, unlockable, unlocks):
    available = list(set(unlockable) - set(unlocks))
    sim = WeightedRandomSimulation(simulation)
    if simulation.get('type', 'weighted-random') == 'weighted-random':
        sim = WeightedRandomSimulation(simulation)
    return sim.choose(available)

### Checking unlockable requirements

def meets_and_req(req, unlocks, found):
    met_reqs = []
    for r in req:
        #print("AND req: checking", r, unlocks, found)
        if isinstance(r, str) and ((r in unlocks) or (r in found)):
            #print(">> " + r + " in unlocks or found")
            met_reqs.append(r)
        elif isinstance(r, list) and meets_or_req(r, unlocks, found):
            #print(">> " + ", ".join(r) + " or req met by unlocks/found")
            met_reqs.append(r)
    return (len(req) == len(met_reqs))

def meets_or_req(req, unlocks, found):
    met_req = False
    for r in req:
        if isinstance(r, str) and ((r in unlocks) or (r in found)):
            #print(">> " + r + " in unlocks or found")
            met_req = True
            break
        elif isinstance(r, list):
            f = meets_and_req(r, unlocks, found)
            if f:
                #print(">> " + ", ".join(r) + " and req met by unlocks/found")
                met_req = f
                break
    return met_req

def find_unlockables(base, unlocks, found):
    u = []
    for unlockable_name in base["unlockables"].keys():
        unlockable = base["unlockables"][unlockable_name]
        if 'requirements' in unlockable:
            req = unlockable["requirements"]
            if isinstance(req, str) and ((req in unlocks) or (req in found)):
                #print(">> " + unlockable_name + " requires only " + req + " which we have, adding")
                u.append(unlockable_name)
            elif isinstance(req, list):
                if meets_and_req(req, unlocks, found):
                    #print(">> " + unlockable_name + " requires " + ", ".join(req) + " which we have, adding")
                    u.append(unlockable_name)
            elif isinstance(req, dict):
                if ("and" in req) and ("or" not in req):
                    # and-only, probably with nested or
                    if meets_and_req(req["and"], unlocks, found):
                        #print(">> " + unlockable_name, req)
                        u.append(unlockable_name)
                elif ("or" in req) and ("and" not in req):
                    # or-only, maybe with nested ands
                    if meets_or_req(req["or"], unlocks, found):
                        #print(">> " + unlockable_name, req)
                        u.append(unlockable_name)
                elif ("or" in req) and ("and" in req):
                    # both parts
                    if meets_and_req(req["and"], unlocks, found) and meets_or_req(req["or"], unlocks, found):
                        #print(">> " + unlockable_name, req)
                        u.append(unlockable_name)
        else:
            #print(">> " + unlockable_name + " has no requirements, adding")
            u.append(unlockable_name)
    return u

### automatic unlocks
def findable_unlocks(base, found, unlocks):
    u = []
    for f_name in found:
        found_obj = base["findables"].get(f_name, {})
        if "unlocks" in found_obj:
            u.extend(found_obj["unlocks"])
    for u_name in unlocks:
        unlock_obj = base["unlockables"].get(u_name, {})
        if "unlocks" in unlock_obj:
            u.extend(unlock_obj["unlocks"])
    return u

### findables that have been found
def found_findables(base, choices, unlocks):
    return [choices[k] for k in base["initial"].keys()] + [choices[k] for k in unlocks if k in choices]

def update_lists(base, choices, found, unlocks, unlockables):
    f = copy.copy(found)
    u1 = copy.copy(unlocks)
    u2 = copy.copy(unlockables)

    u1.extend(findable_unlocks(base, found, unlocks))
    u1 = list(set(u1))
    changed_u1 = (len(u1) != len(unlocks))

    u2 = find_unlockables(base, unlocks, found)
    changed_u2 = (len(u2) != len(unlockables))

    f = found_findables(base, choices, unlocks)
    changed_f = (len(f) != len(found))

    if changed_u1:
        new = set(u1) - set(unlocks)
        print("New unlocks found: " + ", ".join(new))

    if changed_u2:
        new = set(u2) - set(unlockables)
        print("New unlockables found: " + ", ".join(new))

    if changed_f:
        new = set(f) - set(found)
        print("New findables found: " + ", ".join(new))

    if changed_u1 or changed_u2 or changed_f:
        print("~~~~~ recursing")
        (f, u1, u2) = update_lists(base, choices, f, u1, u2)

    return (f, u1, u2)

def run_one_simulation(base, choices, sim, simulation):
    report = {"choices": []}
    for r in sim["reports"]:
        report[r["label"]] = []
    print("----------")
    found = [choices[k] for k in base["initial"].keys()]
    unlocks = []
    unlockables = []
    (found, unlocks, unlockables) = update_lists(base, choices, found, unlocks, unlockables)
    print("----------")
    print("Available unlocks: " + ", ".join(set(unlockables) - set(unlocks)))
    print("Already unlocked: " + ", ".join(unlocks))
    print("Already found: " + ", ".join(found))
    while len([e for e in sim["end-states"] if e in unlocks]) == 0:
        print("----------")
        next_unlock = choose_unlockable(simulation, unlockables, unlocks)
        print("Next unlock chosen: " + next_unlock)
        unlocks.append(next_unlock)
        report["choices"].append(next_unlock)
        for r in sim["reports"]:
            if r["type"] == "qualitative":
                for cat in r["categories"].keys():
                    # only one condition
                    if "type" in r["categories"][cat]:
                        if r["categories"][cat]["type"] == "made-choice" and r["categories"][cat]["choice"] == next_unlock:
                            report[r["label"]].append(cat)
                    # and-ed/or-ed conditions
                    else:
                        pass
        (found, unlocks, unlockables) = update_lists(base, choices, found, unlocks, unlockables)
        print("----------")
        print("Available unlocks: " + ", ".join(set(unlockables) - set(unlocks)))
        print("Already unlocked: " + ", ".join(unlocks))
        print("Already found: " + ", ".join(found))
    print("Finished!")
    print("----------")
    return report

class SimulationSingle:
    def __init__(self, base, sim, simulation, choices, opts={}):
        self.reports = {}
        self.base = base
        self.sim = sim
        self.simulation = simulation
        self.choices = choices
        self.opts = opts

    def run(self):
        self.reports = run_one_simulation(self.base, self.choices, self.sim, self.simulation)

class SimulationRun:
    def __init__(self, base, sim, simulation, choices, opts={}):
        self.reports = {}
        self.base = base
        self.sim = sim
        self.simulation = simulation
        self.choices = choices
        self.opts = opts
        self.label = self.simulation.get("label", str(self.sim["simulations"].index(self.simulation)))

    def run(self):
        #simulation_label = self.simulation.get("label", str(self.sim["simulations"].index(simulation)))
        #self.reports[simulation_label] = self.reports.get(simulation_label, {})
        for r in self.sim["reports"]:
            self.reports[r["label"]] = []
        for i in range(self.simulation.get("count", 1)):
            run = SimulationSingle(self.base, self.sim, self.simulation, self.choices)
            run.run()
            print(run.reports)
            self.reports[i] = run.reports
            for r in self.sim["reports"]:
                self.reports[r["label"]].append(run.reports[r["label"]])

class FileSimulator:
    def __init__(self, fname, base, sim, opts={}):
        self.reports = {}
        self.fname = fname
        self.base = base
        self.sim = sim
        self.opts = opts
        with open(fname, 'r') as f:
            self.choices = parse_file(f)
        if opts.get("summarize", True):
            summary.summarize_options(self.base, choices=self.choices)

    def simulation(self, index):
        return SimulationRun(self.base, self.sim, self.sim["simulations"][index], self.choices, self.opts)

    def run(self):
        for s in range(len(self.sim["simulations"])):
            simulation = self.simulation(s)
            label = simulation.label
            simulation.run()
            self.reports[label] = simulation.reports

class RandomizerSimulator:
    def __init__(self, choice_files, base, sim, opts={}):
        self.reports = {}
        self.filenames = choice_files
        self.base = base
        self.sim = sim
        self.opts = opts

    def file_simulator(self, file_index):
        return FileSimulator(self.filenames[file_index], self.base, self.sim, self.opts)

    def run(self):
        for file_index in range(len(self.filenames)):
            fname = self.filenames[file_index]
            file_simulator = self.file_simulator(file_index)
            file_simulator.run()
            self.reports[fname] = file_simulator.reports
