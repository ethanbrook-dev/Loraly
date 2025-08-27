"""
slang_terms.py

This module contains a curated list of modern slang terms that can be used
to detect or augment conversational datasets. 

NOTE: Some entries include common misspellings or variant forms (e.g., "lowkey" -> "lokey", "aight" -> "ight") 
to capture casual typing in chats and social media.

It also provides a function to retrieve them, with an option to return everything in lowercase.
"""

# Curated slang list with misspellings/variants
_SLANG_TERMS = [
    # Classic / modern slang
    "Ace", "Aight", "Ight", "Airhead", "Amped", "A-game", "Afterparty", "Awks", "Aren’tcha",
    "Antsy", "Asap", "Axed", "All-out",
    "Bae", "Banger", "Boujee", "Bro", "Buzzkill", "Bummer", "Boss",
    "Beef", "Blow off", "Benched",
    "Cap", "Clout", "Cringe", "Creep", "Cheesy", "Clown", "Cuffed", "Chop it up", "Cop", "Cash out",
    "Dope", "Dank", "Ditch", "Dub", "Drip", "Dime", "Drop", "Dummy", "Don’t trip", "Dig it",
    "Decked out", "Extra", "Eww", "Ego trip", "Emo", "E-girl", "E-boy", "Endgame",
    "Eye candy",
    "Flex", "FOMO", "Fam", "Freak out", "Flaky", "Fired up", "Facepalm", "Feelin’ it", "Flip out", "Fake it",
    "Frontin’", "Fire", "Fuzz", "Fly", "Flop",
    "Ghost", "Goat", "Gassed", "Grind", "Gucci", "Gig", "Glow up", "Goner", "Gutsy", "Geek out", "Gimme",
    "Grit", "Goof",
    "Hype", "Hater", "Hangry", "Hit up", "Hooked", "Homie", "Hot mess", "Hop off", "High-key", "Hecka", "Hustle",
    "Hyped up", "Hold up", "Hit the spot", "Heat",
    "I’m down", "Iffy", "Icy", "IDK", "I’m game", "IRL", "It’s lit", "I’m shook", "In your feels", "I’m vibing", "It slaps",
    "Jelly", "Jit", "Juiced", "Janky", "J chillin’", "Jam", "Joke’s on you", "Jawn", "Jumped",
    "Jonesing", "Jammed up", "Juice", "Jive", "Jaw-dropper",
    "Kicks", "Krazy", "K.O.", "Killin’ it", "Keep it real", "Keke", "Kickback", "Kaput",
    "Kool", "Keyed up", "Keep cool", "Knock off",
    "Lit", "Low-key", "Lokey", "LOL", "Lolll", "Lurker", "Link up", "Legit", "Loop in", "Litty", "Locked in",
    "Lagging", "Level up", "Lay low", "Let’s roll",
    "Mood", "MIA", "Mocked", "Mob", "Messy", "Maxed out", "Mic drop", "Mad", "Move on", "Major",
    "Make bank", "Mashup", "Mixed signals",
    "No cap", "Nailed it", "NGL", "Noob", "Nopes", "Nah",
    "No sweat", "Not it", "Nuked", "No worries",
    "On fleek", "OMG", "Owned", "Off the hook", "On point", "Outfit check", "On blast", "Over it",
    "Out cold", "On deck", "Over the top", "Oof", "On repeat", "Off day",
    "Props", "Pumped", "Peeps", "Pick-me", "Pop off", "Plug", "Pushy", "Packed", "Popcorn", "Paper", "Peaced out",
    "Poppin’", "Psyched", "Put on blast", "Party foul",
    "Queen", "Quirky", "Quit it", "Quickie", "Quiet flex", "Quack", "Quake", "Quench", "Quicks", "Quip",
    "Queue up", "Quirkin’", "Quick buck", "Quarterbacking", "Quitter",
    "Roasted", "Rizz", "Ride or die", "Ratchet", "Rage", "Real talk", "Ran off", "Receipts", "Red flag", "Rekt",
    "Rich vibes", "Rando", "Roll deep", "Run it",
    "Savage", "Snatched", "Shady", "Slay", "Ship", "Spill", "Squad", "Shook", "Stan", "Sus", "Simmer down", "Snap",
    "Softie", "Smash", "Swipe",
    "Tea", "Thirsty", "Throw shade", "Turnt", "Trashed", "Tight", "TMI", "Tool", "Tapped", "Top-tier", "Trendsetter",
    "Talk trash", "Take L", "Totes", "Troll",
    "Ugh", "Up for it", "Unreal", "Uber", "Unfriend", "Upbeat", "Upgrade", "Uncool", "Ugh", "Not cool bro", "Not cool man",
    "Unbothered", "Upcycle",
    "Vibe", "Viral", "Vexed", "Vibing", "Valid", "Vent", "Vids", "Vacay", "Versed", "Villain era", "Vroom",
    "Voice note", "Vlog", "Volley",
    "Woke", "Whip", "Wavy", "Wack", "Wrecked", "Weak", "Wrap it up", "Word", "Wannabe", "Wildin’", "Whatevs",
    "Wing it", "Whoa", "Work it", "Walk off",
    "Xoxo", "Xtra", "X-ray eyes", "X-ing out", "X-factor", "Xed", "Xhausted", "Xplode", "Xpress", "Xactly",
    "X-game mode", "X-perience", "X-treme", "X-it", "Xhale",
    "Yas", "Yikes", "YOLO", "Y’all", "Yeet", "Yawnfest", "Yard", "Yapper", "Yoloed", "Yanked", "Yummy", "Yawn",
    "Yellfest", "You good?",
    "Zonked", "Zoomer", "Zing", "Zapped", "Zesty", "Z-list", "Zonk", "Zit-faced", "Zilla", "Zapped out", "Zip it",
    "Zipped", "Zero chill", "Zooming", "Zany",

    # Additional modern / viral slang
    "Bussin’", "Cheugy", "Simp", "Finna", "Mog", "Pull up", "My homie",
    "Rofl", "Lmao", "Lmfao"
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
