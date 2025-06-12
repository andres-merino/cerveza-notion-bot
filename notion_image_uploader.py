import base64
from datetime import datetime
from openai import OpenAI 
from notion_client import Client
from keys import OPENAI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID
import sys

client = OpenAI(api_key=OPENAI_API_KEY)
notion = Client(auth=NOTION_TOKEN)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def analizar_imagen_cerveza(ruta_imagen):

    base64_image = encode_image(ruta_imagen)

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", 
                 "text": "Extrae la siguiente información de todas las cervezas que encuentres en esta imagen: Nombre, Grados de alcohol (ABV) (sin porcentaje), IBU." 
                },
                {"type": "input_image",
                 "image_url": f"data:image/jpeg;base64,{base64_image}",
                },
            ],
        }],
    )
    
    prompt = """
Del siguiente texto, extrae una lista con:
- Nombre de la cerveza
- Grados de alcohol (ABV) (sin porcentaje)
- IBU

Devuelve un JSON de cervezas con esta estructura:
{
    "cervezas": [
        {
            "nombre": "Nombre de la cerveza",
            "abv": "Grados de alcohol (ABV) (sin porcentaje)",
            "ibu": "IBU"
        },
        ...
    ]
}
""" + response.output_text
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return eval(response.choices[0].message.content)

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
