#define STREIT

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "./Aufbau.h"

#ifdef STREIT

struct Streit{
    char* DATEI_NAME;   // File nmae of .lp

    int ANZAHL_KANTEN;  // Number of edges
    int ANZAHL_KNOTEN;  // Number of edges

    int GLEICHE_KAPAZITÄT; // Each link has same capacity 

    int** BOGEN;
    int** LISTE;
};

int** bereichkopieren(int anzahl_knoten, int topology[anzahl_knoten][anzahl_knoten]){
    int** bereich = (int**)malloc(sizeof(int*)*anzahl_knoten);
    for(int i=0;i<anzahl_knoten;i++){
        bereich[i] = (int*)malloc(sizeof(int)*anzahl_knoten);
        for(int j=0;j<anzahl_knoten;j++)
            bereich[i][j] = topology[i][j];
    }
    return bereich;
}

struct Streit nehmenStreit(int code){
    struct Streit streit;

    switch(code){
        case 1:
            streit.DATEI_NAME = "erste_modul";

            streit.ANZAHL_KANTEN = 20;
            streit.ANZAHL_KNOTEN = 6;

            streit.GLEICHE_KAPAZITÄT = 100;
            
            int topology_1[6][6] =
                {{0,1,1,0,0,0},
                 {1,0,1,1,1,0},
                 {1,1,0,1,1,0},
                 {0,1,1,0,1,1},
                 {0,1,1,1,0,1},
                 {0,0,0,1,1,0}};

            streit.BOGEN = bereichkopieren(streit.ANZAHL_KNOTEN, topology_1);
            streit.LISTE = bereichkopieren(streit.ANZAHL_KNOTEN, topology_1);

            break;
        
        case 7:
            streit.DATEI_NAME = "SANReN";

            streit.ANZAHL_KANTEN = 14;
            streit.ANZAHL_KNOTEN = 7;

            streit.GLEICHE_KAPAZITÄT = 462;

            int topology_7[7][7] =
                {{0,1,0,0,0,0,1},
                {1,0,1,0,0,0,0},
                {0,1,0,1,0,0,0},
                {0,0,1,0,1,0,0},
                {0,0,0,1,0,1,0},
                {0,0,0,0,1,0,1},
                {1,0,0,0,0,1,0}};

            streit.BOGEN = bereichkopieren(streit.ANZAHL_KNOTEN, topology_7);
            streit.LISTE = bereichkopieren(streit.ANZAHL_KNOTEN, topology_7);

            break;
    }
    
    return streit;
}

int zuordnungCode(char* name){
    if(strcmp(name, "EINS") == ERFOLG)  // Hausaufgaben Vier
        return 1;
    
    if(strcmp(name, "SANReN") == ERFOLG)    // South African National Research Network (SANReN)
	    return 7;
        
    return FEHLGESCHLAGEN;
}

#endif