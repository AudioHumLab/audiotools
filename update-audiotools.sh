#!/bin/bash

cd ~/

# Borramos si hubiera algun master.zip
if [[ -f master.zip ]]; then
    rm master.zip*
fi

# Bajamos el zip de GitHUb
wget https://github.com/Rsantct/audiotools/archive/master.zip
# Descomprimos (se descomprime en audiotools-master)
unzip -o master.zip

# Borramos lo antiguo
rm -rf ~/audiotools

# Y renombramos el directorio descomprimido
mv audiotools-master audiotools

# Hacemos ejecutables los archivos
chmod +x audiotools/*

# Incluimos auditools en el profile del usuario
profileFile=$(ls -a .*profile*)
if ! grep -q "bin" "$profileFile"; then
    export PATH=$PATH:$HOME/audiotools
    echo "export PATH=$PATH:$HOME/audiotools" >> profileFile
fi