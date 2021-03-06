import random
import copy
import sys

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

def _strmet(reqstr, got):
    return reqstr in got

def meets_and_req(req, got):
    met_reqs = []
    for r in req:
        if isinstance(r, str) and _strmet(r, got):
            met_reqs.append(r)
        elif isinstance(r, list) and meets_or_req(r, got):
            met_reqs.append(r)
    return (len(req) == len(met_reqs))

def meets_or_req(req, got):
    met_req = False
    for r in req:
        if isinstance(r, str) and _strmet(r, got):
            met_req = True
            break
        elif isinstance(r, list):
            f = meets_and_req(r, got)
            if f:
                met_req = f
                break
    return met_req

class QualitativeReport:
    def __init__(self, label, categories):
        self.supported_hooks = ['made-choice', 'found']
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

        if "or" in category or "or_not" in category:
            # return true on first match
            for c in category.get("or", []):
                if self.condition_matches(c):
                    return True
            for c in category.get("or_not", []):
                if not self.condition_matches(c):
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

    def combine_simulations(self, reports, label):
        data = []
        for sim in reports["simulations"].keys():
            data.extend(reports["simulations"][sim]["raw"][label])
        return data

    def combine_files(self, reports, report_label, simulation_label):
        data = []
        for f in reports["files"].keys():
            data.extend(reports["files"][f]["raw"][report_label])
        return data

    def summarize_raw_data(self, raw_data):
        summary = {}
        summary["all_seen"] = []
        summary["individual_percentages"] = {}
        summary["individual_counts"] = {}
        summary["joint_percentages"] = {}
        summary["joint_counts"] = {}
        summary["joint_ordered_percentages"] = {}
        summary["joint_ordered_counts"] = {}
        count = len(raw_data)
        for run in raw_data:
            summary["all_seen"].extend(run)
            joint_key = "::".join(sorted(run))
            summary["joint_counts"][joint_key] = summary["joint_counts"].get(joint_key, 0) + 1
            ordered_key = "::".join(run)
            summary["joint_ordered_counts"][ordered_key] = summary["joint_ordered_counts"].get(ordered_key, 0) + 1
            for category in run:
                summary["individual_counts"][category] = summary["individual_counts"].get(category, 0) + 1
        summary["all_seen"] = list(set(summary["all_seen"]))
        for category in summary["individual_counts"].keys():
            summary["individual_percentages"][category] = summary["individual_counts"][category] / count
        summary["individual_percentages_sum"] = sum(summary["individual_percentages"].values())
        for category in summary["joint_counts"].keys():
            summary["joint_percentages"][category] = summary["joint_counts"][category] / count
        summary["joint_percentages_sum"] = sum(summary["joint_percentages"].values())
        for category in summary["joint_ordered_counts"].keys():
            summary["joint_ordered_percentages"][category] = summary["joint_ordered_counts"][category] / count
        summary["joint_ordered_percentages_sum"] = sum(summary["joint_ordered_percentages"].values())
        return summary


def get_report(report):
    if report.get('type', None) == "qualitative":
        return QualitativeReport(report["label"], report["categories"])
    return None

