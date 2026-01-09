def get_patrimoines():
    return [
        {"nom": "Monument 1", "lat": 6.20, "lon": 1.17, "ville": "lome"},
        {"nom": "Monument 2", "lat": 6.21, "lon": 1.18, "ville": "lome"},
        {"nom": "Monument 3", "lat": 6.13, "lon": 1.25, "ville": "lome"},
        {"nom": "Monument 4", "lat": 6.50, "lon": 1.80, "ville": "lome"},  # ❌ hors zone
        {"nom": "Lac Togo", "lat": 6.23, "lon": 1.60, "ville": "aneho"},
    ]


def get_zones_villes():
    return {
        "lome": [
            (6.10, 1.10),
            (6.10, 1.35),
            (6.30, 1.35),
            (6.30, 1.10),
        ],
        "aneho": [
            (6.18, 1.45),
            (6.18, 1.70),
            (6.30, 1.70),
            (6.30, 1.45),
        ],
    }
