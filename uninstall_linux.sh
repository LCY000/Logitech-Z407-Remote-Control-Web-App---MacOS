#!/bin/bash

# Ensure execution with bash
if [ -z "$BASH_VERSION" ]; then
    exec bash "$0" "$@"
fi

# Z407 Remote Control - Uninstaller
# Author: Androrama

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   Logitech Z407 Remote Control - Uninstaller         ${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Check Root
if [ "$(id -u)" -ne 0 ]; then
  echo -e "${RED}Please run as root (sudo).${NC}"
  echo "Usage: sudo ./uninstall_linux.sh"
  exit 1
fi

# Detect User for Desktop shortcut removal
REAL_USER=$SUDO_USER
if [ -z "$REAL_USER" ]; then
    read -p "Enter your username to check for Desktop shortcut: " REAL_USER
fi
USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

INSTALL_DIR="/opt/Z407_Remote"
MENU_SHORTCUT="/usr/share/applications/z407-control.desktop"
DESKTOP_SHORTCUT_EN="$USER_HOME/Desktop/z407-control.desktop"
DESKTOP_SHORTCUT_ES="$USER_HOME/Escritorio/z407-control.desktop"

echo "The following will be removed:"
if [ -d "$INSTALL_DIR" ]; then echo " - Application directory: $INSTALL_DIR"; fi
if [ -f "$MENU_SHORTCUT" ]; then echo " - Menu shortcut: $MENU_SHORTCUT"; fi
if [ -f "$DESKTOP_SHORTCUT_EN" ]; then echo " - Desktop shortcut: $DESKTOP_SHORTCUT_EN"; fi
if [ -f "$DESKTOP_SHORTCUT_ES" ]; then echo " - Desktop shortcut: $DESKTOP_SHORTCUT_ES"; fi

echo ""
read -p "Are you sure you want to uninstall? [y/N] " response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

echo -e "${BLUE}Removing files...${NC}"

# Remove Install Directory
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo " - Removed /opt/Z407_Remote"
else
    echo " - /opt/Z407_Remote not found."
fi

# Remove Menu Shortcut
if [ -f "$MENU_SHORTCUT" ]; then
    rm "$MENU_SHORTCUT"
    echo " - Removed Menu shortcut"
fi

# Remove Desktop Shortcuts
if [ -f "$DESKTOP_SHORTCUT_EN" ]; then
    rm "$DESKTOP_SHORTCUT_EN"
    echo " - Removed Desktop shortcut (Desktop)"
fi

if [ -f "$DESKTOP_SHORTCUT_ES" ]; then
    rm "$DESKTOP_SHORTCUT_ES"
    echo " - Removed Desktop shortcut (Escritorio)"
fi

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}   Uninstallation Complete. 👋${NC}"
echo -e "${GREEN}===========================================${NC}"
