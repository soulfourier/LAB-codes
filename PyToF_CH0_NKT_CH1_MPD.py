# -*- coding: utf-8 -*-
"""
Created on Mon Jul 24 17:54:05 2023

@author: sanab
"""
# Copy of file pyToF_test for measurements on 20-08-2023 - bone measurements 


#Author : Pranav Lanka 
# 8th July 2022
#Program for automating TRS measurements using existing python fuctions and libraries

# Prerequisites : Switch on the PIMikroMove Servo
#                       4) Turn on the laser/ amp up to full power (or 90% maybe)
#                       5) Run this program


#PATHS

import os

Pospath = os.getcwd()+'\\Position'
PIPythonpath =  os.getcwd()+'\Source\PIPython-2.3.0.3'
sourcepath = os.getcwd()+'\Source' 
codepath = os.getcwd()
savepath = os.getcwd() + '\Out'

# MODULES AND FUNCTIONS NEEDED FOR THE PROGRAM TO RUN

# import string
# import random
import struct
import time
import ctypes as ct
from ctypes import byref
from sys import exit
from matplotlib.pyplot import *
import matplotlib.pyplot as plt
from numpy import *
from pandas import *
import json
from matplotlib.animation import FuncAnimation
# from pytictoc import TicToc
import sys
# from Other_Functions import generate_random_string



os.chdir(sourcepath)
from pylablib.devices import Thorlabs # device library for Kinesis Motor (Attenuator Stepper Motor)
phlib = ct.CDLL("phlib64.dll") #DLL for PicoHarp 300 

sys.path.append(sourcepath + '\Functions')
from PH_functions import tryfunc,TRSacquire,TRSoptimize, PHarp_init
from Other_Functions import write_counts_to_file,create_graph_with_text

os.chdir(PIPythonpath)
import setup
from pipython import GCSDevice, pitools  # device library for PI (Prism Rotation Stage)


# t = TicToc()

#%% USER INPUTS FOR RUNNING THE PROGRAM


def closeDevices():
    phlib.PH_CloseDevice(ct.c_int(0))
    exit(0)

