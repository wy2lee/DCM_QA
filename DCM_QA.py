#!/usr/bin/python

# Supervisor QA program for OBI-POND data
#   Checks and prepares DICOM data for upload to BRAINCODE

#    File Name:  DCM_QA.py
#
#    NOTES - WL - 13/07/04 - Initial Creation
#
#   AUTHOR - Wayne Lee, Daniel Cassel
#   Created - 2013/07/04
#   REVISIONS 

#       A - 2013-07-04 - WL - Original Creation, loose class and function definitions
#       B - 2013-10-21 - WL - Default tolerance for numbers is 1% unless otherwise specified
#       C - 2015-03-19 - WL - Added to GitHub


# NOTES
#     1) Program may get confused and generate errors for interpolated images stored in MOSAIC format
#        - Acquisition Matrix will properly capture actual k-space matrix
#        - Rows / Cols specifies reconnstructed image matrix
#        - In the case of MOSAIC Rows/Cols will also be multiplied by the 'montage' view
#     2) BATCH CALL
#   for dir in /data8/mrdata/MR160/MR160-*-*; do echo ${dir}; echo ${dir} >> QA_log.txt; ./POND_QA.py ${dir} >> QA_log.txt ; done
#     3) Should this program check all dicoms?
#        - Right now just checks first and last to make sure stuff makes sense


from optparse import OptionParser, Option, OptionValueError
import datetime
import string
import glob
import os, shlex, subprocess
import numpy

program_name = 'POND_QA.py'

#*************************************************************************************
# FUNCTIONS

