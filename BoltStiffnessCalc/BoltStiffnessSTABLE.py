import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io
import numpy as np
import pandas as pd
from itertools import product
import threading
import queue
import sqlite3
import os
import json

# Cıvata boyutları ve malzeme özellikleri
bolt_sizes = {
    'M6': {'A_shank': 28.27, 'A_thread': 20.1},
    'M8': {'A_shank': 50.27, 'A_thread': 36.6},
    'M10': {'A_shank': 78.54, 'A_thread': 58.0},
    'M12': {'A_shank': 113.10, 'A_thread': 84.3},
    'M14': {'A_shank': 153.94, 'A_thread': 114.8},
    'M16': {'A_shank': 201.06, 'A_thread': 157.1},
}
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
parametric_clamped_parts_frames = []  # Parametrik hesaplama için bağımsız parça listesi
results_history = []
max_rows = 5
canvas = None
para_canvas = None
parametric_results = []
analysis_queue = queue.Queue()
cancel_flag = threading.Event()
db_path = "parametric_results.db"
test_buttons = []
notebook = None
bolt_size_var = None
shank_length_var = None
thread_length_var = None
material_var = None
preload_percent_var = None
tensile_force_var = None
shear_force_var = None
shear_area_var = None
safety_basis_var = None
clamped_parts_frame = None
results_tree = None
material_tree = None
para_results_tree = None
param_to_graph_var = None
progress_bar = None
progress_label = None
optimal_label = None
para_plot_frame = None
plot_frame = None
material_entry = None
max_rows_var = None
param_bolt_size_var = None
param_shank_length_var = None
param_thread_length_var = None
param_preload_percent_var = None
param_tensile_force_var = None

# Dil desteği için sözlük
dil_sozlugu = {
    "tr": {
        "hesaplama": "Hesaplama",
        "parametre_tanimlama": "Parametre Tanımlama",
        "civata_boyutu": "Cıvata Boyutu:",
        "govde_uzunlugu": "Gövde Uzunluğu (mm):",
        "disli_kisim_uzunlugu": "Dişli Kısım Uzunluğu (mm):",
        "malzeme": "Malzeme:",
        "on_yukleme_yuzdesi": "Ön Yükleme Yüzdesi (%):",
        "cekme_kuvveti": "Çekme Kuvveti (N):",
        "kesme_kuvveti": "Kesme Kuvveti (N):",
        "kesme_alani": "Kesme Alanı",
        "govde": "Gövde",
        "disli": "Dişli",
        "guvenlik_faktoru": "Güvenlik Faktörü",
        "verim": "Verim",
        "nihai": "Nihai",
        "parca_ekle": "Parça Ekle",
        "hesapla": "Hesapla",
        "temizle": "Temizle",
        "test": "Test",
        "sonuclar_tablosu": "Sonuçlar Tablosu",
        "gosterilecek_hesaplama_sayisi": "Gösterilecek Hesaplama Sayısı:",
        "guncelle": "Güncelle",
        "excel_aktar": "Excel'e Aktar",
        "yuk_carpilma_egrisi": "Yük-Çarpılma Eğrisi",
        "malzeme_kutuphanesi": "Malzeme Kütüphanesi",
        "malzeme_adi": "Malzeme Adı *:",
        "elastiklik_modulu": "Elastiklik Modülü (GPa) *:",
        "verim_dayanimi": "Verim Dayanımı (MPa) *:",
        "nihai_dayanimi": "Nihai Dayanım (MPa) *:",
        "poisson_orani": "Poisson Oranı:",
        "uzama_yuzdesi": "Uzama Yüzdesi (%):",
        "yogunluk": "Yoğunluk (g/cm³):",
        "malzeme_ozellikleri": "Malzeme Özellikleri",
        "kaydet": "Kaydet",
        "yeni": "Yeni",
        "sil": "Sil",
        "parametrik_hesaplama": "Parametrik Hesaplama",
        "iptal_et": "İptal Et",
        "en_optimal_kombinasyon": "En Optimal Kombinasyon",
        "parametrik_sonuclar": "Parametrik Sonuçlar",
        "grafik_parametresi": "Grafik Parametresi:",
        "grafik_ciz": "Grafik Çiz",
        "optimal_grafik_ciz": "Optimal Grafik Çiz",
        "parametrik_grafik": "Parametrik Grafik",
        "bilgi": "Bilgi",
        "ayarlar": "Ayarlar",
        "dil_secimi": "Dil Seçimi",
        "gelistirici_modu": "Geliştirici Modu",
        "test_degerleri_yuklendi": "Test değerleri yüklendi. 'Hesapla' butonuna basarak sonuçları görebilirsiniz.",
        "sıkıştırılan_parca_tanimlama": "Sıkıştırılan Parça Tanımlama"
    },
    "en": {
        "hesaplama": "Calculation",
        "parametre_tanimlama": "Parameter Definition",
        "civata_boyutu": "Bolt Size:",
        "govde_uzunlugu": "Shank Length (mm):",
        "disli_kisim_uzunlugu": "Thread Length (mm):",
        "malzeme": "Material:",
        "on_yukleme_yuzdesi": "Preload Percentage (%):",
        "cekme_kuvveti": "Tensile Force (N):",
        "kesme_kuvveti": "Shear Force (N):",
        "kesme_alani": "Shear Area",
        "govde": "Shank",
        "disli": "Thread",
        "guvenlik_faktoru": "Safety Factor",
        "verim": "Yield",
        "nihai": "Ultimate",
        "parca_ekle": "Add Part",
        "hesapla": "Calculate",
        "temizle": "Clear",
        "test": "Test",
        "sonuclar_tablosu": "Results Table",
        "gosterilecek_hesaplama_sayisi": "Number of Calculations to Show:",
        "guncelle": "Update",
        "excel_aktar": "Export to Excel",
        "yuk_carpilma_egrisi": "Load-Deflection Curve",
        "malzeme_kutuphanesi": "Material Library",
        "malzeme_adi": "Material Name *:",
        "elastiklik_modulu": "Elastic Modulus (GPa) *:",
        "verim_dayanimi": "Yield Strength (MPa) *:",
        "nihai_dayanimi": "Ultimate Strength (MPa) *:",
        "poisson_orani": "Poisson's Ratio:",
        "uzama_yuzdesi": "Percent Elongation (%):",
        "yogunluk": "Density (g/cm³):",
        "malzeme_ozellikleri": "Material Properties",
        "kaydet": "Save",
        "yeni": "New",
        "sil": "Delete",
        "parametrik_hesaplama": "Parametric Calculation",
        "iptal_et": "Cancel",
        "en_optimal_kombinasyon": "Most Optimal Combination",
        "parametrik_sonuclar": "Parametric Results",
        "grafik_parametresi": "Graph Parameter:",
        "grafik_ciz": "Draw Graph",
        "optimal_grafik_ciz": "Draw Optimal Graph",
        "parametrik_grafik": "Parametric Graph",
        "bilgi": "Information",
        "ayarlar": "Settings",
        "dil_secimi": "Language Selection",
        "gelistirici_modu": "Developer Mode",
        "test_degerleri_yuklendi": "Test values loaded. Press 'Calculate' to see results.",
        "sıkıştırılan_parca_tanimlama": "Clamped Part Definition"
    }
}

# Geliştirici modu kontrolü
dev_mode = False
def toggle_dev_mode():
    global test_buttons
    for btn in test_buttons:
        if dev_mode:
            btn.pack(side="left", padx=5)
        else:
            btn.pack_forget()

