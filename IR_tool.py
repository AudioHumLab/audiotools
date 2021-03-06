#!/usr/bin/env python3

"""
    Visor de impulsos IR .wav, .pir, o datos en bruto ( binarios o de texto plano)

    (i) Los archivos binarios deben estar codificados 'float32'.

    Si se pasan impulsos raw (binarios o de texto) se precisa indicar la FS

    Ejemplo de uso:

    IR_tool.py  file1.wav  file2.pcm  [FS]  [ fmin-fmax -1 -eq -lptolX -pha]

    Opciones:

    FS              sampling frequency

    -f=min-max      Rango de frecuencias visualizado (Hz)

    -dBrange=X      Rango de magnitudes visualizado (dB)

    -dBtop=X        Límite superior de la visualización (dB)

    -1              Muestra las gráficas de los impulsos en una fila única.

    -pdf            Guarda la gráfica en archivo PDF, incluyendo el zoom
                    que se hiciese durante la visualización.

    -lptol=X        Tolerancia en dB para evaluar si el impulso es linear phase
                    (por defecto -60 dB)

    -pha            Muestra la fase (experimental)

"""
# version = 'v0.2c'
#   Opcion -pha oculta para pintar la phase (WORK IN PROGRESS)
#
# version = 'v0.2d'
#   Dejamos de pintar phases o gd fuera de la banda de paso,
#   con nuevo umbral a -50dB parece más conveniente para FIRs cortos con rizado alto.
#   Se aumenta el rango de magnitudes hasta -60 dB
#   Muestra el pkOffset en ms
#   El GD recoge en la gráfica el delay del pico del filtro.
#   Se deja de mostrar los taps en 'Ktaps'
#
# version = 'v0.2f'
#   Axes de impulsos en una fila opcinalmente
#   Se muestra la versión del programa al pie de las gráficas.
#
# version = 'v0.2i'
#   Admite IRs en archivos de texto.
#
# version = 'v0.2ip3'
#   Python3
#
#
# TO DO:
#   Revisar la información mostrada "GD avg" que pretende ser la moda de los valores
#
#
# version = 'v0.2j'
#   Pinta la phase symmetrical log scale (experimental):
#       - En filtros lin-pha se aproxima a una recta,
#       - En filtros no lin-pha veremos una curva clara
#       - Se informa si el filtro es lin-pha (simétrico respecto del pico)
#
version = 'v0.2k'
#   lee PIR de ARTA

import sys
import numpy as np, math
from scipy import signal
from matplotlib import pyplot as plt
from matplotlib.ticker import EngFormatter
from matplotlib import gridspec             # customize subplots array
import tools


def lee_commandline(opcs):

    global fmin, fmax, plotPha, dBtop, dBrange, lp_tolerance
    global plotIRsInOneRow, generaPDF

    plotIRsInOneRow = False
    generaPDF = False

    # impulsos que devolverá esta función
    IRs = []
    # archivos que leeremos
    fnames = []
    fs = 0
    plotPha = False

    for opc in opcs:
        if opc in ("-h", "-help", "--help"):
            print (__doc__)
            sys.exit()

        elif opc.isdigit():
            fs = float(opc)

        elif opc[:3] == "-f=":
            fmin, fmax = opc.split("=")[-1].split("-")
            fmin = float(fmin)
            fmax = float(fmax)

        elif opc[:7].lower() == "-dbtop=":
            dBtop = float(opc[7:])

        elif opc[:9].lower() == "-dbrange=":
            dBrange = float(opc[9:])

        elif "-ph" in opc:
            plotPha = True

        elif opc[:7] == "-lptol=":
            value = float(opc[7:])
            if value <= 0:
                lp_tolerance = value
            else:
                raise ValueError('-lptol <= 0 dB')

        elif opc == "-1":
            plotIRsInOneRow = True

        elif opc == "-pdf":
            generaPDF = True

        else:
            fnames.append(opc)

    # si no hay fnames
    if not fnames:
        print (__doc__)
        sys.exit()

    for fname in fnames:

        if fname.endswith('.wav'):
            fswav, imp = tools.readWAV(fname)
            IRs.append( (fswav, imp, fname) )

        elif fname.endswith('.pir'):
            fspir, imp = tools.readPIR(fname)
            IRs.append( (fspir, imp, fname) )

        elif fname.endswith('.pcm') or \
             fname.endswith('.bin') or \
             fname.endswith('.f32'):
            if fs:
                imp = tools.readPCM(fname, dtype='float32')
                IRs.append( (fs, imp, fname) )
            else:
                print (__doc__)
                sys.exit()

        else:   # it is supposed to be a text file
            if fs:
                imp = np.loadtxt(fname)
                IRs.append( (fs, imp, fname) )
            else:
                print (__doc__)
                sys.exit()

    return IRs


