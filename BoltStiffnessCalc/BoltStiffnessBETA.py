import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io
import numpy as np
import pandas as pd
from itertools import product

# Cıvata boyutları
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
    'Steel': {'E': 200000, 'yield_strength': 800, 'ultimate_strength': 1000, 'poisson_ratio': 0.30, 'percent_elongation': 40, 'density': 7.85},
    'Aluminum': {'E': 70000, 'yield_strength': 275, 'ultimate_strength': 310, 'poisson_ratio': 0.33, 'percent_elongation': 12, 'density': 2.70},
    'Titanium': {'E': 110000, 'yield_strength': 800, 'ultimate_strength': 900, 'poisson_ratio': 0.34, 'percent_elongation': 10, 'density': 4.51},
}

# Wiki metni (Markdown ve LaTeX karışımı)
wiki_text = """
# Cıvata Sertliği Hesaplama Bilgileri

Bu bölümde cıvata sertliği hesaplamaları için temel bilgiler ve formüller yer alıyor.

## Temel Formüller

Cıvata sertliği \( k_b \) ve kavrama sertliği \( k_c \) aşağıdaki gibi hesaplanır:

- **Cıvata Sertliği:**
  $$ k_b = \\frac{E \\cdot A}{L} $$
  Burada:
  - \( E \): Elastiklik modülü (MPa)
  - \( A \): Kesit alanı (mm²)
  - \( L \): Uzunluk (mm)

- **Kavrama Sertliği:**
  $$ k_c = \\frac{1}{\\sum \\frac{L_i}{E_i \\cdot A_i}} $$
  Burada \( L_i \), \( E_i \), ve \( A_i \) sırasıyla her bir sıkıştırılan parçanın uzunluğu, elastiklik modülü ve kesit alanıdır.

## Örnek Hesaplama

Bir M10 cıvata için:
- **Gövde Uzunluğu:** 30 mm
- **Dişli Uzunluk:** 10 mm
- **Malzeme:** Steel (\( E = 200000 \, \text{MPa} \))

Sertlik:
$$ k_b = \\frac{200000 \\cdot 58}{40} = 290000 \, \text{N/mm} $$

## Notlar
- Daha fazla bilgi için Shigley's Mechanical Engineering Design kitabına bakabilirsiniz.
"""

# Parça türleri
clamped_part_types = ['Washer', 'Plate', 'Cylinder']

# Global değişkenler
current_material = None
clamped_parts_frames = []
results_history = []
max_rows = 5
canvas = None
para_canvas = None  # Parametric plot canvas

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
        label = tk.Label(tw, text=self.text, background="#FFFFE0", relief="solid", borderwidth=1, fg="#333333")
        label.pack()

    def hide_tip(self, event):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

def calculate_stiffness():
    global canvas
    bolt_size = bolt_size_var.get()
    try:
        if not bolt_size:
            raise ValueError("Lütfen bir cıvata boyutu seçin.")
        L_shank = float(shank_length_var.get() or 0)
        if L_shank <= 0:
            raise ValueError("Gövde uzunluğu 0'dan büyük olmalıdır.")
        L_thread = float(thread_length_var.get() or 0)
        if L_thread < 0:
            raise ValueError("Dişli kısım uzunluğu negatif olamaz.")
        material = material_var.get()
        if not material:
            raise ValueError("Lütfen bir malzeme seçin.")
        E_bolt = materials[material]['E']
        yield_strength = materials[material]['yield_strength']
        ultimate_strength = materials[material]['ultimate_strength']
        A_shank = bolt_sizes[bolt_size]['A_shank']
        A_thread = bolt_sizes[bolt_size]['A_thread']
        preload_percent = float(preload_percent_var.get() or 0)
        if not 0 <= preload_percent <= 100:
            raise ValueError("Ön yükleme yüzdesi 0-100 arasında olmalıdır.")
        F_preload = (preload_percent / 100) * yield_strength * A_thread
        F_ext_tensile = float(tensile_force_var.get() or 0)
        F_ext_shear = float(shear_force_var.get() or 0)
        
        k_shank = (E_bolt * A_shank) / L_shank
        if L_thread > 0:
            k_thread = (E_bolt * A_thread) / L_thread
            k_bolt = 1 / (1/k_shank + 1/k_thread)
        else:
            k_bolt = k_shank
        
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
        
        delta_F_bolt = (k_bolt / (k_bolt + k_clamped_total)) * F_ext_tensile
        F_bolt_total = F_preload + delta_F_bolt
        F_clamped = F_ext_tensile - delta_F_bolt
        
        delta_L_bolt = F_bolt_total / k_bolt
        delta_L_clamped = F_clamped / k_clamped_total if k_clamped_total > 0 else 0
        
        safety_basis = safety_basis_var.get()
        max_load = yield_strength * A_thread if safety_basis == "Yield" else ultimate_strength * A_thread
        safety_factor = max_load / F_bolt_total if F_bolt_total > 0 else float('inf')
        
        shear_area = shear_area_var.get()
        shear_area_value = A_shank if shear_area == "Shank" else A_thread
        shear_stress = F_ext_shear / shear_area_value
        
        # Sonuçları kaydet
        result = {
            "Toplam Cıvata Sertliği (N/mm)": f"{k_bolt:.2f}",
            "Toplam Kavrama Sertliği (N/mm)": f"{k_clamped_total:.2f}",
            "Toplam Cıvata Kuvveti (N)": f"{F_bolt_total:.2f}",
            "Cıvata Çarpılma (mm)": f"{delta_L_bolt:.4f}",
            "Kavrama Çarpılma (mm)": f"{delta_L_clamped:.4f}",
            "Kesme Gerilimi (MPa)": f"{shear_stress:.2f}",
            f"Güvenlik Faktörü ({safety_basis})": f"{safety_factor:.2f}"
        }
        results_history.append(result)
        update_results_table()
        
        # Yük-çarpılma eğrisini arayüzde güncelle
        if canvas:
            canvas.get_tk_widget().destroy()
        fig, ax = plt.subplots(figsize=(4, 3))
        F_total_bolt = F_preload + delta_F_bolt
        delta_L_bolt_preload = F_preload / k_bolt
        delta_L_bolt_total = F_total_bolt / k_bolt
        x_bolt = [0, delta_L_bolt_preload, delta_L_bolt_total]
        y_bolt = [0, F_preload, F_total_bolt]
        ax.plot(x_bolt, y_bolt, marker='o', label='Yük-Çarpılma', color='blue')
        ax.set_xlabel('Çarpılma (mm)')
        ax.set_ylabel('Yük (N)')
        ax.set_title('Yük-Çarpılma Eğrisi')
        ax.grid(True)
        ax.legend()
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    except ValueError as e:
        messagebox.showerror("Giriş Hatası", str(e))
    except KeyError:
        messagebox.showerror("Giriş Hatası", "Geçersiz cıvata boyutu veya malzeme seçimi.")

