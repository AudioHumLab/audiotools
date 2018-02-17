#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    v0.2b
    visor de impulsos IR wav o raw (.pcm)
    
    Si se pasan impulsos raw (.pcm) se precisa pasar también la Fs
    
    Ejemplo de uso:
    
    visor_IR.py  drcREW_test1.wav  drcREW_test1.pcm  44100 fmin-fmax
    
    fmin-fmax (Hz) es opcional y permite visualizar un rango, útil para ver graves.
    
"""
# v0.2
#   Se añade un visor de la fase y otro pequeño visor de los impulsos
# v0.2b
#   Opción del rango de frecuencias a visualizar

import sys
import numpy as np
from scipy.io import wavfile
from scipy import signal
from matplotlib import pyplot as plt
from matplotlib import ticker   # Para rotular a medida
from matplotlib import gridspec # Para ajustar disposición de los subplots

def readPCM32(fname):
    """ lee un archivo pcm float32
    """
    #return np.fromfile(fname, dtype='float32')
    return np.memmap(fname, dtype='float32', mode='r')

def readWAV16(fname):
    fs, imp = wavfile.read(fname)
    return fs, imp.astype('float32') / 32768.0
    
def lee_commandline(opcs):
    global fmin, fmax
    
    # impulsos que devolverá esta función
    IRs = []
    # archivos que leeremos
    fnames = []
    fs = 0

    for opc in opcs:
        if opc in ("-h", "-help", "--help"):
            print __doc__
            sys.exit()
            
        elif opc.isdigit():
            fs = float(opc)

        elif "-" in opc and opc[0].isdigit() and opc[-1].isdigit():
            fmin, fmax = opc.split("-")
            fmin = float(fmin)
            fmax = float(fmax)

        else:
            fnames.append(opc)

    # si no hay fnames
    if not fnames:
        print __doc__
        sys.exit()

    for fname in fnames:
    
        if fname.endswith('.wav'):
            fswav, imp = readWAV16(fname)
            IRs.append( (fswav, imp, fname) )
            
        else:
            if fs:
                imp = readPCM32(fname)
                IRs.append( (fs, imp, fname) )
            else:
                print __doc__
                sys.exit()
            
    return IRs

def prepara_eje_frecuencias(ax):
    """ según las opciones fmin, fmax, frec_ticks """
    frec_ticks = 20, 100, 1000, 10000
    ax.set_xscale("log")
    fmin2 = 10; fmax2 = 20000
    if fmin:
        fmin2 = fmin
    if fmax:
        fmax2 = fmax
    ax.set_xticks(frec_ticks)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.set_xlim([fmin2, fmax2])

def preparaGraficas():
    columnas = len(IRs)
    top_dBs = 5
    range_dBs = 30
    
    global fig, grid, axMag, axDrv, axPha, axGD, axIR
    #-------------------------------------------------------------------------------
    # Preparamos el área de las gráficas 'fig'
    #-------------------------------------------------------------------------------
    fig = plt.figure(figsize=(10,7))
    # Para que no se solapen los rótulos
    fig.set_tight_layout(True)

    # Preparamos una matriz de Axes (gráficas).
    # Usamos GridSpec que permite construir un array chachi.
    # Las gráficas de MAG ocupan 3 filas, la de PHA ocupa 2 filas,
    # y la de IR será de altura simple, por tanto declaramos 6 filas.
    grid = gridspec.GridSpec(nrows=6, ncols=columnas)

    # --- SUBPLOT para pintar las FRs (alto 3 filas, ancho todas las columnas)
    axMag = fig.add_subplot(grid[0:3, :])
    axMag.grid(linestyle=":")
    prepara_eje_frecuencias(axMag)
    axMag.set_ylim([top_dBs - range_dBs, top_dBs])
    axMag.set_ylabel("filter magnitude dB")
    
    # --- SUBPLOT para pintar las PHASEs (alto 2 filas, ancho todas las columnas)
    axPha = fig.add_subplot(grid[3:5, :])
    axPha.grid(linestyle=":")
    prepara_eje_frecuencias(axPha)
    axPha.set_ylim([-180.0,180.0])
    axPha.set_yticks(range(-135, 180, 45))
    axPha.set_ylabel(u"filter phase")
 
    # --- SUBPLOT para pintar el GD (común con el de las phases)
    # comparte el eje X (twinx) con el de la phase
    # https://matplotlib.org/gallery/api/two_scales.html
    axGD = axPha.twinx()
    axGD.grid(False)
    prepara_eje_frecuencias(axGD)
    axGD.set_ylim(-25, 75)
    axGD.set_ylabel(u"--- filter GD (ms)")
    
if __name__ == "__main__":

    fmin = 10
    fmax = 20000

    if len(sys.argv) == 1:
        print __doc__
        sys.exit()

    IRs = lee_commandline(sys.argv[1:])
        
    preparaGraficas()

    columnaIR = 0
    for IR in IRs:
    
        fs, imp, info = IR
        fny = fs/2.0
        limp = imp.shape[0]
        limpK = limp / 1024
        peakOffset = np.round(abs(imp).argmax() / fs, 3) # en segundos

        # 500 bins de frecs logspaciadas para que las resuelva freqz
        w1 = 1 / fny * (2 * np.pi)
        w2 = 2 * np.pi
        bins = np.geomspace(w1, w2, 500)

        # Semiespectro
        # whole=False --> hasta Nyquist
        w, h = signal.freqz(imp, worN=bins, whole=False)
        # frecuencias trasladadas a Fs
        freqs = w / np.pi * fny
        
        # Magnitud
        magdB = 20 * np.log10(abs(h))

        # Wrapped Phase
        phase = np.angle(h, deg=True)

        # Group Delay
        wgd, gd = signal.group_delay((imp, 1), w=bins, whole=False)
        # GD es en radianes los convertimos a milisegundos
        gdms = gd / fs * 1000 - peakOffset * 1000
        
        # PLOTEOS
        axMag.plot(freqs, magdB, label=info)
        color = axMag.lines[-1].get_color() # anotamos el color de la última línea        
        axPha.plot(freqs, phase, "-", linewidth=1.0, color=color)
        axGD.plot(freqs, gdms, "--", linewidth=1.0, color=color)
    
        # plot del IR. Nota: separamos los impulsos en columnas
        axIR = fig.add_subplot(grid[5, columnaIR])
        axIR.set_title(str(limpK) + " Ktaps - pk offset " + str(peakOffset) + " s")
        axIR.set_xticks(range(0,len(imp),10000))
        axIR.ticklabel_format(style="sci", axis="x", scilimits=(0,0))
        axIR.plot(imp, "-", linewidth=1.0, color=color)
        columnaIR += 1

    axMag.legend(loc='lower right', prop={'size':'small', 'family':'monospace'})
    plt.show()

   
