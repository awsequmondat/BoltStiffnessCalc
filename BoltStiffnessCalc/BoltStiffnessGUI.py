import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io

# Cıvata boyutları
bolt_sizes = {
    'M10': {'A_nom': 58, 'A_t': 48.5},
    'M12': {'A_nom': 84.3, 'A_t': 68.0},
}

# Wiki metnini dosyadan yükle
with open("c:/Users/DELL/Desktop/Kısayollar/Things/Projects/BoltStiffnessCalc/BoltStiffnessCalc/wiki_text.txt", "r", encoding="utf-8") as file:
    wiki_text = file.read()

def calculate_stiffness():
    bolt_size = bolt_size_var.get()
    try:
        L_shank = float(shank_length_var.get())
        L_thread = float(thread_length_var.get())
        E_bolt = float(elastic_modulus_var.get())
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numerical values.")
        return

    if bolt_size in bolt_sizes:
        A_nom = bolt_sizes[bolt_size]['A_nom']
        A_t = bolt_sizes[bolt_size]['A_t']
        
        if L_shank > 0:
            k_shank = (E_bolt * A_nom) / L_shank
        else:
            messagebox.showerror("Input Error", "Shank length must be greater than 0.")
            return
        
        if L_thread > 0:
            k_thread = (E_bolt * A_t) / L_thread
        else:
            k_thread = float('inf')
        
        k_bolt = 1 / (1/k_shank + 1/k_thread) if L_thread > 0 else k_shank
        
        result_var.set(f"Total bolt stiffness: {k_bolt:.2f} N/mm")
    else:
        messagebox.showerror("Input Error", "Invalid bolt size.")

def render_latex_to_image(latex_text):
    fig, ax = plt.subplots(figsize=(8, 1), dpi=100)
    ax.text(0.5, 0.5, f"${latex_text}$", fontsize=12, ha='center', va='center')
    ax.axis('off')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1)
    buf.seek(0)
    img = Image.open(buf)
    plt.close(fig)  # Bellek sızıntısını önlemek için figürü kapat
    return ImageTk.PhotoImage(img)

def render_wiki_text(widget, text):
    widget.config(state="normal")
    widget.delete("1.0", tk.END)
    widget.image_list = []  # Eski resimleri temizle
    
    while text:
        start = text.find('$$')
        if start == -1:
            widget.insert(tk.END, text)
            break
        widget.insert(tk.END, text[:start])
        text = text[start+2:]
        end = text.find('$$')
        if end == -1:
            widget.insert(tk.END, text)
            break
        latex_text = text[:end]
        try:
            image = render_latex_to_image(latex_text)
            widget.image_list.append(image)  # Referansı tut
            widget.image_create(tk.END, image=image)
        except Exception as e:
            widget.insert(tk.END, f"[LaTeX Hatası: {str(e)}]")
        text = text[end+2:]
    widget.config(state="disabled")

# Ana pencere
root = tk.Tk()
root.title("Bolt Stiffness Calculator")
root.geometry("600x400")

# Notebook oluştur
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')

# Calculatör sekmesi
calc_frame = ttk.Frame(notebook)
notebook.add(calc_frame, text="Calculator")

# Calculatör widget'ları
tk.Label(calc_frame, text="Bolt Size (e.g., M10):").grid(row=0, column=0, padx=10, pady=5)
bolt_size_var = tk.StringVar()
tk.Entry(calc_frame, textvariable=bolt_size_var).grid(row=0, column=1, padx=10, pady=5)

tk.Label(calc_frame, text="Shank Length (mm):").grid(row=1, column=0, padx=10, pady=5)
shank_length_var = tk.StringVar()
tk.Entry(calc_frame, textvariable=shank_length_var).grid(row=1, column=1, padx=10, pady=5)

tk.Label(calc_frame, text="Thread Length (mm):").grid(row=2, column=0, padx=10, pady=5)
thread_length_var = tk.StringVar()
tk.Entry(calc_frame, textvariable=thread_length_var).grid(row=2, column=1, padx=10, pady=5)

tk.Label(calc_frame, text="Elastic Modulus (MPa):").grid(row=3, column=0, padx=10, pady=5)
elastic_modulus_var = tk.StringVar(value="200000")
tk.Entry(calc_frame, textvariable=elastic_modulus_var).grid(row=3, column=1, padx=10, pady=5)

result_var = tk.StringVar()
tk.Label(calc_frame, textvariable=result_var).grid(row=4, column=0, columnspan=2, padx=10, pady=5)

tk.Button(calc_frame, text="Calculate", command=calculate_stiffness).grid(row=5, column=0, columnspan=2, padx=10, pady=10)

# Wiki sekmesi
wiki_frame = ttk.Frame(notebook)
notebook.add(wiki_frame, text="Wiki")

# Tek bir render edilmiş metin alanı
wiki_text_widget = tk.Text(wiki_frame, wrap="word", state="disabled")
wiki_text_widget.image_list = []  # Resim referanslarını tutmak için
wiki_text_widget.pack(fill="both", expand=True, padx=10, pady=10)

# Scrollbar for wiki_text_widget
wiki_scrollbar = ttk.Scrollbar(wiki_frame, command=wiki_text_widget.yview)
wiki_scrollbar.pack(side="right", fill="y")
wiki_text_widget.config(yscrollcommand=wiki_scrollbar.set)

# Wiki metnini render et
render_wiki_text(wiki_text_widget, wiki_text)

# Uygulamayı çalıştır
root.mainloop()