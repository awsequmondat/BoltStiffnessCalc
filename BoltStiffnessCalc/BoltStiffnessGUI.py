import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io
import numpy as np

# Cıvata boyutları
bolt_sizes = {
    'M6': {'A_shank': 28.27, 'A_thread': 20.1},
    'M8': {'A_shank': 50.27, 'A_thread': 36.6},
    'M10': {'A_shank': 78.54, 'A_thread': 58.0},
    'M12': {'A_shank': 113.10, 'A_thread': 84.3},
    'M14': {'A_shank': 153.94, 'A_thread': 114.8},
    'M16': {'A_shank': 201.06, 'A_thread': 157.1},
}

# Malzeme özellikleri (düzenlenebilir)
materials = {
    'Steel': {'E': 200000, 'yield_strength': 800, 'ultimate_strength': 1000, 'poisson_ratio': 0.30, 'percent_elongation': 40, 'density': 7.85},
    'Aluminum': {'E': 70000, 'yield_strength': 275, 'ultimate_strength': 310, 'poisson_ratio': 0.33, 'percent_elongation': 12, 'density': 2.70},
    'Titanium': {'E': 110000, 'yield_strength': 800, 'ultimate_strength': 900, 'poisson_ratio': 0.34, 'percent_elongation': 10, 'density': 4.51},
}

# Wiki metnini dosyadan yükle
try:
    with open(r"c:\Users\DELL\Desktop\Kısayollar\Things\Projects\BoltStiffnessCalc\BoltStiffnessCalc\wiki_text.txt", "r", encoding="utf-8") as file:
        wiki_text = file.read()
except FileNotFoundError:
    wiki_text = "Wiki metni bulunamadı. Lütfen wiki_text.txt dosyasını oluşturun."

# Parça türleri
clamped_part_types = ['Washer', 'Plate', 'Cylinder']

# Global değişkenler
current_material = None
clamped_parts_frames = []

