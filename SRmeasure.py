#!/usr/bin/env python
# Master SR785 measurement script
# Eric Quintero - 2014

# Standard library imports
import os, sys, time
import argparse

# Neccesary external libraries
import yaml
import numpy as np
import matplotlib.pyplot as plt

# Custom libaries
import SR785 as inst

def readParams(paramFile):
    # Function to read a measurement parameter file in the YAML format
    with open(paramFile,'r') as f:
        reader = yaml.load_all(f)
        params = reader.next()
        reader.close()
    return(params)


def specPlot(dataArray, nDisp, params, legLabel, axlist):
    plotTitle = params.get('plotTitle','SR785 Spectrum')
    if nDisp == 2:
        ## Switch this out if your matplotlib is too old to have plt.subplots
        #f =plt.gcf()
        #axlist=[plt.subplot(211), plt.subplot(212)]

        axlist[0].plot(dataArray[:,0],dataArray[:,1],label=legLabel+" (Ch1)")
        axlist[1].plot(dataArray[:,0],dataArray[:,2],label=legLabel+" (Ch2)")
        axlist[0].set_xscale('log')
        axlist[0].set_ylabel('Magnitude ('+params['dataMode']+')')
        axlist[0].set_yscale('log')
        axlist[1].set_xscale('log')
        axlist[1].set_xlabel('Freq. (Hz)')
        axlist[1].set_yscale('log')
        axlist[1].set_ylabel('Magnitude ('+params['dataMode']+')')
        axlist[0].set_title(plotTitle+' - ' +
                time.strftime('%b %d %Y - %H:%M:%S', time.localtime()))
        axlist[0].axis('tight')
        axlist[1].axis('tight')
        axlist[0].grid('on', which='both')
        axlist[1].grid('on', which='both')
        axlist[0].legend()
        axlist[0].get_legend().get_frame().set_alpha(.7)
    else:
        axlist.plot(dataArray[:,0],dataArray[:,1],label=legLabel)
        axlist.set_xscale('log')
        axlist.set_xlabel('Freq. (Hz)')
        axlist.set_ylabel('Magnitude ('+params['dataMode']+')')
        axlist.set_yscale('log')
        axlist.set_title(params['plotTitle']+' - ' +
                time.strftime('%b %d %Y - %H:%M:%S', time.localtime()))
        axlist.axis('tight')
        axlist.grid('on', which='both')
        axlist.legend()
        axlist.get_legend().get_frame().set_alpha(.7)


def tfPlot(dataArray, params, legLabel, axlist):
    plotTitle = params.get('plotTitle','SR785 TF')
    format = params['dataMode']
    if format.lower() == 'reim':
        Carray = dataArray[:,1] + 1j*dataArray[:,2]
    elif format.lower() =='magdeg':
        Carray = dataArray[:,1] * np.exp(1j*dataArray[:,2]/180.0*np.pi)
    elif format.lower() =='dbdeg':
        Carray = 10**(dataArray[:,1]/20.0)*np.exp(1j*dataArray[:,2]/180.0*np.pi)
    else: # FIXME, what do I do if it doesn't match anything?
        print('Problem detecting units for plot... assuming dB, Degrees')
        Carray = 10**(dataArray[:,1]/20.0)*np.exp(1j*dataArray[:,2]/180.0*np.pi)

    ## Switch this out if your matplotlib is too old to have plt.subplots
    #f =plt.gcf()
    #axlist=[plt.subplot(211), plt.subplot(212)]
    axlist[0].plot(dataArray[:,0],20*np.log10(np.abs(Carray)),label=legLabel)
    axlist[1].plot(dataArray[:,0],np.angle(Carray, deg=True),label=legLabel)

    axlist[0].set_xscale('log')
    axlist[0].set_ylabel('Magnitude (dB)')
    axlist[0].set_yscale('linear')
    axlist[1].set_xscale('log')
    axlist[1].set_xlabel('Freq. (Hz)')
    axlist[1].set_yscale('linear')
    axlist[1].set_ylabel('Phase (deg)')
    axlist[0].set_title(plotTitle+' - ' +
            time.strftime('%b %d %Y - %H:%M:%S', time.localtime()))
    axlist[0].axis('tight')
    axlist[1].axis('tight')
    axlist[1].set_ylim((-180,180))
    axlist[0].grid('on', which='both')
    axlist[1].grid('on', which='both')
    axlist[1].legend(loc=2)
    axlist[1].get_legend().get_frame().set_alpha(.7)


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

