from PyQt6.QtWidgets import QMainWindow


class ThemeManager:
    @staticmethod
    def apply_light_theme(window: QMainWindow):
        window.setStyleSheet("""
            QMainWindow, QWidget { 
                background-color: #ffffff; 
                color: #000000; 
            }
            QListWidget { 
                background-color: #ffffff; 
                color: #000000; 
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item { 
                background-color: transparent;
                padding: 0;
                border: none;
            }
            QListWidget::item:selected { 
                background-color: transparent;
            }
            QListWidget QWidget {
                background-color: transparent;
            }
            QListWidget QWidget[selected="true"] {
                background-color: #e7f0fa;
            }
            QPushButton { 
                background-color: #4a86e8; 
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: #3a76d8; 
            }
            QPushButton:pressed { 
                background-color: #2a66c8; 
            }
            QFrame { 
                background-color: #ffffff; 
                color: #000000; 
            }
            QLabel { 
                color: #000000; 
            }
            #token_label {
                color: #888;
            }
            QListWidget QWidget[selected="true"] #token_label {
                color: #000000;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #000000;
                padding: 8px 16px;
                border: 1px solid #e0e0e0;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom-color: #4a86e8;
            }
            QTabBar::tab:hover {
                background-color: #e7f0fa;
            }
            QCheckBox {
                color: #000000;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
            }
            QCheckBox::indicator:checked {
                background-color: #4a86e8;
            }
            QCheckBox::indicator:hover {
                border-color: #4a86e8;
            }
            QStatusBar {
                background-color: #f0f0f0;
                color: #000000;
                border-top: 1px solid #e0e0e0;
            }
            QStatusBar QLabel {
                background-color: transparent;
                color: #4a86e8;
                padding: 2px 4px;
                font-size: 12px;
                font-weight: normal;
            }
        """)

    @staticmethod
    def apply_dark_theme(window: QMainWindow):
        window.setStyleSheet("""
            QMainWindow, QWidget, QListWidget, QFrame { 
                background-color: #1e1e1e; 
                color: #ffffff; 
            }
            QListWidget { 
                border: 1px solid #3e3e40;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item { 
                background-color: transparent;
                padding: 0;
                border: none;
            }
            QListWidget::item:selected { 
                background-color: transparent;
            }
            QListWidget QWidget {
                background-color: transparent;
            }
            QListWidget QWidget[selected="true"] {
                background-color: #3e3e40;
            }
            QPushButton { 
                background-color: #007acc; 
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: #1c8ad9; 
            }
            QPushButton:pressed { 
                background-color: #005c99; 
            }
            QLabel { 
                color: #ffffff; 
            }
            #token_label {
                color: #888;
            }
            QListWidget QWidget[selected="true"] #token_label {
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #3e3e40;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d30;
                color: #ffffff;
                padding: 8px 16px;
                border: 1px solid #3e3e40;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-bottom-color: #007acc;
            }
            QTabBar::tab:hover {
                background-color: #3e3e40;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #1e1e1e;
                border: 1px solid #3e3e40;
            }
            QCheckBox::indicator:checked {
                background-color: #007acc;
            }
            QCheckBox::indicator:hover {
                border-color: #007acc;
            }
            QStatusBar {
                background-color: #252526;
                color: #ffffff;
                border-top: 1px solid #3e3e40;
            }
            QStatusBar QLabel {
                background-color: transparent;
                color: #007acc;
                padding: 2px 4px;
                font-size: 10px;
                font-weight: normal;
            }
        """)