def calculate_stiffness():
    bolt_size = bolt_size_var.get()
    try:
        L_shank = float(shank_length_var.get())
        if L_shank <= 0:
            raise ValueError("Gövde uzunluğu 0'dan büyük olmalıdır.")
        L_thread = float(thread_length_var.get())
        if L_thread < 0:
            raise ValueError("Dişli kısım uzunluğu negatif olamaz.")
        material = material_var.get()
        E_bolt = materials[material]['E']
        yield_strength = materials[material]['yield_strength']
        ultimate_strength = materials[material]['ultimate_strength']
        A_shank = bolt_sizes[bolt_size]['A_shank']
        A_thread = bolt_sizes[bolt_size]['A_thread']
        preload_percent = float(preload_percent_var.get())
        if not 0 <= preload_percent <= 100:
            raise ValueError("Ön yükleme yüzdesi 0-100 arasında olmalıdır.")
        F_preload = (preload_percent / 100) * yield_strength * A_thread
        F_ext_tensile = float(tensile_force_var.get())
        F_ext_shear = float(shear_force_var.get())
        
        # Cıvata sertliği
        k_shank = (E_bolt * A_shank) / L_shank
        if L_thread > 0:
            k_thread = (E_bolt * A_thread) / L_thread
            k_bolt = 1 / (1/k_shank + 1/k_thread)
        else:
            k_bolt = k_shank
        
        # Sıkıştırılan parçaların sertliği
        k_clamped_total = 0
        total_thickness = 0
        for part_frame in clamped_parts_frames:
            thickness = float(part_frame['thickness_var'].get())
            if thickness <= 0:
                raise ValueError("Lütfen tüm parçalar için geçerli kalınlık değerleri girin (>0).")
            material = part_frame['material_var'].get()
            E_part = materials[material]['E']
            area = float(part_frame['area_var'].get())
            if area <= 0:
                raise ValueError("Lütfen tüm parçalar için geçerli alan değerleri girin (>0).")
            total_thickness += thickness
            k_part = (E_part * area) / thickness
            k_clamped_total = k_part if k_clamped_total == 0 else 1 / (1/k_clamped_total + 1/k_part)
        
        if total_thickness == 0:
            raise ValueError("En az bir sıkıştırılan parça eklenmelidir.")
        
        # Yük dağılımı
        delta_F_bolt = (k_bolt / (k_bolt + k_clamped_total)) * F_ext_tensile
        F_bolt_total = F_preload + delta_F_bolt
        F_clamped = F_ext_tensile - delta_F_bolt
        
        # Çarpılmalar
        delta_L_bolt = F_bolt_total / k_bolt
        delta_L_clamped = F_clamped / k_clamped_total if k_clamped_total > 0 else 0
        
        # Güvenlik faktörü
        safety_basis = safety_basis_var.get()
        max_load = yield_strength * A_thread if safety_basis == "Yield" else ultimate_strength * A_thread
        safety_factor = max_load / F_bolt_total if F_bolt_total > 0 else float('inf')
        
        # Kesme gerilimi
        shear_area = shear_area_var.get()
        shear_area_value = A_shank if shear_area == "Shank" else A_thread
        shear_stress = F_ext_shear / shear_area_value
        
        # Sonuçları göster
        result_text = (f"Toplam Cıvata Sertliği: {k_bolt:.2f} N/mm\n"
                       f"Toplam Kavrama Sertliği: {k_clamped_total:.2f} N/mm\n"
                       f"Toplam Cıvata Kuvveti: {F_bolt_total:.2f} N\n"
                       f"Cıvata Çarpılma: {delta_L_bolt:.4f} mm\n"
                       f"Kavrama Çarpılma: {delta_L_clamped:.4f} mm\n"
                       f"Kesme Gerilimi: {shear_stress:.2f} MPa\n"
                       f"Güvenlik Faktörü ({safety_basis}): {safety_factor:.2f}")
        result_var.set(result_text)
        
        # Grafik çizimi
        plot_load_displacement(k_bolt, k_clamped_total, F_preload, F_ext_tensile, delta_F_bolt)
    except ValueError as e:
        messagebox.showerror("Giriş Hatası", str(e))
    except KeyError:
        messagebox.showerror("Giriş Hatası", "Geçersiz cıvata boyutu veya malzeme seçimi.")

def plot_load_displacement(k_bolt, k_clamped, F_preload, F_ext_tensile, delta_F_bolt):
    F_total_bolt = F_preload + delta_F_bolt
    delta_L_bolt_preload = F_preload / k_bolt
    delta_L_bolt_total = F_total_bolt / k_bolt
    
    x_bolt = [0, delta_L_bolt_preload, delta_L_bolt_total]
    y_bolt = [0, F_preload, F_total_bolt]
    
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(x_bolt, y_bolt, marker='o', label='Cıvata Yük-Çarpılma', color='blue')
    ax.set_xlabel('Çarpılma (mm)')
    ax.set_ylabel('Yük (N)')
    ax.set_title('Cıvata Yük-Çarpılma İlişkisi')
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
    
    material_var = tk.StringVar(value='Steel')
    ttk.Combobox(frame, textvariable=material_var, values=list(materials.keys()), width=15).pack(side='left', padx=5)
    
    area_var = tk.StringVar()
    tk.Entry(frame, textvariable=area_var, width=10).pack(side='left', padx=5)
    
    ttk.Button(frame, text="Kaldır", command=lambda: remove_clamped_part(frame)).pack(side='left', padx=5)
    
    clamped_parts_frames.append({'type_var': type_var, 'thickness_var': thickness_var, 'material_var': material_var, 'area_var': area_var})
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
    shear_area_var.set("Thread")
    safety_basis_var.set("Yield")
    for frame in clamped_parts_frames[:]:
        remove_clamped_part(frame.winfo_children()[0].master)

