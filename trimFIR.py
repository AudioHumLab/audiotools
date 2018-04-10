#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    v0.1

    Recorta un FIR .pcm float32 o .wav int16 aplicando una ventana
    El resultado se guarda en formato .pcm float 32

    Uso y opciones:

        python trimPCM.py  file.pcm -tM [-pP] [-sym] [-o] [-lp|-mp]

        -tM     M taps de salida potencia de 2 (sin espacios)
        
        -lp     equivale a -sym
        
        -mp     equivale a -p0

        -pP     Posición en P taps del peak en el FIR de entrada (no se buscará).
                Si se omite -p, se buscará el peak automáticamente.

        -sym    Ventana simétrica.
                Si se omite se aplicará una semiventana.

        -o      Sobreescribe el archivo original.
                Si se omite se le añade un prefijo 'Mtaps_'

    Notas de aplicación:

    tipo de FIR             ventana           peakPos
    -----------------       -------           -------
    minimum phase                             0
    linear phase            -sym              auto/userdef
    linear + min phase      -sym              auto/userdef

"""

# ----------   config   -------------------
# En enventanado asimétrico, fracción de 'M'
# que se enventanará por delante del pico
frac = 0.001
# -----------------------------------------

import sys
import numpy as np
import pydsd as dsd
import utils

def lee_opciones():
    global f_in, f_out, phasetype
    global m, overwriteFile, sym, pkPos
    f_in = ''
    phaseType= ''
    pkPos = -1 # fuerza la búsqueda
    m = 0
    overwriteFile = False
    sym = False
    if len(sys.argv) == 1:
        print __doc__
        sys.exit()
    for opc in sys.argv[1:]:
        if opc.startswith('-t'):
            m = int(opc.replace('-t', ''))
            if not utils.isPowerOf2(m):
                print __doc__
                sys.exit()
        elif opc.startswith('-p'):
            pkPos = int(opc.replace('-p', ''))
        elif opc == '-h' or opc == '--help':
            print __doc__
            sys.exit()
        elif opc == '-o':
            overwriteFile = True
        elif opc == '-sym':
            sym = True
        elif opc == '-lp':
            phaseType = 'lp'
        elif opc == '-mp':
            phaseType = 'mp'
        else:
            if not f_in:
                f_in = opc
    if not m:
        print __doc__
        sys.exit()

    if phaseType == 'lp':
        sym = True
        pkPos = -1 # pkPos autodiscovered
    if phaseType == 'mp':
        sym = False
        pkPos = 0

        
    # El nombre de archivo de salida depende de si se pide sobreescribir
    if not overwriteFile:
        f_out = str(m) + "taps_" + f_in.replace('.wav', '.pcm')
    else:
        f_out = f_in.replace('.wav', '.pcm')


if __name__ == "__main__":

    # Leemos opciones
    lee_opciones()

    # Leemos el impulso de entrada imp1
    if   f_in[-4:] == '.pcm':
        imp1 = utils.readPCM32(f_in)
    elif f_in[-4:] == '.wav':
        fs, imp1 = utils.readWAV16(f_in)
    else:
        print "(i) trimFIR.py '" + f_in + "' no se reconoce :-/"
        sys.exit()

    # Buscamos el pico si no se ha indicado una posición predefinida:
    if pkPos == -1:
        pkPos = abs(imp1).argmax()

    # Enventanado NO simétrico
    if not sym:
        # Hacemos dos semiventanas, una muy corta por delante para pillar bien el impulso
        # y otra larga por detrás hasta completar los taps finales deseados:
        nleft  = int(frac * m)
        if nleft <= pkPos:
            nright = m - nleft
            imp2L = imp1[pkPos-nleft:pkPos]  * dsd.semiblackman(nleft)[::-1]
            imp2R = imp1[pkPos:pkPos+nright] * dsd.semiblackman(nright)
            imp2 = np.concatenate([imp2L, imp2R])
        else:
            imp2 = imp1[0:m] * dsd.semiblackman(m)

    # Enventanado simétrico
    else:
        # Aplicamos la ventana centrada en el pico
        imp2 = imp1[pkPos-m/2 : pkPos+m/2] * dsd.blackman(m)

    # Informativo
    pkPos2 = abs(imp2).argmax()

    # Y lo guardamos en formato pcm float 32
    utils.savePCM32(imp2, f_out)
    print "FIR recortado en: " + f_out + " (peak:" + str(pkPos) + " peak_" + str(m) + ":" + str(pkPos2) + ")"
