import geopandas as gpd
import pandas as pd
import os
import subprocess
import shutil
from zipfile import ZipFile
from rasterio.merge import merge
import rasterio as rio
from glob import glob
import json
import csv
#import osgeo
#from osgeo import gdal
#from rasterio.crs import CRS
#import rasterio.mask
#from rasterio.wrap import calculate_default_transform, reproject, Resampling

# Define Data Paths
data_path = os.getenv('DATA_PATH', '/data')

# Define Input Paths
inputs_path = os.path.join(data_path,'inputs')
raster_path = os.path.join(inputs_path, 'rasters')
boundary_path = os.path.join(inputs_path,'boundary')
parameters_path = os.path.join(inputs_path, 'parameters')

# Define and Create Output Paths
outputs_path = os.path.join(data_path, 'outputs')
outputs_path_ = data_path + '/' + 'outputs'
if not os.path.exists(outputs_path):
    os.mkdir(outputs_path_)
dem_path = os.path.join(outputs_path, 'dem')
dem_path_ = outputs_path + '/' + 'dem'
if not os.path.exists(dem_path):
    os.mkdir(dem_path_)
parameter_outputs_path = os.path.join(outputs_path, 'parameters')
parameter_outputs_path_ = outputs_path + '/' + 'parameters'
if not os.path.exists(parameter_outputs_path):
    os.mkdir(parameter_outputs_path_)
boundary_outputs_path = os.path.join(outputs_path, 'boundary')
boundary_outputs_path_ = outputs_path + '/' + 'boundary'
if not os.path.exists(boundary_outputs_path):
    os.mkdir(boundary_outputs_path_)

# Look to see if a parameter file has been added
parameter_file = glob(parameters_path + "/*.csv", recursive = True)
print('parameter_file:', parameter_file)

# Identify the EPSG projection code
if len(parameter_file) == 1 :
    parameters = pd.read_csv(parameter_file[0])
    with open(parameter_file[0]) as file_obj:
        reader_obj = csv.reader(file_obj)
        for row in reader_obj:
            try:
                if row[0] == 'PROJECTION':
                    projection = row[1]
            except:
                continue
else:
    projection = os.getenv('PROJECTION')

# Identify input polygons and shapes (boundary of city)
boundary_1 = glob(boundary_path + "/*.*", recursive = True)
print('Boundary File:',boundary_1)

# Read in the boundary
boundary = gpd.read_file(boundary_1[0])

# Check boundary crs matches the projection
if boundary.crs != projection:
    boundary.to_crs(epsg=projection, inplace=True)

print('boundary_crs:', boundary.crs)

# Identify the name of the boundary file for the city name
file_path = os.path.splitext(boundary_1[0])
print('file_path:',file_path)
filename=file_path[0].split("/")
print('filename:',filename)
location = filename[-1]
print('Location:',location)

# Identify if the buildings are saved in a zip file
dem_files_zip = glob(raster_path + "/*.zip", recursive = True)
print(dem_files_zip)

# If yes, unzip the file (if the user has formatted the data correctly, this should reveal a .gpkg)
for i in range (0,len(dem_files_zip)):
    if len(dem_files_zip) != 0:
        print('zip file found')
        with ZipFile(dem_files_zip[i],'r') as zip:
            zip.extractall(raster_path)

# Identify geopackages containing the polygons of the buildings
raster_files = glob(raster_path + "/**/*.asc", recursive = True)

if len(raster_files) == 0:
    raster_files = glob(raster_path + "/**/*.tiff", recursive = True)

if len(raster_files) == 0:
    raster_files = glob(raster_path + "/**/*.tif", recursive = True)

print('raster_files:',raster_files)

# Merge the asc files to create one raster file for the chosen area
raster_to_mosiac = []

for p in raster_files:
    raster = rio.open(p)
    if p == raster_files[0]:
        info=subprocess.run(["gdalinfo","-json", raster_files[0]],stdout=subprocess.PIPE)
        print('***********')
        info=info.stdout.decode("utf-8")
        info_ = json.loads(info)
        if 'coordianteSystem' in info_.keys():
            proj = info_['coordinateSystem']['wkt'].split(',')[0].replace('PROJCRS[','').replace('"','')
        else:
            # no projection information available
            proj = None
    raster_to_mosiac.append(raster)

print('proj:',proj)

raster_to_mosiac
mosaic, output = merge(raster_to_mosiac)

if proj == None:
    print('step1')
    output_meta = raster.meta.copy()
    output_meta.update(
        {"driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": output,
            "crs": "epsg:"+projection
        })
    src_crs = 'EPSG:'+projection
else:
    print('step2')
    output_meta = raster.meta.copy()
    output_meta.update(
        {"driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": output,
            "crs": proj
        })    
    src_crs = proj

print('src_crs:',src_crs)

raster_output = os.path.join(dem_path, location +'1.asc')
print('raster_output:',raster_output)
raster_output_clip = os.path.join(dem_path,location +'.tif')
print('raster_output_clip:',raster_output_clip)
raster_output_image = os.path.join(dem_path,location +'_old.asc')
print('raster_output_image:',raster_output_image)
raster_output_image_crs = os.path.join(dem_path,location +'.asc')
print('raster_output_image_crs:',raster_output_image_crs)

# Write to file
with rio.open(raster_output, 'w', **output_meta) as m:
    m.write(mosaic)
    print('Raster created')


# Make a note of the directories
print('Clip_file:',boundary_1[0])
print('Input_file:',raster_output)
print('Output_file:', raster_output_clip)


command_output = subprocess.run(["gdalwarp", "-cutline", boundary_1[0], "-crop_to_cutline", raster_output,
                            raster_output_clip, '-dstnodata', '-9999'])


#Convert tif to an asc (for CityCat input)
subprocess.run(['gdal_translate', '-of', 'GTiff', raster_output_clip, raster_output_image])


#if proj != None:
dst_crs = 'EPSG:'+projection
if os.path.exists(raster_output_image): 
    reprojected = subprocess.run(["gdalwarp", "-s_srs",src_crs,"-t_srs",dst_crs, raster_output_image, raster_output_image_crs])#"-t_srs",dst_crs,
else:
    reprojected = subprocess.run(["gdalwarp", "-s_srs",src_crs,"-t_srs",dst_crs, raster_output, raster_output_image_crs])#"-t_srs",dst_crs,

if os.path.exists(raster_output_image): 
    os.remove(raster_output_image)


# Remove unclipped file
if os.path.exists(raster_output_image_crs): 
    os.remove(raster_output)
if os.path.exists(raster_output_clip): 
    os.remove(raster_output_clip)
print('Pre-clipped file removed')

dtm_size = os.getenv('DTM_SIZE')

# Print all of the input parameters to an excel sheet to be read in later
with open(os.path.join(parameter_outputs_path,'elevation-parameters.csv'), 'w') as f:
    f.write('PARAMETER,VALUE\n')
    f.write('DTM_SIZE,%s\n' %dtm_size)

# Move the boundary file to the outputs folder
if len(boundary_1) == 1 :
    
    file_path = os.path.splitext(boundary_1[0])
    print('Filepath:',file_path)
    filename=file_path[0].split("/")
    print('Filename:',filename[-1])

    src = boundary_1[0]
    print('src:',src)
    dst = os.path.join(boundary_outputs_path,filename[-1] + '.gpkg')
    print('dst,dst')
    shutil.copy(src,dst)
