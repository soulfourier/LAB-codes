import os
import pickle
import numpy as np
import matplotlib.pyplot as plt
import time
import seabreeze
seabreeze.use('cseabreeze')
from seabreeze.spectrometers import Spectrometer
import ctypes as ct


PIPythonpath =  os.getcwd()+'\Source\PIPython-2.3.0.3'
sourcepath = os.getcwd()+'\Source' 


os.chdir(PIPythonpath)
import setup
from pipython import GCSDevice, pitools  # device library for PI (Prism Rotation Stage)

os.chdir(sourcepath)
from pylablib.devices import Thorlabs # device library for Kinesis Motor (Attenuator Stepper Motor)
phlib = ct.CDLL("phlib64.dll")

PRISMSTAGENAME = 'C-863.11'
ATTMOTORNUM = "27260206"
com_port_num = 3
baud_rate_num = 115200

filename = 'persistent_data.pkl' #to save the coefficients even after running the code
store_lambda = '700_800_850.txt' #saves all the target wavelengths

High_Thres = 20000
Low_Thres =  15000
startpos = 15
ideg = 3
Attthrshld = 100
wavelength_arr = [700, 800, 850]
###########################################
# acquires spectrum at different prism stage positions from 11 to 12 degrees in steps of 0.05 degrees (20 values)
# applies polynomial fit of degree 3 to the wavelength-rotation curve and computes the coefficients
# save the coefficients to a pickle file persistent_data.pkl (so that it can be used in future)
###########################################
def recalibrate(PRISMSTAGENAME, int_time_s, wavelength_arr ):
    degree = 3
    rot_arr = np.arange(11.1,12.5,0.1)
    spec = Spectrometer.from_first_available() #instantiate spec object 
    spec.integration_time_micros(int_time_s) #set integration time of spectrometer
    with GCSDevice(PRISMSTAGENAME) as pidevice:
      pidevice.ConnectRS232(comport = com_port_num, baudrate= baud_rate_num)
      axis = 1  
      position = pidevice.qPOS(axis)[axis]#establish communication with prism stage rotator
      # pidevice.InterfaceSetupDlg() 
      print('Current position of prism: ', position, 'deg')
      wavelength = np.array([]) # array to store the argument of max intensity from intensity array (basically the wavelengths)
      
      for irot in rot_arr :
        pidevice.MOV(axis,irot) #move the prism to the i position
        time.sleep(0.5) #wait for ___ s
        wave_arr = spec.wavelengths() #acquire wavelengths
        intensity_arr = spec.intensities() #acquire intensities
        plt.plot(wave_arr,intensity_arr)
        
        m = np.argmax(intensity_arr) #find the index of the max intensity (thats the selected wavelength)
        wavelength = np.append(wavelength,wave_arr[m])  #append the selected wavelength to the array
      coefficients = [float(f"{i:.6f}") for i in np.polyfit(rot_arr, wavelength, degree)] #fit a polynomial curve of degree __ to the data
      with open(filename, "wb") as f: #save the coefficients to a pickle file so that it can be used in future (no recalibration needed)
        pickle.dump(coefficients, f)
      poly = np.poly1d(coefficients)
      rot_range = np.arange(11,13.377000,0.000050) #range of prism rotation degrees
      fit_curve = [float("{:.2f}".format(poly(x))) for x in rot_range] #generates the wavelength values for the polynomial function
      with open(store_lambda, 'w') as store:
        for ilam in wavelength_arr:
          index = np.where(np.isclose(fit_curve, ilam, atol = 0.05)) #finds the index of the closest value to the target wavelength
          index = index[0][0] 
          store.write(str(ilam) + ' ' + str(rot_range[index]) + '\n')

      pidevice.CloseConnection()
      spec.close() #close the spectrometer connection
      
      

      

####################################
# Here user can input the target wavelength and the prism stage rotates to a position where the fiber selects the target wavelength
####################################
with open("persistent_data.pkl", "rb") as f:
    coefficients = pickle.load(f)
poly = np.poly1d(coefficients) #generates the polynomial function with the coefficients
rot_range = np.arange(11,13.377000,0.000050) #range of prism rotation degrees
fit_curve = [float("{:.2f}".format(poly(x))) for x in rot_range] #generates the wavelength values for the polynomial function


