#!/usr/bin/env python3
"""
decomp_data.py — Shared data library for pokeemerald-expansion dev tools

Pure Python; no Qt dependency at import time.
Conditional PyQt5 import only inside make_shiny_pixmap().
"""
import os, re, sys, json, math as _math
from dataclasses import dataclass, field

# ══════════════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════════════
ROOT           = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
DATA_DIR       = os.path.join(ROOT, "src/data/pokemon/species_info")
GEN_FILES      = {i: os.path.join(DATA_DIR, f"gen_{i}_families.h") for i in range(1, 10)}
SPRITES_DIR    = os.path.join(ROOT, "graphics/pokemon")
PARTY_FILE     = os.path.join(ROOT, "src/data/trainers.party")
MOVES_FILE     = os.path.join(ROOT, "src/data/moves_info.h")
SPECIES_FILE   = os.path.join(ROOT, "include/constants/species.h")
ITEMS_FILE     = os.path.join(ROOT, "include/constants/items.h")
TRAINERS_CONST = os.path.join(ROOT, "include/constants/trainers.h")
AI_FLAGS_FILE  = os.path.join(ROOT, "include/constants/battle_ai.h")
ABILITIES_FILE = os.path.join(ROOT, "include/constants/abilities.h")
ITEM_ICONS     = os.path.join(ROOT, "graphics/items/icons")
TRAINER_PICS   = os.path.join(ROOT, "graphics/trainers/front_pics")
POKEMON_GFX    = SPRITES_DIR   # alias
LEARNSET_DIR   = os.path.join(ROOT, "src/data/pokemon/level_up_learnsets")
EGG_MOVES_FILE = os.path.join(ROOT, "src/data/pokemon/egg_moves.h")
TEACHABLE_FILE  = os.path.join(ROOT, "src/data/pokemon/teachable_learnsets.h")
TMSHMHM_FILE    = os.path.join(ROOT, "include/constants/tms_hms.h")
ABILITIES_DATA_FILE = os.path.join(ROOT, "src/data/abilities.h")
WILD_ENCOUNTERS_FILE = os.path.join(ROOT, "src/data/wild_encounters.json")
ITEMS_DATA_FILE          = os.path.join(ROOT, "src/data/items.h")
REGION_MAP_SECTIONS_FILE = os.path.join(ROOT, "src/data/region_map/region_map_sections.json")
REGION_MAP_LAYOUT_FILE   = os.path.join(ROOT, "src/data/region_map/region_map_layout.h")
MAPS_DATA_DIR            = os.path.join(ROOT, "data/maps")

# ══════════════════════════════════════════════════════════════════════════════
# TYPE / DISPLAY CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
ALL_TYPES = [
    "NORMAL","FIRE","WATER","ELECTRIC","GRASS","ICE","FIGHTING","POISON",
    "GROUND","FLYING","PSYCHIC","BUG","ROCK","GHOST","DRAGON","DARK","STEEL","FAIRY",
]
TYPE_HEX = {
    "NORMAL":"#a8a878","FIRE":"#f08030","WATER":"#6890f0","ELECTRIC":"#f8d030",
    "GRASS":"#78c850","ICE":"#98d8d8","FIGHTING":"#c03028","POISON":"#a040a0",
    "GROUND":"#e0c068","FLYING":"#a890f0","PSYCHIC":"#f85888","BUG":"#a8b820",
    "ROCK":"#b8a038","GHOST":"#705898","DRAGON":"#7038f8","DARK":"#705848",
    "STEEL":"#b8b8d0","FAIRY":"#ee99ac",
}
CATEGORY_HEX = {
    "DAMAGE_CATEGORY_PHYSICAL": "#fab387",
    "DAMAGE_CATEGORY_SPECIAL":  "#89b4fa",
    "DAMAGE_CATEGORY_STATUS":   "#a6adc8",
}
STATUS_HEX  = {"BUFFED":"#a6e3a1","NERFED":"#f38ba8","UNTOUCHED":"#6c7086"}
STATUS_BG   = {"BUFFED":"#1a2e1a","NERFED":"#2e1a1a","UNTOUCHED":"#1e1e2e"}
GEN_HEX     = {
    1:"#cdd6f4",2:"#f9e2af",3:"#a6e3a1",4:"#89b4fa",
    5:"#cba6f7",6:"#89dceb",7:"#fab387",8:"#a6adc8",9:"#eba0ac",
}
EVO_STAGES   = ["SINGLE","BASIC","MIDDLE","FINAL"]
STATUSES     = ["UNTOUCHED","BUFFED","NERFED"]
STATUS_CYCLE = ["UNTOUCHED","BUFFED","NERFED"]
STAGE_ORDER  = {"BASIC":0,"MIDDLE":1,"FINAL":2,"SINGLE":3}

def bst_color(bst):
    if bst >= 600: return "#f38ba8"
    if bst >= 500: return "#fab387"
    if bst >= 400: return "#f9e2af"
    return "#a6adc8"

def type_color(t):
    return TYPE_HEX.get(t.upper().replace("TYPE_",""), "#585b70")

def cat_color(c):
    return CATEGORY_HEX.get(c, "#585b70")

def cat_label(c):
    return c.replace("DAMAGE_CATEGORY_","").title() if c else "—"

# ══════════════════════════════════════════════════════════════════════════════
# NATURE / STAT CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
NATURE_MODS = {
    "Hardy":(0,0),"Lonely":(1,2),"Brave":(1,5),"Adamant":(1,3),"Naughty":(1,4),
    "Bold":(2,1),"Docile":(0,0),"Relaxed":(2,5),"Impish":(2,3),"Lax":(2,4),
    "Timid":(5,1),"Hasty":(5,2),"Serious":(0,0),"Jolly":(5,3),"Naive":(5,4),
    "Modest":(3,1),"Mild":(3,2),"Quiet":(3,5),"Bashful":(0,0),"Rash":(3,4),
    "Calm":(4,1),"Gentle":(4,2),"Sassy":(4,5),"Careful":(4,3),"Quirky":(0,0),
}
NATURES    = list(NATURE_MODS.keys())
STAT_NAMES = ["HP","Atk","Def","SpA","SpD","Spe"]
_NATURE_BOOST = {
    "Lonely":(1,2),"Brave":(1,5),"Adamant":(1,3),"Naughty":(1,4),
    "Bold":(2,1),"Relaxed":(2,5),"Impish":(2,3),"Lax":(2,4),
    "Timid":(5,1),"Hasty":(5,2),"Jolly":(5,3),"Naive":(5,4),
    "Modest":(3,1),"Mild":(3,2),"Quiet":(3,5),"Rash":(3,4),
    "Calm":(4,1),"Gentle":(4,2),"Sassy":(4,5),"Careful":(4,3),
}

# ══════════════════════════════════════════════════════════════════════════════
# TRAINER / BATTLE CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
AI_FLAGS_ORDERED = [
    ("Check Bad Move",             "AI_FLAG_CHECK_BAD_MOVE"),
    ("Try To Faint",               "AI_FLAG_TRY_TO_FAINT"),
    ("Check Viability",            "AI_FLAG_CHECK_VIABILITY"),
    ("Force Setup First Turn",     "AI_FLAG_FORCE_SETUP_FIRST_TURN"),
    ("Risky",                      "AI_FLAG_RISKY"),
    ("Try To 2HKO",                "AI_FLAG_TRY_TO_2HKO"),
    ("Prefer Baton Pass",          "AI_FLAG_PREFER_BATON_PASS"),
    ("HP Aware",                   "AI_FLAG_HP_AWARE"),
    ("Powerful Status",            "AI_FLAG_POWERFUL_STATUS"),
    ("Negate Unaware",             "AI_FLAG_NEGATE_UNAWARE"),
    ("Will Suicide",               "AI_FLAG_WILL_SUICIDE"),
    ("Prefer Status Moves",        "AI_FLAG_PREFER_STATUS_MOVES"),
    ("Stall",                      "AI_FLAG_STALL"),
    ("Smart Switching",            "AI_FLAG_SMART_SWITCHING"),
    ("Ace Pokemon",                "AI_FLAG_ACE_POKEMON"),
    ("Omniscient",                 "AI_FLAG_OMNISCIENT"),
    ("Smart Mon Choices",          "AI_FLAG_SMART_MON_CHOICES"),
    ("Conservative",               "AI_FLAG_CONSERVATIVE"),
    ("Sequence Switching",         "AI_FLAG_SEQUENCE_SWITCHING"),
    ("Double Ace Pokemon",         "AI_FLAG_DOUBLE_ACE_POKEMON"),
    ("Weigh Ability Prediction",   "AI_FLAG_WEIGH_ABILITY_PREDICTION"),
    ("Prefer Highest Damage Move", "AI_FLAG_PREFER_HIGHEST_DAMAGE_MOVE"),
    ("Predict Switch",             "AI_FLAG_PREDICT_SWITCH"),
    ("Predict Incoming Mon",       "AI_FLAG_PREDICT_INCOMING_MON"),
    ("PP Stall Prevention",        "AI_FLAG_PP_STALL_PREVENTION"),
    ("Predict Move",               "AI_FLAG_PREDICT_MOVE"),
]
AI_FLAG_BY_DISPLAY  = {d: c for d, c in AI_FLAGS_ORDERED}
AI_CONST_TO_DISPLAY = {c: d for d, c in AI_FLAGS_ORDERED}
AI_PRESETS = {
    "Basic Trainer":  ["Check Bad Move","Try To Faint","Check Viability"],
    "Smart Trainer":  ["Check Bad Move","Try To Faint","Check Viability","Omniscient",
                       "Smart Switching","Smart Mon Choices","Weigh Ability Prediction"],
    "Prediction":     ["Predict Switch","Predict Incoming Mon","Predict Move"],
}
MUSIC_OPTIONS   = ["Male","Female","Girl","Suspicious","Intense","Cool",
                   "Aqua","Magma","Swimmer","Twins","Elite Four","Hiker","Interviewer","Rich"]
GENDER_OPTIONS  = ["Male","Female"]
BATTLE_OPTIONS  = ["Singles","Doubles"]
MUGSHOT_OPTIONS = ["","Purple","Green","Pink","Blue","Yellow"]

# ══════════════════════════════════════════════════════════════════════════════
# REGEX PATTERNS
# ══════════════════════════════════════════════════════════════════════════════
PAT_BLOCK      = re.compile(r"\[SPECIES_([A-Z0-9_]+)\]\s*=\s*\{(.*?)\n\s*\},", re.DOTALL)
PAT_FIELD      = re.compile(r"\.([a-zA-Z0-9_]+)\s*=\s*([^,\n]+)")
PAT_TYPES      = re.compile(r"\.types\s*=\s*MON_TYPES\s*\(\s*([A-Z_0-9]+)\s*(?:,\s*([A-Z_0-9]+))?\s*\)")
PAT_TYPES_BRACE= re.compile(r"\.types\s*=\s*\{\s*([A-Z_0-9]+)\s*(?:,\s*([A-Z_0-9]+))?\s*\}")
PAT_TYPE_MACRO = re.compile(r"#define\s+([A-Z0-9_]+)\s+\{\s*(TYPE_[A-Z0-9_]+)(?:\s*,\s*(TYPE_[A-Z0-9_]+))?\s*\}", re.MULTILINE)
PAT_TYPES_MACRO_REF = re.compile(r"\.types\s*=\s*([A-Z][A-Z0-9_]+)\s*,")
PAT_NAME       = re.compile(r'\.speciesName\s*=\s*_\("([^"]+)"\)')
PAT_DEFINE     = re.compile(r'^#define\s+([A-Z0-9_]+)\s+\(?(-?\d+)\)?\s*(?://.*)?$', re.MULTILINE)
PAT_TERNARY    = re.compile(r'\(?P_UPDATED_\w+\s*>=\s*GEN_\w+\)?\s*\?\s*(-?\d+)\s*:\s*(-?\d+)')
PAT_EVO_HAS    = re.compile(r'\.evolutions\s*=\s*EVOLUTION\s*\(')
PAT_EVO_TARGET = re.compile(r'EVO_\w+\s*,\s*[^,{}]+,\s*(SPECIES_[A-Z0-9_]+)\s*\}')

