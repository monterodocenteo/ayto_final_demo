import json
import os
import sys
from bokeh.io import curdoc
from bokeh.models import GeoJSONDataSource, HoverTool, Tap, CategoricalColorMapper
from bokeh.plotting import figure
from bokeh.models import Button, CustomJS, Select, TextInput, Button, Div, TextInput, FileInput, Spacer
from bokeh.layouts import column, row
from bokeh.palettes import Category20
import geopandas as gpd
import csv
from collections import defaultdict
import time
from bokeh.io.export import export_png
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import platform
from bokeh.server.server import Server
import webbrowser

# CARGA DATOS

# Variable global para almacenar el REFCAT seleccionado
selected_refcat = None

usos = {
    "A": "Almacén - Estacionamiento",
    "V": "Residencial",
    "I": "Industrial",
    "O": "Oficinas",
    "C": "Comercial",
    "K": "Deportivo",
    "T": "Espectáculos",
    "G": "Ocio y Hostelería",
    "Y": "Sanidad y Beneficencia",
    "E": "Cultural",
    "R": "Religioso",
    "M": "Obras de urbanización y jardinería, suelos sin edificar",
    "P": "Edificio singular",
    "B": "Almacén agrario",
    "J": "Industrial agrario",
    "Z": "Agrario"
}

# Cargamos RefCat + Uso como diccionario
usos_por_refcat = defaultdict(list)
with open('data/refcat_uso.csv', mode='r', encoding='utf-8') as archivo:
    lector = csv.DictReader(archivo, delimiter=';')
    for fila in lector:
        refcat = fila['RefCat'].strip()
        uso = fila['Uso'].strip()
        if refcat not in usos_por_refcat:
            usos_por_refcat[refcat] = uso
usos_por_refcat = dict(usos_por_refcat)  # opcional

# Cargar el GeoJSON
gdf = gpd.read_file("data/CONSTRU GEOJSON.json")

# Añadir columna 'Uso' al GeoDataFrame
def obtener_uso(refcat):
    usos = usos_por_refcat.get(refcat, [])
    return usos[0] if usos else None

gdf["Uso"] = gdf["REFCAT"].apply(obtener_uso)

gdf = gdf.to_crs(epsg=25830)
# Añadir columna de área
gdf["area"] = gdf.geometry.area

# Ordenar de mayor a menor área (grandes primero, pequeñas después)
gdf = gdf.sort_values("area", ascending=False)

gdf = gdf.to_crs(epsg=4326)
# Crear GeoJSONDataSource con campo 'Uso' incluido
geo_source = GeoJSONDataSource(geojson=gdf.to_json())

# Crear color_mapper según el campo Uso
usos_unicos = sorted(gdf["Uso"].dropna().unique().tolist())
usos_unicos = usos_unicos[:20]  # Bokeh Category20 admite hasta 20
color_mapper = CategoricalColorMapper(factors=usos_unicos, palette=Category20[len(usos_unicos)])

#### CONFIGURAR EXPORT PNG

# Configurar Chrome Headless
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-usb")

# Crear el navegador (solo se usa en el servidor para renderizar PNG)
driver = webdriver.Chrome(options=chrome_options)


### PASO 1 ###

header1 = Div(text='<div style="background-color:#003366; padding:10px; color:white; font-size:20px; font-weight:bold;">PASO 1 - SELECCIONE LA FINCA</div>')

# Crear figura
p = figure(title="Selecciona la finca", tools="pan,wheel_zoom,reset,tap", match_aspect=True,
           x_axis_location=None, y_axis_location=None, width=1000, height=500, background_fill_color="#f9f9f9")

renderer = p.patches(
    xs="xs",
    ys="ys",
    source=geo_source,
    fill_color={'field': 'Uso', 'transform': color_mapper},
    fill_alpha=0.7,
    line_color="black",
    line_width=0.5,
    selection_fill_color="deepskyblue",
    selection_line_color="red",
    nonselection_fill_alpha=0.1
)

