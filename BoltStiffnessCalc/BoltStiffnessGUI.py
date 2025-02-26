import tkinter as tk
from tkinter import messagebox

bolt_sizes = {
    'M10': {'A_nom': 58, 'A_t': 48.5},
    'M12': {'A_nom': 84.3, 'A_t': 68.0},
    # Add more bolt sizes as needed
}

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
            k_thread = float('inf')  # Infinite stiffness if thread length is 0
        
        k_bolt = 1 / (1/k_shank + 1/k_thread) if L_thread > 0 else k_shank
        
        result_var.set(f"Total bolt stiffness: {k_bolt:.2f} N/mm")
    else:
        messagebox.showerror("Input Error", "Invalid bolt size.")

# Create the main window
root = tk.Tk()
root.title("Bolt Stiffness Calculator")

# Create and place the widgets
tk.Label(root, text="Bolt Size (e.g., M10):").grid(row=0, column=0, padx=10, pady=5)
bolt_size_var = tk.StringVar()
tk.Entry(root, textvariable=bolt_size_var).grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Shank Length (mm):").grid(row=1, column=0, padx=10, pady=5)
shank_length_var = tk.StringVar()
tk.Entry(root, textvariable=shank_length_var).grid(row=1, column=1, padx=10, pady=5)

tk.Label(root, text="Thread Length (mm):").grid(row=2, column=0, padx=10, pady=5)
thread_length_var = tk.StringVar()
tk.Entry(root, textvariable=thread_length_var).grid(row=2, column=1, padx=10, pady=5)

tk.Label(root, text="Elastic Modulus (MPa):").grid(row=3, column=0, padx=10, pady=5)
elastic_modulus_var = tk.StringVar(value="200000")
tk.Entry(root, textvariable=elastic_modulus_var).grid(row=3, column=1, padx=10, pady=5)

result_var = tk.StringVar()
tk.Label(root, textvariable=result_var).grid(row=4, column=0, columnspan=2, padx=10, pady=5)

tk.Button(root, text="Calculate", command=calculate_stiffness).grid(row=5, column=0, columnspan=2, padx=10, pady=10)

# Run the application
root.mainloop()