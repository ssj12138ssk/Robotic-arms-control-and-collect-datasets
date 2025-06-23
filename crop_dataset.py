import numpy as np
import cv2
import os
import re
from tqdm import tqdm

class ImageCropper:
    def __init__(self):
        # 相机左手外参
        self.projection_matrix_left = np.array(
            [[5.77684915e-01, -3.32057757e-01, -3.23397164e-01, 1.64017036e-01],
             [9.63920367e-03, 2.16525868e-01, -6.13768421e-01, 2.90201833e-02],
             [1.20259315e-05, -3.58454817e-04, -3.61512970e-04, 3.04328323e-05]]
        )
        # 相机内参矩阵
        self.camera_matrix = np.array([
            [1.02374302e+03, 0, 3.28987281e+02],
            [0, 1.37430887e+03, 2.12861817e+02],
            [0, 0, 1]],
            dtype=np.float32)

        # 畸变系数
        self.dist_coeffs = np.array([1.35715707e+00, -2.41678706e+01, -1.26054713e-02, -8.59585295e-04, 1.95623551e+02],
                               dtype=np.float32)

        self.alpha = [np.pi / 2, 0, -np.pi / 2, 0, np.pi / 2, -np.pi / 2, np.pi / 2, np.pi / 2]
        self.a = [0, 0, 0, 0.3, 0.35, 0, 0, 0]
        self.d = [0, -0.166, 0, 0, 0.145, 0, 0, 0]

        # 裁剪参数
        self.base_depth = 0.0002  # 基准深度（米）
        self.base_crop_size = 280  # 基准深度对应的裁剪尺寸（像素）
        self.min_crop_size = 196  # 最小裁剪尺寸（像素）
        self.max_crop_size = 450  # 最大裁剪尺寸（像素）
        self.depth_factor = 0.9  # 深度变化对裁剪尺寸的影响因子（像素/米）

    def get_angle_from_txt(self, file_path):
        '''
        这个函数用于提取txt文件下的第二行
        txt例子：
        T_array_left =
        [0.20026114583015442, 0.0014349698321893811, 0.0005746484384872019, -0.20263755321502686, -0.9197911620140076, -0.001775514567270875, 1.4169011116027832, 0.1489548683166504, 0.00044433027505874634, -0.3964218199253082, -0.10277658700942993, -0.5083941221237183, -0.0016443297499790788, -1.487537145614624]
        返回第二行，作为list
        '''
        with open(file_path, 'r') as file:
            lines = file.readlines()
            if len(lines) < 2:
                return None
            second_line = lines[1].strip()
            match = re.search(r'\[([^]]+)\]', second_line)
            if match:
                data_str = match.group(1)
                return [float(x.strip()) for x in data_str.split(',')]
        return None


    def mdh(self, alpha, a, d, theta):
        # x轴旋转变化矩阵
        rx = np.array([
            [1, 0, 0, 0],
            [0, np.cos(alpha), -np.sin(alpha), 0],
            [0, np.sin(alpha), np.cos(alpha), 0],
            [0, 0, 0, 1]
        ])
        # 沿着x轴平移
        tx = np.array([
            [1, 0, 0, a],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        # 沿着z轴旋转
        rz = np.array([
            [np.cos(theta), -np.sin(theta), 0, 0],
            [np.sin(theta), np.cos(theta), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        # 沿着z轴平移，有方向
        tz = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, d],
            [0, 0, 0, 1]
        ])
        return rx @ tx @ rz @ tz

    def calculate_robot_pose(self, q_values):
        """计算机械臂末端位姿"""
        # 使用前7个角度值，先计算左臂
        q_left = q_values[:7]

        theta_left = [
        np.pi / 2, q_left[0], np.pi / 2 + q_left[1],
        -np.pi / 2 + q_left[2] - q_left[1], q_left[3], q_left[4],
        np.pi / 2 + q_left[5], np.pi + q_left[6]
        ]
        # 计算末端位姿矩阵
        pose = np.eye(4)
        for i in range(8):
            trans = self.mdh(self.alpha[i], self.a[i], self.d[i], theta_left[i])
            pose = pose @ trans

        return pose

    def transform_to_pixel(self, robot_pose):
        """
        将机械臂末端坐标转换为像素坐标（考虑畸变）

        参数:
        projection_matrix: 3x4标定矩阵
        camera_matrix: 3x3相机内参矩阵
        dist_coeffs: 1x5畸变系数矩阵
        robot_pose: 4x4机械臂末端位姿矩阵

        返回:
        (u, v): 畸变校正后的像素坐标
        """
        position = robot_pose[:3, 3]

        # 齐次坐标向量 [x, y, z, 1]
        world_point = np.append(position, 1)

        projected = self.projection_matrix_left @ world_point
        # 获取深度值（相机坐标系下的Z值）
        depth = projected[2]
        u_norm = projected[0] / projected[2]
        v_norm = projected[1] / projected[2]

        norm_point = np.array([[[u_norm, v_norm]]], dtype=np.float32)

        dist_point = cv2.undistortPoints(norm_point, self.camera_matrix, self.dist_coeffs, P=self.camera_matrix)

        u, v = dist_point[0, 0]

        return int(round(u)), int(round(v)), depth

    def calculate_crop_size(self, depth):
        """
        根据深度计算裁剪尺寸（线性关系）
        深度越大（物体越远），裁剪尺寸越小
        深度越小（物体越近），裁剪尺寸越大

        使用公式：
        crop_size = base_crop_size * scale_factor * depth_factor

        其中：
        base_crop_size: 基准深度下的裁剪尺寸
        depth_factor: 深度变化对裁剪尺寸的影响因子
        base_depth: 基准深度
        depth: 当前深度
        """
        scale_factor = abs(self.base_depth / depth)
        crop_size = self.base_crop_size * scale_factor * self.depth_factor

        # 裁剪尺寸在最小值和最大值之间
        crop_size = max(self.min_crop_size, min(crop_size, self.max_crop_size))

        # 确保裁剪尺寸是偶数（方便中心裁剪）
        return int(round(crop_size))


    def crop_image(self, image, center_x, center_y, depth):
        """以指定点为中心裁剪图像"""
        height, width = image.shape[:2]
        crop_size = self.calculate_crop_size(depth)
        half_size = crop_size // 2
        # 计算裁剪区域边界
        top = max(0, center_y - half_size)
        bottom = min(height, center_y + half_size)
        left = max(0, center_x - half_size)
        right = min(width, center_x + half_size)
        # 实际裁剪
        cropped_img = image[top:bottom, left:right]

        # 计算需要填充的边界
        pad_top = max(0, half_size - center_y)
        pad_bottom = max(0, (center_y + half_size) - height)
        pad_left = max(0, half_size - center_x)
        pad_right = max(0, (center_x + half_size) - width)
        # 如果有边界需要填充
        if pad_top > 0 or pad_bottom > 0 or pad_left > 0 or pad_right > 0:
            cropped_img = cv2.copyMakeBorder(
                cropped_img,
                pad_top, pad_bottom,
                pad_left, pad_right,
                cv2.BORDER_CONSTANT,
                value=[0, 0, 0]
            )

        return cropped_img



    def process_folder(self, img_folder, txt_folder, output_folder):
        """处理整个文件夹"""
        os.makedirs(output_folder, exist_ok=True)
        txt_files = [f for f in os.listdir(txt_folder) if f.endswith('.txt')]
        for txt_file in tqdm(txt_files, desc="Processing images"):
            base_name = os.path.splitext(txt_file)[0]
            img_path = os.path.join(img_folder, base_name + ".jpg")
            txt_path = os.path.join(txt_folder, txt_file)
            if not os.path.exists(img_path):
                continue
            q_values = self.get_angle_from_txt(txt_path)
            if q_values is None or len(q_values) < 7:
                continue
            robot_pose = self.calculate_robot_pose(q_values)
            u, v, depth = self.transform_to_pixel(robot_pose)

            image = cv2.imread(img_path)
            if image is None:
                continue

            cropped_img = self.crop_image(image, u, v, depth)
            if cropped_img is None:
                continue
            output_path = os.path.join(output_folder, base_name + "_cropped.jpg")
            cv2.imwrite(output_path, cropped_img)


if __name__ == "__main__":
    cropper = ImageCropper()

    # 设置路径,分别为图片路径，对应txt路径啊输出路径
    IMAGE_FOLDER = r"D:\python\loose_hands_detection\250618\left-hand\image\around_hands"
    TXT_FOLDER = r"D:\python\loose_hands_detection\250618\left-hand\state\around_hands"
    OUTPUT_FOLDER = r"D:\python\loose_hands_detection\temp\cropped"

    cropper.process_folder(IMAGE_FOLDER, TXT_FOLDER, OUTPUT_FOLDER)
    print("completed")