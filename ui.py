import customtkinter as ctk
from tkinter import messagebox
import os
# Importation de tes modules personnalisés
from data_provider import get_patrimoines, get_zones_villes
from gpx_generator import build_gpx_content, build_kml_content, save_gpx, filtrer_par_zone

# --- Configuration Thème ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AppGPX(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Propriétés de la Fenêtre ---
        self.title("Giga Tech GPX - Gestion du Patrimoine")
        self.geometry("500x400")  # Légèrement plus grand pour les stats
        self.resizable(False, False)

        # Centrage sur l'écran
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - 500) // 2
        y = (screen_h - 400) // 2
        self.geometry(f"+{x}+{y}")

        # --- Variables d'Animation ---
        self.colors = ["#1abc9c", "#3498db", "#9b59b6", "#e74c3c", "#f1c40f"]
        self.color_index = 0

        # --- Construction de l'Interface ---
        self.setup_ui()
        self.animate_border()

        # Raccourci Touche Entrée
        self.bind("<Return>", lambda e: self.generate())

    def setup_ui(self):
        """Initialisation des composants graphiques"""
        self.main_frame = ctk.CTkFrame(self, corner_radius=20, border_width=2)
        self.main_frame.pack(padx=30, pady=30, fill="both", expand=True)

        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Générateur GPX & KML",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(25, 5))

        self.subtitle_label = ctk.CTkLabel(
            self.main_frame,
            text="Visualisation du patrimoine togolais",
            text_color="gray"
        )
        self.subtitle_label.pack(pady=(0, 20))

        self.entry = ctk.CTkEntry(
            self.main_frame,
            placeholder_text="Entrez une ville (ex: Lome, Aneho)",
            width=300,
            height=45,
            corner_radius=10
        )
        self.entry.pack(pady=10)
        self.entry.focus()

        self.btn_generate = ctk.CTkButton(
            self.main_frame,
            text="Générer les fichiers",
            command=self.generate,
            width=240,
            height=45,
            corner_radius=10,
            font=ctk.CTkFont(weight="bold"),
            hover_color="#16a085"
        )
        self.btn_generate.pack(pady=20)

        # Label pour les statistiques (Propos 2)
        self.stats_label = ctk.CTkLabel(
            self.main_frame,
            text="Prêt pour l'extraction",
            text_color="#7f8c8d",
            font=ctk.CTkFont(size=12, slant="italic")
        )
        self.stats_label.pack(pady=10)

    def animate_border(self):
        """Animation de la bordure pour le look Giga Tech"""
        self.main_frame.configure(border_color=self.colors[self.color_index])
        self.color_index = (self.color_index + 1) % len(self.colors)
        self.after(1000, self.animate_border)

    def generate(self):
        """Logique principale de génération"""
        city = self.entry.get().strip().lower()

        if not city:
            messagebox.showwarning("Attention", "Veuillez entrer une ville.")
            return

        # Changement d'état visuel
        self.btn_generate.configure(state="disabled", text="Extraction DB...")
        self.update()

        try:
            # 1. Récupération des données depuis PostgreSQL
            patrimoines = get_patrimoines()
            zones = get_zones_villes()

            if city not in zones:
                messagebox.showerror("Erreur", f"La ville '{city}' n'existe pas en base.")
                return

            # 2. Filtrage (On ne garde que les monuments de la ville saisie)
            patrimoines_ville = [p for p in patrimoines if p["ville"].lower() == city]

            # 3. Vérification spatiale (Ray Casting)
            valides, rejetes = filtrer_par_zone(patrimoines_ville, zones[city])

            # Mise à jour des stats (Propos 2)
            stats_msg = f"Trouvé : {len(valides)} monument(s) à {city.capitalize()}."
            if rejetes:
                stats_msg += f"\n({len(rejetes)} hors zone ignorés)"
            self.stats_label.configure(text=stats_msg, text_color="#1abc9c")

            if not valides:
                messagebox.showwarning("Info", "Aucun monument trouvé dans la zone définie.")
                return

            # 4. Génération des fichiers (GPX + KML)
            gpx_content = build_gpx_content(valides, city)
            path_gpx = save_gpx(f"{city}_export.gpx", gpx_content)

            kml_content = build_kml_content(valides, city, zones[city])
            path_kml = save_gpx(f"{city}_visualisation.kml", kml_content)

            # 5. Message de succès et Ouverture (Propos 1)
            succes_msg = f"Exportation terminée !\n\nGPX : {os.path.basename(path_gpx)}\nKML : {os.path.basename(path_kml)}"
            messagebox.showinfo("Succès Giga Tech", succes_msg)

            if messagebox.askyesno("Visualisation", "Voulez-vous ouvrir le rendu dans Google Earth Pro ?"):
                os.startfile(path_kml)

        except Exception as e:
            messagebox.showerror("Erreur Système", f"Détails : {str(e)}")

        finally:
            self.btn_generate.configure(state="normal", text="Générer les fichiers")


if __name__ == "__main__":
    app = AppGPX()
    app.mainloop()