
############################################################################
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://mozilla.org/MPL/2.0/.
#
############################################################################
#
#Copyright (c) 2026 Pedro Tagwato
#Original Project: https://github.com/tagwato/PyWinCMD
#
############################################################################

__version__ = "2.0.0"



# HOW TO TEST?
# To test this program, run PyWinCMD and type the commands listed in the 'TEST_CASES.txt' file



import cmd
import os
import msvcrt
import sys
import re
import time
import json
import base64
import shutil
import subprocess
import platform
import ctypes
import struct
from ctypes import wintypes


# Some ANSI colors (RGB)
# See more at:   https://en.wikipedia.org/wiki/ANSI_escape_code
#         AND:   https://rgbcolorpicker.com/
#         and:   https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797  <<-- has codes for bold, blink, italic etc.
#  \x1b[38;2;r;g;bm  <<--- foreground template
#  \x1b[48;2;r;g;bm  <<--- background template
#--------  FOREGROUND
FG_WHITE =  "\x1b[38;2;255;255;255m"  
FG_BLACK =  "\x1b[38;2;0;0;0m"  
FG_RED   =  "\x1b[38;2;255;0;0m"  
FG_GREEN =  "\x1b[38;2;0;255;0m"  
FG_BLUE  =  "\x1b[38;2;0;0;255m"  
FG_YELLOW=  "\x1b[38;2;255;255;0m"
FG_PURPLE=  "\x1b[38;2;255;0;255m"
FG_CYAN  =  "\x1b[38;2;0;255;255m"
FG_ORANGE =  "\x1b[38;2;255;180;0m"
FG_DGRAY =  "\x1b[38;2;80;80;80m"
FG_LGRAY =  "\x1b[38;2;128;128;128m"
#--------  BACKGROUND
BG_WHITE =  "\x1b[48;2;255;255;255m"  
BG_BLACK =  "\x1b[48;2;0;0;0m"  
BG_RED   =  "\x1b[48;2;255;0;0m"  
BG_GREEN =  "\x1b[48;2;0;255;0m"  
BG_DGREEN = "\x1b[48;2;0;105;0m"
BG_BLUE  =  "\x1b[48;2;0;0;255m"  
BG_YELLOW=  "\x1b[48;2;255;255;0m"
BG_PURPLE=  "\x1b[48;2;255;0;255m"
BG_DPURPLE = "\x1b[48;2;105;0;105m"
BG_CYAN  =  "\x1b[48;2;0;255;255m"
BG_ORANGE =  "\x1b[48;2;255;180;0m"
BG_DGRAY =  "\x1b[48;2;80;80;80m"
BG_LGRAY =  "\x1b[48;2;128;128;128m"
BG_CARMIN = "\x1b[48;2;72;0;0m"

#--------- RESET -----
RST_CLR =  "\x1b[0m"   #<<---- this DOES NOT reset bold, italic, blink, but there are other reset codes, see 3rd link above




