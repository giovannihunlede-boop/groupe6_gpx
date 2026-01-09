import customtkinter as ctk
from tkinter import messagebox
from data_provider import get_patrimoines, get_zones_villes
from gpx_generator import *

# --- Thème ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AppGPX(ctk.CTk):
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

    def __init__(self):
        super().__init__()

        # --- Fenêtre ---
        self.title("GPX Generator Pro - Groupe 6")
        self.geometry("500x350")
        self.resizable(False, False)

        # Centrage
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - 500) // 2
        y = (screen_h - 350) // 2
        self.geometry(f"+{x}+{y}")

        # --- Animation ---
        self.colors = ["#1abc9c", "#3498db", "#9b59b6", "#e74c3c", "#f1c40f"]
        self.color_index = 0

        # --- UI ---
        self.setup_ui()
        self.animate_border()

        self.bind("<Return>", lambda e: self.generate())

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=20, border_width=2)
        self.main_frame.pack(padx=40, pady=40, fill="both", expand=True)

        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Génération de fichiers GPX",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title_label.pack(pady=(20, 10))

        self.subtitle_label = ctk.CTkLabel(
            self.main_frame,
            text="Entrez une ville pour afficher son patrimoine",
            text_color="gray"
        )
        self.subtitle_label.pack(pady=(0, 20))

        self.entry = ctk.CTkEntry(
            self.main_frame,
            placeholder_text="Ex : Lome, Aneho...",
            width=280,
            height=42,
            corner_radius=10
        )
        self.entry.pack(pady=10)
        self.entry.focus()

        self.btn_generate = ctk.CTkButton(
            self.main_frame,
            text="Générer le fichier GPX",
            command=self.generate,
            width=220,
            height=42,
            corner_radius=10,
            font=ctk.CTkFont(weight="bold"),
            hover_color="#16a085"
        )
        self.btn_generate.pack(pady=20)

    def animate_border(self):
        self.main_frame.configure(border_color=self.colors[self.color_index])
        self.color_index = (self.color_index + 1) % len(self.colors)
        self.after(1000, self.animate_border)

    def generate(self):
        city = self.entry.get().strip().lower()

        if not city:
            messagebox.showwarning("Attention", "Veuillez entrer une ville.")
            return

        patrimoines = get_patrimoines()
        zones = get_zones_villes()

        if city not in zones:
            messagebox.showerror(
                "Zone inconnue",
                f"La délimitation géographique de « {city} » n'est pas encore définie."
            )
            return

        self.btn_generate.configure(state="disabled", text="Traitement...")
        self.update()

        try:
            patrimoines_ville = [
                p for p in patrimoines if p["ville"].lower() == city.lower()
            ]

            valides, rejetes = filtrer_par_zone(
                patrimoines_ville,
                zones[city]
            )

            content = build_gpx_content(valides, city)
            path = save_gpx(f"{city}_patrimoines.gpx", content)

            message = f"Fichier GPX généré avec succès !\n\n{path}"

            if rejetes:
                message += (
                    f"\n\n⚠️ {len(rejetes)} point(s) ignoré(s)\n"
                    "car hors de la délimitation officielle de la ville."
                )

            messagebox.showinfo("Succès", message)

        except Exception as e:
            messagebox.showerror("Erreur", str(e))

        finally:
            self.btn_generate.configure(state="normal", text="Générer le fichier GPX")


if __name__ == "__main__":
    app = AppGPX()
    app.mainloop()
