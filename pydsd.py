#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    pydsd v0.01aBETA
    
    %%%%%%%%%%%%%%  DSD  %%%%%%%%%%%%%%%%%
    %% Traslación a python/scipy de     %%
    %% funciones del paquete DSD        %%
    %% https://github.com/rripio/DSD    %%
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    DISCLAIMER: El autor de DSD no garantiza ni supervisa
                esta traslación.
                
    ACHTUNG:    work in progress BETA

    Nota:       En cada función adaptada podemos ver código
                original en octave comentado con #%%
"""
# v0.01aBETA
# + blackmanharris
# *'blackman' functions renombradas a *'blackmanharris'

import numpy as np
from scipy import signal, interpolate

def semiblackmanharris(m):
    """
    %% Obtiene la mitad derecha de una ventana Blackman-Harris de longitud m.
    %% w = Ventana.
    %% m = Número de muestras.
    """
    # generamos la ventana con tamaño 2*m
    w = signal.blackmanharris(2*m)
    # devolvemos la mitad derecha
    return w[m:]

def blackmanharris(m):
    """
    %% Obtiene una ventana Blackman-Harris de longitud m.
    """
    return signal.blackmanharris(m)

def minphsp(sp):
    """
    %% Obtiene el espectro de fase mínima a partir de un espectro completo.
    %% minph = Espectro completo de fase mínima con la misma magnitud de espectro que imp.
    %% sp    = Espectro completo. Longitud par.
    Nota del traductor:
        El espectro en phase minima se consigue simplemente haciendo
        la transformada de Hilbert de la magnitud del espectro proporcionado.
    """

    if not sp.ndim == 1:
        raise ValueError("ssp must be a column vector")

    #%% exp(conj(hilbert(log(abs(sp)))));
    return np.exp(np.conj(signal.hilbert(np.log(abs(sp)))));

def wholespmp(ssp):
    """
    %% Obtiene el espectro causal completo a partir 
    %% del espectro de las frecuencias positivas.
    %% ssp = Espectro de las frecuencias positivas entre 0 y m/2.
    %% wsp = Espectro completo entre 0 y m-1 (m par).
    
    Nota del traductor:
        entrada: un semiespectro de trabajo de freq positivas
        salida:  el espectro completo
    """

    if not ssp.ndim == 1:
        raise ValueError("ssp must be a column vector")

    m = len(ssp) 
    # Verifica que la longitud del espectro proporcionado sea impar 
    if m % 2 == 0:
        raise ValueError("wholespmp: Spectrum length must be odd")

    #%% nsp = flipud(conj(ssp(2:m-1)));
    nsp = np.conj(ssp[1:m-2])
    nsp = nsp[::-1]

    #%% [ssp;nsp];
    return np.concatenate([ssp, nsp])
    
def lininterp(F, mag, m, fs):
    """
    %% Obtiene la valores de magnitud interpolados sobre el semiespectro.
    %% mag    = Magnitud a interpolar.
    %% F      = Vector de frecuencias.
    %% m      = Longitud del espectro completo (debe ser par).
    %% fs     = Frecuencia de muestreo.
    """

    if not F.ndim == 1:
        raise ValueError("F must be a column vector")
    if not m % 2 == 0:
        raise ValueError("m must be even")

    # Prepara el nuevo vector de frecuencias OjO lo genera de long impar m/2+1
    #%% fnew = (0:m/2)'*fs/m; % column vector
    fnew = np.arange(0, m/2) * fs/m
    
    # DSD usa a la funcion de interpolación interp1:
    # (nota: maglin es la variable resultado que entregará esta función)
    #%% maglin = interp1(F, mag, fnew, "spline");
    #   Traducción a scipy de la función de interpolación.
    #   Primero se define, luego se usa.
    #   Eludimos errores si se pidieran valores fuera de rango,
    #   y rellenamos extrapolando si fuera necesario.
    #   'cubic' == 'spline 3th order'
    I = interpolate.interp1d(F, mag, kind="cubic", bounds_error=False, 
                             fill_value="extrapolate")
    # Obtenemos las magnitudes interpoladas en las 'fnew':
    maglin = I(fnew)
    
    # Y esto ¿¿¿??
    #%% maglin(fnew<F(1)  )=mag(1);
    #%% maglin(fnew>F(end))=mag(end);

    return maglin

        
