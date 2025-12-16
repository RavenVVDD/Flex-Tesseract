import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Scrollbar, Text, ttk
import pytesseract
from PIL import Image
import json
from datetime import datetime
import pandas as pd
import os

# Configura la ruta a Tesseract si es necesario
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Diccionario de ciudades asociadas a cada cordón
cordones = {
    "Primer cordón": ["AVELLANEDA", "HURLINGHAM", "ITUZAINGO", "LA MATANZA NORTE", "LANUS", "LOMAS DE ZAMORA", "MORON", "SAN FERNANDO", "SAN ISIDRO", "SAN MARTIN",
                      "TRES DE FEBRERO", "VICENTE LOPEZ"],
    "Segundo cordón": ["ALMIRANTE BROWN", "BERAZATEGUI", "ESTEBAN ECHEVERRIA", "EZEIZA", "FLORENCIO VARELA",
                       "JOSE C PAZ", "LA MATANZA SUR", "MALVINAS ARGENTINAS", "MERLO", "MORENO", "QUILMES", "SAN MIGUEL", "TIGRE"],
    "Tercer cordón (CABA)": ["CABA"],
    "Cuarto cordón": ["BERISSO", "DEL VISO", "DERQUI", "ENSENADA", "GENERAL RODRIGUEZ", "LA PLATA CENTRO", "LA PLATA NORTE", "LUJAN", "NORDELTA",
                      "PILAR"]
}

# Precios asociados a cada cordón
precios_cordon = {
    "Primer cordón": 4631,
    "Segundo cordón": 6380,
    "Tercer cordón (CABA)": 2910,
    "Cuarto cordón": 8000
}

# Archivo para guardar los datos semanales
data_file = "data_semanal.json"

# Cargar datos semanales si existen
try:
    with open(data_file, 'r') as file:
        datos_semanales = json.load(file)
except FileNotFoundError:
    datos_semanales = {"Lunes": {}, "Martes": {}, "Miércoles": {}, "Jueves": {}, "Viernes": {}}

# Función para identificar el cordón y la ciudad basada en el texto extraído
def identificar_cordon_por_ciudad(texto):
    lineas = texto.splitlines()
    for linea in lineas:
        for cordon, ciudades in cordones.items():
            for ciudad in ciudades:
                if ciudad in linea.upper():
                    return (cordon, ciudad)  # Devuelve tanto el cordón como la ciudad
    return ("cordon_no_identificado", None)

# Función para mostrar el texto interpretado por Tesseract en una ventana emergente
def mostrar_texto_interpretado(texto, titulo):
    ventana_texto = Toplevel(root)
    ventana_texto.title(f"Texto interpretado - {titulo}")
    scrollbar = Scrollbar(ventana_texto)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    texto_area = Text(ventana_texto, wrap=tk.WORD, yscrollcommand=scrollbar.set)
    texto_area.insert(tk.END, texto)
    texto_area.pack(expand=True, fill='both')

    scrollbar.config(command=texto_area.yview)

# Función para abrir la imagen original
def abrir_imagen(file_path):
    os.startfile(file_path)  # Para Windows