# Konfigürasyon dosyası işlemleri
def load_config():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            return config["dil"], config["dev_mode"]
    except FileNotFoundError:
        return "tr", False

def save_config(dil, dev_mode):
    config = {"dil": dil, "dev_mode": dev_mode}
    with open("config.json", "w") as f:
        json.dump(config, f)

# ToolTip sınıfı
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

# Sekmeleri oluşturma fonksiyonu
def create_all_frames(dil, dev_mode_flag):
    global dev_mode, notebook
    dev_mode = dev_mode_flag
    for widget in notebook.winfo_children():
        widget.destroy()

    # Stil tanımlamaları
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TFrame", background="#F0F0F0")  # Açık gri arka plan
    style.configure("TLabel", background="#F0F0F0", foreground="#333333")  # Koyu gri yazı
    style.configure("TButton", background="#F0F0F0", foreground="#333333", padding=5)
    style.map("TButton", background=[("active", "#E0E0E0")])
    style.configure("Accent.TButton", background="#4CAF50", foreground="white")  # Yeşil
    style.map("Accent.TButton", background=[("active", "#45A049")])
    style.configure("Danger.TButton", background="#F44336", foreground="white")  # Kırmızı
    style.map("Danger.TButton", background=[("active", "#D32F2F")])
    style.configure("Test.TButton", background="#FF9800", foreground="white")  # Turuncu
    style.map("Test.TButton", background=[("active", "#F57C00")])
    style.configure("Export.TButton", background="#3F51B5", foreground="white")  # Mavi
    style.map("Export.TButton", background=[("active", "#303F9F")])
    root.configure(bg="#F0F0F0")

    # Hesaplama sekmesi
    calc_frame = ttk.Frame(notebook)
    notebook.add(calc_frame, text=dil_sozlugu[dil]["hesaplama"])
    create_calc_frame(calc_frame, dil)

    # Malzeme Kütüphanesi sekmesi
    material_frame = ttk.Frame(notebook)
    notebook.add(material_frame, text=dil_sozlugu[dil]["malzeme_kutuphanesi"])
    create_material_frame(material_frame, dil)

    # Parametrik Hesaplama sekmesi
    parametric_frame = ttk.Frame(notebook)
    notebook.add(parametric_frame, text=dil_sozlugu[dil]["parametrik_hesaplama"])
    create_parametric_frame(parametric_frame, dil)

    # Wiki sekmesi
    wiki_frame = ttk.Frame(notebook)
    notebook.add(wiki_frame, text=dil_sozlugu[dil]["bilgi"])
    create_wiki_frame(wiki_frame, dil)

    # Ayarlar sekmesi
    settings_frame = ttk.Frame(notebook)
    notebook.add(settings_frame, text=dil_sozlugu[dil]["ayarlar"])
    create_settings_frame(settings_frame, dil, dev_mode)

    toggle_dev_mode()

# Hesaplama sekmesi oluşturma
def create_calc_frame(parent, dil):
    global bolt_size_var, shank_length_var, thread_length_var, material_var, preload_percent_var, tensile_force_var, shear_force_var, shear_area_var, safety_basis_var, clamped_parts_frame, results_tree, plot_frame, material_entry, max_rows_var, test_buttons
    input_frame = ttk.LabelFrame(parent, text=dil_sozlugu[dil]["parametre_tanimlama"], padding=5)
    input_frame.pack(side="left", fill='y', padx=5, pady=5)

    tk.Label(input_frame, text=dil_sozlugu[dil]["civata_boyutu"]).grid(row=0, column=0, padx=10, pady=5, sticky="e")
    bolt_size_var = tk.StringVar()
    bolt_size_entry = ttk.Combobox(input_frame, textvariable=bolt_size_var, values=list(bolt_sizes.keys()), width=15)
    bolt_size_entry.grid(row=0, column=1, padx=10, pady=5)
    ToolTip(bolt_size_entry, dil_sozlugu[dil]["civata_boyutu"])

    tk.Label(input_frame, text=dil_sozlugu[dil]["govde_uzunlugu"]).grid(row=1, column=0, padx=10, pady=5, sticky="e")
    shank_length_var = tk.StringVar()
    tk.Entry(input_frame, textvariable=shank_length_var, width=20).grid(row=1, column=1, padx=10, pady=5)

    tk.Label(input_frame, text=dil_sozlugu[dil]["disli_kisim_uzunlugu"]).grid(row=2, column=0, padx=10, pady=5, sticky="e")
    thread_length_var = tk.StringVar()
    tk.Entry(input_frame, textvariable=thread_length_var, width=20).grid(row=2, column=1, padx=10, pady=5)

    tk.Label(input_frame, text=dil_sozlugu[dil]["malzeme"]).grid(row=3, column=0, padx=10, pady=5, sticky="e")
    material_var = tk.StringVar(value='Steel')
    material_entry = ttk.Combobox(input_frame, textvariable=material_var, values=list(materials.keys()), width=18, state="readonly")
    material_entry.grid(row=3, column=1, padx=10, pady=5)

    tk.Label(input_frame, text=dil_sozlugu[dil]["on_yukleme_yuzdesi"]).grid(row=4, column=0, padx=10, pady=5, sticky="e")
    preload_percent_var = tk.StringVar(value='67')
    tk.Entry(input_frame, textvariable=preload_percent_var, width=20).grid(row=4, column=1, padx=10, pady=5)

    tk.Label(input_frame, text=dil_sozlugu[dil]["cekme_kuvveti"]).grid(row=5, column=0, padx=10, pady=5, sticky="e")
    tensile_force_var = tk.StringVar()
    tk.Entry(input_frame, textvariable=tensile_force_var, width=20).grid(row=5, column=1, padx=10, pady=5)

    tk.Label(input_frame, text=dil_sozlugu[dil]["kesme_kuvveti"]).grid(row=6, column=0, padx=10, pady=5, sticky="e")
    shear_force_var = tk.StringVar()
    tk.Entry(input_frame, textvariable=shear_force_var, width=20).grid(row=6, column=1, padx=10, pady=5)

    shear_frame = ttk.LabelFrame(input_frame, text=dil_sozlugu[dil]["kesme_alani"], padding=2)
    shear_frame.grid(row=7, column=0, columnspan=2, pady=5)
    shear_area_var = tk.StringVar(value="Thread")
    ttk.Radiobutton(shear_frame, text=dil_sozlugu[dil]["govde"], variable=shear_area_var, value="Shank").pack(side="left", padx=2)
    ttk.Radiobutton(shear_frame, text=dil_sozlugu[dil]["disli"], variable=shear_area_var, value="Thread").pack(side="left", padx=2)

    safety_frame = ttk.LabelFrame(input_frame, text=dil_sozlugu[dil]["guvenlik_faktoru"], padding=2)
    safety_frame.grid(row=8, column=0, columnspan=2, pady=5)
    safety_basis_var = tk.StringVar(value="Yield")
    ttk.Radiobutton(safety_frame, text=dil_sozlugu[dil]["verim"], variable=safety_basis_var, value="Yield").pack(side="left", padx=2)
    ttk.Radiobutton(safety_frame, text=dil_sozlugu[dil]["nihai"], variable=safety_basis_var, value="Ultimate").pack(side="left", padx=2)

    clamped_parts_frame = ttk.Frame(input_frame)
    clamped_parts_frame.grid(row=9, column=0, columnspan=2, pady=5)
    ttk.Button(input_frame, text=dil_sozlugu[dil]["parca_ekle"], command=add_clamped_part, style="Accent.TButton").grid(row=10, column=0, columnspan=2, pady=5)

    button_frame = ttk.Frame(input_frame)
    button_frame.grid(row=11, column=0, columnspan=2, pady=10)
    ttk.Button(button_frame, text=dil_sozlugu[dil]["hesapla"], command=calculate_stiffness, style="Accent.TButton").pack(side="left", padx=5)
    ttk.Button(button_frame, text=dil_sozlugu[dil]["temizle"], command=clear_inputs, style="Danger.TButton").pack(side="left", padx=5)
    test_button = ttk.Button(button_frame, text=dil_sozlugu[dil]["test"], command=test_values, style="Test.TButton")
    test_button.pack(side="left", padx=5)
    test_buttons = [test_button]

    right_frame = ttk.Frame(parent)
    right_frame.pack(side="right", fill='both', expand=True, padx=10, pady=5)

    result_frame = ttk.LabelFrame(right_frame, text=dil_sozlugu[dil]["sonuclar_tablosu"], padding=5)
    result_frame.pack(fill='x', pady=5)
    rows_frame = ttk.Frame(result_frame)
    rows_frame.pack(fill='x', pady=5)
    tk.Label(rows_frame, text=dil_sozlugu[dil]["gosterilecek_hesaplama_sayisi"]).pack(side="left", padx=5)
    max_rows_var = tk.StringVar(value=str(max_rows))
    tk.Entry(rows_frame, textvariable=max_rows_var, width=5).pack(side="left", padx=5)
    ttk.Button(rows_frame, text=dil_sozlugu[dil]["guncelle"], command=update_results_table).pack(side="left", padx=5)
    ttk.Button(rows_frame, text=dil_sozlugu[dil]["excel_aktar"], command=export_to_excel, style="Export.TButton").pack(side="left", padx=5)
    ttk.Button(rows_frame, text=dil_sozlugu[dil]["temizle"], command=clear_results, style="Danger.TButton").pack(side="left", padx=5)

    results_tree = ttk.Treeview(result_frame, height=7, show="headings")
    results_tree.pack(fill='x')
    scrollbar = ttk.Scrollbar(result_frame, orient="horizontal", command=results_tree.xview)
    scrollbar.pack(side="bottom", fill="x")
    results_tree.configure(xscrollcommand=scrollbar.set)

    plot_frame = ttk.LabelFrame(right_frame, text=dil_sozlugu[dil]["yuk_carpilma_egrisi"], padding=5)
    plot_frame.pack(fill='both', expand=True)

