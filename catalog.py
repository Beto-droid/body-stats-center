"""Catálogo de ejercicios y alimentos comunes."""

EXERCISES: dict[str, list[str]] = {
    "🫁 Pecho": [
        "Press de banca plano", "Press de banca inclinado", "Press de banca declinado",
        "Aperturas con mancuernas", "Aperturas en polea", "Push-ups", "Dips",
    ],
    "🔙 Espalda": [
        "Dominadas", "Jalón al pecho", "Remo con barra", "Remo con mancuerna",
        "Remo en polea baja", "Peso muerto", "Pull-over",
    ],
    "🦵 Piernas": [
        "Sentadilla", "Prensa de piernas", "Curl femoral", "Extensión de cuádriceps",
        "Elevación de talones", "Estocadas", "Sentadilla búlgara", "Hip thrust",
    ],
    "💪 Hombros": [
        "Press militar", "Press Arnold", "Elevaciones laterales", "Elevaciones frontales",
        "Face pull", "Remo al mentón",
    ],
    "💪 Brazos": [
        "Curl con barra", "Curl con mancuerna", "Curl martillo", "Curl en polea",
        "Fondos en tríceps", "Extensión de tríceps", "Press francés", "Tríceps en polea",
    ],
    "🧘 Core": [
        "Plancha", "Crunch", "Crunch en polea", "Elevación de piernas",
        "Russian twist", "Rueda abdominal", "Side plank",
    ],
}

CARDIO_TYPES: list[str] = [
    "🚶 Caminata", "🏃 Carrera", "🚴 Bicicleta", "🏊 Natación",
    "⛵ Remo (máquina)", "🪂 Saltar soga", "🏔️ Elíptica", "🧗 Escaladora",
]

# Macros por 100g: (calories, protein_g, carbs_g, fat_g)
FOODS: dict[str, tuple[float, float, float, float]] = {
    # Proteínas
    "Pechuga de pollo (cocida)":   (165, 31.0,  0.0,  3.6),
    "Carne vacuna magra (cocida)": (250, 26.0,  0.0, 15.0),
    "Atún en agua (lata)":         (116, 26.0,  0.0,  0.9),
    "Salmón (cocido)":             (208, 20.0,  0.0, 13.0),
    "Huevo entero":                (155, 13.0,  1.1, 11.0),
    "Clara de huevo":              ( 52, 11.0,  0.7,  0.2),
    "Queso cottage":               ( 98, 11.0,  3.4,  4.3),
    "Yogur griego (0%)":           ( 59, 10.0,  3.6,  0.4),
    "Proteína whey (polvo)":       (380, 80.0,  7.0,  5.0),
    # Carbohidratos
    "Arroz blanco (cocido)":       (130,  2.7, 28.0,  0.3),
    "Avena (seca)":                (389, 17.0, 66.0,  7.0),
    "Pan integral":                (247, 13.0, 41.0,  4.0),
    "Papa (cocida)":               ( 87,  1.9, 20.0,  0.1),
    "Batata (cocida)":             ( 86,  1.6, 20.0,  0.1),
    "Pasta (cocida)":              (158,  6.0, 31.0,  0.9),
    "Lenteja (cocida)":            (116,  9.0, 20.0,  0.4),
    "Banana":                      ( 89,  1.1, 23.0,  0.3),
    "Manzana":                     ( 52,  0.3, 14.0,  0.2),
    # Grasas
    "Almendras":                   (579, 21.0, 22.0, 50.0),
    "Maní":                        (567, 26.0, 16.0, 49.0),
    "Palta / Aguacate":            (160,  2.0,  9.0, 15.0),
    "Aceite de oliva":             (884,  0.0,  0.0,100.0),
    # Lácteos
    "Leche entera":                ( 61,  3.2,  4.8,  3.3),
    "Leche descremada":            ( 34,  3.4,  5.0,  0.1),
    # Verduras
    "Brócoli":                     ( 34,  2.8,  7.0,  0.4),
    "Espinaca":                    ( 23,  2.9,  3.6,  0.4),
    "Zanahoria":                   ( 41,  0.9, 10.0,  0.2),
}

