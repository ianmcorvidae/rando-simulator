import argparse
import random
import json
import copy

def parse_file(arg):
    return json.load(arg)

def summarize_options(base, choices=None):
    if choices is None:
        print("No choices provided, showing available options.")
        print("All unlockables:")
        print(", ".join(base["unlockables"].keys()))
        print("----------")
        print("All findables:")
        print(", ".join(base["findables"].keys()))
        print("----------")
        print("Initial unlocks:")
        print(", ".join(base["initial"].keys()))
    else:
        print("Initial unlocks + findables:")
        print(", ".join([k + ": " + choices[k] for k in base["initial"].keys()]))
        print("----------")
        print("All unlockables with findables:")
        print(", ".join([k + ": " + choices[k] for k in base["unlockables"].keys() if k in choices]))
        print("----------")
        print("All other unlockables:")
        print(", ".join([k for k in base["unlockables"].keys() if k not in choices]))

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

def found_findables(choices, unlocks):
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

    f = found_findables(choices, unlocks)
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

def choose_unlockable(simulation, unlockable, unlocks):
    available = list(set(unlockable) - set(unlocks))
    if simulation.get('type', 'weighted-random') == 'weighted-random':
        # check first-choices
        for choice in simulation.get('first-choices', []):
            if choice in available:
                print(">> found first-choice option: " + choice)
                return choice
        # then choose randomly
        return random.choice(available)

def run_one_simulation(base, choices, sim, simulation):
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
        (found, unlocks, unlockables) = update_lists(base, choices, found, unlocks, unlockables)
        print("----------")
        print("Available unlocks: " + ", ".join(set(unlockables) - set(unlocks)))
        print("Already unlocked: " + ", ".join(unlocks))
        print("Already found: " + ", ".join(found))
    print("Finished!")
    print("----------")

if __name__ == "__main__":
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
        summarize_options(base)
    else:
        for fname in args.choices:
            print("Summary of " + fname + ":")
            with open(fname, 'r') as f:
                choices = parse_file(f)
            summarize_options(base, choices=choices)
            for simulation in sim["simulations"]:
                run_one_simulation(base, choices, sim, simulation)
            #print("----------")
            #found = [choices[k] for k in base["initial"].keys()]
            #unlocks = []
            #unlockables = []
            #(found, unlocks, unlockables) = update_lists(base, choices, found, unlocks, unlockables)
            #print("----------")
            #print("Available unlocks: " + ", ".join(set(unlockables) - set(unlocks)))
            #print("Already unlocked: " + ", ".join(unlocks))
            #print("Already found: " + ", ".join(found))
            #while len([e for e in sim["end-states"] if e in unlocks]) == 0:
            #    print("----------")
            #    next_unlock = choose_unlockable(sim["simulations"][0], unlockables, unlocks)
            #    #next_unlock = random.choice(list(set(unlockables) - set(unlocks)))
            #    print("Next unlock chosen: " + next_unlock)
            #    unlocks.append(next_unlock)
            #    (found, unlocks, unlockables) = update_lists(base, choices, found, unlocks, unlockables)
            #    print("----------")
            #    print("Available unlocks: " + ", ".join(set(unlockables) - set(unlocks)))
            #    print("Already unlocked: " + ", ".join(unlocks))
            #    print("Already found: " + ", ".join(found))
