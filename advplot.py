import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QThread, pyqtSignal, QIODevice
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
import pyqtgraph as pg
import time 

class SerialReaderThread(QThread):
    data_received = pyqtSignal(str)

    def __init__(self, port_name, baudrate=9600, log_file=None):
        super().__init__()
        self.port = QSerialPort()
        self.port.setPortName(port_name)
        self.port.setBaudRate(baudrate)
        self.port.readyRead.connect(self.read_data)
        self.log_file = log_file
        if not self.log_file:
            self.log_file = "EFM_log_"+time.strftime("%Y%m%d_%H%M%S", time.gmtime()) + "_UTC.csv"
        self.log_file_handle = open(self.log_file, 'a')
        if not self.port.open(QIODevice.ReadOnly):
            print(f"Failed to open port {port_name}")

    def read_data(self):
        while self.port.canReadLine():
            data = self.port.readLine().data().decode().strip()
            try:
                #print("Read data", data)
                self.data_received.emit(data)
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Serial Data Plotter")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)


        self.plot_widget.setYRange(-255, 255)
        self.plot_widget.showGrid(x=True, y=True)
        
        self.plot_data = []
        self.plot = self.plot_widget.plot(self.plot_data, pen=pg.mkPen(width=5))

        self.serial_thread = SerialReaderThread('/dev/ttyUSB0')
        self.serial_thread.data_received.connect(self.add_data)
        self.serial_thread.start()

    def add_data(self, value):
        value = [int(x)-255 for x in value.split(',')]
        #print("ADD data", value)
        self.plot.setData(value)
        #self.plot_data.append(value)
        #print(value)
        #if len(self.plot_data) > 100:
        #    self.plot_data.pop(0)

    #def update_plot(self):
    #    self.plot.setData(self.plot_data)

    def closeEvent(self, event):
        self.serial_thread.stop()
        self.plot_thread.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