# Función para procesar varias imágenes
# Función para procesar varias imágenes
def procesar_imagenes():
    file_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.jpg;*.jpeg;*.png")])
    if file_paths:
        for idx, file_path in enumerate(file_paths):
            imagen = Image.open(file_path)
            texto = ""
            for angle in [0, 90, 180, 270]:  # Probar diferentes rotaciones
                imagen_rotada = imagen.rotate(angle, expand=True)
                texto_rotado = pytesseract.image_to_string(imagen_rotada, lang='eng')
                if texto_rotado.strip():  # Si se encontró texto en esta rotación, detener el ciclo
                    texto = texto_rotado
                    break
            
            if not texto:
                texto = "No se pudo leer texto en ninguna rotación."
            
            # Obtener el cordón y la ciudad detectada
            cordon, ciudad = identificar_cordon_por_ciudad(texto)

            # Crear un marco para cada imagen procesada
            frame = tk.Frame(scrollable_frame)
            frame.pack(fill='x', pady=5)

            # Crear un título para la imagen
            titulo = f"ETIQUETA #{idx + 1}"

            # Mostrar el título de la imagen como hipervínculo
            link = tk.Label(frame, text=titulo, fg="blue", cursor="hand2")
            link.pack(side='left', padx=10)
            link.bind("<Button-1>", lambda e, p=file_path: abrir_imagen(p))

            # Mostrar el cordón y la ciudad detectada o permitir selección manual
            if cordon == "cordon_no_identificado":
                label_resultado = tk.Label(frame, text="No identificado", fg="red")
                label_resultado.pack(side='left', padx=10)
                
                # Combobox para seleccionar manualmente el cordón
                combobox_cordon = ttk.Combobox(frame, values=list(cordones.keys()), state="readonly")
                combobox_cordon.pack(side='left', padx=10)
                combobox_cordon.set("Seleccionar cordón")
                
                # Botón para confirmar la selección manual
                btn_confirmar_cordon = tk.Button(frame, text="Confirmar", command=lambda c=combobox_cordon, d=dia_seleccionado.get(), t=titulo: actualizar_cordon_manual(c, d, t))
                btn_confirmar_cordon.pack(side='left', padx=10)
            else:
                if ciudad:  # Si se detectó una ciudad específica, mostrarla
                    label_resultado = tk.Label(frame, text=f"{cordon} - {ciudad}")
                    label_resultado.pack(side='left', padx=10)
                else:
                    label_resultado = tk.Label(frame, text=f"{cordon}")
                    label_resultado.pack(side='left', padx=10)

                # Guardar los resultados en la tabla semanal automáticamente
                dia_actual = dia_seleccionado.get()
                if dia_actual in datos_semanales:
                    if cordon not in datos_semanales[dia_actual]:
                        datos_semanales[dia_actual][cordon] = 0
                    datos_semanales[dia_actual][cordon] += 1

        # Guardar los datos en el archivo JSON
        with open(data_file, 'w') as file:
            json.dump(datos_semanales, file, indent=4)
        
        mostrar_tabla_semanal()

    else:
        messagebox.showerror("Error", "No se seleccionó ninguna imagen.")

def actualizar_cordon_manual(combobox_cordon, dia, titulo):
    cordon_seleccionado = combobox_cordon.get()
    if cordon_seleccionado and cordon_seleccionado in cordones:
        if dia in datos_semanales:
            if cordon_seleccionado not in datos_semanales[dia]:
                datos_semanales[dia][cordon_seleccionado] = 0
            datos_semanales[dia][cordon_seleccionado] += 1

        # Guardar los datos en el archivo JSON
        guardar_datos()
        mostrar_tabla_semanal()
    else:
        messagebox.showwarning("Advertencia", "Por favor, seleccione un cordón válido.")


# Función para mostrar la tabla semanal en la GUI
def mostrar_tabla_semanal():
    # Limpiar cualquier tabla previa
    for widget in tabla_frame.winfo_children():
        widget.destroy()
    
    headers = ["Día", "Primer cordón", "Segundo cordón", "Tercer cordón (CABA)", "Cuarto cordón", "Total Día", "Manual"]
    for col_num, header in enumerate(headers):
        header_label = tk.Label(tabla_frame, text=header, font=('Arial', 12, 'bold'))
        header_label.grid(row=0, column=col_num, padx=10, pady=5)
    
    for row_num, (dia, data) in enumerate(datos_semanales.items(), start=1):
        total_dia = 0  # Para calcular el total del día
        tk.Label(tabla_frame, text=dia, font=('Arial', 12)).grid(row=row_num, column=0, padx=10, pady=5)
        
        for col_num, cordon in enumerate(headers[1:-2], start=1):
            cantidad = data.get(cordon, 0)
            costo_cordon = precios_cordon.get(cordon, 0) * cantidad
            total_dia += costo_cordon
            tk.Label(tabla_frame, text=f"{cantidad} (${costo_cordon})", font=('Arial', 12)).grid(row=row_num, column=col_num, padx=10, pady=5)
    
            # Counter manual para agregar paquetes manualmente
            spinbox = tk.Spinbox(tabla_frame, from_=0, to=100, width=5)
            spinbox.config(command=lambda c=cordon, d=dia, s=spinbox: actualizar_manual(c, d, s))
            spinbox.grid(row=row_num, column=col_num + 4, padx=10, pady=5)


        # Mostrar el total del día en la última columna
        tk.Label(tabla_frame, text=f"${total_dia}", font=('Arial', 12, 'bold')).grid(row=row_num, column=len(headers)-2, padx=10, pady=5)

        # Botón para resetear ese día
        reset_btn = tk.Button(tabla_frame, text="Resetear Día", command=lambda d=dia: resetear_dia(d))
        reset_btn.grid(row=row_num, column=len(headers), padx=10, pady=5)