for uso, color in zip(color_mapper.factors, color_mapper.palette):
    p.patches(
        xs=[[[-9999, -9998, -9998, -9999]]],  # coordenadas invisibles
        ys=[[[-9999, -9999, -9998, -9998]]],fill_color=color,
        line_color="black",
        fill_alpha=0.7,
        legend_label= usos[uso]
    )

p.legend.title = "Uso del suelo"
p.legend.label_text_font_size = "8pt"
p.legend.title_text_font_size = "10pt"
p.legend.title_text_font_style = "bold"
p.legend.location = "top_right"
p.legend.click_policy = "hide"  # permite ocultar categorías al hacer clic

hover = HoverTool(renderers=[renderer], tooltips=[("REFCAT", "@REFCAT")])
p.add_tools(hover)


# Callback para capturar selección
def callback(attr, old, new):
    global selected_refcat
    # ... (código anterior)
    # Ejemplo: guardar en un archivo
    if new:
        selected_idx = new[0]
        geojson_dict = json.loads(geo_source.geojson)  # Parsear geojson
        selected_refcat = geojson_dict["features"][selected_idx]["properties"]["REFCAT"]
        print(f"REFCAT almacenado: {selected_refcat}")  # Verificación en consola
    with open("seleccion.txt", "w") as f:
        f.write(selected_refcat)

# Conectar el evento de selección
geo_source.selected.on_change("indices", callback)

contenido1 = column(
    Div(text="<div style='margin-bottom:10px; font-size:14px;'>Seleccione una finca del mapa para comenzar el trámite.</div>"),
    p,
    sizing_mode="stretch_width",
    width=750,
    css_classes=["contenedor-mapa"]
)


boton_paso1 = Button(label="Continuar al paso 2", button_type="success", disabled=True, width=250)
boton_paso1.disabled = True

def callback_seleccion(attr, old, new):
    seleccion = geo_source.selected.indices
    if seleccion:
        boton_paso1.disabled = False
    else:
        boton_paso1.disabled = True

# Enlazamos el callback
geo_source.selected.on_change("indices", callback_seleccion)

### PASO 2 ###

# Contenido 2.1: uso == "V"
plantas_select = Select(title="¿Cuántas plantas tiene el edificio?", options=["1", "2"], width=300)
altura_input = TextInput(title="Altura del alero (en metros):", placeholder="Introduce un número", width=300)
retranq_input = TextInput(title="Retranqueo frontal (en metros):", placeholder="Introduce un número", width=300)
mensaje_altura = Div(text="")
retranqueo_resultado = Div(text="")
validar_button = Button(label="Validar altura", button_type="primary", width=250)
retr_button = Button(label="Validar retranqueo", button_type="primary", width=250)
volver_paso1_btn = Button(label="⬅ Volver al paso 1", button_type="warning", width = 250, visible = False)
boton_paso3 = Button(label="Continuar al paso 3", button_type="success", disabled=True, width=250)

def volver_a_paso1():
    contenido1.visible = True
    boton_paso1.visible = True
    contenido2_1.visible = False
    volver_paso1_btn.visible = False
    contenido2_3.visible = False
    mensaje_altura.text = ""  # limpiar mensajes de validación si quieres
    retranqueo_resultado.text = ""  # limpiar mensajes de validación si quieres
    geo_source.selected.indices = []
    boton_paso1.disabled = True
    plantas_select.value = "1"                 # valor por defecto
    altura_input.value = ""                    # campo vacío
    mensaje_altura.text = ""                   # quitar validación
    retranq_input.value = ""             # quitar resultado

flag_altura = False
flag_retranqueo = False

def habilitar_paso3():
    if flag_altura and flag_retranqueo:
        boton_paso3.disabled = False
    else:
        boton_paso3.disabled = True

