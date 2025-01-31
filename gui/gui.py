import time
import cv2
import numpy as np
from PyQt5.QtCore import (Qt, QSize, pyqtSlot)
from PyQt5.QtGui import (QIcon, QPixmap, QImage)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QStackedWidget, QSizePolicy,
                             QGridLayout, QSplashScreen, QHBoxLayout, QMessageBox, QLabel, QProgressDialog, QDialog, QFileDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, QPushButton, QProgressBar
                             )
from dehazing.dehazing import *
from dehazing.utils import *
from dehazing.utils import VideoProcessor
from PyQt5.QtCore import Qt, QTimer, QThread
import sys
import configparser
import os
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = r'path/to/qt/plugins/platforms'


class GUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.background_pixmap = QPixmap('gui/assets/splash.jpg')
        self.background_pixmap = self.background_pixmap.scaled(
            800, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.splash = QSplashScreen(self.background_pixmap)

        # Get the current screen desktop geometry
        screen_geometry = QApplication.desktop().screenGeometry()
        splash_width = 800
        splash_height = 400
        x = (screen_geometry.width() - splash_width) // 2
        y = (screen_geometry.height() - splash_height) // 2
        self.splash.setGeometry(x, y, splash_width, splash_height)
        self.splash.show()

        QTimer.singleShot(2000, self.show_main_window)
        self.setWindowTitle("SeeThrough")
        self.setGeometry(100, 100, 1440, 900)
        self.setMinimumSize(1280, 720)  # Minimum width and height
        self.setWindowIcon(QIcon('gui/assets/icons/logo.svg'))
        self.setStyleSheet("QMainWindow {background-color: #fff;}")

        # Create a stacked widget to manage frames
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Create and add frames to the stacked widget
        self.stacked_widget.addWidget(self.realtime_frames())
        self.stacked_widget.addWidget(self.static_dehazing_frames())

        # Create navbar and connect buttons to frame switching
        navbar = self.navbar()
        navbar_buttons = navbar.findChildren(QPushButton)
        for button in navbar_buttons:
            button.clicked.connect(self.switch_frame)

        # Create switch_framea layout for the central widget and add the stacked widget and navbar
        central_layout = QVBoxLayout()
        central_layout.addWidget(self.stacked_widget)
        central_layout.addWidget(navbar)
        # 0 is the index of Realtime Dehazing

        central_widget = QWidget()
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)
        self.active_button = None  # Track the active button
        self.active_frame = 0
        self.processed_image = None
        self.image_path = None
        self.camera_stream = None

    def show_main_window(self):
        # Close splash screen and show main GUI
        self.splash.finish(self)
        self.show()

    def load_image(self):
        # Define the action when the "Input Image" button is clicked
        # For example, open a file dialog to select an input image
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        self.image_path, _ = QFileDialog.getOpenFileName(
            self, "Select Input Image", "", "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)", options=options)
        pixmap = QPixmap(self.image_path)
        pixmap = pixmap.scaled(
            self.InputFile.width(), self.InputFile.height(), Qt.KeepAspectRatio)
        self.InputFile.setPixmap(pixmap)
        self.InputFile.setAlignment(Qt.AlignCenter)

    def save_image(self):
        """Save the image to the specified path."""
        if self.processed_image is None:
            QMessageBox.information(self, "Error", "No image to save.")
            return

        output_image_path, _ = QFileDialog.getSaveFileName(
            self, "Save Processed Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")

        if output_image_path:
            cv2.imwrite(output_image_path, (self.processed_image * 255))
            QMessageBox.information(
                self, "Success", "Image saved successfully.")
            return

    def start_processing(self):
        if self.image_path is None:
            QMessageBox.information(
                self, "Error", "Please, Load an Image First!")
            return
        image = cv2.imread(self.image_path)
        dehazing_instance = DehazingCPU()
        self.processed_image = dehazing_instance.image_processing(
            image)
        pixmap = QPixmap(self.image_path)
        pixmap = pixmap.scaled(
            self.InputFile.width(), self.InputFile.height(), Qt.KeepAspectRatio)
        self.InputFile.setPixmap(pixmap)
        self.InputFile.setAlignment(Qt.AlignCenter)

        # Scale the processed image values to the range [0, 255] without data loss
        scaled_image = (self.processed_image *
                        255.0).clip(0, 255).astype(np.uint8)

        # Convert the NumPy array (BGR format) to an RGB image
        rgb_image = cv2.cvtColor(
            scaled_image, cv2.COLOR_BGR2RGB)

        # Create a QImage from the RGB image
        qimage = QImage(rgb_image.data, rgb_image.shape[1],
                        rgb_image.shape[0], rgb_image.shape[1] * 3, QImage.Format_BGR888).rgbSwapped()
        qimage = qimage.scaled(
            self.OutputFile.width(), self.OutputFile.height(), Qt.KeepAspectRatio)
        # Convert the QImage to a QPixmap
        pixmap = QPixmap(qimage)
        self.OutputFile.setPixmap(pixmap)
        self.OutputFile.setAlignment(Qt.AlignCenter)

    def navbar(self):
        # Create a widget for the navigation bar
        navbar = QWidget()
        navbar.setFixedHeight(64)

        # Label for the logo
        logo = QLabel('seeThrough')
        logo.setStyleSheet('''
            QLabel {
                font-family: "Montserrat";
                font-size: 20px;
                font-weight: bold;
                color: #191919;
            }
        ''')

        # Create buttons for frame switching
        btn_realtime_dehazing = QPushButton('Realtime Dehazing')
        btn_realtime_dehazing.setObjectName(
            "realtime_button")  # Add an object name
        btn_realtime_dehazing.setStyleSheet('''
            QPushButton {
                background-color: #fff;
                border: 1px solid gray; /* Add a border */
                border-radius: 10px;
                padding: 10px 60px; /* Adjust padding */
                font-size: 13px; /* Increase font size */
            }

            QPushButton:hover {
                background-color: #373030; /* Change background color on hover */
                color: #fff; /* Change text color on hover */
            }
        ''')
        btn_realtime_dehazing.clicked.connect(
            lambda: self.stacked_widget.setCurrentIndex(0)
        )

        btn_static_dehazing = QPushButton('Image Dehazing')
        btn_static_dehazing.setObjectName("static_button")
        btn_static_dehazing.setStyleSheet('''
            QPushButton {
                background-color: #fff;
                border: 1px solid gray; /* Add a border */
                border-radius: 10px;
                padding: 10px 60px; /* Adjust padding */
                font-size: 13px; /* Increase font size */
            }

            QPushButton:hover {
                background-color: #373030; /* Change background color on hover */
                color: #fff; /* Change text color on hover */
            }
        ''')

        btn_static_dehazing.clicked.connect(
            lambda: self.stacked_widget.setCurrentIndex(1))
        btn_video_dehazing = QPushButton('Video Dehazing')
        btn_video_dehazing.setStyleSheet('''
            QPushButton {
                background-color: #fff;
                border: 1px solid gray; /* Add a border */
                border-radius: 10px;
                padding: 10px 60px; /* Adjust padding */
                font-size: 13px; /* Increase font size */
            }

            QPushButton:hover {
                background-color: #373030; /* Change background color on hover */
                color: #fff; /* Change text color on hover */
            }
        ''')
        btn_video_dehazing.clicked.connect(self.video_dehazing)
        btn_exit = QPushButton()
        # btn_exit icon
        btn_exit.setIcon(QIcon('gui/assets/icons/exit.svg'))
        btn_exit.setIconSize(QSize(32, 32))
        btn_exit.setStyleSheet('''
            QPushButton {
                background-color: #fff;
                border: 1px solid gray;
                border-radius: 10px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
        ''')
        btn_exit.clicked.connect(self.confirm_exit)

        # Add buttons to the navbar
        layout = QHBoxLayout(navbar)
        layout.addWidget(logo, alignment=Qt.AlignLeft)
        layout.addWidget(btn_realtime_dehazing, )
        layout.addWidget(btn_static_dehazing, )
        layout.addWidget(btn_video_dehazing, )
        layout.addWidget(btn_exit, alignment=Qt.AlignRight)

        return navbar

    def video_dehazing(self):
        # Ask the user to select a video file
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        input_video_path, _ = QFileDialog.getOpenFileName(
            self, "Select Input Video", "", "Videos (*.mp4 *.avi *.mov);;All Files (*)", options=options)

        if not input_video_path:
            print("No input video selected.")
            return

        # Ask the user to select a save location
        output_video_path, _ = QFileDialog.getSaveFileName(
            self, "Save Processed Video", "", "Videos (*.mp4 *.avi *.mov)")

        if not output_video_path:
            print("No save location selected.")
            return

        # Create a VideoProcessor object
        video_processor = VideoProcessor(input_video_path, output_video_path)
        video_processor.update_progress_signal.connect(
            self.update_progress_dialog)
        # Create and show a progress dialog
        self.progress_dialog = QProgressDialog(
            "Processing Video...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Video Processing")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.show()

        # Start the video processing thread
        video_processor.start_processing()

    def update_progress_dialog(self, progress_percentage):
        self.progress_dialog.setValue(progress_percentage)

        if progress_percentage == 100:
            # Close the progress dialog when processing is complete
            self.progress_dialog.close()
            # Show a success message
            QMessageBox.information(
                self, "Success", "Video saved successfully.")

    def switch_frame(self):
        frame_text = self.sender().text()

        if frame_text == 'Realtime Dehazing':
            self.stacked_widget.setCurrentIndex(0)
        elif frame_text == 'Static Dehazing':
            self.stacked_widget.setCurrentIndex(1)

    def show_options_popup(self):
        options_popup = QDialog()
        options_popup.setWindowTitle("Camera Options")
        options_popup.setWindowFlags(
            options_popup.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        options_popup.setFixedWidth(320)
        options_popup.setFixedHeight(240)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)  # Add padding to the dialog

        # Add a title label
        title_label = QLabel("<h2>Camera Options</h2>")
        layout.addWidget(title_label)

        input_label = QLabel("IP Address:")
        layout.addWidget(input_label)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter IP address")
        layout.addWidget(self.input_field)

        # Add a button box with custom styling
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
            options_popup)
        buttons.accepted.connect(options_popup.accept)
        buttons.rejected.connect(options_popup.reject)
        layout.addWidget(buttons)

        # Apply custom styling using CSS
        options_popup.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QLabel {
                font-size: 18px;
            }
            QLineEdit {
                padding: 8px;
                font-size: 16px;
                border: 2px solid #000;
                border-radius: 4px;
            }
            QPushButton {
                padding: 8px 16px;
                font-size: 16px;
                background-color: #007ACC;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005FAA;
            }
        """)

        options_popup.setLayout(layout)

        # Load settings with error handling
        try:
            config = configparser.ConfigParser()
            config.read('settings.cfg')
            if 'DEFAULT' in config and 'input' in config['DEFAULT']:
                self.input_field.setText(config['DEFAULT']['input'])
        except (FileNotFoundError, configparser.Error) as e:
            print(f"Error loading settings: {e}")

        result = options_popup.exec_()

        if result == QDialog.Accepted:
            # Save settings with error handling
            try:
                config = configparser.ConfigParser()
                config.read('settings.cfg')
                if 'DEFAULT' not in config:
                    config['DEFAULT'] = {}
                config['DEFAULT']['input'] = self.input_field.text().replace(
                    '%', '%%')
                with open('settings.cfg', 'w') as configfile:
                    config.write(configfile)

                # Show a success message
                QMessageBox.information(
                    options_popup, "Success", "Settings saved successfully.")
            except (FileNotFoundError, configparser.Error) as e:
                print(f"Error saving settings: {e}")

    def static_dehazing_frames(self):
        # Create the widget
        widget_static = QWidget()
        widget_static.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create layout
        layout = QGridLayout(widget_static)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove any margin

        # Input File (Only Images and Videos)
        self.InputFile = QLabel()  # Use QLabel to display an image
        self.InputFile.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.InputFile.setContentsMargins(0, 0, 0, 0)  # Remove any margin
        self.InputFile.setStyleSheet(
            "border: 1px solid gray; border-radius: 10px; background-color: black;")

        # Add the "Select Image" button
        btn_load_image = QPushButton("Load Image")
        btn_load_image.setIcon(QIcon('gui/assets/icons/settings.svg'))
        btn_load_image.setToolTip('Load Image')
        btn_load_image.clicked.connect(self.load_image)

        # Apply button styling
        btn_load_image.setStyleSheet('''
            QPushButton {
                background-color: #fff;
                border: 1px solid gray;
                border-radius: 10px;
                padding: 15px; /* Adjust the padding as needed */
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
        ''')

        # Add the "Load Image" button
        layout.addWidget(btn_load_image, 1, 0)
        # Add widgets to the layout
        layout.addWidget(self.InputFile, 0, 0)

        # Input File (Only Images and Videos)
        self.OutputFile = QLabel()
        self.OutputFile.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.OutputFile.setContentsMargins(0, 0, 0, 0)  # Remove any margin
        self.OutputFile.setStyleSheet(
            "border: 1px solid gray; border-radius: 10px; background-color: black;")

        # Add widgets to the layout
        layout.addWidget(self.OutputFile, 0, 1)

        # Add the "Save Image" button
        btn_save_image = QPushButton("Save Image")
        btn_save_image.setIcon(QIcon('gui/assets/icons/settings.svg'))
        btn_save_image.setToolTip('Save Image')
        btn_save_image.clicked.connect(self.save_image)

        # Apply button styling
        btn_save_image.setStyleSheet('''
            QPushButton {
                background-color: #fff;
                border: 1px solid gray;
                border-radius: 10px;
                padding: 15px; /* Adjust the padding as needed */
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
        ''')

        layout.addWidget(btn_save_image, 1, 1)  # Add the "Save Image" button
        btn_start_processing = QPushButton("Start Processing")
        btn_start_processing.clicked.connect(self.start_processing)

        layout.addWidget(btn_start_processing, 2, 0, 1, 2)
        # Set equal stretch factors for the columns
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        return widget_static

    @pyqtSlot()
    def start_camera_stream(self):
        config = configparser.ConfigParser()
        config.read('settings.cfg')
        if 'DEFAULT' in config and 'input' in config['DEFAULT']:
            ip_address = config['DEFAULT']['input']
        else:
            ip_address = '0'

        if self.start_button.isChecked():
            # Create an instance of the CameraStream class (assuming it's properly initialized)
            self.camera_stream = CameraStream(ip_address)
            self.camera_stream.start()
            # Connect the CameraStream's signal to update the cctv_frame
            self.camera_stream.frame_processed.connect(self.update_cctv_frame)
            self.start_button.setText("Stop")
        else:
            # Stop the camera stream if the button is unchecked
            self.start_button.setText("Start")
            if hasattr(self, 'camera_stream'):
                self.camera_stream.stop()

    @pyqtSlot(np.ndarray)
    def update_cctv_frame(self, cv_img):
        scaled_image = (
            cv_img * 255.0).clip(0, 255).astype(np.uint8)
        rgb_image = cv2.cvtColor(scaled_image, cv2.COLOR_BGR2RGB)
        qimage = QImage(rgb_image.data, rgb_image.shape[1], rgb_image.shape[0],
                        rgb_image.shape[1] * 3, QImage.Format_RGB888)
        # Convert the image to QPixmap
        pixmap = QPixmap.fromImage(qimage)

        # Scale the pixmap while keeping the aspect ratio
        pixmap = pixmap.scaled(self.cctv_frame.width(),
                               self.cctv_frame.height(), Qt.KeepAspectRatio)

        # Update the camera feed label with the scaled pixmap
        self.cctv_frame.setPixmap(pixmap)
        self.cctv_frame.setAlignment(Qt.AlignCenter)

    def take_screenshot(self):
        # Capture the current frames
        original_frame = self.camera_stream.img
        processed_frame = self.camera_stream.frame
        timestamp = time.time()
        # Save the original and processed frames as images
        cv2.imwrite(f"original_screenshot_{timestamp}.png", original_frame)
        cv2.imwrite(
            f"processed_screenshot_{timestamp}.png", processed_frame * 255)
        print("Screenshots saved successfully.")

    def realtime_frames(self):
        # Create widget
        widget_rt = QWidget()
        widget_rt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create layout
        cctv_layout = QGridLayout(widget_rt)
        cctv_layout.setAlignment(Qt.AlignCenter)
        cctv_layout.setContentsMargins(0, 0, 0, 0)  # Remove any margin

        # CCTV Frames

        self.cctv_frame = QLabel()
        self.cctv_frame.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.cctv_frame.setContentsMargins(0, 0, 0, 0)  # Remove any margin
        self.cctv_frame.setStyleSheet(
            "border: 1px solid gray; border-radius: 10px; background-color: black;")

        # I want to add a label here that will display the camera name
        label = QLabel("")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 20px; font-weight: bold;")
        label.setContentsMargins(0, 0, 0, 0)  # Remove any margin
        # You can create an image label to display the camera feed
        camera_feed = QLabel()
        camera_feed.setAlignment(Qt.AlignCenter)
        camera_feed.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        camera_feed.setContentsMargins(0, 0, 0, 0)

        # Add widgets to the layout
        cctv_layout.addWidget(self.cctv_frame, 1, 1)
        cctv_layout.addWidget(label, 1, 1)
        cctv_layout.addWidget(camera_feed, 1, 1)

        # read the ip address from the settings.cfg file

        self.start_button = QPushButton("Start")
        self.start_button.setCheckable(True)  # Make it a toggle button
        # Connect the button's toggled signal to the start_camera_stream method
        self.start_button.toggled.connect(self.start_camera_stream)

        self.screenshot_button = QPushButton("Screenshot")
        self.screenshot_button.clicked.connect(
            self.take_screenshot)

        # Create the settings button
        manage_camera_button = QPushButton()
        manage_camera_button.setIcon(QIcon('gui/assets/icons/settings.svg'))
        manage_camera_button.setToolTip('Manage Cameras')
        manage_camera_button.setStyleSheet('''
            QPushButton {
                background-color: #fff;
                border: 1px solid gray;
                border-radius: 10px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
        ''')
        manage_camera_button.clicked.connect(self.show_options_popup)
        # Create a horizontal layout and add the start button and the settings button to it
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(manage_camera_button)
        button_layout.addWidget(self.screenshot_button)
        # Add the button layout to the grid layout
        cctv_layout.addLayout(button_layout, 2, 0, 1, 2, Qt.AlignCenter)
        return widget_rt

    def confirm_exit(self):
        reply = QMessageBox.question(
            self, 'Message', "Are you sure to quit?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.quit()