# Malzeme Kütüphanesi sekmesi oluşturma
def create_material_frame(parent, dil):
    global material_tree
    material_input_frame = ttk.Frame(parent)
    material_input_frame.pack(fill='both', expand=True, padx=5, pady=5)

    input_subframe = ttk.Frame(material_input_frame)
    input_subframe.pack(fill='x', pady=5)

    tk.Label(input_subframe, text=dil_sozlugu[dil]["malzeme_adi"]).grid(row=0, column=0, padx=5, pady=2, sticky="e")
    material_name_var = tk.StringVar()
    material_name_entry = tk.Entry(input_subframe, textvariable=material_name_var, width=20)
    material_name_entry.grid(row=0, column=1, padx=5, pady=2)

    tk.Label(input_subframe, text=dil_sozlugu[dil]["elastiklik_modulu"]).grid(row=1, column=0, padx=5, pady=2, sticky="e")
    material_E_var = tk.StringVar()
    tk.Entry(input_subframe, textvariable=material_E_var, width=20).grid(row=1, column=1, padx=5, pady=2)

    tk.Label(input_subframe, text=dil_sozlugu[dil]["verim_dayanimi"]).grid(row=2, column=0, padx=5, pady=2, sticky="e")
    material_yield_var = tk.StringVar()
    tk.Entry(input_subframe, textvariable=material_yield_var, width=20).grid(row=2, column=1, padx=5, pady=2)

    tk.Label(input_subframe, text=dil_sozlugu[dil]["nihai_dayanimi"]).grid(row=3, column=0, padx=5, pady=2, sticky="e")
    material_ultimate_var = tk.StringVar()
    tk.Entry(input_subframe, textvariable=material_ultimate_var, width=20).grid(row=3, column=1, padx=5, pady=2)

    tk.Label(input_subframe, text=dil_sozlugu[dil]["poisson_orani"]).grid(row=4, column=0, padx=5, pady=2, sticky="e")
    material_poisson_var = tk.StringVar()
    tk.Entry(input_subframe, textvariable=material_poisson_var, width=20).grid(row=4, column=1, padx=5, pady=2)

    tk.Label(input_subframe, text=dil_sozlugu[dil]["uzama_yuzdesi"]).grid(row=5, column=0, padx=5, pady=2, sticky="e")
    material_elongation_var = tk.StringVar()
    tk.Entry(input_subframe, textvariable=material_elongation_var, width=20).grid(row=5, column=1, padx=5, pady=2)

    tk.Label(input_subframe, text=dil_sozlugu[dil]["yogunluk"]).grid(row=6, column=0, padx=5, pady=2, sticky="e")
    material_density_var = tk.StringVar()
    tk.Entry(input_subframe, textvariable=material_density_var, width=20).grid(row=6, column=1, padx=5, pady=2)

    material_tree_frame = ttk.LabelFrame(material_input_frame, text=dil_sozlugu[dil]["malzeme_ozellikleri"], padding=5)
    material_tree_frame.pack(fill='both', expand=True, pady=5)
    material_tree = ttk.Treeview(material_tree_frame, show="headings")
    material_tree.pack(fill='both', expand=True)
    scrollbar = ttk.Scrollbar(material_tree_frame, orient="vertical", command=material_tree.yview)
    scrollbar.pack(side="right", fill="y")
    material_tree.configure(yscrollcommand=scrollbar.set)
    material_tree.bind('<<TreeviewSelect>>', on_material_select)
    update_material_table()

    material_button_frame = ttk.Frame(material_input_frame)
    material_button_frame.pack(fill='x', pady=5)
    ttk.Button(material_button_frame, text=dil_sozlugu[dil]["kaydet"], command=save_material, style="Accent.TButton").pack(side="left", padx=5)
    ttk.Button(material_button_frame, text=dil_sozlugu[dil]["yeni"], command=new_material, style="TButton").pack(side="left", padx=5)
    ttk.Button(material_button_frame, text=dil_sozlugu[dil]["sil"], command=delete_material, style="Danger.TButton").pack(side="left", padx=5)

