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

__version__ = "1.0.1"

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
              "It's useful when access to the native prompt is restricted. " 
              "The environment state is preserved throughout the execution of commands (directories, variables, doskey macros, codepage)."
              )
        print(r"""
Navigation Keys and Shortcuts:
  [ F1 ]           : Displays this help screen
  [ F2 or Ctrl+F2] : Saves the current environment state to a JSON file  (if CTRL+F2, opens a visual FileChooser)
  [ F3 or Ctrl+F3] : Restores the previously saved environment state  (if CTRL+F3, opens a visual FileChooser)
  [ F4 ]           : Shows the current state of this PyWinCmd command session
  [ ↑ ] and [ ↓ ]  : Navigates through previously executed commands (History)
  [ TAB ]          : Auto-completes file and folder when typing in the command line -- also during F2 and F3
                     Note: Use TAB repeatedly to cycle through autocomplete options (if more than one)
  [ ESC ]          : Clears the entire command line being typed
  [ Ctrl+, ]       : Opens the 'Windows Terminal' settings window, if available

All 'CMD' commands can be executed. Type HELP to list them.
Note: SETLOCAL, PUSHD, and COLOR executed in PyWinCmd prompt do NOT persist (They work normally inside a BAT/CMD).
For help on a specific 'CMD' command, type <<command>> /? or HELP <<command>> 
  - Examples:  COPY /?   or   help COPY
  
To execute a script file such as BAT, CMD, or PS1, simply type its name and press ENTER.
It is also possible to run any program from the PyWinCmd prompt, including interactive programs like 'python'. 
You can even activate virtual environments (virtualenv) with different Python versions and execute it. 

Advanced Feature - DOSKEY:
  PyWinCmd supports the use of DOSKEY for creating macros/aliases.
  - Example of macro creation:  DOSKEY cat=type $*   Another example: doskey catfi=type $1 $B find /I $2
  - For help on creating and managing macros:  DOSKEY /?  or  HELP DOSKEY
  """
)


    def select_from_native_file_chooser(self, filtro=None, tipo="load"):
        timestamp = int(time.time() * 1000)
        pwc_var   = "PWC_VAR_"+ str(timestamp)
        bat_path = os.path.join(os.environ.get('TEMP', '.'), f'pywincmd_temp_{timestamp}.bat')
        out_path = os.path.join(os.environ.get('TEMP', '.'), f'pywincmd_{pwc_var}.tmp')
        vnada = "###Nothing##Set##Yet###"

        filtro = "Supported file types (*.txt;*.json)|*.txt;*.json|Text Files (*.txt)|*.txt|Jason Documents (*.json)|*.json"

        if tipo.lower()=="save":
            mensagem = "Set the file name to save in the opened file selection dialog/window..."
            ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.SaveFileDialog; $f.InitialDirectory = $PWD.Path; $f.Title = 'Save environment state'; $f.Filter = '{filtro}'; if($f.ShowDialog() -eq 'OK') {{$f.FileName }}"
        else:          # 'load'
            mensagem = "Select a file to load in the opened file selection dialog/window..."
            ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.OpenFileDialog; $f.InitialDirectory = $PWD.Path; $f.Title = 'Load saved state'; $f.Filter = '{filtro}'; if($f.ShowDialog() -eq 'OK') {{$f.FileName }}"

        bat_content = f"""@echo off
cd /d "{self.current_dir}"        
:: Prepares the command
set "PS_CMD={ps_cmd}"
:: Executes PowerShell, which shows the File-Chooser, then captures the result into the variable {pwc_var}
for /f "usebackq delims=" %%I in (`powershell -STA -NoProfile -Command "%PS_CMD%"`) do (
    set "{pwc_var}=%%I"
)
if defined {pwc_var} (
    echo %{pwc_var}% > {out_path}
) else (
    echo  {vnada} > {out_path}
)
"""

        with open(bat_path, 'w', encoding=f'cp{self.current_codepage}', errors='ignore') as f:
            f.write(bat_content)

        print(mensagem)

        try:
            subprocess.run(f'cmd.exe /c "{bat_path}"', cwd=self.current_dir) 
        except KeyboardInterrupt:  # IF Ctrl+C is pressed during batch execution
            print(FG_YELLOW + "\n[PWC] BAT process interrupted by the user. Moving on..." + RST_CLR)
            return None

        # Now we read the file where the BAT wrote the chosen file name
        selected = None
        if os.path.exists(out_path):
            try:
                with open(out_path, 'r', encoding=f'cp{self.current_codepage}', errors='ignore') as f:
                    selected = f.read().strip()
                if selected == vnada:  # if the user clicked the "Cancel" button in the FileChooser, it will read vnada
                    selected = None 
            except:
                pass   # selected remains None
        
        return selected



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
            if file_chooser:  # We will use the native Dialog to get the filepath
                filepath = self.select_from_native_file_chooser(tipo='save')
                if not filepath:  #<-- If selection was canceled inside the FileChooser
                    print(FG_YELLOW + "Operation canceled!" + RST_CLR)
                    return False
            else:             # We will use the command line to get the filepath
                prompt_str = "File to save [D = default 'state_pywincmd.json', start of name+TAB = autocomplete, ESC clears, C = cancel]:"
                while filepath is None:  # if empty ENTER or Ctrl+C was pressed while executing SET /p
                    filepath = self.get_user_input_from_native_CMD(prompt_str)

                if filepath.strip().upper() == "C":   # If C+ENTER was typed at the input, cancel the saving
                    print(FG_YELLOW + "Operation canceled by user" + RST_CLR)
                    return False
                elif  filepath.strip().upper() == "D":  #  D = Default state filename 
                    filepath = "state_pywincmd.json"
            
                filepath = filepath.strip()
                if not os.path.isabs(filepath):
                    filepath = os.path.join(self.current_dir, filepath)

                if os.path.exists(filepath):  # Only needs to test this if on the command line; FileChooser already checks this
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

        if file_chooser:  # We will use the native Dialog to get the filepath
            filepath = self.select_from_native_file_chooser(tipo='load')
            if not filepath:  #<-- If selection was canceled inside the FileChooser
                print(FG_YELLOW + "Operation canceled!" + RST_CLR)
                return False
        else:             # We will use the command line to get the filepath
            prompt_str = "File to load [D = default 'state_pywincmd.json', start of name+TAB = autocomplete, ESC clears, C = cancel]:"
            filepath = None
            while filepath is None:  # if empty ENTER or Ctrl+C was pressed while executing SET /p
                filepath = self.get_user_input_from_native_CMD(prompt_str)

            if filepath.strip().upper() == "C":   # If C+ENTER was typed at the input, cancel the loading
                print(FG_YELLOW + "Operation canceled by user" + RST_CLR)
                return False
            elif  filepath.strip().upper() == "D":  #  D = Default state filename 
                filepath = "state_pywincmd.json"

            filepath = filepath.strip()            
            if not os.path.isabs(filepath):
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
                elif sub_ch == "_": # Ctrl+F2 (Scancode 95)
                    print()
                    print ("Ctrl + F2 was pressed")
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
            for item in os.listdir(base_dir):
                full_path = os.path.join(base_dir, item)
                
                if not item.lower().startswith(partial.lower()):
                    continue
                    
                if only_dirs and not os.path.isdir(full_path):
                    continue
                    
                prefix = os.path.dirname(text)
                candidate = os.path.join(prefix, item) if prefix else item
                
                if " " in candidate:
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

    # =========================================================================
    # --- UNIFIED EXECUTION ENGINE ---
    # =========================================================================
    def _execute_cmd(self, user_command):
            cmd_clean = user_command.strip()
            if not cmd_clean:
                return False

            cmd_lower = cmd_clean.lower()

            # --- DOSKEY INTERCEPTION AND DEFINITION ---
            if cmd_lower.startswith("doskey ") or cmd_lower.startswith("doskey/"):  # DoskeyBLABLA could be a file or pgm name, hence check for SPACE or /
                args = cmd_clean[6:].strip()
                args_lower = args.lower()
                
                if args == "/?":
                    print(r"""
This command allows you to create, edit, export, and import macros, as well as list the command history.
DOSKEY [/MACROS] [/MACROFILE=file] [macro_name=[text]]
    macro_name:    Specifies the name of the macro to be created or edited
    text      :    Specifies the command(s) you want to associate with the macro
    /MACROS   :    Displays all macros
    /MACROFILE=file: Imports previously exported macros to the file (to export, see examples below)
    /HISTORY  :    Lists the entire command history (navigate with Up/Dw and PgUp/PgDw arrows)
    /REINSTALL:    Clears/Resets all macros and ALSO the entire command history.

The following special coding can be used in Doskey macro definitions.
They will be replaced by symbols or texts, according to the table below:
    Code            Description
    $G or $g        Will be replaced by the output redirector ('>').
    $G$G or $g$g    Will be replaced by the append mode output redirector ('>>')
    $L or $l        Will be replaced by the input redirector ('<').
    $B or $b        Will be replaced by the 'pipe' symbol, which makes the output of one command the input of another ('|').
    $T or $t        Will be replaced by the command concatenation symbol ('&').
    $$              Escape code for the '$' character, in case it needs to appear within the macro ('$').
    $1 to $9        Will be replaced by each parameter typed at runtime. $1 is equivalent to %1, etc.
    $* Will be replaced by all text following the macro name at runtime.

Example that simulates the '&&' symbol (execute second concatenated command only if the first succeeds):
    DOSKEY compile=build.bat $T IF NOT ERRORLEVEL 1 deploy.bat 
Example that simulates the '||' symbol (execute second concatenated command only if the first fails):
    DOSKEY test=test.bat $T IF ERRORLEVEL 1 echo Failed! $T something_else.bat
Other Examples:
______ Macro definition ____________________________ Typed ___________________ Executed _____________________________
▌   DOSKEY ls=dir $*                            ▌ ls \users\john    ====>>  dir \users\john                         ▐
▌   DOSKEY cdw=cd $1 $T dir/w $1                ▌ cdw \temp *.bat   ====>>  cd \temp & dir /w *.bat                 ▐
▌   DOSKEY mcd=md $1 $T cd $1                   ▌ mcd logs          ====>>  md logs & cd logs                       ▐
▌   DOSKEY dirfi=dir $1 /b $B findstr /I "$2"   ▌ dirfi logs error  ====>>  dir logs /b & findstr /I "error"        ▐
▌   DOSKEY sd=systeminfo $G sysinfo.txt         ▌ sd                ====>>  systeminfo > sysinfo.txt                ▐
▌   DOSKEY cat=type $*                          ▌ cat ..\bla.log    ====>>  type ..\bla.log                         ▐
▌   DOSKEY catfi=type $1 $B find /I $2          ▌ cat test.ps1 "write"   ====>>  type test.ps1 | find /I "write"    ▐
______ Typed ______________________________________ Result __________________________________________________________  
▌   DOSKEY /MACROS                              ▌ shows a list of all defined macros                                ▐ 
▌   DOSKEY /HISTORY                             ▌ shows a list of all commands already executed                     ▐ 
▌   DOSKEY /REINSTALL                           ▌ resets/clears all macros and ALSO the command history             ▐
▌   DOSKEY /macros > my_macros.txt              ▌ exports current macros to the file my_macros.txt                  ▐ 
▌   DOSKEY /macrofile=my_macros.txt             ▌ imports macros saved in the file (appends or replaces them)       ▐ 
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
                                for key, value in self.macros.items():
                                    f.write(f"{key}={value}\n")
                        except Exception as e:
                            print(FG_RED + f"Error exporting macros file: {e}" + RST_CLR)
                            
                        return False
                    else:
                        return False # Other unrecognized text after /macros	
                    
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
                    key = key.strip()
                    value = value.strip()
                    if not value:
                        self.macros.pop(key, None) # Removes the macro
                    else:
                        self.macros[key] = value
                    return False
                    
                else:
                    return False # Empty or invalid doskey call (except /?)

            # --- DOSKEY MACRO EXPANSION ---
            parts = cmd_clean.split(maxsplit=1)
            if parts:
                first_word = parts[0]
                if first_word in self.macros:
                    macro_val = self.macros[first_word]
                    rest_of_line = parts[1] if len(parts) > 1 else ""
                    
                    # Native DOSKEY special characters substitutions
                    # We use (?i) in regex to be case-insensitive (e.g., accept $t or $T)
                    macro_val = re.sub(r'(?i)\$T', '&', macro_val)
                    macro_val = re.sub(r'(?i)\$G', '>', macro_val)
                    macro_val = re.sub(r'(?i)\$L', '<', macro_val)
                    macro_val = re.sub(r'(?i)\$B', '|', macro_val)

                    # Checks if there is any numerical argument marker ($1 to $9) or $*
                    has_args_marker = bool(re.search(r'\$(\*|[1-9])', macro_val))

                    if has_args_marker:
                        # Extracts the arguments keeping quoted blocks together
                        # Ex: 'arg1 "arg 2" arg3' becomes a list: ['arg1', '"arg 2"', 'arg3']
                        args = re.findall(r'".*?"|\S+', rest_of_line)
                        
                        user_command = macro_val
                        
                        # Replaces $1 to $9
                        for i in range(1, 10):
                            arg_val = args[i-1] if i <= len(args) else ""
                            user_command = user_command.replace(f"${i}", arg_val)
                        
                        # Replaces $* with the entire rest of the original line
                        user_command = user_command.replace("$*", rest_of_line)
                    else:
                        # CMD default behavior: if there are no variables, 
                        # the typed arguments are just concatenated at the end
                        user_command = macro_val + (" " + rest_of_line if rest_of_line else "")

                    # Finally, replaces $$ with a literal $ (in case the user escaped it)
                    user_command = user_command.replace("$$", "$")

                    # Updates execution variables so the rest of the script processes the macro
                    cmd_clean = user_command.strip()
                    cmd_lower = cmd_clean.lower()

            # Interception: EXIT
            if cmd_lower == "exit" or cmd_lower.startswith("exit/"):
                opt = input("Closing emulator session... Do you want to Save the environment state (S/N)? ")
                if opt.lower().startswith("s"):
                    self.save_state_f2()            
                return True

            # Interception: TITLE
            if cmd_lower.startswith("title "):
                args = cmd_clean[5:].strip()
                self.title = args

            # Interception: START (Open new PyWinCmd window)
            is_start_base = (cmd_lower == "start ") or (cmd_lower.startswith("start/"))
                    
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
                return

            # IN CASE it's the 'START' command followed by some program/command/parameter, it will be executed normally.
            # This even allows opening a native CMD window via 'START cmd', IF there are no restrictions/policies   

            # Prepares the execution line (Automatic enveloping in a temporary Batch for PS1, CMD, BAT and 'DOS' INTERNAL commands)
            execution_line = cmd_clean
            match_first = re.match(r'^(?:\"([^\"]+)\"|(\S+))', cmd_clean) 
            
            flag_assoc_file= False
            flag_GUI_pgm= False
            flag_cui_pgm= False
            flag_ps1=False
            flag_cmd_bat=False
            flag_internal_command=False
            update_state_after_batch=True
            first_token = None
            first_token_path = None
            abs_path=False
            if match_first:

                # LET's see if the user 'command' is an  absolut or relative 'path' , and use shutil.which() on it:
                first_token = match_first.group(1) if match_first.group(1) else match_first.group(2) 
                if first_token.startswith('\\'): # An absolute PATH was given, starting with '\'
                    #This search PATHEXT extensions, if it was not given
                    first_token_path = shutil.which(first_token) # Does NOT need the 'path' argument here
                    abs_path = True
                elif len(first_token) > 2 and first_token[1:3] == ':\\' : # An absolute PATH was given, starting with Drive letter
                    #This search PATHEXT extensions, if it was not given
                    first_token_path = shutil.which(first_token) # Does NOT need the 'path' argument here
                    abs_path = True

                # NOW, LET's search for the 'command' in the PATH, only extensions in PATHEXT are looked for 
                if not first_token_path: # Check if a relative PATH as given
                    # Below We check if the command/program/script is part of OUR tracked PATH.
                    # WHY? (we could NOT check at all, and the native CMD would find it in t he PATH - or not). 
                    # The problem is: if the program is an executable EXE that has Windows GUI, and we just call
                    # it from our temporary BAT file, then our PyWinCMD prompt will be blocked until the 
                    # called program is finished (could be MS-Excel, MS-Word, Notepad etc.). That is NOT good !
                    # So, we find the executable in OUR path to be able to check wether it's a GUI type. If it is,
                    # the program is called WITHOUT a temporary BAT, ensuring the call will NOT block. 
                    curr_path=self.current_env.get('PATH', os.environ['PATH'])
                    curr_path=self.current_dir + ";" + curr_path  #<<--- which() does NOT search in the current dir when the 'path' parameter is used, so we add it, to build a CMD-like behavior
                    # the which() function returns ONLY one path, whichever has precedence in the PATH
                    first_token_path = shutil.which(first_token, path=curr_path)
                #End-if

                # Not found yet, BUT it could be a file with extension NOT in PATHEXT, like *.xlsx, *.docx, etc
                if not first_token_path:
                    if abs_path:
                        if os.path.exists(first_token):
                            first_token_path = first_token
                    else:
                        if os.path.exists(self.current_dir + os.sep + first_token):  
                            first_token_path = self.current_dir + os.sep + first_token

                if not first_token_path:
                    # If it is NOT in the PATH, then we consider it an INTERNAL COMMAND (e.g., DIR, ECHO, SET), 
                    # and it will be enveloped in a temp batch. 
                    flag_internal_command = True
                    first_token_path = user_command
                    arguments = ""

                # At this point, any 'resolvable' extension would have been set in first_token_path, just like the native CMD would do  
                else: # The command/pgm/partial-path etc, was found in the PATH

                    #Get the arguments, but before check if user_command is surrounded by quotes:
                    qfirst_token=f'\"{first_token}\"'
                    if cmd_clean.startswith(qfirst_token): # It came with quotes!
                        ft = qfirst_token
                    else:
                        ft = first_token
                    # Now uses the correct surroundings to find the len() below:
                    arguments=cmd_clean[len(ft):].strip()  # Treat as argument everything that comes after the 'command' 

#                   print("Executable or associated file FOUND in path: " + first_token_path )
                    p_lower = first_token_path.lower()

                    # MUST test every case:
                    if p_lower.endswith('.ps1'):
                        flag_ps1 = True
                    elif  p_lower.endswith( ('.bat', '.cmd',) ):
                        flag_cmd_bat = True
                    elif  p_lower.endswith( ('.exe', '.com',) ):
                        IMAGE_SUBSYSTEM_WINDOWS_GUI = 2
                        IMAGE_SUBSYSTEM_WINDOWS_CUI = 3
                        if self.get_exe_subsystem(first_token_path) == IMAGE_SUBSYSTEM_WINDOWS_GUI:  # GUI type / separate apps
                            # Note that GUI programs, like NOTEPAD, or EXCEL.EXE fall here
                            flag_GUI_pgm = True
                        else:  # It's an EXE/COM of type CUI: console program.... and it could be interactive
                            # Also interactive CUI programs like PYTHON.EXE fall here
                            flag_cui_pgm = True
                    else: 
                        # If file EXISTS,  but has NON EXECUTABLE extensions, like *.DOCX, *.VBS, *.XLSX etc, then it may be associated with some PGM
#                        print('Assoc file command:   {first_token_path} {arguments}')
                        flag_assoc_file = True 

            if first_token_path.lower().endswith("cmd.exe") and arguments.lower().startswith("/c"):
                update_state_after_batch= False  # We SHOULD NOT update state when the command is 'cmd /c', this is the correct native behavior


            # Check if the arguments contain '/?' or '/  <spaces> ?', so it is 'getting help' on a command/pgm 
            args_help = False
            patt = r"/ *\?"
            if re.search(patt, arguments):
                update_state_after_batch = False
                args_help = True

            # If the 'command' has spaces in it, then we must surround it with quotes
            if " " in first_token_path:
               ft_path = f'\"{first_token_path}\"'
            else:
               ft_path = first_token_path  

            # --- IF it is a GUI program or a FOUND associated file (like XLSX or DOCX) then we MUST use 'start'
            #     otherwise the temporary BAT file will stay blocked forever on the 'call' :(
            if flag_GUI_pgm or flag_assoc_file:
               execution_line =  f'start /MIN "Temp" {ft_path} {arguments}' 

            elif flag_cmd_bat:
                execution_line = f'call {ft_path} {arguments}' 

            elif flag_internal_command or args_help:   # If arguments have '/?', then we can NOT use 'call', otherwise gets help for 'call'
                execution_line = f'{cmd_clean}'  #<<--- Internal commands should NOT use call, to allow '/?' argument to work

            elif flag_ps1:
                execution_line = f'powershell.exe -ExecutionPolicy Bypass -File {ft_path} {arguments}'

            elif flag_cui_pgm: # It's an EXE or COM of type CUI: they are console programs.... and can be interactive
               # Any interactive CUI program like PYTHON.EXE falls here 
               # They MUST be 'call'ed, otherwise the interactivity would be LOST (user could NOT interact)               
                execution_line = f'call {ft_path} {arguments}'  
            else:
                print(FG_YELLOW + "Could not found a way to execute this command line:( " + RST_CLR)
                self.update_prompt_visual()
                return


            # --- MAIN EXECUTION block -- envelops the execution line in a temporary BAT file to be executed ---
            ERR_MARKER = "PWC_ERR_CAPTURE"
            DIR_MARKER = "PWC_DIR_CAPTURE"
            DRIVES_MARKER = "PWC_DRIVES_CAPTURE"
            CHCP_MARKER = "PWC_CHCP_CAPTURE"
            ENV_MARKER = "PWC_ENV_CAPTURE"

            timestamp = int(time.time() * 1000)
            bat_path = os.path.join(os.environ.get('TEMP', '.'), f'pywincmd_int_{timestamp}.bat')
            out_path = os.path.join(os.environ.get('TEMP', '.'), f'pywincmd_out_{timestamp}.tmp')
            out_path_chcp = os.path.join(os.environ.get('TEMP', '.'), f'pywincmd_chcp_{timestamp}.tmp')

            # Builds the commands to restore the state of each drive in the background
            drive_restorations = "\n".join([f'cd "{path}"' for path in self.drive_dirs.values()])

            bat_content_part1 = f"""@echo off


@REM This script is ALWAYS written and read with UTF-8 encoding by pywincmd.py
@REM So, the  UTF-8 codepage MUST be active throughout the execution of this script, EXCEPT before executing the 'execution_line'; 
@REM This is to ensure that any NON-ASCII chars present in the drives/folders path are not affected by differents CHCP  
chcp 65001 >nul

@REM restore drives and self.current_dir (THESE can have NON-ASCII characters, hence UTF-8 was previously ativacted ):
{drive_restorations}
cd /d "{self.current_dir}"

@REM restore errorlevel from the previous execution of this BAT:
cmd /c exit {self.last_errorlevel}

@REM ONLY AT THIS POINT restore CHCP eventually set in the previous execution  - immediatelly before calling the new execution line:
chcp {self.current_codepage} >nul

@REM The variable below  has the 'execution line' just typed by the user:  {execution_line}
@REM Note that the 'execution line' was set in % PWC_EXECUTION_LINE % env var  by pywincmd just before calling this BAT (visible in that session only)
@rem PS - must use 'call' below, because we have to absorve env vars set when executing *.cmd or *.bat
%PWC_EXECUTION_LINE%

@REM store in env var the NEW chcp EVENTUALLY modified by the execution line above
chcp > "{out_path_chcp}"
set /p NEW_CHCP=<"{out_path_chcp}"

            """

            #Second part of the temporary BAT:     
            bat_content_part2 = f"""
@REM This extra echo off is necessary if the 'execution line' was cmd /k or a long BAT, when exited with Ctrl+C or 'exit'
@echo off

@REM Now restore the UTF-8 codepage again, SO the MARKERS below will be saved in the TMP output file ALWAYS with that encoding
chcp 65001 >nul

(
echo {ERR_MARKER} %errorlevel%
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
            """

            bat_content = bat_content_part1 + bat_content_part2  if update_state_after_batch  else  bat_content_part1 
            with open(bat_path, 'w', encoding='utf-8', errors='ignore') as f: #  'utf-8' is mandatory here

                f.write(bat_content)


            # Now, saves the execution line as an ENV VARIABLE, as they are ENCODING AGNOSTIC  (works in any codepage) !
            # This is required, otherwise the execution_line COULD be misinterpreted if CHCP was called in a previous execution line 
            # and the current execution line has NON-ASCII characters (Common in latin files/folders names )
            self.current_env["PWC_EXECUTION_LINE"] = execution_line #<-- this will be visible to the temp BAT, and well interpreted, regarding the active codepage

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
                subprocess.run(f'cmd /c "{bat_path}"', 
                            cwd=self.current_dir, 
                            )
            except KeyboardInterrupt:
                print(FG_YELLOW + "\n[PWC] Temporary BAT process interrupted by the user. Moving on..." + RST_CLR)

            os.environ.clear()
            os.environ.update(old_environ)

            # --- ENVIRONMENT STATE SYNCHRONIZATION ---
            if not update_state_after_batch:
                # We would do NOTHING here, but there is a little quirk that can affect the console title...
                # Recovers the title; it could have changed if the given command was 'cmd /c' setting a new TITLE, 
                # something unlikely to occur, but here we ensure the STATE is consistent. 
                subprocess.run(f'cmd.exe /c "TITLE {self.title}"')

            else: # STATE will be updated from the existing state when the executed command/program finished
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
            for p in [bat_path, out_path, out_path_chcp]:
                try: os.remove(p)
                except: pass

            self.update_prompt_visual()


    def do_help(self, arg):
        """
        Overrides the default help of Python's cmd.Cmd module and 
        passes the command to the native Windows CMD help.
        """
        klarg = arg.strip().lower()
        if klarg.startswith('doskey'):
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



if __name__ == '__main__':
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
