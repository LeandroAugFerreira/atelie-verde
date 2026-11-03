"""Shared presentation groups derived from the registered botanical attributes."""

from .business import normalized


def plant_groups(species):
    use = normalized(species.use)
    family = normalized(species.family)
    name = normalized(species.name)
    groups = []
    for label, matches in [
        ("Cactos", "cactos" in use),
        ("Frutíferas", "frutiferas" in use or "pomar" in use),
        ("Suculentas", "suculentas" in use),
        ("Flores", "flores" in use),
        ("Folhagens", "folhagem" in use),
        ("Aromáticas e temperos", "aromaticas" in use or "horta" in use),
        ("Palmeiras", family == "arecaceae" or "palmeira" in name),
        ("Samambaias", "samambaia" in name),
        ("Trepadeiras", "trepadeira" in use or "pergolado" in use),
        ("Cercas vivas", "cerca viva" in use),
        ("Ornamentais", "ornamental" in use),
    ]:
        if matches:
            groups.append(label)
    return groups or ["Outras plantas"]
