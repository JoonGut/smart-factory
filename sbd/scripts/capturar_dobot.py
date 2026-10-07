import socket
import struct
import csv
import time
from datetime import datetime

# ==============================================================================
# 1. CONFIGURACIÓN DEL ROBOT Y DEL ARCHIVO
# ==============================================================================
DOBOT_IP = "192.168.15.10"        # IP asignada a la caja de control del Dobot CR5A
PORT_FEEDBACK = 30004            # Puerto TCP nativo para telemetría en tiempo real
CSV_FILE = "dataset_dobot_cr5a.csv"
SAMPLE_INTERVAL = 0.5            # Intervalo de muestreo en segundos (0.5s = 2 lecturas/seg)

# ==============================================================================
# 2. INICIALIZACIÓN DEL DATASET (CABECERA DEL CSV)
# ==============================================================================
def initialize_csv():
    """Crea la estructura del archivo CSV con sus columnas si aún no existe."""
    try:
        with open(CSV_FILE, "x", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",       # Fecha y hora en formato ISO UTC
                "robot_mode",      # Estado operativo (7: Running, 5: Standby, 9: Error, etc.)
                # --- Posición Cartesiana de la Herramienta (mm y grados) ---
                "pos_x", "pos_y", "pos_z", "rot_rx", "rot_ry", "rot_rz",
                # --- Temperaturas de los Motores (°C) - Clave para fallos térmicos ---
                "j1_temp", "j2_temp", "j3_temp", "j4_temp", "j5_temp", "j6_temp",
                # --- Corriente Eléctrica (A) - Clave para detectar desgaste/fricción ---
                "j1_current", "j2_current", "j3_current", "j4_current", "j5_current", "j6_current"
            ])
            print(f"📁 Dataset creado exitosamente: '{CSV_FILE}'")
    except FileExistsError:
        print(f"📁 Añadiendo filas al dataset existente: '{CSV_FILE}'")

# ==============================================================================
# 3. DECODIFICACIÓN DEL PAQUETE BINARIO (TCP 30004)
# ==============================================================================
def parse_cr5a_feedback(data):
    """
    Decodifica el paquete binario de 1440 bytes que envía la controladora Dobot.
    Utiliza 'struct.unpack' para convertir los bytes en valores numéricos.
    """
    if len(data) < 1440:
        return None

    try:
        # Estado actual del robot (entero de 64 bits / 8 bytes)
        robot_mode = struct.unpack("q", data[24:32])[0]

        # Posición espacial del efector final (6 floats de doble precisión = 48 bytes)
        tool_vector = struct.unpack("6d", data[440:488])

        # Temperaturas internas de los 6 servomotores (°C)
        joint_temps = struct.unpack("6d", data[632:680])

        # Consumo de corriente eléctrica de cada articulación (Amperios)
        joint_currents = struct.unpack("6d", data[680:728])

        return {
            "robot_mode": robot_mode,
            "tool_vector": [round(v, 2) for v in tool_vector],
            "joint_temps": [round(t, 1) for t in joint_temps],
            "joint_currents": [round(c, 3) for c in joint_currents]
        }
    except Exception as e:
        print(f"⚠️ Error al decodificar la trama: {e}")
        return None

# ==============================================================================
# 4. BUCLE DE CAPTURA Y REGISTRO DE DATOS
# ==============================================================================
def main():
    initialize_csv()
    
    print(f"🔌 Conectando al puerto de telemetría {DOBOT_IP}:{PORT_FEEDBACK}...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    
    try:
        sock.connect((DOBOT_IP, PORT_FEEDBACK))
        print("✅ Conexión establecida. Iniciando captura de telemetría...")
        print("Pulsa Ctrl + C en la terminal para detener el proceso de recolección.\n")

        last_sample_time = 0

        while True:
            # Recibir la trama de datos desde el buffer del socket
            data = sock.recv(1440)
            current_time = time.time()

            # Control de frecuencia de muestreo (SAMPLE_INTERVAL)
            if current_time - last_sample_time >= SAMPLE_INTERVAL:
                telemetry = parse_cr5a_feedback(data)
                
                if telemetry:
                    timestamp = datetime.utcnow().isoformat()
                    
                    # Construir la fila para el CSV
                    row = [
                        timestamp,
                        telemetry["robot_mode"],
                        *telemetry["tool_vector"],
                        *telemetry["joint_temps"],
                        *telemetry["joint_currents"]
                    ]

                    # Escritura en el archivo CSV
                    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(row)

                    last_sample_time = current_time

                    # Confirmación visual en consola
                    print(
                        f"[{timestamp[:19]}] Modo: {telemetry['robot_mode']} | "
                        f"Pos XYZ: {telemetry['tool_vector'][:3]} mm | "
                        f"Temps: {telemetry['joint_temps']} °C | "
                        f"Corrientes: {telemetry['joint_currents']} A"
                    )

    except KeyboardInterrupt:
        print("\n🛑 Captura detenda correctamente por el usuario. Datos a salvo.")
    except socket.timeout:
        print(f"\n❌ Tiempo de espera agotado. Verifica que la IP {DOBOT_IP} sea alcanzable.")
    except Exception as e:
        print(f"\n❌ Error de comunicación con el Dobot CR5A: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    main()