def writeParams(sr785, paramFile):
    #Get measurement parameters
    print('Reading instrument parameters')

    #Get the display format
    if int(sr785._query("DFMT?")) != '0':
        dispList = range(2)
    else:
        dispList = [int(sr785._query('ACTD?')[0])]

    #Get display parameters for each display
    measGrp=[]
    measurement=[]
    view=[]
    unit=[]

    time.sleep(0.1)

    for disp in dispList:
        i=int(sr785._query("MGRP?"+str(disp)))
        measGrp.append({0: 'FFT' ,
                         1: 'Correlation',
                         2: 'Octave',
                         3: 'Swept Sine',
                         4: 'Order',
                         5: 'Time/Histogram'}[i])

    #Get measurement
        i=int(sr785._query("MEAS?"+str(disp)))
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
        i=int(sr785._query("VIEW?"+str(disp)))
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
        result=sr785._query('UNIT?'+str(disp))
        result=result[:-1]  # Chop a new line character
        unit.append(result.replace('\xfb','rt'))

    #Input Source
    i=int(sr785._query("ISRC?"))
    time.sleep(0.1)
    inputSource={0: 'Analog',
                 1: 'Capture'}[i]

    #Input Mode
    i=int(sr785._query("I1MD?"))
    CH1inputMode={0: 'Single ended',
                 1: 'Differential'}[i]
    i=int(sr785._query("I2MD?"))
    CH2inputMode={0: 'Single ended',
                 1: 'Differential'}[i]

    #Grounding
    i=int(sr785._query("I1GD?"))
    CH1Grounding={0: 'Float',
                 1: 'Grounded'}[i]
    i=int(sr785._query("I2GD?"))
    CH2Grounding={0: 'Float',
                 1: 'Grounded'}[i]

    #Coupling
    i=int(sr785._query("I1CP?"))
    CH1Coupling={0: 'DC',
                 1: 'AC',
                  2:'ICP'}[i]
    i=int(sr785._query("I2CP?"))
    CH2Coupling={0: 'DC',
                 1: 'AC',
                  2:'ICP'}[i]

    #Input Range
    result=sr785._query("I1RG?")
    match=re.search(r'^\s*([-+\d]*),.*',result)
    CH1Range=str(float(match.group(1)))
    match=re.search(r'\d,(\d)',result)
    i=int(match.group(1))
    CH1Range=CH1Range+{0: 'dBVpk', 1: 'dBVpp', 2: 'dBVrms', 3: 'Vpk', 4: 'Vpp',
                       5: 'Vrms', 6: 'dBEUpk', 7: 'dBEUpp', 8: 'dBEUrms',
                       9: 'EUpk', 10: 'EUpp', 11: 'EUrms'}[i]

    result=sr785._query("I2RG?")
    match=re.search(r'^\s*([-+\d]*),.*',result)
    CH2Range=str(float(match.group(1)))
    match=re.search(r'\d,(\d)',result)
    i=int(match.group(1))
    CH2Range=CH2Range+{0: 'dBVpk', 1: 'dBVpp', 2: 'dBVrms', 3: 'Vpk', 4: 'Vpp',
                       5: 'Vrms', 6: 'dBEUpk', 7: 'dBEUpp', 8: 'dBEUrms',
                       9: 'EUpk', 10: 'EUpp', 11: 'EUrms'}[i]

    #Auto Range
    i=int(sr785._query("A1RG?"))
    CH1AutoRange={0: 'Off', 1: 'On'}[i]
    i=int(sr785._query("I1AR?"))
    CH1AutoRangeMode={0: 'Up Only', 1: 'Tracking'}[i]
    i=int(sr785._query("A2RG?"))
    CH2AutoRange={0: 'Off', 1: 'On'}[i]
    i=int(sr785._query("I2AR?"))
    CH2AutoRangeMode={0: 'Normal', 1: 'Tracking'}[i]

    #Anti-Aliasing Filter
    i=int(sr785._query("I1AF?"))
    CH1AAFilter={0: 'Off', 1: 'On'}[i]
    i=int(sr785._query("I1AF?"))
    CH2AAFilter={0: 'Off', 1: 'On'}[i]

    #Source type
    i=int(sr785._query("STYP?"))
    SrcType={0: "Sine", 1: "Chirp", 2: "Noise", 3: "Arbitrary"}[i]

    #Source amplitude
    if SrcType == "Sine":
        if measGrp[0] == "Swept Sine":
            result=sr785._query("SSAM?")
        else:
            result=sr785._query("S1AM?")

        match=re.search(r'^\s*([-+.\d]*),.*',result)
        SrcAmp=str(float(match.group(1)))
        match=re.search(r'\d,(\d)',result)
        i=int(match.group(1))
        SrcAmp=SrcAmp+{0: 'mVpk', 1: 'mVpp', 2: 'mVrms', 3: 'Vpk', 4: 'Vrms',
                       5: 'dBVpk', 6: 'dBVpp', 7: 'dBVrms'}[i]
    elif SrcType == "Chirp":
        result=sr785._query("CAMP?")
        match=re.search(r'^\s*([-+.\d]*),.*',result)
        SrcAmp=str(float(match.group(1)))
        match=re.search(r'\d,(\d)',result)
        i=int(match.group(1))
        SrcAmp=SrcAmp+{0: 'mV', 1: 'V', 2: 'dBVpk'}[i]
    elif SrcType == "Noise":
        result=sr785._query("NAMP?")
        match=re.search(r'^\s*([-+.\d]*),.*',result)
        SrcAmp=str(float(match.group(1)))
        match=re.search(r'\d,(\d)',result)
        i=int(match.group(1))
        SrcAmp=SrcAmp+{0: 'mV', 1: 'V', 2: 'dBVpk'}[i]
    else:
        result=float(sr785._query("AAMP?"))
        SrcAmp=str(result/100)+"V"

    SrcOn = sr785._query("SRCO?")

    print("Writing to the parameter file.")

    paramFile.write('#---------- Measurement Setup ------------\n')

    if measGrp[0] == 'FFT':
        startFreq=sr785._query("FSTR?0")[:-1]
        spanFreq=sr785._query("FSPN?0")[:-1]
        resDict={'0':'100', '1':'200', '2':'400', '3':'800'}
        numOfPoints = resDict[sr785._query("FLIN?"+str(0))[:-1]]
        numAvg = sr785._query("FAVN?0")[:-1]
        avgModDict = {'0':"None", '1':"Vector", '2':"RMS", '3':"PeakHold"}
        avgMode = avgModDict[sr785._query("FAVM?0")[:-1]]
        winFuncDict = {'0':"Uniform", '1':"Flattop", '2':"Hanning", '3':"BMH",
                       '4':"Kaiser", '5':"Force/Exponential", '6':"User",
                       "[-T/2,T/2]":7, '8':"[0,T/2]", '9':"[-T/4,T/4]"}
        windowFunc = winFuncDict[sr785._query('FWIN?0')[:-1]]

        paramFile.write('# Start Frequency (Hz): '+startFreq+'\n')
        paramFile.write('# Frequency Span (Hz): '+spanFreq+'\n')
        paramFile.write('# Frequency Resolution: '+numOfPoints+'\n')
        paramFile.write('# Number of Averages: '+numAvg+'\n')
        paramFile.write('# Averaging Mode: '+avgMode+'\n')
        paramFile.write('# Window function: '+windowFunc+'\n')

    elif measGrp[0] == 'Swept Sine':
        startFreq = sr785._query('SSTR?0')[:-1]
        stopFreq = sr785._query('SSTP?0')[:-1]
        numOfPoints = sr785._query("SNPS?0")[:-1]
        excAmp = sr785._query('SSAM?')[:-3]
        settleCycles = sr785._query('SSCY?0')[:-1]
        intCycles = sr785._query('SICY?0')[:-1]

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





