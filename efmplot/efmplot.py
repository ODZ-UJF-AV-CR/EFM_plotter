import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QThread, pyqtSignal, QIODevice
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
import pyqtgraph as pg
import time 
import sys
import argparse
from PyQt5.QtWidgets import QApplication
import asyncio
import websockets
import signal
import json

class SerialReaderThread(QThread):
    data_received = pyqtSignal(list)

    def __init__(self, port_name, baudrate=9600, log_file=None, log_prefix = "EFM"):
        super().__init__()
        self.port = QSerialPort()
        self.port.setPortName(port_name)
        self.port.setBaudRate(baudrate)
        self.port.readyRead.connect(self.read_data)
        print("Serial read buffer size:", self.port.readBufferSize())
        self.log_file = log_file
        if not self.log_file:
            self.log_file = log_prefix+"log_"+time.strftime("%Y%m%d_%H%M%S", time.gmtime()) + "_UTC.csv"
        self.log_file_handle = open(self.log_file, 'a')
        if not self.port.open(QIODevice.ReadOnly):
            print(f"Failed to open port {port_name}")

    def read_data(self):
        while self.port.canReadLine():
            data = self.port.readLine().data().decode().strip()
            try:
                #print("Read data", data)
                #self.data_received.emit([-int(x)+(65536/2) for x in data.split(',')])
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
                #self.message_received.emit(f"Received: {message}")
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


        #self.plot_widget.setYRange(-(65536/2), (65536/2))
        self.plot_widget.setYRange(-10, 65546)
        self.plot_widget.setXRange(0, 105)
        self.plot_widget.showGrid(x=True, y=True)
        
        self.plot_data = []
        self.plot = self.plot_widget.plot(self.plot_data, pen=pg.mkPen(width=5))

        #self.serial_thread = SerialReaderThread(port)
        self.serial_thread = srt
        self.serial_thread.data_received.connect(self.add_data)
        #self.serial_thread.start()

    def add_data(self, value):
        self.plot.setData(value)

    def closeEvent(self, event):
        self.serial_thread.stop()
        self.plot_thread.stop()
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
            # Nechci posilat WS zpravy prilis casto
            if (time.time() - last_ws_message) < args.ws_min_period:
                return
            
            payload = {
                "type": "round",
                "data": data
            }
            ws.broadcast_message.emit(json.dumps(payload))

        serial_thread.data_received.connect(process_data)

    if args.gui:
        window = MainWindow(srt = serial_thread)
        window.show()
            

    # Aby to slo ukoncit pomoci Ctrl+C
    def signal_handler(signal, frame):
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