class PyEmulatedCMD(cmd.Cmd):
    intro = (
        "\033[94m=== PyWinCmd - CMD prompt emulator in Python ===\033[0m\n"
        "Supports commands, scripts, interactive programs and maintains the environment state.\n"
    )
    
    def __init__(self, inherited_title=None, inherited_dir=None, inherited_env=None, inherited_drives=None, inherited_macros=None):
        super().__init__()
        
        os_name = platform.system()
        if os_name.lower() != "windows":
            raise ValueError(f"This program only works on the Windows operating system, not on: {os_name} ")

        self.verbosity = False
        self.debug = False
        self.set_of_complex_subcommands=set(["doskey", "cd", "chdir", "pushd"])
        self.default_state_filename = "state_pywincmd.json"
        self.current_dir = inherited_dir if inherited_dir else os.getcwd()
        self.current_env = inherited_env if inherited_env else dict(os.environ)
        self.drive_dirs = inherited_drives if inherited_drives else {}
        self.macros = inherited_macros if inherited_macros else {}
        if inherited_title:
            self.title = inherited_title 
        else:
            self.title = "PyWinCMD"
        os.system(f"title {self.title}")

        try:
            self.current_codepage = ctypes.windll.kernel32.GetConsoleCP()
        except Exception as e:
            print(e)
            self.current_codepage = "1252" #<-- for Portuguese, generally better than '850', see XCOPY output
        self.last_errorlevel = "0"
        
        # If no PROMPT is defined in the inherited environment, assumes the classic default $P$G
        if 'PROMPT' not in self.current_env or not self.current_env['PROMPT']:
            self.current_env['PROMPT'] = "$P$G"
            
        # History Management
        self.history = []
        self.history_index = 0

        self.update_prompt_visual()
        self.show_help_f1()

    def show_help_f1(self):
        cols = shutil.get_terminal_size((120, 30)).columns
        help_title = f"PyWinCMD HELP (v{__version__})"
        num_spcs  = 1/2 * (cols - len(help_title))
        spcs = int(num_spcs) * ' ' 
        help_title = spcs + help_title + spcs
        if len(help_title) < cols:
            help_title += ' '
        elif len(help_title) > cols:
            help_title = help_title[:-1]
 
        print("\n" + FG_BLACK + BG_CYAN + help_title + RST_CLR)
        print("PyWinCMD simulates the CMD prompt on Windows systems. " 
              "It's useful when access to the native prompt is restricted. ")
        print("The state of the environment is preserved throughout the execution of commands: directory, variables, macros, codepage.")
        print(r"""
Navigation Keys and Shortcuts:
  [ F1 ]           : Displays this help screen
  [ F2 or Ctrl+F2] : Saves the current state of the environment to a JSON file   (CTRL+F2 opens a visual FileChooser)
  [ F3 or Ctrl+F3] : Restores the previously saved state of the environment   (CTRL+F3 opens a visual FileChooser)
  [ F4 ]           : Shows the current state of this PyWinCmd command session
  [ F5 ] , [F7]    : F5-Toggles the command line execution verbosity  |  F7-Toggles a pseudo-debug feature (ON/OFF)
  [ ↑ ] and [ ↓ ]  : Navigates through previously executed commands (History)
  [ TAB ]          : Auto-completes file and folder names when typing in the command line -- also during F2 and F3
                     Note: Use TAB repeatedly to cycle through autocomplete options (if more than one)
  [ ESC ]          : Clears the entire command line that is being typed
  [ Ctrl+,]        : Opens the 'Windows Terminal' settings window, if available
  
All 'CMD' commands can be executed. Type HELP to list them all. 
For help on a specific command, type <<command>> /? or HELP <<command>>  -  Examples:  COPY /?   or   help COPY
SETLOCAL/ENDLOCAL, PUSHD/POPD work only WHILE the command line is running (They work normally within a BAT/CMD).
  
To run a script file such as BAT, CMD, or PS1, simply type its name and press ENTER.
It is also possible to run any program from the PyWinCmd prompt, including interactive programs like 'python'. 
You can even activate virtual environments (virtualenv) with different Python versions and execute it. 

Advanced Feature - DOSKEY:
  PyWinCmd supports the use of DOSKEY for creating macros/aliases BUT it must be the ONLY command on the cmdline
  - Example of macro creation:  DOSKEY cat=type $*   Another example: doskey catfi=type $1 $B find /I $2
  - For help on creating and managing macros:  DOSKEY /?  or  HELP DOSKEY
  """
)

    # Internal class to define the OPENFILENAMEW structure as specified by the Windows API
    class OPENFILENAMEW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD),
            ("hwndOwner", wintypes.HWND),
            ("hInstance", wintypes.HINSTANCE),
            ("lpstrFilter", wintypes.LPCWSTR),
            ("lpstrCustomFilter", wintypes.LPWSTR),
            ("nMaxCustFilter", wintypes.DWORD),
            ("nFilterIndex", wintypes.DWORD),
            ("lpstrFile", wintypes.LPWSTR),
            ("nMaxFile", wintypes.DWORD),
            ("lpstrFileTitle", wintypes.LPWSTR),
            ("nMaxFileTitle", wintypes.DWORD),
            ("lpstrInitialDir", wintypes.LPCWSTR),
            ("lpstrTitle", wintypes.LPCWSTR),
            ("Flags", wintypes.DWORD),
            ("nFileOffset", wintypes.WORD),
            ("nFileExtension", wintypes.WORD),
            ("lpstrDefExt", wintypes.LPCWSTR),
            ("lCustData", wintypes.LPARAM),
            ("lpfnHook", ctypes.c_void_p),
            ("lpTemplateName", wintypes.LPCWSTR),
            ("pvReserved", ctypes.c_void_p),
            ("dwReserved", wintypes.DWORD),
            ("FlagsEx", wintypes.DWORD)
        ]


    def select_from_native_file_chooser(self, dialog_type="open", title=None, initial_dir=None, initial_file=None, filter_string="All Files\0*.*\0\0", default_ext=None):
        """
        Opens a Windows native File-Chooser dialog for opening or saving files.
        
        :param dialog_type: "open" or "save"
        :param title: The title of the dialog window.
        :param initial_dir: The starting directory (defaults to the current working directory).
        :param initial_file: Default file name to pre-fill in the input text field.
        :param filter_string: A null-separated string defining the file filters (must end in \0\0).
        :param default_ext: The default extension to append if the user doesn't type one (e.g., "txt").
        :return: The selected file path as a string, or None if the user canceled.
        """
        is_save = dialog_type.lower() == "save"
        
        # Initialize the OPENFILENAMEW structure
        ofn = self.OPENFILENAMEW()
        ofn.lStructSize = ctypes.sizeof(self.OPENFILENAMEW)
        ofn.lpstrTitle = title if title else ("Save File" if is_save else "Open File")
        
        if initial_dir:
            ofn.lpstrInitialDir = initial_dir

        # We must keep references to these buffers so they aren't garbage collected during the API call
        filter_buffer = ctypes.create_unicode_buffer(filter_string)
        ofn.lpstrFilter = ctypes.cast(filter_buffer, wintypes.LPCWSTR)

        if default_ext:
            def_ext_buffer = ctypes.create_unicode_buffer(default_ext)
            ofn.lpstrDefExt = ctypes.cast(def_ext_buffer, wintypes.LPCWSTR)

        # Allocate a buffer to hold the returned file path
        buffer_size = 32768  #<<--- Supports Windows extended path size, this big

        if initial_file:
            file_buffer = ctypes.create_unicode_buffer(initial_file, buffer_size)
        else:
            file_buffer = ctypes.create_unicode_buffer(buffer_size)
            file_buffer[0] = '\0'

        ofn.lpstrFile = ctypes.cast(file_buffer, wintypes.LPWSTR)
        ofn.nMaxFile = buffer_size

        # Define flags
        OFN_EXPLORER = 0x00080000      # Use the newer Explorer-style dialog
        OFN_PATHMUSTEXIST = 0x00000800 # Prevent user from typing a path that doesn't exist
        OFN_FILEMUSTEXIST = 0x00001000 # (Open) Prevent user from typing a file that doesn't exist
        OFN_OVERWRITEPROMPT = 0x00000002 # (Save) Warn if selecting an existing file
        
        if is_save:
            ofn.Flags = OFN_EXPLORER | OFN_PATHMUSTEXIST | OFN_OVERWRITEPROMPT
        else:
            ofn.Flags = OFN_EXPLORER | OFN_PATHMUSTEXIST | OFN_FILEMUSTEXIST

        # Call the appropriate function from comdlg32.dll
        comdlg32 = ctypes.windll.comdlg32
        if is_save:
            success = comdlg32.GetSaveFileNameW(ctypes.byref(ofn))
        else:
            success = comdlg32.GetOpenFileNameW(ctypes.byref(ofn))
            
        if success:
            return file_buffer.value
        
        return None


    def get_user_input_from_native_CMD(self, prompt_str):
        timestamp = int(time.time() * 1000)
        PWC_VAR   = "PWC_VAR_"+ str(timestamp)
        vnada   = "###Nothing##Set##Yet###"
        # TRICK: We will use the native SET /P command to get user input, because this
        # will make the NATIVE autocomplete of the command work as usual,  allowing the
        # user to select file names among the existing ones, via TAB key, if desired !
        # (If we obtained input via python function, this kind of autocomplete WOULD NOT work)
        set_p_cmd = f"set {PWC_VAR}={vnada} & ECHO {prompt_str} & SET /p {PWC_VAR}="
        self._execute_cmd(f"{set_p_cmd}") # <-- CMD commands called this way ARE NOT logged in history, only when passing through self.readline_with_tab()
        resposta = self.current_env.pop(f'{PWC_VAR}', None)  # The pop() is destructive and we want exactly that: remove it from the environment
        if resposta == vnada: 
            resposta = None  #<<--- If the value in PWC_VAR remained = vnada, it's because only a ENTER was typed, or CTRL+C was used
        return resposta       


    def save_state_f2(self,  filepath=None, file_chooser=False):
        print("\n--- SAVE ENVIRONMENT STATE ---")
        if not filepath:
            if file_chooser:  # Let's use the native Dialog to get the filepath
                filepath = self.select_from_native_file_chooser(dialog_type='save', 
                                                                title="Save the current state to a file",
                                                                initial_dir=self.current_dir,
                                                                initial_file=self.default_state_filename,
                                                                filter_string="Supported Files (*.json;*.txt)\0*.json;*.txt\0\0",
                                                                default_ext='json')                
                if not filepath:  #<-- If selection was canceled inside the FileChooser
                    print(FG_YELLOW + "Operation canceled!" + RST_CLR)
                    return False
            else:  # Let's use the command line to get the filepath
                prompt_str = f"File to save [D = default '{self.default_state_filename}', start of name+TAB = autocomplete, ESC clears, C = cancel]:"
                while filepath is None:  # if empty ENTER or Ctrl+C was pressed while executing SET /p
                    filepath = self.get_user_input_from_native_CMD(prompt_str)

                if filepath.strip().upper() == "C":   # If C+ENTER was typed at the input, cancel the saving
                    print(FG_YELLOW + "Operation canceled by user" + RST_CLR)
                    return False
                elif  filepath.strip().upper() == "D":  #  D = Default state filename 
                    filepath = self.default_state_filename
            
                filepath = filepath.strip()
                if not os.path.isabs(filepath):
                    # Strip off leading and trailer quotes, if present
                    if len(filepath) >= 2 and filepath[0] == '\"' and filepath[0] == filepath[-1]:
                        filepath = filepath[1:-1]
                    filepath = os.path.join(self.current_dir, filepath)

                if os.path.exists(filepath):  # Only needs to test this when using the command line; FileChooser already checks this
                    resp = None
                    try:
                        resp = input(f"The file {filepath} already exists, do you want to overwrite it? (Y/N): ")
                    except:  # if Ctrl+C is pressed during this input() call, it lands here
                        resp = 'N'
                    if resp and resp.upper().startswith('N'):
                        print(FG_YELLOW + "Operation canceled!" + RST_CLR)
                        return False
                
        state_data = {
            "title": self.title,
            "dir": self.current_dir,
            "env": self.current_env,
            "drives": self.drive_dirs,
            "macros": self.macros,
            "history": self.history,
            "codepage": self.current_codepage
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=4)
            print(f"[OK] State saved successfully to: {filepath}\n")
            return True
        except Exception as e:
            print(e)
            print(FG_RED + f"[ERROR] Failed to save state to: {filepath}\n" + RST_CLR)
            return False


    def load_state_f3(self, file_chooser=False):
        print("\n--- LOAD ENVIRONMENT STATE ---")

        if file_chooser:  # Let's use the native Dialog to get the filepath
            filepath = self.select_from_native_file_chooser(dialog_type='open', 
                                                            initial_dir=self.current_dir,
                                                            title="Load state from a file",
                                                            filter_string="Supported Files (*.json;*.txt)\0*.json;*.txt\0\0")
            if not filepath:  #<-- If selection was canceled inside the FileChooser
                print(FG_YELLOW + "Operation canceled!" + RST_CLR)
                return False
        else:  # Let's use the command line to get the filepath
            prompt_str = f"File to load [D = default '{self.default_state_filename}', start of name+TAB = autocomplete, ESC clears, C = cancel]:"
            filepath = None
            while filepath is None:  # if empty ENTER or Ctrl+C was pressed while executing SET /p
                filepath = self.get_user_input_from_native_CMD(prompt_str)

            if filepath.strip().upper() == "C":   # If C+ENTER was typed at the input, cancel the loading
                print(FG_YELLOW + "Operation canceled by user" + RST_CLR)
                return False
            elif  filepath.strip().upper() == "D":  #  D = Default state filename 
                filepath = self.default_state_filename

            filepath = filepath.strip()            
            if not os.path.isabs(filepath):
                # Strip off leading and trailer quotes, if present
                if len(filepath) >= 2 and filepath[0] == '\"' and filepath[0] == filepath[-1]:
                    filepath = filepath[1:-1]
                filepath = os.path.join(self.current_dir, filepath)
                
            if not os.path.exists(filepath):
                print(FG_RED + f"[ERROR] File '{filepath}' not found!\n" + RST_CLR)
                return False
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            tst_cur_dir = state_data.get("dir", self.current_dir)
            if not os.path.exists(tst_cur_dir):  #<<=== if removed/renamed after the file was saved
                print(FG_RED + "[ERROR] Directory name in the 'dir' key of the loaded file is invalid" + RST_CLR)
                return False
            
            # Handles possible removal/renaming of drives or paths mapped to them
            # as well as possible removal of portable drives (USB unplugged) :  
            drive_dirs = state_data.get("drives", self.drive_dirs)  
            for d in drive_dirs.values():
                if not os.path.exists(d): 
                    print(FG_RED + f"[ERROR] Directory name in the 'drive_dirs' key of the loaded file is invalid: '{d}'" + RST_CLR)
                    return False

            self.title = state_data.get("title", self.title)
            self.current_dir = state_data.get("dir", self.current_dir)
            self.current_env = state_data.get("env", self.current_env)
            self.drive_dirs = state_data.get("drives", self.drive_dirs)
            self.macros = state_data.get("macros", self.macros)
            self.history = state_data.get("history", self.history)
            self.current_codepage = state_data.get("codepage", self.current_codepage)
            
            self.history_index = len(self.history)
            self.update_prompt_visual()
            sys.stdout.write(self.prompt) # Displays the Prompt prefix already updated from the file
            sys.stdout.flush()
            print(f"[OK] State loaded successfully from: {filepath}")
            self._execute_cmd(f"TITLE {self.title}")
            return True
        except Exception as e:
            print(e)
            print(FG_RED + f"[ERROR] Failed to load state" + RST_CLR)
            return False

            
    def show_state_f4(self):
        print("\n\n" + "="*80)
        print(" COMPLETE SESSION STATE (F4) ".center(80, "="))
        print("="*80)
            
        print(f"\n[ENVIRONMENT VARIABLES (ENV)]")
        if self.current_env:
            for key, value in sorted(self.current_env.items()):
                print(f"  {key}={value}")
        else:
            print("  No environment variables defined.")            
        
        print(f"\n[CURRENT DIRECTORY]")
        print(f"  {self.current_dir}")
        
        print(f"\n[CODE PAGE (CHCP)]")
        print(f"  {self.current_codepage}")
        
        print(f"\n[LAST ERRORLEVEL]")
        print(f"  {self.last_errorlevel}")
        
        print(f"\n[DIRECTORIES PER DRIVE]")
        if self.drive_dirs:
            for drive, path in self.drive_dirs.items():
                print(f"  {drive}: -> {path}")
        else:
            print("  No specific drive directory registered.")
            
        print(f"\n[MACROS (DOSKEY)]")
        if self.macros:
            for key, value in self.macros.items():
                print(f"  {key}={value}")
        else:
            print("  No macro defined.")
            
        print(f"\n[COMMAND HISTORY]")
        print(f"  Total commands : {len(self.history)}")
        print(f"  Indent index   : {self.history_index}")
        if self.history:
            print("  List:")
            for i, cmd_line in enumerate(self.history, 1):
                print(f"    {i:03d}: {cmd_line}")
        else:
            print("  Empty history.")
        print()


    def update_prompt_visual(self):
        # Resolves the special codes of the Windows PROMPT command
        raw_prompt = self.current_env.get('PROMPT', '$P$G')
        resolved = raw_prompt
        resolved = resolved.replace("$P", self.current_dir)
        resolved = resolved.replace("$G", ">")
        resolved = resolved.replace("$L", "<")
        resolved = resolved.replace("$B", "|")
        resolved = resolved.replace("$A", "&")
        resolved = resolved.replace("$C", "(")
        resolved = resolved.replace("$F", ")")
        resolved = resolved.replace("$E", "\033")
        resolved = resolved.replace("$S", " ")
        resolved = resolved.replace("$T", time.strftime("%H:%M:%S"))
        resolved = resolved.replace("$D", time.strftime("%a %d/%m/%Y"))
        resolved = resolved.replace("$$", "$")
        resolved = resolved.strip().replace('\r', '').replace('\n', '')
        print() # The native CMD prompt always put an empty line before the new prompt
        self.prompt = f"\033[96m[PWC]{resolved}\033[0m "


    def get_native_console_size(self, fallback=(132, 28)):
        """Gets the real console size (columns, lines) using native Windows API via ctypes."""
        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short),
                        ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]

        class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
            _fields_ = [("dwSize", COORD),
                        ("dwCursorPosition", COORD),
                        ("wAttributes", ctypes.c_ushort),
                        ("srWindow", SMALL_RECT),
                        ("dwMaximumWindowSize", COORD)]

        STD_OUTPUT_HANDLE = -11
        
        try:
            h_stdout = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            csbi = CONSOLE_SCREEN_BUFFER_INFO()
            success = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(h_stdout, ctypes.byref(csbi))
            
            if success:
                # Calculate width and height from the visible window rectangle
                cols = csbi.srWindow.Right - csbi.srWindow.Left + 1
                lines = csbi.srWindow.Bottom - csbi.srWindow.Top + 1
                return cols, lines
        except Exception:
            pass
            
        return fallback


    # =========================================================================
    # --- KEYBOARD READING AND NAVIGATION INTERFACE ---
    # =========================================================================
    def readline_with_tab(self):
        buffer = ""
        cursor_pos = 0
        self.history_index = len(self.history)
    
        def draw_line(old_cursor_pos, new_buffer, new_cursor_pos, force_fresh=False):
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            visible_prompt = ansi_escape.sub('', self.prompt)
            prompt_len = len(visible_prompt)
            
            # 1. Try shutil first with a (1, 1) fallback
            term_size = shutil.get_terminal_size((1, 1))
            cols, lines = term_size.columns, term_size.lines
            
            # 2. If shutil fails and returns the fallback, use the native Windows API
            if cols == 1 and lines == 1:
                cols, lines = self.get_native_console_size(fallback=(150, 30))
                
            # Helper to calculate physical rows/cols perfectly modeling "deferred wrap"
            def get_row_col(pos):
                if pos == 0:
                    return 0, 0
                # (pos - 1) // cols keeps exact multiples (e.g. 80) on row 0 instead of row 1
                return (pos - 1) // cols, (pos - 1) % cols + 1
            
            # Calculate where the cursor currently is physically
            old_total_pos = prompt_len + old_cursor_pos
            old_row, _ = get_row_col(old_total_pos)
            
            if not force_fresh:
                if old_row > 0:
                    sys.stdout.write(f"\033[{old_row}A") # Move UP to the start of the prompt
                sys.stdout.write("\r")
                sys.stdout.write("\033[0J") # Clear everything below
            
            # Print the new prompt and buffer
            sys.stdout.write(self.prompt + new_buffer)
            
            # If the user is editing in the middle of the string, manually place the cursor
            if new_cursor_pos < len(new_buffer):
                end_total_pos = prompt_len + len(new_buffer)
                end_row, _ = get_row_col(end_total_pos)
                
                target_total_pos = prompt_len + new_cursor_pos
                target_row, target_col = get_row_col(target_total_pos)
                
                rows_to_move_up = end_row - target_row
                if rows_to_move_up > 0:
                    sys.stdout.write(f"\033[{rows_to_move_up}A")
                    
                # ANSI cursor columns are 1-based, target_col is already 0-based + 1 from get_row_col
                sys.stdout.write(f"\033[{target_col + 1}G") 
                
            sys.stdout.flush()
        
        tab_matches = []
        tab_index = -1
        last_key_was_tab = False
        last_completion_len = 0

        while True:
            ch = msvcrt.getwch()     
            old_cursor_pos = cursor_pos
            force_fresh = False

            if ch != "\t":
                last_key_was_tab = False

            if ch == "\r":
                print()
                # Only adds to the global history if it is not a prompt for the user to reply to
                if not self.history or self.history[-1] != buffer:
                    self.history.append(buffer)
                return buffer

            elif ch == "\x03":  # <<======== Ctrl+C 
                if len(buffer) > 0:
                    print(FG_YELLOW + "\nTyping interrupted by Ctrl+C" + RST_CLR)
                else:
                    print()
                raise KeyboardInterrupt   # <-- the Ctrl+C will be handled in main()
                
            elif ch == "\x1b":  # ESC Key
                    # Default behavior at the main prompt: clears the current line
                    buffer = ""
                    cursor_pos = 0

            elif ch == "\b":
                if cursor_pos > 0:
                    buffer = buffer[:cursor_pos - 1] + buffer[cursor_pos:]
                    cursor_pos -= 1

            elif ch == "\t":
                if last_key_was_tab and tab_matches:
                    # It's a repeated TAB: rotates to the next file in the list
                    tab_index = (tab_index + 1) % len(tab_matches)
                    completion = tab_matches[tab_index]
                    
                    # Removes the previous option and inserts the new one
                    tail = buffer[cursor_pos:]
                    buffer = buffer[:cursor_pos - last_completion_len] + completion + tail
                    cursor_pos = cursor_pos - last_completion_len + len(completion)
                    last_completion_len = len(completion)
                    
                else:
                    # It's the first TAB: Does a greedy search and saves the results
                    text_to_complete = buffer[:cursor_pos]
                    cmd_part = text_to_complete.strip().split()[0].lower() if text_to_complete.strip() else ""
                    only_dirs = (cmd_part in ["cd", "chdir", "pushd", "tree"])

                    # --- UPDATED LOGIC: Only record spaces that are OUTSIDE of quotes ---
                    in_quote = False
                    quote_start = -1
                    unquoted_spaces = []
                    
                    for i, char in enumerate(text_to_complete):
                        if char == '"':
                            in_quote = not in_quote
                            if in_quote:
                                quote_start = i
                        elif char == ' ' and not in_quote:
                            unquoted_spaces.append(i)

                    matches = []
                    current_text = ""

                    if in_quote:
                        token_start = quote_start
                        current_text = text_to_complete[token_start:]
                        matches = self._path_completer(current_text, only_dirs=only_dirs)
                    else:
                        found_match = False
                        # Use unquoted_spaces instead of searching indiscriminately
                        for space_idx in unquoted_spaces:
                            test_start = space_idx + 1
                            test_text = text_to_complete[test_start:]
                            
                            if not test_text and space_idx != unquoted_spaces[-1]:
                                continue
                                
                            m = self._path_completer(test_text, only_dirs=only_dirs)
                            if m:
                                matches = m
                                current_text = test_text
                                found_match = True
                                break
                                
                        if not found_match:
                            last_space = unquoted_spaces[-1] if unquoted_spaces else -1
                            token_start = last_space + 1 if last_space != -1 else 0
                            current_text = text_to_complete[token_start:]
                            matches = self._path_completer(current_text, only_dirs=only_dirs)

                    if matches:
                        # Saves the state for the next TABs
                        tab_matches = matches
                        tab_index = 0
                        last_key_was_tab = True
                        
                        completion = tab_matches[0]
                        tail = buffer[cursor_pos:]
                        
                        # Makes the first replacement
                        buffer = buffer[:cursor_pos - len(current_text)] + completion + tail
                        cursor_pos = cursor_pos - len(current_text) + len(completion)
                        last_completion_len = len(completion)

            elif ch in ("\x00", "\xe0"):
                sub_ch = msvcrt.getwch()
                # --- FUNCTION KEYS (F1, F2, F3) ---
                if sub_ch == ";": # F1 (Scancode 59)
                    print() # Breaks the current line so it doesn't overwrite the buffer
                    self.show_help_f1()
                    force_fresh = True
                elif sub_ch == "<": # F2 (Scancode 60)
                    print()
                    self.save_state_f2()
                    force_fresh = True
                elif sub_ch == "=": # F3 (Scancode 61)
                    print()
                    self.load_state_f3()
                    force_fresh = True
                elif sub_ch == ">": # F4 (Scancode 62)
                    print()
                    self.show_state_f4()
                    force_fresh = True
                elif sub_ch == "?": # F5 (Scancode 63)
                    self.verbosity = not self.verbosity  # Just switch OFF/ON/OFF/ON...
                    status = FG_GREEN + "-- ON --" if self.verbosity else FG_RED + "-- OFF --"
                    print()
                    print("Command line execution verbosity is now: " + status + RST_CLR )
                    force_fresh = True
                elif sub_ch == "A": # F7 (Scancode 65)
                    self.debug = not self.debug  # Just switch OFF/ON/OFF/ON...
                    status = FG_GREEN + "-- ON --" if self.debug else FG_RED + "-- OFF --"
                    print()
                    print("Pseudo-debug mode is now: " + status + RST_CLR  + " (this mode allows inspection of the temporary BAT scripts)")
                    force_fresh = True
                elif sub_ch == "_": # Ctrl+F2 (Scancode 95)
                    print()
                    self.save_state_f2(file_chooser=True)  # In this case, we will use the native GUI FileChooser
                    force_fresh = True
                elif sub_ch == "`": # Ctrl+F3 (Scancode 96)
                    print()
                    self.load_state_f3(file_chooser=True)  # In this case, we will use the native GUI FileChooser
                    force_fresh = True

                if sub_ch == "H": # Up
                    if self.history and self.history_index > 0:
                        self.history_index -= 1
                        buffer = self.history[self.history_index]
                        cursor_pos = len(buffer)
                elif sub_ch == "P": # Down
                    if self.history_index < len(self.history):
                        self.history_index += 1
                        if self.history_index < len(self.history):
                            buffer = self.history[self.history_index]
                        else:
                            buffer = ""
                        cursor_pos = len(buffer)
                elif sub_ch == "K": # Left
                    if cursor_pos > 0:
                        cursor_pos -= 1
                elif sub_ch == "M": # Right
                    if cursor_pos < len(buffer):
                        cursor_pos += 1
                elif sub_ch == "G": # Home
                    cursor_pos = 0
                elif sub_ch == "O": # End
                    cursor_pos = len(buffer)
                elif sub_ch == "S": # Del
                    if cursor_pos < len(buffer):
                        buffer = buffer[:cursor_pos] + buffer[cursor_pos + 1:]
                elif sub_ch == "I": # PgUp
                    if self.history:
                        self.history_index = 0
                        buffer = self.history[self.history_index]
                        cursor_pos = len(buffer)
                elif sub_ch == "Q": # PgDn
                    self.history_index = len(self.history)
                    buffer = ""
                    cursor_pos = 0
            else:
                # --- PRO-TIP UX: LIVE QUOTE REMOVAL ---
                # If the user types \ or / immediately after a closing quote, replace the quote with the slash
                if ch in ("\\", "/") and cursor_pos > 0 and buffer[cursor_pos - 1] == '"':
                    # Only remove if it is a closing quote (meaning we have an even number of quotes so far)
                    if buffer[:cursor_pos].count('"') % 2 == 0:
                        buffer = buffer[:cursor_pos - 1] + ch + buffer[cursor_pos:]
                        # We DO NOT increment cursor_pos here because we removed a char (") and added a char (\),
                        # so the cursor remains in the same absolute position.
                    else:
                        buffer = buffer[:cursor_pos] + ch + buffer[cursor_pos:]
                        cursor_pos += 1
                else:
                    buffer = buffer[:cursor_pos] + ch + buffer[cursor_pos:]
                    cursor_pos += 1

            draw_line(old_cursor_pos, buffer, cursor_pos, force_fresh)


    def _path_completer(self, text, only_dirs=False):
        text = text.strip('"')
        try:
            base_dir = self.current_dir
            partial = text

            if "\\" in text or "/" in text:
                candidate_path = os.path.join(self.current_dir, text)
                base_dir = os.path.dirname(candidate_path)
                if not base_dir:
                    base_dir = self.current_dir
                partial = os.path.basename(text)

            matches = []
            
            # SET com todos os caracteres que forçam o uso de aspas no CMD nativo para foldernames/filenames
