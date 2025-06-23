import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QCheckBox, QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QListWidget, QAbstractItemView, QHeaderView, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QColor
import numpy as np
from AdsReaderWriter import ADSReaderWriter
from DelayTrigger import DelayTrigger
from MissionBuffer import MissionBuffer
import pyads

JNT_NUM=7
MES_NUM=22
txtpath = "testPoints8.txt"
class CommunicationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Go Point Tool v1.0.4.1")
        self.setGeometry(100, 100, 1100, 750)

        app_font = QFont("Segoe UI", 9)
        QApplication.setFont(app_font)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

        self.create_connection_control(left_layout)
        self.create_state_group(left_layout)
        self.create_control_panel(left_layout)
        self.create_mission_points(right_layout)
        self.create_test_state_group(right_layout)

        self.init_variables()

        self.visible_control_timer = QTimer(self)
        self.visible_control_timer.setInterval(30)
        self.visible_control_timer.timeout.connect(self.visible_control_tick)

        self.ads_update_timer = QTimer(self)
        self.ads_update_timer.setInterval(30)
        self.ads_update_timer.timeout.connect(self.ads_update_tick)


        self.init_ui_state()

        self.init_data_grids()
        self.load_settings()

        self.adsrw = ADSReaderWriter()
        self.adsrw_motion = ADSReaderWriter()

    def init_variables(self):
        self.inst_test_state = 0
        self.inst_test_state_pre = 0
        self.cur_arm_pos = np.zeros(JNT_NUM)
        self.communication_start = False
        self.test_on_flag = False
        self.test_off_flag = False
        self.next_test_flag = False
        self.pre_test_flag = False
        self.test_switch_visible = True
        self.end_test_flag = False


        default_buffer = np.loadtxt(txtpath, delimiter=",")
        self.mission_buf = MissionBuffer(default_buffer)
        self.start_trig = DelayTrigger(2)
        self.cur_cmd_pos = self.mission_buf.get_cur_buffer()


        self.running_state = 0
        self.inst_type = np.zeros(4, dtype=np.uint16)
        self.inst_state = np.zeros(4, dtype=np.uint16)
        self.self_test_flag = False
        self.ready_flag = False
        self.recover_flag = False
        self.clear_flag = False
        self.error_list = np.zeros(20, dtype=np.uint32)
        self.error_list_dsp = np.zeros(20, dtype=np.uint32)

        self.dev_ratio = 1.0
        self.dev_ratio_r = 1.0
        self.result_file = "result.txt"

    def load_settings(self):
        self.net_id = "10.1.233.139.1.1"
        self.port = 855
        #self.point_file_path = "testPoints8.txt"
        #self.result_file_path = "result.txt"

    def create_connection_control(self, layout):
        connection_group = QWidget()
        connection_layout = QHBoxLayout(connection_group)
        connection_layout.setContentsMargins(5, 5, 5, 5)

        self.net_connection = QCheckBox("Connected")
        self.net_connection.setEnabled(False)
        self.net_connection.setFixedHeight(30)

        self.but_net = QPushButton("Connect")
        self.but_net.setFixedSize(100, 35)
        self.but_net.clicked.connect(self.but_net_clicked)

        connection_layout.addWidget(self.net_connection)
        connection_layout.addWidget(self.but_net)
        connection_layout.addStretch()

        layout.addWidget(connection_group)

    def create_state_group(self, layout):
        """创建状态组"""
        self.state_group = QGroupBox("State group")
        state_layout = QGridLayout(self.state_group)
        state_layout.setContentsMargins(10, 15, 10, 15)
        state_layout.setSpacing(10)

        self.state_lab = QLabel("Running State")
        self.state_box = QLineEdit()
        self.state_box.setReadOnly(True)
        self.state_box.setFixedHeight(30)

        self.self_test_but = QPushButton("Self Test")
        self.clear_but = QPushButton("Clear")
        self.recover_but = QPushButton("Recover")
        self.but_ready = QPushButton("Ready")

        for button in [self.self_test_but, self.clear_but, self.recover_but, self.but_ready]:
            button.setFixedHeight(35)
            button.setStyleSheet("""
                        QPushButton {
                            background-color: #4A6572;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #5D7B8C;
                }
                QPushButton:pressed {
                    background-color: #344955;
                }
            """)

        self.self_test_but.clicked.connect(self.self_test_but_clicked)
        self.clear_but.clicked.connect(self.clear_but_clicked)
        self.recover_but.clicked.connect(self.recover_but_clicked)
        self.but_ready.clicked.connect(self.but_ready_clicked)

        self.txb_in_type1 = QLineEdit()
        self.txb_in_type2 = QLineEdit()
        self.txb_in_type3 = QLineEdit()
        self.txb_in_type4 = QLineEdit()

        for txb in [self.txb_in_type1, self.txb_in_type2, self.txb_in_type3, self.txb_in_type4]:
            txb.setReadOnly(True)
            txb.setFixedSize(50, 30)
            txb.setAlignment(Qt.AlignCenter)

        self.txb_in_state1 = QLineEdit()
        self.txb_in_state2 = QLineEdit()
        self.txb_in_state3 = QLineEdit()
        self.txb_in_state4 = QLineEdit()

        for txb in [self.txb_in_state1, self.txb_in_state2, self.txb_in_state3, self.txb_in_state4]:
            txb.setReadOnly(True)
            txb.setFixedSize(50, 30)
            txb.setAlignment(Qt.AlignCenter)

        self.error_lst = QListWidget()
        self.error_lst.setFixedHeight(120)

        state_layout.addWidget(self.state_lab, 0, 0)
        state_layout.addWidget(self.state_box, 0, 1, 1, 3)

        state_layout.addWidget(self.self_test_but, 1, 0)
        state_layout.addWidget(self.but_ready, 1, 1)
        state_layout.addWidget(self.clear_but, 1, 2)
        state_layout.addWidget(self.recover_but, 1, 3)

        state_layout.addWidget(QLabel("Input Type"), 2, 0)
        state_layout.addWidget(self.txb_in_type1, 2, 1)
        state_layout.addWidget(self.txb_in_type2, 2, 2)
        state_layout.addWidget(self.txb_in_type3, 2, 3)
        state_layout.addWidget(self.txb_in_type4, 2, 4)

        state_layout.addWidget(QLabel("Input State"), 3, 0)
        state_layout.addWidget(self.txb_in_state1, 3, 1)
        state_layout.addWidget(self.txb_in_state2, 3, 2)
        state_layout.addWidget(self.txb_in_state3, 3, 3)
        state_layout.addWidget(self.txb_in_state4, 3, 4)

        state_layout.addWidget(self.error_lst, 4, 0, 1, 5)

        layout.addWidget(self.state_group)

    def create_control_panel(self, layout):
        """创建控制面板"""
        self.control_group = QGroupBox("Control Panel")
        control_layout = QGridLayout(self.control_group)
        control_layout.setContentsMargins(15, 15, 15, 15)
        control_layout.setSpacing(15)

        self.lab_arm_idx = QLabel("ArmIdx")
        self.cbx_arm_num = QComboBox()
        self.cbx_arm_num.addItems(["1", "3", "4"])
        self.cbx_arm_num.setCurrentIndex(0)
        self.cbx_arm_num.setFixedWidth(60)

        self.but_test_on = QPushButton("TestOn")
        self.but_test_off = QPushButton("TestOff")
        self.but_start_test = QPushButton("NxtPoint")
        self.but_pre_point = QPushButton("PrePoint")
        self.but_end_test = QPushButton("End Test")

        control_buttons = [
            self.but_test_on, self.but_test_off,
            self.but_start_test, self.but_pre_point,
            self.but_end_test
        ]

        for button in control_buttons:
            button.setFixedSize(120, 40)
            button.setStyleSheet("""
                        QPushButton {
                            background-color: #4A6572;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #5D7B8C;
                        }
                        QPushButton:pressed {
                    background-color: #344955;
                }
            """)

        self.but_test_on.clicked.connect(self.but_test_on_clicked)
        self.but_test_off.clicked.connect(self.but_test_off_clicked)
        self.but_start_test.clicked.connect(self.next_test_clicked)
        self.but_pre_point.clicked.connect(self.pre_test_clicked)
        self.but_end_test.clicked.connect(self.but_end_test_clicked)

        control_layout.addWidget(self.lab_arm_idx, 0, 0)
        control_layout.addWidget(self.cbx_arm_num, 0, 1)

        control_layout.addWidget(self.but_test_on, 1, 0)
        control_layout.addWidget(self.but_start_test, 1, 1)

        control_layout.addWidget(self.but_test_off, 2, 0)
        control_layout.addWidget(self.but_pre_point, 2, 1)

        control_layout.addWidget(self.but_end_test, 3, 0, 1, 2)

        layout.addWidget(self.control_group)

    def create_mission_points(self, layout):
        """创建任务点表格"""
        self.mission_group = QGroupBox("Mission Points")
        mission_layout = QVBoxLayout(self.mission_group)

        self.dg_mission_point = QTableWidget(22, 3)
        headers = ["0", "1", "2"]
        self.dg_mission_point.setHorizontalHeaderLabels(headers)

        self.dg_mission_point.verticalHeader().setVisible(False)
        self.dg_mission_point.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dg_mission_point.setAlternatingRowColors(True)
        self.dg_mission_point.setStyleSheet("""
                    QTableWidget {
                        gridline-color: #D0D0D0;
                        background-color: #FFFFFF;
                        alternate-background-color: #F5F5F5;
                    }
                    QHeaderView::section {
                        background-color: #4A6572;
                        color: white;
                        padding: 4px;
                        font-weight: bold;
                        border: 1px solid #3A4A5A;
                    }
                """)
        mission_layout.addWidget(self.dg_mission_point)
        layout.addWidget(self.mission_group)

    def create_test_state_group(self, layout):
        """创建测试状态组"""
        self.state_group = QGroupBox("Test State")
        state_layout = QGridLayout(self.state_group)
        state_layout.setContentsMargins(15, 15, 15, 15)
        state_layout.setSpacing(15)

        self.lab_test_state = QLabel("TestState")
        self.txb_test_state = QLineEdit()
        self.txb_test_state.setReadOnly(True)
        self.txb_test_state.setFixedHeight(30)

        self.lab_plan_state = QLabel("PlanState")
        self.txb_plan_state = QLineEdit()
        self.txb_plan_state.setReadOnly(True)
        self.txb_plan_state.setFixedHeight(30)

        self.lab_mis_index = QLabel("MissionIndex")
        self.txb_mis_index = QLineEdit()
        self.txb_mis_index.setReadOnly(True)
        self.txb_mis_index.setFixedHeight(30)

        # 任务时间
        self.lab_mis_te = QLabel("te")
        self.txb_mis_te = QLineEdit()
        self.txb_mis_te.setReadOnly(True)
        self.txb_mis_te.setFixedHeight(30)

        self.lab_mis_tn = QLabel("tn")
        self.txb_mis_tn = QLineEdit()
        self.txb_mis_tn.setReadOnly(True)
        self.txb_mis_tn.setFixedHeight(30)

        self.lab_mis_n = QLabel("N")
        self.txb_mis_n = QLineEdit()
        self.txb_mis_n.setReadOnly(True)
        self.txb_mis_n.setFixedHeight(30)

        self.lab_qs = QLabel("StartPos")
        self.dg_qs = QTableWidget(7, 1)
        self.dg_qs.verticalHeader().setVisible(False)
        self.dg_qs.horizontalHeader().setVisible(False)
        self.dg_qs.setFixedWidth(150)

        self.lab_qe = QLabel("EndPos")
        self.dg_qe = QTableWidget(7, 1)
        self.dg_qe.verticalHeader().setVisible(False)
        self.dg_qe.horizontalHeader().setVisible(False)
        self.dg_qe.setFixedWidth(150)

        # 布局
        state_layout.addWidget(self.lab_test_state, 0, 0)
        state_layout.addWidget(self.txb_test_state, 0, 1)

        state_layout.addWidget(self.lab_plan_state, 1, 0)
        state_layout.addWidget(self.txb_plan_state, 1, 1)

        state_layout.addWidget(self.lab_mis_index, 2, 0)
        state_layout.addWidget(self.txb_mis_index, 2, 1)

        state_layout.addWidget(self.lab_mis_te, 3, 0)
        state_layout.addWidget(self.txb_mis_te, 3, 1)

        state_layout.addWidget(self.lab_mis_tn, 4, 0)
        state_layout.addWidget(self.txb_mis_tn, 4, 1)

        state_layout.addWidget(self.lab_mis_n, 5, 0)
        state_layout.addWidget(self.txb_mis_n, 5, 1)

        state_layout.addWidget(self.lab_qs, 0, 2)
        state_layout.addWidget(self.dg_qs, 1, 2, 5, 1)

        state_layout.addWidget(self.lab_qe, 0, 3)
        state_layout.addWidget(self.dg_qe, 1, 3, 5, 1)

        layout.addWidget(self.state_group)

    def init_ui_state(self):
        """初始化UI状态"""
        self.control_group.setVisible(False)
        self.state_group.setVisible(False)
        self.state_group.setVisible(True)

        self.txb_test_state.setText("0")
        self.txb_plan_state.setText("0")
        self.txb_mis_index.setText("0")
        self.txb_mis_te.setText("0")
        self.txb_mis_tn.setText("0")
        self.txb_mis_n.setText("0")

        self.state_box.setText("0")

        # 设置输入类型和状态
        self.txb_in_type1.setText("0")
        self.txb_in_type2.setText("0")
        self.txb_in_type3.setText("0")
        self.txb_in_type4.setText("0")

        self.txb_in_state1.setText("0")
        self.txb_in_state2.setText("0")
        self.txb_in_state3.setText("0")
        self.txb_in_state4.setText("0")

        self.error_lst.addItem("No errors detected")

        self.visible_control_timer.start()
        self.ads_update_timer.start()

    def init_data_grids(self):
        """初始化数据表格"""
        for i in range(6):
            self.dg_qs.setItem(i, 0, QTableWidgetItem("0.0"))
            self.dg_qe.setItem(i, 0, QTableWidgetItem("0.0"))

        '''self.dg_mission_point.setRowCount(22)
        self.dg_mission_point.setColumnCount(3)
        for i in range(22):
            for j in range(3):
                self.dg_mission_point.setItem(i, j, QTableWidgetItem(str(self.mission_buf.get_buffer_data(i,j))))
'''
        self.load_settings()
        matrix = np.loadtxt(txtpath, delimiter=',', dtype="float")
        rows, cols = matrix.shape
        self.dg_mission_point.setRowCount(rows)
        self.dg_mission_point.setColumnCount(cols)
        for i in range(rows):
            for j in range(cols):
                self.dg_mission_point.setItem(i, j, QTableWidgetItem(str(matrix[i][j])))




    def read_matrix_ftxt(self, file_path):
        """从文本文件读取矩阵数据"""
        try:
            if not os.path.exists(file_path):
                return None

            data = np.loadtxt(file_path, delimiter=',')
            return data
        except Exception as e:
            print(f"Error reading matrix from file: {e}")
            return None

    def dev_ratio_set(self):
        """设置设备比例"""
        file_name = "devRatio.txt"
        dev_ratio_txt_buffer = self.read_matrix_ftxt(file_name)
        if dev_ratio_txt_buffer is not None and dev_ratio_txt_buffer.shape[0] >= 2:
            self.dev_ratio = dev_ratio_txt_buffer[0, 0]
            self.dev_ratio_r = dev_ratio_txt_buffer[1, 0]
        else:
            self.dev_ratio = 1.0
            self.dev_ratio_r = 1.0
        if self.adsrw_motion.try_connect(self.net_id, self.ports):
            for i in range(4):
                symbol_new_roll = f"MAIN.hT.Arm[{i}].test_newRoll"
                symbol_new_roll_r = f"MAIN.hT.Arm[{i}].test_newRoll_R"

                self.adsrw_motion.write_value(symbol_new_roll, self.dev_ratio)
                self.adsrw_motion.write_value(symbol_new_roll_r, self.dev_ratio_r)

    def dev_ratio_recover(self):
        if self.adsrw_motion.try_connect(self.net_id, self.ports):
            for i in range(4):
                symbol_new_roll = f"MAIN.hT.Arm[{i}].test_newRoll"
                symbol_new_roll_r = f"MAIN.hT.Arm[{i}].test_newRoll_R"

                self.adsrw_motion.write_value(symbol_new_roll, 1.0)
                self.adsrw_motion.write_value(symbol_new_roll_r, 1.0)

    def but_net_clicked(self):
        """网络连接按钮点击事件"""
        if not self.communication_start:
            self.but_net.setText("Connecting...")
            self.but_net.setEnabled(False)
            QApplication.processEvents()
            if self.adsrw.try_connect(self.net_id, self.port):
                self.communication_start = True
                self.but_net.setText("Disconnect")
                self.net_connection.setChecked(True)
                self.but_net.setStyleSheet("background-color: #F44336; color: white;")
                self.control_group.setVisible(True)
                self.state_group.setVisible(True)
                self.ads_update_timer.start()
                QMessageBox.information(self, "连接成功", "已成功连接到PLC")
            else:
                self.but_net.setText("Connect")
                self.but_net.setEnabled(True)
                self.net_connection.setChecked(False)
                QMessageBox.warning(self, "连接失败", "无法连接到PLC，请检查网络设置")
        else:
            self.communication_start = False
            if self.adsrw.plc:
                self.adsrw.plc.close()
            self.adsrw.is_connected = False
            self.but_net.setText("Connect")
            self.net_connection.setChecked(False)
            self.but_net.setStyleSheet("")

    def but_test_on_clicked(self):
        self.test_on_flag = True
        self.test_off_flag = False

    def but_test_off_clicked(self):
        self.test_off_flag = True
        self.test_on_flag = False

    def next_test_clicked(self):
        self.next_test_flag = True
        self.test_switch_visible = False

    def pre_test_clicked(self):
        self.pre_test_flag = True
        self.test_switch_visible = False

    def but_end_test_clicked(self):
        self.end_test_flag = True

    def self_test_but_clicked(self):
        self.self_test_flag = True

    def clear_but_clicked(self):
        self.clear_flag = True

    def recover_but_clicked(self):
        self.recover_flag = True

    def but_ready_clicked(self):
        self.ready_flag = True

    def visible_control_tick(self):
        """可见控制定时器事件"""
        if self.communication_start:
            self.net_connection.setChecked(True)
            self.ads_update_timer.start()
            self.but_net.setVisible(False)
            self.control_group.setVisible(True)
            self.state_group.setVisible(True)
            #self.state_group.setVisible(True)
            if self.inst_test_state == 0:
                self.but_start_test.setVisible(True)
                self.but_pre_point.setVisible(True)
            else:
                self.but_start_test.setVisible(False)
                self.but_pre_point.setVisible(False)

            # 更新机器人状态
            self.state_box.setText(str(self.running_state))
            self.txb_in_type1.setText(hex(self.inst_type[0])[2:].upper())
            self.txb_in_type2.setText(hex(self.inst_type[1])[2:].upper())
            self.txb_in_type3.setText(hex(self.inst_type[2])[2:].upper())
            self.txb_in_type4.setText(hex(self.inst_type[3])[2:].upper())
            self.txb_in_state1.setText(str(self.inst_state[0]))
            self.txb_in_state2.setText(str(self.inst_state[1]))
            self.txb_in_state3.setText(str(self.inst_state[2]))
            self.txb_in_state4.setText(str(self.inst_state[3]))
            # 更新错误列表
            error_list_changed = False
            for i in range(20):
                if self.error_list[i] != self.error_list_dsp[i]:
                    error_list_changed = True
                    break
            if error_list_changed:
                self.error_lst.clear()
                self.error_list_dsp = self.error_list.copy()
                for i in range(20):
                    self.error_lst.addItem(hex(self.error_list_dsp[i])[2:].upper())
        else:
            self.net_connection.setChecked(False)
            self.ads_update_timer.stop()

    def ads_update_tick(self):
        """ADS更新定时器事件"""
        if not self.communication_start or not self.adsrw.is_connected:
            return

            # 读取值
        test_sub_state = self.adsrw.read_value("HumanInterface.TestHmiDataOut.testState", pyads.PLCTYPE_INT)
        if test_sub_state is not None:
            self.txb_test_state.setText(str(test_sub_state))

        inst_test_state_new = self.adsrw.read_value("HumanInterface.TestHmiDataOut.planState", pyads.PLCTYPE_INT)
        if inst_test_state_new is not None:
            if inst_test_state_new != self.inst_test_state:
                self.inst_test_state_pre = self.inst_test_state
                self.inst_test_state = inst_test_state_new
            self.txb_plan_state.setText(str(self.inst_test_state))

        self.txb_mis_index.setText(str(self.mission_buf.get_cur_idx()))
        received_cmd = self.adsrw.read_array("HumanInterface.TestHmiDataOut.receivedMessage", MES_NUM, pyads.PLCTYPE_REAL)
        if received_cmd is not None:
            for i in range(JNT_NUM):
                precision = 4 if i == 0 else 3
                qs_value = round(received_cmd[i], precision)
                qe_value = round(received_cmd[i + JNT_NUM], precision)
                if i < self.dg_qs.rowCount():
                    if self.dg_qs.item(i, 0) is None:
                        self.dg_qs.setItem(i, 0, QTableWidgetItem(str(qs_value)))
                    else:
                        self.dg_qs.item(i, 0).setText(str(qs_value))
                if i < self.dg_qe.rowCount():
                    if self.dg_qe.item(i, 0) is None:
                        self.dg_qe.setItem(i, 0, QTableWidgetItem(str(qe_value)))
                    else:
                        self.dg_qe.item(i, 0).setText(str(qe_value))
            self.txb_mis_te.setText(str(received_cmd[2 * JNT_NUM]))
            self.txb_mis_tn.setText(str(received_cmd[2 * JNT_NUM + 1]))
            self.txb_mis_n.setText(str(received_cmd[2 * JNT_NUM + 2]))

        running_state = self.adsrw.read_value("HumanInterface.TestHmiDataOut.robotState.runningState", pyads.PLCTYPE_INT)
        if running_state is not None:
            self.running_state = running_state

        inst_type = self.adsrw.read_array("HumanInterface.TestHmiDataOut.robotState.instType", 4, np.uint16)
        if inst_type is not None:
            self.inst_type = inst_type

        inst_state = self.adsrw.read_array("HumanInterface.TestHmiDataOut.robotState.instState", 4, np.uint16)
        if inst_state is not None:
            self.inst_state = inst_state

        # 读取错误信息
        for i in range(20):
            symbol_name = f"Warn.errorInfo[{i}].LogInfo"
            error_info = self.adsrw.read_value(symbol_name, np.uint32)
            if error_info is not None:
                self.error_list[i] = error_info

        write_flag = False
        if self.test_on_flag:
            write_flag = True
            self.test_on_flag = False
        self.adsrw.write_value("HumanInterface.TestHmiDataIn.TestOn", write_flag)
        write_flag = False

        if self.test_off_flag:
            write_flag = True
            self.test_off_flag = False
        self.adsrw.write_value("HumanInterface.TestHmiDataIn.TestOff", write_flag)

        arm_idx = int(self.cbx_arm_num.currentText()) - 1
        if arm_idx < 0: arm_idx = 0
        if arm_idx > 3: arm_idx = 3
        self.adsrw.write_value("HumanInterface.TestHmiDataIn.ArmIdx", arm_idx)

        start_test_flag = False
        self.cur_cmd_pos = self.mission_buf.get_cur_buffer()
        if self.next_test_flag:
            start_test_flag = True
            self.cur_cmd_pos = self.mission_buf.get_next_buffer()
            self.next_test_flag = False

        if self.pre_test_flag:
            start_test_flag = True
            self.cur_cmd_pos = self.mission_buf.get_pre_buffer()
            self.pre_test_flag = False

        start_test_flag = self.start_trig.update(start_test_flag)
        self.adsrw.write_value("HumanInterface.TestHmiDataIn.flag[0]", start_test_flag)
        self.adsrw.write_array("HumanInterface.TestHmiDataIn.message", self.cur_cmd_pos)

        end_test = False
        if self.end_test_flag:
            self.end_test_flag = False
            end_test = True
        self.adsrw.write_value("HumanInterface.TestHmiDataIn.flag[1]", end_test)
        write_flag = False
        if self.self_test_flag:
            write_flag = True
            self.self_test_flag = False

        # 机器人状态控制
        self.adsrw.write_value("HumanInterface.MasterTestButton", write_flag)
        write_flag = False
        if self.ready_flag:
            write_flag = True
            self.ready_flag = False

        self.adsrw.write_value("HumanInterface.readyButton", write_flag)
        write_flag = False
        if self.clear_flag:
            write_flag = True
            self.clear_flag = False
        self.adsrw.write_value("HumanInterface.clearErrButton", write_flag)
        write_flag = False
        if self.recover_flag:
            write_flag = True
            self.recover_flag = False

        self.adsrw.write_value("HumanInterface.errRecoverButton", write_flag)

    def closeEvent(self, event):
        """关闭窗口事件处理"""
        self.dev_ratio_recover()
        if self.adsrw.plc and self.adsrw.is_connected:
            self.adsrw.plc.close()
        event.accept()



if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    window = CommunicationApp()
    window.show()
    sys.exit(app.exec_())
