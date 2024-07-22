FROM python:3.11

RUN mkdir /src
RUN mkdir /data

WORKDIR /src

RUN apt-get -y update
RUN pip install geopandas rasterio
RUN apt-get -y install libgdal-dev gdal-bin

# RUN apt -y install libgdal-dev
# RUN pip install gdal==3.6.0 geopandas rasterio


ENV DTM_SIZE 5

COPY run.py /src

ENTRYPOINT python run.py
