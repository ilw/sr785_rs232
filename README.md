netgpibdata
===========
SRmeasure, AGmeasure, HPmeasure
---------
These program set up, run, and download the results of measurements performed on a SR785 signal analyzer,  spectrum analyzer, presuming an RS232 communication capability 

Ran without any arguments, the programs displays help text, detailing the available commands. These include options to:

- Download the data currently on the instrument display, with the option of plotting the data with matplotlib.
- Remotely trigger a previously configured measurement.
- Run a user-defined measurement through the use of a template file, with the option to plot the results of the current and previous measurements with matplotlib. 
- Remotely reset the instrument.

Example template files for PSD and frequency response measurements are included, which have some explanation of what the different arguments expect and define. In addition, the program has the option to copy the template files to the user's current working directory to be modified as desired for a specific measurement. 

Python package dependencies:
- numpy
- matplotlib
- yaml 

In ubuntu, these can be installed via `sudo apt-get install python3-numpy python3-matplotlib python3-yaml`


Forked from netgpibdata