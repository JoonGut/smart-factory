import ssl
import json
import csv
import threading
import os
from datetime import datetime
import paho.mqtt.client as mqtt

# ==============================================================================
# 1. CONFIGURACIÓN DE RUTAS Y ARCHIVOS (GUARDA EN sbd/datos/)
# ==============================================================================

# Averiguamos la carpeta exacta donde está guardado este script (sbd/scripts)
RUTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# Subimos un nivel ("..") a la carpeta raíz "sbd" y luego entramos a la carpeta "datos"
CARPETA_DATA = os.path.abspath(os.path.join(RUTA_SCRIPT, "..", "datos"))

# Si la carpeta "sbd/datos" no existe en tu ordenador, el programa la crea automáticamente
os.makedirs(CARPETA_DATA, exist_ok=True)

# Definimos la ruta completa donde se guardará el archivo CSV dentro de "sbd/datos/"
CSV_FILE = os.path.join(CARPETA_DATA, "dataset_bambu_multi_printer.csv")

# ==============================================================================
# 2. CONFIGURACIÓN DE LAS IMPRESORAS
# ==============================================================================
PRINTERS = [
    {
        "name": "Bambu_H2D_1",
        "ip": "192.168.15.32",
        "sn": "0948BB5B1600363",
        "access_code": "bb7eb044"
    },
    {
        "name": "Bambu_H2D_2",
        "ip": "192.168.15.209",
        "sn": "0948BB5B1601428",
        "access_code": "86bf9c6a"
    }
]

# Un "cerrojo" para evitar que dos impresoras escriban en el CSV a la vez y lo rompan
csv_lock = threading.Lock()

# ==============================================================================
# 3. MEMORIA INDIVIDUAL PARA CADA IMPRESORA (AMS Y MATERIALES)
# ==============================================================================
# Diccionario para guardar el estado de cada impresora usando su Número de Serie (SN)
estado_impresoras = {}

def extract_ams_tray_type(data, printer_sn):
    """
    Esta función lee los mensajes de la impresora y averigua qué material se usa.
    Si la impresora envía un mensaje sin el campo de material, recuerda el último
    material conocido para no poner "Desconocido".
    """
    # Si es la primera vez que leemos esta impresora, le creamos su espacio en memoria
    if printer_sn not in estado_impresoras:
        estado_impresoras[printer_sn] = {
            "trays": {},               # Guarda qué plástico hay en cada hueco del AMS
            "current_slot": "Desconocido",   # Hueco del AMS que se está usando
            "current_material": "Desconocido" # Nombre del material (ej: PLA, ABS)
        }

    estado = estado_impresoras[printer_sn]
    trays = estado["trays"]

    # PASO A: Guardar/actualizar la lista de materiales cargados en el AMS
    if "ams" in data:
        ams_info = data["ams"]
        ams_list = ams_info.get("ams", []) if isinstance(ams_info, dict) else ams_info
        
        if isinstance(ams_list, list):
            for ams_unit in ams_list:
                try:
                    ams_id = int(ams_unit.get("id", 0)) # 0 para AMS 1, 1 para AMS 2
                except (ValueError, TypeError):
                    ams_id = 0

                for tray in ams_unit.get("tray", []):
                    tray_id = tray.get("id")
                    tray_type = tray.get("tray_type", "")
                    if tray_id is not None and tray_type:
                        try:
                            # Mapeo de ranuras:
                            # AMS 1 -> Ranuras 0, 1, 2, 3
                            # AMS 2 -> Ranuras 4, 5, 6, 7
                            global_slot_idx = str((ams_id * 4) + int(tray_id))
                            trays[global_slot_idx] = tray_type
                        except (ValueError, TypeError):
                            pass

    # PASO B: Si la impresora usa el soporte trasero (sin AMS)
    vt_tray = data.get("vt_tray", {})
    if isinstance(vt_tray, dict) and vt_tray.get("tray_type"):
        trays["254"] = vt_tray.get("tray_type") # El código 254 es la bobina trasera

    # PASO C: Buscar qué ranura está imprimiendo en este instante
    raw_tray_now = data.get("tray_now")
    if raw_tray_now is None and isinstance(data.get("ams"), dict):
        raw_tray_now = data["ams"].get("tray_now")
    if raw_tray_now is None:
        raw_tray_now = data.get("tray_tar") or data.get("tar_tray")

    # PASO D: Si encontramos la ranura activa, la actualizamos en memoria
    if raw_tray_now is not None:
        tray_str = str(raw_tray_now).strip()
        if tray_str in ["254", "255", "-1"]:
            if tray_str == "254":
                estado["current_slot"] = "254"
        else:
            try:
                slot_idx = str(int(float(tray_str)))
                estado["current_slot"] = slot_idx
            except ValueError:
                pass

    # PASO E: Miramos qué material corresponde a la ranura activa
    slot_actual = estado["current_slot"]
    if slot_actual in trays:
        estado["current_material"] = trays[slot_actual]

    # Devolvemos el material activo
    return estado["current_material"]


