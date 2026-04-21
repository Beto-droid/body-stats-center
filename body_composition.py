"""
Body composition calculations reverse-engineered from the Xiaomi Mi Scale 2 app.
Based on: https://github.com/lolouk44/xiaomi_mi_scale

Inputs  : weight (kg), impedance (ohm), height (cm), age (years), sex ("male"/"female")
"""

from dataclasses import dataclass


@dataclass
class BodyComposition:
    bmi: float
    fat_percent: float
    muscle_mass_kg: float
    bone_mass_kg: float
    water_percent: float
    visceral_fat: float
    bmr_kcal: int
    lean_mass_kg: float
    protein_percent: float


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _lean_body_mass(weight: float, impedance: int, height_cm: int, age: int, sex: str) -> float:
    """Lean Body Mass (LBM) — core of all Xiaomi calculations."""
    if sex == "male":
        lbm = (height_cm * 9.058 / 100) * (height_cm / 100)
        lbm += weight * 0.32 + 12.226
        lbm -= impedance * 0.0068
        lbm -= age * 0.0542
    else:
        lbm = (height_cm * 0.751)
        lbm += weight * 0.35
        lbm -= impedance * 0.0077
        lbm -= age * 0.1502
        lbm -= 2.962
    return lbm


def calculate_bmi(weight: float, height_cm: int) -> float:
    return round(weight / ((height_cm / 100) ** 2), 1)


def calculate_fat_percent(weight: float, impedance: int, height_cm: int, age: int, sex: str) -> float:
    lbm = _lean_body_mass(weight, impedance, height_cm, age, sex)

    if sex == "male":
        fat = (weight - lbm) / weight * 100
        if age < 30:
            fat *= 0.98
    else:
        fat = (weight - lbm) / weight * 100
        fat -= 5.8
        if age < 30:
            fat *= 0.98

    return round(_clamp(fat, 5, 75), 1)


def calculate_water_percent(weight: float, impedance: int, height_cm: int, age: int, sex: str) -> float:
    fat = calculate_fat_percent(weight, impedance, height_cm, age, sex)
    water = (100 - fat) * 0.7
    coefficient = 0.98 if sex == "female" else 1.02
    return round(_clamp(water * coefficient, 35, 75), 1)


def calculate_lean_mass(weight: float, impedance: int, height_cm: int, age: int, sex: str) -> float:
    fat = calculate_fat_percent(weight, impedance, height_cm, age, sex)
    return round(_clamp(weight * (1 - fat / 100), 0, 200), 1)


def calculate_bone_mass(weight: float, impedance: int, height_cm: int, age: int, sex: str) -> float:
    lbm = _lean_body_mass(weight, impedance, height_cm, age, sex)
    if sex == "female":
        base = 0.245691014
    else:
        base = 0.18016894
    bone = (base - (age * 0.0011 + impedance * 0.0000016)) * weight
    bone = _clamp(bone, 0.5, 8) * (height_cm / 170)
    return round(bone, 2)


def calculate_muscle_mass(weight: float, impedance: int, height_cm: int, age: int, sex: str) -> float:
    lean = calculate_lean_mass(weight, impedance, height_cm, age, sex)
    bone = calculate_bone_mass(weight, impedance, height_cm, age, sex)
    return round(_clamp(lean - bone, 10, 120), 1)


def calculate_visceral_fat(weight: float, height_cm: int, age: int, sex: str) -> float:
    if sex == "female":
        if weight > (13 - (height_cm * 0.5)) * -1:
            sub = 1.0 + weight * 0.1 - height_cm * 0.0935 + age * 0.15
        else:
            sub = 0.5 + weight * 0.1 - height_cm * 0.0402 + age * 0.07
    else:
        if weight > ((17 * height_cm) - 1000) / 140:
            sub = 1.0 + weight * 0.1 - height_cm * 0.12 + age * 0.10
        else:
            sub = 0.5 + weight * 0.1 - height_cm * 0.0602 + age * 0.08
    return round(_clamp(sub, 1, 50), 1)


def calculate_bmr(weight: float, height_cm: int, age: int, sex: str) -> int:
    if sex == "female":
        bmr = 864.6 + weight * 10.2036 - height_cm * 0.39336 - age * 6.204
    else:
        bmr = 877.8 + weight * 14.916 - height_cm * 0.726 - age * 8.976
    return round(_clamp(bmr, 500, 10000))


def calculate_protein_percent(weight: float, impedance: int, height_cm: int, age: int, sex: str) -> float:
    water = calculate_water_percent(weight, impedance, height_cm, age, sex)
    lean = calculate_lean_mass(weight, impedance, height_cm, age, sex)
    protein = (lean / weight * 100) - water
    return round(_clamp(protein, 5, 32), 1)


def calculate_body_composition(
    weight: float, impedance: int, height_cm: int, age: int, sex: str,
) -> BodyComposition:
    return BodyComposition(
        bmi=calculate_bmi(weight, height_cm),
        fat_percent=calculate_fat_percent(weight, impedance, height_cm, age, sex),
        muscle_mass_kg=calculate_muscle_mass(weight, impedance, height_cm, age, sex),
        bone_mass_kg=calculate_bone_mass(weight, impedance, height_cm, age, sex),
        water_percent=calculate_water_percent(weight, impedance, height_cm, age, sex),
        visceral_fat=calculate_visceral_fat(weight, height_cm, age, sex),
        bmr_kcal=calculate_bmr(weight, height_cm, age, sex),
        lean_mass_kg=calculate_lean_mass(weight, impedance, height_cm, age, sex),
        protein_percent=calculate_protein_percent(weight, impedance, height_cm, age, sex),
    )
