"""
Cálculos de % de grasa corporal mediante calibrador (caliper).

Métodos implementados:
  - Jackson-Pollock 3 pliegues (hombre: pecho, abdomen, muslo)
  - Jackson-Pollock 3 pliegues (mujer: tríceps, suprailíaco, muslo)
  - Jackson-Pollock 7 pliegues (ambos sexos)

Fórmula general:
  1. Calcular densidad corporal (BD) a partir de la suma de pliegues y la edad
  2. % grasa = (495 / BD) - 450   [fórmula de Siri]

Referencias: Jackson & Pollock (1978, 1980)
"""


def _siri(body_density: float) -> float:
    """Convierte densidad corporal a % de grasa (Siri, 1956)."""
    return round((495 / body_density) - 450, 1)


def jackson_pollock_3_male(chest_mm: float, abdomen_mm: float, thigh_mm: float, age: int) -> float:
    """JP-3 para hombres. Pliegues: pecho, abdomen, muslo."""
    s = chest_mm + abdomen_mm + thigh_mm
    bd = 1.10938 - (0.0008267 * s) + (0.0000016 * s ** 2) - (0.0002574 * age)
    return _siri(bd)


def jackson_pollock_3_female(tricep_mm: float, suprailiac_mm: float, thigh_mm: float, age: int) -> float:
    """JP-3 para mujeres. Pliegues: tríceps, suprailíaco, muslo."""
    s = tricep_mm + suprailiac_mm + thigh_mm
    bd = 1.0994921 - (0.0009929 * s) + (0.0000023 * s ** 2) - (0.0001392 * age)
    return _siri(bd)


def jackson_pollock_7(
    chest_mm: float,
    midaxillary_mm: float,
    tricep_mm: float,
    subscapular_mm: float,
    abdomen_mm: float,
    suprailiac_mm: float,
    thigh_mm: float,
    age: int,
    sex: str,
) -> float:
    """JP-7 para ambos sexos."""
    s = chest_mm + midaxillary_mm + tricep_mm + subscapular_mm + abdomen_mm + suprailiac_mm + thigh_mm
    if sex == "male":
        bd = 1.112 - (0.00043499 * s) + (0.00000055 * s ** 2) - (0.00028826 * age)
    else:
        bd = 1.097 - (0.00046971 * s) + (0.00000056 * s ** 2) - (0.00012828 * age)
    return _siri(bd)


def caliper_results(fat_percent: float, weight_kg: float) -> tuple[float, float]:
    """Devuelve (masa_grasa_kg, masa_magra_kg)."""
    fat_mass = round(weight_kg * fat_percent / 100, 2)
    lean_mass = round(weight_kg - fat_mass, 2)
    return fat_mass, lean_mass


# ── Sitios de medición por método ────────────────────────────────────────────

JP3_MALE_SITES = [
    ("Pecho (pectoral)",           "chest_mm"),
    ("Abdomen (2cm del ombligo)",  "abdomen_mm"),
    ("Muslo (anterior)",           "thigh_mm"),
]

JP3_FEMALE_SITES = [
    ("Tríceps (posterior)",        "tricep_mm"),
    ("Suprailíaco (cresta ilíaca)","suprailiac_mm"),
    ("Muslo (anterior)",           "thigh_mm"),
]

JP7_SITES = [
    ("Pecho (pectoral)",           "chest_mm"),
    ("Axilar medio",               "midaxillary_mm"),
    ("Tríceps (posterior)",        "tricep_mm"),
    ("Subescapular",               "subscapular_mm"),
    ("Abdomen (2cm del ombligo)",  "abdomen_mm"),
    ("Suprailíaco (cresta ilíaca)","suprailiac_mm"),
    ("Muslo (anterior)",           "thigh_mm"),
]