def prepara_eje_frecuencias(ax):

    ax.set_xscale("log")

    # nice formatting "1 K" flavour
    ax.xaxis.set_major_formatter( EngFormatter() )
    ax.xaxis.set_minor_formatter( EngFormatter() )

    # rotate_labels for both major and minor xticks
    for label in ax.get_xticklabels(which='both'):
        label.set_rotation(70)
        label.set_horizontalalignment('center')

    ax.set_xlim([fmin, fmax])


def preparaGraficas():

    plt.rcParams.update({'font.size': 8})

    numIRs = len(IRs)
    global fig, grid, axMag, axDrv, axPha, axGD, axIR

    #-------------------------------------------------------------------------------
    # Preparamos el tamaño de las gráficas 'fig'
    #-------------------------------------------------------------------------------
    if plotIRsInOneRow:
        fig = plt.figure(figsize=(9, 6))
    else:
        fig = plt.figure(figsize=(9, 8 + numIRs))

    # Tamaño de la fuente usada en los títulos de los axes
    plt.rcParams.update({'axes.titlesize': 'medium'})

    # Para que no se solapen los rótulos
    fig.set_tight_layout(True)

    #-------------------------------------------------------------------------------
    # Preparamos una matriz de Axes (gráficas).
    # Usamos GridSpec que permite construir un array chachi.
    # Las gráficas de MAG ocupan 3 filas, la de PHA ocupa 2 filas,
    # y gráfica de IR según la opcion elegida:
    #   - en una fila única simple declaramos 6 filas y numIRs columnas
    #   - en filas independientes de altura doble declaramos 5 + 2*numIRs filas.
    #-------------------------------------------------------------------------------

    if plotIRsInOneRow:
        grid = gridspec.GridSpec(nrows = 6, ncols = numIRs)
    else:
        grid = gridspec.GridSpec(nrows = 5 + 2*numIRs, ncols = 1)

    # --- SUBPLOT para pintar las FRs (alto 3 filas, ancho todas las columnas)
    axMag = fig.add_subplot(grid[0:3, :])
    axMag.grid(True, which='both', linestyle=":")
    prepara_eje_frecuencias(axMag)
    axMag.set_ylabel("magnitude (dB)")
    axMag.set_yticks(range(-210, 210, 3), minor=True)
    axMag.set_yticks(range(-210, 210, 6), minor=False)

    # --- SUBPLOT para pintar el GD (alto 2 filas, ancho todas las columnas)
    # comparte el eje X (twinx) con el de la phase
    # https://matplotlib.org/gallery/api/two_scales.html
    axGD = fig.add_subplot(grid[3:5, :])
    axGD.grid(False)
    prepara_eje_frecuencias(axGD)
    #axGD.set_ylim(-25, 75) # dejamos los límites del eje y para cuando conozcamos el GD
    axGD.set_ylabel(u"--- filter GD (ms)")

    # --- SUBPLOT para pintar las PHASEs (común con el de GD)
    if plotPha:
        axPha = axGD.twinx()
        axPha.grid(linestyle=":")
        prepara_eje_frecuencias(axPha)
        axPha.set_ylabel(u"filter unwrapped phase")
        axPha.set_yscale('symlog')
        # Hide y-ticks
        axPha.yaxis.set_major_locator(plt.NullLocator())


def check_lin_pha(imp, tol):

    result = False

    # Ensure the impulse is centered
    center = np.argmax(imp)
    if center - imp.shape[0] // 2 > 1:
        return False

    # Check if symmetric with tolerance
    atol = 10 ** (tol/20.0)
    if imp.shape[0] % 2 == 0:
        begin = 1
    else:
        begin = 0

    try:
        result = np.allclose(imp[begin:center], imp[center + 1:][::-1], atol=atol)
    except:
        print( '(!) error when checking for linear phase, sorry :-/ ' )

    return result


