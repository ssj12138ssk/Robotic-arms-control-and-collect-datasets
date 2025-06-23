# get-dataset
A software to collect specific dataset by PYQT5
run get_handspic.py or use pyinstaller to package to start. You may choose place to save dataset after click "browse", the folder will create automatically. Then click "start collection", if the ads is not connected correctly, the application may break.
The categories of dataset are on hand, around hand and loose hand. After choose the category which will collect, and click capture, the image will be saved in folder images and the angle of each mechanical arm will be saved in txt in folder state.
run ./form/form1.py to start control mechanical arm. JNT_NUM is the number of mechanical arms, MES_NUM is the paras needs to write, txtpath saves the points. Remember to modify the ip address and port of BeckHoff ads device.
After the dataset collection, run cropdataset.py will help crop the original images.According to angles， hand-eye calibration and camera calibration, it will crop the region end of the arm.
And the size of the region depends on the depth of the end of the arm. For example, if the hand is close to camera, the size of region may be 450*450(max). And it will linear decrease with increasing distance. The base distance or factor can be modified according to the actual situation.