# Parametrik Hesaplama sekmesi oluşturma
def create_parametric_frame(parent, dil):
    global para_results_tree, progress_bar, progress_label, optimal_label, para_plot_frame, param_to_graph_var, param_bolt_size_var, param_shank_length_var, param_thread_length_var, param_preload_percent_var, param_tensile_force_var, test_buttons, parametric_clamped_parts_frames
    para_input_frame = ttk.LabelFrame(parent, text=dil_sozlugu[dil]["parametre_tanimlama"], padding=5)
    para_input_frame.pack(side="left", fill='y', padx=5, pady=5)

    tk.Label(para_input_frame, text=dil_sozlugu[dil]["civata_boyutu"]).grid(row=0, column=0, padx=5, pady=5)
    param_bolt_size_var = tk.StringVar()
    tk.Entry(para_input_frame, textvariable=param_bolt_size_var, width=20).grid(row=0, column=1, padx=5)
    ttk.Button(para_input_frame, text="Tanımla", command=lambda: define_range(param_bolt_size_var, dil_sozlugu[dil]["civata_boyutu"], False)).grid(row=0, column=2, padx=5)

    tk.Label(para_input_frame, text=dil_sozlugu[dil]["govde_uzunlugu"]).grid(row=1, column=0, padx=5, pady=5)
    param_shank_length_var = tk.StringVar()
    tk.Entry(para_input_frame, textvariable=param_shank_length_var, width=20).grid(row=1, column=1, padx=5)
    ttk.Button(para_input_frame, text="Tanımla", command=lambda: define_range(param_shank_length_var, dil_sozlugu[dil]["govde_uzunlugu"])).grid(row=1, column=2, padx=5)

    tk.Label(para_input_frame, text=dil_sozlugu[dil]["disli_kisim_uzunlugu"]).grid(row=2, column=0, padx=5, pady=5)
    param_thread_length_var = tk.StringVar()
    tk.Entry(para_input_frame, textvariable=param_thread_length_var, width=20).grid(row=2, column=1, padx=5)
    ttk.Button(para_input_frame, text="Tanımla", command=lambda: define_range(param_thread_length_var, dil_sozlugu[dil]["disli_kisim_uzunlugu"])).grid(row=2, column=2, padx=5)

    tk.Label(para_input_frame, text=dil_sozlugu[dil]["on_yukleme_yuzdesi"]).grid(row=3, column=0, padx=5, pady=5)
    param_preload_percent_var = tk.StringVar()
    tk.Entry(para_input_frame, textvariable=param_preload_percent_var, width=20).grid(row=3, column=1, padx=5)
    ttk.Button(para_input_frame, text="Tanımla", command=lambda: define_range(param_preload_percent_var, dil_sozlugu[dil]["on_yukleme_yuzdesi"])).grid(row=3, column=2, padx=5)

    tk.Label(para_input_frame, text=dil_sozlugu[dil]["cekme_kuvveti"]).grid(row=4, column=0, padx=5, pady=5)
    param_tensile_force_var = tk.StringVar()
    tk.Entry(para_input_frame, textvariable=param_tensile_force_var, width=20).grid(row=4, column=1, padx=5)
    ttk.Button(para_input_frame, text="Tanımla", command=lambda: define_range(param_tensile_force_var, dil_sozlugu[dil]["cekme_kuvveti"])).grid(row=4, column=2, padx=5)

    # Sıkıştırılan Parça Tanımlama Bölümü
    clamped_frame = ttk.LabelFrame(para_input_frame, text=dil_sozlugu[dil]["sıkıştırılan_parca_tanimlama"], padding=5)
    clamped_frame.grid(row=5, column=0, columnspan=3, pady=5)
    parametric_clamped_parts_frame = ttk.Frame(clamped_frame)
    parametric_clamped_parts_frame.pack(fill='x', pady=2)
    ttk.Button(clamped_frame, text=dil_sozlugu[dil]["parca_ekle"], command=lambda: add_param_clamped_part(parametric_clamped_parts_frame), style="Accent.TButton").pack(pady=5)

    button_frame = ttk.Frame(para_input_frame)
    button_frame.grid(row=7, column=0, columnspan=3, pady=10)
    ttk.Button(button_frame, text=dil_sozlugu[dil]["hesapla"], command=run_parametric_analysis, style="Accent.TButton").pack(side="left", padx=5)
    ttk.Button(button_frame, text=dil_sozlugu[dil]["iptal_et"], command=cancel_analysis, style="Danger.TButton").pack(side="left", padx=5)
    test_button = ttk.Button(button_frame, text=dil_sozlugu[dil]["test"], command=test_parametric_values, style="Test.TButton")
    test_button.pack(side="left", padx=5)
    test_buttons.append(test_button)

    progress_bar = ttk.Progressbar(parent, length=300)
    progress_bar.pack(pady=5)
    progress_label = ttk.Label(parent, text="Hesaplama: 0% tamamlandı")
    progress_label.pack(pady=5)

    optimal_frame = ttk.LabelFrame(parent, text=dil_sozlugu[dil]["en_optimal_kombinasyon"], padding=5)
    optimal_frame.pack(side="right", fill='y', padx=5, pady=5)
    optimal_label = ttk.Label(optimal_frame, text="En Optimal Kombinasyon: Henüz hesaplanmadı")
    optimal_label.pack(pady=5)

    para_results_frame = ttk.LabelFrame(parent, text=dil_sozlugu[dil]["parametrik_sonuclar"], padding=5)
    para_results_frame.pack(fill='x', padx=10, pady=5)
    para_results_tree = ttk.Treeview(para_results_frame, show="headings", height=7)
    para_results_tree.pack(fill='x')
    para_scrollbar = ttk.Scrollbar(para_results_frame, orient="horizontal", command=para_results_tree.xview)
    para_scrollbar.pack(side="bottom", fill="x")
    para_results_tree.configure(xscrollcommand=para_scrollbar.set)
    ttk.Button(para_results_frame, text=dil_sozlugu[dil]["excel_aktar"], command=export_parametric_to_excel, style="Export.TButton").pack(pady=5)

    para_graph_frame = ttk.Frame(para_results_frame)
    para_graph_frame.pack(fill='x', pady=5)
    tk.Label(para_graph_frame, text=dil_sozlugu[dil]["grafik_parametresi"]).pack(side="left", padx=5)
    param_to_graph_var = tk.StringVar()
    ttk.Combobox(para_graph_frame, textvariable=param_to_graph_var, values=[dil_sozlugu[dil]["civata_boyutu"].rstrip(":"), dil_sozlugu[dil]["govde_uzunlugu"].rstrip(":"), dil_sozlugu[dil]["disli_kisim_uzunlugu"].rstrip(":"), dil_sozlugu[dil]["on_yukleme_yuzdesi"].rstrip(":"), dil_sozlugu[dil]["cekme_kuvveti"].rstrip(":")], width=20).pack(side="left", padx=5)
    ttk.Button(para_graph_frame, text=dil_sozlugu[dil]["grafik_ciz"], command=draw_parametric_graph).pack(side="left", padx=5)
    ttk.Button(para_graph_frame, text=dil_sozlugu[dil]["optimal_grafik_ciz"], command=draw_optimal_graph).pack(side="left", padx=5)

    para_plot_frame = ttk.LabelFrame(parent, text=dil_sozlugu[dil]["parametrik_grafik"], padding=5)
    para_plot_frame.pack(fill='both', expand=True, padx=10, pady=5)

# Wiki sekmesi oluşturma
def create_wiki_frame(parent, dil):
    wiki_text_widget = tk.Text(parent, wrap="word", state="disabled", bg="#FFFFFF", fg="#333333")
    wiki_text_widget.pack(fill="both", expand=True, padx=10, pady=10)
    wiki_scrollbar = ttk.Scrollbar(parent, command=wiki_text_widget.yview)
    wiki_scrollbar.pack(side="right", fill="y")
    wiki_text_widget.config(yscrollcommand=wiki_scrollbar.set)
    render_wiki_text(wiki_text_widget, wiki_text)

