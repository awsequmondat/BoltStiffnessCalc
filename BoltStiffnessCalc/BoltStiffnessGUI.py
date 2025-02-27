import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io
import numpy as np

# Cıvata boyutları (genişletilmiş)
bolt_sizes = {
    'M6': {'A_shank': 28.27, 'A_thread': 20.1},
    'M8': {'A_shank': 50.27, 'A_thread': 36.6},
    'M10': {'A_shank': 78.54, 'A_thread': 58.0},
    'M12': {'A_shank': 113.10, 'A_thread': 84.3},
    'M14': {'A_shank': 153.94, 'A_thread': 114.8},
    'M16': {'A_shank': 201.06, 'A_thread': 157.1},
}

# Malzeme özellikleri
materials = {
    'Steel': {'E': 200000, 'yield_strength': 800},  # E in MPa, yield_strength in MPa
    'Aluminum': {'E': 70000, 'yield_strength': 275},
    'Titanium': {'E': 110000, 'yield_strength': 800},
}

# Wiki metnini dosyadan yükle (hata durumunda boş metin kullan)
try:
    with open(r"c:\Users\DELL\Desktop\Kısayollar\Things\Projects\BoltStiffnessCalc\BoltStiffnessCalc\wiki_text.txt", "r", encoding="utf-8") as file:
        wiki_text = file.read()
except FileNotFoundError:
    wiki_text = "Wiki metni bulunamadı. Lütfen wiki_text.txt dosyasını oluşturun."

# Parça türleri
clamped_part_types = ['Washer', 'Plate', 'Cylinder']

def calculate_stiffness():
    bolt_size = bolt_size_var.get()
    try:
        L_shank = float(shank_length_var.get())
        if L_shank <= 0:
            raise ValueError("Gövde uzunluğu 0'dan büyük olmalı.")
        L_thread = float(thread_length_var.get())
        if L_thread < 0:
            raise ValueError("Dişli kısım uzunluğu negatif olamaz.")
        material = material_var.get()
        E_bolt = materials[material]['E']
        yield_strength = materials[material]['yield_strength']
        A_shank = bolt_sizes[bolt_size]['A_shank']
        A_thread = bolt_sizes[bolt_size]['A_thread']
        preload_percent = float(preload_percent_var.get())
        if not 0 <= preload_percent <= 100:
            raise ValueError("Ön yükleme yüzdesi 0-100 arasında olmalı.")
        F_preload = (preload_percent / 100) * yield_strength * A_thread
        F_ext_tensile = float(tensile_force_var.get())
        F_ext_shear = float(shear_force_var.get())
        
        # Calculate bolt stiffness
        k_shank = (E_bolt * A_shank) / L_shank
        if L_thread > 0:
            k_thread = (E_bolt * A_thread) / L_thread
            k_bolt = 1 / (1/k_shank + 1/k_thread)
        else:
            k_bolt = k_shank
        
        # Calculate clamped parts stiffness
        k_clamped_total = 0
        total_thickness = 0
        for part_frame in clamped_parts_frames:
            thickness = float(part_frame['thickness_var'].get())
            if thickness <= 0:
                raise ValueError("Parça kalınlığı 0'dan büyük olmalı.")
            total_thickness += thickness
            part_type = part_frame['type_var'].get()
            # Simplified area assumption (using A_thread for all parts)
            k_part = (E_bolt * A_thread) / thickness
            k_clamped_total = k_part if k_clamped_total == 0 else 1 / (1/k_clamped_total + 1/k_part)
        
        if total_thickness == 0:
            messagebox.showwarning("Uyarı", "En az bir sıkıştırılan parça eklenmeli.")
            return
        
        # Load distribution
        delta_F_bolt = (k_bolt / (k_bolt + k_clamped_total)) * F_ext_tensile
        F_bolt_total = F_preload + delta_F_bolt
        F_clamped = F_ext_tensile - delta_F_bolt
        
        # Calculate displacements
        delta_L_bolt = F_bolt_total / k_bolt
        delta_L_clamped = F_clamped / k_clamped_total if k_clamped_total > 0 else 0
        
        # Safety factor (simplified)
        max_load = yield_strength * A_thread
        safety_factor = max_load / F_bolt_total if F_bolt_total > 0 else float('inf')
        
        # Shear stress (simplified)
        shear_stress = F_ext_shear / A_thread
        
        # Display results
        result_text = (f"Toplam Cıvata Sertliği: {k_bolt:.2f} N/mm\n"
                       f"Toplam Kavrama Sertliği: {k_clamped_total:.2f} N/mm\n"
                       f"Toplam Cıvata Kuvveti: {F_bolt_total:.2f} N\n"
                       f"Cıvata Çarpılma: {delta_L_bolt:.4f} mm\n"
                       f"Kavrama Çarpılma: {delta_L_clamped:.4f} mm\n"
                       f"Kesme Gerilimi: {shear_stress:.2f} MPa\n"
                       f"Güvenlik Faktörü: {safety_factor:.2f}")
        result_var.set(result_text)
        
        # Plot load-displacement curve
        plot_load_displacement(k_bolt, k_clamped_total, F_preload, F_ext_tensile, delta_F_bolt)
    except ValueError as e:
        messagebox.showerror("Giriş Hatası", str(e))
    except KeyError:
        messagebox.showerror("Giriş Hatası", "Geçersiz cıvata boyutu ya da malzeme.")

