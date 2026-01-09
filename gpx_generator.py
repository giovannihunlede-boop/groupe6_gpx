import os


def point_in_polygon(lat, lon, polygon):
    """Algorithme Ray Casting"""
    inside = False
    n = len(polygon)
    j = n - 1

    for i in range(n):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[j]

        intersect = ((lon_i > lon) != (lon_j > lon)) and \
                    (lat < (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i + 1e-9) + lat_i)

        if intersect:
            inside = not inside
        j = i

    return inside


def filtrer_par_zone(patrimoines, polygon):
    valides = []
    rejetes = []

    for p in patrimoines:
        if point_in_polygon(p["lat"], p["lon"], polygon):
            valides.append(p)
        else:
            rejetes.append(p)

    return valides, rejetes


def calcul_centre(patrimoines, city):
    if not patrimoines:
        return None

    latitudes = [p["lat"] for p in patrimoines]
    longitudes = [p["lon"] for p in patrimoines]

    return {
        "nom": f"Centre de {city}",
        "lat": sum(latitudes) / len(latitudes),
        "lon": sum(longitudes) / len(longitudes),
    }


def build_gpx_content(patrimoines, city):
    content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    content += '<gpx version="1.1" creator="Groupe6">\n'

    centre = calcul_centre(patrimoines, city)
    if centre:
        content += f'''  <wpt lat="{centre['lat']}" lon="{centre['lon']}">
    <name>{centre['nom']}</name>
    <sym>Star</sym>
    <type>CentreVille</type>
  </wpt>
'''

    for p in patrimoines:
        content += f'''  <wpt lat="{p['lat']}" lon="{p['lon']}">
    <name>{p['nom']}</name>
    <sym>Historic</sym>
    <type>Monument</type>
  </wpt>
'''

    content += '</gpx>'
    return content


def save_gpx(filename, content):
    output_dir = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(output_dir, exist_ok=True)

    full_path = os.path.join(output_dir, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return full_path
