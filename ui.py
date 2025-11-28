import tkinter as tk
from tkinter import messagebox
from data_provider import get_patrimoines
from gpx_generator import choix_ville, build_gpx_content, save_gpx

def generate():
    city = entry.get()
    patrimoines = get_patrimoines()
    results = choix_ville(patrimoines, city)

    if not results:
        messagebox.showinfo("GPX", "Aucun patrimoine pour cette ville.")
        return

    content = build_gpx_content(results)
    filename = f"{city}_patrimoines.gpx"
    save_gpx(filename, content)
    fullpath = save_gpx(filename, content)
    messagebox.showinfo("GPX", f"Fichier généré dans :\n{fullpath}")


app = tk.Tk()
app.title("Générateur GPX - Groupe 6")

tk.Label(app, text="Entrez une ville :").pack()
entry = tk.Entry(app)
entry.pack()

tk.Button(app, text="Générer GPX", command=generate).pack()

app.mainloop()