def main(paramFile=None, filename=None, serial=None,
         plotResult=None, plotRefs=None, leglabel=None):
    if paramFile is None:
        # Set sensible defaults for downloading live data
        noParam = True
        params={}
        params['nameRoot'] = 'SR785'
        params['saveDir'] = os.getcwd()+'/'
        params['plotRefs'] = False
        params['plotResult'] = False
    else:
        noParam = False
        print('Reading parameters from '+paramFile)
        params=readParams(paramFile)
        params['fileName']=paramFile

    fileExt='.txt'
    if filename is not None:
        params['nameRoot'] = filename.split('.')[0]
        if '.' in filename:
            fileExt = ''.join(filename.split('.')[1:])
    if serial is not None:
        params['serial'] = serial
    if plotResult is not None:
        params['plotResult'] = plotResult
        params['saveFig'] = True
    if plotRefs is not None:
        params['plotRefs'] = plotRefs
        params['refDir'] = os.getcwd()+'/'

    sr785 = inst.SR785(params['serial'])

    # Set up output file names
    params['timeStamp'] = time.strftime('%b %d %Y - %H:%M:%S', time.localtime())
    fileRoot = (params['nameRoot'] + '_' +
                time.strftime('%d-%m-%Y', time.localtime()) +
                time.strftime('_%H%M%S', time.localtime()))
    dataFileName = fileRoot+fileExt
    outDir = params['saveDir'];

    # If new measurement is requested, do it!
    if noParam is False:
        print('Executing measurement specified in '+paramFile)
        sr785.set_parameters(params)
        sr785.measure(params['measType'])

    else: # What kind of measurement are we doing?
        active = int(sr785._query('ACTD?')[0])
        measGrp=int(sr785._query("MGRP?"+str(active)))
        if measGrp==3:
            params['measType']='TF'
            result=sr785._query('UNIT?0')[:-1]+sr785._query('UNIT?1')[:-1]
            params['dataMode']=result
        elif measGrp==0:
            params['measType']='Spectrum'
            #Units
            result=sr785._query('UNIT?'+str(active))
            result=result[:-1]  # Chop a new line character
            params['dataMode']=result.replace('\xfb','rt')
        else:
            params['measType']='Other'
            if params['plotResult'] is True:
                print("Not measuring TF or Spectrum, will skip plotting")
                params['plotResult']=False
        print('Detected Units: '+params['dataMode'])

    # Let the instrument catch up, then download the data
    time.sleep(2)
    (freq, data) = sr785.download_data()

    # Done measuring! Just output file writing and plotting below
    print('Saving files to '+outDir)
    print('Measurement data will be written into '+outDir+dataFileName)

    with open(outDir + dataFileName,'w') as dataFile:
        sr785.writeHeader(dataFile, params['timeStamp'])

        if noParam is False: dataFile.write('# Parameter File: '
                                            + params['fileName']+'\n')

        writeParams(sr785, dataFile)
        writeData(dataFile, freq, data)

    print("Done!")
    sr785.close()

    if params['plotResult'] is True:
        print('Plotting!')
        dataArray = np.transpose(np.vstack((np.array(freq[0],dtype='float'),
                                            np.array(data,dtype='float'))))

        f, axlist = plt.subplots(nrows=len(data), ncols=1, sharex=True)

        # Plot references if desired
        if params['plotRefs'] is True:
            # Get list of files with the same nameRoot
            refFiles = [ rf for rf in os.listdir(params['refDir'])
                         if (params['nameRoot'] in rf and '.txt' in rf and
                             rf != dataFileName)]
            print('Found ' + str(len(refFiles)) + ' references; plotting...')

            # Plot each reference in order
            refFiles.sort()
            for filename in refFiles:
                refArray = np.loadtxt(params['refDir']+filename)

                # Find memo or timestamp of Ref for the legend
                with open(params['refDir']+filename,'r') as rf:
                    foundLine = False
                    for line in rf:
                        if foundLine is False:
                            if 'Memo:' in line:
                                legendLine = ''.join(line.split('Memo:')[1:])
                                foundLine=True
                            elif 'Timestamp:' in line:
                                legendLine = ''.join(line.split('Timestamp:')[1:])
                                foundLine=True
                    if foundLine is False: legendLine = filename

                if params['measType'] == 'Spectrum':
                    specPlot(refArray, len(data), params, legendLine, axlist)
                elif params['measType'] == 'TF':
                    tfPlot(refArray, params, legendLine, axlist)

        if leglabel is None: 
            leglabel = params['timeStamp']
        if params['measType'] == 'Spectrum':
            specPlot(dataArray, len(data), params, leglabel, axlist)
        elif params['measType'] == 'TF':
            tfPlot(dataArray, params, leglabel, axlist)

        f.set_size_inches(17,11)
        if params['saveFig'] is True:
            f.savefig(outDir+fileRoot+'.pdf',format='pdf')
        try:
            plt.show()
        except:
            print('Failed to show plot! X11 problem?')


