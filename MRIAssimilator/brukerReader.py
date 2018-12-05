#!/usr/bin/env python3

#from numpy import set_printoptions, array, zeros, asarray, amax, int, dtype, fabs, fromfile, prod, size, reshape, nan, array2string
import numpy as np
import re
import os
import utils

from brukerData import BrukerData

np.set_printoptions(precision=5)

def ReadDirectory(fpath):
    """
Reading directory according to the fpath and return a dictionary of files:

AllFiles{EXPNAME1 : {EXPNUM1 : [list of files], EXPNUM2 : [list of files], ..., 
                                                OTHER : [list of files]},
         EXPNAME2 : {EXPNUM1 : [list of files], EXPNUM2 : [list of files], ..., 
                                                OTHER : [list of files]},
         ...}

    """
    AllFiles = {}
    files_list = []
    expname = ""
    exp_number = ""
    common_files = {}
    end = 0
    inpdata = 0
    makesubnum = 0
    for path_to_file, subdirs, files in os.walk(fpath):

        if makesubnum:
            subnum = re.findall(r"pdata\\(\d+)$", path_to_file)
            if subnum:                
                exp_number = expnum + "." + subnum[-1]
                end = 1

        # if there is more then 1 data files in exp_num
        if inpdata:
            makesubnum = len(subdirs) > 1
            if not makesubnum:
                exp_number = expnum                
                end = 1
            else:
                common_files = files_list[:]
            inpdata = 0

        if "pdata" in subdirs:
            exp_tuple = re.findall(r'([^\\]+) \\ (\d+) $',
                                   path_to_file, re.X)[0]
            expname = exp_tuple[0]
            expnum = exp_tuple[1]
            if expname not in AllFiles.keys():
                AllFiles[expname] = {}

            inpdata = 1

        for name in files:
            if not set(["acqp", "2dseq"]).isdisjoint(files):
                files_list.append(os.path.join(path_to_file, name))

        if "2dseq" in files and end:
            end = 0
            if not set(common_files).issubset(files_list):
                files_list += common_files
            AllFiles[expname][exp_number] = files_list
            files_list = []
    return check_dict(AllFiles)

def ReadExperiment(files_dict, ExpNum, ExpName = ""):
    """
Read in a Bruker MRI Experiment. Returns raw data, processed data, 
and method, acqp and visu_pars parameters in a dictionary.

    """ 
    try:
        data = BrukerData(os.path, ExpNum, ExpName)
        # parameter files as dictionaries
        data.method = \
                ReadParamFile(PathToFile(files_dict, "method", ExpNum, ExpName))
        data.acqp = \
                ReadParamFile(PathToFile(files_dict, "acqp", ExpNum, ExpName))
        data.visu = \
                ReadParamFile(PathToFile(files_dict, "visu_pars", ExpNum, ExpName))

        data.d3proc = \
                ReadParamFile(PathToFile(files_dict, "d3proc", ExpNum, ExpName))

        # processed data
        data.IntenseData = \
                ReadProcessedData(PathToFile(files_dict, "2dseq", ExpNum, ExpName),
                                  data.visu, data.d3proc,
                                  data.acqp, ExpNum, ExpName)

        data.max_val = np.amax(data.IntenseData)
        data.min_val = np.amin(data.IntenseData)
        data.Dimension = np.asarray(data.IntenseData.shape)

        data.ROI = data.visu["VisuCoreExtent"]

        data.path = os.path
        data.ExpNum = ExpNum

        return data

    except Exception as err:
        utils.logger.warning(err)
        #utils.logger.exception(err)
        return None

def ReadParamFile(filepath):
    """
Read a Bruker MRI experiment's method or acqp file to a dictionary.
    """
    param_dict = {}
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            for line in file:

                # when line contains parameter
                if line.startswith('##$'):

                    (param_name, current_line) = line[3:].split('=') # split at "="

                    # if current entry (current_line) is arraysize
                    if current_line[0:2] == "( " and current_line[-3:-1] == " )":
                        value = ParseArray(file, current_line)

                    # if current entry (current_line) is struct/list
                    elif current_line[0] == "(" and current_line[-3:-1] != " )":

                        # if neccessary read in multiple lines
                        while current_line[-2] != ")":
                            current_line = current_line[0:-1] + file.readline()

                        # parse the values to a list
                        value = [ParseSingleValue(x)
                                 for x in current_line[1:-2].split(', ')]

                    # otherwise current entry must be single string or number
                    else:
                        value = ParseSingleValue(current_line)

                    # save parsed value to dict
                    param_dict[param_name] = value
        param_dict["path_to_file"] = filepath
    return param_dict

def ReadProcessedData(filepath, visu, d3proc, acqp, ExpNum, ExpName):
    """
Read the data of images from file "2dseq"
    """
    with open(filepath, "r") as f:
        
        np_type, [img_bit,_,_] = ImageBitType(visu, d3proc)
        data = np.fromfile(f, dtype=np_type)

        mn = np.amin(data)
        if mn < 0:
            utils.logger.info("There is a negative minimal value = '{0}' in {1}/{2}".format(mn, ExpName, ExpNum))

        if visu:
            if visu["VisuCoreDim"] == 1:
                raise Exception("\"VisuCoreDim\" is equal 1 in the \'visu_pars\' data in {0}/{1}".format(ExpName, ExpNum))

            data = data.reshape(-1, visu["VisuCoreSize"][0], visu["VisuCoreSize"][1])
        elif d3proc:
            data = data.reshape(-1, d3proc['IM_SIX'], d3proc['IM_SIY'])
        return data

