"""Скачивает вводные тексты со starwars.fandom.com и подменяет ключевые слова."""

import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "knowledge_base"
MAP_PATH = ROOT / "terms_map.json"

# Одна страница — одна сущность: персонажи, места, техника, события.
PAGES = [
    "Luke Skywalker",
    "Leia Organa",
    "Han Solo",
    "Anakin Skywalker",
    "Obi-Wan Kenobi",
    "Yoda",
    "Darth Sidious",
    "Padmé Amidala",
    "Chewbacca",
    "R2-D2",
    "C-3PO",
    "Boba Fett",
    "Lando Calrissian",
    "Rey",
    "Ben Solo",
    "Finn",
    "Poe Dameron",
    "Ahsoka Tano",
    "Mace Windu",
    "Qui-Gon Jinn",
    "Maul",
    "Grogu",
    "Tatooine",
    "Coruscant",
    "Naboo",
    "Hoth",
    "Endor",
    "Dagobah",
    "Mustafar",
    "Alderaan",
    "Kashyyyk",
    "DS-1 Orbital Battle Station",
    "Lightsaber",
    "Millennium Falcon",
    "X-wing starfighter",
    "Battle of Yavin",
    "Order 66",
    "Clone Wars",
    "Jedi Order",
    "Sith",
    "Stormtrooper",
    "Galactic Empire",
]