# ══════════════════════════════════════════════════════════════════════════════
# FORM / SPRITE MAPS
# ══════════════════════════════════════════════════════════════════════════════
_FORM_TAGS = (
    "_MEGA","_ALOLAN","_GALARIAN","_HISUIAN","_PALDEAN","_GMAX","_PRIMAL",
    "_ORIGIN","_THERIAN","_RESOLUTE","_PIROUETTE","_ASH","_ETERNAMAX",
    "_CROWNED","_HANGRY","_GULPING","_GORGING","_NOICE","_AMPED","_LOW_KEY",
    "_HERO","_WELLSPRING","_HEARTHFLAME","_CORNERSTONE",
    "_FAMILY_OF_THREE","_FAMILY_OF_FOUR",
)
_SPRITE_SUFFIX_MAP = {
    'ALOLAN': 'alola', 'GALARIAN': 'galar', 'HISUIAN': 'hisui', 'PALDEAN': 'paldea',
    'ALOLA': 'alola',  'GALAR': 'galar',    'HISUI': 'hisui',   'PALDEA': 'paldea',
    'MEGA_X': 'mega_x', 'MEGA_Y': 'mega_y',
}
_FORM_DISPLAY = {
    'MEGA_X':'Mega X','MEGA_Y':'Mega Y','LOW_KEY':'Low Key','AMPED':'Amped',
    'DUSK_MANE':'Dusk Mane','DAWN_WINGS':'Dawn Wings',
    'TEN_PERCENT':'10%','COMPLETE':'Complete',
    'ORIGINAL_CAP':'Original Cap','HOENN_CAP':'Hoenn Cap',
    'SINNOH_CAP':'Sinnoh Cap','UNOVA_CAP':'Unova Cap',
    'KALOS_CAP':'Kalos Cap','ALOLA_CAP':'Alola Cap',
    'PARTNER_CAP':'Partner Cap','WORLD_CAP':'World Cap',
    'POWER_CONSTRUCT':'Power Construct',
    'FAMILY_OF_THREE':'3-Family','FAMILY_OF_FOUR':'4-Family',
    'WELLSPRING':'Wellspring','HEARTHFLAME':'Hearthflame','CORNERSTONE':'Cornerstone',
    'MEGA':'Mega',
    'ALOLAN':'Alolan','ALOLA':'Alolan','GALARIAN':'Galarian','GALAR':'Galarian',
    'HISUIAN':'Hisuian','HISUI':'Hisuian','PALDEAN':'Paldean','PALDEA':'Paldean',
    'GMAX':'Gigantamax','PRIMAL':'Primal','ORIGIN':'Origin','THERIAN':'Therian',
    'RESOLUTE':'Resolute','PIROUETTE':'Pirouette','ETERNAMAX':'Eternamax',
    'CROWNED':'Crowned','HANGRY':'Hangry','GULPING':'Gulping','GORGING':'Gorging',
    'NOICE':'Noice','HERO':'Hero',
    'ATTACK':'Attack','DEFENSE':'Defense','SPEED':'Speed',
    'MIDNIGHT':'Midnight','DUSK':'Dusk','MIDDAY':'Midday',
    'CONFINED':'Confined','UNBOUND':'Unbound',
    'SUNNY':'Sunny','RAINY':'Rainy','SNOWY':'Snowy',
    'EAST':'East Sea','WEST':'West Sea',
    'PLANT':'Plant','SANDY':'Sandy','TRASH':'Trash',
    'OVERCAST':'Overcast','SUNSHINE':'Sunshine',
    'SKY':'Sky','LAND':'Land','BLADE':'Blade','SHIELD':'Shield',
    'WHITE':'White','BLACK':'Black',
    'ORDINARY':'Ordinary','ARIA':'Aria',
    'COSPLAY':'Cosplay','ASH':'Ash',
    'SMALL':'Small','LARGE':'Large','SUPER':'Super','AVERAGE':'Average',
    'ULTRA':'Ultra','BUSTED':'Busted',
    'DADA':'Dada','STARTER':'Starter','SCHOOL':'School',
    'F':'Female','FEMALE':'Female','MALE':'Male',
    'CORE':'Core','BAILE':'Baile','POM_POM':'Pom-Pom','PA_U':"Pa'u",'SENSU':'Sensu',
}

def get_form_label(key, name):
    base = name.upper().replace(' ','_').replace('-','_').replace('.','').replace("'","")
    if key == base or not key.startswith(base + '_'):
        return ''
    suffix = key[len(base) + 1:]
    parts  = suffix.split('_')
    for n in range(len(parts), 0, -1):
        cand = '_'.join(parts[:n])
        if cand in _FORM_DISPLAY:
            return _FORM_DISPLAY[cand]
    return suffix.replace('_',' ').title()

# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════
class Pokemon:
    __slots__ = (
        'key','name','display_name','gen','type1','type2',
        'hp','atk','def_','spa','spd','spe','bst',
        'stage','is_legendary','is_mythical','is_ultra_beast','is_paradox',
        'description','category','nat_dex','height','weight','abilities','catch_rate',
        'gender_ratio',
    )
    def __init__(self, key, name, gen, type1, type2,
                 hp, atk, def_, spa, spd, spe, stage,
                 legendary=False, mythical=False, ultra_beast=False, paradox=False,
                 description='', category='', nat_dex=0, height=0, weight=0, abilities=(),
                 display_name='', catch_rate=0, gender_ratio=0):
        self.key, self.name, self.gen = key, name, gen
        self.display_name = display_name or name
        self.type1, self.type2 = type1, type2
        self.hp, self.atk, self.def_ = hp, atk, def_
        self.spa, self.spd, self.spe = spa, spd, spe
        self.bst = hp + atk + def_ + spa + spd + spe
        self.stage = stage
        self.is_legendary, self.is_mythical = legendary, mythical
        self.is_ultra_beast, self.is_paradox = ultra_beast, paradox
        self.description = description
        self.category    = category
        self.nat_dex     = nat_dex
        self.height      = height
        self.weight      = weight
        self.abilities   = abilities
        self.catch_rate  = catch_rate
        self.gender_ratio = gender_ratio
    def has_type(self, t):      return self.type1 == t or self.type2 == t
    def dual_type(self, a, b):  return a in {self.type1,self.type2} and b in {self.type1,self.type2}


@dataclass
class TrainerMon:
    species:       str  = "NONE"
    level:         int  = 5
    nickname:      str  = ""
    gender:        str  = ""
    held_item:     str  = ""
    ability:       str  = ""
    nature:        str  = "Hardy"
    ivs:           list = field(default_factory=lambda: [31]*6)
    evs:           list = field(default_factory=lambda: [0]*6)
    moves:         list = field(default_factory=list)
    happiness:     int  = 255
    ball:          str  = ""
    shiny:         bool = False
    dynamax_level: int  = 10
    gigantamax:    bool = False
    tera_type:     str  = ""
    def display_name(self): return self.nickname if self.nickname else self.species


@dataclass
class Trainer:
    key:             str  = ""
    name:            str  = ""
    trainer_class:   str  = "Pkmn Trainer 1"
    pic:             str  = "Hiker"
    gender:          str  = "Male"
    music:           str  = "Male"
    double_battle:   bool = False
    ai_flags:        list = field(default_factory=list)
    items:           list = field(default_factory=list)
    mugshot:         str  = ""
    starting_status: str  = ""
    party:           list = field(default_factory=list)

# ══════════════════════════════════════════════════════════════════════════════
# CACHE + FILE READ
# ══════════════════════════════════════════════════════════════════════════════
_cache = {}

def _read(path):
    if not os.path.isfile(path): return ""
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

# ══════════════════════════════════════════════════════════════════════════════
# PREPROCESSING  (resolve P_UPDATED_* → Gen 8 / GEN_LATEST values)
# ══════════════════════════════════════════════════════════════════════════════
def resolve_blocks(text, take_first=True):
    lines, result, stack = text.split('\n'), [], []
    def emitting(): return all(e['emit'] for e in stack)
    for line in lines:
        s = line.strip()
        if re.match(r'#if\b', s) or re.match(r'#ifdef\b', s) or re.match(r'#ifndef\b', s):
            is_p = s.startswith('#if ') and bool(re.search(r'P_UPDATED_', s))
            if is_p:  stack.append({'p':True,  'emit': take_first and emitting()})
            else:
                if emitting(): result.append(line)
                stack.append({'p':False, 'emit': emitting()})
        elif s.startswith('#elif') and stack:
            top = stack[-1]
            if top['p']:  top['emit'] = False
            elif emitting(): result.append(line)
        elif s == '#else' and stack:
            top = stack[-1]
            if top['p']:
                top['emit'] = (not take_first) and all(e['emit'] for e in stack[:-1])
            elif emitting(): result.append(line)
        elif s == '#endif' and stack:
            top = stack.pop()
            if not top['p'] and emitting(): result.append(line)
        else:
            if emitting(): result.append(line)
    return '\n'.join(result)

def preprocess(raw):
    t = resolve_blocks(raw, take_first=True)
    t = PAT_TERNARY.sub(lambda m: m.group(1), t)
    macros = {m.group(1): m.group(2) for m in PAT_DEFINE.finditer(t)}
    return t, macros

def _int_v(raw, macros):
    if raw is None: return 0
    v = raw.strip().rstrip(',').strip()
    try: return int(v)
    except: pass
    t = PAT_TERNARY.search(v)
    if t: return int(t.group(1))
    q = re.search(r'\?\s*(-?\d+)\s*:', v)
    if q: return int(q.group(1))
    if v in macros: return _int_v(macros[v], macros)
    subbed = re.sub(r'\b([A-Z][A-Z0-9_]+)\b',
                    lambda m: str(macros[m.group(1)]) if m.group(1) in macros else m.group(1), v)
    if subbed != v:
        t2 = PAT_TERNARY.search(subbed)
        if t2: return int(t2.group(1))
        q2 = re.search(r'\?\s*(-?\d+)\s*:', subbed)
        if q2: return int(q2.group(1))
        try: return int(eval(subbed, {"__builtins__": {}}))  # noqa: S307
        except: pass
    return 0

def _bool_f(fields, key):
    return fields.get(key, 'FALSE').strip().rstrip(',') in ('TRUE','1','true')

def _strip_type(t):
    return t[5:] if t and t.startswith('TYPE_') else (t or '')

# ══════════════════════════════════════════════════════════════════════════════
# EVOLUTION GRAPH
# ══════════════════════════════════════════════════════════════════════════════
def build_evo_graph():
    can_evolve = set(); has_pre_evo = set()
    for path in GEN_FILES.values():
        if not os.path.isfile(path): continue
        raw  = open(path, 'r', encoding='utf-8', errors='replace').read()
        text, _ = preprocess(raw)
        for m in PAT_EVO_TARGET.finditer(text):
            has_pre_evo.add(m.group(1)[8:])
        for bm in PAT_BLOCK.finditer(text):
            if PAT_EVO_HAS.search(bm.group(2)):
                can_evolve.add(bm.group(1))
    return can_evolve, has_pre_evo