def generate_random_string(length):
    import string
    import random
    import struct
    """Generate a random string of specified length"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def check_elements_in_list(list1, list2):
    return all(element in list2 for element in list1)


header = generate_random_string(764)
subheader = generate_random_string(204)
    
    
#METADATA (OPTIONAL¦ WILL BE UPDATED TO THE OVERRIDE)
ri = 1.4 # Refractive index of the sample 
Ph_Letter = 'irf'
Ph_Number = 2
data = DataFrame()

geometry = 'reflection' #**** #Reflectance or Transmittance
SDD = 1.5 #**** # Source Detector Distanceance (cm) (thickness of sample in transmittance and 0 in IRF)
rep = 3 #**** # NUMBER OF REPETITIONS YOU WANT AT EACH WAVELENGTH ###############~~~~~~~~~~###############
AFM = 1  #**** # Acquisition Factor Multiple ¦ factor to be multiplied with the Acq time (if higher acq times are needed otherwise leave it to 1)
ARM =60 #**** # Acquisition time Ratio (Max) the max number of seconds the data is acquired when the att treshold is reached but the countrate is not. 
RAS = 1#**** # Relative Attenuation Shift (with Wavelength) - if 0 does not return the Att to startpos on change of wavelength if 1 changes it to startpos

misc = 'kho' #**** # Miscellaneous comments or Remarks on the measurements (will be stored ins the metadata of the output file)

#NECESSARY

meas = 'i' # i-IRF, m- MEASUREMENT, p- PHANTOM
prismname = '690_730_780_850.txt' #**** 500_1100_10 # INxSERT THE FILE WITH THE PRISM STAGE POSITIONS YOU WANT TO MEASURE ###############~~~~~~~~~~###############
breakflag = 0  #**** # FLAG IF YOU NEED A BREAK IN BETWEEN THE MEASUREMENTS TO CHANGE FILTERS OR ...
outname_prefix = 'Irf.end'#**** SoB10b_C2 ###############~~~~~~~~~~#############
outname = outname_prefix + 'Irf.end' #**** ###############~~~~~~~~~~###############
# outname = 'HCBp0001.json' #**** ###############~~~~~~~~~~#############
Outpath = savepath +'\sara\\Sob9f_remeasurement_07.03.2025\\'

# Check if the directory exists
if not os.path.exists(Outpath):
    # Create the directory
    os.makedirs(Outpath)


binning = 0 # you can change this 
offset = 0 # time offset of PH, you can change this   
tacq = 1000 # Measurement time in millisec, you can change this
syncDivider = 8 # you can change this 

CFDZeroCross0 = 15 # you can change this (in mV)
CFDLevel0 = 200 # you can change this (in mV)
CFDZeroCross1 = 20 # you can change this (in mV)
CFDLevel1 = 100 # you can change this (in mV) ## These are the default values



HISTCHAN = 65536 #DO NOT CHANGE
counts = (ct.c_uint * HISTCHAN)()
countRate0 = ct.c_int() #DO NOT CHANGE
countRate1 = ct.c_int() #DO NOT CHANGE

os.chdir(codepath)
with open(Pospath + '\\' + prismname) as f: 
    table1 = read_table(f, index_col=0, header=None, names=['A'],
                          lineterminator='\n')


#%% INIT. PARAMETERS AND VARIABLES FOR PICOHARP 300 (TDC COUNTING BOARD)

LIB_VERSION = "3.0" #DO NOT CHANGE
HISTCHAN = 65536 #DO NOT CHANGE
MODE_HIST = 0 #DO NOT CHANGE
FLAG_OVERFLOW = 0x0040 #DO NOT CHANGE
# resolution = ct.c_double() #DO NOT CHANGE


dev = PHarp_init(syncDivider,offset, CFDZeroCross0 , CFDLevel0 , CFDZeroCross1, CFDLevel1)
# INIT. PARAMETERS AND VARIABLES FOR PRISM AND ATTENUATOR STEPPER MOTORS

PRISMSTAGENAME = 'C-863.11'  # Name of the PI Prism Rotation Stage
REFMODES = ['FRF']  # reference the connected stages
ATTMOTORNUM = "27260206" # Serial Number of Attenuator Stepper Motor
com_port_num = 3
baud_rate_num = 115200

#%% PARAMETERS FOR ITERATIVE OPTIMIZATION  

Cntthrshld_low = 250000 # COUNT RATE THRESHOLD / LOWER GOAL
Cntthrshld_high = 330000 # COUNT RATE THRESHOLD / HIGHER GOAL

if meas == 'i': #IF MEASURING IRF

    Attthrshld = 140 # ATTENUATION MAXIMUM IN DEGREES (STOPS ACQUISITION HERE EVEN IF GOAL IS NOT REACHED) 170 default
    ideg = 3  # STEP SIZE OF ATTENUATOR MOVEMENT IN DEGREES
    startpos = 10 # START ATTENUATING FROM A PREDEFINED POSITION (default-40 for MPD and 2 var filters) (60 IRF with extra OD2 filter***)  

elif meas == 'm': #IF MEASURING DATA

    Attthrshld = 280 # ATTENUATION MAXIMUM IN DEGREES (STOPS ACQUISITION HERE EVEN IF GOAL IS NOT REACHED)
    ideg = 5 # STEP SIZE OF ATTENUATOR MOVEMENT IN DEGREES
    startpos = 220 # START ATTENUATING FROM A PREDEFINED POSITION  default-270 for MPD

elif meas == 'p': #IF MEASURING PHANTOMS

    Attthrshld = 280 # ATTENUATION MAXIMUM IN DEGREES (STOPS ACQUISITION HERE EVEN IF GOAL IS NOT REACHED)
    ideg = 5 # STEP SIZE OF ATTENUATOR MOVEMENT IN DEGREES
    startpos = 180# START ATTENUATING FROM A PREDEFINED POSITION dafault-240 for MPD , Changed to 220 after the nkt high power 

else: #IF MEASURING PHANTOMS

    Attthrshld = 320 # ATTENUATION MAXIMUM IN DEGREES (STOPS ACQUISITION HERE EVEN IF GOAL IS NOT REACHED)
    ideg = 5 # STEP SIZE OF ATTENUATOR MOVEMENT IN DEGREES
    startpos = 10# START ATTENUATING FROM A PREDEFINED POSITION  
    
#%% ITREATIVE OPTIMIZATION OF COUNT RATE

properties = {
              "Geometry" : geometry, # METADATA DICTIONARY (ADD OTHER NECESSARY INFORMATION)
              "SDD" : SDD,                            
              "Refractive Index" : ri,                                          
              # "Resolution" : resolution.value, 
              "Offset" : offset,
              "AcquisitionTime" : tacq,
              "SyncDivider" : syncDivider,
              "CFDZeroCross0" : CFDZeroCross0,
              "CFDLevel0" : CFDLevel0,
              "CFDZeroCross1" : CFDZeroCross1,
              "CFDLevel1" : CFDLevel1,
              "Meas State": meas,
              "Repetitions": rep,
              "Ph_Letter": Ph_Letter,
              "Ph_Number": Ph_Number,              
              "Wavelengths":table1.index.to_list()
              
              }


tacq_optimize = 200 # acqusition time for optimization (ms)   
slp_t1 = 0.1 # first iteration 
slp_t2 = 0.2 # decrement
lamd = []
optpos = []
save_irfopa = 0

# t.tic()

# if filterflag == 1:
#     break_lambda = int(input("Enter the wavelength where you want to pause the acquisition. If no pause is necessary ENTER 0"))
#     if break_lambda in table1.index:
#         print(f"{break_lambda} is in the list.")
#         truncate_index = searchsorted(table1.index, break_lambda)
#         table2 = table1[:truncate_index]
#     else:
#         print(f"{break_lambda} is not on the list of measured wavelengths. Try again.")    

# if breakflag == 1: 
#     pause_values_input = input("Enter the wavelengths to break (separated by spaces): ").split()
#     pause_values = [int(value) for value in pause_values_input]
#     check_pauseval = check_elements_in_list(pause_values, table1.index)


for irot in table1.index:
# for irot in [1100]:
    
    
    # fig2, ax2 = plt.subplots(figsize = (8,6))
    
    
    with GCSDevice(PRISMSTAGENAME) as pidevice:
        pidevice.ConnectRS232(comport=com_port_num, baudrate=baud_rate_num)  # interface cabling properties RS232, Comport and baudrate      
        # print('connected: {}'.format(pidevice.qIDN().strip()))
        print('initialize connected stages...')
        # pitools.startup(pidevice,  refmodes=REFMODES)
        axis = 1
        PI_prev_pos = pidevice.qPOS(axis)[axis]  # query single axis
        print('previous position of prism is {:.2f}'.format( PI_prev_pos))        
        PIposition = float(table1[table1.index == irot].values[0])
        pidevice.MOV(1, PIposition) # Move Prism Stage to the location specified in the file from LINE 35
        print('current position of prism is {:.2f}'.format( PIposition))        
        
        # print('current position of prism is {:.2f}'.format( PIposition))
        
        istage = 0    
        # countRate1.value = 0
        # time.sleep(3)

    with Thorlabs.KinesisMotor(ATTMOTORNUM) as stage:

        stage.setup_velocity(0, 20000, 40000,  scale=True)
        # if irot == table1.index.values[0] :
        stage.move_to(1919* startpos)
        stage.wait_move()
            
        istageval = stage.get_position()
        istage = istageval/1919
        
        while   istage < Attthrshld:    
 
            countRate0, countRate1, counts = TRSacquire(dev,tacq_optimize) 
            time.sleep(slp_t1)
            temp = []
        
            for i in range(0, HISTCHAN):
                temp.append(ct.c_long(counts[i]).value)
            
            # fig = plt.figure(figsize=(12, 9))  # Figure Showing the Acquired Data after each Wavelength Measured
            # plot(temp)
            

            if countRate1.value < Cntthrshld_low :

                istage = istage + ideg    
                stage.move_by(1919*ideg) # initiate a move | 1919 = movement of 1 degree                
                cur_pos = stage.get_position()                                
                time.sleep(slp_t1)
                countRate0, countRate1, counts = TRSacquire(dev,tacq_optimize) 
                x = range(len(counts))
                create_graph_with_text(x, counts, irot, countRate1.value, cur_pos)

            elif  countRate1.value > Cntthrshld_high :
                stage.move_by(-1919*ideg) # initiate a move | 1919 = movement of 1 degree                
                time.sleep(slp_t2)
                cur_pos = stage.get_position()
                countRate0, countRate1, counts = TRSacquire(dev,tacq_optimize)                
                x = range(len(counts))                                
                create_graph_with_text(x, counts, irot, countRate1.value, cur_pos)
 
            else:
                countRate0, countRate1, counts = TRSacquire(dev,tacq_optimize) 
                x = range(len(counts))
                cur_pos = stage.get_position()                                
                time.sleep(slp_t1)
                create_graph_with_text(x, counts, irot, countRate1.value, cur_pos)                
                break
            
        plt.show()      
                    
            
        final_counts = countRate1.value
        aa = stage.get_position(scale=False)
        Acqtime_Ratio = Cntthrshld_high/final_counts

        for irep in range(1,rep+1):  
            temp = []        
            if (Attthrshld - 2 * ideg) < istage and 1 < Acqtime_Ratio < ARM :
                countRate0, countRate1, counts = TRSacquire(dev,int(round(Acqtime_Ratio,2)*1000)) 
                write_counts_to_file(counts, irot, irep, Outpath, outname_prefix,data, header, subheader)                
                x = range(len(counts))                                                
                
            elif (Attthrshld - 2 * ideg) < istage and  Acqtime_Ratio >= ARM :
                Acqtime_Ratio = ARM # if Acqtime is over 30, limit it to 30
                countRate0, countRate1, counts  = TRSacquire(dev,int(round(Acqtime_Ratio,2)*1000)) 
                write_counts_to_file(counts, irot, irep, Outpath, outname_prefix,data, header, subheader)                
                x = range(len(counts))                                                

            else:                
                Acqtime_Ratio = 1 # if no tresholds are reached just acquire for 1 s                
                countRate0, countRate1, counts  = TRSacquire(dev,AFM*int(round(Acqtime_Ratio,2)*1000)) 
                write_counts_to_file(counts, irot, irep, Outpath, outname_prefix,data, header, subheader)                
                x = range(len(counts))                                                

                                

with Thorlabs.KinesisMotor(ATTMOTORNUM) as stage:
    stage.move_to(1919* 10)
    stage.wait_move()


data.columns =  data.columns.map(str)           
dictionaryObject = data.to_dict('list') 
supdict = {'properties' : properties,
            'results':   dictionaryObject}
with open(Outpath + outname, 'w') as outfile:
    json.dump(supdict,outfile)
    
# t.toc()
         
closeDevices()

