import asyncio
import logging
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
from dearpygui.dearpygui import *

# --- Configurar logging ---
logging.basicConfig(level=logging.DEBUG)

# --- Crear Modbus Datastore ---
store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0]*100),
    co=ModbusSequentialDataBlock(0, [0]*100),
    hr=ModbusSequentialDataBlock(0, [0]*100),
    ir=ModbusSequentialDataBlock(0, [0]*100)
)
context = ModbusServerContext(slaves=store, single=True)

# --- Lista para logs ---
logs = []

# --- Mapeo de dispositivos con direcciones en formato vectorial ---
coils = {
    "UW_VALVE_POSITION": [0, 0],  # %IX0.0 -> [0][0]
    "OW_VALVE_POSITION": [1, 0],  # %IX1.0 -> [1][0]
    "UW_PLATF_VALVE_POSITION": [2, 0],  # %IX2.0 -> [2][0]
    "RUN_BARTEC": [3, 0],  # %IX3.0 -> [3][0]
    "DOW_PLATFORM": [4, 0],  # %IX4.0 -> [4][0]
    "UP_PLATFORM": [5, 0],  # %IX5.0 -> [5][0]
    "DEADMAN_INTERLOCK": [6, 0],  # %IX6.0 -> [6][0]
    "DEADMAN_SWITCH": [7, 0],  # %IX7.0 -> [7][0]
    "DEADMAN_TIMER": [8, 0],  # %IX8.0 -> [8][0]
}

inputs = {
    "ULTRA_LEFT_SENSOR": 0,
    "ULTRA_RIGHT_SENSOR": 1,
    "MAX_LIMIT_PLATF": 2,
}

# --- Funciones ---
async def run_modbus_server():
    await StartAsyncTcpServer(context, address=("192.168.56.1", 5030))

async def updating_holding_register(context):
    register_address = 0
    value = 0
    while True:
        value += 1
        context[0x00].setValues(3, register_address, [value])  # 3 = Holding Register
        await asyncio.sleep(1)

async def auto_update_gui():
    while True:
        update_log_window()
        update_device_status()
        await asyncio.sleep(1)

# Función para encender y apagar las coils
def toggle_coil(sender, app_data, user_data):
    device_name = user_data
    address = coils[device_name]  # Obtener la dirección en formato [X][Y]
    coil_address = address[0] * 10 + address[1]  # Convertir la dirección en formato Modbus (ejemplo %IX0.0 -> 0)
    new_state = get_value(f"switch_{device_name}")
    context[0x00].setValues(1, coil_address, [new_state])  # 1 = Coils
    logs.append(f"[Acción] {device_name} -> {'ON' if new_state else 'OFF'}")

def update_device_status():
    for name, address in coils.items():
        coil_address = address[0] * 10 + address[1]  # Calcula la dirección Modbus
        estado = context[0x00].getValues(1, coil_address, count=1)[0]
        set_value(f"switch_{name}", estado)
    for name, address in inputs.items():
        estado = context[0x00].getValues(2, address, count=1)[0]  # 2 = Discrete Inputs
        set_value(f"input_{name}", "Activo" if estado else "Inactivo")

def update_log_window():
    delete_item("log_text", children_only=True)
    for log in logs[-10:]:
        add_text(log, parent="log_text")

# --- Configuración de la GUI ---
def setup_gui():
    with window(tag="main_window", label="Servidor Modbus TCP", width=700, height=600):
        add_text("Logs:")
        add_child(tag="log_text", width=680, height=150, border=True)

        add_spacing(count=2)
        add_separator()
        add_spacing(count=2)

        add_text("Control de Dispositivos (Coils):")
        with child_window(width=680, height=180, border=True):
            for device_name in coils.keys():
                add_checkbox(label=device_name, tag=f"switch_{device_name}", callback=toggle_coil, user_data=device_name)

        add_spacing(count=2)
        add_separator()
        add_spacing(count=2)

        add_text("Estado de Sensores (Discrete Inputs):")
        with child_window(width=680, height=120, border=True):
            for sensor_name in inputs.keys():
                add_text(f"{sensor_name}:", tag=f"input_{sensor_name}")
    set_primary_window("main_window", True)

# --- Función principal ---
async def async_main():
    create_context()
    create_viewport(title="Servidor Modbus TCP", width=700, height=600)
    setup_gui()
    setup_dearpygui()
    show_viewport()

    # Crear tareas asincrónicas
    tasks = [
        asyncio.create_task(run_modbus_server()),
        asyncio.create_task(updating_holding_register(context)),
        asyncio.create_task(auto_update_gui())
    ]

    try:
        while is_dearpygui_running():
            render_dearpygui_frame()
            await asyncio.sleep(0.01)
    finally:
        destroy_context()
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

# --- Iniciar ---
if __name__ == "__main__":
    asyncio.run(async_main())