def validar_altura():
    global flag_altura
    mensaje_altura.text = ""  # limpiar mensaje
    flag_altura = False
    try:
        plantas = int(plantas_select.value)
        altura = float(altura_input.value)
        
        if plantas == 1 and (altura < 2.5 or altura > 4):
            mensaje_altura.text = "❌ Error: Para 1 planta, la altura debe estar entre 2.5 y 4 metros."
        elif plantas == 2 and (altura < 5 or altura > 7):
            mensaje_altura.text = "❌ Error: Para 2 plantas, la altura debe estar entre 5 y 7 metros."
        else:
            flag_altura = True
            mensaje_altura.text = '<span style="color: green;">✅ Las alturas entran dentro de las medidas adecuadas.</span>'
    except ValueError:
        mensaje_altura.text = "❌ Error: Introduce un número válido en el campo de altura."

    habilitar_paso3()

def calcular_retranqueo():
    global flag_retranqueo
    retranqueo_resultado.text = ""
    flag_retranqueo = False
    try:
        altura = float(altura_input.value)
        retranq = float(retranq_input.value)
        resultado = altura / 2
        if retranq < 3:
            retranqueo_resultado.text = "❌ Error: El retranqueo mínimo ha de ser de 3 metros."
        elif altura >= 6 and retranq < resultado:
            retranqueo_resultado.text = f"❌ Error: El retranqueo mínimo ha de ser de {resultado} metros."
        else:
            flag_retranqueo = True
            retranqueo_resultado.text = f'<span style="color: green;">✅ El retranqueo frontal necesario es válido.</span>'

    except ValueError:
        retranqueo_resultado.text = "❌ Error: introduce un número válido en el campo de retranqueo."
    habilitar_paso3()

def avanzar_a_paso3():
    contenido2_1.visible = False
    volver_paso1_btn.visible = False
    contenido3.visible = True

validar_button.on_click(validar_altura)
volver_paso1_btn.on_click(volver_a_paso1)
retr_button.on_click(calcular_retranqueo)
boton_paso3.on_click(avanzar_a_paso3)

# Nuevo contenido 2.1 con validación
contenido2_1 = column(
    plantas_select,
    altura_input,
    validar_button,
    mensaje_altura,
    retranq_input,
    retr_button,
    retranqueo_resultado,
    boton_paso3,
    visible=False
)

# Contenido 2.3: uso == "M"
contenido2_3 = column(Div(text="No es posible tramitar una licencia para este tipo de uso."), visible = False)


##### PASO 3 ####
file_input_c1 = FileInput(accept=".pdf", width=400)
file_input_c2 = FileInput(accept=".pdf", width=400)
fichero_1 = column(
    Div(text="<div style='font-weight:bold; margin-bottom:5px;'>📎 Adjunte el estudio de gestión de residuos y demolición (PDF):</div>"),
    file_input_c1
)
fichero_2 = column(
    Div(text="<div style='font-weight:bold; margin-bottom:5px;'>📎 Adjunte el Certificado de Viabilidad Geométrica (PDF)::</div>"),
    file_input_c2
)
adjuntador_ficheros = column(Div(text="Adjunte los documentos requeridos en formato PDF:"), fichero_1, fichero_2)
volver_paso2_btn = Button(label="⬅ Volver al paso 2", button_type="warning", width = 250)
confirmar_paso3_btn = Button(label="Confirmar y enviar", button_type="success", width=250)
confirmacion_paso3 = Div(text="")

vista_admin_btn = Button(label="Pasar a vista admin", button_type="success", width=250)


def abrir_pdf(ruta_pdf):
    if platform.system() == "Darwin":       # macOS
        os.system(f"open {ruta_pdf}")
    elif platform.system() == "Windows":    # Windows
        os.startfile(ruta_pdf)
    elif platform.system() == "Linux":      # Linux
        os.system(f"xdg-open {ruta_pdf}")

