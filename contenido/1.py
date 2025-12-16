import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Scrollbar, Text
import pytesseract
from PIL import Image

# Configura la ruta a Tesseract si es necesario
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Diccionario de ciudades asociadas a cada cordón
cordones = {
    "Primer cordón": ["AVELLANEDA","HURLINGHAM", "ITUZAINGO", "LA MATANZA NORTE", "LANUS", "LOMAS DE ZAMORA", "MORON", "SAN FERNANDO", "SAN ISIDRO", "SAN MARTIN",
                      "TRES DE FEBRERO", "VICENTE LOPEZ"],
    "Segundo cordón": ["ALMIRANTE BROWN", "BERAZATEGUI", "ESTEBAN ECHEVERRIA", "EZEIZA", "FLORENCIO VARELA",
                        "JOSE C PAZ", "LA MATANZA SUR", "MALVINAS ARGENTINAS", "MERLO", "MORENO", "QUILMES", "SAN MIGUEL", "TIGRE"],
    "Tercer cordón (CABA)": ["CABA"],
    "Cuarto cordón": ["BERISSO", "DEL VISO", "DERQUI", "ENSENADA", "GENERAL RODRIGUEZ", "LA PLATA CENTRO", "LA PLATA NORTE", "LUJAN", "NORDELTA",
                      "PILAR"]
}

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
            texto = pytesseract.image_to_string(imagen, lang='eng')  # Cambiado a 'eng'
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
    else:
        messagebox.showerror("Error", "No se seleccionó ninguna imagen.")

# Configurar la ventana principal
root = tk.Tk()
root.title("Clasificador de Paquetes por Cordón")

# Crear los componentes de la GUI
label_instrucciones = tk.Label(root, text="Seleccione una o más imágenes para procesar:")
label_instrucciones.pack(pady=10)

btn_cargar = tk.Button(root, text="Cargar Imágenes", command=procesar_imagenes)
btn_cargar.pack(pady=10)

# Ejecutar la GUI
root.mainloop()