def set_wavelength(PRISMSTAGENAME, target_y):  
  spec = Spectrometer.from_first_available() #instantiate spec object 
  spec.integration_time_micros(100000)
  with GCSDevice(PRISMSTAGENAME) as pidevice:
    pidevice.ConnectRS232(comport = com_port_num, baudrate= baud_rate_num) #establish communication with prism stage rotator
    # pidevice.InterfaceSetupDlg()
    axis = 1
    PI_prev_pos = pidevice.qPOS(axis)[axis] #query the current position of the prism
    print('current position of prism is {:.6f}'.format(PI_prev_pos))   
    index = np.where(np.isclose(fit_curve, target_y, atol = 0.05)) #finds the index of the closest value to the target wavelength
    index = index[0][0]
    print('prism stage moving to ', rot_range[index], 'deg')
    pidevice.MOV(axis, rot_range[index])
    time.sleep(2)
    w = spec.wavelengths()
    intens = spec.intensities()
    print(w[np.argmax(intens)])    
    plt.plot(w,intens)    
        
    spec.close()
    
     #moves the prism to the position where the fiber selects the target wavelength
    # return rot_range[index[0][0]]
  
  # return x_range[index[0][0]], fit_curve, index[0][0] 

# a, fit_curve, loc = set_wavelength(PRISMSTAGENAME,float(target_lambda))
# print(a)
# print(fit_curve[loc])
for iwav in [700, 800, 850]:
    set_wavelength(PRISMSTAGENAME, iwav)

# recalibrate(PRISMSTAGENAME, 100000)

#%%
###############################################################################################
# lam_arr = np.arange(700,800,20)
# PRISMSTAGENAME = 'C-863.11'
# com_port_num = 3
# baud_rate_num = 115200

# for ilam in lam_arr:
#     irot = set_wavelength(PRISMSTAGENAME, ilam)
#     spec = Spectrometer.from_first_available() #instantiate spec object 
#     spec.integration_time_micros(100000) #set integration time of spectrometer
#     with GCSDevice(PRISMSTAGENAME) as pidevice:
#       pidevice.ConnectRS232(comport = com_port_num, baudrate= baud_rate_num)
#       axis = 1  
#       position = pidevice.MOV(axis,irot) #move the prism to the i position
#       print('Current position of prism: ', position, 'deg')
#       wave_arr = spec.wavelengths() #acquire wavelengths
#       intensity_arr = spec.intensities() #acquire intensities
#       plt.plot(wave_arr,intensity_arr)
#       spec.close()
####################################################################################################

# def set_wavelength(PRISMSTAGENAME, target_y):
#   with open("persistent_data.pkl", "rb") as f:
#     coefficients = pickle.load(f)
#   poly = np.poly1d(coefficients) #generates the polynomial function with the coefficients
#   spec = Spectrometer.from_first_available() #instantiate spec object 
#   spec.integration_time_micros(100000)
#   with GCSDevice(PRISMSTAGENAME) as pidevice, Thorlabs.KinesisMotor(ATTMOTORNUM) as stage:
#     stage.setup_velocity(0, 20000, 40000,  scale=True)
#     pidevice.ConnectRS232(comport = com_port_num, baudrate= baud_rate_num) #establish communication with prism stage rotator
#     # pidevice.InterfaceSetupDlg()
#     axis = 1
#     PI_prev_pos = pidevice.qPOS(axis)[axis] #query the current position of the prism
#     print('current position of prism is {:.6f}'.format(PI_prev_pos))
#     rot_range = np.arange(11,13.377000,0.000050) #range of prism rotation degrees
#     fit_curve = [float("{:.2f}".format(poly(x))) for x in rot_range] #generates the wavelength values for the polynomial function
#     index = np.where(np.isclose(fit_curve, target_y, atol = 0.05)) #finds the index of the closest value to the target wavelength
#     index = index[0][0]
#     print('index ', index)
#     stage.move_to(1919* startpos)
#     stage.wait_move()
#     istageval = stage.get_position()
#     istage = istageval/1919
#     print('prism stage moving to ', rot_range[index], 'deg')
#     pidevice.MOV(axis, rot_range[index])
#     time.sleep(2)
#     while istage < Attthrshld:
#         intensities = spec.intensities()
#         max_in = np.max(intensities)
#         print(max_in)
#         if max_in < Low_Thres:
#             stage.move_by(1919*ideg)
#             stage.wait_move()
#             istage = istage + ideg
#             cur_pos = stage.get_position()
#             print('Low intensity: changing attenuator position to ', cur_pos/1919, ' Degrees')
#             time.sleep(3)
#         elif max_in >= High_Thres:
#             stage.move_by(-1919*ideg)
#             stage.wait_move()

#             istage = istage - ideg
#             cur_pos = stage.get_position()
#             print('High intensity: changing attenuator position to ',  cur_pos/1919, ' Degrees')
#             time.sleep(3)
#         else:
#             stage.wait_move()
#             break
        
#     w = spec.wavelengths()
#     intens = spec.intensities()
#     print(w[np.argmax(intens)])    
#     plt.plot(w,intens)    
        
#     spec.close()

#################################################################################################################