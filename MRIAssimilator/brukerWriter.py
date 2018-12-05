#!/usr/bin/env python3

import numpy as np

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

def HeaderForTextFile(file, data):

    file.write("Dimension == {0}\n".format(data.Dimension))
    file.write("Resolution == {0}\n".format(data.Resolution()))
    file.write("SliceDistance == {0}\n".format(data.SliceDistance()))
    file.write("LeftTopCoordinates == {0}\n".format(data.LeftTopCoordinates()))
    file.write("SliceOrientation == \n{0}\n".format(data.SliceOrientation()))
    file.write("ImageWordType == {0}\n".format(data.ImageWordType()))
    file.write("IntenseData == \n")

def ShellForXMLWrite(data):
    root = etree.Element('data')

    dim = etree.SubElement(root, "tag", name="Dimension")
    etree.SubElement(dim, "x").text = str(data.Dimension[1])
    etree.SubElement(dim, "y").text = str(data.Dimension[2])
    etree.SubElement(dim, "z").text = str(data.Dimension[0])

    if data.Resolution().any():
        res = etree.SubElement(root, "tag", name="Resolution")
        etree.SubElement(res, "x").text = str(data.Resolution()[0])
        etree.SubElement(res, "y").text = str(data.Resolution()[1])

    if data.SliceDistance():
        etree.SubElement(root, "tag", name="SliceDistance").text = str(data.SliceDistance())

    if data.LeftTopCoordinates().any():
        ltc = etree.SubElement(root, "tag", name="LeftTopCoordinates")
        etree.SubElement(ltc, "x").text = str(data.LeftTopCoordinates()[0])
        etree.SubElement(ltc, "y").text = str(data.LeftTopCoordinates()[1])
        etree.SubElement(ltc, "z").text = str(data.LeftTopCoordinates()[2])

    if data.SliceOrientation().any():
        orient = etree.SubElement(root, "tag", name="SliceOrientation")
        etree.SubElement(orient, "v1").text = str(data.SliceOrientation()[0])
        etree.SubElement(orient, "v2").text = str(data.SliceOrientation()[1])
        etree.SubElement(orient, "v3").text = str(data.SliceOrientation()[2])

    etree.SubElement(root, "tag", name="ImageWordType").text = str(data.ImageWordType())

    return root

def SingleWriteToTextFile(fname, data = None, index = 0, create = False):
    """
Write the index number of the Image from data in a text file with FNAME nam
    """
    np.set_printoptions(threshold=np.nan)
    if create:
        file = open(fname, "w")
        HeaderForTextFile(file, data)        
    else:
        file = open(fname, "a")

    file.write('\n# Image = {0}\n'.format(index+1))
    file.write(np.array2string(data.IntenseData[index,:,:]))

    file.close()

def SingleWriteToXMLFile(fname, data = None, index = 0, create = False,):
    """
Write the index number of the Image from data in a XML file with FNAME name
    """
    np.set_printoptions(threshold=np.nan)

    if create:
        root = ShellForXMLWrite(data)

        img_data = etree.SubElement(root, "tag", name="IntenseData")
        
        elem = etree.SubElement(img_data, "image")
        elem.set("number", str(index + 1))
        elem.text = np.array2string(data.IntenseData[index,:,:])

        tree = etree.ElementTree(root)
    else:
        # add new Images in the old xml file

        tree = etree.parse(fname)
        xmlRoot = tree.getroot()
        elem = etree.SubElement(xmlRoot[-1], "image")
        elem.text = np.array2string(data.IntenseData[index,:,:])
        elem.set("number", str(index + 1))

    tree.write(fname)

def WriteToTextFile(fname, data):
    """
Write all Images from data in a text file with FNAME name
    """
    file = open(fname, "w")
    HeaderForTextFile(file, data)
    for i in range(data.Dimension[0]):
        file.write('\n# Image = {0}\n'.format(i+1))
        np.set_printoptions(threshold=np.nan)
        file.write(np.array2string(data.IntenseData[i,:,:]))
    file.close()

def WriteToXMLFile(fname, data):
    """
Write all Images from data in a XML file with FNAME name
    """
    root = ShellForXMLWrite(data)

    img_data = etree.SubElement(root, "tag", name="IntenseData")

    np.set_printoptions(threshold=np.nan)
    for i in range(data.Dimension[0]):
        etree.SubElement(img_data, "image{}".format(i)).text = np.array2string(data.IntenseData[i,:,:])

    brukerdata = etree.ElementTree(root)
    brukerdata.write(fname)