# Ayarlar sekmesi oluşturma
def create_settings_frame(parent, dil, dev_mode):
    settings_frame = ttk.Frame(parent)
    settings_frame.pack(fill='both', expand=True, padx=5, pady=5)

    tk.Label(settings_frame, text=dil_sozlugu[dil]["dil_secimi"]).grid(row=0, column=0, padx=5, pady=5)
    dil_combobox = ttk.Combobox(settings_frame, values=["tr", "en"], state="readonly")
    dil_combobox.set(dil)
    dil_combobox.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(settings_frame, text=dil_sozlugu[dil]["gelistirici_modu"]).grid(row=2, column=0, padx=5, pady=5)
    dev_mode_var = tk.BooleanVar(value=dev_mode)
    tk.Checkbutton(settings_frame, variable=dev_mode_var).grid(row=2, column=1, padx=5, pady=5)

    def save_settings():
        new_dil = dil_combobox.get()
        new_dev_mode = dev_mode_var.get()
        save_config(new_dil, new_dev_mode)
        create_all_frames(new_dil, new_dev_mode)

    ttk.Button(settings_frame, text=dil_sozlugu[dil]["kaydet"], command=save_settings, style="Accent.TButton").grid(row=3, column=0, columnspan=2, pady=10)

# Mevcut fonksiyonlar
def compute_stiffness(bolt_size, L_shank, L_thread, material, preload_percent, F_ext_tensile, F_ext_shear, clamped_parts):
    try:
        if not bolt_size or bolt_size not in bolt_sizes:
            raise ValueError("Geçerli bir cıvata boyutu seçin.")
        L_shank = float(L_shank or 0)
        if L_shank <= 0:
            raise ValueError("Gövde uzunluğu 0'dan büyük olmalıdır.")
        L_thread = float(L_thread or 0)
        if L_thread < 0:
            raise ValueError("Dişli kısım uzunluğu negatif olamaz.")
        if not material or material not in materials:
            raise ValueError("Geçerli bir malzeme seçin.")
        E_bolt = materials[material]['E']
        yield_strength = materials[material]['yield_strength']
        ultimate_strength = materials[material]['ultimate_strength']
        A_shank = bolt_sizes[bolt_size]['A_shank']
        A_thread = bolt_sizes[bolt_size]['A_thread']
        preload_percent = float(preload_percent or 0)
        if not 0 <= preload_percent <= 100:
            raise ValueError("Ön yükleme yüzdesi 0-100 arasında olmalıdır.")
        F_preload = (preload_percent / 100) * yield_strength * A_thread
        F_ext_tensile = float(F_ext_tensile or 0)
        F_ext_shear = float(F_ext_shear or 0)

        k_shank = (E_bolt * A_shank) / L_shank
        if L_thread > 0:
            k_thread = (E_bolt * A_thread) / L_thread
            k_bolt = 1 / (1/k_shank + 1/k_thread)
        else:
            k_bolt = k_shank

        k_clamped_total = 0
        total_thickness = 0
        for part in clamped_parts:
            thickness = float(part['thickness_var'].get())
            if thickness <= 0:
                raise ValueError("Parça kalınlığı 0'dan büyük olmalıdır.")
            material_part = part['material_var'].get()
            E_part = materials[material_part]['E']
            area = float(part['area_var'].get())
            if area <= 0:
                raise ValueError("Parça alanı 0'dan büyük olmalıdır.")
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

        result = {
            "Toplam Cıvata Sertliği (N/mm)": f"{k_bolt:.2f}",
            "Toplam Kavrama Sertliği (N/mm)": f"{k_clamped_total:.2f}",
            "Toplam Cıvata Kuvveti (N)": f"{F_bolt_total:.2f}",
            "Cıvata Çarpılma (mm)": f"{delta_L_bolt:.4f}",
            "Kavrama Çarpılma (mm)": f"{delta_L_clamped:.4f}",
            "Kesme Gerilimi (MPa)": f"{shear_stress:.2f}",
            f"Güvenlik Faktörü ({safety_basis})": f"{safety_factor:.2f}"
        }
        return result
    except ValueError as e:
        return {'error': str(e)}

def calculate_stiffness():
    global canvas, bolt_size_var, shank_length_var, thread_length_var, material_var, preload_percent_var, tensile_force_var, shear_force_var, clamped_parts_frames
    result = compute_stiffness(
        bolt_size_var.get(), shank_length_var.get(), thread_length_var.get(),
        material_var.get(), preload_percent_var.get(), tensile_force_var.get(),
        shear_force_var.get(), clamped_parts_frames
    )
    if 'error' in result:
        messagebox.showerror("Giriş Hatası", result['error'])
    else:
        results_history.append(result)
        update_results_table()
        plot_load_deflection(result)

def plot_load_deflection(result):
    global canvas, plot_frame, preload_percent_var, material_var, bolt_size_var
    if canvas:
        canvas.get_tk_widget().destroy()
    fig, ax = plt.subplots(figsize=(4, 3))
    F_preload = (float(preload_percent_var.get() or 0) / 100) * materials[material_var.get()]['yield_strength'] * bolt_sizes[bolt_size_var.get()]['A_thread']
    x_bolt = [0, F_preload / float(result["Toplam Cıvata Sertliği (N/mm)"]), float(result["Cıvata Çarpılma (mm)"])]
    y_bolt = [0, F_preload, float(result["Toplam Cıvata Kuvveti (N)"])]
    ax.plot(x_bolt, y_bolt, marker='o', label='Yük-Çarpılma', color='blue')
    ax.set_xlabel('Çarpılma (mm)')
    ax.set_ylabel('Yük (N)')
    ax.set_title('Yük-Çarpılma Eğrisi')
    ax.grid(True)
    ax.legend()
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

def add_clamped_part(type='Washer', thickness='', material='Steel', area=''):
    global clamped_parts_frame
    frame = ttk.Frame(clamped_parts_frame)
    frame.pack(fill='x', pady=2)
    type_var = tk.StringVar(value=type)
    ttk.Combobox(frame, textvariable=type_var, values=['Washer', 'Plate', 'Cylinder'], width=10).pack(side='left', padx=5)
    thickness_var = tk.StringVar(value=thickness)
    tk.Entry(frame, textvariable=thickness_var, width=10).pack(side='left', padx=5)
    tk.Label(frame, text="Uzunluk (mm)").pack(side='left', padx=5)  # Kalınlık için etiket eklendi
    material_var = tk.StringVar(value=material)
    ttk.Combobox(frame, textvariable=material_var, values=list(materials.keys()), width=15).pack(side='left', padx=5)
    area_var = tk.StringVar(value=area)
    tk.Entry(frame, textvariable=area_var, width=10).pack(side='left', padx=5)
    tk.Label(frame, text="Alan (mm²)").pack(side='left', padx=5)
    ttk.Button(frame, text="Kaldır", command=lambda: remove_clamped_part(frame), style="Danger.TButton").pack(side='left', padx=5)
    clamped_parts_frames.append({'type_var': type_var, 'thickness_var': thickness_var, 'material_var': material_var, 'area_var': area_var})

def remove_clamped_part(frame):
    global clamped_parts_frames
    frame.destroy()
    clamped_parts_frames[:] = [f for f in clamped_parts_frames if f['thickness_var'].get() != frame.winfo_children()[1].get()]