def save_material():
    global current_material
    name = material_name_var.get().strip()
    try:
        if not name:
            raise ValueError("Malzeme adı boş olamaz.")
        E = float(material_E_var.get()) * 1000  # GPa to MPa
        if E <= 0:
            raise ValueError("Elastiklik modülü 0'dan büyük olmalıdır.")
        yield_strength = float(material_yield_var.get())
        if yield_strength <= 0:
            raise ValueError("Verim dayanımı 0'dan büyük olmalıdır.")
        ultimate_strength = float(material_ultimate_var.get())
        if ultimate_strength <= 0 or ultimate_strength < yield_strength:
            raise ValueError("Nihai dayanım, verim dayanımından büyük ve pozitif olmalıdır.")
        poisson_ratio = float(material_poisson_var.get()) if material_poisson_var.get() else 0.3
        if not 0 <= poisson_ratio <= 0.5:
            raise ValueError("Poisson oranı 0-0.5 arasında olmalıdır.")
        percent_elongation = float(material_elongation_var.get()) if material_elongation_var.get() else None
        if percent_elongation is not None and percent_elongation < 0:
            raise ValueError("Uzama yüzdesi negatif olamaz.")
        density = float(material_density_var.get()) if material_density_var.get() else 8.0
        if density <= 0:
            raise ValueError("Yoğunluk 0'dan büyük olmalıdır.")
        
        if current_material and current_material != name and name in materials:
            if not messagebox.askyesno("Uyarı", f"'{name}' zaten var. Üzerine yazmak ister misiniz?"):
                return
        if current_material and current_material != name:
            del materials[current_material]
        materials[name] = {
            'E': E,
            'yield_strength': yield_strength,
            'ultimate_strength': ultimate_strength,
            'poisson_ratio': poisson_ratio,
            'percent_elongation': percent_elongation,
            'density': density
        }
        update_material_listbox()
        material_var.set(name)
        material_entry['values'] = list(materials.keys())
        current_material = name
        clear_material_inputs()
        plot_stress_strain(name)
    except ValueError as e:
        messagebox.showerror("Giriş Hatası", str(e))

def new_material():
    global current_material
    current_material = None
    clear_material_inputs()

def delete_material():
    global current_material
    selected = material_listbox.curselection()
    if selected:
        name = material_listbox.get(selected[0])
        if name in materials:
            del materials[name]
            update_material_listbox()
            material_entry['values'] = list(materials.keys())
            if material_var.get() == name:
                material_var.set('Steel' if 'Steel' in materials else list(materials.keys())[0] if materials else '')
            if current_material == name:
                current_material = None
                clear_material_inputs()

def on_material_select(event):
    global current_material
    selected = material_listbox.curselection()
    if selected:
        name = material_listbox.get(selected[0])
        material = materials.get(name)
        if material:
            current_material = name
            material_name_var.set(name)
            material_E_var.set(str(material['E'] / 1000))  # MPa to GPa
            material_yield_var.set(str(material['yield_strength']))
            material_ultimate_var.set(str(material['ultimate_strength']))
            material_poisson_var.set(str(material['poisson_ratio']))
            material_elongation_var.set(str(material['percent_elongation']) if material['percent_elongation'] is not None else "")
            material_density_var.set(str(material['density']))

def update_material_listbox():
    material_listbox.delete(0, tk.END)
    for name in materials:
        material_listbox.insert(tk.END, name)

def clear_material_inputs():
    material_name_var.set("")
    material_E_var.set("")
    material_yield_var.set("")
    material_ultimate_var.set("")
    material_poisson_var.set("")
    material_elongation_var.set("")
    material_density_var.set("")

def plot_stress_strain(material_name):
    material = materials.get(material_name)
    if not material:
        return
    
    E = material['E']
    yield_strength = material['yield_strength']
    ultimate_strength = material['ultimate_strength']
    percent_elongation = material.get('percent_elongation', None)
    
    strain_yield = yield_strength / E
    strain_ultimate = percent_elongation / 100 if percent_elongation else strain_yield * 1.5
    
    strain = [0, strain_yield, strain_ultimate]
    stress = [0, yield_strength, ultimate_strength]
    
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(strain, stress, marker='o', label=f'{material_name} Stress-Strain')
    ax.set_xlabel('Strain (mm/mm)')
    ax.set_ylabel('Stress (MPa)')
    ax.set_title(f'{material_name} Stress-Strain Eğrisi')
    ax.grid(True)
    ax.legend()
    
    plot_window = tk.Toplevel(root)
    plot_window.title("Stress-Strain Eğrisi")
    canvas = FigureCanvasTkAgg(fig, master=plot_window)
    canvas.draw()
    canvas.get_tk_widget().pack()

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
root.title("Cıvata Sertliği Hesaplayıcısı")
root.geometry("800x600")