def PathToFile(files_dict, filename = "", ExpNum = 0, ExpName = ""):
    """
Find path to "filename" in the "files_dict".

"ExpNum" indicates the certain number of experiment, if no number is specified, 
then the first number in the dictionary is selected.

"ExpName" indicates the certain name of experiment, if no name is specified, 
then the first name in the dictionary is selected.
    """
    if not ExpName:
        ExpName = list(files_dict.keys())[0]

    elif ExpName not in list(files_dict.keys()):
        try:
            raise ValueError
        except ValueError:
            utils.logger.warning("No such name of the experiment")

    if not ExpNum:
        ExpNum = list(files_dict[ExpName].keys())[0]

    elif str(ExpNum) not in list(files_dict[ExpName].keys()):
        try:
            raise ValueError
        except ValueError:
            utils.logger.warning("No such number corresponding to the experiment")

    files = files_dict[ExpName][str(ExpNum)]
    try:
        for file in files:
            if file.find(filename) != -1:
                return file
        raise FileNotFoundError

    except FileNotFoundError:
        utils.logger.warning("Can't find such file '{0}' in {1}/{2}".format(filename, ExpName, ExpNum))
        return ''

def ParseArray(current_file, line):

    # extract the arraysize and convert it to numpy
    line = line[1:-2].replace(" ", "").split(",")
    arraysize = np.array([int(x) for x in line])

    # then extract the next line
    vallist = current_file.readline().split()

    # if the line was a string, then return it directly
    try:
        float(vallist[0])
    except ValueError:
        return " ".join(vallist)

    # include potentially multiple lines
    while len(vallist) != np.prod(arraysize):
        vallist = vallist + current_file.readline().split()

    # try converting to int, if error, then to float
    
    try:
        vallist = [int(x) for x in vallist]
    except ValueError:
        vallist = [float(x) for x in vallist]

    # convert to numpy array
    if len(vallist) > 1:
        if np.size(arraysize) > 1 and arraysize[1] == 9:
            arraysize = np.array([arraysize[0], 3, 3])

        return np.reshape(np.array(vallist),
                          arraysize[1:] if arraysize[0] == 1 else arraysize)
    # or to plain number
    else:
        return vallist[0]

def ParseSingleValue(val):

    try: # check if int
        result = int(val)
    except ValueError:
        try: # then check if float
            result = float(val)
        except ValueError:
            # if not, should  be string. Remove  newline character.
            result = val.rstrip('\n')

    return result

def ImageBitType(visu, d3proc):
    """
Return bitness of the image in the format as "intBIT"(for example "int16")
    """
    # Return list of the values from VisuCoreWordType:
    # visuType = [(numBIT, SGN/UNSGN, TYPE)]
    img_bit = 16
    img_sgn = "sgn"
    img_type = "int"

    if visu:
        visuType = re.findall('[^_]+', visu["VisuCoreWordType"])
        img_bit = int(visuType[0].replace("BIT", ""))

        if len(visuType) == 3:
            img_sgn = visuType[1].lower()
            img_type = visuType[2].lower()
        else: # if no SGN is specified
            img_type = visuType[1].lower()
            img_sgn = None

    elif d3proc:
        # get size of the '2dseq' file in byte
        dseq_path = d3proc["path_to_file"].replace("d3proc","2dseq")
        dseq_size = os.stat(dseq_path).st_size

        img_bit = int(dseq_size * 8 / (d3proc['IM_SIX'] * d3proc['IM_SIY'] * d3proc['IM_SIZ']))

    if img_type == "int":
        numpy_type = '{0}{1}'.format(img_type if img_sgn == "sgn" else 'uint', img_bit)
    else:
        numpy_type = '{0}{1}'.format(img_type, img_bit)

    return np.dtype(numpy_type), [img_bit, img_sgn, img_type]

def check_dict(AllFiles):
    """
Find uncorrect data in AllFiles and remove it
    """
    import collections

    for exp_name in list(AllFiles.keys()):

        for exp_num in list(AllFiles[exp_name].keys()):
            if not AllFiles[exp_name][exp_num]:
                utils.logger.warning("There is no '2dseq' data in {0}\{1}".format(exp_name, exp_num))
                del AllFiles[exp_name][exp_num]

        AllFiles[exp_name] = utils.sort_dict(AllFiles[exp_name])

        if not AllFiles[exp_name]:
            utils.logger.warning("There is no any experiments with '2dseq' data in {}".format(exp_name))
            del AllFiles[exp_name]

    return AllFiles

def CorrectBrukerData(data):
    _, [img_bit, _, _] = ImageBitType(data.visu, data.d3proc)
    dim = 2**(img_bit)
    return np.where(data.IntenseData < 0, data.IntenseData + dim, data.IntenseData)
