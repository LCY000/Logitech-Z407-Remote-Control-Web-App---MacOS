#!/bin/bash

# Ensure execution with bash
if [ -z "$BASH_VERSION" ]; then
    exec bash "$0" "$@"
fi

# Z407 Remote Control - Linux Installer
# Author: Androrama

# --- Colors & Styles ---
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# --- Helper Functions ---
print_step() {
    echo -e "${BLUE}${BOLD}>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✔ $1${NC}"
}

print_error() {
    echo -e "${RED}✖ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Spinner function for visual feedback
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# --- Header ---
clear
echo -e "${CYAN}"
echo "███████╗██╗  ██╗ ██████╗ ███████╗    ██████╗ ███████╗███╗   ███╗ ██████╗" 
echo "╚══███╔╝██║  ██║██╔═████╗╚════██║    ██╔══██╗██╔════╝████╗ ████║██╔═══██╗" 
echo "  ███╔╝ ███████║██║██╔██║    ██╔╝    ██████╔╝█████╗  ██╔████╔██║██║   ██║" 
echo " ███╔╝  ╚════██║████╔╝██║   ██╔╝     ██╔══██╗██╔══╝  ██║╚██╔╝██║██║   ██║" 
echo "███████╗     ██║╚██████╔╝   ██║      ██║  ██║███████╗██║ ╚═╝ ██║╚██████╔╝" 
echo "╚══════╝     ╚═╝ ╚═════╝    ╚═╝      ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝" 
echo -e "${NC}"
echo -e "${BOLD}LOGITECH Z407 UNOFFICIAL REMOTE CONTROL - INSTALLER${NC}"
echo "----------------------------------------------------------------"

# 1. Check Root
if [ "$(id -u)" -ne 0 ]; then
  print_error "This script requires root privileges to install to /opt and set permissions."
  echo "Please run with sudo: sudo ./install_linux.sh"
  exit 1
fi

# Get User Info
REAL_USER=$SUDO_USER
if [ -z "$REAL_USER" ]; then
  print_warning "Could not detect the standard user (invoked directly as root?)."
  read -p "Enter your username for the Desktop shortcut: " REAL_USER
fi
USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

# 2. Check Files
APP_DIR=$(pwd)
EXECUTABLE="./dist/Z407_Control_Linux"
ICON="./icon.png"

echo "Checking installation files..."
if [ ! -f "$EXECUTABLE" ]; then
    print_error "Executable not found at $EXECUTABLE"
    echo "Please run ./build_linux.sh first correctly."
    exit 1
fi

if [ ! -f "$ICON" ]; then
    print_warning "icon.png not found in current directory."
    if [ -f "../icon.png" ]; then
        ICON="../icon.png"
        print_success "Found icon in parent directory."
    else
        print_warning "Continuing without specific icon (system default will be used)."
    fi
else
    print_success "Icon found."
fi

# Confirmation
echo ""
echo -e "Installation details:"
echo -e "  • User: ${CYAN}$REAL_USER${NC}"
echo -e "  • Destination: ${CYAN}/opt/Z407_Remote${NC}"
echo ""
read -p "Press [ENTER] to start installation or Ctrl+C to cancel..." dummy
echo ""

# 3. Installation Process
INSTALL_DIR="/opt/Z407_Remote"

print_step "Creating installation directory..."
if [ -d "$INSTALL_DIR" ]; then
    print_warning "Directory exists. Updating existing installation..."
    rm -rf "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR"
print_success "Directory created at $INSTALL_DIR"

print_step "Copying application files..."
cp "$EXECUTABLE" "$INSTALL_DIR/Z407_Control_Linux" & spinner $!
cp "$ICON" "$INSTALL_DIR/icon.png" 2>/dev/null
chmod +x "$INSTALL_DIR/Z407_Control_Linux"
print_success "Files copied successfully."

# 4. Set Permissions
print_step "Configuring Bluetooth permissions..."
echo "Applying 'cap_net_raw,cap_net_admin+eip' to executable..."
setcap 'cap_net_raw,cap_net_admin+eip' "$INSTALL_DIR/Z407_Control_Linux" & spinner $!
print_success "Permissions set. You can run the app without sudo!"

# 5. Check Dependencies
print_step "Checking optional dependencies..."
if ! command -v xdotool > /dev/null 2>&1; then
    print_warning "'xdotool' is missing. It is required for PC media keys (Play/Pause/Vol)."
    read -p "  Do you want to install xdotool now using apt? [Y/n] " install_xdo
    if [[ "$install_xdo" =~ ^[Yy]$ || -z "$install_xdo" ]]; then
        echo "  Running apt install xdotool..."
        apt-get update -qq && apt-get install -y xdotool -qq & spinner $!
        print_success "xdotool installed."
    else
        echo "  Skipping xdotool. Media keys won't work."
    fi
else
    print_success "'xdotool' is already installed."
fi

# 6. Create Shortcuts
print_step "Creating Shortcuts..."

# Ask for browser auto-open
echo -e -n "\n${BOLD}Do you want the shortcut to also open the browser (web interface)? [Y/n] ${NC}"
read -r open_browser
FINAL_EXEC="$INSTALL_DIR/Z407_Control_Linux"

if [[ "$open_browser" =~ ^[Yy]$ || -z "$open_browser" ]]; then
    # Create wrapper script
    WRAPPER_SCRIPT="$INSTALL_DIR/launch_with_browser.sh"
    
    # Write wrapper content
cat <<EOF > "$WRAPPER_SCRIPT"
#!/bin/bash
echo "Starting Z407 Remote & Browser..."

# Function to handle shutdown signals
cleanup() {
    echo "Stopping Z407 Remote..."
    if [ -n "\$APP_PID" ]; then
        kill -SIGINT "\$APP_PID" 2>/dev/null
        wait "\$APP_PID" 2>/dev/null
    fi
    exit 0
}

# Trap signals (Ctrl+C, etc)
trap cleanup SIGINT SIGTERM

"$INSTALL_DIR/Z407_Control_Linux" &
APP_PID=\$!

sleep 3
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:5000" > /dev/null 2>&1
elif command -v wslview &> /dev/null; then
    wslview "http://localhost:5000" > /dev/null 2>&1
else
    echo "Could not detect browser opener. Please open http://localhost:5000 manually."
fi

# Wait for process and capture exit code
wait \$APP_PID
EXIT_CODE=\$?

# If exit code is 0 (clean) or 130 (SIGINT), exit cleanly to avoid warnings
if [ \$EXIT_CODE -eq 0 ] || [ \$EXIT_CODE -eq 130 ]; then
    exit 0
else
    exit \$EXIT_CODE
fi
EOF

    chmod +x "$WRAPPER_SCRIPT"
    FINAL_EXEC="$WRAPPER_SCRIPT"
    print_success "Shortcut configured to open browser."
else
    echo "  Shortcut will only start the server."
fi

DESKTOP_ENTRY="[Desktop Entry]
Version=1.0
Type=Application
Name=Logitech Z407 Remote
Comment=Control Logitech Z407 Speakers
Exec=$FINAL_EXEC
Icon=$INSTALL_DIR/icon.png
Terminal=true
Categories=Audio;AudioVideo;Utility;
Keywords=Logitech;Z407;Remote;Volume;
StartupNotify=true"

# Desktop Shortcut
echo -e -n "\n${BOLD}Create Desktop shortcut? [Y/n] ${NC}"
read -r create_desktop
if [[ "$create_desktop" =~ ^[Yy]$ || -z "$create_desktop" ]]; then
    DESKTOP_DIR="$USER_HOME/Desktop"
    if [ -d "$USER_HOME/Escritorio" ]; then DESKTOP_DIR="$USER_HOME/Escritorio"; fi
    
    if [ -d "$DESKTOP_DIR" ]; then
        echo "$DESKTOP_ENTRY" > "$DESKTOP_DIR/z407-control.desktop"
        chmod +x "$DESKTOP_DIR/z407-control.desktop"
        chown "$REAL_USER":"$REAL_USER" "$DESKTOP_DIR/z407-control.desktop"
        print_success "Desktop shortcut created."
    else
        print_error "Desktop folder not found ($DESKTOP_DIR). Skipping."
    fi
else
    echo "  Skipped Desktop shortcut."
fi

# Menu Shortcut
echo -e -n "${BOLD}Create Application Menu shortcut? [Y/n] ${NC}"
read -r create_menu
if [[ "$create_menu" =~ ^[Yy]$ || -z "$create_menu" ]]; then
    echo "$DESKTOP_ENTRY" > "/usr/share/applications/z407-control.desktop"
    print_success "Menu shortcut created."
else
    echo "  Skipped Menu shortcut."
fi

echo ""
echo "----------------------------------------------------------------"
echo -e "${GREEN}${BOLD}   INSTALLATION COMPLETED SUCCESSFULLY!   ${NC}"
echo "----------------------------------------------------------------"
echo -e "You can launch the app from the shortcuts created."
echo -e "The app runs in a terminal window to check status."
echo ""