#            cmd_special_chars = {' ', '+', '[', ']', '{', '}', '(', ')', '%', '!', '&', '|', '>', '<', '^', "'", "`", "´"}
            symbols_require_quotes_in_file_names = {' ', '&', '^' }
            
            for item in os.listdir(base_dir):
                full_path = os.path.join(base_dir, item)
                
                if not item.lower().startswith(partial.lower()):
                    continue
                    
                if only_dirs and not os.path.isdir(full_path):
                    continue
                    
                prefix = os.path.dirname(text)
                candidate = os.path.join(prefix, item) if prefix else item
                
                # NOVO: Verifica se o caminho construído possui algum dos caracteres especiais
                if any(char in candidate for char in symbols_require_quotes_in_file_names):
                    candidate = f'"{candidate}"'
                    
                matches.append(candidate)
                
            return sorted(matches)
        except Exception:
            return []


    # Function to check if the EXE/COM is GUI or CUI/console type
    def get_exe_subsystem(self, exe_path):
        """
        Returns the subsystem type of a PE executable.
        Returns:
        2 -> GUI
        3 -> Console (CUI)
        other value -> other subsystem
        None -> invalid file
        """
        try:
            with open(exe_path, "rb") as f:
                # DOS Signature
                if f.read(2) != b"MZ":
                    return None
                
                # PE header offset
                f.seek(0x3C)
                pe_offset = struct.unpack("<I", f.read(4))[0]
                
                # PE\0\0 Signature
                f.seek(pe_offset)
                if f.read(4) != b"PE\0\0":
                    return None
                
                # "Magic" field from the Optional Header
                f.seek(pe_offset + 24)
                magic = struct.unpack("<H", f.read(2))[0]
                
                if magic == 0x10B: # PE32
                    subsystem_offset = pe_offset + 24 + 68
                elif magic == 0x20B: # PE32+
                    subsystem_offset = pe_offset + 24 + 68
                else:
                    return None
                    
                f.seek(subsystem_offset)
                subsystem = struct.unpack("<H", f.read(2))[0]
                return subsystem
        except Exception:
            return None


    def split_typed_cmdline(self, cmdline):
        """
        Split a Windows CMD command line into SUBcommands, preserving the
        execution operators ('&', '&&', '|', '||') that MAY precede each command.
        SUBcomands are EACH part that are concatenated by the operators above.

        Returns:
            A tuple (commands, parens_balanced, quotes_balanced) where:
            - commands (list): A list of dictionaries containing:
                - 'operator' (str | None): The operator before the command
                - 'command' (str): The primary command/executable
                - 'args' (str): The remaining arguments as a single string
                - 'original text' (str): Full original text of the subcommand with arguments
                PS - Leading and trailing whitespace are trimmed from these three values as a result of the processing.
        """
        commands = []
        current = []
        in_quotes = False
        i = 0
        length = len(cmdline)
        
        current_op = ""
        paren_count = 0
        parens_balanced = True
        
        # Track where each subcommand block starts
        block_start = 0

        def _add_subcommand(subcommand_with_args, op, b_start, b_end):
            # 1. Get the raw, unmodified text directly from the original string
            raw_slice = cmdline[b_start:b_end]
            original_text = raw_slice.strip()
            
            # 2. Find the exact start index of the non-whitespace text
            start_idx = b_start
            if original_text:
                start_idx += raw_slice.find(original_text)

            subcommand_with_args = subcommand_with_args.strip()
            
            if not subcommand_with_args:
                if op:
                    commands.append({
                        "operator": op, "command": "", "args": "",
                        "start_index": start_idx, "original_text": original_text
                    })
                return

            # Detect '@<<command>>' and temporarily removes the '@'  -- Also accept '@ <<command>>'; This is how native CMD prompt behaves
            if subcommand_with_args.startswith('@'):
                subcommand_with_args = subcommand_with_args[1:].lstrip()
                if not subcommand_with_args:
                    if op:
                        commands.append({
                            "operator": op, "command": "@", "args": "",
                            "start_index": start_idx, "original_text": original_text
                        })
                    return

            match = re.match(r'^((?:"[^"]*"|\S)+)\s*(.*)', subcommand_with_args)
            if not match:
                return
                
            cmd_name = match.group(1)
            args_str = match.group(2)
            
            idx = -1
            in_q = False
            for j, char in enumerate(cmd_name):
                if char == '"':
                    in_q = not in_q
                elif not in_q and char in ('/', '<', '>'):
                    idx = j
                    break
                    
            if idx > 0:
                glued_part = cmd_name[idx:]
                cmd_name = cmd_name[:idx]
                args_str = f"{glued_part} {args_str}" if args_str else glued_part

            commands.append({
                "operator": op,
                "command": cmd_name.lower(),      # Let's lower it HERE to facilitate comparisons later
                "args": args_str,
                "start_index": start_idx, 
                "original_text": original_text 
            })
        #End_of_add_subcomand

        while i < length:
            c = cmdline[i]

            if c == '^' and not in_quotes:
                current.append(c)
                if i + 1 < length:
                    i += 1
                    current.append(cmdline[i])
                i += 1
                continue

            if c == '"':
                in_quotes = not in_quotes
                current.append(c)
                i += 1
                continue

            if in_quotes and c in ( '<', '>', '&', '|' ):
                # If the user command-line has these symbols INSIDE quotes, we MUST escape them, because the temporary 
                # BAT file uses CALL /C "execution_line" which means there will be one parsing at the parent CMD and 
                # other parsing at the child CMD /C. The escape allow the symbol to 'survive' those two passes.
                # This will correctly interpret command lines like this:
                #         findstr /C:"||" file.cmd
                #   and   echo "bla > ble"    and    echo "Hi^&d"
                # PS-When one of these symbols is  NOT inside a string and the user wants it to behave like a literal, 
                #    then THE USER is responsible  for typing  the escape caret IF that is what he wants ! 
                c = '^' + c  

            if not in_quotes and c in ('<', '>'):
                current.append(c)
                if i + 1 < length and cmdline[i + 1] == '>':
                    i += 1
                    current.append('>')
                if i + 1 < length and cmdline[i + 1] == '&':
                    i += 1
                    current.append('&')
                i += 1
                continue

            if not in_quotes and c in ('&', '|'):
                found_op = c
                op_len = 1
                if i + 1 < length and cmdline[i + 1] == c:
                    found_op = c + c
                    op_len = 2

                text = "".join(current).strip()
                _add_subcommand(text, current_op, block_start, i)
                
                current_op = found_op
                current = []
                
                i += op_len
                block_start = i  # Mark the start of the next block
                continue

            if not in_quotes and c in ('(', ')'):
                if c == '(':
                    paren_count += 1
                else:
                    paren_count -= 1
                    if paren_count < 0:
                        parens_balanced = False

                current.append(c)
                i += 1
                continue

            current.append(c)
            i += 1
        #End-while

        text = "".join(current).strip()
        _add_subcommand(text, current_op, block_start, length)

        if paren_count != 0:
            parens_balanced = False

        quotes_balanced = not in_quotes

        return commands, parens_balanced, quotes_balanced

    #End-of split_typed_cmdline()


    def _adjust_subcommand(self, subcommand):
            '''
            Adjust according to the type of each (sub)command.
            The complete path will be searchd For external programs or associated files, and this path
            will be used, instead of the single text.
            A 'call' will be prepended to BAT and CMD scripts, to ensure they do NOT hang/freeze the temporary BAT;
            Also for CUI programs, like 'python.exe', otherwise their interactivity is lost.
            And for GUI programs, a 'start' is prepended, to ensure they do NOT hang/freeze the temporary BAT.
            '''

            # Can happens if these symbols are mispplaced at the end of the line (detected as a last 'subcomand')
            if subcommand in "['&', '|', '&&', '||', '>', '>>', '<', '<<' ]":
                return subcommand
            
            flag_assoc_file= False
            flag_GUI_pgm= False
            flag_cui_pgm= False
            flag_ps1=False
            flag_cmd_bat=False
            flag_internal_command= False
            subcmd = None
            subcmd_path = None

            # -- LET's see if the received user 'command' is an  absolut or relative 'path' , and use shutil.which() on it:
            subcmd = subcommand.strip() # It was already lower() when inserted in the list
            subcmd_was_quoted = False
            #    Must REMOVE from the subcommand the eventual pair of trailing/leading quotes 
            #    because shutil.which() and os.path.exists() do NOT like them (can NOT find quoted stuff in the path)
            if len(subcmd) >= 2 and subcmd[0] in "'\"" and subcmd[0] == subcmd[-1]:
                subcmd = subcmd[1:-1]
                subcmd_was_quoted = True
                # The line below is to REVERT escapes eventually inserted in OTHER parts of the subcommand 
                # by _split_typed_cmdline(), because the shutils which() and path.exists() used below will NOT find 
                # in the PATH  foldernames/filenames escaped with '^'  
                # PS - do NOT remove insertion of '^' in that function, because they must be inserted in the args part, which is fine
                subcmd = subcmd.replace('^&', '&')  #<--  This reversion is TEMPORARY only, restored a few lines ahead
                subcmd = subcmd.replace("%cd%", self.current_dir) 
            else:  # subcommand was not inside quotes
                subcmd = subcmd.replace("%cd%", self.current_dir) 

            #--------------------------------------------------------------------------#
            #         IMPORTANT - About the search for the 'command' FULL path (part 1)                #
            #--------------------------------------------------------------------------#
            # In the following lines,  We try to get the 'command'/program/script FULL path.
            # WHY? (we could just NOT check at all and the call CMD/C used in the temp BAT would do this search). 
            # The problem is: if the program is an executable EXE that has Windows GUI, and we just 'call' it
            # from our temporary BAT file, then our PyWinCMD prompt will be blocked until the called GUI
            # program is finished (this happens with MS-Excel, MS-Word, Notepad etc.). That would NOT be  good !
            # So, we try to find ourselves the 'command' FULL path, to be able to check wether it's a GUI type. 
            # If it is, the program will be called using 'start' in the temp BAT, ensuring the call will NOT block. 
            #--------------------------------------------------------------------------#

            # Search directly for the 'command' folder/file , if an ABSOLUTE path was received
            if ( subcmd.startswith('\\') or  # <--- An absolute PATH was given, starting with '\'
                 (len(subcmd) > 2 and subcmd[1:3] == ':\\') ) : # <--- An absolute PATH was given, starting with Drive letter) 
                if os.path.exists(subcmd):
                    subcmd_path = subcmd

            # NOW, if not found yet, LET's search for the 'command' in the directories that are in the PATH variable 
            # (only extensions in PATHEXT are looked for,  to see what they are, call 'set PATH' in the command line )
            if not subcmd_path: #<<--- We received  either a  short name or a relative path in the 'command'
                curr_path=self.current_env.get('PATH', os.environ['PATH'])
                curr_path=self.current_dir + ";" + curr_path  #<<--- which() does NOT search in the current dir when the 'path' parameter is used, so we add it, to build a CMD-like behavior
                # the which() function returns ONLY one path, whichever has precedence in the PATH
                subcmd_path = shutil.which(subcmd, path=curr_path)
            #End-if

            # Not found yet? MAYBE the 'command' is just an 'associated' file name, with extensions like *.xlsx, *.docx, etc 
            # (such extensions are NOT in PATHEXT, so the previous search via shutil.which() would NOT have found them)
            if not subcmd_path:
                if os.path.exists(self.current_dir + os.sep + subcmd):  
                    subcmd_path = self.current_dir + os.sep + subcmd

            # If we definetely could NOT find the FULL path, then we consider it an INTERNAL COMMAND (e.g., DIR, ECHO, SET), 
            if not subcmd_path:
                flag_internal_command = True
                subcmd_path = subcmd

            #--------------------------------------------------------------------------#
            #         IMPORTANT - About the search for the 'command' FULL path (part 2)                #
            #--------------------------------------------------------------------------#
            #The search we did in the steps above works perfectly... EXCEPT in cases where the current 'command' is part 
            #  of a sequence of CONCATENATED commands and one of the previous commands executes 'CD', meaning it changes 
            #  the current directory DURING the execution of our temporary BAT file :( 
            # In this case, the search we did above in self.current_dir isn’t effective, because it looks in a directory 
            #  that is NO longer what we have in self.current_dir  (we can only update it at the END of the execution of 
            # CMD /C in the  temporary BAT,  not for each CONCATENATED subcommand). 
            # Q - What is the effect of this? 
            # A – In such cases, we will NOT be able to detect if a 'command' refers to a GUI program and it will be 
            # considered an INTERNAL command, meaning it will be called in the BAT without using 'start', which will 
            # cause our prompt to get 'stuck' until that GUI program is closed :( 
            # Besides, the 'freezing' may last for a while AFTER the GUI program ends, EVEN if we hit Ctrl+Break :(
            #--------
            # SO, to reduce impacts, we will always WARN the user whenever 'CD' is part of concatenated commands, and he 
            # can decide whether he wants to run the concatenated command line anyway, or run the 'CD' in a separate command line.
            #--------------------------------------------------------------------------#

            # At this point, any 'resolvable' extension would have been set in subcmd_path, just like the native CMD would do  
            else: # <-- The FULL path of the command/pgm/script/filename etc was found '

                p_lower = subcmd_path.lower()

                # MUST test every case:
                if p_lower.endswith('.ps1'):
                    flag_ps1 = True
                elif  p_lower.endswith( ('.bat', '.cmd',) ):
                    flag_cmd_bat = True
                elif  p_lower.endswith( ('.exe', '.com',) ):
                    IMAGE_SUBSYSTEM_WINDOWS_GUI = 2
                    IMAGE_SUBSYSTEM_WINDOWS_CUI = 3
                    if self.get_exe_subsystem(subcmd_path) == IMAGE_SUBSYSTEM_WINDOWS_GUI:  # GUI type / separate apps
                        # Note that GUI programs, like NOTEPAD, or EXCEL.EXE fall here
                        flag_GUI_pgm = True
                    else:  # It's an EXE/COM of type CUI: console program.... and it could be interactive
                        # Also interactive CUI programs like PYTHON.EXE fall here
                        flag_cui_pgm = True
                else: 
                    # If file EXISTS,  but has NON EXECUTABLE extensions, like *.DOCX, *.VBS, *.XLSX etc, then it may be associated with some PGM
                    flag_assoc_file = True 

            # If the 'command' has spaces in it, then we must surround it with quotes, otherwise it will fail in the temp BAT.
            # This can happen if the 'command' was expanded with the complete path (external programs or assoc-files) 
            # by the previous call to 'which' OR if the original command typed by the user was quoted path containing spaces
            subcmd_quotes_applyed = False
            # Note that there might be ANOTHER situation where we need to use quotes: when the 
            #  original subcommand was received in quotes EVEN without spaces -- This happens 
            #  when it's a file name with special characters, like '&', '(' and others.
            if " " in subcmd_path or subcmd_was_quoted: #<<-- The presence of quotation marks matters, regardless of whether there were spaces or not
               subcmd_quotes_applyed = True
               subcmd_path = f'\"{subcmd_path}\"'

            # Final adjustment of the subcommand path:
            if subcmd_quotes_applyed:
               subcmd_path = subcmd_path.replace('&', '^&') # Put a cmd escape code before '&', if found

            # --- IF it is a GUI program or a FOUND associated file (like XLSX or DOCX) then we MUST prepend a 'start'
            #     command otherwise the temporary BAT file will stay blocked waiting forever :(
            if flag_GUI_pgm or flag_assoc_file:
                adjusted_subcommand =  f'start "Temp" {subcmd_path} '  

            elif flag_cmd_bat:
                adjusted_subcommand = f'call {subcmd_path} ' 

            elif flag_ps1:
                adjusted_subcommand = f'powershell.exe -ExecutionPolicy Bypass -File {subcmd_path} ' 

            elif flag_cui_pgm: # It's an EXE or COM of type CUI: they are console programs.... and can be interactive
               # Any interactive CUI program like PYTHON.EXE falls here 
                adjusted_subcommand = f'{subcmd_path} '   #  'call' is not required
