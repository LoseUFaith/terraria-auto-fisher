from PyQt5.QtGui import QPixmap, QCursor
from PyQt5.QtGui import QImage
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QLayout
from PyQt5.QtWidgets import QFrame
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QSpinBox
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QStatusBar
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QDialog

from pynput.keyboard import Listener

import sys
import cv2
import numpy
import pyautogui
import configparser

from PlotDrawer import PlotDrawer, QtPlotDrawer
from Monitor import FisherMonitoring

__version__ = '0.4'
__author__ = 'Alexei Metlitski'

SHIFT_FRAME = 100
DEFAULT_POTION_KEY = 't'

ignoreCount = 0


class AppUi(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.setWindowTitle('AutoFisher')
        self.setMouseTracking(True)
        self.updatesRate = 60
        self.onDisplay = False

        if sys.platform == "darwin":
            self.shift = SHIFT_FRAME * 2
        else:
            self.shift = SHIFT_FRAME

        self._init_layout()
        self.fisher = FisherMonitoring(inputX=self.input_screen_x,
                                       inputY=self.input_screen_y,
                                       shift=SHIFT_FRAME,
                                       threshold=self.input_treshold,
                                       sensitivity=self.input_sensivity,
                                       potionKey=self.config[self._get_current_preset()].get('button_to_drink',
                                                                                             DEFAULT_POTION_KEY),
                                       potionChecked=self.input_drink_potions,
                                       potionDelay=self.input_drink_delay,
                                       # infoUploader=self.plotDrawer.add_data)
                                       infoUploader=None)

    def _init_layout(self):
        self.mainLayout = QHBoxLayout()
        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)
        self._centralWidget.setLayout(self.mainLayout)

        self.generalLayout = QVBoxLayout()
        self.mainLayout.addLayout(self.generalLayout)
        self.rightLayout = QVBoxLayout()
        self.mainLayout.addLayout(self.rightLayout)

        # Init main layout
        self.init_preview_layout()
        self.init_status_layout()
        self.init_control_layout()

        # Init right layout
        self.init_list_layout()

        # Init bottom layout
        # self.plotDrawer = PlotDrawer(20, "b-", [4, 2], yRange=[-0.1, 1.1])
        # self.plotDrawer = PlotDrawer(200, "b-", [4, 2])

        self.plotDrawer = QtPlotDrawer(200, "b-", [4, 2], yRange=[-0.1, 1.1])

        self.plotDrawer.setFixedSize(400, 200)
        self.generalLayout.addWidget(self.plotDrawer)

        self._load_config()
        self.list.itemSelectionChanged.connect(self._load_config)

        self.displayTimer = QTimer()
        self.displayTimer.timeout.connect(self._update_display)
        self.displayTimer.setInterval(int(1000 / self.updatesRate))
        self.displayTimer.start()

    def init_preview_layout(self):
        previews = QHBoxLayout()
        self.imageLabel = QLabel(self)
        self.imageLabel.setFrameShape(QFrame.Panel)
        self.imageLabel.setFrameShadow(QFrame.Sunken)
        self.imageLabel.setLineWidth(2)
        self.imageLabel.resize(self.shift, self.shift)
        self.imageLabel.setFixedSize(self.shift, self.shift)
        previews.addWidget(self.imageLabel)
        self.previewLabel = QLabel(self)
        self.previewLabel.setFrameShape(QFrame.Panel)
        self.previewLabel.setFrameShadow(QFrame.Sunken)
        self.previewLabel.setLineWidth(2)
        self.previewLabel.setFixedSize(self.shift, self.shift)
        previews.addWidget(self.previewLabel)
        self.generalLayout.addLayout(previews)

    def init_status_layout(self):
        self.progress = QProgressBar(self)
        self.display = QPushButton(self)
        self.display.setText("Turn on preview")
        self.display.clicked.connect(self.display_button_clicked)
        self.mouse_status = QLabel(self)
        self.state_status = QLabel(self)
        self.potion_status = QLabel(self)

        self.generalLayout.addWidget(self.progress)
        self.generalLayout.addWidget(self.display)
        self.generalLayout.addWidget(self.mouse_status)
        self.generalLayout.addWidget(self.state_status)
        self.generalLayout.addWidget(self.potion_status)

    def init_control_layout(self):
        infoLayout = QFormLayout()
        self.input_screen_x = QSpinBox()
        self.input_screen_x.setMaximum(QApplication.primaryScreen().size().width())
        self.input_screen_y = QSpinBox()
        self.input_screen_y.setMaximum(QApplication.primaryScreen().size().height())

        self._update_pos_hotkey = 'v'
        self.input_screen_xy_key = QPushButton()
        self.input_screen_xy_key.clicked.connect(self._change_pos_hotkey)
        self.input_screen_xy_key.setText('Change hotkey ({})'.format(self._update_pos_hotkey))

        self.input_treshold = QSpinBox()
        self.input_treshold.setMaximum(255)

        self.input_sensivity = QSpinBox()
        self.input_sensivity.setMaximum(999)

        self.input_drink_potions = QCheckBox()
        self.input_drink_delay = QSpinBox()
        self.input_drink_delay.setMaximum(3600)

        infoLayout.addRow("Coordinate X", self.input_screen_x)
        infoLayout.addRow("Coordinate Y", self.input_screen_y)
        infoLayout.addRow("Coordinates to MousePos", self.input_screen_xy_key)
        infoLayout.addRow("Mov. Treshold", self.input_treshold)
        infoLayout.addRow("Sensivity", self.input_sensivity)
        infoLayout.addRow("Drink potions", self.input_drink_potions)
        infoLayout.addRow("Drink delay", self.input_drink_delay)
        self.rightLayout.addLayout(infoLayout)

        self.start = QPushButton(self)
        self.start.setText("Start fishing")
        self.start.clicked.connect(self._on_push_button)
        self.rightLayout.addWidget(self.start)

        self._hotkey = 'z'
        self._hotkey_listener = Listener(on_press=self._keypress_event)
        self._hotkey_listener.start()

        self.select_hotkey = QPushButton(self)
        self.select_hotkey.setText('Change fishing hotkey ({})'.format(self._hotkey))
        self.select_hotkey.clicked.connect(self._change_hotkey)
        self.rightLayout.addWidget(self.select_hotkey)

        self.save = QPushButton(self)
        self.save.setText("Save this preset")
        self.save.clicked.connect(self._save_config)
        self.rightLayout.addWidget(self.save)

    def init_list_layout(self):
        list_controls = QHBoxLayout()
        self.b_create_preset = QPushButton(self)
        self.b_create_preset.setText("Add preset")
        self.b_create_preset.clicked.connect(self._add_preset)
        list_controls.addWidget(self.b_create_preset)

        self.b_delete_preset = QPushButton(self)
        self.b_delete_preset.setText("Delete preset")
        self.b_delete_preset.clicked.connect(self._del_preset)
        list_controls.addWidget(self.b_delete_preset)
        self.rightLayout.addLayout(list_controls)

        self.list = QListWidget()
        self.rightLayout.addWidget(self.list)
        self._update_list_from_config()

    def closeEvent(self, event):
        self.fisher.stop_running()
        self._hotkey_listener.stop()
        self._set_enabled(True)
        self.close()

    def display_button_clicked(self):
        if self.onDisplay:
            self.display.setText("Turn on preview")
            self.onDisplay = False
            self.imageLabel.clear()
            self.previewLabel.clear()
        else:
            self.display.setText("Turn off preview")
            self.onDisplay = True

    def _keypress_event(self, key):
        try:
            if self._hotkey == key.char:
                self._on_push_button()
            elif self._update_pos_hotkey == key.char:
                self._xy_pos_update()
        except AttributeError:
            return

    def _change_hotkey(self):
        if self._hotkey_listener.running:
            self._hotkey_listener.stop()

        self.hotkey_dialog = QDialog(self)
        self.hotkey_dialog.keyPressEvent = lambda key: self.assign_hotkey(key)
        self.hotkey_dialog.setWindowTitle('Press your desired hotkey.')
        self.hotkey_dialog.exec()

        self._hotkey_listener = Listener(on_press=self._keypress_event)
        self._hotkey_listener.start()

    def assign_hotkey(self, key):
        if key.text() != '' and key.text() != self._update_pos_hotkey:
            self._hotkey = key.text()
        self.hotkey_dialog.close()
        self.select_hotkey.setText('Change fishing hotkey ({})'.format(self._hotkey))

    def assign_pos_hotkey(self, key):
        if key.text() != '' and key.text() != self._hotkey:
            self._update_pos_hotkey = key.text()
        self.pos_hotkey_dialog.close()
        self.input_screen_xy_key.setText('Change hotkey ({})'.format(self._update_pos_hotkey))

    def _change_pos_hotkey(self):
        if self._hotkey_listener.running:
            self._hotkey_listener.stop()

        self.pos_hotkey_dialog = QDialog(self)
        self.pos_hotkey_dialog.keyPressEvent = lambda key: self.assign_pos_hotkey(key)
        self.pos_hotkey_dialog.setWindowTitle('Press your desired hotkey.')
        self.pos_hotkey_dialog.exec()

        self._hotkey_listener = Listener(on_press=self._keypress_event)
        self._hotkey_listener.start()

    def _xy_pos_update(self):
        pos = pyautogui.position()
        self.input_screen_x.setValue(pos.x)
        self.input_screen_y.setValue(pos.y)

    def _update_list_from_config(self):
        self.list.clear()  # HAS SIDE EFFECTS ON CONFIG ??
        for each in self.config.keys():
            self.list.addItem((each + '.')[:-1])
        self.list.setCurrentRow(0)

    def _add_preset(self):
        text, ok = QInputDialog.getText(self, 'Create preset', 'Choose preset name:')
        if ok:
            self.list.addItem(text)
            self.list.setCurrentRow(self.list.count() - 1)
            self._save_config()

    def _del_preset(self):
        if self.list.count() <= 1:
            QMessageBox.warning(self, "Warning", "Can't delete last item")
            return
        preset = self._get_current_preset()
        if preset == 'DEFAULT':
            QMessageBox.critical(self, "Heat death of the universe",
                                 "DEFAULT is superior, it can't be deteled")
            return
        reply = QMessageBox.question(self, 'Delete preset', 'Delete {}?'.format(preset),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.list.takeItem(self.list.currentRow())
            self.config.remove_section(preset)
            self._update_list_from_config()
            self._save_config()

    def _load_config(self):
        name = self._get_current_preset()
        if name not in self.config:
            self.config[name] = {}
        self.input_screen_x.setValue(int(self.config[name].get('screen_x', 850)))
        self.input_screen_y.setValue(int(self.config[name].get('screen_y', 850)))
        self.input_treshold.setValue(int(self.config[name].get('treshold', 6)))
        self.input_sensivity.setValue(int(self.config[name].get('sensivity', 55)))
        self.input_drink_potions.setChecked(self.config[name].get('drink_potions', 'False') == 'True')
        self.input_drink_delay.setValue(int(self.config[name].get('drink_delay', 185)))

    def _save_config(self):
        name = self._get_current_preset()
        if name not in self.config:
            self.config[name] = {}
        self.config[name]['screen_x'] = str(self.input_screen_x.value())
        self.config[name]['screen_y'] = str(self.input_screen_y.value())
        self.config[name]['treshold'] = str(self.input_treshold.value())
        self.config[name]['sensivity'] = str(self.input_sensivity.value())
        self.config[name]['drink_potions'] = str(self.input_drink_potions.isChecked())
        self.config[name]['drink_delay'] = str(self.input_drink_delay.value())
        self.config[name]['button_to_drink'] = DEFAULT_POTION_KEY

        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)

    def _on_push_button(self):
        if self.fisher.in_fishing():
            self.fisher.stop_fishing()
            self.start.setText("Start fishing again")
            self._set_enabled(True)
        else:
            self.fisher.start_fishing()
            self.start.setText("Stop fishing")
            self.mouse_status.setText("Mouse position is not tracked")
            self._set_enabled(False)

    def _set_enabled(self, state):
        """Changes enableness of all UI controls"""
        self.mouse_status.setEnabled(state)
        self.save.setEnabled(state)
        self.input_screen_x.setEnabled(state)
        self.input_screen_y.setEnabled(state)
        self.input_screen_xy_key.setEnabled(state)
        self.input_treshold.setEnabled(state)
        self.input_sensivity.setEnabled(state)
        self.input_drink_potions.setEnabled(state)
        self.input_drink_delay.setEnabled(state)
        self.select_hotkey.setEnabled(state)
        self.b_create_preset.setEnabled(state)
        self.b_delete_preset.setEnabled(state)
        self.list.setEnabled(state)

    def _get_current_preset(self):
        item = self.list.currentItem()
        return item.text() if item else None

    def _update_display(self):
        # Get graphical info
        try:
            image, preview, sense, processedTime = self.fisher.get_graphical_info()
        except TypeError:
            return

        if self.onDisplay:
            # Update first preview
            cv_img = numpy.array(image)
            frame = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            h, w = cv_img.shape[:2]
            bytesPerLine = 3 * w
            qimage = QImage(frame.data, w, h, bytesPerLine, QImage.Format.Format_RGB888)
            pixmap1 = QPixmap.fromImage(qimage)
            self.imageLabel.setPixmap(pixmap1)

            # Update second preview
            height, width = preview.shape
            cv2qimg = QImage(preview.data, width, height, width * 1, QImage.Format_Grayscale8)
            pixmap2 = QPixmap.fromImage(cv2qimg)
            self.previewLabel.setPixmap(pixmap2)

        self.progress.setValue(min(100, int(sense * 100)))

        self.plotDrawer.add_data(processedTime, sense)

        # Update status
        if self.fisher.in_fishing():
            self.state_status.setText(self.fisher.get_state_description())
        else:
            # Mouse cursor only update when machine is inactive
            coords = QCursor.pos()
            self.mouse_status.setText("Mouse at ({0}, {1});".format(coords.x(), coords.y()))
            self.state_status.setText("Preset: " + str(self._get_current_preset()))

        if self.input_drink_potions.isChecked():
            drinkIn = self.fisher.get_potion_drinking_in()
            if drinkIn:
                self.potion_status.setText("Drink all in {} seconds".format(drinkIn))
            else:
                self.potion_status.setText("Drink potions every {} seconds".format(self.input_drink_delay.value()))
        else:
            self.potion_status.setText("No potion drinking")


# Client code
def main():
    """Main function."""
    app = QApplication(sys.argv)
    app.setStyle('Windows')
    view = AppUi()
    view.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
