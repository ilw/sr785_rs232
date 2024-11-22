import re
import sys
import time
import serial
import termstatus
from typing import Dict, List, Tuple, Union

class SR785:
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1):
        """
        Initialize SR785 instrument connection
        
        Args:
            port (str): Serial port name (e.g., '/dev/ttyUSB0')
            baudrate (int): Communication baud rate
            timeout (float): Communication timeout
        """
        self.ser = self._connect_rs232(port, baudrate, timeout)
    
    def _connect_rs232(self, port: str, baudrate: int, timeout: float) -> serial.Serial:
        """
        Establish serial connection to SR785
        
        Args:
            port (str): Serial port name
            baudrate (int): Communication baud rate
            timeout (float): Communication timeout
        
        Returns:
            serial.Serial: Configured serial connection
        """
        print(f'Connecting to {port} at {baudrate} baud...')
        try:
            ser = serial.Serial(
                port=port, 
                baudrate=baudrate, 
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )
            print('Connected.')
            
            # Clear buffers
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Verify communication
            ser.write(b"*IDN?\n")
            idn_response = ser.readline().decode('ascii').strip()
            print("Instrument ID:", idn_response)
            
            return ser
        except serial.SerialException as e:
            print(f"Error connecting to serial port: {e}")
            raise
    
    def _send_command(self, command: str) -> None:
        """
        Send a command to the SR785
        
        Args:
            command (str): Command to send
        """
        full_command = command + "\n"
        self.ser.write(full_command.encode('ascii'))
        time.sleep(0.1)
    
    def _query(self, command: str) -> str:
        """
        Send a query and read the response
        
        Args:
            command (str): Query to send
        
        Returns:
            str: Response from the instrument
        """
        self._send_command(command)
        response = self.ser.readline().decode('ascii').strip()
        return response
    
    def reset(self) -> None:
        """Reset the SR785 instrument"""
        print('Resetting SR785...')
        self._send_command("*RST")
        time.sleep(12)
        print('Done!')
    
    def download_data(self) -> Tuple[List[List[str]], List[List[str]]]:
        """
        Download measurement data from instrument
        
        Returns:
            Tuple of frequency and data lists
        """
        data = []
        freq = []
        
        dfmt = self._query('DFMT?')[0]
        if dfmt != '0':  # Dual channel or overlay
            for disp in range(2):
                print(f'Downloading data from display #{disp}')
                f, d = self._download_display(disp)
                freq.append(f[:-1])
                data.append(d[:-1])
        else:
            active = int(self._query('ACTD?')[0])
            print(f'Downloading data from display #{active}')
            f, d = self._download_display(active)
            freq.append(f[:-1])
            data.append(d[:-1])
        
        return freq, data
    
    def _download_display(self, disp: int) -> Tuple[List[str], List[str]]:
        """
        Download data for a specific display
        
        Args:
            disp (int): Display number
        
        Returns:
            Tuple of frequency and data lists
        """
        num_points = int(self._query(f'DSPN?{disp}'))
        freq = []
        data = []
        
        print('Reading data')
        progress_info = termstatus.statusTxt('0%')
        
        for bin_num in range(num_points):
            percent = int((bin_num / num_points) * 100)
            progress_info.update(f'{percent}%')
            
            f = self._query(f"DBIN?{disp},{bin_num}")[:-1]
            d = self._query(f"DSPY?{disp},{bin_num}")[:-1]
            
            freq.append(f)
            data.append(d)
        
        progress_info.end('100%')
        time.sleep(1)
        
        return freq, data
    
    def set_parameters(self, params: Dict[str, Union[str, int, float]]) -> None:
        """
        Set instrument parameters based on provided dictionary
        
        Args:
            params (dict): Dictionary of parameter settings
        """
        # Implementation similar to original setParameters function
        # This is a placeholder - you'll need to translate the full logic from the original script
        print('Setting up parameters for the measurement...')

        if params.get('measType') == 'Spectrum':
            if params.get('numOfPoints') <= 100:
                fRes=0 # Resolution is 100 points
            elif params.get('numOfPoints') <= 200:
                fRes=1 # Resolution is 200 points
            elif params.get('numOfPoints') <= 400:
                fRes=2 # Resolution is 400 points
            else:
                fRes=3 # Resolution is 800 points

            if params.get('dualChannel').lower() == "dual":
                self._send_command('DFMT1') # Dual display
                numDisp=2
            else:
                self._send_command('DFMT0') # single display
                numDisp=1

            # Input Settings
            if params.get('inputCoupling1') == "AC":
                icp1="1"
            else:
                icp1="0"
            self._send_command('I1CP'+icp1) #CH1 Input Coupling

            if params.get('inputCoupling2') == "AC":
                icp2="1"
            else:
                icp2="0"
            self._send_command('I2CP'+icp2) #CH2 Input Coupling

            if params.get('inputGND1') == "Float":
                igd1="0"
            else:
                igd1="1"
            self._send_command('I1GD'+igd1) #CH1 Input GND

            if params.get('inputGND2') == "Float":
                igd2="0"
            else:
                igd2="1"
            self._send_command('I2GD'+igd2) #CH2 Input GND

            self._send_command('A1RG0') #AutoRange Off
            self._send_command('A2RG0') #AutoRange Off
            if params.get('arMode') == "Tracking":
                arModeID='1'
            else:
                arModeID='0'
            self._send_command('I1AR'+arModeID) #Auto Range Mode
            self._send_command('I2AR'+arModeID) #Auto Range Mode
            self._send_command('A1RG1') #AutoRange On
            self._send_command('A2RG1') #AutoRange On
            self._send_command('I1AF1') #Anti-Aliasing filter On
            self._send_command('I2AF1') #Anti-Aliasing filter On

            if params.get('inputDiff1') == "A":
                idf1="0"
            else:
                idf1="1"
            self._send_command('I1MD'+idf1) #CH1 Input A-B = 1; A = 0

            if params.get('inputDiff2') == "A":
                idf1="0"
            else:
                idf1="1"
            self._send_command('I2MD'+idf1) #CH2 Input A-B = 1; A = 0

            # Set measurement type, displays

            self._send_command('MGRP2,0') # Measurement Group = FFT
            self._send_command('ISRC1')   # Input = Analog

            if params.get('baseFreq') == "102.4kHz":
                self._send_command('FBAS2,1')  # Base Frequency = 102.4kHz
            else:
                self._send_command('FBAS2,0') # Base Frequency = 100.0kHz

            if  params.get('dataMode') == "dbVrms/rtHz":
                for disp in range(numDisp):
                    self._send_command('UNDB'+str(disp)+','+str(1))   # dB ON
                    self._send_command('UNPK'+str(disp)+','+str(0))   # Vrms OFF
            else:
                for disp in range(numDisp):
                    self._send_command('UNDB'+str(disp)+','+str(0))   # dB OFF
                    self._send_command('UNPK'+str(disp)+','+str(2))   # Vrms ON

            for disp in range(numDisp):
                self._send_command('ACTD'+str(disp)) # Change active display
                self._send_command('MEAS'+str(disp)+','+str(disp)) # 0:FFT1, 1:FFT2
                self._send_command('VIEW'+str(disp)+',0') #Log Magnitude
                self._send_command('PSDU'+str(disp)+',1') # PSD ON
                self._send_command('DISP'+str(disp)+',1') # Live display on

            self._send_command('FLIN2,'+str(fRes))     # Frequency resolution
            self._send_command('FAVG2,1')              # Averaging On

            avgModDict = {"None":0, "Vector":1, "RMS":2, "PeakHold":3}
            if params.get('avgMode') in avgModDict:
                avgModID=avgModDict[params.get('avgMode')]
            else:
                avgModID=2
            self._send_command('FAVM2,'+str(avgModID)) # Averaging mode
            self._send_command('FAVT2,0')            # Averaging Type = Linear
            self._send_command('FREJ2,1')            # Overload Reject On
            self._send_command('FAVN2,'+str(params.get('numAvg'))) # Number of Averaging
            winFuncDict = {"Uniform":0, "Flattop":1, "Hanning":2, "BMH":3,
                           "Kaiser":4, "Force/Exponential":5, "User":6,
                           "[-T/2,T/2]":7,"[0,T/2]":8, "[-T/4,T/4]":9}

            if params.get('windowFunc') in winFuncDict:
                winFuncID=winFuncDict[params.get('windowFunc')]
            else:
                winFuncID=2
            self._send_command('FWIN2,'+str(winFuncID))    # Window function
            self._send_command('FSTR2,'+params.get('startFreq'))         # Start frequency
            self._send_command('FSPN2,'+params.get('spanFreq'))          # Frequency span

        elif params.get('measType') == 'TF':
            # Make sure PSD units are off
            psdOff(ser)
            # Input Settings
            if params.get('inputCoupling1') == "AC":
                icp1="1"
            else:
                icp1="0"
            self._send_command('I1CP'+icp1) #CH1 Input Coupling

            if params.get('inputCoupling2') == "AC":
                icp2="1"
            else:
                icp2="0"
            self._send_command('I2CP'+icp2) #CH2 Input Coupling

            if params.get('inputGND1') == "Float":
                igd1="0"
            else:
                igd1="1"
            self._send_command('I1GD'+igd1) #CH1 Input GND

            if params.get('inputGND2') == "Float":
                igd2="0"
            else:
                igd2="1"
            self._send_command('I2GD'+igd2) #CH2 Input GND

            self._send_command('A1RG0') #AutoRange Off
            self._send_command('A2RG0') #AutoRange Off
            if params.get('arMode') == "Tracking":
                arModeID='1'
            else:
                arModeID='0'
            self._send_command('I1AR'+arModeID) #Auto Range Mode
            self._send_command('I2AR'+arModeID) #Auto Range Mode
            self._send_command('A1RG1') #AutoRange On
            self._send_command('A2RG1') #AutoRange On
            self._send_command('I1AF1') #Anti-Aliasing filter On
            self._send_command('I2AF1') #Anti-Aliasing filter On

            if params.get('inputDiff1') == "A":
                idf1="0"
            else:
                idf1="1"
            self._send_command('I1MD'+idf1) #CH1 Input A-B = 1; A = 0

            if params.get('inputDiff2') == "A":
                idf1="0"
            else:
                idf1="1"
            self._send_command('I2MD'+idf1) #CH2 Input A-B = 1; A = 0

            # Set measurement type, displays

            self._send_command('DFMT1') # Dual display
            self._send_command('ACTD0') # Active display 0
            self._send_command('MGRP2,3') # Measurement Group = Swept Sine
            self._send_command('MEAS2,47') # Frequency Resp
            self._send_command('DISP0,1') # Live display on
            self._send_command('DISP1,1') # Live display on
            if params.get('integrate').lower() == 'time':
                self._send_command('SSTM2,'+str(params.get('settleTime'))) #Settle time
                self._send_command('SITM2,'+str(params.get('intTime'))) #Integration Time
            else:
                self._send_command('SSCY2,'+str(params.get('settleCycles'))) # Settle cycles
                self._send_command('SICY2,'+str(params.get('intCycles'))) # Integration cycles
            self._send_command('SSTR2,'+params.get('startFreq')) #Start frequency
            self._send_command('SSTP2,'+params.get('stopFreq')) #Stop frequency
            self._send_command('SNPS2,'+str(params.get('numOfPoints'))) #Number of points
            self._send_command('SRPT2,0') #Single shot mode
            if params.get('sweepType') == 'Linear':
                sweepTypeID='0'
            else:
                sweepTypeID='1'
            self._send_command('SSTY2,'+sweepTypeID) # Sweep Type
            self._send_command('SSAM'+params.get('excAmp')) #Source Amplitude
            self._send_command('SOFF'+params.get('excOff')) #Source Offset

            # Windowing
            #windowDict={'Uniform':0,'Flattop':1, 'Hanning':2, 'BMH':3, 'Kaiser':4,
            #            'Force/Exponential':5, 'User':6}
            #self._send_command('FWIN0,'+windowDict[windowFunc])
            # Set units
            if params.get('dataMode') == "ReIm":
                self._send_command('VIEW0,3') # Disp 0 = Real part
                self._send_command('VIEW1,4') # Disp 1 = Imag part
                self._send_command('UNDB0,0') # dB OFF
                self._send_command('UNDB1,0') # dB OFF
            else:
                self._send_command('VIEW0,0') # Disp 0 = LogMag
                self._send_command('VIEW1,5') # Dsip 1 = Phase
                if 'dB' in params.get('dataMode'):
                    self._send_command('UNDB0,1') # dB On
                else:
                    self._send_command('UNDB0,0') # dB Off
                self._send_command('UNDB1,0') # dB OFF
                self._send_command('UNPH1,0') # Phase Unit deg.
        else:
            raise ValueError('Wrong measurement type entered in parameter file!')
    
    def measure(self, meas_type: str) -> None:
        """
        Start a measurement
        
        Args:
            meas_type (str): Type of measurement ('Spectrum' or 'TF')
        """
        # Start measurement
        sys.stdout.flush()
        self._send_command('STRT')
        
        if meas_type == 'Spectrum':
            print('Starting Spectrum measurement...')
            time.sleep(0.1)
            print('    Averages completed:')
            av_tot = int(self._query('FAVN?0'))
            avg_status = termstatus.progressBar(20, av_tot)
            
            measuring = True
            while measuring:
                measuring = not int(self._query('DSPS?1'))
                avg = int(self._query("NAVG?0"))
                avg_status.update(avg)
                time.sleep(0.5)
            
            avg_status.update(int(self._query("NAVG?0")))
            
            # Auto scale
            self._send_command('ASCL0')
            self._send_command('ASCL1')
        
        elif meas_type == 'TF':
            print('Starting Transfer Function measurement...')
            time.sleep(1)
            
            num_points = int(self._query('SNPS?0'))
            progress_info = termstatus.progressBar(20, num_points)
            
            measuring = True
            while measuring:
                measuring = not int(self._query('DSPS?4'))
                time.sleep(0.1)
                progress_info.update(int(self._query('SSFR?')))
                time.sleep(0.4)
            
            progress_info.end()
    
    def close(self) -> None:
        """Close the serial connection"""
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
            print('SR785 connection closed.')
            


      
'''
# Basic usage
sr785 = SR785('/dev/ttyUSB0')
sr785.reset()

# Set parameters (you'll need to fill in the actual parameter dictionary)
params = {
    'measType': 'Spectrum',
    # other parameters...
}
sr785.set_parameters(params)

# Perform measurement
sr785.measure('Spectrum')

# Download data
freq, data = sr785.download_data()

# Close connection
sr785.close()

'''