def plot_load_displacement(k_bolt, k_clamped, F_preload, F_ext_tensile, delta_F_bolt):
    F_total_bolt = F_preload + delta_F_bolt
    delta_L_bolt_preload = F_preload / k_bolt
    delta_L_bolt_total = F_total_bolt / k_bolt
    delta_L_clamped = (F_ext_tensile - delta_F_bolt) / k_clamped if k_clamped > 0 else 0
    
    x_bolt = [0, delta_L_bolt_preload, delta_L_bolt_total]
    y_bolt = [0, F_preload, F_total_bolt]
    
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(x_bolt, y_bolt, marker='o', label='Cıvata Yük-Çarpılma', color='blue')
    ax.set_xlabel('Çarpılma (mm)')
    ax.set_ylabel('Yük (N)')
    ax.set_title('Cıvata ve Kavrama Yük-Çarpılma İlişkisi')
    ax.grid(True)
    ax.legend()
    
    plot_window = tk.Toplevel(root)
    plot_window.title("Yük-Çarpılma Eğrisi")
    canvas = FigureCanvasTkAgg(fig, master=plot_window)
    canvas.draw()
    canvas.get_tk_widget().pack()

def add_clamped_part():
    frame = ttk.Frame(clamped_parts_frame)
    frame.pack(fill='x', pady=2)
    
    type_var = tk.StringVar(value='Washer')
    ttk.Combobox(frame, textvariable=type_var, values=clamped_part_types, width=10).pack(side='left', padx=5)
    
    thickness_var = tk.StringVar()
    tk.Entry(frame, textvariable=thickness_var, width=10).pack(side='left', padx=5)
    
    ttk.Button(frame, text="Kaldır", command=lambda: remove_clamped_part(frame)).pack(side='left', padx=5)
    
    clamped_parts_frames.append({'type_var': type_var, 'thickness_var': thickness_var})
    update_clamped_parts_frame()

def remove_clamped_part(frame):
    frame.destroy()
    clamped_parts_frames[:] = [f for f in clamped_parts_frames if f['thickness_var'].get() != frame.winfo_children()[1].get()]
    update_clamped_parts_frame()

def update_clamped_parts_frame():
    clamped_parts_frame.update_idletasks()

def clear_inputs():
    bolt_size_var.set("")
    shank_length_var.set("")
    thread_length_var.set("")
    material_var.set('Steel')
    preload_percent_var.set('67')
    tensile_force_var.set("")
    shear_force_var.set("")
    result_var.set("")
    for frame in clamped_parts_frames[:]:
        remove_clamped_part(frame.winfo_children()[0].master)

def render_latex_to_image(latex_text):
    fig, ax = plt.subplots(figsize=(8, 1), dpi=100)
    ax.text(0.5, 0.5, f"${latex_text}$", fontsize=12, ha='center', va='center')
    ax.axis('off')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1)
    buf.seek(0)
    img = Image.open(buf)
    plt.close(fig)
    return ImageTk.PhotoImage(img)

def render_wiki_text(widget, text):
    widget.config(state="normal")
    widget.delete("1.0", tk.END)
    widget.image_list = []
    
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
            widget.image_list.append(image)
            widget.image_create(tk.END, image=image)
        except Exception as e:
            widget.insert(tk.END, f"[LaTeX Hatası: {str(e)}]")
        text = text[end+2:]
    widget.config(state="disabled")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height()
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#ffffe0", relief="solid", borderwidth=1)
        label.pack()

    def hide_tip(self, event):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

# Ana pencere
root = tk.Tk()
root.title("Bolt Stiffness Calculator")
root.geometry("800x600")

# Notebook oluştur
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')

# Calculator sekmesi
calc_frame = ttk.Frame(notebook)
notebook.add(calc_frame, text="Hesaplama")

