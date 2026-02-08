import os


def point_in_polygon(lat, lon, polygon):
    """
    ALGORITHME RAY CASTING
    Vérifie si un point (GPS) est à l'intérieur d'une zone (Polygone).
    C'est le coeur du filtrage géographique.
    """
    inside = False
    n = len(polygon)
    j = n - 1

    for i in range(n):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[j]

        # On trace un rayon imaginaire et on compte les intersections avec les bords
        intersect = ((lon_i > lon) != (lon_j > lon)) and \
                    (lat < (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i + 1e-9) + lat_i)

        if intersect:
            inside = not inside
        j = i

    return inside


def filtrer_par_zone(patrimoines, polygon):
    """Sépare les monuments en deux listes : ceux dans la ville et les autres."""
    valides = []
    rejetes = []

    for p in patrimoines:
        if point_in_polygon(p["lat"], p["lon"], polygon):
            valides.append(p)
        else:
            rejetes.append(p)

    return valides, rejetes


def calcul_centre(patrimoines, city):
    """Calcule le point moyen (barycentre) pour placer l'étoile au centre de la ville."""
    if not patrimoines:
        return None

    latitudes = [p["lat"] for p in patrimoines]
    longitudes = [p["lon"] for p in patrimoines]

    return {
        "nom": f"Centre de {city.capitalize()}",
        "lat": sum(latitudes) / len(latitudes),
        "lon": sum(longitudes) / len(longitudes),
    }


def build_gpx_content(patrimoines, city):
    """Génère le flux XML au format GPX pour les GPS standards."""
    content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    content += '<gpx version="1.1" creator="GigaTech_Groupe6">\n'

    # 1. Marqueur du centre ville
    centre = calcul_centre(patrimoines, city)
    if centre:
        content += f'''  <wpt lat="{centre['lat']}" lon="{centre['lon']}">
    <name>{centre['nom']}</name>
    <sym>Star</sym>
    <type>CentreVille</type>
  </wpt>\n'''

    # 2. Marqueurs des monuments
    for p in patrimoines:
        content += f'''  <wpt lat="{p['lat']}" lon="{p['lon']}">
    <name>{p['nom']}</name>
    <sym>Historic</sym>
    <type>{p.get('type_patrimoine', 'Monument')}</type>
  </wpt>\n'''

    content += '</gpx>'
    return content


def build_kml_content(patrimoines, city_name, polygon_coords):
    """Génère le fichier KML pour Google Earth avec polygones et icônes."""
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Patrimoine - {city_name.capitalize()}</name>

    <Style id="cityZone">
      <LineStyle><color>ff0000ff</color><width>2</width></LineStyle>
      <PolyStyle><color>400000ff</color></PolyStyle>
    </Style>

    <Placemark>
      <name>Zone officielle de {city_name}</name>
      <styleUrl>#cityZone</styleUrl>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              {" ".join([f"{lon},{lat},0" for lat, lon in polygon_coords])}
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
'''
    # 2. Points des monuments
    for p in patrimoines:
        kml += f'''
    <Placemark>
      <name>{p['nom']}</name>
      <description>{p.get('description', '')}</description>
      <Point>
        <coordinates>{p['lon']},{p['lat']},0</coordinates>
      </Point>
    </Placemark>'''

    kml += '\n  </Document>\n</kml>'
    return kml


def save_gpx(filename, content):
    """Sauvegarde le contenu (GPX ou KML) dans le dossier exports."""
    output_dir = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(output_dir, exist_ok=True)

    full_path = os.path.join(output_dir, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return full_path