if __name__ == "__main__":

    dBtop   = 5  # inicial lugo se reajustará
    dBrange = 65
    fmin = 20
    fmax = 20000
    # Umbral de la magnitud en dB para dejar de pintar phases o gd
    magThr = -50.0
    # Umbral en dB para evaluar si el impulso es linear phase
    lp_tolerance = -60 # dB

    if len(sys.argv) == 1:
        print (__doc__)
        sys.exit()

    IRs = lee_commandline(sys.argv[1:])

    preparaGraficas()

    GDavgs = [] # los promedios de GD de cada impulso, para mostrarlos por separado

    IRnum = 0

    for IR in IRs:

        fs, imp, info = IR
        fny = fs/2.0
        limp = len(imp)
        peakOffsetms = np.round(abs(imp).argmax() / fs * 1000, 1) # en ms

        # Semiespectro
        # whole=False --> hasta Nyquist
        w, h = signal.freqz(imp, worN=int(len(imp)/2), whole=False)

        # frecuencias trasladadas a Fs
        freqs = w / np.pi * fny

        # Magnitud:
        magdB = 20 * np.log10(abs(h))

        # Un wrapped Phase:
        phase = np.unwrap( np.angle(h) )
        # Eliminamos (np.nan) los valores de phase fuera de
        # la banda de paso, por debajo de un umbral configurable.
        phaseClean  = np.full((len(phase)), np.nan)
        mask = (magdB > magThr)
        np.copyto(phaseClean, phase, where=mask)
        phaseClean *= 180 / (2*np.pi)

        # Group Delay:
        wgd, gd = signal.group_delay((imp, 1), w=int(len(imp)/2), whole=False)
        # Eliminamos (np.nan) los valores fuera de
        # la banda de paso, por debajo de un umbral configurable.
        gdClean  = np.full((len(gd)), np.nan)
        mask = (magdB < magThr)
        np.copyto(gd, gdClean, where=mask)
        # GD es en radianes los convertimos a milisegundos
        gdms = gd / fs * 1000
        # Computamos el GD promedio (en ms) para mostrarlo en la gráfica
        #   1. Vemos un primer promedio
        gdmsAvg = np.round(np.nanmean(gdms), 1)
        #   2. limpiamos las desviaciones > 5 ms respecto del promedio (wod: without deviations)
        gdmswod = np.full((len(gdms)), np.nan)
        mask = (gdms < (gdmsAvg + 5.0) ) # nota: se muestra un Warning porque se evalúan valores np.nan
        np.copyto(gdmswod, gdms, where=mask)
        #   3. Promedio recalculado sobre los valores without deviations
        gdmsAvg = np.round(np.nanmean(gdms), 1)
        GDavgs.append(gdmsAvg)

        # ---- PLOTEOS ----

        # Ploteo de la Magnitud con autoajuste del top
        tmp = np.max(magdB)
        tmp = math.ceil(tmp/5.0) * 5.0 + 5.0
        if tmp > dBtop:
            dBtop = tmp
        axMag.set_ylim(dBtop - dBrange, dBtop)
        axMag.plot(freqs, magdB, label=info)
        color = axMag.lines[-1].get_color() # anotamos el color de la última línea

        # Phase
        if plotPha:
            axPha.plot(freqs, phaseClean, "-", linewidth=1.0, color=color)

        # Ploteo del GD con autoajuste del top
        ymin = peakOffsetms - 25
        ymax = peakOffsetms + 75
        axGD.set_ylim(bottom = ymin, top = ymax)
        axGD.plot(freqs, gdms, "--", linewidth=1.0, color=color)

        # Plot del IR
        # (i) Opcionalmente podemos pintar los impulsos en una sola fila
        rotuloIR = str(limp) + " taps - pk offset " + str(peakOffsetms) + " ms"
        if check_lin_pha(imp, lp_tolerance):
            rotuloIR += f'\nlinear phase (tolerance {lp_tolerance} dB)'
        else:
            rotuloIR += f'\nnot linear phase (tolerance {lp_tolerance} dB)'
        if plotIRsInOneRow:
            # Todos los IRs en una fila de altura simple, en columnas separadas:
            axIR = fig.add_subplot(grid[5, IRnum]) # (i) grid[rangoVocupado, rangoHocupado]
            # Rotulamos en el espacio de título:
            axIR.set_title(rotuloIR)
        else:
            # Cada IR en una fila de altura doble:
            axIR = fig.add_subplot(grid[5+2*IRnum:5+2*IRnum+2, :])
            # Rotulamos dentro del axe:
            axIR.annotate(rotuloIR, xy=(.6,.8), xycoords='axes fraction') # coords referidas al area gráfica
        IRnum += 1
        axIR.set_xticks(range(0,len(imp),10000))
        axIR.ticklabel_format(style="sci", axis="x", scilimits=(0,0))
        axIR.plot(imp, "-", linewidth=1.0, color=color)

    # Mostramos los valores de GD avg de cada impulso:
    GDtitle = 'GD avg:    ' + '    '.join([str(x) for x in GDavgs]) + ' (ms)'
    axGD.set_title(GDtitle)

    # Leyenda con los nombres de los impulsos en el gráfico de magnitudes
    axMag.legend(loc='lower right', prop={'size':'small', 'family':'monospace'})

    # Y un footer con la versión:
    progname = sys.argv[0].split("/")[-1]
    footer = "AudioHumLab " + progname + " " + version
    plt.gcf().text(0.01, 0.01, footer, size='smaller')

    # Finalmente mostramos las gráficas por pantalla.
    plt.show()

    if generaPDF:
        # Y guardamos las gráficas en un PDF:
        pdfName = ",".join([x for x in sys.argv[1:] if '.' in x]) + '.pdf'
        print ( f'\nGuardando en el archivo: {pdfName}' )
        # evitamos los warnings del pdf
        # C:\Python27\lib\site-packages\matplotlib\figure.py:1742: UserWarning:
        # This figure includes Axes that are not compatible with tight_layout, so
        # its results might be incorrect.
        import warnings
        warnings.filterwarnings("ignore")
        fig.savefig(pdfName, bbox_inches='tight')

    print ("Bye!")
