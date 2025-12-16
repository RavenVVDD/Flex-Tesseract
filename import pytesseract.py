import pytesseract
from PIL import Image

# Configura la ruta a Tesseract si es necesario
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Cargar la imagen (asegúrate de que la ruta es correcta y apunta a un archivo de imagen)
imagen = Image.open(r'C:\Users\PC3\Desktop\Flex Tesseract\Imagenes\imagen1.jpeg')

# Extraer el texto
texto = pytesseract.image_to_string(imagen, lang='eng')

print("Texto extraído:")
print(texto)

# Diccionario de ciudades asociadas a cada cordón
cordones = {
    "primer_cordon": ["CABA", "PALERMO", "RETIRO"],
    "segundo_cordon": ["SAN MIGUEL", "MORON", "VICENTE LOPEZ"],
    "tercer_cordon": ["LA PLATA", "BERAZATEGUI", "QUILMES"],
    "cuarto_cordon": ["LUJAN", "ESCOBAR", "CAMPANA"]
}

def identificar_cordon_por_ciudad(texto):
    # Dividimos el texto en líneas para identificar el primer renglón relevante
    lineas = texto.splitlines()
    for linea in lineas:
        # Buscamos en qué cordón se encuentra la primera ciudad identificada
        for cordon, ciudades in cordones.items():
            for ciudad in ciudades:
                if ciudad in linea.upper():  # Convertimos a mayúsculas para evitar problemas de capitalización
                    return cordon
    return "cordon_no_identificado"

# Ejemplo de uso con el texto extraído
cordon = identificar_cordon_por_ciudad(texto)
print(f"Este paquete pertenece al: {cordon}")