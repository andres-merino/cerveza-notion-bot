import base64
from datetime import datetime
from openai import OpenAI 
from notion_client import Client
from keys import OPENAI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID
import sys
import json

client = OpenAI(api_key=OPENAI_API_KEY)
notion = Client(auth=NOTION_TOKEN)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def analizar_imagen_cerveza(ruta_imagen):
    
    base64_image = encode_image(ruta_imagen)
    
    # URL de la imagen en formato base64
    image_url = f"data:image/jpeg;base64,{base64_image}"
    
    # Instrucciones para el modelo (System Prompt)
    system_prompt = """
    Eres un asistente experto en análisis de menús de cervezas.
    Analiza la imagen proporcionada y extrae la siguiente información de cada cerveza que encuentres:
    - Nombre de la cerveza
    - Grados de alcohol (ABV) (sin el símbolo de porcentaje)
    - IBU (Unidades Internacionales de Amargor)

    Si la información de ABV o IBU no se encuentra visible en la imagen para alguna cerveza, asigna el valor 0 en su lugar.
    Debes devolver estrictamente un objeto JSON con la estructura solicitada, que contenga un array de cervezas.
    """

    # Llamada única al modelo (visión y extracción JSON)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {
                    "type": "text", 
                    "text": "Extrae la información de todas las cervezas visibles en esta imagen y devuélvela como un objeto JSON con el array 'cervezas' y las claves 'nombre', 'abv' e 'ibu' para cada cerveza.",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
            ]},
        ],
        # Configuración para forzar la respuesta en formato JSON
        response_format={"type": "json_object"}, 
        temperature=0.0
    )
    
    # La respuesta es un string JSON que necesita ser cargado en Python
    json_str = response.choices[0].message.content
    return json.loads(json_str)

def enviar_cervezas_a_notion(datos, lugar):
    # Fecha actual sin hora ISO 8601
    fecha_actual = datetime.now().strftime("%Y-%m-%d")

    for cerveza in datos["cervezas"]:
        nombre = cerveza.get("nombre", "Sin nombre")
        abv = float(cerveza.get("abv", 0))
        ibu = int(cerveza.get("ibu", 0))

        propiedades = {
            "Nombre": {
                "title": [{"text": {"content": nombre}}]
            },
            "Grados": {
                "number": abv
            },
            "IBU": {
                "number": ibu
            },
            "Lugar": {
                "multi_select": [{"name": lugar}]
            },
            "Fecha": {
                "date": {
                    "start": fecha_actual,
                }
            },
        }

        try:
            notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties=propiedades
            )
        except Exception as e:
            raise Exception(f"Error al crear la página en Notion: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python notion_image_uploader.py <ruta_imagen> <lugar>")
        sys.exit(1)

    ruta_img = sys.argv[1]
    lugar = sys.argv[2]
    datos = analizar_imagen_cerveza(ruta_img)
    try:
        enviar_cervezas_a_notion(datos, lugar)
        print("Imagen procesada y enviada a Notion con éxito.")
    except Exception as e:
        print(f"Error al enviar la información a Notion: {e}")