# Notebook
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')

# Hesaplama sekmesi
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

# Kesme alanı seçimi
tk.Label(calc_frame, text="Kesme Alanı:").grid(row=7, column=0, padx=10, pady=5, sticky="e")
shear_area_var = tk.StringVar(value="Thread")
ttk.Radiobutton(calc_frame, text="Gövde", variable=shear_area_var, value="Shank").grid(row=7, column=1, padx=5, pady=5, sticky="w")
ttk.Radiobutton(calc_frame, text="Dişli", variable=shear_area_var, value="Thread").grid(row=7, column=2, padx=5, pady=5, sticky="w")

# Güvenlik faktörü temeli
tk.Label(calc_frame, text="Güvenlik Faktörü Temeli:").grid(row=8, column=0, padx=10, pady=5, sticky="e")
safety_basis_var = tk.StringVar(value="Yield")
ttk.Radiobutton(calc_frame, text="Verim Dayanımı", variable=safety_basis_var, value="Yield").grid(row=8, column=1, padx=5, pady=5, sticky="w")
ttk.Radiobutton(calc_frame, text="Nihai Dayanım", variable=safety_basis_var, value="Ultimate").grid(row=8, column=2, padx=5, pady=5, sticky="w")

# Sıkıştırılan parçalar
tk.Label(calc_frame, text="Sıkıştırılan Parçalar (Kalınlık-mm, Alan-mm²):").grid(row=9, column=0, padx=10, pady=5, sticky="e")
clamped_parts_frame = ttk.Frame(calc_frame)
clamped_parts_frame.grid(row=9, column=1, padx=10, pady=5, sticky="w")

ttk.Button(calc_frame, text="Parça Ekle", command=add_clamped_part).grid(row=10, column=1, padx=10, pady=5, sticky="w")

# Butonlar
button_frame = ttk.Frame(calc_frame)
button_frame.grid(row=11, column=0, columnspan=2, pady=10)
ttk.Button(button_frame, text="Hesapla", command=calculate_stiffness).pack(side="left", padx=5)
ttk.Button(button_frame, text="Temizle", command=clear_inputs).pack(side="left", padx=5)

# Sonuçlar
result_var = tk.StringVar()
result_label = tk.Label(calc_frame, textvariable=result_var, justify="left")
result_label.grid(row=12, column=0, columnspan=2, padx=10, pady=10)

# Malzeme Kütüphanesi sekmesi
material_frame = ttk.Frame(notebook)
notebook.add(material_frame, text="Malzeme Kütüphanesi")

# Malzeme Kütüphanesi widget'ları
tk.Label(material_frame, text="Malzeme Adı *:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
material_name_var = tk.StringVar()
material_name_entry = tk.Entry(material_frame, textvariable=material_name_var, width=20)
material_name_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_name_entry, "Malzeme adı, örneğin '316 Stainless Steel'.")

tk.Label(material_frame, text="Durum:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
material_condition_var = tk.StringVar()
material_condition_entry = tk.Entry(material_frame, textvariable=material_condition_var, width=20)
material_condition_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_condition_entry, "Malzeme durumu, örneğin 'Annealed'.")

tk.Label(material_frame, text="Form:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
material_form_var = tk.StringVar()
material_form_entry = tk.Entry(material_frame, textvariable=material_form_var, width=20)
material_form_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_form_entry, "Malzeme formu, örneğin 'Bar'.")

