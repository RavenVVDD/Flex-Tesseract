import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Scrollbar, Text
import pytesseract
from PIL import Image
import json
from datetime import datetime

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
    "Primer cordón": 4518,
    "Segundo cordón": 6225,
    "Tercer cordón (CABA)": 2839,
    "Cuarto cordón": 7538
}

# Archivo para guardar los datos semanales
data_file = "data_semanal.json"

# Cargar datos semanales si existen
try:
    with open(data_file, 'r') as file:
        datos_semanales = json.load(file)
except FileNotFoundError:
    datos_semanales = {"Lunes": {}, "Martes": {}, "Miércoles": {}, "Jueves": {}, "Viernes": {}}

# Función para identificar el cordón basado en el texto extraído
def identificar_cordon_por_ciudad(texto):
    lineas = texto.splitlines()
    for linea in lineas:
        for cordon, ciudades in cordones.items():
            for ciudad in ciudades:
                if ciudad in linea.upper():
                    return cordon
    return "cordon_no_identificado"

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

# Función para procesar varias imágenes
def procesar_imagenes():
    file_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.jpg;*.jpeg;*.png")])
    if file_paths:
        for idx, file_path in enumerate(file_paths):
            imagen = Image.open(file_path)
            texto = pytesseract.image_to_string(imagen, lang='eng')
            cordon = identificar_cordon_por_ciudad(texto)

            # Crear un marco para cada imagen procesada
            frame = tk.Frame(root)
            frame.pack(fill='x', pady=5)

            # Crear un título para la imagen
            titulo = f"ETIQUETA #{idx + 1}"

            # Mostrar el título de la imagen y el cordón identificado
            label_resultado = tk.Label(frame, text=f"{titulo}: {cordon}")
            label_resultado.pack(side='left', padx=10)

            # Botón para ver el texto interpretado
            btn_ver_texto = tk.Button(frame, text="Ver texto interpretado",
                                      command=lambda t=texto, p=titulo: mostrar_texto_interpretado(t, p))
            btn_ver_texto.pack(side='right')

            # Guardar los resultados en la tabla semanal
            dia_actual = dias_semana[datetime.now().weekday()]  # Obtener el día actual en español
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

# Función para mostrar la tabla semanal en la GUI
def mostrar_tabla_semanal():
    # Limpiar cualquier tabla previa
    for widget in tabla_frame.winfo_children():
        widget.destroy()
    
    headers = ["Día", "Primer cordón", "Segundo cordón", "Tercer cordón (CABA)", "Cuarto cordón", "Total Día"]
    for col_num, header in enumerate(headers):
        header_label = tk.Label(tabla_frame, text=header, font=('Arial', 12, 'bold'))
        header_label.grid(row=0, column=col_num, padx=10, pady=5)
    
    for row_num, (dia, data) in enumerate(datos_semanales.items(), start=1):
        total_dia = 0  # Para calcular el total del día
        tk.Label(tabla_frame, text=dia, font=('Arial', 12)).grid(row=row_num, column=0, padx=10, pady=5)
        
        for col_num, cordon in enumerate(headers[1:-1], start=1):
            cantidad = data.get(cordon, 0)
            costo_cordon = precios_cordon.get(cordon, 0) * cantidad
            total_dia += costo_cordon
            tk.Label(tabla_frame, text=f"{cantidad} (${costo_cordon})", font=('Arial', 12)).grid(row=row_num, column=col_num, padx=10, pady=5)
        
        # Mostrar el total del día en la última columna
        tk.Label(tabla_frame, text=f"${total_dia}", font=('Arial', 12, 'bold')).grid(row=row_num, column=len(headers)-1, padx=10, pady=5)

# Mapear números de día de la semana a nombres en español
dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Configurar la ventana principal
root = tk.Tk()
root.title("Clasificador de Paquetes por Cordón")

# Crear los componentes de la GUI
label_instrucciones = tk.Label(root, text="Seleccione una o más imágenes para procesar:")
label_instrucciones.pack(pady=10)

btn_cargar = tk.Button(root, text="Cargar Imágenes", command=procesar_imagenes)
btn_cargar.pack(pady=10)

# Frame para la tabla de doble entrada
tabla_frame = tk.Frame(root)
tabla_frame.pack(pady=20)

mostrar_tabla_semanal()

# Ejecutar la GUI
root.mainloop()
