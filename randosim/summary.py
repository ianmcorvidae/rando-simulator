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
