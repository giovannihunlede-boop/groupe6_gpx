import os
import xml.etree.ElementTree as ET


# --- 1. LOGIQUE GÉOGRAPHIQUE (RAY CASTING) ---

def point_in_polygon(lat, lon, polygon):
    """Algorithme Ray Casting : vérifie si un point est dans une zone."""
    if not polygon: return False
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
        # On gère les clés 'lat' ou 'latitude' pour être flexible
        lat = p.get('lat') or p.get('latitude')
        lon = p.get('lon') or p.get('longitude')
        if point_in_polygon(lat, lon, polygon):
            valides.append(p)
        else:
            rejetes.append(p)
    return valides, rejetes


def calcul_centre(patrimoines, city):
    """Calcule le point moyen pour placer l'étoile au centre de la ville."""
    if not patrimoines: return None
    lats = [p.get('lat') or p.get('latitude') for p in patrimoines]
    lons = [p.get('lon') or p.get('longitude') for p in patrimoines]
    return {
        "nom": f"Centre de {city.capitalize()}",
        "lat": sum(lats) / len(lats),
        "lon": sum(lons) / len(lons),
    }


# --- 2. LECTURE / PARSING (IMPORTATION) ---

def parse_kml_data(file_stream):
    points = []
    # On définit l'espace de nom KML
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    try:
        # On remonte au début du flux au cas où
        file_stream.seek(0)
        tree = ET.parse(file_stream)
        root = tree.getroot()

        # On cherche tous les Placemarks
        for placemark in root.findall('.//kml:Placemark', ns):
            coords_node = placemark.find('.//kml:coordinates', ns)

            if coords_node is not None and coords_node.text:
                # Extraction sécurisée du nom
                name_node = placemark.find('kml:name', ns)
                raw_name = str(name_node.text).strip() if (name_node is not None and name_node.text) else "Sans nom"

                # Extraction sécurisée de la description
                desc_node = placemark.find('kml:description', ns)
                raw_desc = str(desc_node.text).strip() if (desc_node is not None and desc_node.text) else ""

                # Parsing des coordonnées (Lon, Lat, Alt)
                coord_text = coords_node.text.strip().split()
                if not coord_text: continue

                c_parts = coord_text[0].split(',')
                if len(c_parts) >= 2:
                    try:
                        points.append({
                            'name': raw_name,
                            'lat': float(c_parts[1]),
                            'lon': float(c_parts[0]),
                            'desc': raw_desc
                        })
                    except ValueError:
                        continue  # Saute le point si les coordonnées ne sont pas des nombres
    except Exception as e:
        print(f"❌ Erreur parsing KML: {e}")
    return points

# --- 3. GÉNÉRATION DE CONTENU (EXPORTATION) ---

def build_gpx_content(patrimoines, city):
    """Génère le flux XML au format GPX."""
    content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    content += '<gpx version="1.1" creator="GigaTech_Groupe6" xmlns="http://www.topografix.com/GPX/1/1">\n'

    centre = calcul_centre(patrimoines, city)
    if centre:
        content += f'''  <wpt lat="{centre['lat']}" lon="{centre['lon']}">
    <name>{centre['nom']}</name>
    <sym>Star</sym>
  </wpt>\n'''

    for p in patrimoines:
        lat = p.get('lat') or p.get('latitude')
        lon = p.get('lon') or p.get('longitude')
        nom = p.get('nom') or p.get('nom_patrimoine')
        content += f'''  <wpt lat="{lat}" lon="{lon}">
    <name>{nom}</name>
    <sym>Historic</sym>
  </wpt>\n'''
    content += '</gpx>'
    return content


def build_kml_content(patrimoines, city_name, polygon_coords):
    """Génère le KML avec styles et zones (Option A respectée)."""
    valides, rejetes = filtrer_par_zone(patrimoines, polygon_coords) if polygon_coords else (patrimoines, [])
    if polygon_coords and len(polygon_coords) > 0:
        if polygon_coords[0] != polygon_coords[-1]:
            polygon_coords.append(polygon_coords[0])

    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Patrimoine - {city_name.capitalize()}</name>
    <Style id="cityZone">
      <LineStyle><color>ff0000ff</color><width>2</width></LineStyle>
      <PolyStyle><color>400000ff</color></PolyStyle>
    </Style>
    <Style id="iconValide">
      <IconStyle><color>ff00ffff</color><scale>1.1</scale></IconStyle>
    </Style>
    <Style id="iconHorsZone">
      <IconStyle><color>ff0000ff</color><scale>0.9</scale></IconStyle>
    </Style>
'''
    if polygon_coords:
        coords_str = " ".join([f"{lon},{lat},0" for lat, lon in polygon_coords])
        kml += f'''    <Placemark>
      <name>Zone officielle de {city_name}</name>
      <styleUrl>#cityZone</styleUrl>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>{coords_str}</coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark>\n'''

    for p in valides:
        lat, lon = (p.get('lat') or p.get('latitude')), (p.get('lon') or p.get('longitude'))
        nom = p.get('nom') or p.get('nom_patrimoine')
        kml += f'''    <Placemark>
      <name>✅ {nom}</name>
      <styleUrl>#iconValide</styleUrl>
      <description>{p.get('description', 'Site patrimonial')}</description>
      <Point><coordinates>{lon},{lat},0</coordinates></Point>
    </Placemark>\n'''

    for p in rejetes:
        lat, lon = (p.get('lat') or p.get('latitude')), (p.get('lon') or p.get('longitude'))
        nom = p.get('nom') or p.get('nom_patrimoine')
        kml += f'''    <Placemark>
      <name>⚠️ {nom} (Hors zone)</name>
      <styleUrl>#iconHorsZone</styleUrl>
      <description>HORS ZONE OFFICIELLE</description>
      <Point><coordinates>{lon},{lat},0</coordinates></Point>
    </Placemark>\n'''

    kml += '  </Document>\n</kml>'
    return kml


def save_gpx(filename, content):
    """Sauvegarde le fichier dans le dossier exports."""
    output_dir = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path