def add_clamped_part(type='Washer', thickness='', material='Steel', area=''):
    frame = ttk.Frame(clamped_parts_frame, relief="groove", borderwidth=1)
    frame.pack(fill='x', pady=2)
    
    type_var = tk.StringVar(value=type)
    ttk.Combobox(frame, textvariable=type_var, values=clamped_part_types, width=10).pack(side='left', padx=5, pady=2)
    
    thickness_var = tk.StringVar(value=thickness)
    tk.Entry(frame, textvariable=thickness_var, width=10).pack(side='left', padx=5, pady=2)
    
    material_var = tk.StringVar(value=material)
    ttk.Combobox(frame, textvariable=material_var, values=list(materials.keys()), width=15).pack(side='left', padx=5, pady=2)
    
    area_var = tk.StringVar(value=area)
    tk.Entry(frame, textvariable=area_var, width=10).pack(side='left', padx=5, pady=2)
    
    ttk.Button(frame, text="Kaldır", command=lambda: remove_clamped_part(frame)).pack(side='left', padx=5, pady=2)
    
    clamped_parts_frames.append({'type_var': type_var, 'thickness_var': thickness_var, 'material_var': material_var, 'area_var': area_var})
    update_clamped_parts_frame()

def remove_clamped_part(frame):
    frame.destroy()
    clamped_parts_frames[:] = [f for f in clamped_parts_frames if f['thickness_var'].get() != frame.winfo_children()[1].get()]
    update_clamped_parts_frame()

def update_clamped_parts_frame():
    clamped_parts_frame.update_idletasks()

def clear_inputs():
    global canvas
    bolt_size_var.set("")
    shank_length_var.set("")
    thread_length_var.set("")
    material_var.set('Steel')
    preload_percent_var.set('67')
    tensile_force_var.set("")
    shear_force_var.set("")
    shear_area_var.set("Thread")
    safety_basis_var.set("Yield")
    for frame in clamped_parts_frames[:]:
        frame.winfo_children()[0].master.destroy()
    clamped_parts_frames.clear()
    if canvas:
        canvas.get_tk_widget().destroy()
        canvas = None

def clear_results():
    global results_history
    results_history = []
    update_results_table()

def test_values():
    clear_inputs()
    root.update()
    bolt_size_var.set("M10")
    shank_length_var.set("30")
    thread_length_var.set("10")
    material_var.set("Steel")
    preload_percent_var.set("70")
    tensile_force_var.set("10000")
    shear_force_var.set("5000")
    shear_area_var.set("Thread")
    safety_basis_var.set("Yield")
    
    add_clamped_part(type="Plate", thickness="10", material="Steel", area="100")
    add_clamped_part(type="Washer", thickness="5", material="Aluminum", area="80")
    root.update()
    messagebox.showinfo("Test", "Test değerleri yüklendi. 'Hesapla' butonuna basarak sonuçları görebilirsiniz.")

def update_results_table():
    global max_rows
    try:
        max_rows = int(max_rows_var.get())
        if max_rows < 1:
            raise ValueError("En az 1 hesaplama gösterilmelidir.")
    except ValueError:
        max_rows = 5
        max_rows_var.set("5")
    
    for item in results_tree.get_children():
        results_tree.delete(item)
    
    if not results_history:
        return
    
    headers = ["Parametre"] + [f"Hesaplama {i+1}" for i in range(min(len(results_history), max_rows))]
    results_tree["columns"] = headers
    results_tree.column("#0", width=0, stretch=tk.NO)
    results_tree.heading("#0", text="", anchor="w")
    for col in headers:
        results_tree.column(col, anchor="center", width=150 if col == "Parametre" else 120)
        results_tree.heading(col, text=col, anchor="center")
    
    params = list(results_history[0].keys())
    for i, param in enumerate(params):
        values = [param] + [result[param] for result in results_history[-max_rows:]]
        results_tree.insert("", "end", values=values)

