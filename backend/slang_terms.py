"""
slang_terms.py

This module contains a large list of modern slang terms that can be used
to detect or augment conversational datasets. It also provides a function
to retrieve them, with an option to return everything in lowercase.
"""

# Master slang list (combined from multiple curated sources)
_SLANG_TERMS = [
    "Ace", "Aight", "Airhead", "Amped", "Adulting", "A-game", "Afterparty", "All-nighter", "Awks", "Aren’tcha",
    "Antsy", "Asap", "Axed", "All-out", "All set",
    "Bae", "Banger", "Boujee", "Bro", "Basic", "Burn", "Blast", "Bail", "Buzzkill", "Bread", "Bummer", "Boss",
    "Beef", "Blow off", "Benched",
    "Cap", "Clout", "Cringe", "Creep", "Chill", "Cheesy", "Crash", "Cram", "Cooked", "Clown", "Catch up", "Cuffed",
    "Chop it up", "Cop", "Cash out",
    "Dope", "Dead", "Dank", "Ditch", "Down", "Dub", "Drip", "Dime", "Drop", "Dummy", "Don’t trip", "Dig it",
    "Decked out", "Dive", "Deep",
    "Extra", "Eww", "Ego trip", "Emo", "E-girl", "E-boy", "Eats", "Endgame", "Epic", "EZ", "Edge", "Elbowed", "Empty",
    "Eye candy", "Even out",
    "Flex", "FOMO", "Fam", "Freak out", "Flaky", "Fired up", "Facepalm", "Feelin’ it", "Flip out", "Fake it",
    "Frontin’", "Fire", "Fuzz", "Fly", "Flop",
    "Ghost", "Goat", "Gassed", "Grind", "Gucci", "Gig", "Glow up", "Grub", "Goner", "Gutsy", "Geek out", "Gimme",
    "Grit", "Goof", "Gone",
    "Hype", "Hater", "Hangry", "Hit up", "Hooked", "Homie", "Hot mess", "Hop off", "High-key", "Hecka", "Hustle",
    "Hyped up", "Hold up", "Hit the spot", "Heat",
    "I’m down", "Iffy", "Icy", "IDK", "I’m game", "IRL", "It’s lit", "I’m shook", "In your feels", "I’m weak",
    "Insta", "I can’t even", "Iconic", "I’m vibing", "It slaps",
    "Jacked", "Jelly", "Jit", "Juiced", "Janky", "J chillin’", "Jam", "Joke’s on you", "Jawn", "Jumped",
    "Jonesing", "Jammed up", "Juice", "Jive", "Jaw-dropper",
    "Kick it", "Kicks", "Kinda", "Krazy", "K.O.", "Killin’ it", "Keep it real", "Keke", "Kickback", "Kaput",
    "Kicks in", "Kool", "Keyed up", "Keep cool", "Knock off",
    "Lit", "Low-key", "Lame", "LOL", "Lurker", "Link up", "Legit", "Loser", "Loop in", "Litty", "Locked in",
    "Lagging", "Level up", "Lay low", "Let’s roll",
    "Mood", "MIA", "My bad", "Mocked", "Mob", "Main", "Messy", "Maxed out", "Mic drop", "Mad", "Move on", "Major",
    "Make bank", "Mashup", "Mixed signals",
    "No cap", "Nailed it", "NGL", "Noob", "Netflix and chill", "Nuts", "No clue", "Next-level", "Nopes", "Nah",
    "No sweat", "Not it", "Nuked", "No worries", "Neat",
    "On fleek", "OMG", "Owned", "Off the hook", "Outta line", "On point", "Outfit check", "On blast", "Over it",
    "Out cold", "On deck", "Over the top", "Oof", "On repeat", "Off day",
    "Props", "Pumped", "Peeps", "Pick-me", "Pop off", "Plug", "Pushy", "Packed", "Popcorn", "Paper", "Peaced out",
    "Poppin’", "Psyched", "Put on blast", "Party foul",
    "Queen", "Quirky", "Quit it", "Quickie", "Quiet flex", "Quack", "Quake", "Quench", "Quicks", "Quip",
    "Queue up", "Quirkin’", "Quick buck", "Quarterbacking", "Quitter",
    "Roasted", "Rizz", "Ride or die", "Ratchet", "Rage", "Real talk", "Ran off", "Receipts", "Red flag", "Rekt",
    "Rich vibes", "Rando", "Roll deep", "Rip", "Run it",
    "Savage", "Snatched", "Shady", "Slay", "Ship", "Spill", "Squad", "Shook", "Stan", "Sus", "Simmer down", "Snap",
    "Softie", "Smash", "Swipe",
    "Tea", "Thirsty", "Throw shade", "Turnt", "Trashed", "Tight", "TMI", "Tool", "Tapped", "Top-tier", "Trendsetter",
    "Talk trash", "Take L", "Totes", "Troll",
    "Ugh", "Up for it", "Unreal", "Uber", "Unfriend", "Upbeat", "Upgrade", "Uncool", "Unwind", "Underdog", "U-turn",
    "Unbothered", "Upcycle", "Unrealistic", "Use your head",
    "Vibe", "Viral", "Vanilla", "Vexed", "Vibing", "Valid", "Vent", "Vids", "Vacay", "Versed", "Villain era", "Vroom",
    "Voice note", "Vlog", "Volley",
    "Woke", "Whip", "Wavy", "Wack", "Wrecked", "Weak", "Wrap it up", "Word", "Wannabe", "Wildin’", "Whatevs",
    "Wing it", "Whoa", "Work it", "Walk off",
    "Xoxo", "Xtra", "X-ray eyes", "X-ing out", "X-factor", "Xed", "Xhausted", "Xplode", "Xpress", "Xactly",
    "X-game mode", "X-perience", "X-treme", "X-it", "Xhale",
    "Yas", "Yikes", "YOLO", "Y’all", "Yeet", "Yawnfest", "Yard", "Yapper", "Yoloed", "Yanked", "Yummy", "Yawn",
    "Yankee", "Yellfest", "You good?",
    "Zonked", "Zoomer", "Zing", "Zapped", "Zesty", "Z-list", "Zonk", "Zit-faced", "Zilla", "Zapped out", "Zip it",
    "Zipped", "Zero chill", "Zooming", "Zany"
]


def get_all_slang_terms(lowercase: bool = False):
    """
    Retrieve the full slang term list.

    Args:
        lowercase (bool, optional): If True, return all slang terms in lowercase. Defaults to False.

    Returns:
        list[str]: List of slang terms.
    """
    if lowercase:
        return [term.lower() for term in _SLANG_TERMS]
    return _SLANG_TERMS[:]
