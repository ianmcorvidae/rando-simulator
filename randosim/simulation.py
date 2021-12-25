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

def get_sim(simulation):
    if simulation.get('type', 'weighted-random') in ['weighted-random', 'random', 'fixed-list']:
        return WeightedRandomSimulation(simulation)
    else:
        return WeightedRandomSimulation(simulation)


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

class QualitativeReport:
    def __init__(self, label, categories):
        self.label = label
        self.categories = categories
        self.choices = []
        self.founds = []

    def condition_matches(self, condition):
        if condition["type"] == "made-choice":
            return (condition["choice"] in self.choices)
        elif condition["type"] == "got-findable":
            return (condition["findable"] in self.founds)
        else:
            print("Unknown condition type", condition["type"])
            return False

    def category_matches(self, category):
        if "type" in category:
            category = {"and": [category]}
        if "and" in category:
            # loop over all of them, return false if any returns false
            for c in category["and"]:
                if not self.condition_matches(c):
                    return False
        if "and_not" in category:
            # loop over all of them, return false if any returns true
            for c in category["and"]:
                if self.condition_matches(c):
                    return False

        if "or" in category: # eh, we'll not bother with or_not for now
            # return true on first match
            for c in category["or"]:
                if self.condition_matches(c):
                    return True
            return False # if we got here, we checked all the ors and got none
        else:
            # there is no 'or', so if we got here, all the ands matched
            return True

    def check_categories(self, reports):
        for cat in self.categories.keys():
            category = self.categories[cat]
            if self.category_matches(category) and cat not in reports[self.label]:
                reports[self.label].append(cat)
        return reports

    def made_choice(self, reports, choice_made):
        self.choices.append(choice_made)
        return self.check_categories(reports)

    def found(self, reports, findable_found):
        self.founds.append(findable_found)
        return self.check_categories(reports)

class SimulationSingle:
    def __init__(self, base, sim, simulation, choices, opts={}):
        self.reports = {"choices": [], "choice_count": 0}
        self.base = base
        self.sim = sim
        self.simulation = simulation
        self.choices = choices
        self.opts = opts

        self.found = []
        self.unlocks = []
        self.unlockables = []

        self.reporting_hooks = {'made-choice': [], 'found': []}

        self._init_reports()
        self._init_lists()
        if opts.get("summarize", True):
            self.summarize() 

    def _init_reports(self):
        for r in self.sim["reports"]:
            self.reports[r["label"]] = self.reports.get(r["label"],[])
            if r["type"] == "qualitative":
                self.reporting_hooks["made-choice"].append(QualitativeReport(r["label"], r["categories"]))
                self.reporting_hooks["found"].append(QualitativeReport(r["label"], r["categories"]))

    def _init_lists(self):
        self.found = [self.choices[k] for k in self.base["initial"].keys()]
        self.update_lists()

    def _update_choice_count(self):
        self.reports["choice_count"] = len(self.reports.get("choices", []))

    def summarize(self):
        print("----------")
        print("Available unlocks: " + ", ".join(set(self.unlockables) - set(self.unlocks)))
        print("Already unlocked: " + ", ".join(self.unlocks))
        print("Already found: " + ", ".join(self.found))

    def _found_findables(self, unlocks):
        return [self.choices[k] for k in self.base["initial"].keys()] + [self.choices[k] for k in unlocks if k in self.choices]

    def _findable_unlocks(self, found, unlocks):
        u = []
        for f_name in found:
            found_obj = self.base["findables"].get(f_name, {})
            if "unlocks" in found_obj:
                u.extend(found_obj["unlocks"])
        for u_name in unlocks:
            unlock_obj = self.base["unlockables"].get(u_name, {})
            if "unlocks" in unlock_obj:
                u.extend(unlock_obj["unlocks"])
        return u

    def _find_unlockables(self, unlocks, found):
        u = []
        for unlockable_name in self.base["unlockables"].keys():
            unlockable = self.base["unlockables"][unlockable_name]
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

    def _updated_lists(self, found, unlocks, unlockables):
        f = copy.copy(found)
        u1 = copy.copy(unlocks)
        u2 = copy.copy(unlockables)

        u1.extend(self._findable_unlocks(found, unlocks))
        u1 = list(set(u1))
        changed_u1 = (len(u1) != len(unlocks))

        u2 = self._find_unlockables(unlocks, found)
        changed_u2 = (len(u2) != len(unlockables))

        f = self._found_findables(unlocks)
        changed_f = (len(f) != len(found))

        if self.opts.get("summarize", True):
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
            (f, u1, u2) = self._updated_lists(f, u1, u2)

        return (f, u1, u2)

    def update_lists(self):
        (f, u1, u2) = self._updated_lists(self.found, self.unlocks, self.unlockables)
        if len(f) != len(self.found):
            for hook in self.reporting_hooks['found']:
                for findable in list(set(f) - set(self.found)):
                    self.reports = hook.found(self.reports, findable)
        (self.found, self.unlocks, self.unlockables) = (f, u1, u2)

    def choose_unlockable(self):
        available = list(set(self.unlockables) - set(self.unlocks))
        sim = get_sim(self.simulation)
        return sim.choose(available)

    def run(self):
        while len([e for e in self.sim["end-states"] if e in self.unlocks]) == 0:
            print("----------")
            next_unlock = self.choose_unlockable()
            print("Next unlock chosen: " + next_unlock)
            self.unlocks.append(next_unlock)
            self.reports["choices"].append(next_unlock)
            for hook in self.reporting_hooks['made-choice']:
                self.reports = hook.made_choice(self.reports, next_unlock)
            self.update_lists()
            if self.opts.get("summarize", True):
                self.summarize()
        print("Finished!")
        print("----------")
        self._update_choice_count()

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
            run = SimulationSingle(self.base, self.sim, self.simulation, self.choices, self.opts)
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
