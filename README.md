# Argile

[![N|Solid](https://cldup.com/dTxpPi9lDf.thumb.png)](https://nodesource.com/products/nsolid)

**Argile** is a maya plugin and python script used for postSculpt.

It is used by Blur studios 

Pronounce it  **aʀʒil** (french for clay)

This package include 
  - argile (python module for ui)
  - cpp *blurPostDeform.mll* for maya 2016, 2016.5, 2017

### Installation

Copy the argile folder in maya scripts directory : 
```sh
    C:\Users\...\Documents\maya\scripts\argile
```
It already contains the .mll plugins

 ### CPP
The *argileCppCode* folder contains the code to compile blurPostDeform cpp plugin

### Run in Maya
To open the argile tool in maya run the following command : 
```sh
from argile import runArgileDeformUI
runArgileDeformUI() 
```
