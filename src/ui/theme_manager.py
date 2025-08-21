from PyQt6.QtWidgets import QMainWindow


class ThemeManager:
    # Base CSS template with placeholders for theme-specific colors
    BASE_QSS = """
        QMainWindow, QWidget {{ 
            background-color: {bg_primary}; 
            color: {text_primary};
            font-family: {font_family};
        }}
        QListWidget {{ 
            background-color: {bg_primary}; 
            color: {text_primary}; 
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 8px;
            selection-background-color: transparent;
        }}
        QListWidget::item {{ 
            background-color: transparent;
            padding: 2px;
            border: none;
            border-radius: 4px;
            margin: 1px;
            transition: background-color 0.2s ease-in-out;
        }}
        QListWidget::item:hover {{ 
            background-color: {selection_bg};
        }}
        QListWidget::item:selected {{ 
            background-color: transparent;
        }}
        QListWidget QWidget {{
            background-color: transparent;
            border-radius: 4px;
            transition: all 0.2s ease-in-out;
        }}
        QListWidget QWidget[selected="true"] {{
            background-color: {selection_bg};
            border: 1px solid {accent_color};
        }}
        QListWidget QWidget:hover {{
            background-color: {selection_bg};
        }}
        QPushButton {{ 
            background-color: {accent_color}; 
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 10px 18px;
            font-weight: bold;
            transition: all 0.2s ease-in-out;
        }}
        QPushButton:hover {{ 
            background-color: {accent_hover}; 
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }}
        QPushButton:pressed {{ 
            background-color: {accent_pressed}; 
            transform: translateY(0px);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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
            padding: 10px 18px;
            border: 1px solid {border_color};
            border-radius: 4px 4px 0 0;
            margin-right: 2px;
            transition: all 0.2s ease-in-out;
        }}
        QTabBar::tab:selected {{
            background-color: {bg_primary};
            border-bottom-color: {accent_color};
            border-bottom-width: 3px;
            color: {accent_color};
            font-weight: bold;
        }}
        QTabBar::tab:hover {{
            background-color: {selection_bg};
            transform: translateY(-1px);
        }}
        QCheckBox {{
            color: {text_primary};
            padding: 5px;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            background-color: {bg_primary};
            border: 2px solid {border_color};
            border-radius: 3px;
            transition: all 0.2s ease-in-out;
        }}
        QCheckBox::indicator:checked {{
            background-color: {accent_color};
            border-color: {accent_color};
        }}
        QCheckBox::indicator:hover {{
            border-color: {accent_color};
            transform: scale(1.05);
        }}
        QCheckBox::indicator:checked:hover {{
            background-color: {accent_hover};
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
        "font_family": '"Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", "Roboto", sans-serif',
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
        "font_family": '"Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", "Roboto", sans-serif',
    }

    @staticmethod
    def apply_light_theme(window: QMainWindow):
        css = ThemeManager.BASE_QSS.format(**ThemeManager.LIGHT_THEME_COLORS)
        window.setStyleSheet(css)

    @staticmethod
    def apply_dark_theme(window: QMainWindow):
        css = ThemeManager.BASE_QSS.format(**ThemeManager.DARK_THEME_COLORS)
        window.setStyleSheet(css)