if __name__ == "__main__":

    # Set location of template files, should live with the script
    scriptPath = os.path.dirname(os.path.realpath(__file__))
    SPtemplateFile = scriptPath + '/SPSR785template.yml'
    TFtemplateFile = scriptPath + '/TFSR785template.yml'

    class helpfulParser(argparse.ArgumentParser):
        def error(self, message):
            sys.stderr.write('Error: %s\n' % message)
            self.print_help()
            sys.exit(2)

    parser = helpfulParser()
    group = parser.add_mutually_exclusive_group()

    group.add_argument('paramFile', nargs='?',
                       help = 'The parameter file for the measurement.',
                       default=None)

    parser.add_argument('-s', '--serial',  help='serial port location, typically'\
                        '/dev/ttyUSB0 Overrides parameter file.', default = '/dev/ttyUSB0')

    parser.add_argument('-f', '--filename',  help='Stem of output filename.'\
                        'Overrides parameter file.', default = None)

    parser.add_argument('-l', '--leglabel',  help='Legend label for measured'\
                        'trace. Overrides parameter file.', default = None)

    group.add_argument('--template', help='Copy template parameter files to'\
                       ' current dir; no measurement is made.',
                       action='store_true')

    group.add_argument('--reset', help='Resets the SR785, a serial port is required'\
                       ' are required.', action='store_true')

    group.add_argument('--getdata', help='Downloads live data from an SR785.'\
                       ' a serial port is required.',
                       action='store_true')

    group.add_argument('--trigger', help='Trigger the currently configured '\
                       'measurement on an SR785. a serial port is required '\
                       '.', action='store_true')

    parser.add_argument('--plot', help='Plot result of measurement. Overrides'\
                        ' parameter file.', action='store_true',default = None)

    parser.add_argument('--plotRefs', help='Plot reference traces. Overrides'\
                        ' parameter file. Reads files that have the same'\
                        ' filename stem as references.',action='store_true',
                        default = None)

    args = parser.parse_args()

    if args.paramFile is not None:
        main(args.paramFile, args.filename, args.serial,
             args.plot, args.plotRefs, args.leglabel)

    elif args.template:
        import shutil
        print('Copying ' +SPtemplateFile+ ' to ' + os.getcwd())
        shutil.copyfile(SPtemplateFile, os.getcwd()+'/SPSR785template.yml')
        print('Copying ' +TFtemplateFile+ ' to ' + os.getcwd())
        shutil.copyfile(TFtemplateFile, os.getcwd()+'/TFSR785template.yml')
        print('Done!')

    elif args.serial is None:
        parser.error('Must specify a serial port!\n')

    elif args.getdata:
        main(None, args.filename, args.serial
             args.plot, args.plotRefs, args.leglabel)

    elif args.reset:
        sr785 = inst.SR785(args.serial)
        sr785.reset()
        sr785.close()

    elif args.trigger:
        sr785 = inst.SR785(args.serial)
        sr785._send_command('STRT')
        sr785.close()