def export_to_excel():
    if not results_history:
        messagebox.showwarning("Uyarı", "Export edilecek veri yok!")
        return
    
    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
    if file_path:
        df = pd.DataFrame(results_history)
        df.to_excel(file_path, index=False)
        messagebox.showinfo("Başarılı", f"Veriler '{file_path}' dosyasına kaydedildi.")

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
        materials[name] = {
            'E': E,
            'yield_strength': yield_strength,
            'ultimate_strength': ultimate_strength,
            'poisson_ratio': poisson_ratio,
            'percent_elongation': percent_elongation,
            'density': density
        }
        current_material = name
        material_var.set(name)
        material_entry['values'] = list(materials.keys())
        clear_material_inputs()
        update_material_table()
        plot_stress_strain(name)
    except ValueError as e:
        messagebox.showerror("Giriş Hatası", str(e))

def new_material():
    global current_material
    current_material = None
    clear_material_inputs()

def delete_material():
    global current_material
    selected = material_tree.selection()
    if selected:
        name = material_tree.item(selected[0])['values'][0]  # İlk sütundan malzeme adını al
        if name in materials:
            del materials[name]
            material_var.set('Steel' if 'Steel' in materials else list(materials.keys())[0] if materials else '')
            if current_material == name:
                current_material = None
                clear_material_inputs()
            update_material_table()

def on_material_select(event):
    global current_material
    selected = material_tree.selection()
    if selected:
        name = material_tree.item(selected[0])['values'][0]  # İlk sütundan malzeme adını al
        material = materials.get(name)
        if material:
            current_material = name
            material_name_var.set(name)
            material_E_var.set(str(material['E'] / 1000))
            material_yield_var.set(str(material['yield_strength']))
            material_ultimate_var.set(str(material['ultimate_strength']))
            material_poisson_var.set(str(material['poisson_ratio']))
            material_elongation_var.set(str(material['percent_elongation']) if material['percent_elongation'] is not None else "")
            material_density_var.set(str(material['density']))
            update_material_table()

def clear_material_inputs():
    material_name_var.set("")
    material_E_var.set("")
    material_yield_var.set("")
    material_ultimate_var.set("")
    material_poisson_var.set("")
    material_elongation_var.set("")
    material_density_var.set("")
    update_material_table()

