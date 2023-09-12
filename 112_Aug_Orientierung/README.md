# 112_Aug_Orientierung

Tags: mininet, orientation
Datum: 12. September 2023
Status: Im Gange

Hier beginnt alles, es stehen vier Experimente an.
Um es ganz klar auszudrücken: Dieses Experiment wurde von meinen Vorgesetzten als Lebensmittelverschwendung beschimpft, daher empfehle ich, es nicht zu erwähnen, obwohl ich sehr hart gearbeitet habe.

## Flow entries management

![Topology_Year1_Tutorial.pptx (3).png](images/Topology_Year1_Tutorial.pptx_(3).png)

### Ping test (Matching switch port and IP/MAC Address)

- H1🡨🡪H3
- H2🡨🡪H4

### IPERF test (Matching IP and TCP port)

- H1🡨🡪H4
- H3🡨🡪H4

### Meter test (Matching IP and UDP, limit users’ bandwidth)

- H1🡨🡪H3 with rate 300Mbps
- H3🡨🡪H4 with rate 200Mbps