import psycopg2
from psycopg2.extras import RealDictCursor

from py_bd.config_db import DB_CONFIG
DB_URL = "postgresql://postgres:Master@localhost:5432/ton_nom_bd"

def get_db_connection():
    """Établit la connexion à PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        try:
            import os
            # On nettoie les variables d'environnement qui pourraient forcer un mauvais encodage
            os.environ['PGCLIENTENCODING'] = 'utf8'
            conn = psycopg2.connect("host=localhost dbname=patrimoine_db user=postgres password=votre_password")
            return conn
        except Exception as e2:
            print(f"Erreur de connexion persistante : {e2}")
            return None


def get_patrimoines():
    """Récupère tous les patrimoines depuis la DB avec le nom de leur ville"""
    conn = get_db_connection()
    if not conn: return []

    cur = conn.cursor(cursor_factory=RealDictCursor)
    # On fait une jointure pour avoir le nom de la ville
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

        # --- LA CORRECTION EST ICI ---
        # Si la ville n'a pas de polygone (NULL en base), on l'ignore proprement
        if wkt is None:
            print(f"⚠️ Attention : La ville '{nom_ville}' n'a pas de délimitation (polygone) en base.")
            continue

            # Transformation du WKT "POLYGON((...))" en liste de tuples (lat, lon)
        try:
            coords_str = wkt.replace("POLYGON((", "").replace("))", "")
            coords_list = []
            for pair in coords_str.split(","):
                lon, lat = map(float, pair.strip().split())
                coords_list.append((lat, lon))
            zones[nom_ville] = coords_list
        except Exception as e:
            print(f"❌ Erreur de lecture du polygone pour {nom_ville} : {e}")

    cur.close()
    conn.close()
    return zones