# Parametrik hesaplama için sıkıştırılan parça ekleme
def add_param_clamped_part(frame, type='Washer', thickness='', material='Steel', area=''):
    param_frame = ttk.Frame(frame)
    param_frame.pack(fill='x', pady=2)
    type_var = tk.StringVar(value=type)
    ttk.Combobox(param_frame, textvariable=type_var, values=['Washer', 'Plate', 'Cylinder'], width=10).pack(side='left', padx=5)
    thickness_var = tk.StringVar(value=thickness)
    tk.Entry(param_frame, textvariable=thickness_var, width=10).pack(side='left', padx=5)
    tk.Label(param_frame, text="Uzunluk (mm)").pack(side='left', padx=5)  # Kalınlık için etiket eklendi
    material_var = tk.StringVar(value=material)
    ttk.Combobox(param_frame, textvariable=material_var, values=list(materials.keys()), width=15).pack(side='left', padx=5)
    area_var = tk.StringVar(value=area)
    tk.Entry(param_frame, textvariable=area_var, width=10).pack(side='left', padx=5)
    tk.Label(param_frame, text="Alan (mm²)").pack(side='left', padx=5)
    ttk.Button(param_frame, text="Kaldır", command=lambda: remove_param_clamped_part(param_frame), style="Danger.TButton").pack(side='left', padx=5)
    parametric_clamped_parts_frames.append({'type_var': type_var, 'thickness_var': thickness_var, 'material_var': material_var, 'area_var': area_var})

def remove_param_clamped_part(frame):
    global parametric_clamped_parts_frames
    frame.destroy()
    parametric_clamped_parts_frames[:] = [f for f in parametric_clamped_parts_frames if f['thickness_var'].get() != frame.winfo_children()[1].get()]

def update_results_table():
    global results_tree, max_rows_var, results_history, max_rows
    try:
        new_max = int(max_rows_var.get())
        if new_max > 0:
            max_rows = new_max
    except ValueError:
        pass
    for item in results_tree.get_children():
        results_tree.delete(item)
    if not results_history:
        return
    headers = ["Parametre"] + [f"Hesaplama {i+1}" for i in range(min(len(results_history), max_rows))]
    results_tree["columns"] = headers
    for col in headers:
        results_tree.column(col, anchor="center", width=150 if col == "Parametre" else 120)
        results_tree.heading(col, text=col, anchor="center")
    for param in results_history[0]:
        values = [param] + [r[param] for r in results_history[-max_rows:]]
        results_tree.insert("", "end", values=values)

def run_parametric_analysis():
    global cancel_flag, parametric_results, progress_bar, progress_label, material_var, shear_force_var, parametric_clamped_parts_frames
    cancel_flag.clear()
    parametric_results.clear()

    if not parametric_clamped_parts_frames:
        messagebox.showerror("Hata", "Parametrik analiz için en az bir sıkıştırılan parça eklenmelidir!")
        return

    bolt_size_vals = param_bolt_size_var.get().split(',') if param_bolt_size_var.get() else [bolt_size_var.get()]
    shank_length_vals = param_shank_length_var.get().split(',') if param_shank_length_var.get() else [shank_length_var.get()]
    thread_length_vals = param_thread_length_var.get().split(',') if param_thread_length_var.get() else [thread_length_var.get()]
    preload_percent_vals = param_preload_percent_var.get().split(',') if param_preload_percent_var.get() else [preload_percent_var.get()]
    tensile_force_vals = param_tensile_force_var.get().split(',') if param_tensile_force_var.get() else [tensile_force_var.get()]

    bolt_size_vals = [v.strip() for v in bolt_size_vals]
    shank_length_vals = [v.strip() for v in shank_length_vals]
    thread_length_vals = [v.strip() for v in thread_length_vals]
    preload_percent_vals = [v.strip() for v in preload_percent_vals]
    tensile_force_vals = [v.strip() for v in tensile_force_vals]

    combinations = list(product(bolt_size_vals, shank_length_vals, thread_length_vals, preload_percent_vals, tensile_force_vals))
    total_combinations = len(combinations)

    if total_combinations > 1000:
        if not messagebox.askyesno("Uyarı", "Bu işlem uzun sürebilir. Devam etmek istiyor musunuz?"):
            return

    progress_bar['maximum'] = total_combinations
    progress_bar['value'] = 0
    progress_label.config(text="Hesaplama: 0% tamamlandı")

    worker = threading.Thread(target=parametric_worker, args=(combinations, parametric_clamped_parts_frames, material_var.get(), shear_force_var.get()))
    worker.daemon = True
    worker.start()
    root.after(100, check_queue)

def parametric_worker(combinations, clamped_parts, material, F_ext_shear):
    global analysis_queue, cancel_flag
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS results (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 bolt_size TEXT, shank_length TEXT, thread_length TEXT,
                 preload_percent TEXT, tensile_force TEXT,
                 stiffness TEXT, clamped_stiffness TEXT,
                 bolt_force TEXT, bolt_deflection TEXT,
                 clamped_deflection TEXT, shear_stress TEXT,
                 safety_factor TEXT)''')
    conn.commit()

    total_combinations = len(combinations)
    for i, (bolt_size, L_shank, L_thread, preload_percent, F_ext_tensile) in enumerate(combinations):
        if cancel_flag.is_set():
            analysis_queue.put(('canceled',))
            break
        result = compute_stiffness(bolt_size, L_shank, L_thread, material, preload_percent, F_ext_tensile, F_ext_shear, clamped_parts)
        if 'error' in result:
            analysis_queue.put(('error', result['error']))
        else:
            c.execute('''INSERT INTO results (bolt_size, shank_length, thread_length, preload_percent, tensile_force,
                        stiffness, clamped_stiffness, bolt_force, bolt_deflection, clamped_deflection, shear_stress, safety_factor)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (bolt_size, L_shank, L_thread, preload_percent, F_ext_tensile,
                       result["Toplam Cıvata Sertliği (N/mm)"],
                       result["Toplam Kavrama Sertliği (N/mm)"],
                       result["Toplam Cıvata Kuvveti (N)"],
                       result["Cıvata Çarpılma (mm)"],
                       result["Kavrama Çarpılma (mm)"],
                       result["Kesme Gerilimi (MPa)"],
                       result[f"Güvenlik Faktörü ({safety_basis_var.get()})"]))
            conn.commit()
            analysis_queue.put(('result', {
                'Cıvata Boyutu': bolt_size, 'Gövde Uzunluğu': L_shank, 'Dişli Kısım Uzunluğu': L_thread,
                'Ön Yükleme Yüzdesi': preload_percent, 'Çekme Kuvveti': F_ext_tensile,
                **result
            }))
        analysis_queue.put(('progress', i + 1, total_combinations))
    analysis_queue.put(('done',))
    conn.close()

def check_queue():
    global analysis_queue, progress_bar, progress_label, parametric_results
    try:
        while True:
            msg = analysis_queue.get_nowait()
            if msg[0] == 'progress':
                progress_bar['value'] = msg[1]
                progress_label.config(text=f"Hesaplama: {(msg[1] / msg[2]) * 100:.1f}% tamamlandı")
            elif msg[0] == 'result':
                parametric_results.append(msg[1])
            elif msg[0] == 'done':
                load_parametric_results_from_db()
                update_parametric_results()
                messagebox.showinfo("Bilgi", "Parametrik analiz tamamlandı!")
                return
            elif msg[0] == 'canceled':
                progress_bar['value'] = 0
                progress_label.config(text="Hesaplama iptal edildi.")
                messagebox.showinfo("Bilgi", "Parametrik analiz iptal edildi.")
                return
            elif msg[0] == 'error':
                messagebox.showerror("Hata", msg[1])
    except queue.Empty:
        root.after(100, check_queue)