def update_material_table():
    for item in material_tree.get_children():
        material_tree.delete(item)
    
    headers = ["Malzeme Adı", "Elastiklik Modülü (GPa)", "Verim Dayanımı (MPa)", "Nihai Dayanım (MPa)", "Poisson Oranı", "Uzama Yüzdesi (%)", "Yoğunluk (g/cm³)"]
    material_tree["columns"] = headers
    material_tree.column("#0", width=0, stretch=tk.NO)
    material_tree.heading("#0", text="", anchor="w")
    for col in headers:
        material_tree.column(col, anchor="w", width=120)
        material_tree.heading(col, text=col, anchor="w")
    
    for name, props in materials.items():
        values = [
            name,
            str(props['E'] / 1000),
            str(props['yield_strength']),
            str(props['ultimate_strength']),
            str(props['poisson_ratio']),
            str(props['percent_elongation']) if props['percent_elongation'] is not None else "",
            str(props['density'])
        ]
        material_tree.insert("", "end", values=values)

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
    ax.plot(strain, stress, marker='o', label=f'{material_name} Stress-Strain', color='#2196F3')
    ax.set_xlabel('Strain (mm/mm)')
    ax.set_ylabel('Stress (MPa)')
    ax.set_title(f'{material_name} Stress-Strain Eğrisi')
    ax.grid(True)
    ax.legend()
    
    plot_window = tk.Toplevel(root)
    plot_window.title("Stress-Strain Eğrisi")
    canvas = FigureCanvasTkAgg(fig, master=plot_window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

def render_latex_to_image(latex_text):
    fig, ax = plt.subplots(figsize=(len(latex_text) * 0.1 + 1, 1), dpi=100)
    ax.text(0.5, 0.5, f"${latex_text}$", fontsize=12, ha='center', va='center', color='#333333')
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
    widget.image_list = []  # Resimleri saklamak için liste
    
    lines = text.split('\n')
    for line in lines:
        if line.strip().startswith('#'):
            # Markdown başlıklarını işleme
            level = line.count('#')
            text = line.strip('# ').strip()
            widget.insert(tk.END, text + '\n', f"h{level}")
        elif line.strip().startswith('$$') and line.strip().endswith('$$'):
            # LaTeX formülleri
            latex_text = line.strip().strip('$$').strip()
            try:
                image = render_latex_to_image(latex_text)
                widget.image_list.append(image)
                widget.image_create(tk.END, image=image)
                widget.insert(tk.END, '\n')
            except Exception as e:
                widget.insert(tk.END, f"[LaTeX Hatası: {str(e)}]\n")
        else:
            # Normal metin
            widget.insert(tk.END, line + '\n')
    
    # Markdown başlık stilleri
    widget.tag_configure("h1", font=("Arial", 16, "bold"))
    widget.tag_configure("h2", font=("Arial", 14, "bold"))
    widget.tag_configure("h3", font=("Arial", 12, "bold"))
    widget.config(state="disabled")

# Popup window for defining parameter ranges
def define_range(param_var, param_name, is_numeric=True):
    popup = tk.Toplevel(root)
    popup.title(f"{param_name} Tanımla")
    popup.geometry("300x200")
    
    if is_numeric:
        tk.Label(popup, text="Başlangıç:").grid(row=0, column=0, padx=5, pady=5)
        start_var = tk.StringVar()
        tk.Entry(popup, textvariable=start_var).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(popup, text="Bitiş:").grid(row=1, column=0, padx=5, pady=5)
        end_var = tk.StringVar()
        tk.Entry(popup, textvariable=end_var).grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(popup, text="Adım:").grid(row=2, column=0, padx=5, pady=5)
        step_var = tk.StringVar()
        tk.Entry(popup, textvariable=step_var).grid(row=2, column=1, padx=5, pady=5)
        
        def apply_range():
            try:
                start = float(start_var.get())
                end = float(end_var.get())
                step = float(step_var.get())
                if step <= 0:
                    raise ValueError("Adım değeri pozitif olmalıdır.")
                values = np.arange(start, end + step, step)
                param_var.set(','.join(map(str, values)))
                popup.destroy()
            except ValueError as e:
                messagebox.showerror("Hata", str(e) or "Geçersiz giriş.")
        
        ttk.Button(popup, text="Uygula", command=apply_range).grid(row=3, column=0, columnspan=2, pady=10)
    else:
        tk.Label(popup, text="Değerler (virgülle ayrılmış):").grid(row=0, column=0, padx=5, pady=5)
        list_var = tk.StringVar()
        tk.Entry(popup, textvariable=list_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        def apply_list():
            param_var.set(list_var.get())
            popup.destroy()
        
        ttk.Button(popup, text="Uygula", command=apply_list).grid(row=1, column=0, columnspan=2, pady=10)

# Parametrik analiz fonksiyonu
def run_parametric_analysis():
    global parametric_results
    # Get input values
    bolt_size_vals = param_bolt_size_var.get().split(',') if param_bolt_size_var.get() else [bolt_size_var.get()]
    shank_length_vals = param_shank_length_var.get().split(',') if param_shank_length_var.get() else [shank_length_var.get()]
    thread_length_vals = param_thread_length_var.get().split(',') if param_thread_length_var.get() else [thread_length_var.get()]
    preload_percent_vals = param_preload_percent_var.get().split(',') if param_preload_percent_var.get() else [preload_percent_var.get()]
    tensile_force_vals = param_tensile_force_var.get().split(',') if param_tensile_force_var.get() else [tensile_force_var.get()]
    
    # Convert to appropriate types
    bolt_size_vals = [v.strip() for v in bolt_size_vals]
    shank_length_vals = [float(v.strip()) for v in shank_length_vals]
    thread_length_vals = [float(v.strip()) for v in thread_length_vals]
    preload_percent_vals = [float(v.strip()) for v in preload_percent_vals]
    tensile_force_vals = [float(v.strip()) for v in tensile_force_vals]
    
    # Generate all combinations
    combinations = list(product(bolt_size_vals, shank_length_vals, thread_length_vals, preload_percent_vals, tensile_force_vals))
    parametric_results = []
    
    for combo in combinations:
        bolt_size_var.set(combo[0])
        shank_length_var.set(str(combo[1]))
        thread_length_var.set(str(combo[2]))
        preload_percent_var.set(str(combo[3]))
        tensile_force_var.set(str(combo[4]))
        calculate_stiffness()
        if results_history:
            result = results_history[-1].copy()
            result['Cıvata Boyutu'] = combo[0]
            result['Gövde Uzunluğu'] = combo[1]
            result['Dişli Kısım Uzunluğu'] = combo[2]
            result['Ön Yükleme Yüzdesi'] = combo[3]
            result['Çekme Kuvveti'] = combo[4]
            parametric_results.append(result)
    
    # Find optimal combination (highest safety factor)
    if parametric_results:
        safety_key = f"Güvenlik Faktörü ({safety_basis_var.get()})"
        optimal_result = max(parametric_results, key=lambda x: float(x[safety_key]))
        optimal_combo = (optimal_result['Cıvata Boyutu'], optimal_result['Gövde Uzunluğu'], 
                         optimal_result['Dişli Kısım Uzunluğu'], optimal_result['Ön Yükleme Yüzdesi'], 
                         optimal_result['Çekme Kuvveti'])
        messagebox.showinfo("Optimal Kombinasyon", f"En verimli kombinasyon: {optimal_combo}\nGüvenlik Faktörü: {optimal_result[safety_key]}")
    
    # Update parametric results table
    for item in para_results_tree.get_children():
        para_results_tree.delete(item)
    
    if not parametric_results:
        return
    
    headers = ['Cıvata Boyutu', 'Gövde Uzunluğu', 'Dişli Kısım Uzunluğu', 'Ön Yükleme Yüzdesi', 'Çekme Kuvveti'] + list(parametric_results[0].keys())
    para_results_tree["columns"] = headers
    for col in headers:
        para_results_tree.column(col, anchor="center", width=120)
        para_results_tree.heading(col, text=col, anchor="center")
    
    for result in parametric_results:
        values = [result['Cıvata Boyutu'], result['Gövde Uzunluğu'], result['Dişli Kısım Uzunluğu'], 
                  result['Ön Yükleme Yüzdesi'], result['Çekme Kuvveti']] + list(result.values())
        para_results_tree.insert("", "end", values=values)

# Grafik çizme fonksiyonu
def draw_parametric_graph():
    global para_canvas, parametric_results
    if not parametric_results:
        messagebox.showwarning("Uyarı", "Önce parametrik analiz yapmalısınız!")
        return
    
    selected_param = param_to_graph_var.get()
    safety_key = f"Güvenlik Faktörü ({safety_basis_var.get()})"
    
    # Group results by selected parameter and calculate average safety factor
    grouped_data = {}
    for result in parametric_results:
        param_value = result[selected_param]
        if param_value not in grouped_data:
            grouped_data[param_value] = []
        grouped_data[param_value].append(float(result[safety_key]))
    
    x_values = list(grouped_data.keys())
    y_values = [sum(values) / len(values) for values in grouped_data.values()]
    
    # Determine graph type based on parameter
    is_numeric = selected_param in ['Gövde Uzunluğu', 'Dişli Kısım Uzunluğu', 'Ön Yükleme Yüzdesi', 'Çekme Kuvveti']
    
    if para_canvas:
        para_canvas.get_tk_widget().destroy()
    
    fig, ax = plt.subplots(figsize=(6, 4))
    if is_numeric:
        # Convert x_values to float for numeric parameters
        x_values = [float(x) for x in x_values]
        ax.plot(x_values, y_values, marker='o', label='Ortalama Güvenlik Faktörü', color='blue')
    else:
        ax.bar(x_values, y_values, color='blue', label='Ortalama Güvenlik Faktörü')
    
    ax.set_xlabel(selected_param)
    ax.set_ylabel('Ortalama Güvenlik Faktörü')
    ax.set_title(f'{selected_param} vs Güvenlik Faktörü')
    ax.grid(True)
    ax.legend()
    
    para_canvas = FigureCanvasTkAgg(fig, master=para_plot_frame)
    para_canvas.draw()
    para_canvas.get_tk_widget().pack(fill='both', expand=True)

# Ana pencere
root = tk.Tk()
root.title("Cıvata Sertliği Hesaplayıcısı")
root.geometry("900x700")
root.configure(bg="#F0F0F0")

# Tema ayarı
style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", background="#F0F0F0", foreground="#333333", padding=5)
style.map("TButton", background=[("active", "#E0E0E0")])
style.configure("TFrame", background="#F0F0F0")
style.configure("TLabel", background="#F0F0F0", foreground="#333333")

# Notebook
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both', padx=10, pady=10)

# Hesaplama sekmesi
calc_frame = ttk.Frame(notebook)
notebook.add(calc_frame, text="Hesaplama")

# Giriş ve seçenekler çerçevesi
input_options_frame = ttk.Frame(calc_frame)
input_options_frame.pack(side="left", fill='y', padx=10, pady=5)

# Giriş alanı
input_frame = ttk.Frame(input_options_frame)
input_frame.pack(fill='x', pady=5)

tk.Label(input_frame, text="Cıvata Boyutu:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
bolt_size_var = tk.StringVar()
bolt_size_entry = ttk.Combobox(input_frame, textvariable=bolt_size_var, values=list(bolt_sizes.keys()), width=15)
bolt_size_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")
ToolTip(bolt_size_entry, "Cıvata boyutu, örneğin M10.")

tk.Label(input_frame, text="Gövde Uzunluğu (mm):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
shank_length_var = tk.StringVar()
shank_length_entry = tk.Entry(input_frame, textvariable=shank_length_var, width=20, bg="#FFFFFF", fg="#333333")
shank_length_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
ToolTip(shank_length_entry, "Cıvatanın düz kısmının uzunluğu (mm).")

tk.Label(input_frame, text="Dişli Kısım Uzunluğu (mm):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
thread_length_var = tk.StringVar()
thread_length_entry = tk.Entry(input_frame, textvariable=thread_length_var, width=20, bg="#FFFFFF", fg="#333333")
thread_length_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
ToolTip(thread_length_entry, "Dişli kısım uzunluğu, yoksa 0.")

tk.Label(input_frame, text="Malzeme:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
material_var = tk.StringVar(value='Steel')
material_entry = ttk.Combobox(input_frame, textvariable=material_var, values=list(materials.keys()), width=18, state="readonly")
material_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
ToolTip(material_entry, "Cıvata malzemesi, elastiklik modülü ve dayanımı belirler.")

tk.Label(input_frame, text="Ön Yükleme Yüzdesi (%):").grid(row=4, column=0, padx=10, pady=5, sticky="e")
preload_percent_var = tk.StringVar(value='67')
preload_percent_entry = tk.Entry(input_frame, textvariable=preload_percent_var, width=20, bg="#FFFFFF", fg="#333333")
preload_percent_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
ToolTip(preload_percent_entry, "Ön yükleme, verim dayanımının yüzdesi (0-100).")

tk.Label(input_frame, text="Çekme Kuvveti (N):").grid(row=5, column=0, padx=10, pady=5, sticky="e")
tensile_force_var = tk.StringVar()
tensile_force_entry = tk.Entry(input_frame, textvariable=tensile_force_var, width=20, bg="#FFFFFF", fg="#333333")
tensile_force_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")
ToolTip(tensile_force_entry, "Cıvatalı birleşmeye uygulanan çekme kuvveti (N).")

tk.Label(input_frame, text="Kesme Kuvveti (N):").grid(row=6, column=0, padx=10, pady=5, sticky="e")
shear_force_var = tk.StringVar()
shear_force_entry = tk.Entry(input_frame, textvariable=shear_force_var, width=20, bg="#FFFFFF", fg="#333333")
shear_force_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")
ToolTip(shear_force_entry, "Cıvatalı birleşmeye yanlara uygulanan kesme kuvveti (N).")

# Kesme alanı seçimi (küçültülmüş)
shear_frame = ttk.LabelFrame(input_options_frame, text="Kesme Alanı", padding=2)
shear_frame.pack(fill='x', pady=5)
shear_area_var = tk.StringVar(value="Thread")
ttk.Radiobutton(shear_frame, text="Gövde", variable=shear_area_var, value="Shank").pack(side="left", padx=2)
ttk.Radiobutton(shear_frame, text="Dişli", variable=shear_area_var, value="Thread").pack(side="left", padx=2)

# Güvenlik faktörü temeli (küçültülmüş)
safety_frame = ttk.LabelFrame(input_options_frame, text="Güvenlik Faktörü", padding=2)
safety_frame.pack(fill='x', pady=5)
safety_basis_var = tk.StringVar(value="Yield")
ttk.Radiobutton(safety_frame, text="Verim", variable=safety_basis_var, value="Yield").pack(side="left", padx=2)
ttk.Radiobutton(safety_frame, text="Nihai", variable=safety_basis_var, value="Ultimate").pack(side="left", padx=2)

# Sıkıştırılan parçalar
clamped_frame = ttk.LabelFrame(input_options_frame, text="Sıkıştırılan Parçalar", padding=5)
clamped_frame.pack(fill='x', pady=5)
clamped_parts_frame = ttk.Frame(clamped_frame)
clamped_parts_frame.pack(fill='x')
ttk.Button(clamped_frame, text="Parça Ekle", command=add_clamped_part, style="Accent.TButton").pack(side="right", padx=5, pady=5)

# Butonlar
button_frame = ttk.Frame(input_options_frame)
button_frame.pack(fill='x', pady=10)
ttk.Button(button_frame, text="Hesapla", command=calculate_stiffness, style="Accent.TButton").pack(side="left", padx=5)
style.configure("Accent.TButton", background="#4CAF50", foreground="white")
style.map("Accent.TButton", background=[("active", "#45A049")])
ttk.Button(button_frame, text="Temizle", command=clear_inputs, style="Danger.TButton").pack(side="left", padx=5)
style.configure("Danger.TButton", background="#F44336", foreground="white")
style.map("Danger.TButton", background=[("active", "#D32F2F")])
ttk.Button(button_frame, text="Test", command=test_values, style="Test.TButton").pack(side="left", padx=5)
style.configure("Test.TButton", background="#FF9800", foreground="white")
style.map("Test.TButton", background=[("active", "#F57C00")])

# Sağ taraf: Tablo ve Grafik
right_frame = ttk.Frame(calc_frame)
right_frame.pack(side="right", fill='both', expand=True, padx=10, pady=5)

# Sonuçlar Tablosu
result_frame = ttk.LabelFrame(right_frame, text="Sonuçlar Tablosu", padding=5)
result_frame.pack(fill='x', pady=5)
rows_frame = ttk.Frame(result_frame)
rows_frame.pack(fill='x', pady=5)
tk.Label(rows_frame, text="Gösterilecek Hesaplama Sayısı:").pack(side="left", padx=5)
max_rows_var = tk.StringVar(value=str(max_rows))
tk.Entry(rows_frame, textvariable=max_rows_var, width=5).pack(side="left", padx=5)
ttk.Button(rows_frame, text="Güncelle", command=update_results_table).pack(side="left", padx=5)
ttk.Button(rows_frame, text="Excel'e Aktar", command=export_to_excel, style="Export.TButton").pack(side="left", padx=5)
style.configure("Export.TButton", background="#3F51B5", foreground="white")
style.map("Export.TButton", background=[("active", "#303F9F")])
ttk.Button(rows_frame, text="Temizle", command=clear_results, style="Danger.TButton").pack(side="left", padx=5)

results_tree = ttk.Treeview(result_frame, height=7, show="headings")
results_tree.pack(fill='x')
scrollbar = ttk.Scrollbar(result_frame, orient="horizontal", command=results_tree.xview)
scrollbar.pack(side="bottom", fill="x")
results_tree.configure(xscrollcommand=scrollbar.set)

# Yük-Çarpılma Grafiği
plot_frame = ttk.LabelFrame(right_frame, text="Yük-Çarpılma Eğrisi", padding=5)
plot_frame.pack(fill='both', expand=True)

# Malzeme Kütüphanesi sekmesi
material_frame = ttk.Frame(notebook)
notebook.add(material_frame, text="Malzeme Kütüphanesi")

# Malzeme giriş ve tablo çerçevesi
material_input_frame = ttk.Frame(material_frame)
material_input_frame.pack(fill='both', expand=True, padx=5, pady=5)

# Giriş alanları
input_subframe = ttk.Frame(material_input_frame)
input_subframe.pack(fill='x', pady=5)

tk.Label(input_subframe, text="Malzeme Adı *:").grid(row=0, column=0, padx=5, pady=2, sticky="e")
material_name_var = tk.StringVar()
material_name_entry = tk.Entry(input_subframe, textvariable=material_name_var, width=20, bg="#FFFFFF", fg="#333333")
material_name_entry.grid(row=0, column=1, padx=5, pady=2)
ToolTip(material_name_entry, "Malzeme adı, örneğin '316 Stainless Steel'.")

tk.Label(input_subframe, text="Elastiklik Modülü (GPa) *:").grid(row=1, column=0, padx=5, pady=2, sticky="e")
material_E_var = tk.StringVar()
material_E_entry = tk.Entry(input_subframe, textvariable=material_E_var, width=20, bg="#FFFFFF", fg="#333333")
material_E_entry.grid(row=1, column=1, padx=5, pady=2)
ToolTip(material_E_entry, "Malzemenin elastiklik modülü (GPa), örneğin 200.")

tk.Label(input_subframe, text="Verim Dayanımı (MPa) *:").grid(row=2, column=0, padx=5, pady=2, sticky="e")
material_yield_var = tk.StringVar()
material_yield_entry = tk.Entry(input_subframe, textvariable=material_yield_var, width=20, bg="#FFFFFF", fg="#333333")
material_yield_entry.grid(row=2, column=1, padx=5, pady=2)
ToolTip(material_yield_entry, "Malzemenin verim dayanımı (MPa), örneğin 200.")

tk.Label(input_subframe, text="Nihai Dayanım (MPa) *:").grid(row=3, column=0, padx=5, pady=2, sticky="e")
material_ultimate_var = tk.StringVar()
material_ultimate_entry = tk.Entry(input_subframe, textvariable=material_ultimate_var, width=20, bg="#FFFFFF", fg="#333333")
material_ultimate_entry.grid(row=3, column=1, padx=5, pady=2)
ToolTip(material_ultimate_entry, "Malzemenin nihai dayanımı (MPa), örneğin 530.")

tk.Label(input_subframe, text="Poisson Oranı:").grid(row=4, column=0, padx=5, pady=2, sticky="e")
material_poisson_var = tk.StringVar()
material_poisson_entry = tk.Entry(input_subframe, textvariable=material_poisson_var, width=20, bg="#FFFFFF", fg="#333333")
material_poisson_entry.grid(row=4, column=1, padx=5, pady=2)
ToolTip(material_poisson_entry, "Malzemenin Poisson oranı, örneğin 0.28.")

tk.Label(input_subframe, text="Uzama Yüzdesi (%):").grid(row=5, column=0, padx=5, pady=2, sticky="e")
material_elongation_var = tk.StringVar()
material_elongation_entry = tk.Entry(input_subframe, textvariable=material_elongation_var, width=20, bg="#FFFFFF", fg="#333333")
material_elongation_entry.grid(row=5, column=1, padx=5, pady=2)
ToolTip(material_elongation_entry, "Malzemenin uzama yüzdesi, örneğin 40.")

tk.Label(input_subframe, text="Yoğunluk (g/cm³):").grid(row=6, column=0, padx=5, pady=2, sticky="e")
material_density_var = tk.StringVar()
material_density_entry = tk.Entry(input_subframe, textvariable=material_density_var, width=20, bg="#FFFFFF", fg="#333333")
material_density_entry.grid(row=6, column=1, padx=5, pady=2)
ToolTip(material_density_entry, "Malzemenin yoğunluğu (g/cm³), örneğin 8.0.")

# Malzeme tablosu
material_tree_frame = ttk.LabelFrame(material_input_frame, text="Malzeme Özellikleri", padding=5)
material_tree_frame.pack(fill='both', expand=True, pady=5)
material_tree = ttk.Treeview(material_tree_frame, show="headings")
material_tree.pack(fill='both', expand=True)
scrollbar = ttk.Scrollbar(material_tree_frame, orient="vertical", command=material_tree.yview)
scrollbar.pack(side="right", fill="y")
material_tree.configure(yscrollcommand=scrollbar.set)
update_material_table()

# Butonlar
material_button_frame = ttk.Frame(material_input_frame)
material_button_frame.pack(fill='x', pady=5)
ttk.Button(material_button_frame, text="Kaydet", command=save_material, style="Accent.TButton").pack(side="left", padx=5)
ttk.Button(material_button_frame, text="Yeni", command=new_material, style="TButton").pack(side="left", padx=5)
ttk.Button(material_button_frame, text="Sil", command=delete_material, style="Danger.TButton").pack(side="left", padx=5)

# Parametrik Hesaplama sekmesi
parametric_frame = ttk.Frame(notebook)
notebook.add(parametric_frame, text="Parametrik Hesaplama")

para_input_frame = ttk.Frame(parametric_frame)
para_input_frame.pack(fill='x', padx=10, pady=5)

# Side-by-side parameter inputs with "Tanımla" buttons
tk.Label(para_input_frame, text="Cıvata Boyutu:").grid(row=0, column=0, padx=5, pady=5)
param_bolt_size_var = tk.StringVar()
param_bolt_size_entry = tk.Entry(para_input_frame, textvariable=param_bolt_size_var, width=20)
param_bolt_size_entry.grid(row=0, column=1, padx=5)
ttk.Button(para_input_frame, text="Tanımla", command=lambda: define_range(param_bolt_size_var, "Cıvata Boyutu", is_numeric=False)).grid(row=0, column=2, padx=5)
ToolTip(param_bolt_size_entry, "örn: M6,M8,M10")

tk.Label(para_input_frame, text="Gövde Uzunluğu (mm):").grid(row=0, column=3, padx=5, pady=5)
param_shank_length_var = tk.StringVar()
param_shank_length_entry = tk.Entry(para_input_frame, textvariable=param_shank_length_var, width=20)
param_shank_length_entry.grid(row=0, column=4, padx=5)
ttk.Button(para_input_frame, text="Tanımla", command=lambda: define_range(param_shank_length_var, "Gövde Uzunluğu")).grid(row=0, column=5, padx=5)
ToolTip(param_shank_length_entry, "örn: 20,30,40 veya 10-20 adım 2")

tk.Label(para_input_frame, text="Dişli Kısım Uzunluğu (mm):").grid(row=0, column=6, padx=5, pady=5)
param_thread_length_var = tk.StringVar()
param_thread_length_entry = tk.Entry(para_input_frame, textvariable=param_thread_length_var, width=20)
param_thread_length_entry.grid(row=0, column=7, padx=5)
ttk.Button(para_input_frame, text="Tanımla", command=lambda: define_range(param_thread_length_var, "Dişli Kısım Uzunluğu")).grid(row=0, column=8, padx=5)
ToolTip(param_thread_length_entry, "örn: 10,15,20 veya 10-20 adım 5")

tk.Label(para_input_frame, text="Ön Yükleme Yüzdesi (%):").grid(row=1, column=0, padx=5, pady=5)
param_preload_percent_var = tk.StringVar()
param_preload_percent_entry = tk.Entry(para_input_frame, textvariable=param_preload_percent_var, width=20)
param_preload_percent_entry.grid(row=1, column=1, padx=5)
ttk.Button(para_input_frame, text="Tanımla", command=lambda: define_range(param_preload_percent_var, "Ön Yükleme Yüzdesi")).grid(row=1, column=2, padx=5)
ToolTip(param_preload_percent_entry, "örn: 60,70,80 veya 50-90 adım 10")

tk.Label(para_input_frame, text="Çekme Kuvveti (N):").grid(row=1, column=3, padx=5, pady=5)
param_tensile_force_var = tk.StringVar()
param_tensile_force_entry = tk.Entry(para_input_frame, textvariable=param_tensile_force_var, width=20)
param_tensile_force_entry.grid(row=1, column=4, padx=5)
ttk.Button(para_input_frame, text="Tanımla", command=lambda: define_range(param_tensile_force_var, "Çekme Kuvveti")).grid(row=1, column=5, padx=5)
ToolTip(param_tensile_force_entry, "örn: 5000,10000 veya 5000-15000 adım 5000")

ttk.Button(para_input_frame, text="Hesapla", command=run_parametric_analysis, style="Accent.TButton").grid(row=2, column=0, columnspan=9, pady=5)

para_results_frame = ttk.LabelFrame(parametric_frame, text="Parametrik Sonuçlar", padding=5)
para_results_frame.pack(fill='x', padx=10, pady=5)
para_results_tree = ttk.Treeview(para_results_frame, show="headings", height=7)
para_results_tree.pack(fill='x')
para_scrollbar = ttk.Scrollbar(para_results_frame, orient="horizontal", command=para_results_tree.xview)
para_scrollbar.pack(side="bottom", fill="x")
para_results_tree.configure(xscrollcommand=para_scrollbar.set)

# Graph selection and drawing
para_graph_frame = ttk.Frame(para_results_frame)
para_graph_frame.pack(fill='x', pady=5)
tk.Label(para_graph_frame, text="Grafik Parametresi:").pack(side="left", padx=5)
param_to_graph_var = tk.StringVar()
ttk.Combobox(para_graph_frame, textvariable=param_to_graph_var, values=['Cıvata Boyutu', 'Gövde Uzunluğu', 'Dişli Kısım Uzunluğu', 'Ön Yükleme Yüzdesi', 'Çekme Kuvveti'], width=20).pack(side="left", padx=5)
ttk.Button(para_graph_frame, text="Grafik Çiz", command=draw_parametric_graph).pack(side="left", padx=5)

para_plot_frame = ttk.LabelFrame(parametric_frame, text="Parametrik Grafik", padding=5)
para_plot_frame.pack(fill='both', expand=True, padx=10, pady=5)

# Wiki sekmesi
wiki_frame = ttk.Frame(notebook)
notebook.add(wiki_frame, text="Bilgi")

wiki_text_widget = tk.Text(wiki_frame, wrap="word", state="disabled", bg="#FFFFFF", fg="#333333")
wiki_text_widget.pack(fill="both", expand=True, padx=10, pady=10)
wiki_scrollbar = ttk.Scrollbar(wiki_frame, command=wiki_text_widget.yview)
wiki_scrollbar.pack(side="right", fill="y")
wiki_text_widget.config(yscrollcommand=wiki_scrollbar.set)
render_wiki_text(wiki_text_widget, wiki_text)

# Uygulamayı çalıştır
root.mainloop()