def load_evo_chains():
    """Parse EVOLUTION() macros from all gen_*_families.h files.

    Returns (forward, backward) where:
      forward:  {SPECIES_KEY: [{'method', 'param', 'target', 'conditions'}, ...]}
      backward: {SPECIES_KEY: SPECIES_KEY}   (child → parent for chain walking)

    All keys are WITHOUT the SPECIES_ prefix and in UPPER_CASE.
    Each 'conditions' value is a list of human-readable condition strings.
    """
    if '_evo_chains' in _cache:
        return _cache['_evo_chains']

    forward  = {}
    backward = {}

    def _parse_evo_entries(raw_content):
        """Split top-level { } groups from EVOLUTION(...) content."""
        entries, depth, buf = [], 0, []
        for ch in raw_content:
            if ch == '{':
                depth += 1
                buf.append(ch)
            elif ch == '}':
                depth -= 1
                buf.append(ch)
                if depth == 0:
                    entries.append(''.join(buf))
                    buf = []
            elif depth > 0:
                buf.append(ch)
        return entries

    def _split_top_level_commas(text):
        """Split 'text' by commas that are not inside () or {}."""
        parts, depth, buf = [], 0, []
        for ch in text:
            if ch in '({': depth += 1
            elif ch in ')}': depth -= 1
            if ch == ',' and depth == 0:
                parts.append(''.join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        if buf:
            parts.append(''.join(buf).strip())
        return parts

    def _parse_conditions(cond_text):
        """Convert CONDITIONS({IF_X, val, ...}) to list of human-readable strings."""
        labels = []
        for entry in re.findall(r'\{([^}]+)\}', cond_text):
            parts = [p.strip() for p in entry.split(',') if p.strip()]
            if not parts:
                continue
            ctype = parts[0]
            val   = parts[1] if len(parts) > 1 else ''
            val2  = parts[2] if len(parts) > 2 else ''

            if   ctype == 'IF_MIN_FRIENDSHIP':  labels.append('High Friendship')
            elif ctype == 'IF_TIME':
                labels.append('at Night' if 'NIGHT' in val else 'during Day')
            elif ctype == 'IF_NOT_TIME':
                labels.append('during Day' if 'NIGHT' in val else f'not {val}')
            elif ctype == 'IF_GENDER':
                labels.append('if Female' if 'FEMALE' in val else 'if Male')
            elif ctype == 'IF_KNOWS_MOVE':
                labels.append('knowing ' + val.replace('MOVE_','').replace('_',' ').title())
            elif ctype == 'IF_HOLD_ITEM':
                labels.append('holding ' + val.replace('ITEM_','').replace('_',' ').title())
            elif ctype == 'IF_ATK_GT_DEF':      labels.append('Atk > Def')
            elif ctype == 'IF_ATK_LT_DEF':      labels.append('Atk < Def')
            elif ctype == 'IF_ATK_EQ_DEF':      labels.append('Atk = Def')
            elif ctype == 'IF_MIN_BEAUTY':       labels.append(f'Beauty ≥ {val}')
            elif ctype == 'IF_IN_MAPSEC':
                labels.append('in ' + val.replace('MAPSEC_','').replace('_',' ').title())
            elif ctype == 'IF_SPECIES_IN_PARTY':
                labels.append('with ' + val.replace('SPECIES_','').replace('_',' ').title() + ' in party')
            elif ctype == 'IF_TYPE_IN_PARTY':
                labels.append('with ' + val.replace('TYPE_','').title() + '-type in party')
            elif ctype == 'IF_WEATHER':
                labels.append('in ' + val.replace('WEATHER_','').replace('_',' ').title())
            elif ctype == 'IF_MIN_OVERWORLD_STEPS':
                labels.append(f'{val} steps')
            elif ctype == 'IF_TRADE_PARTNER_SPECIES':
                labels.append('trade with ' + val.replace('SPECIES_','').replace('_',' ').title())
            elif ctype == 'IF_DEFEAT_X_WITH_ITEMS':
                labels.append(f'defeat {val}× with items')
            elif ctype == 'IF_CRITICAL_HITS_GE':
                labels.append(f'{val} crits')
            elif ctype == 'IF_CURRENT_DAMAGE_GE':
                labels.append(f'damage ≥ {val}')
            elif ctype == 'IF_RECOIL_DAMAGE_GE':
                labels.append(f'{val} recoil dmg')
            elif ctype == 'IF_USED_MOVE_X_TIMES':
                mv = val.replace('MOVE_','').replace('_',' ').title()
                labels.append(f'use {mv} {val2}×')
            elif ctype == 'IF_BAG_ITEM_COUNT':
                itm = val.replace('ITEM_','').replace('_',' ').title()
                labels.append(f'own {val2}× {itm}')
            elif ctype == 'IF_AMPED_NATURE':    labels.append('Amped nature')
            elif ctype == 'IF_LOW_KEY_NATURE':  labels.append('Low Key nature')
            elif ctype in ('IF_PID_MODULO_100_EQ','IF_PID_MODULO_100_GT',
                           'IF_PID_UPPER_MODULO_10_GT','IF_PID_UPPER_MODULO_10_LT'):
                labels.append('Personality')
            elif ctype == 'IF_IN_MAP':
                labels.append('in ' + val.replace('MAP_','').replace('_',' ').title())
            else:
                labels.append(ctype.replace('IF_','').replace('_',' ').title())
        return labels

    def _method_label(method, param):
        """Return a short human-readable label for an EVO method + param."""
        if method == 'EVO_LEVEL':
            p = param.strip().rstrip(',')
            return f'Lv. {p}' if p and p != '0' else 'Level Up'
        if method == 'EVO_ITEM':
            return param.replace('ITEM_','').replace('_',' ').title()
        if method == 'EVO_TRADE':           return 'Trade'
        if method == 'EVO_BATTLE_END':      return 'After Battle'
        if method == 'EVO_SPIN':            return 'Spin'
        if method == 'EVO_SCRIPT_TRIGGER':  return 'Special'
        if method == 'EVO_NONE':            return 'Form Change'
        if method == 'EVO_SPLIT_FROM_EVO':  return 'Shed'
        if method == 'EVO_LEVEL_BATTLE_ONLY': return 'In Battle'
        return method.replace('EVO_','').replace('_',' ').title()

    # ── Parse all gen files ───────────────────────────────────────────────────
    # Regex to capture the full content of EVOLUTION(...)
    # Uses a simple approach: match everything up to the closing paren of EVOLUTION
    PAT_EVO_FULL = re.compile(
        r'\.evolutions\s*=\s*EVOLUTION\s*\((.+?)\)\s*[,;]',
        re.DOTALL
    )
    for path in GEN_FILES.values():
        if not os.path.isfile(path):
            continue
        raw  = open(path, 'r', encoding='utf-8', errors='replace').read()
        text, _ = preprocess(raw)
        for block_m in PAT_BLOCK.finditer(text):
            species_key = block_m.group(1)   # e.g. 'BULBASAUR'
            blk         = block_m.group(2)
            evo_m = PAT_EVO_FULL.search(blk)
            if not evo_m:
                continue
            evo_content = evo_m.group(1)
            evo_entries = _parse_evo_entries(evo_content)
            parsed = []
            for entry_raw in evo_entries:
                # Strip outer { }
                inner = entry_raw.strip()
                if inner.startswith('{') and inner.endswith('}'):
                    inner = inner[1:-1].strip()
                parts = _split_top_level_commas(inner)
                if len(parts) < 3:
                    continue
                method = parts[0].strip()
                param  = parts[1].strip()
                target_raw = parts[2].strip()
                target = target_raw[8:] if target_raw.startswith('SPECIES_') else target_raw

                conditions = []
                if len(parts) > 3:
                    cond_raw = ', '.join(parts[3:])
                    conditions = _parse_conditions(cond_raw)

                parsed.append({
                    'method':     method,
                    'param':      param,
                    'label':      _method_label(method, param),
                    'target':     target,
                    'conditions': conditions,
                })
                backward.setdefault(target, species_key)

            if parsed:
                forward[species_key] = parsed

    _cache['_evo_chains'] = (forward, backward)
    return forward, backward


def get_evo_stage(key, can_evolve, has_pre_evo):
    c, h = key in can_evolve, key in has_pre_evo
    if   c and not h: return "BASIC"
    elif c and h:     return "MIDDLE"
    elif not c and h: return "FINAL"
    else:             return "SINGLE"

# ══════════════════════════════════════════════════════════════════════════════
# POKEMON LOADING  (cached)
# ══════════════════════════════════════════════════════════════════════════════
def load_all_pokemon():
    if 'all_pokemon' in _cache: return _cache['all_pokemon']
    can_evolve, has_pre_evo = build_evo_graph()
    results = []
    for gen, path in GEN_FILES.items():
        if not os.path.isfile(path): continue
        raw  = open(path, 'r', encoding='utf-8', errors='replace').read()
        text, macros = preprocess(raw)
        # Collect family-type macros e.g. #define CLEFAIRY_FAMILY_TYPES { TYPE_FAIRY, TYPE_FAIRY }
        # (resolved from preprocessed text so conditional branches are already resolved)
        _type_macros = {}
        for _tm in PAT_TYPE_MACRO.finditer(text):
            _t1m = _strip_type(_tm.group(2))
            _t2m = _strip_type(_tm.group(3)) if _tm.group(3) else ''
            if _t2m == _t1m: _t2m = ''
            _type_macros[_tm.group(1)] = (_t1m, _t2m)
        for m in PAT_BLOCK.finditer(text):
            key, blk = m.group(1), m.group(2)
            fields = {f.group(1): f.group(2).strip() for f in PAT_FIELD.finditer(blk)}
            hp  = _int_v(fields.get('baseHP'),        macros)
            atk = _int_v(fields.get('baseAttack'),    macros)
            df  = _int_v(fields.get('baseDefense'),   macros)
            spa = _int_v(fields.get('baseSpAttack'),  macros)
            spd = _int_v(fields.get('baseSpDefense'), macros)
            spe = _int_v(fields.get('baseSpeed'),     macros)
            if hp == 0 and atk == 0: continue
            nm   = PAT_NAME.search(blk)
            name = nm.group(1) if nm else key.replace('_',' ').title()
            desc_m = re.search(r'\.description\s*=\s*COMPOUND_STRING\s*\((.*?)\)', blk, re.DOTALL)
            description = ''
            if desc_m:
                parts = re.findall(r'"([^"]*)"', desc_m.group(1))
                description = ' '.join(p.replace('\\n',' ') for p in parts).strip()
            cat_m = re.search(r'\.categoryName\s*=\s*_\("([^"]+)"\)', blk)
            category = cat_m.group(1) if cat_m else ''
            ht_m = re.search(r'\.height\s*=\s*(\d+)', blk)
            wt_m = re.search(r'\.weight\s*=\s*(\d+)', blk)
            height = int(ht_m.group(1)) if ht_m else 0
            weight = int(wt_m.group(1)) if wt_m else 0
            ab_m = re.search(r'\.abilities\s*=\s*\{([^}]+)\}', blk)
            abilities = ('', '', '')
            if ab_m:
                raw_abs = [a.strip().rstrip(',') for a in ab_m.group(1).split(',')]
                while len(raw_abs) < 3: raw_abs.append('ABILITY_NONE')
                abilities = tuple(
                    a.replace('ABILITY_','').replace('_',' ').title() if a not in ('','ABILITY_NONE') else ''
                    for a in raw_abs[:3]
                )
            cr_m = re.search(r'\.catchRate\s*=\s*(\d+)', blk)
            catch_rate = int(cr_m.group(1)) if cr_m else 0
            gr_raw = ''
            gr_m = re.search(r'\.genderRatio\s*=\s*([^\s,;]+)', blk)
            if gr_m:
                gr_raw = gr_m.group(1).strip()
            if 'MON_GENDERLESS' in gr_raw:
                gender_ratio = 255
            elif gr_raw.strip().rstrip(',') in ('MON_FEMALE', 'MON_FEMALE_ONLY'):
                gender_ratio = 254
            elif gr_raw.strip().rstrip(',') in ('MON_MALE', 'MON_MALE_ONLY'):
                gender_ratio = 0
            else:
                pf_m = re.search(r'PERCENT_FEMALE\s*\(\s*([\d.]+)\s*\)', gr_raw)
                gender_ratio = int(float(pf_m.group(1)) * 2.54 + 0.5) if pf_m else 127
            tm = PAT_TYPES.search(blk)
            if tm:
                t1 = _strip_type(tm.group(1))
                t2 = _strip_type(tm.group(2)) if tm.group(2) else ''
                if t2 == t1: t2 = ''
            else:
                # Fallback 1: brace syntax  .types = { TYPE_X, TYPE_Y }
                tb = PAT_TYPES_BRACE.search(blk)
                if tb:
                    t1 = _strip_type(tb.group(1))
                    t2 = _strip_type(tb.group(2)) if tb.group(2) else ''
                    if t2 == t1: t2 = ''
                else:
                    # Fallback 2: macro reference  .types = CLEFAIRY_FAMILY_TYPES,
                    mr = PAT_TYPES_MACRO_REF.search(blk)
                    if mr and mr.group(1) in _type_macros:
                        t1, t2 = _type_macros[mr.group(1)]
                    else:
                        t1 = t2 = ''
            form_lbl  = get_form_label(key, name)
            disp_name = f"{name} ({form_lbl})" if form_lbl else name
            results.append(Pokemon(
                key=key, name=name, gen=gen,
                type1=t1, type2=t2,
                hp=hp, atk=atk, def_=df, spa=spa, spd=spd, spe=spe,
                stage=get_evo_stage(key, can_evolve, has_pre_evo),
                legendary=_bool_f(fields,'isLegendary'),
                mythical=_bool_f(fields,'isMythical'),
                ultra_beast=_bool_f(fields,'isUltraBeast'),
                paradox=_bool_f(fields,'isParadox'),
                description=description, category=category, nat_dex=0,
                height=height, weight=weight, abilities=abilities,
                display_name=disp_name, catch_rate=catch_rate,
                gender_ratio=gender_ratio,
            ))
    _cache['all_pokemon'] = results
    return results

# ══════════════════════════════════════════════════════════════════════════════
# STATUS TRACKING  (stat_dex BUFFED/NERFED annotations)
# ══════════════════════════════════════════════════════════════════════════════
def load_status(status_file):
    if os.path.isfile(status_file):
        with open(status_file, 'r') as f:
            return json.load(f)
    return {}

def save_status(d, status_file):
    with open(status_file, 'w') as f:
        json.dump(d, f, indent=2, sort_keys=True)

def cycle_status(current):
    idx = STATUS_CYCLE.index(current) if current in STATUS_CYCLE else 0
    return STATUS_CYCLE[(idx + 1) % len(STATUS_CYCLE)]

# ══════════════════════════════════════════════════════════════════════════════
# REFERENCE DATA LOADERS
# ══════════════════════════════════════════════════════════════════════════════
def load_species():
    """List of display-name strings, excluding Mega forms."""
    if 'species' in _cache: return _cache['species']
    pat = re.compile(r'#define SPECIES_([A-Z0-9_]+)\s+\d+')
    names = []
    for m in pat.finditer(_read(SPECIES_FILE)):
        key = m.group(1)
        if key in ('NONE','EGG','UNOWN_B','UNOWN_C'): continue
        if 'MEGA' in key: continue
        names.append(key.replace('_',' ').title())
    _cache['species'] = names
    return names

def load_all_abilities():
    """Sorted list of ability display names."""
    if 'all_abilities' in _cache: return _cache['all_abilities']
    if not os.path.isfile(ABILITIES_FILE): return []
    pat = re.compile(r'#define ABILITY_([A-Z0-9_]+)\s+\d+')
    abilities = []
    for m in pat.finditer(open(ABILITIES_FILE, encoding='utf-8', errors='replace').read()):
        key = m.group(1)
        if key in ('NONE','COUNT','ILLUSION','NONE_HIDDEN'): continue
        abilities.append(key.replace('_',' ').title())
    abilities.sort()
    _cache['all_abilities'] = abilities
    return abilities

def load_ability_info():
    """Dict {name_lower: {'name':str,'desc':str}} parsed from src/data/abilities.h."""
    if '_ability_info' in _cache: return _cache['_ability_info']
    result = {}
    if not os.path.isfile(ABILITIES_DATA_FILE):
        _cache['_ability_info'] = result
        return result
    raw = open(ABILITIES_DATA_FILE, encoding='utf-8', errors='replace').read()
    pat = re.compile(r'\[ABILITY_\w+\]\s*=\s*\{([^}]+)\}', re.DOTALL)
    for m in pat.finditer(raw):
        blk = m.group(1)
        nm = re.search(r'\.name\s*=\s*_\("([^"]+)"\)', blk)
        if not nm: continue
        name = nm.group(1)
        if name == '-------': continue
        desc_m = re.search(r'\.description\s*=\s*COMPOUND_STRING\s*\((.*?)\)\s*,', blk, re.DOTALL)
        description = ''
        if desc_m:
            parts = re.findall(r'"([^"]*)"', desc_m.group(1))
            description = ' '.join(p.replace('\\n', ' ') for p in parts).strip()
        result[name.lower()] = {'name': name, 'desc': description}
    _cache['_ability_info'] = result
    return result

def _camel_to_snake(s):
    """Convert CamelCase identifier to snake_case (e.g. PokeBall → poke_ball)."""
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', s)
    s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
    return s.lower()

def _load_item_icon_map():
    """Parse src/data/items.h for .iconPic fields → {ITEM_KEY: filename}."""
    if '_item_icon_map' in _cache: return _cache['_item_icon_map']
    result = {}
    if not os.path.isfile(ITEMS_DATA_FILE):
        _cache['_item_icon_map'] = result
        return result
    current_item = None
    for line in _read(ITEMS_DATA_FILE).splitlines():
        m_item = re.match(r'\s*\[ITEM_([A-Z0-9_]+)\]', line)
        if m_item:
            current_item = 'ITEM_' + m_item.group(1)
        if current_item:
            m_icon = re.search(r'\.iconPic\s*=\s*gItemIcon_(\w+)', line)
            if m_icon:
                result[current_item] = _camel_to_snake(m_icon.group(1)) + '.png'
                current_item = None
    _cache['_item_icon_map'] = result
    return result

def load_items():
    """List of (key, display_name, icon_path).  key = ITEM_X string."""
    if 'items' in _cache: return _cache['items']
    icon_map = _load_item_icon_map()
    pat = re.compile(r'#define (ITEM_[A-Z0-9_]+)\s+(\d+)')
    result = [("","— No Item —","")]
    for m in pat.finditer(_read(ITEMS_FILE)):
        key = m.group(1)
        if key == "ITEM_NONE": continue
        display = key[5:].replace('_', ' ').title()
        # Try exact iconPic map first, then fall back to naive name
        icon_file = icon_map.get(key) or (key[5:].lower() + '.png')
        icon_path = os.path.join(ITEM_ICONS, icon_file)
        if not os.path.isfile(icon_path): icon_path = ""
        result.append((key, display, icon_path))
    _cache['items'] = result
    return result

def item_lookup(name_or_key):
    """(key, display, icon_path) for ITEM_ constant or display name.  None if not found."""
    if not name_or_key: return None
    if '_items_by_name' not in _cache:
        by_name = {}
        for tup in load_items():
            k, d, p = tup
            by_name[k.lower()] = tup
            by_name[d.lower()] = tup
        _cache['_items_by_name'] = by_name
    return _cache['_items_by_name'].get(name_or_key.strip().lower())

def load_trainer_classes():
    if 'trainer_classes' in _cache: return _cache['trainer_classes']
    pat = re.compile(r'#define TRAINER_CLASS_([A-Z0-9_]+)\s+0x[0-9a-fA-F]+')
    names = []
    for m in pat.finditer(_read(TRAINERS_CONST)):
        key = m.group(1)
        if key in ('COUNT',): continue
        names.append(key.replace('_',' ').title())
    _cache['trainer_classes'] = names
    return names

def load_trainer_pics():
    if 'trainer_pics' in _cache: return _cache['trainer_pics']
    pat = re.compile(r'#define TRAINER_PIC_([A-Z0-9_]+)\s+(\d+)')
    raw = []
    for m in pat.finditer(_read(TRAINERS_CONST)):
        key     = m.group(1)
        display = key.replace('_',' ').title()
        fname   = key.lower() + ".png"
        path    = os.path.join(TRAINER_PICS, fname)
        if not os.path.isfile(path): path = ""
        raw.append((display, path))
    if os.path.isdir(TRAINER_PICS):
        found_names = {d.lower() for d,_ in raw}
        for f in sorted(os.listdir(TRAINER_PICS)):
            if f.endswith('.png'):
                display = f[:-4].replace('_',' ').title()
                if display.lower() not in found_names:
                    raw.append((display, os.path.join(TRAINER_PICS, f)))
    _cache['trainer_pics'] = raw
    return raw

def load_moves():
    """dict: MOVE_KEY → {name, type, category, power, accuracy, pp, description}."""
    if 'moves' in _cache: return _cache['moves']
    content = _read(MOVES_FILE)
    pat = re.compile(r'\[\s*(MOVE_[A-Z0-9_]+)\s*\]\s*=\s*\{(.*?)\n\s*\},', re.DOTALL)
    result = {}
    for m in pat.finditer(content):
        key, blk = m.group(1), m.group(2)
        def g(p, default=''):
            mm = re.search(p, blk)
            return mm.group(1).strip() if mm else default
        nm     = re.search(r'\.name\s*=\s*COMPOUND_STRING\("([^"]*)"\)', blk)
        desc_m = re.search(r'\.description\s*=\s*COMPOUND_STRING\((.*?)\)\s*,', blk, re.DOTALL)
        desc = ''
        if desc_m:
            parts = re.findall(r'"([^"]*)"', desc_m.group(1))
            desc = ''.join(p.replace('\\n',' ') for p in parts)
        result[key] = {
            'name':        nm.group(1) if nm else key,
            'type':        g(r'\.type\s*=\s*([^,\n]+),'),
            'category':    g(r'\.category\s*=\s*([^,\n]+),'),
            'power':       int(g(r'\.power\s*=\s*(\d+)','0')),
            'accuracy':    int(g(r'\.accuracy\s*=\s*(\d+)','0')),
            'pp':          int(g(r'\.pp\s*=\s*(\d+)','0')),
            'description': desc,
        }
    _cache['moves'] = result
    return result

def move_lookup(name_or_key):
    """Move data dict for MOVE_ constant or display name.  {} if not found."""
    if not name_or_key: return {}
    moves = load_moves()
    if name_or_key in moves: return moves[name_or_key]
    if '_moves_by_name' not in _cache:
        by_name = {}
        for k, v in moves.items():
            name = v.get('name','')
            by_name[name.lower()] = v
            by_name[k.lower()] = v
            # Hyphen↔space variants (PS stores "Mud Slap", game has "Mud-Slap")
            if '-' in name:
                by_name[name.replace('-', ' ').lower()] = v
            if ' ' in name:
                by_name[name.replace(' ', '-').lower()] = v
        _cache['_moves_by_name'] = by_name
    return _cache['_moves_by_name'].get(name_or_key.strip().lower(), {})

def load_tmhm_moves():
    """Returns frozenset of MOVE_X constant strings that are TM or HM moves."""
    if '_tmhm_moves' in _cache: return _cache['_tmhm_moves']
    raw = _read(TMSHMHM_FILE)
    # FOREACH_TM and FOREACH_HM macros use F(MOVE_NAME) pattern
    moves = frozenset('MOVE_' + m for m in re.findall(r'F\(([A-Z0-9_]+)\)', raw))
    _cache['_tmhm_moves'] = moves
    return moves

def load_learnsets():
    """dict: species_name_lower → {levelup:[(lvl,MOVE_X)], egg:[…], tm:[…], tutor:[…]}."""
    if 'learnsets' in _cache: return _cache['learnsets']
    _blank = lambda: {'levelup':[],'egg':[],'tm':[],'tutor':[]}
    result = {}
    lu_arr = re.compile(r's([A-Za-z0-9]+)LevelUpLearnset\[\]\s*=\s*\{(.*?)\};', re.DOTALL)
    lu_mv  = re.compile(r'LEVEL_UP_MOVE\(\s*(\d+)\s*,\s*(MOVE_[A-Z0-9_]+)\s*\)')
    for gen in range(1, 10):
        path = os.path.join(LEARNSET_DIR, f"gen_{gen}.h")
        content = _read(path)
        for am in lu_arr.finditer(content):
            name  = am.group(1).lower()
            moves = [(int(l), mv) for l, mv in lu_mv.findall(am.group(2))]
            if name not in result: result[name] = _blank()
            result[name]['levelup'] = sorted(moves, key=lambda x: x[0])
    egg_arr = re.compile(r's([A-Za-z0-9]+)EggMoveLearnset\[\]\s*=\s*\{(.*?)\};', re.DOTALL)
    egg_mv  = re.compile(r'(MOVE_[A-Z0-9_]+)')
    for am in egg_arr.finditer(_read(EGG_MOVES_FILE)):
        name  = am.group(1).lower()
        moves = [mv for mv in egg_mv.findall(am.group(2)) if mv != 'MOVE_UNAVAILABLE']
        if name not in result: result[name] = _blank()
        result[name]['egg'] = moves
    teach_arr = re.compile(r's([A-Za-z0-9]+)TeachableLearnset\[\]\s*=\s*\{(.*?)\};', re.DOTALL)
    teach_mv  = re.compile(r'(MOVE_[A-Z0-9_]+)')
    tmhm = load_tmhm_moves()
    for am in teach_arr.finditer(_read(TEACHABLE_FILE)):
        name  = am.group(1).lower()
        moves = [mv for mv in teach_mv.findall(am.group(2)) if mv != 'MOVE_UNAVAILABLE']
        if name not in result: result[name] = _blank()
        result[name]['tm']    = [mv for mv in moves if mv in tmhm]
        result[name]['tutor'] = [mv for mv in moves if mv not in tmhm]
    _cache['learnsets'] = result
    return result

_GAME_TO_LS_SUFFIX = {
    'alolan': 'alola', 'galarian': 'galar',
    'hisuian': 'hisui', 'paldean': 'paldea',
}

def load_move_learners():
    """Returns {move_name_lower: [(species_display_name, learn_method), ...]} for gen 8 learnset data.
    learn_method is e.g. 'Lv.12', 'Egg', or 'TM/Tutor'.
    """
    if '_move_learners' in _cache: return _cache['_move_learners']
    learnsets = load_learnsets()
    moves     = load_moves()
    all_pkmn  = load_all_pokemon()
    # learnset key (e.g. 'bulbasaur') → display name (e.g. 'Bulbasaur')
    ls_to_display = {}
    for p in all_pkmn:
        lk = species_to_learnset_key(p.key)
        if lk not in ls_to_display:
            ls_to_display[lk] = p.display_name
    result = {}   # move_name_lower → list of (display_name, method)
    for ls_key, data in learnsets.items():
        disp = ls_to_display.get(ls_key)
        if not disp: continue
        seen = {}   # move_name_lower → method string (first encounter wins)
        for lvl, mk in data.get('levelup', []):
            mv = moves.get(mk, {})
            name = mv.get('name', mk)
            k = name.lower()
            if k not in seen: seen[k] = f"Lv.{lvl}"
        for mk in data.get('egg', []):
            mv = moves.get(mk, {})
            name = mv.get('name', mk)
            k = name.lower()
            if k not in seen: seen[k] = 'Egg'
        for mk in data.get('tm', []):
            mv = moves.get(mk, {})
            name = mv.get('name', mk)
            k = name.lower()
            if k not in seen: seen[k] = 'TM/HM'
        for mk in data.get('tutor', []):
            mv = moves.get(mk, {})
            name = mv.get('name', mk)
            k = name.lower()
            if k not in seen: seen[k] = 'Tutor'
        for k, method in seen.items():
            result.setdefault(k, []).append((disp, method))
    for k in result:
        result[k].sort(key=lambda x: x[0])
    _cache['_move_learners'] = result
    return result

def species_to_learnset_key(species_display):
    s = species_display.strip()
    if s.upper().startswith('SPECIES_'): s = s[8:]
    # Remove all non-alphanumeric chars (including underscores); lowercase
    s = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    # Map game-style suffixes (alolan) to learnset-style (alola)
    for game_suf, ls_suf in _GAME_TO_LS_SUFFIX.items():
        if s.endswith(game_suf):
            s = s[:-len(game_suf)] + ls_suf
            break
    return s

# ══════════════════════════════════════════════════════════════════════════════
# SPRITE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def find_sprite_for_key(species_key):
    """Map SPECIES_* key → (front_path, back_path). '' if not found."""
    if not os.path.isdir(SPRITES_DIR): return '', ''
    key = species_key.strip().lower()

    def _try_dir(dpath):
        front = next((os.path.join(dpath, fn)
                      for fn in ('front.png','anim_front.png')
                      if os.path.isfile(os.path.join(dpath, fn))), '')
        back  = os.path.join(dpath,'back.png') if os.path.isfile(os.path.join(dpath,'back.png')) else ''
        return (front, back) if front else None

    def _try_female(dpath):
        front = next((os.path.join(dpath, fn)
                      for fn in ('frontf.png','anim_frontf.png')
                      if os.path.isfile(os.path.join(dpath, fn))), '')
        back  = os.path.join(dpath,'backf.png') if os.path.isfile(os.path.join(dpath,'backf.png')) else ''
        return (front, back) if front else None

    direct = os.path.join(SPRITES_DIR, key)
    if os.path.isdir(direct):
        r = _try_dir(direct)
        if r: return r

    parts = key.split('_')
    for split_at in range(len(parts) - 1, 0, -1):
        base     = '_'.join(parts[:split_at])
        suffix   = '_'.join(parts[split_at:])
        base_dir = os.path.join(SPRITES_DIR, base)
        if not os.path.isdir(base_dir): continue
        normalized = _SPRITE_SUFFIX_MAP.get(suffix.upper(), suffix)
        subdir = os.path.join(base_dir, normalized)
        if os.path.isdir(subdir):
            r = _try_dir(subdir)
            if r: return r
        if suffix == 'f':
            r = _try_female(base_dir)
            if r: return r
        r = _try_dir(base_dir)
        if r: return r
        break
    return '', ''

def build_sprite_map(all_pokemon):
    """dict: key → (front_path, pal_dir). Only for Pokemon with a front sprite."""
    result = {}
    for p in all_pokemon:
        f, _ = find_sprite_for_key(p.key)
        if f: result[p.key] = (f, os.path.dirname(f))
    return result

def pokemon_sprite(species_display):
    """Return (front_path, back_path) for any species display name or SPECIES_ key."""
    raw = species_display.strip()
    if raw.upper().startswith('SPECIES_'): raw = raw[8:]
    # Normalize PS hyphen-form (Raichu-Alola) to underscore-form for find_sprite_for_key
    raw = raw.replace('-', '_')
    return find_sprite_for_key(raw)

def _parse_jasc_pal(path):
    try:
        lines = open(path,'r').read().splitlines()
        if not lines or lines[0].strip() != 'JASC-PAL': return []
        n    = int(lines[2].strip())
        cols = []
        for i in range(n):
            parts = lines[3+i].split()
            cols.append((int(parts[0]), int(parts[1]), int(parts[2])))
        return cols[1:]
    except Exception:
        return []

def make_shiny_pixmap(front_path, normal_pixmap):
    """Build shiny-palette version of normal_pixmap.  Requires PyQt5."""
    sprite_dir = os.path.dirname(front_path)
    norm_pal   = os.path.join(sprite_dir, 'normal.pal')
    shin_pal   = os.path.join(sprite_dir, 'shiny.pal')
    if not os.path.isfile(norm_pal):
        parent   = os.path.dirname(sprite_dir)
        norm_pal = os.path.join(parent, 'normal.pal')
        shin_pal = os.path.join(parent, 'shiny.pal')
    norm_colors = _parse_jasc_pal(norm_pal) if os.path.isfile(norm_pal) else []
    shin_colors = _parse_jasc_pal(shin_pal) if os.path.isfile(shin_pal) else []
    if norm_colors and shin_colors and len(norm_colors) == len(shin_colors):
        swap = {nc: sc for nc,sc in zip(norm_colors,shin_colors) if nc != sc}
        if swap:
            from PyQt5.QtGui import QImage
            img = normal_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
            for y in range(img.height()):
                for x in range(img.width()):
                    pixel = img.pixel(x, y)
                    a = (pixel >> 24) & 0xFF
                    if a < 10: continue
                    k = ((pixel >> 16)&0xFF, (pixel >> 8)&0xFF, pixel&0xFF)
                    if k in swap:
                        sr, sg, sb = swap[k]
                        img.setPixel(x, y, (a<<24)|(sr<<16)|(sg<<8)|sb)
            from PyQt5.QtGui import QPixmap as _QPix
            return _QPix.fromImage(img)
    from PyQt5.QtGui   import QPixmap as _QPix, QColor, QPainter
    from PyQt5.QtCore  import Qt
    result = _QPix(normal_pixmap.size())
    result.fill(Qt.transparent)
    p = QPainter(result)
    p.drawPixmap(0, 0, normal_pixmap)
    p.setCompositionMode(QPainter.CompositionMode_Screen)
    p.fillRect(result.rect(), QColor(255, 210, 0, 80))
    p.end()
    return result

def make_transparent_pixmap(pixmap):
    """Remove the background color from a GBA sprite or item icon QPixmap.

    GBA indexed-color images have no alpha channel; the background is a solid
    color that fills the region outside the artwork.  This function uses a
    BFS flood-fill starting from every border pixel that matches the top-left
    background sample, so only connected background pixels are removed — sprite
    pixels that happen to share the bg color (e.g. a blue item on a blue bg)
    are left intact.

    Works for any background color (grey-blue Pokemon bg, purple, pink, tan,
    teal, yellow, etc.).  Already-transparent pixmaps are returned unchanged.
    Requires PyQt5.
    """
    from PyQt5.QtGui import QImage
    from PyQt5.QtGui import QPixmap as _QPix
    from collections import deque

    img = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    if w == 0 or h == 0:
        return pixmap

    bg = img.pixel(0, 0)
    bg_a = (bg >> 24) & 0xFF
    if bg_a < 128:
        return pixmap  # already transparent

    bg_r = (bg >> 16) & 0xFF
    bg_g = (bg >> 8) & 0xFF
    bg_b = bg & 0xFF
    tol = 20  # covers GBA 5-bit palette rounding (step ≈ 8) plus minor conversion noise

    def _matches(px):
        return (abs(((px >> 16) & 0xFF) - bg_r) <= tol and
                abs(((px >> 8)  & 0xFF) - bg_g) <= tol and
                abs((px         & 0xFF) - bg_b) <= tol)

    # BFS: seed every border pixel that matches the background
    visited = bytearray(w * h)  # flat bool array, faster than list-of-lists
    queue = deque()

    def _try_seed(x, y):
        idx = y * w + x
        if not visited[idx] and _matches(img.pixel(x, y)):
            visited[idx] = 1
            queue.append((x, y))

    for x in range(w):
        _try_seed(x, 0)
        _try_seed(x, h - 1)
    for y in range(1, h - 1):
        _try_seed(0, y)
        _try_seed(w - 1, y)

    while queue:
        x, y = queue.popleft()
        img.setPixel(x, y, 0)  # make fully transparent
        for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if 0 <= nx < w and 0 <= ny < h:
                idx = ny * w + nx
                if not visited[idx] and _matches(img.pixel(nx, ny)):
                    visited[idx] = 1
                    queue.append((nx, ny))

    return _QPix.fromImage(img)

# ══════════════════════════════════════════════════════════════════════════════
# TRAINERS.PARTY I/O
# ══════════════════════════════════════════════════════════════════════════════
_PAT_IV = re.compile(r'(\d+)\s+(HP|Atk|Def|SpA|SpD|Spe)')
_IV_IDX = {'HP':0,'Atk':1,'Def':2,'SpA':3,'SpD':4,'Spe':5}


def _parse_species_line(line):
    line = line.strip()
    nickname = ''; species = ''; gender = ''; held_item = ''
    if ' @ ' in line:
        line, held_item = line.rsplit(' @ ', 1)
        held_item = held_item.strip()
    m_gender = re.search(r'\s+\(([MF])\)\s*$', line)
    if m_gender:
        gender = 'Male' if m_gender.group(1) == 'M' else 'Female'
        line   = line[:m_gender.start()].strip()
    m_nick = re.match(r'^(.+?)\s+\(([^)]+)\)\s*$', line)
    if m_nick:
        nickname = m_nick.group(1).strip()
        species  = m_nick.group(2).strip()
    else:
        species = line.strip()
    return nickname, species, gender, held_item


def _parse_mon_block(lines):
    if not lines: return None
    mon = TrainerMon()
    mon.nickname, mon.species, mon.gender, mon.held_item = _parse_species_line(lines[0])
    for line in lines[1:]:
        line = line.strip()
        if not line: continue
        if line.startswith('- '):
            if len(mon.moves) < 4: mon.moves.append(line[2:].strip())
            continue
        if ':' not in line: continue
        key, _, val = line.partition(':')
        key = key.strip(); val = val.strip(); kl = key.lower()
        if   kl == 'level':    mon.level   = int(val) if val.isdigit() else mon.level
        elif kl == 'ability':  mon.ability = val
        elif kl == 'nature':   mon.nature  = val
        elif kl == 'ball':     mon.ball    = val
        elif kl == 'happiness':
            try: mon.happiness = int(val)
            except: pass
        elif kl == 'shiny':    mon.shiny        = val.lower() == 'yes'
        elif kl == 'dynamax level':
            try: mon.dynamax_level = int(val)
            except: pass
        elif kl == 'gigantamax': mon.gigantamax = val.lower() == 'yes'
        elif kl == 'tera type':  mon.tera_type  = val
        elif kl == 'ivs':
            ivs = [31]*6
            for mv in _PAT_IV.finditer(val):
                idx = _IV_IDX.get(mv.group(2))
                if idx is not None:
                    try: ivs[idx] = int(mv.group(1))
                    except: pass
            mon.ivs = ivs
        elif kl == 'evs':
            evs = [0]*6
            for mv in _PAT_IV.finditer(val):
                idx = _IV_IDX.get(mv.group(2))
                if idx is not None:
                    try: evs[idx] = int(mv.group(1))
                    except: pass
            mon.evs = evs
    return mon


def _map_name_to_label(map_name):
    """Convert MAP_ROUTE101 → 'Route 101', MAP_LITTLEROOT_TOWN → 'Littleroot Town'."""
    s = map_name
    if s.startswith('MAP_'): s = s[4:]
    s = re.sub(r'([A-Z])(\d)', r'\1 \2', s)
    return s.replace('_', ' ').title()

def load_wild_encounters():
    """Returns {SPECIES_KEY: [(map_label, table_type, min_lvl, max_lvl, pct), ...]}"""
    if '_wild_encounters' in _cache: return _cache['_wild_encounters']
    result = {}
    if not os.path.isfile(WILD_ENCOUNTERS_FILE):
        _cache['_wild_encounters'] = result
        return result
    data = json.load(open(WILD_ENCOUNTERS_FILE, encoding='utf-8'))
    TABLE_LABELS = {
        'land_mons': 'Land', 'water_mons': 'Surfing', 'rock_smash_mons': 'Rock Smash',
    }
    ROD_LABELS = {'old_rod': 'Old Rod', 'good_rod': 'Good Rod', 'super_rod': 'Super Rod'}
    for group in data.get('wild_encounter_groups', []):
        field_rates = {}
        fishing_groups = {}
        for field in group.get('fields', []):
            ftype = field['type']
            field_rates[ftype] = field.get('encounter_rates', [])
            if ftype == 'fishing_mons' and 'groups' in field:
                fishing_groups = field['groups']
        for enc in group.get('encounters', []):
            map_label = _map_name_to_label(enc.get('map', ''))
            for ftype, rates in field_rates.items():
                if ftype not in enc: continue
                mons = enc[ftype].get('mons', [])
                total = sum(rates[:len(mons)]) or 1
                if ftype == 'fishing_mons':
                    for rod_key, slot_ids in fishing_groups.items():
                        rod_label = ROD_LABELS.get(rod_key, rod_key.title())
                        rod_rates = [rates[i] for i in slot_ids if i < len(rates)]
                        rod_total = sum(rod_rates) or 1
                        merged = {}
                        for idx, slot_idx in enumerate(slot_ids):
                            if slot_idx >= len(mons): continue
                            mon = mons[slot_idx]
                            sp = mon.get('species', 'SPECIES_NONE')
                            if not sp or sp == 'SPECIES_NONE': continue
                            key = sp[8:] if sp.startswith('SPECIES_') else sp
                            r = rod_rates[idx] if idx < len(rod_rates) else 0
                            if key in merged:
                                merged[key]['pct'] += r
                                merged[key]['min_l'] = min(merged[key]['min_l'], mon['min_level'])
                                merged[key]['max_l'] = max(merged[key]['max_l'], mon['max_level'])
                            else:
                                merged[key] = {'pct': r, 'min_l': mon['min_level'], 'max_l': mon['max_level']}
                        for key, d in merged.items():
                            pct = round(d['pct'] * 100 / rod_total)
                            result.setdefault(key, []).append((map_label, rod_label, d['min_l'], d['max_l'], pct))
                else:
                    table_label = TABLE_LABELS.get(ftype, ftype.replace('_', ' ').title())
                    merged = {}
                    for idx, mon in enumerate(mons):
                        sp = mon.get('species', 'SPECIES_NONE')
                        if not sp or sp == 'SPECIES_NONE': continue
                        key = sp[8:] if sp.startswith('SPECIES_') else sp
                        r = rates[idx] if idx < len(rates) else 0
                        if key in merged:
                            merged[key]['pct'] += r
                            merged[key]['min_l'] = min(merged[key]['min_l'], mon['min_level'])
                            merged[key]['max_l'] = max(merged[key]['max_l'], mon['max_level'])
                        else:
                            merged[key] = {'pct': r, 'min_l': mon['min_level'], 'max_l': mon['max_level']}
                    for key, d in merged.items():
                        pct = round(d['pct'] * 100 / total)
                        result.setdefault(key, []).append((map_label, table_label, d['min_l'], d['max_l'], pct))
    for key in result:
        result[key].sort(key=lambda x: (x[0], x[1]))
    _cache['_wild_encounters'] = result
    return result


def load_map_encounters():
    """Returns per-map encounter tables for the Fateful Encounter navigator.

    Structure:
        {
          "MAP_ROUTE101": {
            "land_mons":  {"encounter_rate": 20, "mons": [{"species": "SPECIES_RATTATA",
                            "min_level": 3, "max_level": 4, "rate": 20}, ...]},
            "water_mons": {...},
            "rock_smash_mons": {...},
            "fishing_mons": {
                "old_rod":   [{"species":..., "min_level":..., "max_level":..., "rate":...}, ...],
                "good_rod":  [...],
                "super_rod": [...],
            },
          },
          ...
        }
    Each mon entry has a "rate" (raw rate value) and "pct" (percentage within the table).
    """
    if '_map_encounters' in _cache:
        return _cache['_map_encounters']
    result = {}
    if not os.path.isfile(WILD_ENCOUNTERS_FILE):
        _cache['_map_encounters'] = result
        return result
    data = json.load(open(WILD_ENCOUNTERS_FILE, encoding='utf-8'))
    for group in data.get('wild_encounter_groups', []):
        field_rates   = {}
        fishing_groups = {}
        for field in group.get('fields', []):
            ftype = field['type']
            field_rates[ftype] = field.get('encounter_rates', [])
            if ftype == 'fishing_mons' and 'groups' in field:
                fishing_groups = field['groups']
        for enc in group.get('encounters', []):
            map_key = enc.get('map', '')
            if not map_key:
                continue
            entry = result.setdefault(map_key, {})
            for ftype, rates in field_rates.items():
                if ftype not in enc:
                    continue
                raw_mons = enc[ftype].get('mons', [])
                enc_rate = enc[ftype].get('encounter_rate', 0)
                if ftype == 'fishing_mons':
                    fish_tables = entry.setdefault('fishing_mons', {})
                    for rod_key, slot_ids in fishing_groups.items():
                        rod_rates = [rates[i] for i in slot_ids if i < len(rates)]
                        rod_total = sum(rod_rates) or 1
                        rod_mons  = []
                        for idx, slot_idx in enumerate(slot_ids):
                            if slot_idx >= len(raw_mons):
                                continue
                            mon = raw_mons[slot_idx]
                            sp  = mon.get('species', 'SPECIES_NONE')
                            if not sp or sp == 'SPECIES_NONE':
                                continue
                            r   = rod_rates[idx] if idx < len(rod_rates) else 0
                            pct = round(r * 100 / rod_total)
                            rod_mons.append({
                                'species':   sp,
                                'min_level': mon.get('min_level', 1),
                                'max_level': mon.get('max_level', 1),
                                'rate':      r,
                                'pct':       pct,
                            })
                        fish_tables[rod_key] = rod_mons
                else:
                    total = sum(rates[:len(raw_mons)]) or 1
                    mons  = []
                    for idx, mon in enumerate(raw_mons):
                        sp = mon.get('species', 'SPECIES_NONE')
                        if not sp or sp == 'SPECIES_NONE':
                            continue
                        r   = rates[idx] if idx < len(rates) else 0
                        pct = round(r * 100 / total)
                        mons.append({
                            'species':    sp,
                            'min_level':  mon.get('min_level', 1),
                            'max_level':  mon.get('max_level', 1),
                            'rate':       r,
                            'pct':        pct,
                        })
                    entry[ftype] = {'encounter_rate': enc_rate, 'mons': mons}
    _cache['_map_encounters'] = result
    return result


def parse_trainers_party(path=None):
    """Parse trainers.party → (header_comment, list[Trainer])."""
    path    = path or PARTY_FILE
    content = _read(path)
    comment_match  = re.match(r'\s*/\*.*?\*/\s*', content, re.DOTALL)
    header_comment = content[:comment_match.end()] if comment_match else ""
    trainers = []
    splits = list(re.finditer(r'^===\s+(TRAINER_\w+)\s+===\s*$', content, re.MULTILINE))
    for i, match in enumerate(splits):
        key   = match.group(1)
        start = match.end()
        end   = splits[i+1].start() if i+1 < len(splits) else len(content)
        block = content[start:end].strip()
        t = Trainer(key=key)
        lines = block.split('\n')
        header_lines = []; body_lines = []; in_header = True
        for line in lines:
            if in_header:
                if line.strip() == '' and header_lines: in_header = False
                else: header_lines.append(line)
            else:
                body_lines.append(line)
        for line in header_lines:
            if ':' not in line: continue
            hk, _, hv = line.partition(':')
            hk = hk.strip(); hv = hv.strip(); hkl = hk.lower()
            if   hkl == 'name':             t.name           = hv
            elif hkl == 'class':            t.trainer_class  = hv
            elif hkl == 'pic':              t.pic            = hv
            elif hkl == 'gender':           t.gender         = hv
            elif hkl == 'music':            t.music          = hv
            elif hkl == 'double battle':    t.double_battle  = hv.lower() == 'yes'
            elif hkl == 'ai':               t.ai_flags = [f.strip() for f in hv.split('/') if f.strip()]
            elif hkl == 'items':            t.items    = [it.strip() for it in hv.split('/') if it.strip()]
            elif hkl == 'mugshot':          t.mugshot         = hv
            elif hkl == 'starting status':  t.starting_status = hv
        mon_lines = []
        for line in body_lines:
            if line.strip() == '':
                if mon_lines:
                    mon = _parse_mon_block(mon_lines)
                    if mon and mon.species: t.party.append(mon)
                    mon_lines = []
            else:
                mon_lines.append(line)
        if mon_lines:
            mon = _parse_mon_block(mon_lines)
            if mon and mon.species: t.party.append(mon)
        trainers.append(t)
    return header_comment, trainers


def write_trainers_party(trainers, header_comment="", path=None):
    """Serialize list[Trainer] back to trainers.party format."""
    path = path or PARTY_FILE
    lines = []
    if header_comment:
        lines.append(header_comment.rstrip())
        lines.append('')
    for t in trainers:
        lines.append(f"=== {t.key} ===")
        lines.append(f"Name: {t.name}")
        lines.append(f"Class: {t.trainer_class}")
        lines.append(f"Pic: {t.pic}")
        if t.gender: lines.append(f"Gender: {t.gender}")
        if t.music:  lines.append(f"Music: {t.music}")
        lines.append(f"Double Battle: {'Yes' if t.double_battle else 'No'}")
        if t.ai_flags: lines.append(f"AI: {' / '.join(t.ai_flags)}")
        if t.items:    lines.append(f"Items: {' / '.join(t.items)}")
        if t.mugshot:  lines.append(f"Mugshot: {t.mugshot}")
        if t.starting_status: lines.append(f"Starting Status: {t.starting_status}")
        for mon in t.party:
            lines.append('')
            sp_line = mon.species
            if mon.nickname:  sp_line = f"{mon.nickname} ({mon.species})"
            if mon.gender:    sp_line += f" ({'M' if mon.gender=='Male' else 'F'})"
            if mon.held_item: sp_line += f" @ {mon.held_item}"
            lines.append(sp_line)
            lines.append(f"Level: {mon.level}")
            iv_parts = [f"{v} {STAT_NAMES[i]}" for i,v in enumerate(mon.ivs)]
            lines.append(f"IVs: {' / '.join(iv_parts)}")
            if any(v != 0 for v in mon.evs):
                ev_parts = [f"{v} {STAT_NAMES[i]}" for i,v in enumerate(mon.evs) if v]
                lines.append(f"EVs: {' / '.join(ev_parts)}")
            if mon.nature and mon.nature != 'Hardy': lines.append(f"Nature: {mon.nature}")
            if mon.ability:   lines.append(f"Ability: {mon.ability}")
            if mon.ball:      lines.append(f"Ball: {mon.ball}")
            if mon.happiness != 255: lines.append(f"Happiness: {mon.happiness}")
            if mon.shiny:     lines.append("Shiny: Yes")
            if mon.dynamax_level != 10: lines.append(f"Dynamax Level: {mon.dynamax_level}")
            if mon.gigantamax: lines.append("Gigantamax: Yes")
            if mon.tera_type:  lines.append(f"Tera Type: {mon.tera_type}")
            for move in mon.moves: lines.append(f"- {move}")
        lines.append('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def load_region_map_sections():
    """dict: MAPSEC_ID → {name, x, y, width, height} from region_map_sections.json."""
    if '_region_map_sections' in _cache: return _cache['_region_map_sections']
    result = {}
    try:
        with open(REGION_MAP_SECTIONS_FILE, encoding='utf-8') as f:
            data = json.load(f)
        for sec in data.get("map_sections", []):
            result[sec["id"]] = {k: sec[k] for k in ("name", "x", "y", "width", "height")}
    except Exception:
        pass
    _cache['_region_map_sections'] = result
    return result


def load_region_map_layout():
    """2D list[15][28] of MAPSEC_ID strings from region_map_layout.h."""
    if '_region_map_layout' in _cache: return _cache['_region_map_layout']
    result = []
    try:
        with open(REGION_MAP_LAYOUT_FILE, encoding='utf-8') as f:
            text = f.read()
        for m in re.finditer(r'\{([^}]+)\}', text):
            row = [t.strip().lstrip('{') for t in m.group(1).split(',') if t.strip()]
            if len(row) == 28:   # inner rows only; outer braces token count ≠ 28
                result.append(row)
    except Exception:
        pass
    _cache['_region_map_layout'] = result
    return result


def build_mapsec_to_maps():
    """dict: MAPSEC_ID → list[MAP_KEY], scanned from all data/maps/*/map.json.
    Outdoor maps (dir name has no '_') are inserted first in each list."""
    if '_mapsec_to_maps' in _cache: return _cache['_mapsec_to_maps']
    result = {}
    try:
        for entry in os.scandir(MAPS_DATA_DIR):
            if not entry.is_dir():
                continue
            jpath = os.path.join(entry.path, "map.json")
            if not os.path.isfile(jpath):
                continue
            try:
                with open(jpath, encoding='utf-8', errors='replace') as f:
                    data = json.load(f)
            except Exception:
                continue
            mapsec  = data.get("region_map_section", "")
            map_key = data.get("id", "")
            if mapsec and map_key:
                lst = result.setdefault(mapsec, [])
                if "_" not in entry.name:
                    lst.insert(0, map_key)
                else:
                    lst.append(map_key)
    except Exception:
        pass
    _cache['_mapsec_to_maps'] = result
    return result


def build_trainer_location_map():
    """dict: TRAINER_KEY → map_display_name (from scripts.inc trainerbattle calls)."""
    result   = {}
    maps_dir = os.path.join(ROOT, 'data/maps')
    if not os.path.isdir(maps_dir): return result
    pat = re.compile(r'trainerbattle\w*\s+(TRAINER_\w+)\s*,')
    for map_name in sorted(os.listdir(maps_dir)):
        scripts = os.path.join(maps_dir, map_name, 'scripts.inc')
        if not os.path.isfile(scripts): continue
        try:
            content = open(scripts,'r',encoding='utf-8',errors='replace').read()
        except OSError:
            continue
        display = re.sub(r'([A-Z])', r' \1', map_name).strip().replace('_',' ')
        for m in pat.finditer(content):
            key = m.group(1)
            if key not in result: result[key] = display
    return result

# ══════════════════════════════════════════════════════════════════════════════
# HIDDEN POWER + STAT MATH
# ══════════════════════════════════════════════════════════════════════════════
_HP_TYPES = ["Fighting","Flying","Poison","Ground","Rock","Bug","Ghost","Steel",
             "Fire","Water","Grass","Electric","Psychic","Ice","Dragon","Dark"]
_IV_BIT   = [0, 1, 2, 4, 5, 3]

def calc_hidden_power(ivs):
    hp, atk, df, spa, spd, spe = ivs
    bits = (hp&1)|((atk&1)<<1)|((df&1)<<2)|((spe&1)<<3)|((spa&1)<<4)|((spd&1)<<5)
    return _HP_TYPES[int(bits * 15 / 63)]

def optimal_ivs_for_hp_type(target_type):
    if target_type not in _HP_TYPES: return [31]*6
    target_idx = _HP_TYPES.index(target_type)
    best_pattern, best_ones = None, -1
    for pattern in range(64):
        if int(pattern * 15 / 63) == target_idx:
            ones = bin(pattern).count('1')
            if ones > best_ones:
                best_ones, best_pattern = ones, pattern
    if best_pattern is None: return [31]*6
    return [31 if (best_pattern >> _IV_BIT[i]) & 1 else 30 for i in range(6)]

def calc_ingame_hp(base, iv, ev, level):
    if base <= 1: return base
    return _math.floor((2*base + iv + _math.floor(ev/4)) * level / 100) + level + 10

def calc_ingame_stat(base, iv, ev, level, nature_mult):
    return _math.floor((_math.floor((2*base + iv + _math.floor(ev/4)) * level / 100) + 5) * nature_mult)

def calc_all_ingame_stats(species_key, mon_ivs, mon_evs, level, nature):
    base = get_dex_base_stats(species_key)
    if not base: return {k:0 for k in ('hp','atk','def_','spa','spd','spe')}
    ivs = (list(mon_ivs) + [31]*6)[:6]
    evs = (list(mon_evs) + [0]*6)[:6]
    boost_idx, red_idx = _NATURE_BOOST.get(nature, (0,0))
    stat_keys = ('hp','atk','def_','spa','spd','spe')
    result = {}
    for i, key in enumerate(stat_keys):
        b  = base.get(key, 0)
        iv, ev = ivs[i], evs[i]
        if key == 'hp':
            result[key] = calc_ingame_hp(b, iv, ev, level)
        else:
            if boost_idx and i == boost_idx: mult = 1.1
            elif red_idx and i == red_idx:   mult = 0.9
            else:                            mult = 1.0
            result[key] = calc_ingame_stat(b, iv, ev, level, mult)
    return result

def get_dex_base_stats(species_key):
    """Return {hp,atk,def_,spa,spd,spe,bst,name,abilities,type1,type2} for species_key."""
    if '_dex' not in _cache:
        _cache['_dex'] = {}
        for p in load_all_pokemon():
            _cache['_dex'][p.key] = {
                'hp':p.hp,'atk':p.atk,'def_':p.def_,
                'spa':p.spa,'spd':p.spd,'spe':p.spe,
                'bst':p.bst,'name':p.name,
                'abilities': p.abilities,
                'catch_rate': p.catch_rate,
                'gender_ratio': p.gender_ratio,
                'type1': p.type1.upper() if p.type1 else '',
                'type2': p.type2.upper() if p.type2 else '',
            }
    key = species_key.upper().replace(' ','_').replace('-','_')
    if key.startswith('SPECIES_'): key = key[8:]
    return _cache['_dex'].get(key)

# ══════════════════════════════════════════════════════════════════════════════
# GEN 8 TYPE CHART + TEAM ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
_TYPE_CHART = {
    "NORMAL":   {"ROCK":0.5,"GHOST":0,"STEEL":0.5},
    "FIRE":     {"FIRE":0.5,"WATER":0.5,"ROCK":0.5,"DRAGON":0.5,"GRASS":2,"ICE":2,"BUG":2,"STEEL":2},
    "WATER":    {"WATER":0.5,"GRASS":0.5,"DRAGON":0.5,"FIRE":2,"GROUND":2,"ROCK":2},
    "ELECTRIC": {"ELECTRIC":0.5,"GRASS":0.5,"DRAGON":0.5,"GROUND":0,"WATER":2,"FLYING":2},
    "GRASS":    {"FIRE":0.5,"GRASS":0.5,"POISON":0.5,"FLYING":0.5,"BUG":0.5,"DRAGON":0.5,"STEEL":0.5,
                 "WATER":2,"GROUND":2,"ROCK":2},
    "ICE":      {"WATER":0.5,"ICE":0.5,"STEEL":0.5,"GRASS":2,"GROUND":2,"FLYING":2,"DRAGON":2},
    "FIGHTING": {"GHOST":0,"BUG":0.5,"PSYCHIC":0.5,"FAIRY":0.5,"POISON":0.5,"FLYING":0.5,
                 "NORMAL":2,"ICE":2,"ROCK":2,"DARK":2,"STEEL":2},
    "POISON":   {"POISON":0.5,"GROUND":0.5,"ROCK":0.5,"GHOST":0.5,"STEEL":0,"GRASS":2,"FAIRY":2},
    "GROUND":   {"GRASS":0.5,"BUG":0.5,"FLYING":0,"FIRE":2,"ELECTRIC":2,"POISON":2,"ROCK":2,"STEEL":2},
    "FLYING":   {"ELECTRIC":0.5,"ROCK":0.5,"STEEL":0.5,"GRASS":2,"FIGHTING":2,"BUG":2},
    "PSYCHIC":  {"PSYCHIC":0.5,"STEEL":0.5,"DARK":0,"FIGHTING":2,"POISON":2},
    "BUG":      {"FIRE":0.5,"FIGHTING":0.5,"FLYING":0.5,"GHOST":0.5,"STEEL":0.5,"FAIRY":0.5,
                 "GRASS":2,"PSYCHIC":2,"DARK":2},
    "ROCK":     {"FIGHTING":0.5,"GROUND":0.5,"STEEL":0.5,"FIRE":2,"ICE":2,"FLYING":2,"BUG":2},
    "GHOST":    {"NORMAL":0,"DARK":0.5,"GHOST":2,"PSYCHIC":2},
    "DRAGON":   {"STEEL":0.5,"FAIRY":0,"DRAGON":2},
    "DARK":     {"FIGHTING":0.5,"DARK":0.5,"FAIRY":0.5,"GHOST":2,"PSYCHIC":2},
    "STEEL":    {"FIRE":0.5,"WATER":0.5,"ELECTRIC":0.5,"STEEL":0.5,"ICE":2,"ROCK":2,"FAIRY":2},
    "FAIRY":    {"FIRE":0.5,"POISON":0.5,"STEEL":0.5,"FIGHTING":2,"DRAGON":2,"DARK":2},
}
_ABILITY_IMMUNITIES = {
    "levitate":         {"GROUND":0},
    "volt absorb":      {"ELECTRIC":0},
    "lightning rod":    {"ELECTRIC":0},
    "motor drive":      {"ELECTRIC":0},
    "electromorphosis": {"ELECTRIC":0},
    "water absorb":     {"WATER":0},
    "storm drain":      {"WATER":0},
    "dry skin":         {"WATER":0},
    "flash fire":       {"FIRE":0},
    "sap sipper":       {"GRASS":0},
    "earth eater":      {"GROUND":0},
    "well-baked body":  {"FIRE":0},
    "purifying salt":   {"GHOST":0},
    "thick fat":        {"FIRE":0.5,"ICE":0.5},
    "heatproof":        {"FIRE":0.5},
    "water bubble":     {"FIRE":0.5},
}

def _mon_type_effectiveness(atk_type, type1, type2, ability):
    chart = _TYPE_CHART.get(atk_type, {})
    m1   = chart.get(type1, 1.0) if type1 else 1.0
    m2   = chart.get(type2, 1.0) if type2 else 1.0
    mult = m1 * m2
    if ability and ability.lower() == "wonder guard":
        return mult if mult > 1 else 0
    ab_key = ability.lower() if ability else ""
    if ab_key in _ABILITY_IMMUNITIES:
        override = _ABILITY_IMMUNITIES[ab_key]
        if atk_type in override:
            mult *= override[atk_type]
    return mult

def calc_team_type_profile(party):
    """dict: atk_type → {4x,2x,neutral,half,quarter,immune counts for each team member}."""
    result = {}
    for atk in ALL_TYPES:
        mons_mults = []
        for mon in party:
            if not mon or not mon.species: continue
            base = get_dex_base_stats(mon.species)
            if not base: continue
            t1   = base.get('type1','')
            t2   = base.get('type2','')
            ab   = mon.ability or ((base.get('abilities',()) or ('',))[0])
            mons_mults.append(_mon_type_effectiveness(atk, t1, t2, ab))
        tally = {'mons':mons_mults,'4x':0,'2x':0,'neutral':0,'half':0,'quarter':0,'immune':0}
        for m in mons_mults:
            if   m == 0:      tally['immune']  += 1
            elif m <= 0.25:   tally['quarter'] += 1
            elif m < 1:       tally['half']    += 1
            elif m < 2:       tally['neutral'] += 1
            elif m < 4:       tally['2x']      += 1
            else:             tally['4x']      += 1
        result[atk] = tally
    return result

# ══════════════════════════════════════════════════════════════════════════════
# MEGA EVOLUTION
# ══════════════════════════════════════════════════════════════════════════════
MEGA_STONE_TO_SPECIES = {
    "venusaurite":"VENUSAUR_MEGA","charizardite x":"CHARIZARD_MEGA_X",
    "charizardite y":"CHARIZARD_MEGA_Y","blastoisinite":"BLASTOISE_MEGA",
    "beedrillite":"BEEDRILL_MEGA","pidgeotite":"PIDGEOT_MEGA",
    "alakazite":"ALAKAZAM_MEGA","slowbronite":"SLOWBRO_MEGA",
    "gengarite":"GENGAR_MEGA","kangaskhanite":"KANGASKHAN_MEGA",
    "pinsirite":"PINSIR_MEGA","gyaradosite":"GYARADOS_MEGA",
    "aerodactylite":"AERODACTYL_MEGA","mewtwonite x":"MEWTWO_MEGA_X",
    "mewtwonite y":"MEWTWO_MEGA_Y","ampharosite":"AMPHAROS_MEGA",
    "steelixite":"STEELIX_MEGA","scizorite":"SCIZOR_MEGA",
    "heracronite":"HERACROSS_MEGA","houndoominite":"HOUNDOOM_MEGA",
    "tyranitarite":"TYRANITAR_MEGA","sceptilite":"SCEPTILE_MEGA",
    "blazikenite":"BLAZIKEN_MEGA","swampertite":"SWAMPERT_MEGA",
    "gardevoirite":"GARDEVOIR_MEGA","sablenite":"SABLEYE_MEGA",
    "mawilite":"MAWILE_MEGA","aggronite":"AGGRON_MEGA",
    "medichamite":"MEDICHAM_MEGA","manectite":"MANECTRIC_MEGA",
    "sharpedonite":"SHARPEDO_MEGA","cameruptite":"CAMERUPT_MEGA",
    "altarianite":"ALTARIA_MEGA","banettite":"BANETTE_MEGA",
    "absolite":"ABSOL_MEGA","glalitite":"GLALIE_MEGA",
    "salamencite":"SALAMENCE_MEGA","metagrossite":"METAGROSS_MEGA",
    "latiasite":"LATIAS_MEGA","latiosite":"LATIOS_MEGA",
    "lopunnite":"LOPUNNY_MEGA","garchompite":"GARCHOMP_MEGA",
    "lucarionite":"LUCARIO_MEGA","abomasite":"ABOMASNOW_MEGA",
    "galladite":"GALLADE_MEGA","audinite":"AUDINO_MEGA",
    "diancite":"DIANCIE_MEGA",
}

def _get_mega_species(base_species_display, held_item):
    """Return mega species key if held_item is the correct mega stone, else ''."""
    if not held_item: return ''
    tup  = item_lookup(held_item)
    item_display = tup[1].lower() if tup else held_item.lower()
    mega_key = MEGA_STONE_TO_SPECIES.get(item_display, '')
    if not mega_key: return ''
    base_upper = base_species_display.upper().replace(' ','_')
    if mega_key.startswith(base_upper): return mega_key
    return ''

# ══════════════════════════════════════════════════════════════════════════════
# RIVAL DETECTION (ROM hack specific)
# ══════════════════════════════════════════════════════════════════════════════
_RIVAL_BASES   = {'BRENDAN','MAY','BARRY','1ST_NINJA_RIVAL'}
_RIVAL_STARTER = {
    'TREECKO': ('Grass','#78c850','Sprigatito'),
    'TORCHIC': ('Fire', '#f08030','Litten'),
    'MUDKIP':  ('Water','#6890f0','Froakie'),
}

def rival_starter_info(trainer_key):
    ku = trainer_key.upper()
    if not any(rb in ku for rb in _RIVAL_BASES): return None
    for suffix, info in _RIVAL_STARTER.items():
        if ku.endswith('_'+suffix) or ('_'+suffix+'_') in ku: return info
    return ('?','#a6adc8','?')

# ══════════════════════════════════════════════════════════════════════════════
# SHARED DARK THEME  (Catppuccin Mocha — used by all tools)
# ══════════════════════════════════════════════════════════════════════════════
DARK_STYLE = """
QMainWindow, QDialog, QWidget { background:#1e1e2e; color:#cdd6f4; font-size:13px; }
QLabel  { color:#bac2de; }
QLabel#heading { color:#89b4fa; font-weight:bold; font-size:10px;
    letter-spacing:1.5px; padding:6px 0 2px 0; }
QLabel#title   { color:#cdd6f4; font-weight:bold; font-size:15px; padding:4px 0; }
QLineEdit, QSpinBox, QComboBox, QTextEdit {
    background:#313244; border:1px solid #45475a; border-radius:6px;
    padding:5px 10px; color:#cdd6f4; min-height:28px; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus { border-color:#89b4fa; }
QSpinBox::up-button   { width:20px; background:#45475a; border:none; border-top-right-radius:6px; }
QSpinBox::down-button { width:20px; background:#45475a; border:none; border-bottom-right-radius:6px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background:#585b70; }
QComboBox::drop-down  { border:none; width:24px; }
QComboBox::down-arrow { width:10px; height:10px; }
QComboBox QAbstractItemView { background:#313244; border:1px solid #585b70;
    selection-background-color:#45475a; color:#cdd6f4; outline:none; }
QListWidget { background:#181825; border:none; color:#cdd6f4;
    alternate-background-color:#1e1e2e; }
QListWidget::item { padding:5px 10px; border-bottom:1px solid #2a2a3c; }
QListWidget::item:selected { background:#313244; }
QListWidget::item:hover    { background:#252536; }
QTableWidget { background:#181825; gridline-color:#2a2a3c;
    alternate-background-color:#1e1e2e; color:#cdd6f4;
    border:none; selection-background-color:#313244; selection-color:#cdd6f4; }
QTableWidget::item { padding:2px 6px; border:none; }
QTableWidget::item:selected { background:#313244; }
QHeaderView::section { background:#181825; color:#89b4fa; font-weight:bold; font-size:12px;
    padding:8px 6px; border:none;
    border-right:1px solid #2a2a3c; border-bottom:2px solid #45475a; }
QHeaderView::section:hover   { background:#1e1e2e; }
QHeaderView::section:pressed { background:#313244; }
QTabWidget::pane   { border:1px solid #313244; border-radius:6px; background:#1e1e2e; }
QTabBar::tab       { background:#181825; color:#6c7086; padding:8px 18px;
    border-top-left-radius:6px; border-top-right-radius:6px;
    border:1px solid #313244; margin-right:2px; }
QTabBar::tab:selected { background:#313244; color:#cdd6f4; border-bottom:2px solid #89b4fa; }
QTabBar::tab:hover    { background:#252536; color:#bac2de; }
QScrollBar:vertical   { background:#181825; width:8px;  border-radius:4px; }
QScrollBar:horizontal { background:#181825; height:8px; border-radius:4px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background:#45475a; border-radius:4px; min-height:20px; min-width:20px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background:#585b70; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
QCheckBox { spacing:8px; color:#bac2de; }
QCheckBox::indicator { width:16px; height:16px; border-radius:4px;
    border:1px solid #45475a; background:#313244; }
QCheckBox::indicator:checked { background:#89b4fa; border-color:#89b4fa; }
QPushButton { background:#313244; border:1px solid #45475a; border-radius:6px;
    padding:7px 14px; color:#cdd6f4; font-size:13px; }
QPushButton:hover   { background:#45475a; border-color:#89b4fa; }
QPushButton:pressed { background:#1e1e2e; }
QPushButton#accent  { background:#89b4fa; color:#1e1e2e; border:none; font-weight:bold; }
QPushButton#accent:hover   { background:#b4d0f8; }
QPushButton#accent:pressed { background:#6c9fd8; }
QPushButton#danger  { border-color:#f38ba8; color:#f38ba8; }
QPushButton#danger:hover { background:#2e1a1a; }
QPushButton#slot    { background:#252536; border:1px dashed #45475a; border-radius:8px;
    color:#6c7086; font-size:12px; padding:4px; }
QPushButton#slot:hover   { background:#2a2a3c; border-color:#89b4fa; }
QPushButton#slot_filled { background:#252536; border:1px solid #313244; border-radius:8px;
    color:#cdd6f4; font-size:12px; padding:4px; }
QPushButton#slot_filled:hover { background:#2e2e3e; border-color:#89b4fa; }
QGroupBox { border:1px solid #313244; border-radius:6px; margin-top:8px;
    padding-top:6px; color:#89b4fa; font-weight:bold; font-size:11px; }
QGroupBox::title { subcontrol-origin:margin; left:8px; padding:0 4px; }
QSplitter::handle           { background:#313244; }
QSplitter::handle:horizontal{ width:2px; }
QStatusBar { background:#181825; color:#585b70; font-size:12px;
    border-top:1px solid #313244; padding:3px 10px; }
QFrame#sep { background:#313244; max-height:1px; min-height:1px; }
QScrollArea { border:none; }
QProgressBar { background:#313244; border-radius:4px; border:none; }
"""
