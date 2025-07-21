# Contexter

A desktop application for preparing code files to be pasted into LLMs. Features drag-and-drop file management, token counting, and export to clipboard with markdown formatting.

## Features

-   **Drag & Drop Interface:** Add files and folders directly to the application
-   **File Browser:** Navigate through project structure with folder support
-   **Token Counting:** Real-time token count display using tiktoken (GPT-4/3.5-turbo compatible)
-   **Smart Filtering:** Text-only file filtering with .gitignore support
-   **Vim-style Navigation:** Keyboard shortcuts for efficient file management
-   **Clipboard Export:** Copy selected files to clipboard in markdown format
-   **Themes:** Light and dark mode support
-   **Configurable Settings:** Customizable display and filtering options

## Requirements

-   Python 3.12+
-   PyQt6
-   tiktoken
-   pathspec

## Installation & Running

### Using uv (Recommended)

1. Install [uv](https://docs.astral.sh/uv/) if not already installed
2. Clone this repository
3. Run the application:
    ```bash
    uv run python main.py
    ```

### Using pip

1. Clone this repository
2. Create and activate a virtual environment:
    ```bash
    python -m venv .venv
    .venv\Scripts\activate  # Windows
    source .venv/bin/activate  # macOS/Linux
    ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Run the application:
    ```bash
    python main.py
    ```

## Building Executable

Create a standalone executable using PyInstaller:

```bash
uv run pyinstaller main.spec
```

The executable will be created in the `dist/` directory.

## Usage

1. Launch the application
2. Drag and drop files or folders into the drop zone
3. Navigate through the file structure using mouse or vim keys
4. Select files using visual mode (v/V) or standard selection
5. Press 'y' to copy selected files to clipboard
6. Paste the formatted content into your LLM chat

### Keyboard Shortcuts

-   `v` - Enter visual selection mode
-   `V` - Select all items below cursor
-   `y` - Copy selected files to clipboard
-   `d` - Delete selected items from list
-   `C` - Clear entire file list
-   `j/k` - Move up/down
-   `h/l` - Navigate folders (left/right)
-   `g/G` - Go to first/last item
-   `Esc` - Exit visual mode

## Configuration

Settings are stored in `settings.json`:

-   `text_only`: Show only text files (default: true)
-   `hide_empty_folders`: Hide folders without content (default: true)
-   `dark_mode`: Use dark theme (default: false)
-   `show_token_count`: Display token counts (default: true)