class SimulationSingle:
    def __init__(self, base, sim, simulation, choices, opts={}):
        self.reports = {"choices": [], "choice_count": 0}
        self.base = base
        self.sim = sim
        self.simulation = simulation
        self.choices = choices
        self.opts = opts

        self._initf = None
        self.found = []
        self.unlocks = []
        self.unlockables = []

        self.reporting_hooks = {'made-choice': [], 'found': []}

        self._init_reports()
        self._init_lists()
        if opts.get("summarize", False):
            self.summarize() 

    def _init_reports(self):
        for r in self.sim["reports"]:
            self.reports[r["label"]] = self.reports.get(r["label"],[])
            report = get_report(r)
            for hook_type in self.reporting_hooks.keys():
                if hook_type in report.supported_hooks:
                    self.reporting_hooks[hook_type].append(report)

    def _initial_found(self):
        if self._initf is None:
            self._initf = [self.choices[k] for k in self.base["initial"].keys()]
        return self._initf

    def _init_lists(self):
        self.found = self._initial_found()
        for hook in self.reporting_hooks['found']:
            for findable in self.found:
                self.reports = hook.found(self.reports, findable)
        self.update_lists()

    def _update_choice_count(self):
        self.reports["choice_count"] = len(self.reports.get("choices", []))

    def summarize(self):
        print("Available: " + ", ".join(set(self.unlockables) - set(self.unlocks)))
        print("Done:      " + ", ".join(self.unlocks))
        print("Found:     " + ", ".join(self.found))

    def _found_findables(self, unlocks):
        return self._initial_found() + [self.choices[k] for k in unlocks if k in self.choices]

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
        got = set(unlocks) | set(found)
        for unlockable_name, unlockable in self.base["unlockables"].items():
            #unlockable = self.base["unlockables"][unlockable_name]
            if 'requirements' in unlockable:
                req = unlockable["requirements"]
                if isinstance(req, str) and _strmet(req, got):
                    u.append(unlockable_name)
                elif isinstance(req, list):
                    if meets_and_req(req, got):
                        u.append(unlockable_name)
                elif isinstance(req, dict):
                    if ("and" in req) and ("or" not in req):
                        # and-only, probably with nested or
                        if meets_and_req(req["and"], got):
                            u.append(unlockable_name)
                    elif ("or" in req) and ("and" not in req):
                        # or-only, maybe with nested ands
                        if meets_or_req(req["or"], got):
                            u.append(unlockable_name)
                    elif ("or" in req) and ("and" in req):
                        # both parts
                        if meets_and_req(req["and"], got) and meets_or_req(req["or"], got):
                            u.append(unlockable_name)
            else:
                u.append(unlockable_name)
        return u

    def _updated_lists(self, found, unlocks, unlockables):
        f = copy.copy(found)
        u1 = copy.copy(unlocks)
        u2 = copy.copy(unlockables)

        new_u1 = self._findable_unlocks(found, unlocks)
        u1 = u1 + list(set(new_u1) - set(u1))
        changed_u1 = (len(u1) != len(unlocks))

        new_u2 = self._find_unlockables(unlocks, found)
        u2 = u2 + list(set(new_u2) - set(u2))
        changed_u2 = (len(u2) != len(new_u2))

        new_f = self._found_findables(unlocks)
        f = f + list(set(new_f) - set(f))
        changed_f = (len(f) != len(found))

        if self.opts.get("summarize", False):
            if changed_u1:
                new = set(u1) - set(unlocks)
                print("New unlocks:     " + ", ".join(new))

            if changed_u2:
                new = set(u2) - set(unlockables)
                print("New unlockables: " + ", ".join(new))

            if changed_f:
                new = set(f) - set(found)
                print("New findables:   " + ", ".join(new))

        if changed_u1 or changed_u2 or changed_f:
            #print("  ...") if self.opts.get("summarize", False)
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
            #print("----------") if self.opts.get("summarize", False)
            next_unlock = self.choose_unlockable()
            #print("Next unlock: " + next_unlock) if self.opts.get("summarize", False)
            self.unlocks.append(next_unlock)
            self.reports["choices"].append(next_unlock)
            for hook in self.reporting_hooks['made-choice']:
                self.reports = hook.made_choice(self.reports, next_unlock)
            self.update_lists()
            #self.summarize() if self.opts.get("summarize", False)
        #print("==========") if self.opts.get("summarize", False)
        self._update_choice_count()

def simulation_label(simulation, sim):
    return simulation.get("label", str(sim["simulations"].index(simulation)))

def sim_report(simulation_single):
    simulation_single.run()
    return simulation_single.reports