tk.Label(material_frame, text="Boyut:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
material_size_var = tk.StringVar()
material_size_entry = tk.Entry(material_frame, textvariable=material_size_var, width=20)
material_size_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_size_entry, "Malzeme boyutu, örneğin '<= 5 in'.")

tk.Label(material_frame, text="Verim Dayanımı (MPa) *:").grid(row=4, column=0, padx=10, pady=5, sticky="e")
material_yield_var = tk.StringVar()
material_yield_entry = tk.Entry(material_frame, textvariable=material_yield_var, width=15)
material_yield_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_yield_entry, "Malzemenin verim dayanımı (MPa), örneğin 200.")

tk.Label(material_frame, text="Nihai Dayanım (MPa) *:").grid(row=5, column=0, padx=10, pady=5, sticky="e")
material_ultimate_var = tk.StringVar()
material_ultimate_entry = tk.Entry(material_frame, textvariable=material_ultimate_var, width=15)
material_ultimate_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_ultimate_entry, "Malzemenin nihai dayanımı (MPa), örneğin 530.")

tk.Label(material_frame, text="Elastiklik Modülü (GPa) *:").grid(row=6, column=0, padx=10, pady=5, sticky="e")
material_E_var = tk.StringVar()
material_E_entry = tk.Entry(material_frame, textvariable=material_E_var, width=15)
material_E_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_E_entry, "Malzemenin elastiklik modülü (GPa), örneğin 200.")

tk.Label(material_frame, text="Poisson Oranı:").grid(row=7, column=0, padx=10, pady=5, sticky="e")
material_poisson_var = tk.StringVar()
material_poisson_entry = tk.Entry(material_frame, textvariable=material_poisson_var, width=15)
material_poisson_entry.grid(row=7, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_poisson_entry, "Malzemenin Poisson oranı, örneğin 0.28.")

tk.Label(material_frame, text="Uzama Yüzdesi (%):").grid(row=8, column=0, padx=10, pady=5, sticky="e")
material_elongation_var = tk.StringVar()
material_elongation_entry = tk.Entry(material_frame, textvariable=material_elongation_var, width=15)
material_elongation_entry.grid(row=8, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_elongation_entry, "Malzemenin uzama yüzdesi, örneğin 40.")

tk.Label(material_frame, text="Yoğunluk (g/cm³):").grid(row=9, column=0, padx=10, pady=5, sticky="e")
material_density_var = tk.StringVar()
material_density_entry = tk.Entry(material_frame, textvariable=material_density_var, width=15)
material_density_entry.grid(row=9, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_density_entry, "Malzemenin yoğunluğu (g/cm³), örneğin 8.0.")

material_button_frame = ttk.Frame(material_frame)
material_button_frame.grid(row=10, column=0, columnspan=2, pady=10)
ttk.Button(material_button_frame, text="Kaydet", command=save_material).pack(side="left", padx=5)
ttk.Button(material_button_frame, text="Yeni", command=new_material).pack(side="left", padx=5)
ttk.Button(material_button_frame, text="Sil", command=delete_material).pack(side="left", padx=5)

tk.Label(material_frame, text="Mevcut Malzemeler:").grid(row=11, column=0, padx=10, pady=5, sticky="e")
material_listbox = tk.Listbox(material_frame, height=10, width=30)
material_listbox.grid(row=11, column=1, padx=10, pady=5, sticky="w")
material_listbox.bind('<<ListboxSelect>>', on_material_select)
update_material_listbox()

# Wiki sekmesi
wiki_frame = ttk.Frame(notebook)
notebook.add(wiki_frame, text="Bilgi")

wiki_text_widget = tk.Text(wiki_frame, wrap="word", state="disabled", height=20)
wiki_text_widget.pack(fill="both", expand=True, padx=10, pady=10)

wiki_scrollbar = ttk.Scrollbar(wiki_frame, command=wiki_text_widget.yview)
wiki_scrollbar.pack(side="right", fill="y")
wiki_text_widget.config(yscrollcommand=wiki_scrollbar.set)

render_wiki_text(wiki_text_widget, wiki_text)

# Uygulamayı çalıştır
root.mainloop()