# General utility function to call system commands
def run_cmd(sys_cmd, debug, verbose):
# one line call to output system command and control debug state
    if verbose:
        print sys_cmd
    if not debug:
        p = subprocess.Popen(sys_cmd, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, errors = p.communicate()
        return output, errors
    else:
        return '','' 
        
        
# Load subject list from text file
def load_MR_params(fname_scan_params, subj_name, subj_id):
#
# Scan_params.cfg
# Metadata file for POND_QA.py
#  "|" separates fields
#  "," separates allowable values for a given field
#  "-" denotes ranges for a field
#  "NULL" denotes field is not checked
# SPACES and empty lines are ignored
#
#   First Line = field headers **** 13/07/05 WL - for now these are hard coded 
#
# |   scan_type   |   TR   |   TE   |   TI   |   FA   |  ORIENT  |  FOV_X  |  FOV_Y  |  FOV_Z  |  RES_X  |  RES_Y  |  RES_Z  | SLICE_GAP |
# | T1-SAG-MPRAGE |  2300  |  2.96  |   900  |    9   |   SAG    |   192   |   240   |   256   |   192   |   240   |   256   |     0     |
# | T2-AX-TSE     |  9000  |  104   |   NULL |  120   |   AX     |   192   |   230   |   154   |   160   |   192   |   128   |     0     |
    
    if not os.path.exists(fname_scan_params):
        raise SystemExit, 'ERROR - Parameter File - File not found: %s' % (fname_scan_params,) 

    f = open(fname_scan_params,'r')
    line_count = 0;

    lut_dcm_hdr  = {}
    lut_ID_fields = {}
    
    # General DICOM headers
        # 0020,0037 {Image Orientation Patient) vector specifying in-plane orientation
        # Direction cosines for ROW (x,y,z) followed by COLUMN (x,y,y), relative to LPS
        # [row_x, row_y, row_z, cos_x, cos_y, cos_z]
        # AXIAL = [1\0\0\0\1\0 ],  ie. Row is along X, Column is along Y
        # SAG = [0\1\0\0\0\-1]  ie. Row is along Y, Column is along Z

    lut_dcm_hdr['StudyDate'] = '0008,0020'
    lut_dcm_hdr['StudyTime'] = '0008,0030'
    
    # Patient information DCM header fields
    lut_dcm_hdr['PatientName'] = '0010,0010'
    lut_dcm_hdr['PatientID'] = '0010,0020'
    lut_dcm_hdr['PatientBirthDate'] = '0010,0030'
    lut_dcm_hdr['PatientSex'] = '0010,0040'
    lut_dcm_hdr['PatientAge'] = '0010,1010'
    lut_dcm_hdr['PatientSize'] = '0010,1020'
    lut_dcm_hdr['PatientWeight'] = '0010,1030'
    lut_dcm_hdr['PatientTelephoneNumbers'] = '0010,2154'
    
    # Patient information target values
    lut_ID_fields['PatientName'] = subj_name
    lut_ID_fields['PatientID'] = subj_name + '-' + subj_id
    lut_ID_fields['PatientBirthDate'] = '19900101'
    lut_ID_fields['PatientSex'] = '0'
    lut_ID_fields['PatientAge'] = '0'
    lut_ID_fields['PatientSize'] = '0'
    lut_ID_fields['PatientWeight'] = '0'
    lut_ID_fields['PatientTelephoneNumbers'] = '0'
    
    # Scan information
    lut_dcm_hdr['ImageType'] = '0008,0008'
    lut_dcm_hdr['SeriesDescription'] = '0008,103e'
    lut_dcm_hdr['SeriesNum'] = '0020,0011'
    lut_dcm_hdr['AcquisitionNumber'] = '0020,0012'
    lut_dcm_hdr['InstanceNumber'] = '0020,0013'
    lut_dcm_hdr['TR'] = '0018,0080'
    lut_dcm_hdr['TE'] = '0018,0081'
    lut_dcm_hdr['TI'] = '0018,0082'
    lut_dcm_hdr['AcquisitionMatrix'] = '0018,1310'
    lut_dcm_hdr['FA'] = '0018,1314'
    lut_dcm_hdr['ImageOrient'] = '0020,0037'
    lut_dcm_hdr['Rows'] = '0028,0010'
    lut_dcm_hdr['Cols'] = '0028,0011'
    lut_dcm_hdr['PhaseDir'] = '0018,1312'
    lut_dcm_hdr['PixelSpacing'] = '0028,0030'
    lut_dcm_hdr['SliceThick'] = '0018,0050'
    lut_dcm_hdr['SliceSpace'] = '0018,0088'
    lut_dcm_hdr['SliceLocation'] = '0020,1041'
    lut_dcm_hdr['MOSAIC_slices'] = '0019,100a'

    lut_scans = {}
    for line in f:
        line_count = line_count + 1
        if not (line.startswith('#') or len(line.strip('\n'))==0):              # ignore header and blank lines
            line_values = "".join(line.split()).split('|') #line.strip(' ').split('|')
            if line_values[1]=='scan_type':
                line_headers = line_values;
            if not line_values[1]=='scan_type':
                lut_scans[line_values[1]]  = {};
                for count_hdr in range(1,(len(line_values)-2) ):
                    if line_values[count_hdr+1].find('-')>-1:
                        lut_scans[line_values[1]] [line_headers[count_hdr+1]] = {}
                        lut_scans[line_values[1]] [line_headers[count_hdr+1]]['min'] = line_values[count_hdr+1].split('-')[0]
                        lut_scans[line_values[1]] [line_headers[count_hdr+1]]['max'] = line_values[count_hdr+1].split('-')[1]
                    elif line_values[count_hdr+1].find(',')>-1:
                        lut_scans[line_values[1]] [line_headers[count_hdr+1]] = line_values[count_hdr+1].split(',')
                    else:
                        lut_scans[line_values[1]] [line_headers[count_hdr+1]] = line_values[count_hdr+1]
                    
    return lut_scans, lut_dcm_hdr, lut_ID_fields

def get_dcm_value(full_name_dcm, lut_tags):
    valid_chars = '-_%s%s' % (string.ascii_letters, string.digits)

    # Create string of tags to find 
    cmd_tags = '+P 0008,0070'       # Manufacturer tag)
    for curr_tag in lut_tags:
        cmd_tags = "%s +P %s" % (cmd_tags, lut_tags[curr_tag])
    
    # Probe dicom header  for values
    cmd_dcmdump = 'dcmdump +L %s %s' % (cmd_tags, full_name_dcm)
    output, errors = run_cmd(cmd_dcmdump,0, 0)
    # print cmd_dcmdump, output, errors
    
    # extract dcm tag values from OUTPUT
    tag_values = {}
    for curr_tag in lut_tags:
        curr_tag_start = output.find(lut_tags[curr_tag])
        if curr_tag_start > -1:   # Value is in header, find location of closest [ and ]
            if curr_tag.find('AcquisitionMatrix')>-1 or curr_tag.find('Rows')>-1 or curr_tag.find('Cols')>-1 or \
                (curr_tag.find('MOSAIC_slices')>-1 ):    
            # No [ ] around values
                tag_values[curr_tag] = output[curr_tag_start:curr_tag_start+40].split(' ')[2]
            else:
                tag_start = output.find('[',curr_tag_start) +1
                tag_stop = output.find(']',curr_tag_start)
                tag_values[curr_tag] = output[tag_start:tag_stop]
        else:     # value is not in header
            tag_values[curr_tag] = "NULL"

    return tag_values


def get_FOV_RES(tag_values, num_dcm, params_out):
# Function to determine orientation (rough), fov, and resolution based on dcm header info

    # If no SliceSpace field, make slicespace equal slice thicknes
    if tag_values['first']['SliceSpace'].find('NULL')>-1:
        tag_values['first']['SliceSpace'] = tag_values['first']['SliceThick']

        
        
    if tag_values['first']['ImageType'].find('MOSAIC')>-1:
        params_out['NUM_VOL'] = len(list_files_curr_scan)
        num_slices = int(tag_values['first']['MOSAIC_slices'])
        rows = max(int(tag_values['first']['AcquisitionMatrix'].split('\\')[0]), \
            int(tag_values['first']['AcquisitionMatrix'].split('\\')[1]))
        cols = max(int(tag_values['first']['AcquisitionMatrix'].split('\\')[2]), \
            int(tag_values['first']['AcquisitionMatrix'].split('\\')[3]))
    else:
        params_out['NUM_VOL'] = int(tag_values['last']['AcquisitionNumber'])
        num_slices = num_dcm / int(tag_values['last']['AcquisitionNumber'])
        rows = tag_values['first']['Rows']
        cols = tag_values['first']['Cols']

# First need to figure out slice direction 
    dircos_row = numpy.array([float(tag_values['first']['ImageOrient'].split('\\')[0]),\
        float(tag_values['first']['ImageOrient'].split('\\')[1]),\
        float(tag_values['first']['ImageOrient'].split('\\')[2])])
    dircos_col = numpy.array([float(tag_values['first']['ImageOrient'].split('\\')[3]),\
        float(tag_values['first']['ImageOrient'].split('\\')[4]),\
        float(tag_values['first']['ImageOrient'].split('\\')[5])])
    # Slices are in the direction with no in-plane vector (ie. lowest absolute direction cosine)
    slice_dir_index = numpy.argmin(abs(dircos_row) + abs(dircos_col))

    pixel_size_row = float(tag_values['first']['PixelSpacing'].split('\\')[0])
    pixel_size_col = float(tag_values['first']['PixelSpacing'].split('\\')[1])
        
    if slice_dir_index==0:
        params_out['ORIENT'] = "SAG"
        dir_slice = 'X'
        if dircos_row.argmax==1:      # ROW is in Y direction
            dir_row = 'Y'
            dir_col = 'Z'
        else:
            dir_row = 'Z'
            dir_col = 'Y'
    elif slice_dir_index==1:
        params_out['ORIENT'] = "COR"
        dir_slice = 'Y'
        if dircos_row.argmax==0:      # ROW is in X direction
            dir_row = 'X'
            dir_col = 'Z'
        else:
            dir_row = 'Z'
            dir_col = 'X'
    else:
        params_out['ORIENT'] = "AX"
        dir_slice = 'Z'
        if dircos_row.argmax==0:      # ROW is in X direction
            dir_row = 'X'
            dir_col = 'Y'
        else:
            dir_row = 'Y'
            dir_col = 'X'
            
    params_out['RES_' + dir_slice] = int(num_slices)
    params_out['RES_' + dir_row] = rows 
    params_out['RES_' + dir_col] = cols
    params_out['SLICE_GAP'] = round(float(tag_values['first']['SliceSpace']) - float(tag_values['first']['SliceThick']),1)
    params_out['FOV_' + dir_slice] = round(num_slices * float(tag_values['first']['SliceSpace']),1)
    params_out['FOV_' + dir_row] = round(float(params_out['RES_' + dir_row])*pixel_size_row,1)  
    params_out['FOV_' + dir_col] = round(float(params_out['RES_' + dir_col])*pixel_size_col,1)  
    params_out['TR'] = float(tag_values['first']['TR'])
    params_out['TE'] = float(tag_values['first']['TE'])
    params_out['FA'] = float(tag_values['first']['FA'])    
    if tag_values['first']['TI'].find('NULL')>-1:
        params_out['TI'] = tag_values['first']['TI']
    else:
        params_out['TI'] = float(tag_values['first']['TI'])    
    
    return params_out


def check_patient_info(tag_values, lut_ID_fields, SCAN_PASS, SCAN_LOG):
    for ID_field in lut_ID_fields:
        if tag_values[ID_field] != lut_ID_fields[ID_field]:
            SCAN_PASS = 0
            SCAN_LOG = SCAN_LOG + ['        [%s] : %s != %s : FAIL' % \
                    (ID_field, lut_ID_fields[ID_field], tag_values[ID_field]) ]
    return SCAN_PASS, SCAN_LOG


def check_scan_type(dir_curr_scan_clean, scan_type):
# Function to check if current scan needs to be QA's
    list_ignore = ['_ADC','_TRACEW','_FA','_ColFA']   # processed DTI scans to ignore

    QA_THIS_SCAN = 1
    list_scan_type = scan_type.split(',')
    # make sure all keywords present in directory name
    for scan_keywords in list_scan_type:
        if dir_curr_scan_clean.find(scan_keywords)<0:
            QA_THIS_SCAN = 0
            
    # make sure all ignore words are absent in directory name
    for ignore_keywords in list_ignore:
        if dir_curr_scan_clean.find(ignore_keywords)>-1:
            QA_THIS_SCAN = 0

    # ignore any scan with the following keywords
            
    return QA_THIS_SCAN
    
if __name__ == '__main__' :
    usage = "Usage: "+program_name+" <options> subject_name subject_id subject_directory\n"+\
            "   or  "+program_name+" -help";
    parser = OptionParser(usage)
    parser.add_option("-c","--clobber", action="store_true", dest="clobber",
                        default=0, help="overwrite output file")
    parser.add_option("--TOL", type="float", dest="TOL",
                        default = 0.01,help="Allow tolerance on numerical values (Default = 1%)")
    parser.add_option("-d","--debug", action="store_true", dest="debug",
                        default=0, help="Run in debug mode")
    parser.add_option("--sp", type="string", dest="fname_scan_params",
                        default="scan_params.cfg", help="Acceptable scan parameters[default = scan_params.cfg]")
    parser.add_option("-e", "--ext",type="string", dest="ext_type",
                        default="dcm,DCM,ima,IMA", help="Allowable dicom file extension [default = dcm,DCM,ima,IMA]")
    parser.add_option("-v","--verbose", action="store_true", dest="verbose",
                        default=0, help="Verbose output")
    # parser.add_option("--pinfo", type="string", dest="pinfo",
                        # help="File containing processing parameters")
    # parser.add_option("--info", type="string", dest="info",
                        # help="File containing data + processing parameters (mutually exclusive from dinfo, pinfo)")
    # parser.add_option("--tempdir", type="string", dest="tempdir",
                        # default = "/tmp", help="Base location for temporary directory [default =/tmp], creates a directory a unique directory 'asl??????'")
    # parser.add_option("--keeptemp", action="store_true", dest="keeptemp",
                        # default=0, help="Keep temporary directory")
#    parser.add_option("--TR", type="float", dest="TR",
#                        default = 3.9,help="TR of Ax SPGR images [ms] (Default = 3.9)")
#    parser.add_option("--mse", type="string", dest="mse",
#                        help="Optional mean squared error output")
#    parser.add_option("--fill_off", action="store_true", dest="fill_off",
#                        default=0, help="Turn off autofill which replaces -'ve slope or -T1 values with inplane local average")

# # Parse input arguments and store them
    options, args = parser.parse_args()     
        
# # Example of checking for proper number of arguments
    if len(args) != 3:
        parser.error("incorrect number of arguments")
    
    subj_name, subj_id, dir_subj_in = args

    
    list_dir_scan = os.listdir(dir_subj_in)
    list_dir_scan.sort()
    num_dir_scan = len(list_dir_scan)
   
    if dir_subj_in[-1] == '/':
        dir_subj_in = dir_subj_in[0:len(dir_subj_in)-1]

    lut_scans, lut_dcm_hdr, lut_ID_fields = load_MR_params(options.fname_scan_params, subj_name, subj_id)
    
    for dir_curr_scan in list_dir_scan:
        dir_curr_scan_clean = dir_curr_scan.replace('-','_')   # remove variability of - or _
        
        SCAN_PASS = 1 # RESET SCAN PASS BOOLEAN
        SCAN_LOG = []
        tag_values = {}
        for scan_type in lut_scans:
            scan_type = scan_type.replace('-','_')
            
            QA_THIS_SCAN = check_scan_type(dir_curr_scan_clean, scan_type)
            # Check scan type
            
            if QA_THIS_SCAN:
                # ignore ADC, TRACEW, FA, ColFA scans
                
                fdir_curr_scan = "%s/%s" % (dir_subj_in , dir_curr_scan)
                
            # Check number of dicoms / mosaic format / number of slices
                list_files_curr_scan = []
                for ext_type in options.ext_type.split(','):
                    list_files_curr_scan = list_files_curr_scan + glob.glob(fdir_curr_scan + '/*.' + ext_type)
                list_files_curr_scan.sort()
                num_dcm = len(list_files_curr_scan)
                # Pull dicom header values of potential interest
                tag_values['first'] = get_dcm_value(list_files_curr_scan[0], lut_dcm_hdr)
                tag_values['last']  = get_dcm_value(list_files_curr_scan[-1], lut_dcm_hdr)
                
                # Extract parameters of interest from dicom header                
                params_out = {}
                params_out = get_FOV_RES(tag_values, num_dcm, params_out)
                
                # Check patient info
                SCAN_PASS, SCAN_LOG = check_patient_info(tag_values['first'], lut_ID_fields, SCAN_PASS, SCAN_LOG)
                
                # Check parameters to see if match range
                for param_field in params_out:
                    # Numerical Header field
                    param_PASS = 0;
                    if type(params_out[param_field]) in [float,int]:
                        if type(lut_scans[scan_type][param_field]) is dict:
                            # Min / Max values
                            param_min = lut_scans[scan_type][param_field]['min']
                            param_max = lut_scans[scan_type][param_field]['max']
                            if (float(params_out[param_field]) >= float(lut_scans[scan_type][param_field]['min']) ) and \
                                (float(params_out[param_field]) <= float(lut_scans[scan_type][param_field]['max'] )):
                                param_PASS = 1
                        elif type(lut_scans[scan_type][param_field]) is list:
                            # List of Values
                            param_diff = abs(float(params_out[param_field]))
                            for param_value in lut_scans[scan_type][param_field]:
                                param_diff = min(param_diff, abs(float(params_out[param_field]) - float(param_value)))

                            if (param_field.find('RES')>-1 and param_diff == 0) or \
                                 (param_field.find('RES')<0 and param_diff < max(options.TOL * float(params_out[param_field]), options.TOL)):
                                # Resolution must be exact unless MIN/MAX values have been specified
                                param_PASS = 1
                        else:
                            param_diff = abs(float(params_out[param_field]) - float(lut_scans[scan_type][param_field]))
                            if (param_field.find('RES')>-1 and param_diff == 0) or \
                                 (param_field.find('RES')<0 and param_diff < max(options.TOL * float(params_out[param_field]), options.TOL)):
                                # Resolution must be exact unless MIN/MAX values have been specified
                                param_PASS = 1
                    elif  type(params_out[param_field]) in [str]:
                        # STRING based header
                        if params_out[param_field] in lut_scans[scan_type][param_field]:
                            param_PASS = 1
                        
                    if not param_PASS:
                        SCAN_PASS = 0
                        SCAN_LOG = SCAN_LOG + ['        [%s] : %s != %s : FAIL' % \
                            (param_field, lut_scans[scan_type][param_field], params_out[param_field] ) ]
                    elif options.verbose:
                        SCAN_LOG = SCAN_LOG + ['        [%s] : %s == %s : PASS' % \
                            (param_field, lut_scans[scan_type][param_field], params_out[param_field] ) ]
                        

                if SCAN_PASS:
                    print '    %s - PASS' % (dir_curr_scan,)
                else:
                    print '    %s - FAIL' % (dir_curr_scan,)
                    for line in SCAN_LOG:
                        print line
