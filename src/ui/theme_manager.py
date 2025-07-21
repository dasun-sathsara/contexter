from PyQt6.QtWidgets import QMainWindow


class ThemeManager:
    # Base CSS template with placeholders for theme-specific colors
    BASE_QSS = """
        QMainWindow, QWidget {{ 
            background-color: {bg_primary}; 
            color: {text_primary}; 
        }}
        QListWidget {{ 
            background-color: {bg_primary}; 
            color: {text_primary}; 
            border: 1px solid {border_color};
            border-radius: 5px;
            padding: 5px;
        }}
        QListWidget::item {{ 
            background-color: transparent;
            padding: 0;
            border: none;
        }}
        QListWidget::item:selected {{ 
            background-color: transparent;
        }}
        QListWidget QWidget {{
            background-color: transparent;
        }}
        QListWidget QWidget[selected="true"] {{
            background-color: {selection_bg};
        }}
        QPushButton {{ 
            background-color: {accent_color}; 
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{ 
            background-color: {accent_hover}; 
        }}
        QPushButton:pressed {{ 
            background-color: {accent_pressed}; 
        }}
        QFrame {{ 
            background-color: {bg_primary}; 
            color: {text_primary}; 
        }}
        QLabel {{ 
            color: {text_primary}; 
        }}
        #token_label {{
            color: {text_secondary};
        }}
        QListWidget QWidget[selected="true"] #token_label {{
            color: {text_primary};
        }}
        QTabWidget::pane {{
            border: 1px solid {border_color};
            background-color: {bg_primary};
        }}
        QTabBar::tab {{
            background-color: {bg_secondary};
            color: {text_primary};
            padding: 8px 16px;
            border: 1px solid {border_color};
        }}
        QTabBar::tab:selected {{
            background-color: {bg_primary};
            border-bottom-color: {accent_color};
        }}
        QTabBar::tab:hover {{
            background-color: {selection_bg};
        }}
        QCheckBox {{
            color: {text_primary};
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            background-color: {bg_primary};
            border: 1px solid {border_color};
        }}
        QCheckBox::indicator:checked {{
            background-color: {accent_color};
        }}
        QCheckBox::indicator:hover {{
            border-color: {accent_color};
        }}
        QStatusBar {{
            background-color: {bg_secondary};
            color: {text_primary};
            border-top: 1px solid {border_color};
        }}
        QStatusBar QLabel {{
            background-color: transparent;
            color: {accent_color};
            padding: 2px 4px;
            font-size: 13px;
            font-weight: normal;
        }}
    """

    LIGHT_THEME_COLORS = {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f0f0f0",
        "text_primary": "#000000",
        "text_secondary": "#888888",
        "border_color": "#e0e0e0",
        "selection_bg": "#e7f0fa",
        "accent_color": "#4a86e8",
        "accent_hover": "#3a76d8",
        "accent_pressed": "#2a66c8",
    }

    DARK_THEME_COLORS = {
        "bg_primary": "#1e1e1e",
        "bg_secondary": "#2d2d30",
        "text_primary": "#ffffff",
        "text_secondary": "#888888",
        "border_color": "#3e3e40",
        "selection_bg": "#3e3e40",
        "accent_color": "#007acc",
        "accent_hover": "#1c8ad9",
        "accent_pressed": "#005c99",
    }

    @staticmethod
    def apply_light_theme(window: QMainWindow):
        css = ThemeManager.BASE_QSS.format(**ThemeManager.LIGHT_THEME_COLORS)
        window.setStyleSheet(css)

    @staticmethod
    def apply_dark_theme(window: QMainWindow):
        css = ThemeManager.BASE_QSS.format(**ThemeManager.DARK_THEME_COLORS)
        window.setStyleSheet(css)
