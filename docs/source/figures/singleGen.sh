 #!/bin/sh


docker pull minlag/mermaid-cli
docker run --rm -u `id -u`:`id -g` -v `pwd`:/data minlag/mermaid-cli -f \
    -i /data/$1.mmd \
    --scale 4 \
    -o /data/$1.png \
    -b transparent