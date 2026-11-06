# IDP-AGV
Source code for the AGV for the Integrated Design Project.

All code has been compiled into main.py. 
main.py and main_final_to_run.py are identical, initially used to prototype added functionality, as code needed significant changin

To run, simply upload main.py, or main_final_to_run.py on the pico, and press the button, provided all pins and connections are identical

The other files are test scripts to test sensors, and individual fiels to program scripts on before adding to robot script. There was a problem when running scripts covering many files on the pico, so one file main was created. 

Files are well commented so code should be self explanatory. 

Pre requisites for running the code, 
All connections should be made to appropraite pins, see code. 
All sensors should be live and feeding ata to pico
The robot must start on the node, with all 3 sensors on, so its ready to turn to the depots. 
The threshold for magnetic sensing should be callibrated to real world conditions. 
timing constants in code should be changed for real world conditions
Arm out, in and grabbing should be callibrated to real world. 