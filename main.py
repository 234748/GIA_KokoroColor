import serial
import threading
import time
import sys
import asyncio
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

SERIAL_PORT = "/dev/ttyACM0"  # USBシリアルポート
BAUD_RATE = 9600

DEVICE_NAME = "Hue Go"  # 実際のデバイス名に置き換えてください

SERVICE_UUID = "932c32bd-0000-47a2-835a-a8d455b859dd"
CHARACTERISTIC_ON_OFF = "932c32bd-0002-47a2-835a-a8d455b859dd"
CHARACTERISTIC_COLOR = "932c32bd-0005-47a2-835a-a8d455b859dd"

RECONNECT_DELAY = 5.0  # 再接続前に待つ時間（秒）


def map_color(heart_rate: int, humidity: int) -> tuple:
    # 心拍数と湿度から対応するRGB色を返す
    if heart_rate >= 130:
        if humidity >= 90:
            return (255, 0, 0)    # 赤
        elif humidity >= 80:
            return (255, 69, 0)   # 赤橙
        elif humidity >= 70:
            return (255, 165, 0)  # 橙
        elif humidity >= 60:
            return (255, 215, 0)  # 黄橙
        else:
            return (0, 255, 0)
    elif heart_rate >= 100:
        if humidity >= 90:
            return (199, 21, 133) # 赤紫
        elif humidity >= 80:
            return (255, 105, 180)# パステル赤
        elif humidity >= 70:
            return (255, 182, 193)# パステル橙
        elif humidity >= 60:
            return (255, 255, 0)  # 黄
        else:
            return (0, 255, 0)
    elif heart_rate >= 70:
        if humidity >= 90:
            return (128, 0, 128)   # 紫
        elif humidity >= 80:
            return (173, 216, 230) # パステル青
        elif humidity >= 70:
            return (144, 238, 144) # パステル緑
        elif humidity >= 60:
            return (0, 255, 127)   # きみどり
        else:
            return (0, 255, 0)
    elif heart_rate >= 40:
        if humidity >= 90:
            return (138, 43, 226)  # 青紫
        elif humidity >= 80:
            return (0, 0, 255)     # 青
        elif humidity >= 70:
            return (0, 255, 255)   # 青緑
        elif humidity >= 60:
            return (0, 255, 0)     # 緑
        else:
            return (0, 255, 0)
    else:
        return (0, 255, 0)


async def scan_for_device(name: str) -> str:
    #特定の名前を持つBLEデバイスをスキャンし、アドレスを返す
    print(f"Scanning for BLE devices named '{name}'...")
    devices = await BleakScanner.discover(timeout=10.0)
    for device in devices:
        print(f"Found device: {device.name}, Address: {device.address}")
        if device.name == name:
            print(f"Device '{name}' found with address: {device.address}")
            return device.address
    print(f"Device '{name}' not found.")
    return None


def read_serial(loop: asyncio.AbstractEventLoop, data_queue: asyncio.Queue):
    #シリアルポートからデータを読み取り、キューに格納するスレッド関数
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print("Serial port connected.")
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) < 2:
                    print(f"Invalid data format: {line}")
                    continue
                try:
                    heart_rate = int(parts[0])
                    humidity = int(parts[1])
                    asyncio.run_coroutine_threadsafe(
                        data_queue.put((heart_rate, humidity)),
                        loop
                    )
                except ValueError:
                    print(f"Invalid data values: '{line}'")
            time.sleep(0.1)
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        if 'ser' in locals() and ser.is_open:
            ser.close()
        sys.exit()


class HueGoController:
    def __init__(self, address: str, data_queue: asyncio.Queue):
        #Hue Goデバイス制御用クラス
        self.address = address
        self.data_queue = data_queue
        self.last_color = (0, 255, 0)  # 初期色(例)
        self._disconnected_event = None

    async def fade_to_color(self, client: BleakClient, old_color: tuple, new_color: tuple, steps: int = 30, interval: float = 0.05):
        #旧色から新色へ徐々にフェードする
        old_r, old_g, old_b = old_color
        new_r, new_g, new_b = new_color

        for i in range(1, steps + 1):
            r = int(old_r + (new_r - old_r) * (i / steps))
            g = int(old_g + (new_g - old_g) * (i / steps))
            b = int(old_b + (new_b - old_b) * (i / steps))

            color_command = bytearray([1, r, g, b])
            try:
                await client.write_gatt_char(CHARACTERISTIC_COLOR, color_command, response=False)
            except BleakError as e:
                print(f"Failed to update color in fade: {e}")
                break
            await asyncio.sleep(interval)

    def disconnected_callback(self, _client: BleakClient):
        #デバイス切断時に呼ばれるコールバック
        print("Device disconnected!")
        if self._disconnected_event:
            self._disconnected_event.set()

    async def connect_and_run(self):
        #デバイスに接続し、シリアルデータに応じて色をフェードで変更する  
        #切断時は自動再接続を試みる
        while True:
            try:
                async with BleakClient(self.address) as client:
                    connected = await client.is_connected()
                    if not connected:
                        print("Failed to connect to the device.")
                        await asyncio.sleep(RECONNECT_DELAY)
                        continue

                    print(f"Connected to {DEVICE_NAME}")

                    self._disconnected_event = asyncio.Event()
                    client.set_disconnected_callback(self.disconnected_callback)

                    while not self._disconnected_event.is_set():
                        heart_rate, humidity = await self.data_queue.get()
                        print(f"Received data - Heart Rate: {heart_rate}, Humidity: {humidity}")
                        new_color = map_color(heart_rate, humidity)
                        await self.fade_to_color(client, self.last_color, new_color, steps=50, interval=0.05)
                        self.last_color = new_color

                # withを抜けた時点で接続がなくなったため再接続試行
                print("Connection lost, attempting to reconnect...")

            except BleakError as e:
                print(f"BLE connection error: {e}")

            await asyncio.sleep(RECONNECT_DELAY)


async def main():
    data_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    # シリアル読み取りスレッドの起動
    serial_thread = threading.Thread(
        target=read_serial,
        args=(loop, data_queue),
        daemon=True
    )
    serial_thread.start()

    # デバイススキャン
    address = await scan_for_device(DEVICE_NAME)
    if not address:
        print("Device not found. Exiting.")
        return

    # HueGoコントローラ生成・実行
    controller = HueGoController(address, data_queue)
    await controller.connect_and_run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting.")
