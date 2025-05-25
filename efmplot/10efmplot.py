import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QThread, pyqtSignal, QIODevice
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
import pyqtgraph as pg
import time
import argparse
import asyncio
import websockets
import signal
import json
import numpy as np


class SerialReaderThread(QThread):
    data_received = pyqtSignal(list)

    def __init__(self, port_name, baudrate=9600, log_file=None, log_prefix="EFM"):
        super().__init__()
        self.port = QSerialPort()
        self.port.setPortName(port_name)
        self.port.setBaudRate(baudrate)
        self.port.readyRead.connect(self.read_data)
        print("Serial read buffer size:", self.port.readBufferSize())
        self.log_file = log_file
        if not self.log_file:
            self.log_file = log_prefix + "log_" + time.strftime("%Y%m%d_%H%M%S", time.gmtime()) + "_UTC.csv"
        self.log_file_handle = open(self.log_file, 'a')
        if not self.port.open(QIODevice.ReadOnly):
            print(f"Failed to open port {port_name}")

    def read_data(self):
        while self.port.canReadLine():
            data = self.port.readLine().data().decode().strip()
            try:
                self.data_received.emit([int(x) for x in data.split(',')])
                self.log_data(data)
            except ValueError as e:
                print(e)

    def log_data(self, value):
        timestamp = time.time()
        log_entry = f"{timestamp},{value}\n"
        self.log_file_handle.write(log_entry)
        self.log_file_handle.flush()

    def stop(self):
        self.port.close()
        self.log_file_handle.close()
        self.quit()
        self.wait()


class WebsocketThread(QThread):
    message_received = pyqtSignal(str)
    broadcast_message = pyqtSignal(str)

    def __init__(self, host, port, parent=None):
        super(WebsocketThread, self).__init__(parent)
        self.host = host
        self.port = port
        self.loop = None
        self.clients = set()
        self.running = True
        self.broadcast_message.connect(self.handle_broadcast_message)

    async def handler(self, websocket, path):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                print(f"Received: {message}")
        finally:
            self.clients.remove(websocket)

    def handle_broadcast_message(self, message):
        asyncio.run_coroutine_threadsafe(self.send_message_to_all(message), self.loop)

    async def send_message_to_all(self, message):
        if self.clients:
            await asyncio.gather(*(client.send(message) for client in self.clients))

    async def run_server(self):
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.run_server())

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.running = False


class MainWindow(QMainWindow):
    serial_thread = None

    def __init__(self, srt):
        super().__init__()

        self.setWindowTitle("Serial Data Plotter")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)

        self.plot_widget.setYRange(-10, 65546)
        self.plot_widget.setXRange(0, 105)
        self.plot_widget.showGrid(x=True, y=True)

        self.raw_plots = []
        self.last_curve = None   # výrazně zvýrazněný poslední průběh
        self.avg_plot = None     # průměrný průběh
        self.text_item = None   # textový popisek do grafu

        self.history = []
        self.max_history = 30

        self.serial_thread = srt
        self.serial_thread.data_received.connect(self.add_data)
    
    def add_data(self, value):
        data_array = np.array(value) - self.Y_OFFSET
        self.history.append(data_array)
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
        for plot in self.raw_plots:
            self.plot_widget.removeItem(plot)
        self.raw_plots = []
    
        # Smazat staré svislé čáry
        for line in self.delta_lines:
            self.plot_widget.removeItem(line)
        self.delta_lines = []
    
        # Historické průběhy (kromě posledního)
        for h in self.history[:-1]:
            plot = self.plot_widget.plot(h, pen=pg.mkPen(color=(180, 180, 180, 60), width=1))
            self.raw_plots.append(plot)
    
        # Zvýrazněný poslední průběh
        if self.last_curve:
            self.plot_widget.removeItem(self.last_curve)
        self.last_curve = self.plot_widget.plot(self.history[-1], pen=pg.mkPen(color=(255, 215, 0), width=3))
    
        # Klouzavý průměr - šířka 4
        if self.avg_plot:
            self.plot_widget.removeItem(self.avg_plot)
        avg_data = None
        if len(self.history) >= 2:
            min_len = min(len(h) for h in self.history)
            trimmed_data = np.array([h[:min_len] for h in self.history])
            avg_data = np.mean(trimmed_data, axis=0)
            self.avg_plot = self.plot_widget.plot(avg_data, pen=pg.mkPen(color=(0, 255, 255), width=4))
        else:
            self.avg_plot = None
    
        # Svislé čáry pro indexy 11 a 29
        max_x = 0
        if len(self.history) > 0:
            last_data = self.history[-1]
            max_x = len(last_data) - 1
            if max_x >= 29:
                for idx in [11, 29]:
                    line = pg.InfiniteLine(pos=idx, angle=90, pen=pg.mkPen(color=(200, 200, 255, 150), width=2, style=pg.QtCore.Qt.DashLine))
                    self.plot_widget.addItem(line)
                    self.delta_lines.append(line)
    
        # Text
        if self.text_item:
            self.plot_widget.removeItem(self.text_item)
    
        avg_delta = None
        last_delta = None
        if len(self.history) > 0:
            last_data = self.history[-1]
            if avg_data is not None and len(avg_data) >= 30:
                avg_delta = int(round(avg_data[29] - avg_data[11]))
            if len(last_data) >= 30:
                last_delta = int(round(last_data[29] - last_data[11]))
    
        txt = f"Avg Δ: {avg_delta if avg_delta is not None else '-------':>7}   Last Δ: {last_delta if last_delta is not None else '-------':>7}"
    
        self.text_item = pg.TextItem(txt, color='w', anchor=(0,0))
        font = self.text_item.textItem.font()
        font.setPointSize(16)
        self.text_item.setFont(font)
        self.plot_widget.addItem(self.text_item)
        self.text_item.setPos(0, 0)
        
    def closeEvent(self, event):
        self.serial_thread.stop()
        event.accept()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_file", help="Log file to write data to", default=None)
    parser.add_argument("--log_prefix", default="EFM_THUNDERMILL01")
    parser.add_argument("--gui", action="store_true", help="Enable GUI mode")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port to read data from")
    parser.add_argument("--baudrate", default=9600, type=int, help="Baudrate for serial port")
    parser.add_argument("--websocket", action="store_true", help="Enable websocket mode")
    parser.add_argument("--ws_port", default=1234, help="Websocket port ")
    parser.add_argument("--ws_min_period", default=0.25, type=float, help="Minimum period between websocket messages in seconds")

    args = parser.parse_args()

    app = QApplication(sys.argv)

    last_ws_message = time.time()

    serial_thread = SerialReaderThread(args.port, args.baudrate, args.log_file, args.log_prefix)
    serial_thread.start()

    if args.websocket:
        ws = WebsocketThread("0.0.0.0", args.ws_port)
        ws.start()
        ws.message_received.connect(print)

        def process_data(data):
            nonlocal last_ws_message
            if (time.time() - last_ws_message) < args.ws_min_period:
                return
            last_ws_message = time.time()
            payload = {
                "type": "round",
                "data": data
            }
            ws.broadcast_message.emit(json.dumps(payload))

        serial_thread.data_received.connect(process_data)

    if args.gui:
        window = MainWindow(srt=serial_thread)
        window.show()

    def signal_handler(signal, frame):
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