# Исходное название → вымышленное. Длинные фразы скрипт подменяет раньше коротких.
TERMS = {
    "Luke Skywalker": "Lir Kass",
    "Leia Skywalker Organa Solo": "Sera Venn",
    "Leia Organa": "Sera Venn",
    "Han Solo": "Jorr Kane",
    "Ben Solo": "Kael Venn",
    "Anakin Skywalker": "Talen Voss",
    "Anakin": "Talen",
    "Darth Vader": "Xarn Velgor",
    "Obi-Wan Kenobi": "Orin Kel",
    "Obi-Wan": "Orin Kel",
    "Darth Sidious": "Malrec",
    "Sheev Palpatine": "Malrec",
    "Palpatine": "Malrec",
    "Padmé Amidala Naberrie": "Mira Solen",
    "Padmé Amidala": "Mira Solen",
    "Padme Amidala": "Mira Solen",
    "Landonis Balthazar Calrissian": "Dax Renn",
    "Lando Calrissian": "Dax Renn",
    "Din Grogu": "Mip",
    "Poe Dameron": "Cass Drell",
    "Ahsoka Tano": "Sira Tahl",
    "Mace Windu": "Harun Voss",
    "Qui-Gon Jinn": "Quin Jor",
    "Qui-Gon": "Quin Jor",
    "Darth Maul": "Sarn",
    "Kylo Ren": "Lord Kael",
    "Rey Skywalker": "Nima Kass",
    "Boba Fett": "Kor Vess",
    "Jango Fett": "Tann Vess",
    "Jabba the Hutt": "Grull the Sluglord",
    "Jabba": "Grull",
    "C-3PO": "Cee-Unit",
    "R2-D2": "Pip-9",
    "Chewbacca": "Brakk",
    "Millennium Falcon": "Swift Kite",
    "X-wing starfighter": "Needlewing",
    "Alliance to Restore the Republic": "Free Circle",
    "Rebel Alliance": "Free Circle",
    "Galactic Empire": "Iron Dominion",
    "Galactic Republic": "Star Compact",
    "New Republic": "Second Compact",
    "First Order": "Pale Dominion",
    "Count Dooku": "Count Helvar",
    "General Grievous": "General Vex",
    "Jar Jar Binks": "Bim Lowl",
    "Darth Plagueis": "Mire",
    "Darth Tyranus": "Helvar",
    "Darth Bane": "Cinder",
    "Jedi Order": "Seeker Circle",
    "a Sith Lord": "an Umbra Lord",
    "the Jedi's": "the Seekers'",
    "Jedi Knights": "Seekers",
    "Jedi Masters": "Senior Seekers",
    "the Jedi": "the Seekers",
    "a Sith": "an Umbra",
    "Jedi Knight": "Seeker",
    "Jedi Master": "Senior Seeker",
    "Jedi Temple": "Seeker Hall",
    "Sith Lord": "Umbra Lord",
    "the Sith": "the Umbra",
    "Clone Wars": "Vat Wars",
    "Galactic Civil War": "Dominion War",
    "Order 66": "Edict 66",
    "Battle of Yavin": "Battle of Emberhold",
    "Battle of Endor": "Battle of Greenmoon",
    "Battle of Hoth": "Battle of Frostmere",
    "Death Star II": "Void Core II",
    "Death Star": "Void Core",
    "Star Destroyers": "Void Cruisers",
    "Star Destroyer": "Void Cruiser",
    "DS-1 Orbital Battle Station": "Void Core",
    "TIE fighter": "Dartwing",
    "TIE Fighter": "Dartwing",
    "Force-sensitive": "flux-sensitive",
    "the Force": "Synth Flux",
    "dark side": "hollow path",
    "light side": "bright path",
    "kyber crystals": "flux crystals",
    "kyber crystal": "flux crystal",
    "Knights of Ren": "Knights of Vale",
    "DS-2": "VC-2",
    "DS-1": "VC-1",
    "Lightsaber": "fluxblade",
    "lightsaber": "fluxblade",
    "Stormtrooper": "Ashguard",
    "stormtrooper": "Ashguard",
    "clone trooper": "vatguard",
    "Clone trooper": "Vatguard",
    "Star Wars": "Outer Cycle",
    "Skywalkers": "Kass line",
    "Skywalker": "Kass",
    "lightsabers": "fluxblades",
    "Lightsabers": "fluxblades",
    "Stormtroopers": "Ashguards",
    "stormtroopers": "Ashguards",
    "clone troopers": "vatguards",
    "Clone troopers": "Vatguards",
    "Padawans": "Novices",
    "X-wings": "Needlewings",
    "TIE fighters": "Dartwings",
    "droids": "mechs",
    "Droids": "Mechs",
    "blasters": "sparklocks",
    "Dooku": "Helvar",
    "Grievous": "Vex",
    "Plagueis": "Mire",
    "Tyranus": "Helvar",
    "the Resistance": "the Hidden Ring",
    "Imperial": "Dominion",
    "Organa": "Venn",
    "Amidala": "Solen",
    "Kenobi": "Kel",
    "Calrissian": "Renn",
    "Dameron": "Drell",
    "Windu": "Voss",
    "Sidious": "Malrec",
    "Vader": "Velgor",
    "Ahsoka": "Sira",
    "Grogu": "Mip",
    "Snoke": "Vorlath",
    "midi-chlorians": "flux-marks",
    "midi-chlorian": "flux-mark",
    "Tusken Raiders": "Sandfolk",
    "Tusken Raider": "Sandfolk",
    "Tusken": "Sandfolk",
    "Jawas": "Scraplings",
    "Jawa": "Scrapling",
    "Hutts": "Sluglords",
    "Hutt": "Sluglord",
    "Slave I": "Night Hook",
    "Death Watch": "Helm Watch",
    "Plo Koon": "Kel Vos",
    "See-Threepio": "Cee-Unit",
    "Artoo-Deetoo": "Pip-9",
    "Threepio": "Cee",
    "Artoo": "Pip",
    "Chewie": "Brakk",
    "Yoda": "Veym",
    "Boba": "Kor",
    "Lando": "Dax",
    "Jango": "Tann",
    "Tano": "Tahl",
    "Jinn": "Jor",
    "Han": "Jorr",
    "Bane": "Cinder",
    "Maul": "Sarn",
    "Luke": "Lir",
    "Leia": "Sera",
    "Rey": "Nima",
    "Finn": "Toren",
    "Solo": "Kane",
    "Fett": "Vess",
    "Darth": "Lord",
    "Jedi": "Seeker",
    "Sith": "Umbra",
    "Padawan": "Novice",
    "padawan": "novice",
    "Wookiees": "Mossbacks",
    "Wookiee": "Mossback",
    "Ewoks": "Smallfolk",
    "Ewok": "Smallfolk",
    "Mandalorian": "Helmkin",
    "Tatooine": "Dunevar",
    "Coruscant": "Highspire",
    "Naboo": "Lirien",
    "Kashyyyk": "Mossreach",
    "Dagobah": "Mirewood",
    "Mustafar": "Cindervale",
    "Alderaan": "Valoris",
    "Ahch-To": "Stillwater",
    "Kamino": "Vatwell",
    "Geonosis": "Hiverock",
    "Jakku": "Dustmere",
    "Exegol": "Blackspire",
    "Polis Massa": "Greyhaven",
    "Yavin": "Emberhold",
    "Endor": "Greenmoon",
    "Hoth": "Frostmere",
    "Empire": "Dominion",
    "Republic": "Compact",
    "Rebellion": "Uprising",
    "Force": "Synth Flux",
    "X-wing": "Needlewing",
    "hyperspace": "voidspace",
    "hyperdrive": "voiddrive",
    "blaster": "sparklock",
    "droid": "mech",
    "Droid": "Mech",
}


class Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paras = []
        self.buf = []
        self.in_p = False
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "sup"):
            self.skip += 1
        if tag == "p" and self.skip == 0:
            self.in_p = True
            self.buf = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "sup") and self.skip:
            self.skip -= 1
        if tag == "p" and self.in_p:
            text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
            if text:
                self.paras.append(text)
            self.in_p = False

    def handle_data(self, data):
        if self.in_p and self.skip == 0:
            self.buf.append(data)


SKIP_BITS = (
    "wookieepedia",
    "this article",
    "conflicting sources",
    "lucasfilm",
    "bad feeling",
    "editor discretion",
    "for other uses",
    "real-world",
    "stub",
)


def keep(paragraph):
    if len(paragraph) < 120:
        return False
    low = paragraph.lower()
    if any(bit in low for bit in SKIP_BITS):
        return False
    # Длинный перечень названий без обычного предложения — это не текст статьи.
    if paragraph.count(",") >= 8 and not any(
        word in low for word in (" was ", " were ", " is ", " are ")
    ):
        return False
    return True


def fetch(title):
    query = urllib.parse.urlencode(
        {
            "action": "parse",
            "page": title,
            "prop": "text",
            "section": "0",
            "format": "json",
            "redirects": "1",
        }
    )
    url = "https://starwars.fandom.com/api.php?" + query
    request = urllib.request.Request(url, headers={"User-Agent": "student-rag/1.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        data = json.load(response)
    parsed = data["parse"]
    return parsed["title"], parsed["pageid"], parsed["text"]["*"]


def replace_terms(text):
    items = sorted(TERMS.items(), key=lambda item: len(item[0]), reverse=True)
    for source, target in items:
        pattern = r"(?<!\w)" + re.escape(source) + r"(?!\w)"
        text = re.sub(pattern, target, text, flags=re.IGNORECASE)
    return text


def slug(name):
    cleaned = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return cleaned or "page"


def main():
    OUT.mkdir(exist_ok=True)
    seen = set()
    used_names = set()
    saved = []

    for title in PAGES:
        page_title, page_id, html = fetch(title)
        if page_id in seen:
            print(f"skip duplicate: {title} -> {page_title}")
            time.sleep(0.3)
            continue
        seen.add(page_id)

        parser = Paragraphs()
        parser.feed(html)
        paragraphs = [part for part in parser.paras if keep(part)]
        if not paragraphs:
            print(f"skip empty: {page_title}")
            time.sleep(0.3)
            continue

        body = replace_terms("\n\n".join(paragraphs))
        heading = replace_terms(page_title)
        filename = slug(heading)
        if filename in used_names:
            filename = f"{filename}-{len(used_names)}"
        used_names.add(filename)

        path = OUT / f"{filename}.md"
        path.write_text(f"# {heading}\n\n{body}\n", encoding="utf-8")
        saved.append(path.name)
        print(f"{page_title} -> {path.name} ({len(body)} chars)")
        time.sleep(0.3)

    MAP_PATH.write_text(
        json.dumps(TERMS, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"saved {len(saved)} files")


if __name__ == "__main__":
    main()
