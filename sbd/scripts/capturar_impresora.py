import ssl
import json
import csv
import threading
from datetime import datetime
import paho.mqtt.client as mqtt

# --- CONFIGURACIÓN DE LAS IMPRESORAS ---
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

CSV_FILE = "dataset_bambu_multi_printer.csv"
csv_lock = threading.Lock()

# --- 2. GESTIÓN DE FILAMENTO CON AMS (AQUÍ VA EL BLOQUE) ---
materiales_por_impresora = {}

def extract_ams_tray_type(data, printer_sn):
    """Extrae el tipo de filamento activo considerando el AMS y los mensajes delta."""
    global materiales_por_impresora

    if printer_sn not in materiales_por_impresora:
        materiales_por_impresora[printer_sn] = "Desconocido"

    tray_now = data.get("tray_now")
    ams_data = data.get("ams", {})
    
    # Lectura si viene el bloque AMS en el JSON
    if isinstance(ams_data, dict) and "ams" in ams_data:
        try:
            for ams_unit in ams_data.get("ams", []):
                for tray in ams_unit.get("tray", []):
                    if str(tray.get("id")) == str(tray_now):
                        tray_type = tray.get("tray_type")
                        if tray_type:
                            materiales_por_impresora[printer_sn] = tray_type
                            return tray_type
        except Exception:
            pass

    # Carrete externo de respaldo (puerto 254)
    if str(tray_now) == "254":
        vt_tray = data.get("vt_tray", {})
        if isinstance(vt_tray, dict) and vt_tray.get("tray_type"):
            materiales_por_impresora[printer_sn] = vt_tray.get("tray_type")
            return materiales_por_impresora[printer_sn]

    # Devolver el último valor conocido si es un mensaje delta
    return materiales_por_impresora[printer_sn]


# --- 3. FUNCIONES DE CAPTURA Y CONEXIÓN ---
def initialize_csv():
    """Crea la cabecera si el archivo no existe."""
    try:
        with open(CSV_FILE, "x", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "printer_name", "serial_number", "gcode_state",
                "mc_print_stage", "tray_type", "mc_percent", "layer_num",
                "total_layer_num", "nozzle_temp", "bed_temp"
            ])
    except FileExistsError:
        pass

def create_mqtt_client(printer_info):
    printer_name = printer_info["name"]
    ip = printer_info["ip"]
    sn = printer_info["sn"]
    access_code = printer_info["access_code"]
    topic = f"device/{sn}/report"

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"✅ [{printer_name}] Conectado exitosamente ({ip})")
            client.subscribe(topic)
        else:
            print(f"❌ [{printer_name}] Error de conexión: {rc}")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if "print" in payload:
                data = payload["print"]
                timestamp = datetime.utcnow().isoformat()
                
                # Extracción con la nueva función AMS
                gcode_state = data.get("gcode_state", "N/A")
                mc_print_stage = data.get("mc_print_stage", "N/A")
                tray_type = extract_ams_tray_type(data, sn)
                mc_percent = data.get("mc_percent", 0)
                layer_num = data.get("layer_num", 0)
                total_layer_num = data.get("total_layer_num", 0)
                nozzle_temp = data.get("nozzle_temper", 0.0)
                bed_temp = data.get("bed_temper", 0.0)

                row = [
                    timestamp, printer_name, sn, gcode_state, mc_print_stage,
                    tray_type, mc_percent, layer_num, total_layer_num,
                    nozzle_temp, bed_temp
                ]

                # Escritura segura con bloqueo entre hilos
                with csv_lock:
                    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(row)

                print(f"[{timestamp[:19]}] {printer_name} | Mat: {tray_type} | Capa: {layer_num}/{total_layer_num} ({mc_percent}%) | Temp: {nozzle_temp}°C")

        except Exception as e:
            print(f"Error procesando mensaje de {printer_name}: {e}")

    client = mqtt.Client(client_id=f"recorder_{printer_name}_{sn}")
    client.username_pw_set(username="bblp", password=access_code)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(ip, 8883, keepalive=60)
        client.loop_forever()
    except Exception as e:
        print(f"❌ Error en la conexión con {printer_name}: {e}")

# --- 4. EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    initialize_csv()

    threads = []
    for p in PRINTERS:
        t = threading.Thread(target=create_mqtt_client, args=(p,), daemon=True)
        threads.append(t)
        t.start()

    print(f"🚀 Capturando telemetría de {len(PRINTERS)} impresoras en paralelo...")
    print(f"📁 Archivo destino: {CSV_FILE}")
    print("Pulsa Ctrl + C para detener la recolección.\n")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n🛑 Captura finalizada por el usuario.")