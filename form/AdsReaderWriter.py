import pyads
import numpy as np


class ADSReaderWriter:
    def __init__(self):
        self.plc = None
        self.is_connected = False

    def try_connect(self, net_id, port, timeout=2.0):
        try:
            self.plc = pyads.Connection(net_id, port)
            self.plc.set_timeout(int(timeout*1000))
            self.plc.open()
            try:
                test_value = self.plc.read_by_name('HumanInterface.TestHmiDataOut.testState',pyads.PLCTYPE_INT)
                if test_value is not None:
                    self.is_connected = True
                    return self.plc
            except:
                self.plc.close()
                self.is_connected = False
                return None
            self.is_connected = True
            return self.plc
        except:
            self.is_connected = False
            self.plc.close()
            return None

    def read_value(self, symbol_name, dtype):
        if not self.is_connected or self.plc is None:
            return None

        try:
            return self.plc.read_by_name(symbol_name, dtype)
        except:
            return None

    def read_array(self, symbol_name, length, dtype):
        if not self.is_connected or self.plc is None:
            return None

        try:
            return self.plc.read_by_name(symbol_name, dtype * length)
        except:
            return None

    def write_value(self, symbol_name, value):
        if not self.is_connected or self.plc is None:
            return False

        try:
            self.plc.write_by_name(symbol_name, value)
            return True
        except:
            return False

    '''def write_array(self, symbol_name, data_array):
        if not self.is_connected or self.plc is None:
            return False

        try:
            if isinstance(data_array, np.ndarray):
                row = data_array.shape[0]
                col = data_array.shape[1]
                flat_data = data_array.flatten().tolist()
            else:
                row = len(data_array)
                col = len(data_array[0]) if row > 0 else 0
                flat_data = []
                for i in range(row):
                    for j in range(col):
                        flat_data.append(data_array[i][j])
            element_names = []
            for i in range(row):
                for j in range(col):
                    # 使用逗号分隔索引，如 "arr[1,2]"
                    element_names.append(f"{symbol_name}[{i},{j}]")
            if len(flat_data) != len(element_names):
                return False
            try:
                for i in range(len(element_names)):
                    self.plc.write_by_name(element_names[i], flat_data[i], pyads.PLCYTPE_REAL)
                return True
            except:
                return False
        except:
            return False'''

    def write_array(self, symbol_name, current_array):
        if not self.is_connected or self.plc is None:
            return False

        try:
            self.plc.write_by_name(symbol_name, current_array, pyads.PLCTYPE_REAL * len(current_array))
        except:
            return False



