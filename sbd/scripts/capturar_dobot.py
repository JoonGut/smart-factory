import socket
import struct
import csv
import time
import os
from datetime import datetime

# ==============================================================================
# 1. CONFIGURACIÓN DE RUTAS Y ARCHIVOS (GUARDA EN sbd/data/ O sbd/datos/)
# ==============================================================================

# Averiguamos la carpeta exacta donde está guardado este script (sbd/scripts)
RUTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# Subimos un nivel ("..") a la carpeta "sbd" y luego entramos a "datos"
CARPETA_DATA = os.path.abspath(os.path.join(RUTA_SCRIPT, "..", "datos"))

# Si la carpeta "sbd/datos" no existe en tu ordenador, el programa la crea automáticamente
os.makedirs(CARPETA_DATA, exist_ok=True)

# Ruta completa donde se guardará el archivo CSV
CSV_FILE = os.path.join(CARPETA_DATA, "dataset_dobot_cr5a.csv")

# ==============================================================================
# 2. CONFIGURACIÓN DE RED Y MUESTREO DEL ROBOT DOBOT CR5A
# ==============================================================================
DOBOT_IP = "192.168.15.10"     # IP asignada al robot Dobot en la red local
PORT_FEEDBACK = 30004         # Puerto TCP por el que el Dobot envía datos continuamente
SAMPLE_INTERVAL = 0.5         # Tiempo de espera entre lecturas (0.5 segundos = 2 datos por segundo)

# ==============================================================================
# 3. CREACIÓN DEL ARCHIVO CSV (CABECERA)
# ==============================================================================
def initialize_csv():
    """
    Comprueba si el archivo CSV ya existe en la carpeta 'sbd/data/'.
    Si no existe, lo crea y le pone la primera fila con los nombres de las columnas.
    """
    try:
        # Modo "x" = Crear archivo nuevo. Si ya existe, salta al bloque FileExistsError
        with open(CSV_FILE, "x", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",       # Fecha y hora exacta de la lectura
                "robot_mode",      # Estado del robot (7: Trabajando, 5: En espera, 9: Error...)
                # --- Posición y Orientación de la punta del robot (X, Y, Z, Rx, Ry, Rz) ---
                "pos_x", "pos_y", "pos_z", "rot_rx", "rot_ry", "rot_rz",
                # --- Temperatura de los 6 motores (°C) ---
                "j1_temp", "j2_temp", "j3_temp", "j4_temp", "j5_temp", "j6_temp",
                # --- Consumo eléctrico de los 6 motores (Amperios) ---
                "j1_current", "j2_current", "j3_current", "j4_current", "j5_current", "j6_current"
            ])
            print(f"📁 Dataset creado correctamente en: '{CSV_FILE}'")
    except FileExistsError:
        # Si el archivo ya existía de antes, no lo borra, sigue añadiendo datos abajo
        print(f"📄 Guardando datos en el dataset existente: '{CSV_FILE}'")

# ==============================================================================
# 4. DECODIFICADOR DE DATOS DEL DOBOT (TRADUCE BYTES A NÚMEROS)
# ==============================================================================
def parse_cr5a_feedback(data):
    """
    El robot manda un paquete de datos en binario (1440 bytes).
    Esta función usa 'struct.unpack' para traducir esos bytes a números decimales entendibles.
    """
    # Si el paquete que llegó está incompleto (mide menos de 1440 bytes), lo ignoramos
    if len(data) < 1440:
        return None

    try:
        # Extraemos el modo de trabajo del robot (un entero de 8 bytes situado entre la posición 24 y 32)
        robot_mode = struct.unpack("q", data[24:32])[0]

        # Extraemos las 6 coordenadas de posición/orientación (6 números decimales 'double')
        tool_vector = struct.unpack("6d", data[440:488])

        # Extraemos las temperaturas de los 6 motores (°C)
        joint_temps = struct.unpack("6d", data[632:680])

        # Extraemos el consumo eléctrico / corriente de los 6 motores (Amperios)
        joint_currents = struct.unpack("6d", data[680:728])

        # Devolvemos un diccionario con todos los valores ya redondeados para que sean limpios
        return {
            "robot_mode": robot_mode,
            "tool_vector": [round(v, 2) for v in tool_vector],
            "joint_temps": [round(t, 1) for t in joint_temps],
            "joint_currents": [round(c, 3) for c in joint_currents]
        }
    except Exception as e:
        print(f"⚠️ Error al traducir los datos del robot: {e}")
        return None

# ==============================================================================
# 5. BUCLE PRINCIPAL DE CAPTURA
# ==============================================================================
def main():
    # 1. Prepara el archivo CSV dentro de sbd/data/
    initialize_csv()
    
    print(f"🔌 Intentando conectar con el Dobot en {DOBOT_IP}:{PORT_FEEDBACK}...")
    
    # Creamos la conexión de red (Socket TCP)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0) # Si tarda más de 5 segundos en responder, da error
    
    try:
        # Conectamos con el robot
        sock.connect((DOBOT_IP, PORT_FEEDBACK))
        print("✅ Conectado al Dobot CR5A. Capturando datos en tiempo real...")
        print("Para detener la captura en cualquier momento, presiona Ctrl + C en la terminal.\n")

        last_sample_time = 0 # Guarda el momento de la última lectura realizada

        # Bucle infinito: escucha continuamente al robot
        while True:
            # Recibimos el paquete de 1440 bytes que manda el robot
            data = sock.recv(1440)
            current_time = time.time()

            # Comprobamos si ha pasado el tiempo configurado en SAMPLE_INTERVAL (0.5s)
            if current_time - last_sample_time >= SAMPLE_INTERVAL:
                # Decodificamos el paquete de datos
                telemetry = parse_cr5a_feedback(data)
                
                if telemetry:
                    # Obtenemos la hora actual en formato estándar (ISO UTC)
                    timestamp = datetime.utcnow().isoformat()
                    
                    # Preparamos la fila completa que guardaremos en el CSV
                    row = [
                        timestamp,
                        telemetry["robot_mode"],
                        *telemetry["tool_vector"],
                        *telemetry["joint_temps"],
                        *telemetry["joint_currents"]
                    ]

                    # Abrimos el CSV en modo "a" (append = añadir fila al final sin borrar nada)
                    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(row)

                    # Actualizamos el reloj de la última muestra guardada
                    last_sample_time = current_time

                    # Mostramos un resumen del dato guardado por la terminal
                    print(
                        f"[{timestamp[:19]}] Modo: {telemetry['robot_mode']} | "
                        f"Pos XYZ: {telemetry['tool_vector'][:3]} mm | "
                        f"Temps: {telemetry['joint_temps']} °C | "
                        f"Corrientes: {telemetry['joint_currents']} A"
                    )

    except KeyboardInterrupt:
        # Se activa si pulsas Ctrl + C en la terminal
        print("\n🛑 Captura detenida por el usuario. Todos los datos han quedado guardados de forma segura.")
    except socket.timeout:
        print(f"\n❌ Tiempo de espera agotado. Comprueba que el robot esté encendido y con la IP {DOBOT_IP}.")
    except Exception as e:
        print(f"\n❌ Se produjo un error en la conexión con el Dobot: {e}")
    finally:
        # Cerramos la conexión de red al terminar
        sock.close()

# Ejecuta la función principal si abrimos este script directamente
if __name__ == "__main__":
    main()