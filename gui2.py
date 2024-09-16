import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPalette, QColor, QFont
from PyQt5.QtWidgets import * 
import yaml

from main_pipeline.bus import Bus
from main_pipeline.sensor import Sensor
from main_pipeline.interpreter import Interpretor
from main_pipeline.display import Display

class TestGUI(QWidget):

    def __init__(self):
        super(TestGUI, self).__init__()
        
        with open("config/sensor_data.yaml", 'r') as stream:
            self.big_data_dict = yaml.safe_load(stream)

        # Comb through the keys, set the timestamp to the current time and the data to zero
        self.sensor_names = list(self.big_data_dict.keys())

        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        center_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
       
        self.bold16 = QFont("Helvetica", 16, 5)

        ### Center layout
        label = QLabel(self)
        label.setText("Live Sensor Data")
        label.setFont(self.bold16)
        label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        center_layout.addWidget(label)

        # Make the list
        self.leftlist = QListWidget()
        self.leftlist.insertItem(0, 'Contact')
        self.leftlist.insertItem(1, 'Personal')
        self.leftlist.insertItem(2, 'Educational')

        # Make the dropdown
        self.combobox = QComboBox()
        self.combobox.addItems(self.sensor_names)
        
        # Make the stack
        self.stack1UI()
        self.stack2UI()
        self.stack3UI()
        self.Stack = QStackedWidget(self)
        self.Stack.addWidget(self.stack1)
        self.Stack.addWidget(self.stack2)
        self.Stack.addWidget(self.stack3)

        # Stick it all in the center
        # center_vbox = QVBoxLayout(self)
        center_layout.addWidget(self.combobox)
        center_layout.addWidget(self.leftlist)
        center_layout.addWidget(self.Stack)

        ## Left layout
        label = QLabel(self)
        label.setText("Sensor Status & Control")
        label.setFont(self.bold16)
        label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        left_layout.addWidget(label)

        ## Right layout
        label = QLabel(self)
        label.setText("Notes & Logs")
        label.setFont(self.bold16)
        label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        right_layout.addWidget(label)


        main_layout.addLayout(left_layout)
        main_layout.addLayout(center_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

        self.leftlist.currentRowChanged.connect(self.display)
        self.combobox.currentIndexChanged.connect(self.display)
        self.setGeometry(300, 50, 10,10)
        self.setWindowTitle('StackedWidget demo')
        self.show()
	
    def stack1UI(self):
        self.stack1 = QWidget()
        layout = QFormLayout()
        layout.addRow("Name",QLineEdit())
        layout.addRow("Address",QLineEdit())
        #self.setTabText(0,"Contact Details")
        self.stack1.setLayout(layout)
		
    def stack2UI(self):
        self.stack2 = QWidget()
        layout = QFormLayout()
        sex = QHBoxLayout()
        sex.addWidget(QRadioButton("Friend"))
        sex.addWidget(QRadioButton("Foe"))
        layout.addRow(QLabel("Status"),sex)
        layout.addRow("Date of Birth",QLineEdit())

        self.stack2.setLayout(layout)
		
    def stack3UI(self):
        self.stack3 = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(QLabel("subjects"))
        layout.addWidget(QCheckBox("Physics"))
        layout.addWidget(QCheckBox("Maths"))
        self.stack3.setLayout(layout)
		
    def display(self,i):
        self.Stack.setCurrentIndex(i)
		
def main():
   app = QApplication(sys.argv)
   ex = TestGUI()
   sys.exit(app.exec_())
	
if __name__ == '__main__':
   main()