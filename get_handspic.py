import os
import sys
import cv2
import numpy as np
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton,
                             QVBoxLayout, QHBoxLayout, QLineEdit, QFileDialog,
                             QFrame, QGroupBox)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
import pyads
import re


class CameraApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("松手照片采集")
        self.setGeometry(100, 100, 1200, 700)

        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.save_path = ""
        self.category_counters = {
            "loose_hands": 1,
            "around_hands": 1,
            "on_hands": 1
        }
        self.current_category = "loose_hands"  # 默认类别

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        left_layout = QVBoxLayout()
        self.camera_label = QLabel(self)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(1080, 720)
        self.camera_label.setText("请点击'开始采集'按钮启动摄像头")
        self.camera_label.setStyleSheet("background-color: black; color: white;")
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(self)
        self.path_edit.setPlaceholderText("请选择保存路径")
        path_btn = QPushButton("浏览", self)
        path_btn.clicked.connect(self.select_path)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(path_btn)

        category_group = QGroupBox("选择手部状态")
        category_layout = QHBoxLayout(category_group)

        self.loose_btn = QPushButton("Loose Hands", self)
        self.loose_btn.setCheckable(True)
        self.loose_btn.setChecked(True)
        self.loose_btn.clicked.connect(lambda: self.set_category("loose_hands"))
        self.around_btn = QPushButton("Around Hands", self)
        self.around_btn.setCheckable(True)
        self.around_btn.clicked.connect(lambda: self.set_category("around_hands"))

        self.on_btn = QPushButton("On Hands", self)
        self.on_btn.setCheckable(True)
        self.on_btn.clicked.connect(lambda: self.set_category("on_hands"))

        category_layout.addWidget(self.loose_btn)
        category_layout.addWidget(self.around_btn)
        category_layout.addWidget(self.on_btn)

        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始采集", self)
        self.start_btn.clicked.connect(self.start_capture)

        self.capture_btn = QPushButton("拍照", self)
        self.capture_btn.clicked.connect(self.capture_image)
        self.capture_btn.setEnabled(False)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.capture_btn)
        self.status_label = QLabel("就绪", self)
        self.status_label.setAlignment(Qt.AlignCenter)

        left_layout.addWidget(self.camera_label)
        left_layout.addLayout(path_layout)
        left_layout.addWidget(category_group)
        left_layout.addLayout(control_layout)
        left_layout.addWidget(self.status_label)

        right_layout = QVBoxLayout()

        info_label = QLabel("采集信息", self)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(info_label)

        # 状态信息显示
        self.info_text = QLabel("等待开始...\n\n"
                                "当前类别: loose_hands\n"
                                "已采集数量: 0", self)

        self.info_text.setAlignment(Qt.AlignLeft)
        self.info_text.setStyleSheet("padding: 10px;")
        self.info_text.setFrameShape(QFrame.Box)
        right_layout.addWidget(self.info_text)

        right_layout.addStretch(1)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

    def set_category(self, category):
        self.current_category = category
        self.loose_btn.setChecked(category == "loose_hands")
        self.around_btn.setChecked(category == "around_hands")
        self.on_btn.setChecked(category == "on_hands")
        self.update_counter_for_category(category)
        self.update_info_text()

    def update_counter_for_category(self, category):
        """更新指定类别的文件计数器"""
        if not self.save_path:
            self.category_counters[category] = 1
            return

        img_category_dir = os.path.join(self.save_path, "image", category)
        if not os.path.exists(img_category_dir):
            self.category_counters[category] = 1
            return

        img_files = [f for f in os.listdir(img_category_dir)
                     if f.lower().endswith('.jpg') and re.match(r'^\d{4}\.jpg$', f)]

        file_numbers = []
        for f in img_files:
            try:
                num = int(f.split('.')[0])
                file_numbers.append(num)
            except ValueError:
                continue

        if not file_numbers:
            self.category_counters[category] = 1
        else:
            max_num = max(file_numbers)
            self.category_counters[category] = max_num + 1


    def update_info_text(self):
        """更新信息显示区域"""
        if self.save_path:
            base_info = f"保存路径: {self.save_path}\n"
        else:
            base_info = "保存路径: 未设置\n"

        # 添加每个类别的计数信息
        base_info += f"当前类别: {self.current_category}\n"
        base_info += f"当前类别已采集数量: {self.category_counters[self.current_category] - 1}\n\n"
        base_info += "类别统计:\n"
        base_info += f"loose hands: {self.category_counters['loose_hands'] - 1}\n"
        base_info += f"around hands: {self.category_counters['around_hands'] - 1}\n"
        base_info += f"on hands: {self.category_counters['on_hands'] - 1}"
        self.info_text.setText(base_info)

    def start_capture(self):
        """启动摄像头"""
        if not self.save_path:
            self.status_label.setText("错误：请先选择保存路径")
            return

        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.status_label.setText("无法打开摄像头")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        self.timer.start(30)
        self.status_label.setText("摄像头已启动，准备采集")
        self.capture_btn.setEnabled(True)
        self.start_btn.setEnabled(False)
        self.update_info_text()

    def get_rob_pose(self):
        """获取机械臂位姿"""
        q = []
        plc = pyads.Connection('10.1.233.139.1.1', 855)
        plc.open()
        for i in range(14):
            joint = plc.read_by_name(f"HumanInterface.TestHmiDataOut.masterJoint[{i}]", pyads.PLCTYPE_REAL)
            q.append(joint)
        plc.close()
        return q

    def select_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存路径")
        if path:
            self.path_edit.setText(path)
            self.save_path = path
            self.prepare_directories()
            # 更新所有类别的计数器
            for category in self.category_counters.keys():
                self.update_counter_for_category(category)
            self.update_info_text()

    def prepare_directories(self):
        """创建保存目录结构"""
        self.image_dir = os.path.join(self.save_path, "image")
        self.state_dir = os.path.join(self.save_path, "state")

        categories = ["loose_hands", "around_hands", "on_hands"]
        for category in categories:
            img_category_dir = os.path.join(self.image_dir, category)
            os.makedirs(img_category_dir, exist_ok=True)

            state_category_dir = os.path.join(self.state_dir, category)
            os.makedirs(state_category_dir, exist_ok=True)

        self.status_label.setText(f"目录已创建在: {self.save_path}")
        self.start_btn.setEnabled(True)

    def update_frame(self):
        """更新摄像头画面"""
        if not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if ret:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w

            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.camera_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
                1080, 720, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def capture_image(self):
        """拍照并保存原始图像和状态文件"""
        if self.cap.isOpened():
            self.q2 = self.get_rob_pose()
            if self.q2 is None:
                self.status_label.setText("无法获取机械臂数据")
                return

            img_category_dir = os.path.join(self.image_dir, self.current_category)
            state_category_dir = os.path.join(self.state_dir, self.current_category)

            os.makedirs(img_category_dir, exist_ok=True)
            os.makedirs(state_category_dir, exist_ok=True)
            counter = self.category_counters[self.current_category]
            img_name = f"{counter:04d}.jpg"
            txt_name = f"{counter:04d}.txt"

            img_path = os.path.join(img_category_dir, img_name)
            flag, self.image = self.cap.read()
            width, height = self.image.shape[:2]
            image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
            self.showImage = QtGui.QImage(image.data, height, width, QImage.Format_RGB888)
            self.showImage.save(img_path, "JPG", 100)
            txt_path = os.path.join(state_category_dir, txt_name)
            self.save_state_file(txt_path, self.q2)

            self.status_label.setText(f"已保存: {self.current_category}/{img_name} 和 {txt_name}")
            self.category_counters[self.current_category] += 1
            self.update_info_text()
        else:
            self.status_label.setText("拍照失败: 无法获取图像")

    def save_state_file(self, file_path, q3):
        """保存状态文件"""
        self.q = q3
        with open(file_path, 'w') as f:
            f.write("T_array_left =\n" + str(self.q) + "\n")

    def closeEvent(self, event):
        """关闭时释放资源"""
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.timer.isActive():
            self.timer.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()
    sys.exit(app.exec_())