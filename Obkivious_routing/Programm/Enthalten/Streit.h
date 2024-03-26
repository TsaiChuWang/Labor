#define STREIT

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "./Aufbau.h"

#define MAX_NAME_LÄNGE 50

#ifdef STREIT

struct Streit{
    char* DATEI_NAME;   // File nmae of .lp

    int ANZAHL_KANTEN;  // Number of edges
    int ANZAHL_KNOTEN;  // Number of edges

    int GLEICHE_KAPAZITÄT; // Each link has same capacity 

    int** BOGEN;
    int** LISTE;
};

struct Streit nehmenStreit(int code){
    struct Streit streit;

    switch(code){
        case 1:
            streit.DATEI_NAME = "erste_modul";

            streit.ANZAHL_KANTEN = 20;
            streit.ANZAHL_KNOTEN = 6;

            streit.GLEICHE_KAPAZITÄT = 100;
            
            int topology[6][6] =
                {{0,1,1,0,0,0},
                 {1,0,1,1,1,0},
                 {1,1,0,1,1,0},
                 {0,1,1,0,1,1},
                 {0,1,1,1,0,1},
                 {0,0,0,1,1,0}};

            streit.BOGEN = (int**)malloc(sizeof(int*)*streit.ANZAHL_KNOTEN);
            for(int i=0;i<streit.ANZAHL_KNOTEN;i++){
                streit.BOGEN[i] = (int*)malloc(sizeof(int)*streit.ANZAHL_KNOTEN);
                for(int j=0;j<streit.ANZAHL_KNOTEN;j++)
                    streit.BOGEN[i][j] = topology[i][j];
            }
            
            streit.LISTE = (int**)malloc(sizeof(int*)*streit.ANZAHL_KNOTEN);
            for(int i=0;i<streit.ANZAHL_KNOTEN;i++){
                streit.LISTE[i] = (int*)malloc(sizeof(int)*streit.ANZAHL_KNOTEN);
                for(int j=0;j<streit.ANZAHL_KNOTEN;j++)
                    streit.LISTE[i][j] = topology[i][j];
            }
            break;
    }
    
    return streit;
}

int zuordnungCode(char* name){
    if(strcmp(name, "EINS") == ERFOLG)  //
        return 1;
    return FEHLGESCHLAGEN;
}

#endif