# ==============================================================================
# 4. CREACIÓN DEL CSV Y CONEXIÓN MQTT
# ==============================================================================
def initialize_csv():
    """
    Comprueba si el CSV ya existe en 'sbd/data/'.
    Si no existe, lo crea y escribe la primera fila con las cabeceras.
    """
    try:
        # Modo "x" = crear nuevo archivo, lanza error si ya existe
        with open(CSV_FILE, "x", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "printer_name", "serial_number", "gcode_state",
                "mc_print_stage", "tray_type", "mc_percent", "layer_num",
                "total_layer_num", "nozzle_temp", "bed_temp"
            ])
        print(f"📁 Archivo CSV creado correctamente en: '{CSV_FILE}'")
    except FileExistsError:
        # Si ya existía, continúa guardando datos ahí
        print(f"📄 Guardando datos en el CSV existente: '{CSV_FILE}'")


def create_mqtt_client(printer_info):
    """
    Se conecta a una impresora vía red (MQTT) y guarda cada dato recibido en el CSV.
    """
    printer_name = printer_info["name"]
    ip = printer_info["ip"]
    sn = printer_info["sn"]
    access_code = printer_info["access_code"]
    topic = f"device/{sn}/report"

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"✅ [{printer_name}] Conectado correctamente ({ip})")
            client.subscribe(topic) # Se suscribe para recibir los mensajes
        else:
            print(f"❌ [{printer_name}] Error de conexión (Código: {rc})")

    def on_message(client, userdata, msg):
        """Se ejecuta CADA VEZ que la impresora manda un mensaje"""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            
            # Comprobamos si hay información de impresión ("print")
            if "print" in payload:
                data = payload["print"]
                timestamp = datetime.utcnow().isoformat() # Fecha y hora actual
                
                # Extraemos los valores del JSON
                gcode_state = data.get("gcode_state", "N/A")
                mc_print_stage = data.get("mc_print_stage", "N/A")
                tray_type = extract_ams_tray_type(data, sn) # Extrae el plástico del AMS
                mc_percent = data.get("mc_percent", 0)
                layer_num = data.get("layer_num", 0)
                total_layer_num = data.get("total_layer_num", 0)
                nozzle_temp = float(data.get("nozzle_temper", 0.0))
                bed_temp = float(data.get("bed_temper", 0.0))

                # Preparamos la fila que guardaremos en el archivo CSV
                row = [
                    timestamp, printer_name, sn, gcode_state, mc_print_stage,
                    tray_type, mc_percent, layer_num, total_layer_num,
                    nozzle_temp, bed_temp
                ]

                # ESCRITURA SEGURA: Bloqueamos el archivo para que las 2 impresoras no escriban a la vez
                with csv_lock:
                    # Modo "a" = append (añadir datos al final sin borrar nada)
                    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(row)

                # Mostramos la línea informativa en pantalla
                print(f"[{timestamp[:19]}] {printer_name} | Mat: {tray_type} | Capa: {layer_num}/{total_layer_num} ({mc_percent}%) | Temp: {nozzle_temp}°C")

        except Exception as e:
            print(f"⚠️ Error procesando mensaje de {printer_name}: {e}")

    # Creación del cliente MQTT para la impresora
    client = mqtt.Client(client_id=f"recorder_{printer_name}_{sn}")
    client.username_pw_set(username="bblp", password=access_code)
    
    # Configuración de cifrado SSL para Bambu Lab
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(ip, 8883, keepalive=60)
        client.loop_forever() # Mantiene la conexión escuchando datos
    except Exception as e:
        print(f"❌ Error en la conexión con {printer_name}: {e}")


# ==============================================================================
# 5. INICIO DEL PROGRAMA
# ==============================================================================
if __name__ == "__main__":
    # 1. Prepara la carpeta sbd/data y el archivo CSV
    initialize_csv()

    # 2. Crea un hilo de ejecución por cada impresora (para que funcionen en paralelo)
    threads = []
    for p in PRINTERS:
        t = threading.Thread(target=create_mqtt_client, args=(p,), daemon=True)
        threads.append(t)
        t.start()

    print(f"🚀 Capturando datos de {len(PRINTERS)} impresoras en paralelo...")
    print(f"📁 Guardando archivo CSV en: {CSV_FILE}")
    print("Para detener la captura, presiona Ctrl + C en la terminal.\n")

    # 3. Mantiene el script en marcha
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n🛑 Captura detenida por el usuario.")