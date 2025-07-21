from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules("tiktoken")
hiddenimports += collect_submodules("tiktoken_ext")

# Include tiktoken data files
datas = collect_data_files("tiktoken")
datas += collect_data_files("tiktoken_ext")
