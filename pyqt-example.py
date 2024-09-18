from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

class MyMainWindow(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)

        # Create the tabbed widget
        self.central = QTabWidget(self)
        self.setCentralWidget(self.central)

        # Create a new tab
        self.tab1 = QWidget()
        # Tab has a vertical layout
        self.vbox = QVBoxLayout(self.tab1)
        # Tab children: two groups containing a grid of labels and textboxes
        self.group1 = QGroupBox("Group 1")
        self.textBox1 = QLineEdit(self.group1)
        self.textBox2 = QLineEdit(self.group1)
        self.fillGroup(self.group1, self.textBox1, self.textBox2)
        self.group2 = QGroupBox("Group 2")
        self.textBox3 = QLineEdit(self.group2)
        self.textBox4 = QLineEdit(self.group2)
        self.fillGroup(self.group2, self.textBox3, self.textBox4)
        # Add tab children to the tab layout
        self.vbox.addWidget(self.group1)
        self.vbox.addWidget(self.group2)
        # Append tab to the tabbed widget
        self.central.addTab(self.tab1, "Tab 1")

        # Create a new tab and append it to the tabbed widget
        self.tab2 = QWidget()
        self.central.addTab(self.tab2, "Tab 2")

    def fillGroup(self, group, box1, box2) :
        """Arrange the groupbox content in a grid layout"""

        grid = QGridLayout(group)
        label1 = QLabel("Input 1:", group)
        grid.addWidget(label1, 0, 0)
        grid.addWidget(box1, 0, 1)
        label2 = QLabel("Input 2:", self.group1)
        grid.addWidget(label2, 1, 0)
        grid.addWidget(box2, 1, 1)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = MyMainWindow()
    ui.show()
    sys.exit(app.exec_())