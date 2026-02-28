import os
import psycopg2
import csv
import io
import threading
from math import cos, asin, sqrt, pi
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from psycopg2.extras import RealDictCursor
import gpxpy
import gpxpy.gpx
import customtkinter as ctk

# --- INTEGRATION DE MES MODULES ---
from data_provider import get_patrimoines, get_zones_villes
from gpx_generator import point_in_polygon, parse_kml_data, build_kml_content, build_gpx_content

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'py_bd')

app = Flask(__name__, static_folder=TEMPLATE_DIR)  # On dit à Flask d'utiliser py_bd

CORS(app)

# --- CONFIGURATION DB ---
DB_URL = "postgresql://postgres:Master@localhost:5432/patrimoine_db"


def get_db_connection():
    try:
        # Utilise des paramètres séparés plutôt qu'une URL
        conn = psycopg2.connect(
            host="localhost",
            database="patrimoine_db",
            user="postgres",
            password="Master",
            port="5432"
        )
        conn.set_client_encoding('UTF8')  # INDISPENSABLE
        return conn
    except Exception as e:
        print(f"❌ Erreur DB : {e}")
        return None

# --- FONCTION DE CALCUL DE DISTANCE (Haversine) ---
def distance(lat1, lon1, lat2, lon2):
    p = pi / 180
    a = 0.5 - cos((lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
    return 12742 * asin(sqrt(a))  # Retourne en km


import xml.etree.ElementTree as ET

# --- API ROUTES : AUTHENTIFICATION ---

@app.route('/')
def index():
    # Envoie le fichier patrimoine.html qui est dans le dossier py_bd
    return send_from_directory(TEMPLATE_DIR, 'patrimoine.html')


# 3. On crée une route pour les fichiers CSS/JS (styles.css etc.)
@app.route('/<path:path>')
def send_static(path):
    return send_from_directory(TEMPLATE_DIR, path)


@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    # Gestion du pre-flight OPTIONS pour CORS
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    data = request.json
    print(f"Tentative de connexion : {data}")  # DEBUG : Regarde ta console Python

    if not data:
        return jsonify({"status": "error", "message": "Pas de données reçues"}), 400

    username = data.get('username')
    password = data.get('password')

    # Simulation de connexion (à adapter avec ta table users si besoin)
    # Ici on accepte Giovanni avec n'importe quel mot de passe pour le test
    if username and password:
        return jsonify({
            "status": "success",
            "user": {
                "id": 1,
                "username": username,
                "role": "admin"
            }
        }), 200

    return jsonify({"status": "error", "message": "Identifiants invalides"}), 401


# --- API ROUTES : USERS ---
@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB error"}), 500
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT id, username, email FROM users")
        users = cur.fetchall()
    except Exception:
        users = [{"id": 1, "username": "Giovanni", "email": "giovanni@gigatech.tg"}]
    finally:
        cur.close()
        conn.close()
    return jsonify({"users": users})


# --- API ROUTES : PATRIMOINES (LISTE CORRIGÉE) ---
@app.route('/api/heritages', methods=['GET'])
def list_heritages():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB error"}), 500
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # On récupère l'ID exact et on joint la ville
        cur.execute("""
            SELECT p.id_patrimoine, p.nom_patrimoine, p.latitude, p.longitude, 
                   p.description, v.nom_ville, p.id_ville
            FROM patrimoines p
            JOIN villes v ON p.id_ville = v.id_ville
            ORDER BY p.id_patrimoine DESC
        """)
        rows = cur.fetchall()

        formatted = []
        for r in rows:
            formatted.append({
                "id_patrimoine": r['id_patrimoine'],  # L'ID RÉEL DE LA BASE
                "nom_patrimoine": r['nom_patrimoine'],
                "latitude": float(r['latitude']),
                "longitude": float(r['longitude']),
                "nom_ville": r['nom_ville'],
                "id_ville": r['id_ville'],
                "description": r['description'] or ""
            })
        return jsonify({"heritages": formatted})
    except Exception as e:
        print(f"❌ Erreur list_heritages : {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/heritages', methods=['POST'])
def add_heritage():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB error"}), 500
    cur = conn.cursor()

    try:
        # On extrait toutes les infos (avec des valeurs par défaut si manquant depuis l'interface)
        nom = data['name']
        desc = data.get('description', '')
        lat = data['latitude']
        lon = data['longitude']
        type_pat = data.get('type', 'Monument')  # Nouveau champ
        id_ville = data.get('ville_id', 1)  # Nouveau champ (Lomé par défaut)

        # La nouvelle requête qui inclut le type, la ville et la géométrie générée automatiquement
        query = """
            INSERT INTO patrimoines 
            (nom_patrimoine, description, latitude, longitude, type_patrimoine, id_ville, geom) 
            VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_Point(%s, %s), 4326))
        """
        # Attention : ST_Point de PostGIS prend toujours l'ordre (Longitude, Latitude)
        cur.execute(query, (nom, desc, lat, lon, type_pat, id_ville, lon, lat))

        conn.commit()  # Validation
        return jsonify({"status": "success"}), 201

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de l'enregistrement : {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

# --- API ROUTES : DELETE (AVEC VÉRIFICATION) ---
@app.route('/api/heritages/<int:id>', methods=['DELETE'])
def delete_heritage(id):
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB error"}), 500
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM patrimoines WHERE id_patrimoine = %s", (id,))
        rows_deleted = cur.rowcount # On compte combien de lignes ont été supprimées
        conn.commit()

        if rows_deleted > 0:
            print(f"✅ Succès : ID {id} supprimé de la base.")
            return jsonify({"status": "success", "message": "Supprimé"}), 200
        else:
            print(f"⚠️ Attention : L'ID {id} n'existe pas dans la table.")
            return jsonify({"status": "error", "message": "ID introuvable"}), 404

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur suppression : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# --- API ROUTES : IMPORT (CORRIGÉE) ---
@app.route('/api/import/file', methods=['POST'])
@app.route('/api/import/gpx', methods=['POST'])
def import_file():
    if 'file' not in request.files:
        return jsonify({"error": "Fichier manquant"}), 400

    file = request.files['file']
    filename = file.filename.lower()

    from gpx_generator import point_in_polygon, parse_kml_data
    from data_provider import get_zones_villes

    points_to_process = []
    try:
        if filename.endswith('.gpx'):
            import gpxpy
            gpx_data = gpxpy.parse(file.stream)
            for wp in gpx_data.waypoints:
                points_to_process.append({
                    'name': wp.name or "Sans nom",
                    'lat': wp.latitude,
                    'lon': wp.longitude,
                    'desc': wp.description or ""
                })
        elif filename.endswith('.kml'):
            # On appelle le parser qui doit maintenant être robuste
            points_to_process = parse_kml_data(file.stream)
        else:
            return jsonify({"error": "Format non supporté (GPX/KML)"}), 400
    except Exception as e:
        return jsonify({"error": f"Erreur de lecture: {e}"}), 400

    conn = get_db_connection()
    if not conn: return jsonify({"error": "Connexion DB échouée"}), 500
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        zones = get_zones_villes()
        cur.execute("SELECT id_ville, LOWER(TRIM(nom_ville)) as nom FROM villes")
        villes_dict = {v['nom']: v['id_ville'] for v in cur.fetchall()}

        success_count = 0
        refused_points = []

        for p in points_to_process:
            id_ville_trouvee = None
            nom_ville_detectee = "Inconnue"

            # 1. Détection de la ville
            for nom_zone, poly in zones.items():
                if point_in_polygon(p['lat'], p['lon'], poly):
                    nom_ville_detectee = nom_zone.strip().capitalize()
                    break

            # 2. Vérification en base de données
            cur.execute("SELECT id_ville FROM villes WHERE LOWER(nom_ville) = LOWER(%s)", (nom_ville_detectee,))
            res_v = cur.fetchone()

            if res_v:
                id_ville_trouvee = res_v['id_ville']

                # --- 3. NETTOYAGE ET INSERTION (À l'intérieur du if res_v) ---
                # Sécurité anti-None : on s'assure d'avoir une string vide au minimum
                nom_brut = p.get('name') if p.get('name') is not None else "Sans nom"
                desc_brut = p.get('desc') if p.get('desc') is not None else "Import automatique"

                # Maintenant le .replace() ne plantera jamais
                nom_final = str(nom_brut).replace('✅', '').replace('⚠️', '').strip()
                desc_final = str(desc_brut).strip()

                try:
                    cur.execute(
                        """INSERT INTO patrimoines (nom_patrimoine, latitude, longitude, id_ville, description, geom) 
                           VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_Point(%s, %s), 4326))""",
                        (nom_final, p['lat'], p['lon'], id_ville_trouvee, desc_final, p['lon'], p['lat'])
                    )
                    success_count += 1
                except Exception as e_sql:
                    print(f"❌ Erreur SQL sur {nom_final} : {e_sql}")
            else:
                # Si la ville n'est pas trouvée, on enregistre pour le log
                refused_points.append(p.get('name', 'Inconnu'))
                print(f"🚫 Point ignoré (ville inconnue : {nom_ville_detectee}) : {p.get('name')}")

        conn.commit()

        status = "success" if success_count > 0 else "error"
        msg = f"{success_count} sites importés."
        if refused_points:
            msg += f" {len(refused_points)} refusés (Ville inconnue)."

        return jsonify({"status": status, "message": msg})

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur Import détaillée : {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/export', methods=['GET'])
def export_data():
    fmt = request.args.get('format', 'kml').lower()
    ville_id_raw = request.args.get('ville_id')

    # Vérification stricte : est-ce un ID numérique ?
    is_filtered = ville_id_raw and ville_id_raw.isdigit()

    conn = get_db_connection()
    if not conn: return "Erreur de connexion DB", 500
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. LOGIQUE DE FILTRAGE SQL
        if is_filtered:
            query = """
                SELECT p.nom_patrimoine as nom, p.latitude as lat, p.longitude as lon, 
                       v.nom_ville as ville, p.description
                FROM patrimoines p 
                JOIN villes v ON p.id_ville = v.id_ville 
                WHERE p.id_ville = %s
            """
            cur.execute(query, (int(ville_id_raw),))
        else:
            # EXPORT COMPLET (Togo)
            query = """
                SELECT p.nom_patrimoine as nom, p.latitude as lat, p.longitude as lon, 
                       v.nom_ville as ville, p.description
                FROM patrimoines p 
                JOIN villes v ON p.id_ville = v.id_ville
            """
            cur.execute(query)

        rows = cur.fetchall()
        if not rows:
            return "Aucune donnée disponible pour l'exportation", 404

        # 2. GÉNÉRATION KML (Avec ton Option A)
        if fmt == 'kml':
            from data_provider import get_zones_villes
            from gpx_generator import build_kml_content

            # Si filtré : on prend le nom de la ville et son polygone
            # Sinon : on affiche "Togo" et polygone VIDE (Option A)
            ville_nom = rows[0]['ville'] if is_filtered else "Togo"

            if is_filtered:
                zones = get_zones_villes()
                poly = zones.get(ville_nom.lower().strip(), [])
            else:
                poly = []  # Pas de rectangle rouge pour le pays complet

            content = build_kml_content(rows, ville_nom, poly)
            return Response(
                content,
                mimetype="application/vnd.google-earth.kml+xml",
                headers={"Content-disposition": f"attachment; filename=export_giga_{ville_nom.replace(' ', '_')}.kml"}
            )

        # 3. GÉNÉRATION GPX
        elif fmt == 'gpx':
            from gpx_generator import build_gpx_content
            ville_nom = rows[0]['ville'] if is_filtered else "Togo"
            content = build_gpx_content(rows, ville_nom)
            return Response(
                content,
                mimetype="application/gpx+xml",
                headers={"Content-disposition": f"attachment; filename=export_giga_{ville_nom}.gpx"}
            )

        # 4. GÉNÉRATION CSV
        else:
            import io
            import csv
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Nom', 'Latitude', 'Longitude', 'Ville', 'Description'])
            for r in rows:
                writer.writerow([r.get('nom'), r.get('lat'), r.get('lon'), r.get('ville'), r.get('description')])

            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-disposition": "attachment; filename=export_giga_complet.csv"}
            )

    except Exception as e:
        print(f"❌ Erreur critique Export : {e}")
        return f"Erreur interne : {str(e)}", 500
    finally:
        cur.close()
        conn.close()

# --- API ROUTES : EXPORT TRAJET ---
@app.route('/api/export/route', methods=['POST'])
def export_route_formatted():
    data = request.json
    coords = data.get('coords', [])
    fmt = data.get('format', 'kml').lower()

    if not coords:
        return jsonify({"error": "No coordinates"}), 400

    if fmt == 'gpx':
        gpx = gpxpy.gpx.GPX()
        gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(coords[0][0], coords[0][1], name="DÉPART"))
        gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(coords[-1][0], coords[-1][1], name="ARRIVÉE"))
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)
        for lat, lon in coords:
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon))
        return Response(gpx.to_xml(), mimetype="application/gpx+xml",
                        headers={"Content-disposition": "attachment; filename=trajet_giga.gpx"})

    elif fmt == 'kml':
        kml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
            f'<Placemark><name>DÉPART</name><Point><coordinates>{coords[0][1]},{coords[0][0]},0</coordinates></Point></Placemark>',
            f'<Placemark><name>ARRIVÉE</name><Point><coordinates>{coords[-1][1]},{coords[-1][0]},0</coordinates></Point></Placemark>',
            '<Placemark><name>Trajet</name><LineString><coordinates>'
        ]
        for lat, lon in coords:
            kml.append(f"{lon},{lat},0")
        kml.append('</coordinates></LineString></Placemark></Document></kml>')
        return Response("\n".join(kml), mimetype="application/vnd.google-earth.kml+xml",
                        headers={"Content-disposition": "attachment; filename=trajet_giga.kml"})

    return "Format non géré", 400

# --- INTERFACE SERVEUR (FENÊTRE CTK) ---
def run_server():
    app.run(port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    server_ui = ctk.CTk()
    server_ui.title("Giga Tech - Server")
    server_ui.geometry("300x150")
    ctk.CTkLabel(server_ui, text="🚀 Serveur Actif\nPort: 5000",
                 text_color="#2ecc71", font=("Arial", 16, "bold")).pack(expand=True)
    server_ui.mainloop()