#                adjusted_subcommand = f'call {subcmd_path} '  

            else:  # flag_internal_command = True  will be handled here
                # Do NOT prepend 'call' here. 
                # Without 'call', command lines that use '(' ')' to separate commands will WORK fine !
                # Otherwise, blocks of commands using parentheses may raise errors. 
                adjusted_subcommand =  subcommand

            return adjusted_subcommand


    # =========================================================================
    # --- UNIFIED EXECUTION ENGINE ---
    # =========================================================================
    def _execute_cmd(self, user_cmdline):

        def looking_for_help(text: str) -> bool:
            """
            Auxiliary function to Check if the argument contains '/?' ignoring any whitespaces/tabs
            eventually existent before, between, or after these characters ('  /  ?' and '  /C  / ?' both return True )
            """
            pattern = r"/\s*\?"
            return bool(re.search(pattern, text))
        #End_def

        def doskey_macro_expansion(old_text: str) -> str:
            new_text = old_text
            parts = new_text.split(maxsplit=1)
            flag_found = False
            if parts:
                first_word = parts[0].lower() # Always lower the key in doskey dictionary
                if first_word in self.macros:
                    flag_found = True
                    macro_val = self.macros[first_word]
                    rest_of_args = parts[1] if len(parts) > 1 else ""
                    
                    # Native DOSKEY special characters substitutions
                    # We use (?i) in regex to be case-insensitive (e.g., accept $t or $T)
                    macro_val = re.sub(r'(?i)\$T', '&', macro_val)
                    macro_val = re.sub(r'(?i)\$G', '>', macro_val)
                    macro_val = re.sub(r'(?i)\$L', '<', macro_val)
                    macro_val = re.sub(r'(?i)\$B', '|', macro_val)

                    # Checks if there is any numerical argument marker ($1 to $9) or $*
                    has_args_marker = bool(re.search(r'\$(\*|[1-9])', macro_val))

                    if has_args_marker:
                        # Extracts the macro arguments keeping quoted blocks together
                        # Ex: 'arg1 "arg 2" arg3' becomes a list: ['arg1', '"arg 2"', 'arg3']
                        margs = re.findall(r'".*?"|\S+', rest_of_args)
                        
                        new_text = macro_val
                        
                        # Replaces $1 to $9
                        for i in range(1, 10):
                            arg_val = margs[i-1] if i <= len(margs) else ""
                            new_text = new_text.replace(f"${i}", arg_val)
                        
                        # Replaces $* with the entire rest of the original line
                        new_text = new_text.replace("$*", rest_of_args)
                    else:
                        # CMD default behavior: if there are no variables, 
                        # the typed arguments are just concatenated at the end
                        new_text = macro_val + (" " + rest_of_args if rest_of_args else "")

                    # Finally, replaces $$ with a literal $ (in case the user escaped it)
                    new_text = new_text.replace("$$", "$")
                
            return flag_found, new_text.strip()
        #End-def

        cmdline_clean = user_cmdline.strip()
        if not cmdline_clean:
            return False  # Nothing to do; user has just hit ENTER?  PS --> True would EXIT our emulator, it is the return of shell.onecmd()

        subcommands, parens_balanced, quotes_balanced = self.split_typed_cmdline(user_cmdline)

        # Must NOT allow this, because we use CMD /C to run, and it MAY change the command line behavior when 
        #  quotes are  unmatched (results could be different than running the command line in the native CMD prompt).
        # Side effects of not allowing: almost zero, because the native CMD prompt would also throws error messages
        #  in almots all such cases. It only allows weird ECHO subcommands with unbalanced quotes.
        if not quotes_balanced: 
            print(FG_RED + "ERROR: Unbalanced quotes in the command line" + RST_CLR) 
            print("Canceled! Please correct the input and try again."); return False

        if not parens_balanced:   # <--User decides, because Folder/File ENAMES are ALLOWED to have unbalanced "(" and ")" in the name, as well as echo 
            print(FG_YELLOW + "WARNING: Unbalanced parentheses in the command line" + RST_CLR) 
            print ("  IF it occurs in foldernames/filenames or in echo arguments, you can proceed.")
            try:
                resp = input("  Proceed executing the command line (Y/N)? " )
            except:
                resp = 'N'
            if resp.upper().startswith('Y'):
                print("  Trying to execute... if no result displayed, indicates unbalance was fatal/nothing executed")
            else: 
                print("  Canceled!"); return False

        if len(subcommands) > 1: # The command line has concatenated subcommands 

            complex_subcommands_found = [c['command'] for c in subcommands if c.get("command") in self.set_of_complex_subcommands]
            # PS -unlike those in the above set, the 'EXIT' subcommand is ALLOWED to run concatenated, it is not checked here 

            # Noe that the 'text of the 'command' stored is already in lower case
            if 'doskey' in complex_subcommands_found:
                print(FG_RED + f"ERROR - Can NOT run 'doskey' concatenated with other commands" + RST_CLR)
                print("Canceled! - Please try again, using 'doskey' in its own command line")
                return False

            if 'cd' in complex_subcommands_found or 'pushd' in complex_subcommands_found or 'chdir' in complex_subcommands_found:
                print(FG_YELLOW + "WARNING: There is a 'CD' or 'PUSHD' subcommand in the concatenated command line" + RST_CLR) 
                print ("  If any concatenated subcommand that follows 'CD'/'PUSHD' executes a GUI program, this prompt will 'freeze'")
                print ("  In such cases, it is HIGHTLY advisable to execute 'CD'/'PUSHD' in its own cmdline.")
                try:
                    resp = input("  Proceed executing the command line (Y/N)? ")
                except:
                    resp = 'N'
                if resp.upper().startswith('Y'):
                    print("  Executing... if the prompt 'freezes' after you close the GUI program, hit Ctrl+Break and WAIT a few seconds")
                else: 
                    print("  Canceled!"); return False

        # Intercept some commands, like DOSKEY and EXIT
        #  but ONLY if they are the ONLY command in the command line (no other commands concatenated)
        if len(subcommands) == 1:

            cmd_lower = subcommands[0]['command'].lower()
            args = subcommands[0]['args']
            args_lower = args.lower()

            # --- DOSKEY INTERCEPTION AND DEFINITION ---
            if cmd_lower == "doskey":
               
                if looking_for_help(args):
                    print(r"""
This command allows you to create, edit, export, and import macros, as well as list the command history.
DOSKEY [/MACROS] [/MACROFILE=file] [macro_name=[text]]
    macro_name:    Specifies the name of the macro to be created or edited
    text      :    Specifies the command(s) you want to associate with the macro
    /MACROS   :    Displays all macros
    /MACROFILE=file: Imports macros previously exported to the file (to export, see examples below)
    /HISTORY  :    Lists the entire command history (navigate with Up/Dw and PgUp/PgDw arrows)
    /REINSTALL:    Clears/Resets all macros and ALSO the entire command history.

The following special characters can be used in Doskey macro definitions.
They will be replaced by other symbols or texts, according to the table below:
    Special code    Description
    $G or $g        Will be replaced by the output redirector ('>').
    $G$G or $g$g    Will be replaced by the append mode output redirector ('>>')
    $L or $l        Will be replaced by the input redirector ('<').
    $B or $b        Will be replaced by the 'pipe' symbol, which makes the output of one command the input of another ('|').
    $T or $t        Will be replaced by the command concatenation symbol ('&').
    $$              Escape code for the '$' character, in case it needs to appear within the macro ('$').
    $1 to $9        Will be replaced by each parameter typed at runtime. $1 is equivalent to %1, etc.
    $* Will be replaced at runtime by all text following the macro name.

Example that simulates the '&&' operator (execute second concatenated command only if the first succeeds):
    DOSKEY compile=build.bat $T IF NOT ERRORLEVEL 1 deploy.bat 
Example that simulates the '||' operator (execute second concatenated command only if the first fails):
    DOSKEY test=test.bat $T IF ERRORLEVEL 1 echo Failed! $T something_else.bat
Other Examples:
______ Macro definition ____________________________ Typed ___________________ Executed _____________________________
▌   DOSKEY ls=dir $*                            ▌ ls \users\john        ====>>  dir \users\john                     ▐
▌   DOSKEY cdw=cd $1 $T dir/w $1                ▌ cdw \temp *.bat       ====>>  cd \temp & dir /w *.bat             ▐
▌   DOSKEY mcd=md $1 $T cd $1                   ▌ mcd logs              ====>>  md logs & cd logs                   ▐
▌   DOSKEY dirfi=dir $1 /b $B findstr /I $2     ▌ dirfi logs "error"    ====>>  dir logs /b & findstr /I "error"    ▐
▌   DOSKEY sd=systeminfo $G sysinfo.txt         ▌ sd                    ====>>  systeminfo > sysinfo.txt            ▐
▌   DOSKEY cat=type $*                          ▌ cat ..\bla.log        ====>>  type ..\bla.log                     ▐
▌   DOSKEY catfi=type $1 $B find /I $2          ▌ catfi test.ps1 "write"  ====>>  type test.ps1 | find /I "write"   ▐
______ Typed ______________________________________ Result __________________________________________________________  
▌   DOSKEY cat=                                 ▌ Deletes the 'cat' macro, if it was previously defined.            ▐ 
▌   DOSKEY /MACROS                              ▌ Shows a list of all defined macros                                ▐ 
▌   DOSKEY /HISTORY                             ▌ Shows a list of all commands already executed                     ▐ 
▌   DOSKEY /REINSTALL                           ▌ Resets/clears all macros and ALSO the command history             ▐
▌   DOSKEY /macros > my_macros.txt              ▌ Exports current macros to the file 'my_macros.txt'                ▐ 
▌   DOSKEY /macrofile=my_macros.txt             ▌ Imports macros from the specified file (appends or replaces them) ▐ 
_____________________________________________________________________________________________________________________
    """)      
                if args_lower == "" or  args_lower.startswith("/macros"):
                    remainder = args[7:].strip()
                    
                    # 1. If it's just "/macros" without redirection, display on screen
                    if not remainder:
                        for key, value in self.macros.items():
                            print(f"{key}={value}")
                        return False
                    
                    # 2. If there is redirection (> or >>), intercept and write to the file
                    elif remainder.startswith(">"):
                        is_append = remainder.startswith(">>")
                        
                        # Extracts the file path by removing the '>' symbols and spaces
                        filepath = remainder[2:].strip() if is_append else remainder[1:].strip()
                        
                        # Removes quotes if the user typed a path with spaces
                        if filepath.startswith('"') and filepath.endswith('"'):
                            filepath = filepath[1:-1]
                            
                        # Resolves the relative path based on the emulator's current directory
                        if not os.path.isabs(filepath):
                            filepath = os.path.join(self.current_dir, filepath)
                            
                        mode = 'a' if is_append else 'w'
                        
                        try:
                            # Saves the file using the environment's current code page
                            with open(filepath, mode, encoding=f'cp{self.current_codepage}', errors='ignore') as f:
                                if len(self.macros) == 0:
                                    f.write('\n') # if no macros, MUST write something, just like native doskey would do
                                else:
                                    for key, value in self.macros.items():
                                        f.write(f"{key}={value}\n")
                        except Exception as e:
                            print(FG_RED + f"Error exporting macros file: {e}" + RST_CLR)
                            
                        return False
                    else:
                        return False # Found unrecognized text after /macros
                    
                elif args_lower.startswith("/macrofile=") or args_lower.startswith("/macrofile ="):
                    filepath = args[10:].strip().removeprefix("=").strip()
                    
                    # Removes quotes in case the user typed paths with spaces
                    if filepath.startswith('"') and filepath.endswith('"'):
                        filepath = filepath[1:-1]
                    
                    # Resolves the relative path based on the emulator's current directory
                    if not os.path.isabs(filepath):
                        filepath = os.path.join(self.current_dir, filepath)
                    
                    try:
                        # Opens the file using the environment's current code page
                        with open(filepath, 'r', encoding=f'cp{self.current_codepage}', errors='ignore') as f:
                            for line in f:
                                line = line.strip()
                                # Ignores empty lines or common comments
                                if not line or line.startswith(';') or line.startswith('#'):
                                    continue
                                
                                if '=' in line:
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip()
                                    if not value:
                                        self.macros.pop(key, None)
                                    else:
                                        self.macros[key] = value
                    except Exception as e:
                        print(FG_RED + f"Error processing macros file: {e}" + RST_CLR)
                    
                    return False
                # --- Handling of /REINSTALL, which is equivalent to a 'reset' ---
                elif args_lower == "/reinstall":
                    self.macros.clear()      # The default behavior of native DOSKEY is to reset 
                    self.history.clear()     # both macros and the command history !
                    self.history_index = 0
                    # If the Windows environment is using pyreadline under the hood, 
                    # we clear it too for visual safety on the keyboard arrows.
                    try:
                        import readline
                        readline.clear_history()
                    except Exception:
                        pass
                    return False

                # --- Handling of /HISTORY, to list history (with redirection support) ---
                elif args_lower.startswith("/history"):
                    remainder = args[8:].strip()
                    
                    # 1. Without redirection: print on screen
                    if not remainder:
                        print("--- Command history (navigate with Up/Dw and PgUp/PgDn arrows) ---")
                        for cmd_line in self.history:
                            print(cmd_line)
                        return False
                    
                    # 2. With redirection (> or >>)
                    elif remainder.startswith(">"):
                        is_append = remainder.startswith(">>")
                        filepath = remainder[2:].strip() if is_append else remainder[1:].strip()
                        
                        if filepath.startswith('"') and filepath.endswith('"'):
                            filepath = filepath[1:-1]
                            
                        if not os.path.isabs(filepath):
                            filepath = os.path.join(self.current_dir, filepath)
                            
                        mode = 'a' if is_append else 'w'
                        try:
                            with open(filepath, mode, encoding=f'cp{self.current_codepage}', errors='ignore') as f:
                                for cmd_line in self.history:
                                    f.write(f"{cmd_line}\n")
                        except Exception as e:
                            print(FG_RED + f"Error exporting history: {e}" + RST_CLR)
                        return False
                    else:
                        return False
                
                elif "=" in args:
                    key, value = args.split("=", 1)
                    key = key.strip().lower()  #Always lower the key in macros dictionary
                    value = value.strip()
                    if not value:
                        self.macros.pop(key, None) # Removes the macro
                    else:
                        self.macros[key] = value
                    return False
                    
                else:
                    return False # Empty or invalid doskey call

            # Interception: EXIT
            if cmd_lower == "exit" and not looking_for_help(args):
                opt = input("Closing emulator session... Do you want to Save the environment state (Y/N)? ")
                if opt.lower().startswith("y"):
                    self.save_state_f2()            
                return True  #<<--- this will become the return of shell.onecmd() <-- True is the indication to call sys.exit() in main()

            # Interception: TITLE
            if cmd_lower == "title" and not looking_for_help(args):
                args = cmdline_clean[5:].strip()
                self.title = args
                # Proceed with the execution, do NOT return yet

            # Interception: START (Open new PyWinCmd window)
            is_start_base = cmd_lower == "start" and args=="" and not looking_for_help(args) 
                    
            # IN CASE it's just 'START' without parameters, we start a new window of OUR PyWinCMD command prompt        
            if is_start_base:
    #           state_data = {"dir": self.current_dir, "env": self.current_env, "drives": self.drive_dirs, "macros": self.macros}
                state_data = {"dir": self.current_dir, "env": self.current_env, "drives": self.drive_dirs}  
                # We DO NOT pass the Command History state nor the doskey macros to the new 
                # environment, as this is exactly how the native CMD behaves (tested)
                b64_state = base64.b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')
                python_exe = sys.executable
                script_path = os.path.abspath(sys.argv[0])
                
                # ATTENTION - the b64_state CANNOT be LARGER than 8k in size, see: https://learn.microsoft.com/en-us/troubleshoot/windows-client/shell-experience/command-line-string-limitation
                # Anyway, it's hard to reach that limit, because the LARGEST state would be the Command History and we DO NOT send it  :)
                new_window_command = f'start "" /d "{self.current_dir}"  "{python_exe}" "{script_path}" --spawn-state {b64_state}'
                os.system(new_window_command)
                self.last_errorlevel = "0"
                return False  # <<-- This will become the return value for shell.onecmd();  True would indicate to call sys.exit() in main() 

            # IN CASE it's the 'START' command followed by some program/command/parameter, 
            # it will be handled and executed by the code below.
            # This even allows opening a native CMD window via 'START cmd', IF no restrictions/policies   

        #End-If len(subcommands)==1

        # ----- ADJUST every SUBcommand in the command line -----
        #So, we have at least one subcommand and args to process OR we have a bunch of these, concatenated by '&', '&&'. '|' or '||'
        execution_line = user_cmdline.strip()

        # Iterate backwards through all the SUBcommands and args, so string modification doesn't ruin earlier indices
        for cmd in reversed(subcommands):
            start = cmd["start_index"]
            command = cmd["command"]
            original_text = cmd["original_text"]
            maybe_escaped_text = f'{cmd["command"]} {cmd["args"]}'  # args MAY have been escaped with '^', if it has special symbols

            # Expand from doskey macros, if the SUBcommand is an entry there
            # PS - The NATIVE Windows CMD, DOSKEY macros have a strict limitation: 
            #      they are only expanded if they are the very first word on the command line.
            #      HERE we overcome that limitation and expand it EVEN for concatenated subcommands :)
            is_doskey_macro, maybe_escaped_new_text = doskey_macro_expansion(maybe_escaped_text)

            if is_doskey_macro:
                execution_line = execution_line[:start] + execution_line[start:].replace(original_text, maybe_escaped_new_text, 1)
                # TO-DO: if the new_text has concatenated external pgm/scripts, submmit each of them to _adjust_subcommand() 
                #        PS - Not a priority, let's assume most of the users will use only common CMD commands in macros.
            else:
                #  Adjust the text of the command (necessary in same cases, conditions are checked inside the method below)
                adjusted_command = self._adjust_subcommand(command)
                maybe_escaped_new_text = f'{adjusted_command} {cmd["args"]}'  # args MAY have been escaped with '^', if it has special symbols

                # Safe replacement: slice the string at the start index, and replace ONLY 
                # the first occurrence of the original text in the remaining slice.
                execution_line = execution_line[:start] + execution_line[start:].replace(original_text, maybe_escaped_new_text, 1)

        if execution_line[-1] in ( '<', '>', '&', '|', '^' ):   # native CMD would throw error, BUT we can NOT allow it, because we are going to append a ' & call' command after this content
            print(FG_RED + "ERROR: Special symbol at the end of the command line." + RST_CLR) 
            print("Canceled! -  Please correct the input and try again.")
            return False # Does NOT execute the line (but it will remain in the prompt)

        # --- MAIN EXECUTION block -- envelops the execution line in a temporary BAT file to be executed ---
        ERR_MARKER = "PWC_ERR_CAPTURE"
        DIR_MARKER = "PWC_DIR_CAPTURE"
        DRIVES_MARKER = "PWC_DRIVES_CAPTURE"
        CHCP_MARKER = "PWC_CHCP_CAPTURE"
        ENV_MARKER = "PWC_ENV_CAPTURE"

        timestamp = int(time.time() * 1000)
        bat_part1_path = os.path.join(os.environ.get('TEMP', '.'), f'pywincmd_part1_{timestamp}.bat')
        out_path = os.path.join(os.environ.get('TEMP', '.'), f'pywincmd_out_{timestamp}.txt')
        err_path = os.path.join(os.environ.get('TEMP', '.'), f'pywincmd_errorlevel_{timestamp}.txt')
        bat_part2_path = os.path.join(os.environ.get('TEMP', '.'), f'pywincmd_part2_{timestamp}.bat')

        # IMPORTANT1 - Need this to insert the last errorlevel value in the new CMD /C session, and also,
        #  to obtain the new last errorlevel (and other state variables) that results from the command line execution.
        # PS - It's safer to adjust the previous errorlevel this way, otherwise strange things can happen in the substition.
        # PS2- And... this is exactly the behavior of the native CMD do when executing a script: it substitutes the text  %errorlevel% 
        #      by the value it has on the moment the script is 'called'/run (--NOT-- with the errorlevel of each previous command in the script )      
        tweaked_cmdline=re.sub(re.escape("%errorlevel%"), self.last_errorlevel , execution_line , flags=re.IGNORECASE)
        tweaked_cmdline = f'set "errorlevel=" & cmd /c "exit {self.last_errorlevel}" & {tweaked_cmdline.strip()} & call "{bat_part2_path}"'  
        # IMPORTANT2 - Note that we also insert a 'set errorlevel=' before the command line. 
        #              This is NOT to reset the VALUE of %errorlevel%. It is a precaution to avoid a weird effect if the user inadvertently
        #              enters a command that set a USER variable called 'errorlevel': It would take precedence when resolving '%errorlevel%' 
        #              This is an odd behavior of Windows CMD that we are trying to mitigate here.  
        #              So, 'set errorlevel=' just DELETE any eventual user variable with that NAME, restoring the capacity of %errorlevel%.
        #              AND the command that sets the VALUE of the PREVIOUS execution errorlevel is cmd /c "exit {self.last_errorlevel}".

        # Line below builds the commands to restore the path on each DRIVE mounted
        drive_restorations = "\n".join([f'cd "{path}"' for path in self.drive_dirs.values()])

        bat_part1_content = f"""
@echo off

@REM This script is ALWAYS written and read with UTF-8 encoding by pywincmd.py
@REM So, the  UTF-8 codepage MUST be active throughout the execution of this script, EXCEPT before executing the 'execution_line'; 
@REM This is to ensure that any NON-ASCII chars present in the drives/folders path are not affected by differents CHCP  
chcp 65001 >nul

@REM restore drives and self.current_dir (THESE can have NON-ASCII characters, hence UTF-8 was previously ativacted ):
{drive_restorations}
cd /d "{self.current_dir}"

@REM Below is the 'command' just typed by the user:  
@rem {cmdline_clean}

@REM And here is the adjusted 'execution line' that will be executed:
@REM (we had to make an ajustment to correctly mimic the usage of % errorlevel %, and to concatenate the 'call' to the BAT that saves the state after the execution)
@rem = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
@rem "{tweaked_cmdline}" 
@rem = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 

@REM ONLY AT THIS POINT restore CHCP eventually set in the previous execution (immediatelly before calling the new command line):
chcp {self.current_codepage} >nul

@REM restore errorlevel from the PREVIOUS execution of this BAT (only here, just BEFORE the command line is executed):
:: cmd /c "exit {self.last_errorlevel}"  # THIS line is now disabled: already inserted this at the begining of the tweaked_cmdline

@REM Note that the 'tweaked_exec line' was set in % PWC_TWEAKED_CMDLINE % env var  by pywincmd just before calling this BAT (visible in that session only)
@REM An env var is used to hold the command line because an env-var is  ENCODING AGNOSTIC  (works in any codepage) !
@REM This is required, otherwise the execution_line COULD be misinterpreted if CHCP was called in a previous execution line 
@REM and the current execution line (got from our console) has NON-ASCII characters (Common in latin files/folders names )
@REM
@REM Unfortunatelly the ONLY way to correctly expand env-vars in the command line is using CMD /C (better NOT try to replace it)
@REM  but it has a side effect:  there is NO simple way to get the new STATE after the execution (the STATE = errorlevel 
@REM  as well as other variables and information eventually modified in that CMD session).
@REM  That's why we tweaked the original execution_line and ADDED a command to call ANOTHER BAT that save the sate in a file.
cmd /c  "%PWC_TWEAKED_CMDLINE%" 
        """

        # This is the BAT that saves the new STATE after the execution of the command line
        bat_part2_content = f"""
@echo off
@REM This script will be CALLed by the  cmd /c  "%PWC_TWEAKED_CMDLINE%"  that exists in the first script BAT
@REM  PS - A final SUBcommand was added to the original execution_line to do that :)
@REM This script will save the errorlevel that the calling CMD/C  had at the moment of the call
@REM  and save many other state variables from that session too... because this called script is in the SAME session.

@REM The FIRST thing to do is to save the errorlevel from the caller BAT script
@REM PS - The below 'set' MUST be in (this) separate BAT script !! <<---------------------- <<---------------------- IMPORTANT
@REM      And it MUST be called by the command line itself, that's why we injected the call in the tweaked_cmdline
set PWC_ERROR_LEVEL=%errorlevel%

@REM Preserve in env var the NEW chcp EVENTUALLY modified by the command line just executed by the first script
FOR /F "tokens=2 delims=:" %%A IN ('chcp') DO SET NEW_CHCP=%%A

@REM Now restore the UTF-8 codepage again, because the MARKERS below MUST be saved in the TMP output file ALWAYS with that encoding
chcp 65001 >nul

(
echo {ERR_MARKER} 
echo %PWC_ERROR_LEVEL%
echo {DIR_MARKER}
cd
echo {DRIVES_MARKER}
for %%d in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist %%d:\\ (
        echo =%%d=
        cd %%d:
    )
)
echo {CHCP_MARKER}
echo %NEW_CHCP%
echo {ENV_MARKER}
set
) > "{out_path}"
chcp %NEW_CHCP% > nul
        """ 

        with open(bat_part1_path, 'w', encoding='utf-8', errors='ignore') as f: #  'utf-8' is mandatory here
            f.write(bat_part1_content)

        with open(bat_part2_path, 'w', encoding='utf-8', errors='ignore') as f: #  'utf-8' is mandatory here 
            f.write(bat_part2_content)

        if self.debug:
            print(f'The temporary BAT files where generated and you may inspect them now !')
            print(f'    {bat_part1_path}\n    {bat_part2_path}')
            try:
                input("Hit ENTER when you are ready to continue the execution of the command line ")
            except:  # If user hits Ctrl+Break during the input() execution
                pass

        # Now, saves the execution line as an ENV VARIABLE, because they are ENCODING AGNOSTIC  (works in any codepage) !
        # This is required, otherwise the execution_line COULD be misinterpreted if CHCP was called in a previous execution line 
        # and the current execution line has NON-ASCII characters (Common in latin files/folders names )
        self.current_env["PWC_TWEAKED_CMDLINE"] = tweaked_cmdline #<-- this will be visible to the temp BAT, and well interpreted, regarding the active codepage

        # We are updating OUR python-console environment with the last command resultant environment that was stored, 
        # so that it will be inheritec by the NEW and clean process that we are going to start (see below)
        # (Maybe we could just set the'env' parameter as self.current_env ?  TO-DO: test effect on user-typed NON-Ascii text  )
        # (Note: changes made in the environment by the executed command line do NOT reflect back )
        old_environ = dict(os.environ)
        os.environ.clear()
        os.environ.update(self.current_env)
            
        try:
            # ############################   HERE IS THE 'MAGIC'   #############################
            # subprocess.run() inherits the current console natively, supporting any interaction,
            # unlike a subprocess.Popen(). This allows us to run programs 'inside' the console where 
            # this *.py is running. All inputs and outputs of the executed program are done in the 
            # same 'command prompt', until the called program is finished.  After that, our simulated
            # 'prompt' reappears again. 
            # It even allows running another 'python' interactively inside our prompt window!
            if self.verbosity:
                print(FG_LGRAY + f' ~~~~~~~~~~~~  Executing adjusted cmdline via temporary BAT script  ~~~~~~~~~~~~ \nCMD /C " {tweaked_cmdline} " ' + RST_CLR) 
            subprocess.run(f'cmd /c "{bat_part1_path}"', 
                        cwd=self.current_dir, 
                        )
            # Note: bath_path2 is called FROM bat_path1 to save the STATE after the command line is executed

        except KeyboardInterrupt:
            print(FG_YELLOW + "\n[PWC] Temporary BAT process interrupted by the user. Moving on..." + RST_CLR)

        os.environ.clear()
        os.environ.update(old_environ)

        # --- ENVIRONMENT STATE SYNCHRONIZATION ---
        # Must ALWAYS update the state with the eventual modifications made by the command/program that just finished
        # (it is necessary even when the first token of the command line executed was a GUI or CUI program, because 
        #  there MAY BE other tokens/commands concatenated by '&' that could change STATE, and we are NOT checking that)
        if os.path.exists(out_path):
            try:
                with open(out_path, 'r', encoding='utf-8', errors='ignore') as f:  #  'utf-8' is mandatory here
                    text_output = f.read()
                
                if ERR_MARKER in text_output:
                    _, state_part = text_output.split(ERR_MARKER, 1)
                    err_part, resto1 = state_part.split(DIR_MARKER, 1)
                    dir_part, resto2 = resto1.split(DRIVES_MARKER, 1)
                    drives_part, resto3 = resto2.split(CHCP_MARKER, 1)
                    chcp_part, env_part = resto3.split(ENV_MARKER, 1)

                    self.last_errorlevel = err_part.strip().split('\n')[0].strip().replace('\r', '')
                    if self.verbosity:
                        print(FG_LGRAY + f" ~~~~~~~~~~~~  Current errorlevel: {self.last_errorlevel} (Note that some CMD commands do NOT update this value)  ~~~~~~~~~~~~ " + RST_CLR)
                    self.current_dir = dir_part.strip().split('\n')[0].strip().replace('\r', '')

                    # Reads the states of each drive and updates the dictionary
                    self.drive_dirs.clear()
                    current_drive_letter = None
                    for line in drives_part.replace('\r', '').split('\n'):
                        line = line.strip()
                        if not line: continue
                        if re.match(r'^=[A-Z]=$', line):
                            current_drive_letter = line[1]
                        elif current_drive_letter:
                            self.drive_dirs[current_drive_letter] = line
                            current_drive_letter = None

                    cp_match = re.search(r'\d+', chcp_part)
                    if cp_match: self.current_codepage = cp_match.group()
                    # TO-DO: Decide if we would apply the current_codepage to the REAL console of this python session
                    #        We could do that via another subprocess.run(f'\windows\system32\chcp.com {self.current_codepage}}')
                    #        PS - Doing that will NOT have effect on the FILE input/output, only console I/O made BY THIS PYTHON would be affected.

                    new_env = {}
                    clean_env_part = env_part.replace('\r', '')
                    for line in clean_env_part.split('\n'):
                        line = line.strip()
                        if '=' in line:
                            if any(m in line for m in [DIR_MARKER, ENV_MARKER, CHCP_MARKER, ERR_MARKER]): continue
                            k, v = line.split('=', 1)
                            k_upper = k.strip().upper()
                            if k_upper: new_env[k_upper] = v.strip()
                    
                    if new_env: 
                        self.current_env = new_env
                        if 'PROMPT' not in self.current_env: self.current_env['PROMPT'] = "$P$G"
            except Exception:
                pass

        # Silent cleanup
        try:
            for p in [bat_part1_path, bat_part2_path, out_path ]:
                os.remove(p)
        except: pass

        self.update_prompt_visual()
        return False  #<<--- This will become the return value from shell.onecmd() -- True would indicate we want to EXIT


    def do_help(self, arg):
        """
        Called when user types 'help xxxxxx'.
        This function overrides the default help of cmd.Cmd module and  passes the command to the native Windows CMD help.
        """
        klarg = arg.strip().lower()
        if klarg.startswith('doskey'):   # The user typed 'HELP doskey or HELP doskeyxxxx yyyy zzzz, whathever, consider a call for Help on DOSKEY
            command = 'DOSKEY /?'
        else:
            command = f"HELP {arg}".strip()
        
        # Passes it to our command execution engine
        if self._execute_cmd(command):
            return True

    def default(self, line):
        if not line.strip(): return
        if self._execute_cmd(line):
            return True

    def emptyline(self):
        pass
