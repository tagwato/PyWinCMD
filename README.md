![](images/PWC.png)  
<br><br>

# PyWinCMD
Python program that simulates the command prompt on Windows systems.  
It's useful when access to the CMD native prompt is restricted.
<br><br>

# Motivation
Although there are other ways to execute commands — even when the native CMD prompt is restricted — there are situations where using a tool that mimics the native prompt is more advantageous, for example:
- for those accustomed to using the CMD prompt
- for those who need to execute a command and then run another one only after evaluating the result of the previous execution
- for those who want to manually activate or deactivate different Python virtual environments and run .py programs within them.

# How to use
Download the content of this repository and extract it in any folder.  
Run the 'PyWinCm - RUN.cmd' script and, at the 'PWC' prompt, type the commands you want.  
<br>
PS - Check out some examples in ['TEST_CASES.txt'](TEST_CASES.txt)  
<br><br>

# Compatibility with 'CMD.exe'
PyWinCMD uses the system console through Python, and each command is executed via the native 'CMD.exe', so it has full compatibility with that program.  
To keep the environment state consistent, PyWinCMD tracks and internally persists relevant information after each command is executed.  
See the online Help for more information.
<br><br>

# Requirements
PyWinCMD uses the installed 'python.exe' on the target computer.  

Alternatively, PyWinCMD can be used together with a portable version of Python. In this case, we recommend using [PortablePython4Windows](https://github.com/heindrickson/PortablePython4Windows) due to its versatility. Another advantage is that it comes with PyWinCMD pre-installed, ready for use with any Python version you wish to configure within that portable environment! 🚀
<br><br>

# Screenshots
<br>
PyWinCMD online help:

<img src="images/PyWinCMD%20Help%20message.png" alt="PyWinCMD online help" style="border: 1px solid white; border-radius: 8px;">
<br><br>

Some commands executed in PyWinCMD prompt:

<img src="images/Some%20commands.png" alt="Some commands executed in PyWinCMD prompt" style="border: 1px solid white; border-radius: 8px;">
<br><br>

Interactive commands/programs executed in PyWinCMD prompt:

<img src="images/Interactive%20commands.png" alt="Interative commands/programs executed in PyWinCMD prompt" style="border: 1px solid white; border-radius: 8px;">
<br><br>

Activating other Python virtual environments from PyWinCMD prompt:

<img src="images/Executing%20Python%20virtual%20environments.png" alt="[Activating other Python virtual environments from PyWinCMD prompt" style="border: 1px solid white; border-radius: 8px;">
<br><br>

Native Help for CMD commands:

<img src="images/Native%20HELP%20for%20CMD%20commands.png" alt="Native Help for CMD commands" style="border: 1px solid white; border-radius: 8px;">
<br><br>

Customization is possible via Windows Terminal 'Settings' menu.  
It's advisable to create a new profile for PyWinCMD and configure it:

<img src="images/Settings%20via%20Windows%20Terminal.png" alt="[Customization via Windows Terminal 'Settings' menu" style="border: 1px solid white; border-radius: 8px;">
<br><br>

Customizing appearance (fonts,foreground and background colors etc.) for a PyWinCMD profile:

<img src="images/Appearance%20settings%20via%20Windows%20Terminal.png" alt="Customizing appearance for a PyWinCMD profile" style="border: 1px solid white; border-radius: 8px;">
<br>

# License
PyWinCMD is licensed for use, modification and distribution under the terms of Mozilla Public License version 2.0 (MPL-2.0).  
