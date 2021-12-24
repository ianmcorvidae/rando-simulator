import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate playing through a randomized game, gathering statistics.")
    parser.add_argument('base', help="The base game description file", type=argparse.FileType('r'))
    parser.add_argument('simulation', help="The file specifying the simulation to run", type=argparse.FileType('r'))
    # string for this one, we'll open each one in the loop
    parser.add_argument('choices', help="The file(s) describing randomized choices to use for simulating", nargs='*')
    args = parser.parse_args()
    print(args)