def load_parametric_results_from_db():
    global parametric_results
    parametric_results.clear()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM results")
    rows = c.fetchall()
    headers = ["bolt_size", "shank_length", "thread_length", "preload_percent", "tensile_force",
               "stiffness", "clamped_stiffness", "bolt_force", "bolt_deflection",
               "clamped_deflection", "shear_stress", "safety_factor"]
    for row in rows[1:]:
        result = {
            'Cıvata Boyutu': row[1], 'Gövde Uzunluğu': row[2], 'Dişli Kısım Uzunluğu': row[3],
            'Ön Yükleme Yüzdesi': row[4], 'Çekme Kuvveti': row[5],
            "Toplam Cıvata Sertliği (N/mm)": row[6], "Toplam Kavrama Sertliği (N/mm)": row[7],
            "Toplam Cıvata Kuvveti (N)": row[8], "Cıvata Çarpılma (mm)": row[9],
            "Kavrama Çarpılma (mm)": row[10], "Kesme Gerilimi (MPa)": row[11],
            f"Güvenlik Faktörü ({safety_basis_var.get()})": row[12]
        }
        parametric_results.append(result)
    conn.close()

def cancel_analysis():
    global cancel_flag
    cancel_flag.set()

def update_parametric_results():
    global para_results_tree, parametric_results, optimal_label, safety_basis_var
    for item in para_results_tree.get_children():
        para_results_tree.delete(item)
    
    if parametric_results:
        safety_key = f"Güvenlik Faktörü ({safety_basis_var.get()})"
        optimal_result = max(parametric_results, key=lambda x: float(x[safety_key]))
        optimal_label.config(text=f"En Optimal Kombinasyon:\n"
                                 f"Cıvata Boyutu: {optimal_result['Cıvata Boyutu']}\n"
                                 f"Gövde Uzunluğu: {optimal_result['Gövde Uzunluğu']} mm\n"
                                 f"Dişli Kısım Uzunluğu: {optimal_result['Dişli Kısım Uzunluğu']} mm\n"
                                 f"Ön Yükleme Yüzdesi: {optimal_result['Ön Yükleme Yüzdesi']}%\n"
                                 f"Çekme Kuvveti: {optimal_result['Çekme Kuvveti']} N\n"
                                 f"Güvenlik Faktörü: {optimal_result[safety_key]}")
        
        headers = ['Cıvata Boyutu', 'Gövde Uzunluğu', 'Dişli Kısım Uzunluğu', 'Ön Yükleme Yüzdesi', 'Çekme Kuvveti'] + list(parametric_results[0].keys())
        headers = [h for h in headers if h not in ['Cıvata Boyutu', 'Gövde Uzunluğu', 'Dişli Kısım Uzunluğu', 'Ön Yükleme Yüzdesi', 'Çekme Kuvveti']] + ['Cıvata Boyutu', 'Gövde Uzunluğu', 'Dişli Kısım Uzunluğu', 'Ön Yükleme Yüzdesi', 'Çekme Kuvveti']
        para_results_tree["columns"] = headers
        for col in headers:
            para_results_tree.column(col, anchor="center", width=120)
            para_results_tree.heading(col, text=col, anchor="center")
        
        for result in parametric_results:
            values = [result[h] for h in headers]
            para_results_tree.insert("", "end", values=values)

def draw_parametric_graph():
    global para_canvas, para_plot_frame, parametric_results, param_to_graph_var, safety_basis_var
    if not parametric_results:
        messagebox.showwarning("Uyarı", "Önce parametrik analiz yapmalısınız!")
        return
    
    selected_param = param_to_graph_var.get()
    safety_key = f"Güvenlik Faktörü ({safety_basis_var.get()})"
    optimal_result = max(parametric_results, key=lambda x: float(x[safety_key]))
    
    grouped_data = {}
    for result in parametric_results:
        param_value = result[selected_param]
        grouped_data[param_value] = grouped_data.get(param_value, []) + [float(result[safety_key])]
    
    x_values = list(grouped_data.keys())
    y_values = [sum(values) / len(values) for values in grouped_data.values()]
    is_numeric = selected_param in ['Gövde Uzunluğu', 'Dişli Kısım Uzunluğu', 'Ön Yükleme Yüzdesi', 'Çekme Kuvveti']
    
    if para_canvas:
        para_canvas.get_tk_widget().destroy()
    
    fig, ax = plt.subplots(figsize=(6, 4))
    if is_numeric:
        x_values = [float(x) for x in x_values]
        ax.plot(x_values, y_values, marker='o', label='Ortalama Güvenlik Faktörü', color='blue')
        ax.axvline(float(optimal_result[selected_param]), color='red', linestyle='--', label='Optimal Değer')
    else:
        ax.bar(x_values, y_values, color='blue', label='Ortalama Güvenlik Faktörü')
        ax.axvline(x_values.index(optimal_result[selected_param]), color='red', linestyle='--', label='Optimal Değer')
    
    ax.set_xlabel(selected_param)
    ax.set_ylabel('Güvenlik Faktörü')
    ax.set_title(f'{selected_param} vs Güvenlik Faktörü')
    ax.grid(True)
    ax.legend()
    para_canvas = FigureCanvasTkAgg(fig, master=para_plot_frame)
    para_canvas.draw()
    para_canvas.get_tk_widget().pack(fill='both', expand=True)

def draw_optimal_graph():
    global para_canvas, para_plot_frame, parametric_results, safety_basis_var, bolt_size_var, shank_length_var, thread_length_var, preload_percent_var, tensile_force_var, material_var
    if not parametric_results:
        messagebox.showwarning("Uyarı", "Önce parametrik analiz yapmalısınız!")
        return
    
    safety_key = f"Güvenlik Faktörü ({safety_basis_var.get()})"
    optimal_result = max(parametric_results, key=lambda x: float(x[safety_key]))
    
    bolt_size_var.set(optimal_result['Cıvata Boyutu'])
    shank_length_var.set(str(optimal_result['Gövde Uzunluğu']))
    thread_length_var.set(str(optimal_result['Dişli Kısım Uzunluğu']))
    preload_percent_var.set(str(optimal_result['Ön Yükleme Yüzdesi']))
    tensile_force_var.set(str(optimal_result['Çekme Kuvveti']))
    
    E_bolt = materials[material_var.get()]['E']
    yield_strength = materials[material_var.get()]['yield_strength']
    A_shank = bolt_sizes[optimal_result['Cıvata Boyutu']]['A_shank']
    A_thread = bolt_sizes[optimal_result['Cıvata Boyutu']]['A_thread']
    
    k_shank = (E_bolt * A_shank) / float(optimal_result['Gövde Uzunluğu'])
    if float(optimal_result['Dişli Kısım Uzunluğu']) > 0:
        k_thread = (E_bolt * A_thread) / float(optimal_result['Dişli Kısım Uzunluğu'])
        k_bolt = 1 / (1/k_shank + 1/k_thread)
    else:
        k_bolt = k_shank
    
    F_preload = (float(optimal_result['Ön Yükleme Yüzdesi']) / 100) * yield_strength * A_thread
    delta_F_bolt = (k_bolt / (k_bolt + float(optimal_result['Toplam Kavrama Sertliği (N/mm)']))) * float(optimal_result['Çekme Kuvveti'])
    F_total_bolt = F_preload + delta_F_bolt
    
    delta_L_bolt_preload = F_preload / k_bolt
    delta_L_bolt_total = F_total_bolt / k_bolt
    
    if para_canvas:
        para_canvas.get_tk_widget().destroy()
    
    fig, ax = plt.subplots(figsize=(6, 4))
    x_bolt = [0, delta_L_bolt_preload, delta_L_bolt_total]
    y_bolt = [0, F_preload, F_total_bolt]
    ax.plot(x_bolt, y_bolt, marker='o', label='Yük-Çarpılma (Optimal)', color='green')
    ax.set_xlabel('Çarpılma (mm)')
    ax.set_ylabel('Yük (N)')
    ax.set_title('Optimal Kombinasyon Yük-Çarpılma Eğrisi')
    ax.grid(True)
    ax.legend()
    para_canvas = FigureCanvasTkAgg(fig, master=para_plot_frame)
    para_canvas.draw()
    para_canvas.get_tk_widget().pack(fill='both', expand=True)

