pyinstaller --clean --noconfirm --onefile --windowed --name "Stapler-y" ^
    --paths src ^
    --hidden-import chat_win ^
    --hidden-import ai ^
    --hidden-import history ^
    --hidden-import elderCore ^
    src/main.py
