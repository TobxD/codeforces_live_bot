#!/bin/bash

arg=$1
if [ $# -eq 0 ]
  then arg=0
fi
gnuplot -e "col=$arg" gnuplotInstr.txt
