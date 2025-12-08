#!/bin/bash

# Function to handle errors
check_error() {
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: $1 failed."
        echo "Fix the error and try again."
        exit 1
    fi
}

echo "Creating Linux Portable Executable..."

# 1. Create Virtual Environment if missing
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    check_error "Virtual Environment Creation"
fi

# 2. Activate and Install Dependencies
source venv/bin/activate
echo "Installing dependencies..."
pip install -r requirements.txt
check_error "Dependency Installation"

# 3. Build with PyInstaller
echo "Building Executable..."
pyinstaller --noconfirm --onefile --windowed --name "Z407_Control_Linux" \
    --add-data "templates:templates" \
    --hidden-import "pyscreeze" \
    --hidden-import "PIL" \
    app.py

if [ $? -ne 0 ]; then
    echo "❌ ERROR: PyInstaller Build Failed."
    exit 1
fi

echo ""
echo "✅ Build Complete!"
echo "Your executable is located in 'dist/Z407_Control_Linux'"
echo "You can delete everything else and just keep that file."
deactivate
