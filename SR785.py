import re
import sys
from math import floor
import time
import serial
import termstatus

####################
# RS232
####################

def connectRS232(port, baudrate=9600, timeout=1):
    """
    Connect to SR785 via RS232 serial port
    
    Args:
        port (str): COM port name (e.g., 'COM3' or '/dev/ttyUSB0')
        baudrate (int): Baud rate for communication (default 9600)
        timeout (float): Communication timeout in seconds
    
    Returns:
        serial.Serial: Configured serial connection object
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
        
        # Clear any existing buffer
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Send simple query to verify communication
        ser.write(b"*IDN?\n")
        idnResponse = ser.readline().decode('ascii').strip()
        print("Instrument ID:", idnResponse)
        
        return ser
    except serial.SerialException as e:
        print(f"Error connecting to serial port: {e}")
        raise

def send_command(ser, command):
    """
    Send a command to the SR785
    
    Args:
        ser (serial.Serial): Serial connection object
        command (str): Command to send
    """
    full_command = command + "\n"
    ser.write(full_command.encode('ascii'))
    time.sleep(0.1)

def query(ser, command):
    """
    Send a query and read the response
    
    Args:
        ser (serial.Serial): Serial connection object
        command (str): Query to send
    
    Returns:
        str: Response from the instrument
    """
    send_command(ser, command)
    response = ser.readline().decode('ascii').strip()
    return response

# Most other functions from the original script remain the same
# Just replace send_command(ser,) with send_command(ser, )
# and query(ser,) with query(ser, )

def reset(ser):
    """Reset the SR785 instrument"""
    print('Resetting SR785...')
    send_command(ser, "*RST")
    time.sleep(12)
    print('Done!')

def psdOff(ser):
    """Ensure PSD units are off"""
    while query(ser, 'PSDU?0')[0] == '1' or query(ser, 'PSDU?1')[0] == '1':
        mGrp = query(ser, 'MGRP?0')
        meas0 = query(ser, 'MEAS?0')
        meas1 = query(ser, 'MEAS?1')
        send_command(ser, 'MGRP2,0')
        send_command(ser, 'MEAS0,0')
        send_command(ser, 'MEAS0,1')
        send_command(ser, 'PSDU0,0')
        send_command(ser, 'PSDU1,0')
        time.sleep(.5)
        send_command(ser, f'MGRP2,{mGrp.split()[0]}')
        send_command(ser, f'MEAS0,{meas0.split()[0]}')
        send_command(ser, f'MEAS1,{meas1.split()[0]}')



####################
# Compatibility with old netgpibdata script
####################


def getdata(ser, dataFile, paramFile):
    # For compatibility with old netgpibdata
    timeStamp = time.strftime('%b %d %Y - %H:%M:%S', time.localtime())
    send_command(ser,"OUTX0")
    time.sleep(0.1)
    (freq,data)=download(ser)
    writeHeader(dataFile, timeStamp)
    writeData(dataFile, freq, data, delimiter=', ')


def getparam(ser, fileRoot, dataFile, paramFile):
    # For compatibility with old netgpibdata
    timeStamp = time.strftime('%b %d %Y - %H:%M:%S', time.localtime())
    writeHeader(paramFile, timeStamp)
    writeParams(ser, paramFile)


####################
# Fetching data
####################


def download(ser):
    data=list()
    freq=list()
    if query(ser,'DFMT?')[0] != '0': # Dual channel, or overlay
        for disp in range(2):
            print('Downloading data from display #'+str(disp))
            (f,d)=downloadDisplay(ser, disp)
            freq.append(f[:-1])
            data.append(d[:-1])
    else:
        active = int(query(ser,'ACTD?')[0])
        print('Downloading data from display #'+str(active))
        (f,d)=downloadDisplay(ser, active)
        freq.append(f[:-1])
        data.append(d[:-1])

    return(freq, data)


def downloadDisplay(ser, disp):
    #Get the number of points on the Display
    numPoint = int(query(ser,'DSPN?'+str(disp),100))
    freq=[]
    data=[]
    accomplished=0
    print('Reading data')
    progressInfo=termstatus.statusTxt('0%')

    for bin in range(numPoint): #Loop for frequency bins
        percent = int(floor(100*bin/numPoint))

        if (percent - accomplished) >= 1 and percent < 100:
            progressInfo.update(str(percent)+'%')
            accomplished = percent
            pass

        f=query(ser,"DBIN?"+str(disp)+","+str(bin),100)
        f=f[:-1] #Chop new line character
        d=query(ser,"DSPY?"+str(disp)+","+str(bin),100)
        d=d[:-1] #Chop new line character
        freq.append(f)
        data.append(d)

    progressInfo.end('100%')
    time.sleep(1)
    return (freq,data)


####################
# Output file writing
####################


def writeHeader(dataFile, timeStamp):
    dataFile.write('# SR785 Measurement - Timestamp: ' + timeStamp+'\n')


def writeData(dataFile, freq, data, delimiter='    '):
    print('Writing measurement data to file...')
    #Write data vectors
    if len(freq) > 1: #Dual chan

        if freq[0] == freq[1]: #Shared Freq axis
            for i in range(len(freq[0])):
                dataFile.write(str(freq[0][i]) + delimiter + str(data[0][i])
                                + delimiter + str(data[1][i]) + '\n')

        else: #Unequal axes! Kind of awkward to output nicely
            print('Unequal Frequency Axes, stacking output')
            for i in range(len(freq[0])):
                dataFile.write(str(freq[0][i]) + delimiter + str(data[0][i]) + '\n')
            # Print unit line?
            dataFile.write('# Channel 2 Data\n')
            for i in range(len(freq[1])):
                dataFile.write(str(freq[1][i]) + delimiter + str(data[1][i]) + '\n')

    else: #Single display
        for i in range(len(freq[0])):
            dataFile.write(str(freq[0][i])+ delimiter +str(data[0][i])+'\n')


####################
# Run new measurement
####################


def measure(ser, measType):
    #Start measurement
    sys.stdout.flush()
    send_command(ser,'STRT') #Start
    #Wait for the measurement to end
    measuring = True

    if measType == 'Spectrum':
        print('Starting ' + measType + ' measurement...')
        time.sleep(0.1)
        print('    Averages completed:')
        avTot=int(query(ser,'FAVN?0'))
        avgStatus=termstatus.progressBar(20,avTot)
        while measuring:
            measuring = not int(query(ser,'DSPS?1'))
            avg=int(query(ser,"NAVG?0"))
            avgStatus.update(avg)
            time.sleep(0.5)
        avgStatus.update(int(query(ser,"NAVG?0")))

        send_command(ser,'ASCL0') #Auto scale
        send_command(ser,'ASCL1') #Auto scale

    elif measType =='TF':
        print('Starting ' + measType + ' measurement...')
        time.sleep(1)
        numPoints=int(query(ser,'SNPS?0')) #Number of points
        progressInfo=termstatus.progressBar(20,numPoints)
        while measuring:
            #Get status
            ## Manual says we should check bit 0 as well...
            #measuring = not (int(query(ser,'DSPS?4'))
            #                 or int(query(ser,'DSPS?0')))
            measuring = not int(query(ser,'DSPS?4'))
            time.sleep(0.1)
            progressInfo.update(int(query(ser,'SSFR?')))
            time.sleep(0.4)
        progressInfo.end()


####################
# Saving and setting measurement parameters
####################


def writeParams(ser, paramFile):
    #Get measurement parameters
    print('Reading instrument parameters')

    #Get the display format
    if int(query(ser,"DFMT?")) != '0':
        dispList = range(2)
    else:
        dispList = [int(query(ser,'ACTD?')[0])]

    #Get display parameters for each display
    measGrp=[]
    measurement=[]
    view=[]
    unit=[]

    time.sleep(0.1)

    for disp in dispList:
        i=int(query(ser,"MGRP?"+str(disp)))
        measGrp.append({0: 'FFT' ,
                         1: 'Correlation',
                         2: 'Octave',
                         3: 'Swept Sine',
                         4: 'Order',
                         5: 'Time/Histogram'}[i])

    #Get measurement
        i=int(query(ser,"MEAS?"+str(disp)))
        measurement.append(
        {0: 'FFT 1',
         1: 'FFT 2',
         2: 'Power Spectrum 1',
         3: 'Power Spectrum 2',
         4: 'Time 1',
         5: 'Time 2',
         6: 'Windowed Time 1',
         7: 'Windowed Time 2',
         8: 'Orbit',
         9: 'Coherence',
         10: 'Cross Spectrum',
         11: 'Frequency Response',
         12: 'Capture Buffer 1',
         13: 'Capture Buffer 2',
         14: 'FFT User Function 1',
         15: 'FFT User Function 2',
         16: 'FFT User Function 3',
         17: 'FFT User Function 4',
         18: 'FFT User Function 5',
         19: 'Auto Correlation 1',
         20: 'Auto Correlation 2',
         21: 'Cross Correlation',
         22: 'Time 1',
         23: 'Time 2',
         24: 'Windowed Time 1',
         25: 'Windowed Time 2',
         26: 'Capture Buffer 1',
         27: 'Capture Buffer 2',
         28: 'Correlation Function 1',
         29: 'Correlation Function 2',
         30: 'Correlation Function 3',
         31: 'Correlation Function 4',
         32: 'Correlation Function 5',
         33: 'Octave 1',
         34: 'Octave 2',
         35: 'Capture 1',
         36: 'Capture 2',
         37: 'Octave User Function 1',
         38: 'Octave User Function 2',
         39: 'Octave User Function 3',
         40: 'Octave User Function 4',
         41: 'Octave User Function 5',
         42: 'Spectrum 1',
         43: 'Spectrum 2',
         44: 'Normalized Variance 1',
         45: 'Normalized Variance 2',
         46: 'Cross Spectrum',
         47: 'Frequency Response',
         48: 'Swept Sine User Function 1',
         49: 'Swept Sine User Function 2',
         50: 'Swept Sine User Function 3',
         51: 'Swept Sine User Function 4',
         52: 'Swept Sine User Function 5',
         53: 'Linear Spectrum 1',
         54: 'Linear Spectrum 2',
         55: 'Power Spectrum 1',
         56: 'Power Spectrum 2',
         57: 'Time 1',
         58: 'Time 2',
         59: 'Windowed Time 1',
         60: 'Windowed Time 2',
         61: 'RPM Profile',
         62: 'Orbit',
         63: 'Track 1',
         64: 'Track 2',
         65: 'Capture Buffer 1',
         66: 'Capture Buffer 2',
         67: 'Order User Function 1',
         68: 'Order User Function 2',
         69: 'Order User Function 3',
         70: 'Order User Function 4',
         71: 'Order User Function 5',
         72: 'Histogram 1',
         73: 'Histogram 2',
         74: 'PDF 1',
         75: 'PDF 2',
         76: 'CDF 1',
         77: 'CDF 2',
         78: 'Time 1',
         79: 'Time 2',
         80: 'Capture Buffer 1',
         81: 'Capture Buffer 2',
         82: 'Histogram User Function 1',
         83: 'Histogram User Function 2',
         84: 'Histogram User Function 3',
         85: 'Histogram User Function 4',
         86: 'Histogram User Function 5'
         }[i])

        #View information
        i=int(query(ser,"VIEW?"+str(disp)))
        view.append({0: 'Log Magnitude',
                     1: 'Linear Magnitude',
                     2: 'Magnitude Squared',
                     3: 'Real Part',
                     4: 'Imaginary Part',
                     5: 'Phase',
                     6: 'Unwrapped Phase',
                     7: 'Nyquist',
                     8: 'Nichols'}[i])

        #Units
        result=query(ser,'UNIT?'+str(disp))
        result=result[:-1]  # Chop a new line character
        unit.append(result.replace('\xfb','rt'))

    #Input Source
    i=int(query(ser,"ISRC?"))
    time.sleep(0.1)
    inputSource={0: 'Analog',
                 1: 'Capture'}[i]

    #Input Mode
    i=int(query(ser,"I1MD?"))
    CH1inputMode={0: 'Single ended',
                 1: 'Differential'}[i]
    i=int(query(ser,"I2MD?"))
    CH2inputMode={0: 'Single ended',
                 1: 'Differential'}[i]

    #Grounding
    i=int(query(ser,"I1GD?"))
    CH1Grounding={0: 'Float',
                 1: 'Grounded'}[i]
    i=int(query(ser,"I2GD?"))
    CH2Grounding={0: 'Float',
                 1: 'Grounded'}[i]

    #Coupling
    i=int(query(ser,"I1CP?"))
    CH1Coupling={0: 'DC',
                 1: 'AC',
                  2:'ICP'}[i]
    i=int(query(ser,"I2CP?"))
    CH2Coupling={0: 'DC',
                 1: 'AC',
                  2:'ICP'}[i]

    #Input Range
    result=query(ser,"I1RG?")
    match=re.search(r'^\s*([-+\d]*),.*',result)
    CH1Range=str(float(match.group(1)))
    match=re.search(r'\d,(\d)',result)
    i=int(match.group(1))
    CH1Range=CH1Range+{0: 'dBVpk', 1: 'dBVpp', 2: 'dBVrms', 3: 'Vpk', 4: 'Vpp',
                       5: 'Vrms', 6: 'dBEUpk', 7: 'dBEUpp', 8: 'dBEUrms',
                       9: 'EUpk', 10: 'EUpp', 11: 'EUrms'}[i]

    result=query(ser,"I2RG?")
    match=re.search(r'^\s*([-+\d]*),.*',result)
    CH2Range=str(float(match.group(1)))
    match=re.search(r'\d,(\d)',result)
    i=int(match.group(1))
    CH2Range=CH2Range+{0: 'dBVpk', 1: 'dBVpp', 2: 'dBVrms', 3: 'Vpk', 4: 'Vpp',
                       5: 'Vrms', 6: 'dBEUpk', 7: 'dBEUpp', 8: 'dBEUrms',
                       9: 'EUpk', 10: 'EUpp', 11: 'EUrms'}[i]

    #Auto Range
    i=int(query(ser,"A1RG?"))
    CH1AutoRange={0: 'Off', 1: 'On'}[i]
    i=int(query(ser,"I1AR?"))
    CH1AutoRangeMode={0: 'Up Only', 1: 'Tracking'}[i]
    i=int(query(ser,"A2RG?"))
    CH2AutoRange={0: 'Off', 1: 'On'}[i]
    i=int(query(ser,"I2AR?"))
    CH2AutoRangeMode={0: 'Normal', 1: 'Tracking'}[i]

    #Anti-Aliasing Filter
    i=int(query(ser,"I1AF?"))
    CH1AAFilter={0: 'Off', 1: 'On'}[i]
    i=int(query(ser,"I1AF?"))
    CH2AAFilter={0: 'Off', 1: 'On'}[i]

    #Source type
    i=int(query(ser,"STYP?"))
    SrcType={0: "Sine", 1: "Chirp", 2: "Noise", 3: "Arbitrary"}[i]

    #Source amplitude
    if SrcType == "Sine":
        if measGrp[0] == "Swept Sine":
            result=query(ser,"SSAM?")
        else:
            result=query(ser,"S1AM?")

        match=re.search(r'^\s*([-+.\d]*),.*',result)
        SrcAmp=str(float(match.group(1)))
        match=re.search(r'\d,(\d)',result)
        i=int(match.group(1))
        SrcAmp=SrcAmp+{0: 'mVpk', 1: 'mVpp', 2: 'mVrms', 3: 'Vpk', 4: 'Vrms',
                       5: 'dBVpk', 6: 'dBVpp', 7: 'dBVrms'}[i]
    elif SrcType == "Chirp":
        result=query(ser,"CAMP?")
        match=re.search(r'^\s*([-+.\d]*),.*',result)
        SrcAmp=str(float(match.group(1)))
        match=re.search(r'\d,(\d)',result)
        i=int(match.group(1))
        SrcAmp=SrcAmp+{0: 'mV', 1: 'V', 2: 'dBVpk'}[i]
    elif SrcType == "Noise":
        result=query(ser,"NAMP?")
        match=re.search(r'^\s*([-+.\d]*),.*',result)
        SrcAmp=str(float(match.group(1)))
        match=re.search(r'\d,(\d)',result)
        i=int(match.group(1))
        SrcAmp=SrcAmp+{0: 'mV', 1: 'V', 2: 'dBVpk'}[i]
    else:
        result=float(query(ser,"AAMP?"))
        SrcAmp=str(result/100)+"V"

    SrcOn = query(ser,"SRCO?")

    print("Writing to the parameter file.")

    paramFile.write('#---------- Measurement Setup ------------\n')

    if measGrp[0] == 'FFT':
        startFreq=query(ser,"FSTR?0")[:-1]
        spanFreq=query(ser,"FSPN?0")[:-1]
        resDict={'0':'100', '1':'200', '2':'400', '3':'800'}
        numOfPoints = resDict[query(ser,"FLIN?"+str(0))[:-1]]
        numAvg = query(ser,"FAVN?0")[:-1]
        avgModDict = {'0':"None", '1':"Vector", '2':"RMS", '3':"PeakHold"}
        avgMode = avgModDict[query(ser,"FAVM?0")[:-1]]
        winFuncDict = {'0':"Uniform", '1':"Flattop", '2':"Hanning", '3':"BMH",
                       '4':"Kaiser", '5':"Force/Exponential", '6':"User",
                       "[-T/2,T/2]":7, '8':"[0,T/2]", '9':"[-T/4,T/4]"}
        windowFunc = winFuncDict[query(ser,'FWIN?0')[:-1]]

        paramFile.write('# Start Frequency (Hz): '+startFreq+'\n')
        paramFile.write('# Frequency Span (Hz): '+spanFreq+'\n')
        paramFile.write('# Frequency Resolution: '+numOfPoints+'\n')
        paramFile.write('# Number of Averages: '+numAvg+'\n')
        paramFile.write('# Averaging Mode: '+avgMode+'\n')
        paramFile.write('# Window function: '+windowFunc+'\n')

    elif measGrp[0] == 'Swept Sine':
        startFreq = query(ser,'SSTR?0')[:-1]
        stopFreq = query(ser,'SSTP?0')[:-1]
        numOfPoints = query(ser,"SNPS?0")[:-1]
        excAmp = query(ser,'SSAM?')[:-3]
        settleCycles = query(ser,'SSCY?0')[:-1]
        intCycles = query(ser,'SICY?0')[:-1]

        paramFile.write('# Start frequency (Hz) = '+startFreq+'\n')
        paramFile.write('# Stop frequency (Hz) = '+stopFreq+'\n')
        paramFile.write('# Number of frequency points = '+numOfPoints+'\n')
        paramFile.write('# Excitation amplitude (mV) = '+excAmp+'\n')
        paramFile.write('# Settling cycles = '+settleCycles+'\n')
        paramFile.write('# Integration cycles = '+intCycles+'\n')


    paramFile.write('#---------- Measurement Parameters ----------\n')
    paramFile.write('# Measurement Group: ')
    for disp in dispList:
        paramFile.write(' "'+measGrp[disp]+'"')
    paramFile.write('\n')
    paramFile.write('# Measurements: ')
    for disp in dispList:
        paramFile.write(' "'+measurement[disp]+'"')
    paramFile.write('\n')
    paramFile.write('# View: ')
    for disp in dispList:
        paramFile.write(' "'+view[disp]+'"')
    paramFile.write('\n')
    paramFile.write('# Unit: ')
    for disp in dispList:
        paramFile.write(' "'+unit[disp]+'"')
    paramFile.write('\n')

    paramFile.write('#---------- Input Parameters ----------\n')
    paramFile.write('# Input Source: ')
    paramFile.write(inputSource+'\n')
    paramFile.write('# Input Mode: ')
    paramFile.write(CH1inputMode+', '+CH2inputMode+'\n')
    paramFile.write('# Input Grounding: ')
    paramFile.write(CH1Grounding+', '+CH2Grounding+'\n')
    paramFile.write('# Input Coupling: ')
    paramFile.write(CH1Coupling+', '+CH2Coupling+'\n')
    paramFile.write('# Input Range: ')
    paramFile.write(CH1Range+', '+CH2Range+'\n')
    paramFile.write('# Auto Range: ')
    paramFile.write(CH1AutoRange+', '+CH2AutoRange+'\n')
    paramFile.write('# Auto Range Mode: ')
    paramFile.write(CH1AutoRangeMode+', '+CH2AutoRangeMode+'\n')
    paramFile.write('# Anti-Aliasing Filter: ')
    paramFile.write(CH1AAFilter+', '+CH2AAFilter+'\n')

    paramFile.write('#---------- Source Parameters ----------\n')
    paramFile.write('# Source Type: ')
    paramFile.write(SrcType+"\n")
    paramFile.write('# Source Amplitude: ')
    paramFile.write(SrcAmp+"\n")
    paramFile.write('# Source On: ')
    paramFile.write(SrcOn+"\n")

    paramFile.write('#---------- Measurement Data ----------\n')
    paramFile.write('# [Freq(Hz) ')
    for disp in dispList:
        paramFile.write('Display '+str(disp)+'('+unit[disp]+') ')
    paramFile.write(']\n')


def setParameters(ser,params):
    # Read dictionary of settings to set up the instrument
    print('Setting up parameters for the measurement...')

    if params['measType'] == 'Spectrum':
        if params['numOfPoints'] <= 100:
            fRes=0 # Resolution is 100 points
        elif params['numOfPoints'] <= 200:
            fRes=1 # Resolution is 200 points
        elif params['numOfPoints'] <= 400:
            fRes=2 # Resolution is 400 points
        else:
            fRes=3 # Resolution is 800 points

        if params['dualChannel'].lower() == "dual":
            send_command(ser,'DFMT1') # Dual display
            numDisp=2
        else:
            send_command(ser,'DFMT0') # single display
            numDisp=1

        # Input Settings
        if params['inputCoupling1'] == "AC":
            icp1="1"
        else:
            icp1="0"
        send_command(ser,'I1CP'+icp1) #CH1 Input Coupling

        if params['inputCoupling2'] == "AC":
            icp2="1"
        else:
            icp2="0"
        send_command(ser,'I2CP'+icp2) #CH2 Input Coupling

        if params['inputGND1'] == "Float":
            igd1="0"
        else:
            igd1="1"
        send_command(ser,'I1GD'+igd1) #CH1 Input GND

        if params['inputGND2'] == "Float":
            igd2="0"
        else:
            igd2="1"
        send_command(ser,'I2GD'+igd2) #CH2 Input GND

        send_command(ser,'A1RG0') #AutoRange Off
        send_command(ser,'A2RG0') #AutoRange Off
        if params['arMode'] == "Tracking":
            arModeID='1'
        else:
            arModeID='0'
        send_command(ser,'I1AR'+arModeID) #Auto Range Mode
        send_command(ser,'I2AR'+arModeID) #Auto Range Mode
        send_command(ser,'A1RG1') #AutoRange On
        send_command(ser,'A2RG1') #AutoRange On
        send_command(ser,'I1AF1') #Anti-Aliasing filter On
        send_command(ser,'I2AF1') #Anti-Aliasing filter On

        if params['inputDiff1'] == "A":
            idf1="0"
        else:
            idf1="1"
        send_command(ser,'I1MD'+idf1) #CH1 Input A-B = 1; A = 0

        if params['inputDiff2'] == "A":
            idf1="0"
        else:
            idf1="1"
        send_command(ser,'I2MD'+idf1) #CH2 Input A-B = 1; A = 0

        # Set measurement type, displays

        send_command(ser,'MGRP2,0') # Measurement Group = FFT
        send_command(ser,'ISRC1')   # Input = Analog

        if params['baseFreq'] == "102.4kHz":
            send_command(ser,'FBAS2,1')  # Base Frequency = 102.4kHz
        else:
            send_command(ser,'FBAS2,0') # Base Frequency = 100.0kHz

        if  params['dataMode'] == "dbVrms/rtHz":
            for disp in range(numDisp):
                send_command(ser,'UNDB'+str(disp)+','+str(1))   # dB ON
                send_command(ser,'UNPK'+str(disp)+','+str(0))   # Vrms OFF
        else:
            for disp in range(numDisp):
                send_command(ser,'UNDB'+str(disp)+','+str(0))   # dB OFF
                send_command(ser,'UNPK'+str(disp)+','+str(2))   # Vrms ON

        for disp in range(numDisp):
            send_command(ser,'ACTD'+str(disp)) # Change active display
            send_command(ser,'MEAS'+str(disp)+','+str(disp)) # 0:FFT1, 1:FFT2
            send_command(ser,'VIEW'+str(disp)+',0') #Log Magnitude
            send_command(ser,'PSDU'+str(disp)+',1') # PSD ON
            send_command(ser,'DISP'+str(disp)+',1') # Live display on

        send_command(ser,'FLIN2,'+str(fRes))     # Frequency resolution
        send_command(ser,'FAVG2,1')              # Averaging On

        avgModDict = {"None":0, "Vector":1, "RMS":2, "PeakHold":3}
        if params['avgMode'] in avgModDict:
            avgModID=avgModDict[params['avgMode']]
        else:
            avgModID=2
        send_command(ser,'FAVM2,'+str(avgModID)) # Averaging mode
        send_command(ser,'FAVT2,0')            # Averaging Type = Linear
        send_command(ser,'FREJ2,1')            # Overload Reject On
        send_command(ser,'FAVN2,'+str(params['numAvg'])) # Number of Averaging
        winFuncDict = {"Uniform":0, "Flattop":1, "Hanning":2, "BMH":3,
                       "Kaiser":4, "Force/Exponential":5, "User":6,
                       "[-T/2,T/2]":7,"[0,T/2]":8, "[-T/4,T/4]":9}

        if params['windowFunc'] in winFuncDict:
            winFuncID=winFuncDict[params['windowFunc']]
        else:
            winFuncID=2
        send_command(ser,'FWIN2,'+str(winFuncID))    # Window function
        send_command(ser,'FSTR2,'+params['startFreq'])         # Start frequency
        send_command(ser,'FSPN2,'+params['spanFreq'])          # Frequency span

    elif params['measType'] == 'TF':
        # Make sure PSD units are off
        psdOff(ser)
        # Input Settings
        if params['inputCoupling1'] == "AC":
            icp1="1"
        else:
            icp1="0"
        send_command(ser,'I1CP'+icp1) #CH1 Input Coupling

        if params['inputCoupling2'] == "AC":
            icp2="1"
        else:
            icp2="0"
        send_command(ser,'I2CP'+icp2) #CH2 Input Coupling

        if params['inputGND1'] == "Float":
            igd1="0"
        else:
            igd1="1"
        send_command(ser,'I1GD'+igd1) #CH1 Input GND

        if params['inputGND2'] == "Float":
            igd2="0"
        else:
            igd2="1"
        send_command(ser,'I2GD'+igd2) #CH2 Input GND

        send_command(ser,'A1RG0') #AutoRange Off
        send_command(ser,'A2RG0') #AutoRange Off
        if params['arMode'] == "Tracking":
            arModeID='1'
        else:
            arModeID='0'
        send_command(ser,'I1AR'+arModeID) #Auto Range Mode
        send_command(ser,'I2AR'+arModeID) #Auto Range Mode
        send_command(ser,'A1RG1') #AutoRange On
        send_command(ser,'A2RG1') #AutoRange On
        send_command(ser,'I1AF1') #Anti-Aliasing filter On
        send_command(ser,'I2AF1') #Anti-Aliasing filter On

        if params['inputDiff1'] == "A":
            idf1="0"
        else:
            idf1="1"
        send_command(ser,'I1MD'+idf1) #CH1 Input A-B = 1; A = 0

        if params['inputDiff2'] == "A":
            idf1="0"
        else:
            idf1="1"
        send_command(ser,'I2MD'+idf1) #CH2 Input A-B = 1; A = 0

        # Set measurement type, displays

        send_command(ser,'DFMT1') # Dual display
        send_command(ser,'ACTD0') # Active display 0
        send_command(ser,'MGRP2,3') # Measurement Group = Swept Sine
        send_command(ser,'MEAS2,47') # Frequency Resp
        send_command(ser,'DISP0,1') # Live display on
        send_command(ser,'DISP1,1') # Live display on
        if params['integrate'].lower() == 'time':
            send_command(ser,'SSTM2,'+str(params['settleTime'])) #Settle time
            send_command(ser,'SITM2,'+str(params['intTime'])) #Integration Time
        else:
            send_command(ser,'SSCY2,'+str(params['settleCycles'])) # Settle cycles
            send_command(ser,'SICY2,'+str(params['intCycles'])) # Integration cycles
        send_command(ser,'SSTR2,'+params['startFreq']) #Start frequency
        send_command(ser,'SSTP2,'+params['stopFreq']) #Stop frequency
        send_command(ser,'SNPS2,'+str(params['numOfPoints'])) #Number of points
        send_command(ser,'SRPT2,0') #Single shot mode
        if params['sweepType'] == 'Linear':
            sweepTypeID='0'
        else:
            sweepTypeID='1'
        send_command(ser,'SSTY2,'+sweepTypeID) # Sweep Type
        send_command(ser,'SSAM'+params['excAmp']) #Source Amplitude
        send_command(ser,'SOFF'+params['excOff']) #Source Offset

        # Windowing
        #windowDict={'Uniform':0,'Flattop':1, 'Hanning':2, 'BMH':3, 'Kaiser':4,
        #            'Force/Exponential':5, 'User':6}
        #send_command(ser,'FWIN0,'+windowDict[windowFunc])
        # Set units
        if params['dataMode'] == "ReIm":
            send_command(ser,'VIEW0,3') # Disp 0 = Real part
            send_command(ser,'VIEW1,4') # Disp 1 = Imag part
            send_command(ser,'UNDB0,0') # dB OFF
            send_command(ser,'UNDB1,0') # dB OFF
        else:
            send_command(ser,'VIEW0,0') # Disp 0 = LogMag
            send_command(ser,'VIEW1,5') # Dsip 1 = Phase
            if 'dB' in params['dataMode']:
                send_command(ser,'UNDB0,1') # dB On
            else:
                send_command(ser,'UNDB0,0') # dB Off
            send_command(ser,'UNDB1,0') # dB OFF
            send_command(ser,'UNPH1,0') # Phase Unit deg.
    else:
        raise ValueError('Wrong measurement type entered in parameter file!')


# Example usage
def main():
    try:
        # Replace 'COM3' with your actual COM port
        ser = connectRS232('COM3')
        
        # Perform operations...
        reset(ser)
        
        # Close connection when done
        ser.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()