def clear_inputs():
    global canvas, bolt_size_var, shank_length_var, thread_length_var, material_var, preload_percent_var, tensile_force_var, shear_force_var, shear_area_var, safety_basis_var, clamped_parts_frames
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
    global bolt_size_var, shank_length_var, thread_length_var, material_var, preload_percent_var, tensile_force_var, shear_force_var, shear_area_var, safety_basis_var
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
    dil, _ = load_config()
    messagebox.showinfo("Test", dil_sozlugu[dil]["test_degerleri_yuklendi"])

def test_parametric_values():
    global param_bolt_size_var, param_shank_length_var, param_thread_length_var, param_preload_percent_var, param_tensile_force_var, parametric_clamped_parts_frames
    # Daha geniş ve zorlayıcı veriler
    param_bolt_size_var.set("M6,M8,M10")  # M6'dan M10'a kadar
    param_shank_length_var.set(','.join(map(str, range(10, 51, 5))))  # 10-50, 5 mm adımlarla
    param_thread_length_var.set("5,10,15,20")  # 5-20, 5 mm adımlarla
    param_preload_percent_var.set("60,70,80")  # %60-80
    param_tensile_force_var.set("5000,10000,15000")  # 5000-15000 N
    # Test için sıkıştırılan parçalar ekle
    for frame in parametric_clamped_parts_frames[:]:
        frame['type_var'].master.destroy()
    parametric_clamped_parts_frames.clear()
    add_param_clamped_part(parametric_clamped_parts_frame, type="Plate", thickness="10", material="Steel", area="100")
    add_param_clamped_part(parametric_clamped_parts_frame, type="Washer", thickness="5", material="Aluminum", area="80")
    root.update()
    dil, _ = load_config()
    messagebox.showinfo("Test", dil_sozlugu[dil]["test_degerleri_yuklendi"])

def export_to_excel():
    global results_history
    if not results_history:
        messagebox.showwarning("Uyarı", "Export edilecek veri yok!")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
    if file_path:
        df = pd.DataFrame(results_history)
        df.to_excel(file_path, index=False)
        messagebox.showinfo("Başarılı", f"Veriler '{file_path}' dosyasına kaydedildi.")

def save_material():
    global current_material, material_entry, material_var
    name = material_name_var.get().strip()
    try:
        if not name:
            raise ValueError("Malzeme adı boş olamaz.")
        E = float(material_E_var.get()) * 1000
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
    global current_material, material_tree, materials, material_var
    selected = material_tree.selection()
    if selected:
        name = material_tree.item(selected[0])['values'][0]
        if name in materials:
            del materials[name]
            material_var.set('Steel' if 'Steel' in materials else list(materials.keys())[0] if materials else '')
            if current_material == name:
                current_material = None
                clear_material_inputs()
            update_material_table()

def on_material_select(event):
    global current_material, material_tree
    selected = material_tree.selection()
    if selected:
        name = material_tree.item(selected[0])['values'][0]
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
    global material_name_var, material_E_var, material_yield_var, material_ultimate_var, material_poisson_var, material_elongation_var, material_density_var
    material_name_var.set("")
    material_E_var.set("")
    material_yield_var.set("")
    material_ultimate_var.set("")
    material_poisson_var.set("")
    material_elongation_var.set("")
    material_density_var.set("")

def update_material_table():
    global material_tree, materials
    for item in material_tree.get_children():
        material_tree.delete(item)
    headers = ["Malzeme Adı", "Elastiklik Modülü (GPa)", "Verim Dayanımı (MPa)", "Nihai Dayanım (MPa)", "Poisson Oranı", "Uzama Yüzdesi (%)", "Yoğunluk (g/cm³)"]
    material_tree["columns"] = headers
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
    widget.image_list = []
    lines = text.split('\n')
    for line in lines:
        if line.strip().startswith('#'):
            level = line.count('#')
            text_content = line.strip('# ').strip()
            widget.insert(tk.END, text_content + '\n', f"h{level}")
        elif line.strip().startswith('$$') and line.strip().endswith('$$'):
            latex_text = line.strip().strip('$$').strip()
            try:
                image = render_latex_to_image(latex_text)
                widget.image_list.append(image)
                widget.image_create(tk.END, image=image)
                widget.insert(tk.END, '\n')
            except Exception as e:
                widget.insert(tk.END, f"[LaTeX Hatası: {str(e)}]\n")
        else:
            widget.insert(tk.END, line + '\n')
    widget.tag_configure("h1", font=("Arial", 16, "bold"))
    widget.tag_configure("h2", font=("Arial", 14, "bold"))
    widget.tag_configure("h3", font=("Arial", 12, "bold"))
    widget.config(state="disabled")

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
                start, end, step = float(start_var.get()), float(end_var.get()), float(step_var.get())
                if step <= 0:
                    raise ValueError("Adım pozitif olmalı.")
                values = np.arange(start, end + step, step)
                param_var.set(','.join(map(str, values)))
                popup.destroy()
            except ValueError as e:
                messagebox.showerror("Hata", str(e))
        
        ttk.Button(popup, text="Uygula", command=apply_range, style="Accent.TButton").grid(row=3, column=0, columnspan=2, pady=10)
    else:
        tk.Label(popup, text="Değerler (virgülle ayrılmış):").grid(row=0, column=0, padx=5, pady=5)
        list_var = tk.StringVar()
        tk.Entry(popup, textvariable=list_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(popup, text="Uygula", command=lambda: [param_var.set(list_var.get()), popup.destroy()], style="Accent.TButton").grid(row=1, column=0, columnspan=2, pady=10)

def export_parametric_to_excel():
    global parametric_results
    if not parametric_results:
        messagebox.showwarning("Uyarı", "Export edilecek veri yok!")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
    if file_path:
        df = pd.DataFrame(parametric_results)
        df.to_excel(file_path, index=False)
        messagebox.showinfo("Başarılı", f"Veriler '{file_path}' dosyasına kaydedildi.")

# Ana pencere
root = tk.Tk()
root.title("Cıvata Sertliği Hesaplayıcısı")
root.geometry("900x700")

# Notebook
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both', padx=10, pady=10)

# Program başlangıcında ayarları yükle
dil, dev_mode = load_config()
create_all_frames(dil, dev_mode)

root.mainloop()