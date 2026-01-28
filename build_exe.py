"""
Build script for creating standalone executable using PyInstaller
"""

import os
import sys
import subprocess


def build_executable():
    """Build standalone executable using PyInstaller"""
    
    print("=" * 60)
    print("CRM Application - Executable Builder")
    print("=" * 60)
    print()
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print("[OK] PyInstaller is installed")
    except ImportError:
        print("[!] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller installed")
    
    print()
    print("Building executable...")
    print("-" * 60)
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Single executable file
        "--windowed",                   # No console window (GUI app)
        "--name=CRM",                   # Name of the executable
        "--add-data=README.md;.",       # Include README
        "--hidden-import=tkcalendar",   # Ensure tkcalendar is included
        "--hidden-import=babel.numbers", # Required by tkcalendar
        "--collect-all=tkcalendar",     # Collect all tkcalendar files
        "--noconfirm",                  # Overwrite without asking
        "crm_app.py"                    # Main script
    ]
    
    # On Windows, use semicolon for --add-data, on Unix use colon
    if sys.platform != "win32":
        cmd[5] = "--add-data=README.md:."
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print()
        print("=" * 60)
        print("[OK] Build completed successfully!")
        print("=" * 60)
        print()
        print("Executable location:")
        print(f"  -> {os.path.abspath('dist/CRM.exe')}")
        print()
        print("You can now distribute the executable file.")
        print("Users can run it without installing Python!")
        print()
        print("Note: The executable will create config.json and customers.db")
        print("      in the same directory when first run.")
        print()
        
    except subprocess.CalledProcessError as e:
        print()
        print("=" * 60)
        print("[ERROR] Build failed!")
        print("=" * 60)
        print()
        print("Error output:")
        print(e.stderr)
        print()
        print("Please check the error messages above and try again.")
        return False
    
    return True


def clean_build_files():
    """Clean up build artifacts"""
    import shutil
    
    print("Cleaning up build files...")
    
    dirs_to_remove = ["build", "__pycache__"]
    files_to_remove = ["CRM.spec"]
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  [OK] Removed {dir_name}/")
    
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"  [OK] Removed {file_name}")
    
    print("[OK] Cleanup complete")


if __name__ == "__main__":
    print()
    
    # Build
    success = build_executable()
    
    # Check if running in a CI environment (like GitHub Actions)
    is_ci = os.environ.get('GITHUB_ACTIONS') == 'true'
    
    if success:
        if is_ci:
            # In CI, auto-cleanup without asking
            print("Running in CI: Improving cleanup automatically...")
            clean_build_files()
        else:
            print()
            try:
                response = input("Clean up build files? (y/n): ").lower()
                if response == 'y':
                    print()
                    clean_build_files()
            except EOFError:
                pass
    
    print()
    if not is_ci:
        try:
            input("Press Enter to exit...")
        except EOFError:
            pass
