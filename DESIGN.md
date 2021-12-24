## Files ##

This tool should take several files that describe the basic settings for the game being simulated, a description of the simulation to run, and finally a file or set of files that describe randomized choices.

### Base file ###

This file is fairly complex. It should be a JSON (or YAML, maybe?) file with these structures:

 * version: 1
 * unlockables: dictionary, mapping a key (string) to a dictionary describing the unlockable:
   * requirements: optional (missing means no requirements). can be string (a key to a single required thing); list (a list of keys, requires all of them); or dict with keys "and"/"or" that are lists. List elems are either strings or lists of strings (lists denote a group joined by the opposite operator). If both are present, meaning is "everything in 'and' plus one of the 'or' options".
   * unlocks: optional list of other unlockables that are also unlocked if this one is chosen and unlocked
 * findables: dictionary, mapping a key (string) to a dictionary describing the findable:
   * unlocks: optional list of unlockables that are immediately unlocked (no need of choice-making) if this findable is found
 * initial: dictionary, mapping a key (string) to a dictionary describing a location things can be found in, but which doesn't require unlocking (if a findable is in one of these locations, the player has it from the start regardless; if a findable is in an unlockable location with no requirements, the player can choose to do it immediately in order to gain the findable)

findables are key items and characters in JoT; unlockables are dungeons/key item checks; initial is just the two start characters

### Choices file(s) ###

These files are the most simple. They should be a JSON file with a single one-level object mapping keys of locations (unlockable & initial) to keys of findables.

Also, version: 1. Don't name locations `version`.

### Simulation file ###

This file describes the simulation or simulations to run, and what information to collect.

Simulations can follow different strategies:
 * ordered list of choices: always do the first thing in the list that's accessible to you
 * pure random: choose a random thing to do from the list that's accessible to you
 * weighted random
 * probably other stuff that's harder to implement, like dependent choices
 * some combination

For now, we can call this all one kind of strategy type:
 * `weighted-random`, which has an optional list of `first-choices` (done in order when available), and an optional list of `weights` (which are [choice, weight] tuple/lists). If something is in the `first-choices` list, do the first available. If not, choose randomly among available choices, using the weights in `weights` or `1` as a default.

All strategies can take a `count` key of a number of simulations to run, default 1, and an optional `label`.

Simulations have to have some sort of "end state" as well. For now we'll just have that be a set of keys, unlockables, and the simulation ends after any of those unlockables is finished. For JoT probably this is Black Omen & Ocean Palace.

Simulations can also collect information (like what go mode was chosen). We'll call them reports, I guess.

To start:
 * `qualitative`: needs map of `categories`; category keys to dictionaries describing the conditions. and/or lists like unlockables, but each condition is a dict with a `type` key and other keys for other needed info
   * `made-choice` condition type takes a `choice` key that is an unlockable

For go modes, we'd have a qualitative report with `made-choice` conditions for magus castle + ocean palace, tyranno lair + ocean palace, and black omen

Reports also _require_ a `label`.

We can automatically aggregate for now, just totals and percentages.

So overall:

 * version: 1
 * simulations: list of dictionaries, each of which is a simulation strategy identified by a `type` key (plus optional arguments and `count` and/or `label` if desired)
 * end-states: list of end-state unlockables
 * reports: list of dictionaries, each of which is a report identified by `type` and requiring a `label`, plus arguments to calculate with

## Algorithm ##

Roughly, of course.

 * read base and simulation files
 * initialize record-keeping based on `reports` in simulation file
 * for each choices file:
   * read file, initialize lists of unlockables/findables based on `initial` setting and random choices (available unlockables, unlocked unlockables, and found findables)
   * repeatedly:
     * check win conditions and reports, update or finish as needed
     * make a choice based on simulation parameters and available unlockables
 * aggregate reports information