# Calculator widget'ları
tk.Label(calc_frame, text="Cıvata Boyutu:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
bolt_size_var = tk.StringVar()
bolt_size_entry = ttk.Combobox(calc_frame, textvariable=bolt_size_var, values=list(bolt_sizes.keys()), width=10)
bolt_size_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")
ToolTip(bolt_size_entry, "Cıvata boyutu, örneğin M10.")

tk.Label(calc_frame, text="Gövde Uzunluğu (mm):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
shank_length_var = tk.StringVar()
shank_length_entry = tk.Entry(calc_frame, textvariable=shank_length_var, width=15)
shank_length_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
ToolTip(shank_length_entry, "Cıvatanın düz kısmının uzunluğu (mm).")

tk.Label(calc_frame, text="Dişli Kısım Uzunluğu (mm):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
thread_length_var = tk.StringVar()
thread_length_entry = tk.Entry(calc_frame, textvariable=thread_length_var, width=15)
thread_length_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
ToolTip(thread_length_entry, "Dişli kısmın yük altındaki uzunluğu (mm), yoksa 0.")

tk.Label(calc_frame, text="Malzeme:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
material_var = tk.StringVar(value='Steel')
material_entry = ttk.Combobox(calc_frame, textvariable=material_var, values=list(materials.keys()), width=15, state="readonly")
material_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_entry, "Cıvata malzemesi, elastiklik modülü ve dayanımı belirler.")

tk.Label(calc_frame, text="Ön Yükleme Yüzdesi (%):").grid(row=4, column=0, padx=10, pady=5, sticky="e")
preload_percent_var = tk.StringVar(value='67')
preload_percent_entry = tk.Entry(calc_frame, textvariable=preload_percent_var, width=15)
preload_percent_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
ToolTip(preload_percent_entry, "Ön yükleme, verim dayanımının yüzdesi (0-100).")

tk.Label(calc_frame, text="Çekme Kuvveti (N):").grid(row=5, column=0, padx=10, pady=5, sticky="e")
tensile_force_var = tk.StringVar()
tensile_force_entry = tk.Entry(calc_frame, textvariable=tensile_force_var, width=15)
tensile_force_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")
ToolTip(tensile_force_entry, "Cıvatalı birleşmeye uygulanan çekme kuvveti (N).")

tk.Label(calc_frame, text="Kesme Kuvveti (N):").grid(row=6, column=0, padx=10, pady=5, sticky="e")
shear_force_var = tk.StringVar()
shear_force_entry = tk.Entry(calc_frame, textvariable=shear_force_var, width=15)
shear_force_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")
ToolTip(shear_force_entry, "Cıvatalı birleşmeye yanlara uygulanan kesme kuvveti (N).")

# Sıkıştırılan parçalar için dinamik alan
tk.Label(calc_frame, text="Sıkıştırılan Parçalar:").grid(row=7, column=0, padx=10, pady=5, sticky="e")
clamped_parts_frame = ttk.Frame(calc_frame)
clamped_parts_frame.grid(row=7, column=1, padx=10, pady=5, sticky="w")
clamped_parts_frames = []

ttk.Button(calc_frame, text="Parça Ekle", command=add_clamped_part).grid(row=8, column=1, padx=10, pady=5, sticky="w")

# Buttons
button_frame = ttk.Frame(calc_frame)
button_frame.grid(row=9, column=0, columnspan=2, pady=10)
ttk.Button(button_frame, text="Hesapla", command=calculate_stiffness).pack(side="left", padx=5)
ttk.Button(button_frame, text="Temizle", command=clear_inputs).pack(side="left", padx=5)

# Results
result_var = tk.StringVar()
result_label = tk.Label(calc_frame, textvariable=result_var, justify="left")
result_label.grid(row=10, column=0, columnspan=2, padx=10, pady=10)

# Wiki sekmesi
wiki_frame = ttk.Frame(notebook)
notebook.add(wiki_frame, text="Bilgi")

# Wiki metnini gösteren Text widget (salt okunur)
wiki_text_widget = tk.Text(wiki_frame, wrap="word", state="disabled", height=20)
wiki_text_widget.pack(fill="both", expand=True, padx=10, pady=10)

# Scrollbar for wiki_text_widget
wiki_scrollbar = ttk.Scrollbar(wiki_frame, command=wiki_text_widget.yview)
wiki_scrollbar.pack(side="right", fill="y")
wiki_text_widget.config(yscrollcommand=wiki_scrollbar.set)

# Render wiki text with LaTeX
render_wiki_text(wiki_text_widget, wiki_text)

# Uygulamayı çalıştır
root.mainloop()