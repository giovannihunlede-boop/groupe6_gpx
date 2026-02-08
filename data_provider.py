import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Établit la connexion à PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="patrimoine_db",
            user="postgres",
            password="Master",  # Mets le mot de passe que tu as configuré
            port="5432"
        )
        return conn
    except Exception as e:
        print(f"Erreur de connexion : {e}")
        return None


def get_patrimoines():
    """Récupère tous les patrimoines depuis la DB avec le nom de leur ville"""
    conn = get_db_connection()
    if not conn: return []

    cur = conn.cursor(cursor_factory=RealDictCursor)
    # On fait une jointure pour avoir le nom de la ville au lieu de l'ID
    query = """
        SELECT p.nom_patrimoine as nom, p.latitude as lat, p.longitude as lon, v.nom_ville as ville
        FROM patrimoines p
        JOIN villes v ON p.id_ville = v.id_ville
    """
    cur.execute(query)
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_zones_villes():
    """Récupère les polygones des villes pour le filtrage"""
    conn = get_db_connection()
    if not conn: return {}

    cur = conn.cursor()
    # On utilise ST_AsText pour récupérer le polygone en format lisible (WKT)
    cur.execute("SELECT nom_ville, ST_AsText(delimitation) FROM villes")
    rows = cur.fetchall()

    zones = {}
    for row in rows:
        nom_ville = row[0].lower()
        wkt = row[1]
        # Transformation du WKT "POLYGON((...))" en liste de tuples (lat, lon)
        # Note: Dans PostGIS, c'est souvent (Lon Lat), on inverse pour ton code
        coords_str = wkt.replace("POLYGON((", "").replace("))", "")
        coords_list = []
        for pair in coords_str.split(","):
            lon, lat = map(float, pair.strip().split())
            coords_list.append((lat, lon))
        zones[nom_ville] = coords_list

    cur.close()
    conn.close()
    return zones


def build_kml_content(patrimoines, city_name, polygon_coords):
    """Génère un fichier KML riche pour Google Earth"""
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Patrimoine de {city_name.capitalize()}</name>

    <Style id="cityPoly">
      <LineStyle><color>ff0000ff</color><width>2</width></LineStyle>
      <PolyStyle><color>400000ff</color></PolyStyle>
    </Style>

    <Style id="monumentIcon">
      <IconStyle><color>ff00ff00</color><scale>1.1</scale><Icon><href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href></Icon></IconStyle>
    </Style>

    <Placemark>
      <name>Limites de {city_name}</name>
      <styleUrl>#cityPoly</styleUrl>
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
    # 2. Ajout des points (Monuments)
    for p in patrimoines:
        kml += f'''
    <Placemark>
      <name>{p['nom']}</name>
      <description>{p.get('description', 'Aucune description')}</description>
      <styleUrl>#monumentIcon</styleUrl>
      <Point>
        <coordinates>{p['lon']},{p['lat']},0</coordinates>
      </Point>
    </Placemark>'''

    kml += '\n  </Document>\n</kml>'
    return kml