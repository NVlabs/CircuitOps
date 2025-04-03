FROM ubuntu:22.04

WORKDIR /src
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y gnupg2 ca-certificates

RUN echo "deb [trusted=yes] https://downloads.skewed.de/apt jammy main" >> /etc/apt/sources.list
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-key 612DEFB798507F25
RUN apt-get update

RUN apt-get install -y git
RUN apt-get install -y gcc g++
RUN apt-get install -y libpython-all-dev
RUN apt-get install -y libboost-all-dev
RUN apt-get install -y libcairo2
RUN apt-get install -y libcairo2-dev
RUN apt-get install -y python3-matplotlib
RUN apt-get install -y nvidia-cuda-toolkit
RUN apt-get update
RUN apt-get install -y python3-graph-tool

RUN apt-get install -y vim
RUN apt-get install -y python3-pip

RUN apt update
RUN apt install -y libqt5charts5 libqt5charts5-dev

RUN pip install --no-cache-dir torch==2.2.0
RUN pip install dgl==0.9.1
RUN pip install pandas
RUN pip install networkx==2.6.3
RUN pip install scikit-learn
RUN pip install numpy==1.24.4
RUN pip install tqdm==4.53.0

WORKDIR /app
RUN git clone --recursive https://github.com/NVlabs/CircuitOps.git

WORKDIR /app/CircuitOps/src/OpenROAD/
RUN ./etc/DependencyInstaller.sh
RUN mkdir build
WORKDIR /app/CircuitOps/src/OpenROAD/build
RUN cmake ..
RUN make -j

WORKDIR /app


COPY . /app
