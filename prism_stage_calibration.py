
import pickle
from pipython import GCSDevice
import numpy as np
import matplotlib.pyplot as plt
import time
from pipython import GCSDevice, pitools
import seabreeze
from seabreeze.spectrometers import Spectrometer

# y_data = [600, 650, 700, 750, 800, 850, 900]
# x_data = [12.498500, 12.204500, 11.976000, 11.792500, 11.643500, 11.518500, 11.413500] #prism rotation degrees
# degree = 3
# filename = 'persistent_data.pkl'
# coefficients = [float(f"{i:.6f}") for i in np.polyfit(x_data, y_data, degree)]
# with open(filename, "wb") as f:
#       pickle.dump(coefficients, f)
# poly = np.poly1d(coefficients)

PRISMSTAGENAME = 'C-863.11'
REFMODES = ['FRF']
com_port_num = 3
baud_rate_num = 115200
target_lambda = 1000
filename = 'persistent_data.pkl' #to save the coefficients even after running the code


###########################################
# acquires spectrum at different prism stage positions from 11 to 12 degrees in steps of 0.05 degrees (20 values)
# applies polynomial fit of degree 3 to the wavelength-rotation curve and computes the coefficients
# save the coefficients to a pickle file persistent_data.pkl (so that it can be used in future)
###########################################
def recalibrate(PRISMSTAGENAME, int_time_s):
  degree = 3
  rot_arr = np.arange(11,12,0.05)
  try:
    seabreeze.use('cseabreeze') #use cseabreeze backend
    spec = Spectrometer.from_first_available() #instantiate spec object 
    spec.integration_time_micros(int_time_s) #set integration time of spectrometer
    with GCSDevice(PRISMSTAGENAME) as pidevice:
      pidevice.ConnectRS232(comport = com_port_num, baudrate= baud_rate_num) #establish communication with prism stage rotator
      pidevice.InterfaceSetupDlg() 
    axis = 1  
    position = pidevice.qPOS(axis)[axis] 
    print('Current position of prism: ', position, 'deg')
    wavelength = np.array([]) # array to store the argument of max intensity from intensity array (basically the wavelengths)
    
    for i in rot_arr :
      pidevice.MOV(axis,i) #move the prism to the i position
      time.sleep(1) #wait for ___ s
      wave_arr = spec.wavelengths() #acquire wavelengths
      intensity_arr = spec.intensities() #acquire intensities
      m = np.argmax(intensity_arr) #find the index of the max intensity (thats the selected wavelength)
      wavelength = np.append(wavelength,wave_arr[m])  #append the selected wavelength to the array
    coefficients = [float(f"{i:.6f}") for i in np.polyfit(rot_arr, wavelength, degree)] #fit a polynomial curve of degree __ to the data
    spec.close() #close the spectrometer connection
    pidevice.CloseConnection()  #close the connection with the prism stage rotator
    with open(filename, "wb") as f: #save the coefficients to a pickle file so that it can be used in future (no recalibration needed)
      pickle.dump(coefficients, f)

  #shoots error messages if any exception occurs 
  except ValueError as e:
      error_message = str(e)
      return error_message
  except TypeError as e:
      error_message = str(e)
      return error_message
  except Exception as e:
      error_message = str(e)
      return error_message

####################################
# Here user can input the target wavelength and the prism stage rotates to a position where the fiber selects the target wavelength
####################################

def set_wavelength(PRISMSTAGENAME, target_y):
  with open("persistent_data.pkl", "rb") as f:
    coefficients = pickle.load(f)
  poly = np.poly1d(coefficients) #generates the polynomial function with the coefficients
  with GCSDevice(PRISMSTAGENAME) as pidevice:
    pidevice.ConnectRS232(comport = com_port_num, baudrate= baud_rate_num) #establish communication with prism stage rotator
    pidevice.InterfaceSetupDlg()
  axis = 1
  PI_prev_pos = pidevice.qPOS(axis)[axis] #query the current position of the prism
  print('previous position of prism is {:.6f}'.format(PI_prev_pos))
  rot_range = np.arange(10.268500,13.377000,0.000050) #range of prism rotation degrees
  fit_curve = [float("{:.2f}".format(poly(x))) for x in rot_range] #generates the wavelength values for the polynomial function
  index = np.where(np.isclose(fit_curve, target_y, atol = 0.05)) #finds the index of the closest value to the target wavelength
  pidevice.MOV(axis, rot_range[index[0][0]]) #moves the prism to the position where the fiber selects the target wavelength
  return rot_range[index[0][0]]
  # return x_range[index[0][0]], fit_curve, index[0][0] 

# a, fit_curve, loc = set_wavelength(PRISMSTAGENAME,float(target_lambda))
# print(a)
# print(fit_curve[loc])
set_wavelength(PRISMSTAGENAME, target_lambda)