#End-of-class



def main():
    # Enables support for native ANSI codes in Windows 10/11 console
    os.system('')

    import signal
    def ctrl_break_handler(signum, frame):
        """Function automatically called when Ctrl+Break is pressed.
            Note that Ctrl+Break IS NOT the same as Ctrl+C, the 1st is SIGBREAK and the 2nd is SIGABRT  <<=======
        """
#        print("\n[!] Ctrl+Break detected! But we won't do ANYTHING :)   ")
        return
    
    # Registers the SIGBREAK signal; 
    # prevents Ctrl+Break eventually typed in an interactive program from terminating THIS program/prompt
    signal.signal(signal.SIGBREAK, ctrl_break_handler)

    inherited_title = None    
    inherited_dir = None
    inherited_env = None
    inherited_drives = None
    inherited_macros = None
    
    if "--spawn-state" in sys.argv:
        try:
            idx = sys.argv.index("--spawn-state") + 1
            raw_state = sys.argv[idx]
            decoded_state = json.loads(base64.b64decode(raw_state.encode('utf-8')).decode('utf-8'))
            inherited_title = decoded_state.get("title")
            inherited_dir = decoded_state.get("dir")
            inherited_env = decoded_state.get("env")
            inherited_drives = decoded_state.get("drives")
            inherited_macros = decoded_state.get("macros")
        except Exception:
            pass

    shell=None
    try:
        shell = PyEmulatedCMD(
            inherited_title = inherited_title,
            inherited_dir=inherited_dir, 
            inherited_env=inherited_env,
            inherited_drives=inherited_drives,
            inherited_macros=inherited_macros
        )
    except Exception as e:
        print(e)
        print("Error initializing PyEmulatedCMD() class... Exiting.")
        sys.exit(1)

    #shell.load_state_f3(file_chooser=True)  # Uncomment if you want to debug 'F' keys under VSCode

    while True: 
        try:
            sys.stdout.write(shell.prompt)
            sys.stdout.flush()

            line = shell.readline_with_tab()
            if not line.strip(): continue

            flag_exit = shell.onecmd(line)
            if flag_exit: sys.exit(0)  # Normal exit, by EXIT command

        except KeyboardInterrupt:  # <-- raised by readline_with_tab(), when Ctrl+C is detected 
            pass # A message was already shown when keys were checked, in readline_with_tab()
        except EOFError:  # Ctrl+C during the python input() function call is caught here !
            sys.exit(2)
        except Exception as e:
            print(f"{FG_RED}Unexpected ERROR during PyWinCmd execution:")
            print(f"{FG_PURPLE}{e}{RST_CLR}")
            continue


if __name__ == '__main__':
    main()


