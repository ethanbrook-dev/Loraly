"""
slang_terms.py

This module contains a comprehensive, curated list of modern slang terms,
chat fillers, abbreviations, emojis, and common misspellings/variants for
use in conversational dataset augmentation.

All terms include:
- Classic slang
- Modern slang / viral trends
- Fillers and casual interjections
- Typo forms / shorthand / vowel drops
- Emphasized or repeated letters (e.g., "loooool", "yesss")
"""

# -------------------------------
# Full slang, filler, and typo list
# -------------------------------
_SLANG_TERMS = [
    # Classic & modern slang
    "ace", "aight", "ight", "airhead", "amped", "a-game", "afterparty", "awks", "aren'tcha",
    "antsy", "asap", "axed", "all-out",
    "bae", "banger", "boujee", "bro", "buzzkill", "bummer", "boss",
    "beef", "blow off", "benched",
    "cap", "clout", "cringe", "creep", "cheesy", "clown", "cuffed", "chop it up", "cop", "cash out",
    "dope", "dank", "ditch", "dub", "drip", "dime", "drop", "dummy", "don't trip", "dig it",
    "decked out", "extra", "eww", "ego trip", "emo", "e-girl", "e-boy", "endgame",
    "eye candy",
    "flex", "fomo", "fam", "freak out", "flaky", "fired up", "facepalm", "feelin’ it", "flip out", "fake it",
    "frontin’", "fire", "fuzz", "fly", "flop",
    "ghost", "goat", "gassed", "grind", "gucci", "gig", "glow up", "goner", "gutsy", "geek out", "gimme",
    "grit", "goof",
    "hype", "hater", "hangry", "hit up", "hooked", "homie", "hot mess", "hop off", "high-key", "hecka", "hustle",
    "hyped up", "hold up", "hit the spot", "heat",
    "i'm down", "iffy", "icy", "idk", "i'm game", "irl", "it's lit", "i'm shook", "in your feels", "i'm vibing", "it slaps",
    "jelly", "jit", "juiced", "janky", "j chillin’", "jam", "joke’s on you", "jawn", "jumped",
    "jonesing", "jammed up", "juice", "jive", "jaw-dropper",
    "kicks", "krazy", "k.o.", "killin’ it", "keep it real", "keke", "kickback", "kaput",
    "kool", "keyed up", "keep cool", "knock off",
    "lit", "low-key", "lokey", "lol", "lolll", "loooool", "lurker", "link up", "legit", "loop in", "litty", "locked in",
    "lagging", "level up", "lay low", "let’s roll",
    "mood", "mia", "mocked", "mob", "messy", "maxed out", "mic drop", "mad", "move on", "major",
    "make bank", "mashup", "mixed signals",
    "no cap", "nailed it", "ngl", "noob", "nopes", "nah",
    "no sweat", "not it", "nuked", "no worries",
    "on fleek", "omg", "owned", "off the hook", "on point", "outfit check", "on blast", "over it",
    "out cold", "on deck", "over the top", "oof", "on repeat", "off day",
    "props", "pumped", "peeps", "pick-me", "pop off", "plug", "pushy", "packed", "popcorn", "paper", "peaced out",
    "poppin’", "psyched", "put on blast", "party foul",
    "queen", "quirky", "quit it", "quickie", "quiet flex", "quack", "quake", "quench", "quicks", "quip",
    "queue up", "quirkin’", "quick buck", "quarterbacking", "quitter",
    "roasted", "rizz", "ride or die", "ratchet", "rage", "real talk", "ran off", "receipts", "red flag", "rekt",
    "rich vibes", "rando", "roll deep", "run it",
    "savage", "snatched", "shady", "slay", "ship", "spill", "squad", "shook", "stan", "sus", "simmer down", "snap",
    "softie", "smash", "swipe",
    "tea", "thirsty", "throw shade", "turnt", "trashed", "tight", "tmi", "tool", "tapped", "top-tier", "trendsetter",
    "talk trash", "take l", "totes", "troll",
    "ugh", "up for it", "unreal", "uber", "unfriend", "upbeat", "upgrade", "uncool", "not cool bro", "not cool man",
    "unbothered", "upcycle",
    "vibe", "viral", "vexed", "vibing", "valid", "vent", "vids", "vacay", "versed", "villain era", "vroom",
    "voice note", "vlog", "volley",
    "woke", "whip", "wavy", "wack", "wrecked", "weak", "wrap it up", "word", "wannabe", "wildin’", "whatevs",
    "wing it", "whoa", "work it", "walk off",
    "xoxo", "xtra", "x-ray eyes", "x-ing out", "x-factor", "xed", "xhausted", "xplode", "xpress", "xactly",
    "x-game mode", "x-perience", "x-treme", "x-it", "xhale",
    "yas", "yikes", "yolo", "y’all", "yeet", "yawnfest", "yard", "yapper", "yoloed", "yanked", "yummy", "yawn",
    "yellfest", "you good?", "yoo", "yeaaah", "yeettt", "yaaasss",
    "zonked", "zoomer", "zing", "zapped", "zesty", "z-list", "zit-faced", "zilla", "zapped out", "zip it",
    "zipped", "zero chill", "zooming", "zany",

    # Viral / trendy / fillers
    "bussin’", "cheugy", "simp", "finna", "mog", "pull up", "my homie",
    "rofl", "lmao", "lmfao", "lolz", "lolol", "lool", "haha", "heh", "huh", "meh", "ugh", "idk", "idk tho", "bruh",
    "tbh", "fr", "ngl", "omfg", "yolo", "smh", "ikr", "irl", "fml", "btw", "wtf", "omw", "afk",
    "g2g", "bff", "bffs", "jk", "jk lol", "nvm", "lmbo", "lmfaooo", "sksksk", "and i oop", "yeet yeet", "yeetttt",
    "sksk", "uwu", "owo", "rawr", "boi", "sis", "fam", "fam bam", "bet", "cap", "no cap", "sheesh", "cheers",
    "fr fr", "lmk", "wyd", "wtp", "stfu", "stfu lol", "lololol", "omgg", "yesss", "yep", "yaaaas", "yaaassss", "yep yep",
    "lit af", "on god", "deadass", "big mood", "mood af", "vibe check", "periodt", "ok boomer", "okurrr", "skrrt", "bruhhh", "bruhh",
    "aight aight", "ight ight", "ighty", "ightyight", "lowkey"
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