class SimulationRun:
    def __init__(self, base, sim, simulation, choices, pool=None, opts={}):
        self.reports = {"raw": {}, "summary": {}}
        self.base = base
        self.sim = sim
        self.simulation = simulation
        self.choices = choices
        self.opts = opts
        self.pool = pool
        self.label = simulation_label(self.simulation, self.sim)

    def run(self):
        #simulation_label = self.simulation.get("label", str(self.sim["simulations"].index(simulation)))
        #self.reports[simulation_label] = self.reports.get(simulation_label, {})
        print("SIM: " + simulation_label(self.simulation, self.sim),file=sys.stderr)
        for r in self.sim["reports"]:
            self.reports["raw"][r["label"]] = []
        runs = []
        for i in range(self.simulation.get("count", 1)):
            run = SimulationSingle(self.base, self.sim, self.simulation, self.choices, self.opts)
            runs.append(run)
        if self.pool is not None:
            res = self.pool.map(sim_report, runs)
            for i in range(len(runs)):
                self.reports[i] = res[i] 
                for r in self.sim["reports"]:
                    self.reports["raw"][r["label"]].append(res[i][r["label"]])
        else:
            for i in range(len(runs)):
                run = runs[i]
                run.run()
                self.reports[i] = run.reports
                for r in self.sim["reports"]:
                    # raw data across all runs of a simulation in a single file
                    # [raw][<report label>]
                    self.reports["raw"][r["label"]].append(run.reports[r["label"]])
        for r in self.sim["reports"]:
            summarizer = get_report(r)
            if summarizer is not None:
                # summary data across all runs of a single simulation in a single file
                # [summary][<report label>]
                self.reports["summary"][r["label"]] = summarizer.summarize_raw_data(self.reports["raw"][r["label"]])

class FileSimulator:
    def __init__(self, fname, base, sim, pool=None, opts={}):
        self.reports = {"simulations": {}, "raw": {}, "summary": {}}
        self.fname = fname
        self.base = base
        self.sim = sim
        self.pool = pool
        self.opts = opts
        with open(fname, 'r') as f:
            self.choices = parse_file(f)
        if opts.get("summarize", False):
            summary.summarize_options(self.base, choices=self.choices)

    def simulation(self, index):
        return SimulationRun(self.base, self.sim, self.sim["simulations"][index], self.choices, self.pool, self.opts)

    def run(self):
        print("FILE: " + self.fname,file=sys.stderr)
        for s in range(len(self.sim["simulations"])):
            simulation = self.simulation(s)
            label = simulation.label
            simulation.run()
            self.reports["simulations"][label] = simulation.reports
        for r in self.sim["reports"]:
            summarizer = get_report(r)
            if summarizer is not None:
                # raw and summary data across all runs of _all_ simulations in a single file
                # [raw][<report label>] and [summary][<report label>]
                self.reports["raw"][r["label"]] = summarizer.combine_simulations(self.reports, r["label"])
                self.reports["summary"][r["label"]] = summarizer.summarize_raw_data(self.reports["raw"][r["label"]])
        sys.stderr.flush()

class RandomizerSimulator:
    def __init__(self, choice_files, base, sim, pool=None, opts={}):
        self.reports = {"files": {}, "simulations": {}, "raw": {}, "summary": {}}
        self.filenames = choice_files
        self.base = base
        self.sim = sim
        self.pool = pool
        self.opts = opts

    def file_simulator(self, file_index):
        return FileSimulator(self.filenames[file_index], self.base, self.sim, self.pool, self.opts)

    def run(self):
        for file_index in range(len(self.filenames)):
            fname = self.filenames[file_index]
            file_simulator = self.file_simulator(file_index)
            file_simulator.run()
            self.reports["files"][fname] = file_simulator.reports
        for sl in [simulation_label(simulation, self.sim) for simulation in self.sim["simulations"]]:
            self.reports["simulations"][sl] = {"raw": {}, "summary": {}}
        for r in self.sim["reports"]:
            summarizer = get_report(r)
            if summarizer is not None:
                # raw and summary data across all runs of each simulation, across all files
                # [simulations][<simulation identifier>][raw][<report label>] and [summary][<report label>]
                for s in range(len(self.sim["simulations"])):
                    simulation = self.sim["simulations"][s]
                    label = simulation_label(simulation, self.sim)
                    self.reports["simulations"][label]["raw"][r["label"]] = summarizer.combine_files(self.reports, r["label"], label)
                    self.reports["simulations"][label]["summary"][r["label"]] = summarizer.summarize_raw_data(self.reports["simulations"][label]["raw"][r["label"]])
                # raw and summary data across all runs of all simulations across all files
                # [raw][<report label>] and [summary][<report label>]
                self.reports["raw"][r["label"]] = summarizer.combine_simulations(self.reports, r["label"])
                self.reports["summary"][r["label"]] = summarizer.summarize_raw_data(self.reports["raw"][r["label"]])
