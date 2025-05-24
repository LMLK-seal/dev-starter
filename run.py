import os
import subprocess
import platform
import sys
import time
import webbrowser # For opening the browser

# --- Configuration ---
# IMPORTANT: This is now set to 5173 as requested.
# If your project uses a different port, change this value.
LOCALHOST_PORT = 5173 # Set as default to http://localhost:5173/

# How long to wait for the server to become ready before giving up (in seconds)
SERVER_CHECK_TIMEOUT = 60

# How often to check the server's readiness (in seconds)
RETRY_INTERVAL = 1

# ---------------------

# Install 'requests' if you don't have it: pip install requests
try:
    import requests
except ImportError:
    print("The 'requests' library is not installed.")
    print("Please install it using: 'pip install requests'")
    print("Without 'requests', the script cannot wait for the server to be ready and open the browser automatically.")
    print("You will need to open the browser manually once 'npm run dev' starts.")
    requests = None # Set to None so we can check later and skip functionality

def check_server_ready(url, timeout=SERVER_CHECK_TIMEOUT, interval=RETRY_INTERVAL):
    """
    Checks if the server at the given URL is ready by making HTTP GET requests.
    Returns True if ready, False otherwise.
    """
    if not requests:
        return False # Cannot check without requests library

    print(f"\nAttempting to connect to {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # We only care if it connects and gets a response (any status code)
            # as that indicates the server process is listening.
            response = requests.get(url, timeout=5) # 5-second timeout for each request
            print(f"Server responded (status: {response.status_code}). Server is ready!")
            return True
        except requests.exceptions.ConnectionError:
            print(f"Connection refused to {url}. Server not yet ready. Retrying in {interval}s...")
        except requests.exceptions.Timeout:
            print(f"Request timed out for {url}. Server not yet ready. Retrying in {interval}s...")
        except Exception as e:
            print(f"An unexpected error occurred while checking server: {e}. Retrying in {interval}s...")

        time.sleep(interval)

    print(f"Server at {url} did not become ready within {timeout} seconds.")
    return False

def run_npm_dev_and_open_browser():
    # 1. Determine the script's directory and change to it
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Changing directory to: {script_dir}")
    os.chdir(script_dir)

    npm_command = "npm run dev"
    # Construct the localhost URL using the configured port.
    # The trailing slash isn't strictly necessary for most browsers but doesn't hurt.
    localhost_url = f"http://localhost:{LOCALHOST_PORT}/"

    print(f"Attempting to launch '{npm_command}' in a new terminal...")
    print(f"Expecting server to run on: {localhost_url}")

    process_launched = False # Flag to track if any terminal launched successfully

    # 2. Launch 'npm run dev' in a new terminal window (OS-specific logic)
    if platform.system() == "Windows":
        # 'start cmd /k' opens a new cmd window and '/k' keeps it open
        # 'call' ensures correct execution of npm within cmd
        command = f'start cmd /k "call {npm_command}"'
        try:
            subprocess.Popen(command, shell=True)
            print("Launched 'npm run dev' in a new Command Prompt window.")
            process_launched = True
        except Exception as e:
            print(f"Error launching process on Windows: {e}")
            print("Please ensure 'cmd' is available in your PATH.")

    elif platform.system() == "Darwin": # macOS
        # osascript tells the Terminal app to open a new tab/window and run commands
        # 'cd \"{script_dir}\"': ensures correct directory, handles spaces in path
        # '&& exec bash': keeps the terminal open after npm command finishes or crashes
        terminal_command_str = f'cd \\"{script_dir}\\" && {npm_command} && exec bash'
        command = f'tell application "Terminal" to do script "{terminal_command_str}" activate'
        try:
            subprocess.Popen(['osascript', '-e', command])
            print("Launched 'npm run dev' in a new Terminal window (macOS).")
            process_launched = True
        except Exception as e:
            print(f"Error launching process on macOS: {e}")
            print("Please ensure 'osascript' and 'Terminal.app' are available.")

    else: # Linux (attempts common terminal emulators)
        # The full shell command string to execute *within* the new terminal
        shell_cmd_in_terminal = f'cd "{script_dir}" && {npm_command} && exec bash'

        # List of commands to try for various Linux terminal emulators
        terminal_launch_cmds = [
            # For gnome-terminal, konsole, xfce4-terminal, terminator:
            # They typically take arguments for the command to run.
            # '--' is used by some to signify end of options and start of command.
            ['gnome-terminal', '--', 'bash', '-c', shell_cmd_in_terminal],
            ['konsole', '--', 'bash', '-c', shell_cmd_in_terminal],
            ['xfce4-terminal', '--command', 'bash', '-c', shell_cmd_in_terminal],
            ['terminator', '-e', f'bash -c "{shell_cmd_in_terminal}"'], # Terminator needs it as a single string
            ['lxterminal', '-e', f'bash -c "{shell_cmd_in_terminal}"'], # Lxterminal needs it as a single string
            # For xterm and generic x-terminal-emulator:
            # They use '-e' to execute a single command string.
            ['xterm', '-e', f'bash -c "{shell_cmd_in_terminal}"'],
            ['x-terminal-emulator', '-e', f'bash -c "{shell_cmd_in_terminal}"'],
        ]

        for cmd_parts in terminal_launch_cmds:
            try:
                # The first element is the executable name (e.g., 'gnome-terminal')
                # The rest are its arguments
                subprocess.Popen(cmd_parts)
                print(f"Launched 'npm run dev' using: {cmd_parts[0]} (Linux).")
                process_launched = True
                break # Exit loop once one works
            except FileNotFoundError:
                # This is normal, a user won't have all these terminals; try the next one
                pass
            except Exception as e:
                print(f"Error launching with {cmd_parts[0]}: {e}")

        if not process_launched:
            print("\nCould not find a suitable terminal emulator on your system.")
            print(f"Please run '{npm_command}' manually in your project folder ({script_dir}).")
            sys.exit(1) # Exit if no terminal could be launched

    if not process_launched:
        print("Failed to launch 'npm run dev' process. Cannot proceed with browser opening.")
        print("This terminal (where you ran the Python script) will now close in 5 seconds...")
        time.sleep(5)
        sys.exit(1) # Exit if the subprocess didn't launch for any reason

    # --- 3. Server readiness check and browser opening ---
    # Give the dev server a small initial delay to start listening before we bombard it with requests
    print(f"Giving the dev server {RETRY_INTERVAL * 3} seconds to start listening before checking readiness...")
    time.sleep(RETRY_INTERVAL * 3)

    if check_server_ready(localhost_url):
        print(f"Opening browser to {localhost_url}...")
        webbrowser.open_new_tab(localhost_url)
    else:
        print(f"Server did not become ready at {localhost_url} within {SERVER_CHECK_TIMEOUT} seconds.")
        print("Please check the new terminal for errors or if the server started on a different port.")
        print("You might need to open the browser manually once the server is ready.")

    print("\n--------------------------------------------------------------")
    print("The Python script has finished its task.")
    print("A new terminal should have opened running 'npm run dev'.")
    print("This terminal (where you ran the Python script) will now close in 5 seconds...")
    print("--------------------------------------------------------------")
    time.sleep(5) # Give user time to read output before this script's terminal closes

if __name__ == "__main__":
    run_npm_dev_and_open_browser()