def generar_pdf():
    # Crear documento
    nombre_documento = "solicitud"+selected_refcat+".pdf"
    c = canvas.Canvas(nombre_documento, pagesize=A4)

    # Añadir texto
    c.setFont("Helvetica", 12)
    c.drawImage("mapa.png", x=100, y=620, width=400, height=200)
    c.drawString(100, 600, f"Referencia Catastral: {selected_refcat}.")
    
    # Variables dinámicas
    nombre = "Juan Pérez"
    altura = float(altura_input.value)
    retranq = float(retranq_input.value)

    c.drawString(100, 580, f"Nombre: {nombre}")
    c.drawString(100, 560, f"Altura del alero: {altura} m")
    c.drawString(100, 540, f"Retranqueo: {retranq} m")

    c.drawString(100, 520, f"Estudio de gestión de residuos y demolición: {file_input_c1.filename}")
    c.drawString(100, 500, f"Certificado de Viabilidad Geométrica: {file_input_c2.filename}")

    # Guardar el archivo
    c.save()
    abrir_pdf(nombre_documento)
    sys.exit()

def confirmar_paso3():
    try:
         # Comprobamos si ambos archivos han sido cargados correctamente
        archivos_ok = bool(file_input_c1.value) and bool(file_input_c2.value)

        if archivos_ok:
            confirmacion_paso3.text = "✅ Archivos cargados. Generando PDF..."
            generar_pdf()
        else:
            confirmacion_paso3.text = "❌ Debe adjuntar ambos documentos PDF antes de continuar."
    except Exception as e:
        confirmacion_paso3.text = f"❌ Debe adjuntar ambos documentos PDF antes de continuar."

confirmar_paso3_btn.on_click(confirmar_paso3)
   
contenido3 = column(
    volver_paso2_btn,
    adjuntador_ficheros,
    Spacer(height=10),
    confirmar_paso3_btn,
    confirmacion_paso3,
    visible = False
)

def volver_a_paso2():
    contenido2_1.visible = True
    volver_paso1_btn.visible = True
    mensaje_altura.text = ""  # limpiar mensajes de validación si quieres
    retranqueo_resultado.text = ""  # limpiar mensajes de validación si quieres
    geo_source.selected.indices = []
    boton_paso1.disabled = True
    contenido3.visible = False

volver_paso2_btn.on_click(volver_a_paso2)

### LÓGICA CAMBIO PASO ###

def avanzar_a_paso2():
    export_png(p, filename="mapa.png", webdriver=driver)
    uso = usos_por_refcat[selected_refcat][0]
    contenido1.visible = False  # ocultar mapa
    boton_paso1.visible = False
    boton_paso3.disabled = True
    volver_paso1_btn.visible = True
    # Mostrar uno de los tres bloques en función del uso
    if uso == "V":
        contenido2_1.visible = True
    else:
        contenido2_3.visible = True

def abrir_html():
    webbrowser.open("vista.html")

boton_paso1.on_click(avanzar_a_paso2)
vista_admin_btn.on_click(abrir_html)

# ENCABEZADOS
header2 = Div(text='<div style="background-color:#006400; padding:10px; color:white; font-size:18px; font-weight:bold;">PASO 2 - RELLENE LAS ESPECIFICACIONES</div>')
header3 = Div(text='<div style="background-color:#09ebd7; padding:10px; color:white; font-size:18px; font-weight:bold;">PASO 3 - DOCUMENTACIÓN</div>')
separador_visual = Div(text="<hr style='margin:20px 0; border:1px solid #ddd;'>")

# LAYOUT FINAL
layout_app = column(
    header1,
    Spacer(height=10),
    contenido1,
    Spacer(height=10),
    row(boton_paso1),
    Div(text="<hr style='margin:20px 0; border:1px solid #ddd;'>"),
    header2,
    Spacer(height=10),
    volver_paso1_btn,
    contenido2_1,
    contenido2_3,
    Div(text="<hr style='margin:20px 0; border:1px solid #ddd;'>"),
    header3,
    Spacer(height=10),
    contenido3,
    vista_admin_btn
)

curdoc().add_root(layout_app)

def cerrar_programa(session_context):
    import sys
    print(f"🔌 Sesión cerrada: {session_context.id}")
    sys.exit()

curdoc().on_session_destroyed(cerrar_programa)

curdoc().title = "Formulario de Licencias"