# Función para actualizar manualmente los contadores
def actualizar_manual(cordon, dia, spinbox):
    cantidad = int(spinbox.get())
    if dia in datos_semanales:
        if cordon not in datos_semanales[dia]:
            datos_semanales[dia][cordon] = 0
        datos_semanales[dia][cordon] += cantidad
        guardar_datos()
        mostrar_tabla_semanal()

# Función para resetear un día específico
def resetear_dia(dia):
    if dia in datos_semanales:
        datos_semanales[dia] = {}
        guardar_datos()
        mostrar_tabla_semanal()

# Función para resetear toda la semana
def resetear_todo():
    for dia in datos_semanales:
        datos_semanales[dia] = {}
    guardar_datos()
    mostrar_tabla_semanal()

# Función para guardar los datos en un archivo Excel
def guardar_semana_excel():
    df = pd.DataFrame.from_dict(datos_semanales, orient='index')
    df.fillna(0, inplace=True)
    df['Total'] = df.apply(lambda row: sum([precios_cordon.get(cordon, 0) * row[cordon] for cordon in row.index if cordon in precios_cordon]), axis=1)
    save_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
    if save_path:
        df.to_excel(save_path, index=True)
        messagebox.showinfo("Guardado", f"Datos guardados en {save_path}")

# Función para guardar los datos en JSON
def guardar_datos():
    with open(data_file, 'w') as file:
        json.dump(datos_semanales, file, indent=4)

# Mapear números de día de la semana a nombres en español
dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Configurar la ventana principal
root = tk.Tk()
root.title("Clasificador de Paquetes por Cordón")

# Crear los componentes de la GUI
label_instrucciones = tk.Label(root, text="Seleccione una o más imágenes para procesar:")
label_instrucciones.pack(pady=10)

dia_seleccionado = tk.StringVar(value="Lunes")
selector_dia = ttk.Combobox(root, textvariable=dia_seleccionado, values=dias_semana[:-2])
selector_dia.pack(pady=10)

btn_cargar = tk.Button(root, text="Cargar Imágenes", command=procesar_imagenes)
btn_cargar.pack(pady=10)

# Botón para resetear toda la semana
btn_reset_total = tk.Button(root, text="Resetear Toda la Semana", command=resetear_todo)
btn_reset_total.pack(pady=10)

# Botón para guardar la semana en Excel
btn_guardar_excel = tk.Button(root, text="Guardar Semana en Excel", command=guardar_semana_excel)
btn_guardar_excel.pack(pady=10)

# Frame para la tabla de doble entrada
tabla_frame = tk.Frame(root)
tabla_frame.pack(pady=20)

# Frame para el área desplazable (slider)
canvas = tk.Canvas(root)
scrollable_frame = tk.Frame(canvas)
scrollbar = Scrollbar(root, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")
canvas.configure(yscrollcommand=scrollbar.set)

scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.pack(side="left", fill="both", expand=True)

mostrar_tabla_semanal()

# Ejecutar la GUI
root.mainloop()
